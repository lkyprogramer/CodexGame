# 05｜代码修改地图与接口契约

## 5.1 原文件与责任

| 文件（均相对原仓） | 修改范围 |
|---|---|
| `src/targets/qwen3_8/impl/frontend/tokenizer.h/.cpp` | 新增trace输出、显式work计数、复用同一个旧语义scanner；不先改BPE算法。 |
| `src/targets/qwen3_8/impl/frontend/processor.h/.cpp` | 新边界resolver接入`encode_rendered_chat`；原公共结果/错误规则不变。 |
| `src/targets/qwen3_8/impl/frontend/frontend.cpp` | text-only模式选择、缓存owner、完整metadata重建、统计向PreparedPrompt传递。 |
| `src/targets/qwen3_8/export/ninfer/targets/qwen3_8/frontend.h` | 工厂可选配置参数、诊断读取；更新friend签名及全部callsite。 |
| `src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h` | 扩展PrepareStats，不改现有identity含义。 |
| `include/ninfer/types.h` | 如采用Engine启动配置，新增typed FrontendTokenizationOptions与只读诊断结构。 |
| `src/serve/serve_options.h/.cpp` | 解析拟新增CLI选项，严格枚举/范围校验。 |
| `src/serve/generation_service.h/.cpp` | EngineOptions贯通、从prepared取得诊断、保持计时边界。 |
| `src/serve/request_log.h/.cpp` | 保留schema19/20已存在字段，增加版本化嵌套诊断。 |
| `src/targets/qwen3_8/CMakeLists.txt` | 新frontend文件加入ninfer_engine。 |
| `tests/CMakeLists.txt` | 注册新增测试与bench，保持原skip语义。 |

后端工厂callsite不能凭新上游路径猜测。T00执行并存档：

```bash
git grep -n 'make_frontend(' 44a2c6c3392c9d51e76a895ed97bf1867530d252 -- src include tests
git grep -n 'prepare_seconds\|timings_seconds' 44a2c6c3392c9d51e76a895ed97bf1867530d252 -- src/serve
git grep -n 'NINFER_REQUEST_LOG\|kRequestLogSchema' 44a2c6c3392c9d51e76a895ed97bf1867530d252 -- src tests apps
```

工厂贯通如涉及runtime model loading，只传不可变frontend选项，不改变其设备执行。不存在的符号/路径必须在审计记录说明，不得虚构。

## 5.2 拟新增内部文件

`frontend/encoding_trace.h`：03中的纯数据结构。
`frontend/boundary_resolver.h/.cpp`：ByteBoundaryQuery到token frontier的精确映射。
`frontend/token_prefix_cache.h/.cpp`：有界不可变snapshot/LCP+guard选择/入库。

不建立通用插件、model router或第二套Tokenizer实现框架。需要复用的旧BPE子过程保持单一实现；独立oracle来自baseline binary，避免通过复制生产算法形成永久双维护。

## 5.3 规范化接口（均拟新增）

```cpp
// Namespace: ninfer::targets::qwen3_8::frontend_internal
struct EncodeWork {
    std::uint64_t full_encode_calls = 0;
    std::uint64_t main_input_bytes = 0;
    std::uint64_t local_prefix_input_bytes = 0;
    std::uint64_t ordinary_bpe_input_bytes = 0;
    std::uint64_t boundary_queries = 0;
    std::uint64_t unique_boundary_offsets = 0;
    std::uint64_t added_token_search_calls = 0;
};
// Add to Tokenizer; retain existing encode behavior.
EncodeTrace encode_traced(std::string_view text, EncodeOptions options,
                          EncodeWork* work) const;

struct PrefixResolution {
    std::size_t token_count;
    bool exact;
};
PrefixResolution resolve_prefix(const Tokenizer& tokenizer,
                                std::string_view full_text,
                                const EncodeTrace& trace,
                                std::size_t byte_offset,
                                EncodeWork* work);
```

`resolve_prefix`只负责独立前缀编码与完整T的相等性；业务name、allow_full、空值和hint顺序在processor中按旧顺序检查。资源错误与非法UTF8从原encode产生；processor保留旧包装。不得以无效类型默默返回0。

缓存API返回owning snapshot引用及cut，不返回悬空string_view；候选字节证明失败返回miss而不是错误prompt。具体snapshot类定义遵守04，cache不可读取GPU状态。

## 5.4 模式与工厂贯通

typed enum `FrontendTokenizationMode { Legacy, SinglePass, Incremental, Shadow }`；shadow candidate另一个只含SinglePass/Incremental的enum。建议通过EngineOptions下的FrontendTokenizationOptions传入make_frontend，默认值明确。

原Frontend工厂还有vision_enabled、vision_max_tokens、prefix_checkpoint_policy；扩展时使用末尾defaulted typed options，保持现有调用可编译，更新friend签名。`FrontendTestAccess::create_component`同样接收可选配置，以便CPU单元测试。不向用户HTTP body新增必须字段。

## 5.5 三种前端入口

- `prepare(PromptInput)`：text走候选；media维持legacy。所有模式保留原PromptIdentity与starts_in_reasoning。
- `count_tokens(PromptInput)`：首期保留旧token计数路径，不发布snapshot；不能当带hint完整prepare结果。T09必须验证计数一致。
- `prepare_tokens(vector<TokenId>)`：不经过BPE，不进入cross-request文本cache；其allow_prefix_identity不变。

## 5.6 测试/bench target（拟新增）

`ninfer_qwen3_8_tokenizer_trace_test`
`ninfer_qwen3_8_boundary_resolver_test`
`ninfer_qwen3_8_token_prefix_cache_test`
`ninfer_qwen3_8_frontend_equivalence_test`
`ninfer_qwen3_8_frontend_bench`

现有回归target已在[S10]确认：`ninfer_qwen3_8_frontend_test`、`ninfer_qwen3_8_runtime_mechanisms_test`、`ninfer_qwen3_8_27b_prefix_real_test`及serve/schema/request_log等测试。新增target必须通过`ctest -N`实际出现，不能只创建源文件。

## 5.7 基准程序输入输出合同

拟新增bench仅作测试工具，不是产品第二推理API：

```text
--resources-dir DIR     六份原制品frontend资源
--cases FILE            data/adversarial_cases.jsonl或已冻结replay
--mode legacy|single-pass|incremental
--output FILE           规范化逐条JSONL
--oracle-dir DIR        baseline生成的goldens（candidate阶段读取）
--seed N                合成样本确定性种子
```

需要真实artifact资源时，复用[S15]的六对象绑定/读取逻辑，或从用户已验证的资源目录读取并和artifact指纹对应。不得下载HF main替代旧制品资源；测试资源提取工具不得把整17GiB权重物化到GPU。文件提取只读，记录六文件hash，资源本身不放进公开报告。
