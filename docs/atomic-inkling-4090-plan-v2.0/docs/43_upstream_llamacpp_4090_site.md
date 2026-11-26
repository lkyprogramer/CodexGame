# 43 · v2.1 上游 llama.cpp 刷新与 4090 现场修订

**修订日期：2026-11-26（Asia/Shanghai）。本篇基于 GitHub/Hugging Face 一手页面和对目标 4090 的只读观察写成。没有在 4090 上构建、加载模型或停服务。所有数字都标注了来源，没有一项是本方案的 GPU 测量。**

## 1. 结论

1. **上游 mainline 已经能运行正式 Mini。** ggml-org/llama.cpp 已合并 Inkling 2（#32217）、`inkling2_loop` 版 Mini（#32694）、loop slot 修复（#32704）、tokenizer 与 parser 修复（#32799/#32381/#32833）、原生 DSpark（#32218）和 indexed-bias 图（#33053）。v2.0 把 S12 只当作 Atomic 的 DSpark 出处，没有把 mainline 当作现行实现。从本版起，mainline 是 **T02 跨引擎 oracle 的必选对照**，也是向 Atomic 回移植修复的来源。主底座仍是 Atomic，规则不变。
2. **Atomic `fb69fff` 的 CUDA 通用路径落后 mainline。** 已经静态确认，该 pin 没有包含 4 项上游修复（见 §4）。其中 #32799 改变分词，#32704 影响 loop 第 2、3 遍的逐专家 scale。在 T02 证明没有影响或回移植之前，Atomic 的输出不能当作正式 Mini 的基线。
3. **在 4090 上跑 128K 的首要障碍是 attention 的相对位置 bias，而不是权重。** 在 CUDA 后端不支持 indexed bias 时，#33053 会退回到稠密 bias mask。估算显示，prefill 的 compute buffer 随 `n_kv × ubatch × 24` 线性增长，128K、ubatch=512 时会远超 24 GB（§5）。CUDA 实现在 #33063，还没有合并。T04 改为对比“稠密回退 + 小 ubatch”和“#33063”两条路线。
4. **在 PCIe 上流式加载专家几乎没有收益空间。** 历史实测（2026-10-09）的 pinned H2D 只有约 8.1 GB/s。IQ4 级量化（14.6–16.4 GiB）加 Q8 KV 预计能全驻留，所以 T09 预期是 `SKIPPED_WITH_EVIDENCE`，Atomic 预算/streaming 的差异化价值在这台机器上可能用不上（是推断，待 T04 证实）。
5. **投机解码新增 DFlash2 候选。** `incoai/Inkling-2-Mini-DFlash2` 是另一种草稿器（block diffusion + selector）。作者在 H200 上报告的接受长度是 4.8–5.0，DSpark 是 3.5。llama.cpp 侧有两个尚未合并的实现：#33049 是用户点名的 PR，#33073 带转换器。它与旧 Strata/Qwen 的 DFlash2 no-benefit 不是同一模型和草稿器，因此满足 18 的“新模型/新机制”重开条件。但它排在 T06 DSpark 资格之后，不新增 DAG 节点。
6. **4090 必须停生产才能实验。** 现场 Strata 占用 23.3 GiB 显存和约 44.6 GiB RSS。用户已授权停启 `openclaw-qwen38-next.service`（2026-11-20 起有效，2026-11-26 针对本测试再次确认）。§9 给出带自动恢复的窗口脚本。

## 2. 4090 现场只读观察

采集时间：2026-11-26 01:53–01:56 UTC（主机时间 2026-11-25 20:53 EST）。方式是 `ssh 4090` 只读查询，没有运行 GPU 计算，也没有改动任何服务。这不是 T00 交付：T00 还需要在 GPU 空闲时跑 preflight.py，并锁定工具链。

