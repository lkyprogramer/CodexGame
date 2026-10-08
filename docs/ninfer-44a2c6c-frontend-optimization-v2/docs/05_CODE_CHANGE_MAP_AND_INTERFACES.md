# 05 · 产品文件映射与接口合同

## 5.1 允许修改/新增范围

以下路径以目标仓库为根，而不是本包为根。`新增`表示待执行者创建，不声称当前源码已有该接口或target。

| 路径 | 状态 | 职责与限制 |
|---|---|---|
| `src/targets/qwen3_8/impl/frontend/tokenizer.h` |修改|只读首字节桶、trace/work内部类型及方法；保留encode旧签名 |
| `src/targets/qwen3_8/impl/frontend/tokenizer.cpp` |修改|B0及共享encode_impl；不改普通NFC/BPE/decode/资源校验 |
| `src/targets/qwen3_8/impl/frontend/processor.cpp` |修改|B1本地resolver；三个optional、hint/error合同保留 |
| `src/targets/qwen3_8/impl/frontend/processor.h` |按需要修改|EncodedChat携带request-local统计，不改变语义字段 |
| `src/targets/qwen3_8/impl/frontend/frontend.cpp` |按需要修改|将本次统计汇入实际prepare-detail，不为count/vision加分叉 |
| `src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h` |按overlay需要|统计传播；原PromptIdentity含义不变 |
| `src/serve/request_log.cpp` 与实际overlay已改文件 |按需要修改|仅新增计数序列化/来源标签，不更改计时边界 |
| `tests/targets/qwen3_8/test_frontend.cpp` |修改|原fixture与接线回归 |
| `tests/targets/qwen3_8/test_tokenization_equivalence.cpp` |新增|产品scanner/trace/resolver的差分入口 |
| `tests/targets/qwen3_8/reference/legacy_tokenizer.cpp` |新增|从pin独立保存旧编码实现或独立库，不调用新selector |
| `tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp` |新增|完整复制旧边界合同，包含uint32与错误顺序 |
| `tests/targets/qwen3_8/bench_frontend_tokenization.cpp` |新增|CPU-only、资源路径、固定输入、严格JSONL输出 |
| `tests/CMakeLists.txt` |修改|新增两测试/基准target，按原链接风格注册 |

不改CUDA路径、runtime/generation、continuation_cache、chat_template生成规则、权重转换器、现网启动参数；源码注释或文档纠错可单独提交，不与语义修改混淆。

## 5.2 拟新增接口（本期实现合同）

namespace为固定版本的`ninfer::targets::qwen3_8::frontend_internal`。

```cpp
struct EncodingRestart {
    std::size_t byte_end = 0;
    std::size_t token_end = 0;
};
struct TokenizerWork {
    std::uint64_t scan_positions = 0;
    std::uint64_t candidate_checks = 0;
    std::uint64_t selected_added_tokens = 0;
    std::uint64_t ordinary_segments = 0;
    std::uint64_t ordinary_input_bytes = 0;
};
struct TracedEncoding {
    std::vector<int> token_ids;
    std::vector<EncodingRestart> restarts;
};
// Existing signature is retained.
std::vector<int> Tokenizer::encode(std::string_view text,
                                  EncodeOptions options) const;
// New internal method; normal callers need not allocate a trace.
TracedEncoding Tokenizer::encode_traced(std::string_view text,
                                       EncodeOptions options,
                                       TokenizerWork* work) const;
```

Tokenizer内部增加：

```cpp
std::array<std::vector<std::size_t>, 256> added_token_indices_;
std::vector<int> encode_impl(std::string_view text, EncodeOptions options,
                            std::vector<EncodingRestart>* trace,
                            TokenizerWork* work) const;
```

`work`按调用累加，由调用者初始化清零；不存指针到Tokenizer里。encode_traced把trace起点置为0，调用同一encode_impl；`encode`传nullptr。产品只有一种scanner。旧oracle单独target通过不同namespace/符号实现，不能改名后仍链接新内部函数。

## 5.3 B1 内部合同

`encode_rendered_chat`公开内部签名保持不变；需要观测时可在EncodedChat增加一个不影响identity的work字段。

```cpp
struct BoundaryEncodingWork {
    std::uint64_t main_encode_calls = 0;
    std::uint64_t main_input_bytes = 0;
    std::uint64_t checkpoint_hints = 0;
    std::uint64_t boundary_queries = 0;
    std::uint64_t boundary_unique_offsets = 0;
    std::uint64_t local_encode_calls = 0;
    std::uint64_t local_input_bytes = 0;
    std::uint64_t local_max_bytes = 0;
    std::uint64_t memo_hits = 0;
    TokenizerWork main_work;
    TokenizerWork local_work;
};
```

允许调整字段放置以适配真实overlay，但在T01冻结唯一映射。boundary_queries按旧逻辑实际访问的查询递增，包括重复；失败后后续查询不执行。unique_offset只计已到达的合法字节offset；主input只计R一次，local字节独立计，不能把“主编码一次”包装成没有任何局部encode。

## 5.4 Oracle 隔离

推荐从固定版本构建一个只含前端必要源码的独立reference可执行文件，另一可执行链接候选真实产品源。相同输入JSONL和资源directory，输出归一化semantic。也可在同一测试进程中用隔离namespace链接完整旧实现，但必须审查未共享新selector/B1resolver。

允许两侧共享未更改的unicode库/只读资源；不允许两侧共享被优化函数然后称独立。评审bench的`#include tokenizer.cpp` hack只能作为调查参考，不作为最终产品链接机制。

## 5.5 测试/基准可执行协议（待创建）

新增target名明确为：`ninfer_qwen3_8_tokenization_equivalence_test`、`ninfer_qwen3_8_tokenization_bench`。执行者必须在T02/T06/T08注册后再运行。前者支持`--resources DIR --cases JSONL --output JSONL --seed N --fuzz N`；后者支持`--resources DIR --requests JSONL --out JSONL --repetitions N --warmups N`。这些是v2设计接口，不是原仓已有CLI。bench的`--out OUT`输出严格normalized rows，同时写`OUT.work.jsonl`和`OUT.run.json`保存计数和环境，避免与additionalProperties=false的row schema冲突。

reference产物用`--reference-output`或独立`ninfer_qwen3_8_legacy_frontend_oracle`程序输出同一schema。最终使用[compare helper](../tools/compare_frontend_results.py)比较，但其PASS仍需G0证明产物来源。

## 5.6 B0-only 独立发布策略

B0提交只替换scanner并使原processor完整保留。若需要先发B0，要独立完成精确差分、短请求门和维护接线；不能以B0约10秒满足B0+B1亚秒门。默认路径仍是在同一开发分支完成B0/B1后一次发布，避免重复维护开销。
