# 03 接口、张量、状态和来源合同

**本章全部 `LateState*` 类型、新 Op 和新增参数均为待实现合同。** 既有 `Tensor` / `WorkspaceArena` / CUDA stream 使用仓库已有定义。不要建立独立推理 API 或复制 `Program`。

## 1. 宿主策略类型

建议新增 `src/targets/qwen3_8/impl/runtime/late_state_policy.h`；只有 27B package 宣告支持。跨包调度通过现有 Variant trait 进入，不硬编码模型字符串分支。

```cpp
using Digest256 = std::array<std::uint8_t, 32>;
enum class LateStateMode { Off, Auto };
enum class PrefixOrigin { Native, Approximate };

struct LateStateConfig {
    LateStateMode mode = LateStateMode::Off;
    std::uint32_t split_layer = 48;
    std::uint32_t tail_tokens = 2048;
    std::uint32_t min_uncached_tokens = 32768;
    std::uint32_t qualified_context = 200000;
};
struct LateStatePlan {
    std::uint32_t total_tokens;
    std::uint32_t approximate_end; // p, exclusive
    std::uint32_t split_layer;
    std::uint32_t tail_begin;       // always equal to approximate_end
    bool use_prediction;
};
struct LateStateProvenance {
    PrefixOrigin origin;
    Digest256 predictor_sha256;  // zero only for Native
    Digest256 compute_profile_sha256;
    std::uint32_t split_layer;
    std::uint32_t approximate_end;
    std::uint32_t original_tail_tokens;
    std::uint32_t synthesis_version;
};
```

`compute_profile_sha256` 覆盖 prefill 精度、chunk schedule、codec/layout、Predictor precision、state-only 实现版本、MTP backend/window、position profile；仍须使用现有 artifact、adapter、token/media identity 检查，不能替代它们。

`plan_late_state(config,n,uncached,has_native_prefix,supported)`：只对冷输入、n≤qualified_context、uncached≥min_uncached、p>0、受支持 profile 返回预测计划。`tail_tokens=0`、split 不合法、容量不足在 admission 前失败。Unsupported profile 的 auto 模式走 native；无法在当前进程安全满足 native 的请求明确拒绝，不能自动换模型。

## 2. 分层执行

在现有 `TextContext` 内新增：

```cpp
template<class Tap>
void run_layers_range(Tensor& x, Phase phase,
                      int begin_layer, int end_layer, Tap& tap);
```

`0<=begin<=end<=64`；区间左闭右开。现有 `run_layers(x,ph,tap)` 必须严格委托 `[0,64)`。相同层顺序、workspace 生命周期、projection phase 与 tap 位置不变。`Phase::Verify` 仍沿用原语义，不新造一个未接入的 Decode enum。

split 位于完整四层 hybrid block 边界，即 32/40/48。边界 hidden 是最后一层 post-mixer residual `x`，不是该层 input norm，也不是全模型 final norm。

## 3. Predictor 输出张量

以下维度用数学 `[T,channels]` 便于说明，落入 NInfer 时转为连续 `[channels,T]` 并按现有 `Tensor.ne` 合同解释。禁止未经校验的 transpose/view。

| 输出 | 每层 shape | represented dtype | 后续处理 |
|---|---|---|---|
| `attn_k_projected` | [T,4,256] | BF16 | 真正 K norm + 绝对 RoPE + codec append |
| `attn_v_projected` | [T,4,256] | BF16 | codec append；不做额外 RoPE |
| `gdn_preconv_qkv` | [T,10240] | BF16 | 真正 width-4 conv + SiLU；保留最后 3 列 |
| `gdn_g` | [T,48] | FP32 | exp(g)；g≤0 |
| `gdn_beta` | [T,48] | FP32 | beta∈[0,1] |
| `final_hidden` | [T,5120] | BF16 | MTP 使用；是 final norm 之后的目标 |

GDN Q/K/V 顺序及宽度分别为 2048/2048/6144。Q/K 16 heads×128，V48 heads×128。GDN 的 Q 旧前缀 readout 可省，但 future convolution 仍依赖 Q 的三列历史。[S06][S08]

Teacher dump 必须从真实数值边界取值。若当前 fused projection 没有暴露 pre-conv 张量，增加**仅导出工具启用**的 tap，或增加经原 Op parity 验证的 instrumented epilogue；不允许用另一个精度不同的投影临时重算后冒称 Teacher 原值。生产路径没有 tap 开销。

## 4. StateOnly GDN

建议新增 `include/ninfer/ops/gated_delta_net_state_only.h`：

```cpp
std::size_t gated_delta_net_state_only_workspace_capacity_bytes(
    std::int32_t qk_heads, std::int32_t value_heads,
    bool normalize_k, std::int32_t min_tokens,
    std::int32_t max_tokens);

void gated_delta_net_state_only(
    const Tensor& k, const Tensor& v,
    const Tensor& g, const Tensor& beta,
    bool normalize_k, WorkspaceArena& workspace,
    const Tensor& initial_state, Tensor& final_state,
    cudaStream_t stream);
```