| 项目 | 观察值 | 对计划的影响 |
|---|---|---|
| GPU | RTX 4090，UUID `GPU-381cb85f-8ebf-b33e-5076-9305e6af4be5`，总显存 24564 MiB，persistence on，power limit 450 W，Disp.A Off | 起始预算用 24564 MiB 减去实测 reserve，不用标称的“24 GB” |
| GPU 占用 | Strata 引擎（`strata-0.2.17`）占用 23334 MiB；空闲时 P8 | 实验必须停生产，不能与生产共卡 |
| PCIe | max gen 3，链路宽度 x16（空闲时 current gen 1，属于节能） | 历史实测 pinned H2D 约 8.0–8.2 GB/s，D2H 约 8.8–9.5 GB/s，pageable H2D 约 7.7 GB/s（`~/pcie-test-20261009/`，2026-10-09） |
| Driver / CUDA | KMD 610.57.04，CUDA UMD 13.3；Toolkit 只有 `/usr/local/cuda-12.3`（nvcc 12.3.107） | 用 nvcc 12.3 编 sm_89。不能把 UMD 13.3 写成 Toolkit 版本，也不升级驱动 |
| 编译链 | gcc 12.2.0，cmake 3.25.1，Python 3.11.2，git 已装；`hf` 和 `huggingface-cli` 不在 PATH | 在实验目录建 venv 安装 huggingface_hub |
| CPU / RAM | Xeon Silver 4216，16C/32T，单路；MemTotal 62.46 GiB，无 swap；Strata 运行时约 9 GiB available | 生产在跑时不能做大编译（OOM killer 首先会选中 Strata）；host 预算还要扣掉 docker 租户（gunicorn/postgres/redis 约 1.2 GiB） |
| 磁盘 | Samsung 980 1TB NVMe，根分区 915G，已用 656G，**可用 213G**；`/data` 与 `/home` 同在根分区 | 替换 AGENTS 中“SSD 约 600 GB”的旧描述；§8 的下载集约 75 GiB，保持 ≥100 GiB 余量 |
| 网络 | huggingface.co 和 github.com 返回 200 | 可以在线获取固定 revision |
| 生产 | `openclaw-qwen38-next.service`（unit 描述仍是 v0.2.3；`run-iq3_xxs.sh` 转到 v0.2.17）；监听 127.0.0.1:18343 / 0.0.0.0:28343；`/health` 约 30 s 后 loaded | 停启和健康检查见 §9；每分钟的 strata_monitor 会自动把状态记为 down/lab |
| sudo | hhtele 只能免密执行该 unit 的 `systemctl start/stop/restart`，其他 sudo 需要密码 | 不改驱动、不 drop page cache、不改 power limit |

## 3. 上游 llama.cpp 的 Inkling 状态（截至 2026-11-26 01:57 UTC）

固定基线：**mainline `b12751` = `532d67426bb874f06a8acc6959af81b34206f7f9`**（2026-11-25 23:29 UTC）。观察时的 master 是 `9c003a97ab34a69cc49243f9b02014038205ffae`。后续升级另立 baseline，不自动 pull。

| PR | 状态（merge / head） | 内容 | 对本计划 |
|---|---|---|---|
| #32217 | 已合并 `5c008e0` | Inkling 2 文本 + 视觉基础 | mainline oracle 的前提 |
| #32694 | 已合并 `29b52d3` | 正式 Mini `inkling2_loop`：24 物理层展开为 48 个 slot | 与 Atomic 的 `layer_phys` 同构，同一个 GGUF 可以跨引擎对照（待 T00 实测加载） |
| #32704 | 已合并 `690b87d` | scale pass 之后重新共享 loop slot | unsloth 说明：缺少它时，第 2、3 遍会丢失逐专家 NVFP4 scale，PPL 约 130。Atomic pin 缺失 |
| #32799 | 已合并 `d2bceda` | Inkling 2 tokenizer `ignore_merges=true` | 改变 BPE 分词；Atomic pin 缺失 |
| #32381 / #32833 | 已合并 | chat parser 和工具 grammar | Pi 工具调用的前提；T02/T03 需要验证工具调用往返 |
| #32855 | 已合并 `396ed2c` | `mix()` 加权和的矩阵乘法方向 | 改变算子形状与求和顺序；Atomic pin 仍是旧式 |
| #32218 | 已合并 `33aeb17` | 原生 DSpark | 就是 S12；mainline 的 drafter GGUF 格式在 PR 期间变过，必须锁定文件 hash |
| #33053 | 已合并 `2d5b3dd` | 图里改用 indexed bias；后端不支持时回退到稠密 mask | 见 §5；它把 CUDA 128K 的容量问题暴露成显式路径 |
| #33063 | 未合并，head `a5e1731` | CUDA/HIP 实现带 indexed bias 的 Flash Attention | **128K 关键补丁**；用 `test-backend-ops` 在 SM89 上验证 |
| #33060 | 未合并，head `89478df` | CUDA 融合 short conv、depth mix、loop controller、L2 clip、situ | 作者在 sm_120 上报告每 token 的 kernel launch 从 5745 降到 2584，tg128 +28–31%，KLD 0.00205（求和顺序变了）；**没有 SM89 数据** |
| #32943 | 未合并，head `b68cf35` | top-k MoE 权重归一化与加性 bias 融合 | 作者在 GB10 上测得 tg 收益在噪声内；排在 #33060 之后 |
| #32773 | 未合并，head `61031e7` | DSpark 实测与自适应暂停（Vulkan，16 GB） | 提供 draft KV 与 graph rebuild 的经验，见 §7 |
| #33049 | 未合并，head `39e7ac1` | DFlash2 修复：`target_visits`、selector softcap 顺序、借用 embedding 时的 RMS norm | 用户点名的 PR；没有转换器，评审者称实现“hacky” |
| #33073 | 未合并，head `f4fd1dc` | DFlash2 Inkling 支持（含转换） | 优先作为 GGUF 生成路径，与 #33049 交叉核对 |
| #32777 / #33058 / #33072 | 未合并 | 显存受限或多卡时的 loop-aware 放置、按物理层切分、MoE cache 去重 | 只在 T09 被触发时参考；全驻留时不需要 |

## 4. Atomic `fb69fff` 与 mainline 的已确认差异

逐文件读了 Atomic pin（S01）。下表只列已确认的差异；其余 Inkling PR 没有逐项比对，T00 需要做完整的 `git merge-base` 和 cherry-pick 清单。

| 上游修复 | Atomic 观察 | 风险 | 处理 |
|---|---|---|---|
| #32799 `ignore_merges` | `src/llama-vocab.cpp` 的 `inkling2` 分支没有这一行 | 与 HF tokenizer 分词不一致，模板化 prompt 的 token ID 会漂移 | T02 先做与 HF tokenizer 的逐 token 对比；不一致时回移植这一行，作为最小 loader 修复 |
| #32704 `post_arch_tensors` | `inkling2-loop.cpp` 和 `llama-model.cpp` 都没有这个钩子 | 含逐专家 scale 的量化（尤其 NVFP4）在第 2、3 遍可能出错 | 回移植之前，Atomic 不加载 NVFP4 GGUF；其他量化先用 PPL/KLD 与 mainline 对照 |
| #32855 mix 方向 | 仍是 `ggml_mul_mat(transpose(states), scores)` | 数值等价，但 kernel 路径和求和顺序不同 | 记入 arithmetic_contract，不当作缺陷 |
| #33053 indexed bias | 图中没有 `indexed_bias`，只有稠密 `rel_pos` | 长上下文的 compute buffer 会膨胀，与 §5 相同 | Atomic 的 128K 资格依赖于回移植 #33053 + #33063 |

**底座复核记录（D-BASE）。** 不新增任务，而是在 T04 结束后写一份 DECISION：比较 Atomic 与 mainline 在同一 GGUF 上的正确性、容量和速度，以及 T09 是否 SKIPPED。如果 Atomic 在 4090 上的独有能力（离散预算、专家 streaming、Metal 路径）都用不上，而且维护成本主要是持续回移植上游，就把“改用 mainline pin 作为底座”作为选项提交给用户。改不改底座属于产品决策，执行代理不能自行切换。

## 5. 长上下文容量：稠密 bias 回退

模型事实（S02 config `c9d0283`）：24 个物理层，其中 20 个是 SWA（窗口 1024），全局层是物理 5/11/17/23。core 区间 [6,18) 执行 3 次，所以全局逻辑访问有 8 次、SWA 逻辑访问有 40 次。Q 头 24 个，KV 头 8 个，head_dim 128，相对位置参数 `d_rel=16`、`rel_extent=1024`。词表 201024（未 padding 前 200058）。路由专家 128 个，每 token 选 8 个。