k BF16 `[128,Hqk,T]`；v BF16 `[128,Hv,T]`；g/beta FP32 `[Hv,T]`；state FP32 `[128,128,Hv]`。`T>=1`；Hv/Hqk 为正整数。state 输入/输出可完全别名或完全分离，部分 overlap 非法；其他张量互不重叠。不含 Q，因此没有 output scale 参数。scratch 由 capacity 函数完整声明，不在热路径 cudaMalloc。

数学 oracle 从 represented raw K/V/g/beta 与 FP32 初始 state 升为 FP64：

```python
for t in range(T):
    k = raw_k[t] / sqrt(sum(raw_k[t] ** 2) + 1e-6)
    alpha = exp(g[t])
    decayed = alpha * state
    delta = beta[t] * (v[t] - decayed @ k)
    state = decayed + outer(delta, k)
```

每个 value head 映射 QK head `floor(h/(Hv/Hqk))`。`normalize_k=false` 时不执行 normalization。oracle 不模仿 CUDA reduction、staging 或 Tensor Core tile；native baseline 与新 Op 都对同一 oracle 比较。

短 T strict-recurrence oracle、large-T mathematical oracle、native chunked represented-state comparison 是三个不同检查，不合并成“bitwise PASS”。

## 5. 完整状态清单

| 状态 | Teacher 注入 | Predictor 路径 | 检查 |
|---|---|---|---|
| 所有 full-attention layer KV | 同 codec encoded payload 或明确重编码 | 预测 K/V，经原 codec 编码 | 页归属、token数、位置、tail不越界 |
| GDN recurrent | FP32 bit-preserving | StateOnly 生成 | 每层/head，NaN/Inf，维度与 frontier |
| GDN conv history | BF16 `[10240,3]` | 从预测 pre-conv 流更新 | oldest→newest；T<3 时含旧 history |
| 早期层状态 | 正常 prefill | 正常 early prefill | 不重复推进 tail |
| final hidden | 最终 token 的真实 hidden | 非空 tail 真正计算 | 不能把 h_split 当 final hidden |
| MTP prefix KV | P5 Teacher 扩展 | predicted final hidden + 真实 stem/KV | t/t+1 对齐、末列首生成 token |
| MTP pending/hidden/drafts | P5完整state清单 | 原调度准备 | 拒绝缺失 segment |
| turn checkpoint | 原生合法边界 | 和来源标记一起保存 | 回到该点时 KV/GDN/MTP同步 |
| prefix identity / frontend | 正常准备 | 原样保存 | token、type、position、media ledger |
| sampling/RNG/frontier | 原计划 | 原计划 | 绝对token位置，不提前消费随机数 |
| provenance | Native | Approximate | 直到清空/可信native重算前不得变更 |

P1 no-spec 必须拒绝意外带入 MTP segment；P5 使用扩展完整清单再次执行 Teacher 注入实验。

## 6. Teacher 文件与 Predictor 制品

Teacher 数据为离线研究文件，不是 `.ninfer` 产品制品：目录 manifest + 按层 memory-mapped shards + SHA-256。记录 dtype/shape/layout/token范围、split、base SHA、compute profile、chunk、来源repo/session、数据split。禁用 pickle；拒绝路径穿越、长度溢出和不完整 shard。owner-only。

Predictor 发布仍复用 `.ninfer` 容器，不增加第二种产品加载器。新 kind `late-state-predictor/v1`，由 27B 私有 binder 绑定。至少包含 base SHA、split、rank、层列表、shape、tensor dtypes、gate变换、final-hidden开关、训练数据manifest SHA、synthesis version。它不是新增 base model identity。

旧 base 制品只读、不重新打包。Predictor SHA 与 base SHA 双重纳入兼容性。错误 Predictor 在模型启动/请求 admission前失败，不在计算到半途时发现。

## 7. Cache 与来源标记

复用现有 opaque compatibility key 机制。新增 approximate provenance 必须同时进 resident lane、turn checkpoint、导出 image 和 stable/session alias 的兼容域。修改 image framing 时提升版本，使用全新实验 namespace，不覆盖用户既有 cache root；旧版读取新格式安全 miss。

v1 approximate 图像不与 native 图像共享 aliases；一个 prompt_cache_key 不是复用授权。same token + different predictor / split / tail / profile 必须 miss。恢复后仍是 Approximate，即使它之后有十万 token 的正常 decode。

## 8. 新启动参数与指标

待 P4/P5 实现：

```text
--late-state-prefill off|auto       default off
--late-state-predictor PATH         required only for auto
--late-state-split 48|40|32         must match artifact
--late-state-tail N                 default 2048; N>=1
--late-state-min-uncached N          default 32768
--late-state-qualified-context N    default 200000
```

新 runtime stats 使用独立前缀：`late_state_predicted_tokens`、`late_state_early_seconds`、`late_state_predictor_seconds`、`late_state_state_build_seconds`、`late_state_tail_seconds`、`late_state_mtp_prepare_seconds`、`late_state_fallback_count`、`late_state_origin`。不得伪造 `computed_prefill_tokens` 把部分层计算当成完整 native 计算；另外报告 raw input tokens / total prefill seconds。

用户可见 OpenAI/Anthropic 字段保持兼容；来源通过本地日志和可选扩展元数据暴露，不改写正文、不泄露隐藏态。新增日志字段同步 schema tests 与文档。