- **全局 KV**（与 04 一致）：131072 上下文用 Q8_0 是 2.125 GiB，用 F16 是 4.0 GiB。SWA 的 40 次访问按约 (1024+ubatch) 个位置计算，在 0.1–0.2 GiB 量级。
- **稠密 bias mask**（S51 的 `dense_bias_mask` 路径）：每次全局 attention 都会在 F32 下物化形状为 `n_kv × ubatch × 24` 的张量，再经过 permute/cont、与 mask 相加、cast 成 F16，大约产生 2.5–4.4 份副本。这个系数来自 #33040 的观察：32K 上下文时，ub512 的 compute buffer 是 6.6 GiB，ub256 是 1.86 GiB。这是**推断**。

| 128K 时的 ubatch | 单份 F32 bias | 估算 compute buffer | 结论 |
|---:|---:|---:|---|
| 512 | 6.0 GiB | 15–26 GiB | 不可行 |
| 256 | 3.0 GiB | 7.5–13 GiB | 不可行 |
| 128 | 1.5 GiB | 3.8–6.6 GiB | 勉强，挤占权重 |
| 64 | 0.75 GiB | 1.9–3.3 GiB | 可行，但 prefill 吞吐可能大幅下降 |

接入 #33063 后，bias 只读取 `n_bins × 24 × ubatch` 的表，mask 回到普通的 `n_kv × ubatch` F16。这时 ubatch 不再受这项约束，但 FA 的 workspace 和输出 logits（`201024 × ubatch × 4 B`）仍要计入。

**128K 全驻留草案**（GiB，根据 HF 文件大小估算，不是峰值测量）：

| 权重 | 文件 | + Q8 全局 KV | + SWA/conv/输出 | + reserve 1.5 | 余量（23.99 GiB 内） |
|---|---:|---:|---:|---:|---:|
| unsloth UD-IQ4_XS | 14.65 | 2.13 | ≈0.6 | 1.5 | ≈5.1，可容纳 compute buffer 与 DSpark |
| AtomicChat AD-Q4_K | 15.39 | 2.13 | ≈0.6 | 1.5 | ≈4.4 |
| ggml-org IQ4_NL / NVFP4、UD-Q4_K_XL | 16.42 | 2.13 | ≈0.6 | 1.5 | ≈3.3 |
| AtomicChat AD-Q5_K | 17.76 | 2.13 | ≈0.6 | 1.5 | ≈2.0，偏紧 |
| Q6_K 及以上 | ≥21.8 | — | — | — | 128K 不可行 |

T04 必须用 CUDA 日志中的实际 buffer 行和 NVML 峰值替换这张表。DSpark 还要加上 draft 权重（0.47 GiB）、draft KV 和 verify workspace。

## 6. 资产修订（补充 03）

正式 Mini 的官方权重本身是 NVFP4 专家 + MXFP8 + BF16（S02 的 `quantization_config`）。所以“更高精度参考”是指与官方 checkpoint 等价或无损上转的表示，例如 Q8_0 或 BF16 GGUF，而不是比官方训练精度更高。

| 仓库 @revision | 布局 | 候选文件（GiB） | 用途 |
|---|---|---|---|
| ggml-org/Inkling-2-Mini-GGUF @`0bdc580` | mainline | IQ4_NL 16.42；NVFP4 16.42；Q8_0 25.91；BF16 48.64 | IQ4_NL/NVFP4 是质量候选；Q8_0 是 KLD 参考（需要部分 offload）；NVFP4 的转换方式未核实，SM89 走通用 MMQ 布局 |
| unsloth/Inkling-2-Mini-GGUF @`8078d14` | 根目录是 Unsloth 自有布局；**`Mainline_Support/` 是 mainline 布局**（扩展名 `.gguf_file`，下载后改名） | UD-IQ4_XS 14.65；UD-Q4_K_XL 16.42；UD-Q3_K_XL 12.70；`dspark-Inkling-2-Mini-Q8_0.gguf` 0.47 | 主力候选；mainline 需要 ≥ b12611；DSpark 文件见 #33040，大小 503,889,952 B，SHA256 `3da00cf7…` |
| AtomicChat/Inkling-2-Mini-GGUF @`3095098` | Atomic | AD-IQ2_M 8.07；AD-IQ4_XS 13.97；AD-Q4_K 15.39；AD-Q5_K 17.76；dspark Q8_0 0.47 | 只有在 mainline 布局无法被 Atomic 加载时才用作 Atomic 专用对照；IQ2_M 降为可选的冒烟测试 |
| incoai/Inkling-2-Mini-DFlash2 @`4f9088e` | safetensors（BF16，0.92 GiB） | `model.safetensors`、`config.json` | T06-DF2；需要用 #33073 的转换器生成 GGUF，并单独计算 draft_fingerprint |

GGUF 的布局和引擎版本绑在一起（unsloth 根目录与 `Mainline_Support` 的张量逐字节相同，只是 metadata 和名称不同）。因此 `asset_fingerprint` 必须包含 `gguf_layout`（`mainline_inkling2_loop` / `unsloth_loop` / `atomic`）和最低引擎版本，换布局就要新开 model epoch。

## 7. 投机解码修订（补充 07）

**原生 DSpark 的社区数据**（都不是 4090 上测的，只用来调整实验设计）：

- #33040（2× RTX 5060 Ti，CUDA，UD-Q4_K_XL，384 tokens）：AR 44.88 tok/s；`n_max=2` 52.43（+17%，接受率 0.469）；`n_max=3` 47.74。两个 prose prompt 持平或略负。
- #32773（RX 9070 XT，Vulkan，184K，q4_0 KV）：默认 f16 draft KV 会超出显存，拖慢整个 target。verify batch 大小一旦变化就触发 graph 重建，单次约 25 ms，n_max=7 因此跌到 17 tok/s。固定 n_max=4 时 code +68%，prose −20% 到 −36%。

T06 的调整：固定宽度先测 `k ∈ {1,2,3,4}`，k=7 只作上限诊断；显式设置 `-ctkd/-ctvd` 与 target KV 相同，并计入容量账；记录 graph 是否复用（可以用 `LLAMA_GRAPH_REUSE_DISABLE=1` 做诊断性 A/B，不作为生产配置）；按 code / Java / 工具 JSON / prose 分层报告。T08 的自适应 k 必须证明 graph 重建成本低于收益，否则只允许在“全宽或关闭”两个状态之间切换。

**DFlash2（T06-DF2，T06 的扩展，不新增 DAG 节点）。** 草稿器有 5 层（qwen3 型），hidden 2304，SWA 2048，block 8，selector top-k 16、rank 256，softcap 在 correction 之后，target visits 是 [5,23,41,48]。作者在 H200 + SGLang + FA4 上测得（T=1，concurrency 1）：接受长度 4.80–4.97（DSpark 是 3.47–3.66），相对 AR 提速 2.50–2.77×（DSpark 是 1.97–2.17×）。#33049 自报 code 从 51.0 提到 158.0 tok/s，硬件没有说明。

前置条件：T06 的 DSpark 已通过 G2 并有 AR 基线。#33073 的转换器生成 GGUF 后，用 #33049 的三项语义（visits、softcap 顺序、embedding RMS norm）逐项交叉检查。两个 PR 产出的 draft logits 不一致时，判 BLOCKED，不挑结果更快的那个。它必须与最佳固定 k 的 DSpark 配对比较，而不只是与 AR 比。旧的 Strata/Qwen DFlash2 结论对它既不构成阻塞，也不构成支持。

## 8. 对现有任务的增量（不改 DAG）

| 任务 | 新增要求 |
|---|---|
| T00 | 增加 mainline `b12751` 的 SM89 构建（L0），以及 L1 = L0+#33063、L2 = L1+#33060、L3 = L1+#33073 三个独立 worktree/build；锁定 §6 的文件 SHA256；生成 Atomic 与 mainline 的 Inkling 差异清单；写入 §2 的现场事实 |
| T02 | 跨引擎 oracle：同一 GGUF、同一 token ID，比较 Atomic A0 与 mainline L0 的 logits；先与 HF tokenizer 做逐 token 对比（覆盖 #32799）；PPL/KLD 由 `llama-perplexity --kl-divergence` 生成；回移植的上游修复按最小 loader/op 修复提交，每项单独 commit |
| T03 | 候选改为 NVFP4 / IQ4_NL / UD-Q4_K_XL / UD-IQ4_XS，以对 Q8_0 的 KLD 作为预筛，再跑业务集；**加入与现生产（Strata Qwen3.8-next B2-TS5）在同一 Pi/Java 集上的对照**。是否替换生产取决于这个对照，不取决于 Inkling 自身是否达标 |
| T04 | 容量阶梯加入 `ubatch ∈ {64,128,256,512}` × {稠密回退 L0, indexed bias L1}；记录每档的 CUDA buffer 日志；随后写 D-BASE 记录 |
| T06 | 按 §7 调整 k 集合、draft KV 与分层；新增 T06-DF2 |
| T07 / K | 上游优先：在 SM89 上验证 #33060/#32943 的 `test-backend-ops`、KLD 和 tg/pp 配对；融合改变了求和顺序，需要新的 `arithmetic_contract_id` 和质量复核；之后才考虑自研 kernel |
| T09 | 依据 8 GB/s 的 PCIe 实测和 §5 的预算，预期 SKIPPED_WITH_EVIDENCE；只有 T04 证明 DOES_NOT_FIT 时才启动 |

计划测试目录（148 项）和门槛不变。本节新增的检查在相应任务的 TASK 记录中登记为该任务的验收子项。

## 9. 实验窗口、生产停启与构建命令

**窗口划分**（每个窗口都会停生产；时长是估算）：

| 窗口 | 停服时长 | 内容 | 产出 |
|---|---:|---|---|
| W0 | 0 | 不停服：拉代码、下载资产并算 SHA、建 venv、准备 HF tokenizer 参考（CPU 轻量） | 锁文件草稿 |
| W1 | 约 2.5 h | 空闲 GPU 上跑 preflight；以 `-j 16` 构建 A0/L0/L1/L2；4K 冒烟；分词与 logits 跨引擎对照；在 L1/L2 上跑 `test-backend-ops`；llama-bench 跑 pp512/tg128，深度 0 和 8K | T00 / G0，T02 的探索证据 |
| W2 | 约 3 h | Q8_0 参考 logits 和候选 KLD；4K→128K 容量阶梯（L0 与 L1 × ubatch） | T03 预筛、T04 诊断、D-BASE |
| W3 | 约 3 h | DSpark k=1..4 配对；DFlash2 转换与 L3 运行 | T06 / T06-DF2 的探索证据 |
| W4+ | 视情况 | T01 工具到位后，跑 150 个 Java 任务、300 个工具案例、生产对照和 soak | 正式 gate 证据 |

W1–W3 的数字按 `evidence_kind=exploratory_gpu` 保存，用来决定方向和优先级，**不能填进 G1–G6 的 PASS**。正式资格要等 T01 的 lab 工具和预注册的 manifest。

**停启包装脚本**：任何退出路径都会恢复生产并等待 health。

~~~bash
#!/usr/bin/env bash
set -euo pipefail
UNIT=openclaw-qwen38-next.service
LAB=$HOME/inkling-lab-20261126
health_loaded() {
  curl -fsS --max-time 3 http://127.0.0.1:18343/health \
    | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("loaded") is True else 1)'
}
restore() {
  local rc=$?
  pkill -u "$(id -u)" -f "$LAB/.*/bin/llama-" || true
  sudo -n /usr/bin/systemctl start "$UNIT"
  for _ in $(seq 1 60); do
    if health_loaded; then echo "production restored (lab rc=$rc)"; return; fi
    sleep 5
  done
  echo "production NOT healthy after 300 s; inspect run-iq3xxs.out" >&2
}
curl -fsS http://127.0.0.1:18343/metrics \
  | python3 -c 'import json,sys; s=json.load(sys.stdin)["live"]["state"]; sys.exit(0 if s=="idle" else 1)'
trap restore EXIT
sudo -n /usr/bin/systemctl stop "$UNIT"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv | tee "$LAB/evidence/gpu-after-stop.csv"
"$@"
~~~

用法：`lab-window.sh <实验脚本>`。pkill 只匹配实验目录下的 llama 二进制，不碰 Strata。如果生产忙（state 不是 idle），就不进入窗口。

**固定源码与构建**（实验目录全新，不覆盖已有的 llama.cpp 树）：

~~~bash
LAB=$HOME/inkling-lab-20261126
mkdir -p "$LAB/evidence" && cd "$LAB"
git clone --no-checkout https://github.com/ggml-org/llama.cpp.git llama.cpp-mainline
git -C llama.cpp-mainline checkout --detach 532d67426bb874f06a8acc6959af81b34206f7f9
git -C llama.cpp-mainline fetch origin pull/33063/head pull/33060/head pull/33073/head pull/33049/head
git -C llama.cpp-mainline worktree add --detach ../wt-L1 532d67426bb874f06a8acc6959af81b34206f7f9
git -C wt-L1 merge --no-edit a5e173111058076bb620752397b9072c5d20c429
export PATH=/usr/local/cuda-12.3/bin:$PATH
for src in llama.cpp-mainline wt-L1; do
  cmake -S "$src" -B "$src/build-sm89" -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 -DLLAMA_BUILD_TESTS=ON -DGGML_CCACHE=OFF
  nice -n 10 cmake --build "$src/build-sm89" -j 16 --target llama-server llama-bench \
    llama-perplexity llama-tokenize llama-cli test-backend-ops
  sha256sum "$src"/build-sm89/bin/llama-server "$src"/build-sm89/bin/llama-bench
done
~~~

L2（L1 再合入 `89478df95ac525f61d9c9bdfcdf0ca76a8d2c505`）和 L3（L1 再合入 `f4fd1dce91c6d115a6ab0fb6751265cfe58e1d6b`）按同样方式建 worktree。合并冲突要记录下来，不手工改写 PR 语义。Atomic A0 按 16 §2–3 构建，构建目录同样放在 `$LAB` 下。生产在跑时只能用 `-j 3`，并且 MemAvailable 低于 3 GiB 时中止；默认把构建放在 W1。

**SM89 算子与冒烟**（W1 内）：

~~~bash
cd "$HOME/inkling-lab-20261126"
./wt-L1/build-sm89/bin/test-backend-ops -o FLASH_ATTN_EXT -b CUDA0 2>&1 | tee evidence/L1-fattn.log
./llama.cpp-mainline/build-sm89/bin/llama-bench \
  -m models/Inkling-2-Mini-UD-IQ4_XS.gguf -ngl 99 -fa 1 -ctk q8_0 -ctv q8_0 \
  -p 512 -n 128 -d 0,8192 -r 3 -o json | tee evidence/L0-bench-iq4xs.json
~~~

**下载集**（W0，约 75 GiB）：ggml-org 的 IQ4_NL 与 Q8_0；unsloth `Mainline_Support` 下的 UD-Q4_K_XL、UD-IQ4_XS 和根目录 dspark Q8_0；incoai DFlash2。都用 `hf download <repo> <file> --revision <sha>`，revision 取 §6。下载后核对 SHA256，再写入 `profiles/models.lock.json`。NVFP4 与 AtomicChat AD-* 在 T03/D-BASE 需要时再下载。

## 10. 新增风险与停止规则

- 上游 PR 没有合并，head 随时会变：只认锁定的 head SHA，换 head 就是新 candidate，旧证据不追认。
- #33060 只在 Blackwell 上测过，#33063 的 SM89 路径没有作者数据：两者都必须先通过 `test-backend-ops` 和 KLD 门，再测性能。
- 跨引擎差异无法解释（logits/分词）时，按 AGENTS 的硬停止条件处理。不能为了推进进度而改用另一个引擎的输出当 oracle。
- 生产停机：每个窗口都必须用 §9 的包装脚本。restore 失败要立即人工处理，并在 evidence 中记录停机起止时间。如果用户对停机窗口长度另有约束，以用户的为准。
- 本篇所有作者或社区数字（H200、GB10、sm_120、5060 Ti、9070 XT）都不得写入 4090 的 run 测量字段。
