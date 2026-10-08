# 01｜锁定源码审计：这次必须纠正的实施假设

## 1.1 真实调用链

固定 family 路径是 `src/targets/qwen3_8/impl/frontend/`，不是后续上游的 `src/models/qwen3_5/frontend/`。

```text
GenerationService::prepare
  -> Engine::prepare
    -> Frontend::prepare
      -> convert_messages
      -> CompiledChatTemplate::render
      -> encode_rendered_chat
          -> Tokenizer::encode(full rendered.text)
          -> encode_boundary(stable prefix)
          -> encode_boundary(turn rewrite)
          -> encode_boundary(user turn)
          -> for each checkpoint_hint: encode_boundary(prefix)
      -> assign_text_positions / identity
  -> Engine::submit
    -> existing GPU prefix selection / append / prefill / decode
```

Frontend::prepare 的 text-only 分支及 count_tokens 在 [S07](13_SOURCE_REFERENCES.md)。`count_tokens` text-only 是 `tokenizer.encode(rendered.text)`，没有 `encode_rendered_chat` 的所有 hint 验证，这是一个可用于诊断放大量的对照，但不能把它当成完整 prepare 的替代实现。

## 1.2 已确认的重复工作

[S01](13_SOURCE_REFERENCES.md) 中的核心逻辑：先执行 `encoded.input_ids = tokenizer.encode(rendered.text)`；再针对每个字节边界调用 `tokenizer.encode(rendered.text.substr(0, byte_offset))`，比较其是否为整段 token 前缀。

设整段原始字节长度 B，边界数 H，第i个边界为 b_i。仅 tokenizer 调用输入字节总量就是：

`B_requested = B + sum(b_i)`

若 H 与工具回合数共同增长、b_i大致铺在历史内，放大量可接近 `1+H/2`。当 B 也随回合数增长时，总工作随会话增长可能表现为近二次，而不是固定“3000 tokens/s”。这只分析调用输入规模，不假设 BPE 本身线性。

[S06](13_SOURCE_REFERENCES.md) 证明 hints 不是固定三个：assistant opener 在最后真实user后，遇到完成的tool history会持续加入 Rolling hint；最终generation opener也可能加入。StablePrefix还同时经专门字段和hint被验证，因此重复offset也存在优化空间。

**首先要消除的是重做整个历史，而不是丢弃检查点。**

## 1.3 本提交 tokenizer 的实际算法

[S04](13_SOURCE_REFERENCES.md) 的 BPE 对每个预切分词使用 `vector<string>`；每轮扫描全部相邻符号寻找最小merge rank，然后字符串拼接、vector erase。它不是后续上游的 `priority_queue<BpeCandidate>` 实现。长词/特殊字符可能放大常数和最坏复杂度，需另测，不能混在首个修复中。

[S03/S05](13_SOURCE_REFERENCES.md)：added_tokens最终按token ID升序；每次查找所有added token的最早出现位置，相同位置保留先遍历项，即较小ID。**不是最长匹配。** `single_word/lstrip/rstrip/normalized` 只允许false。普通片段独立执行NFC，然后Qwen预切分/BPE。首期必须保持这些确切行为。

## 1.4 前述方案需要明确修订

| 前述假设 | 本提交事实与纠正 |
|---|---|
| 已有 `encode_with_boundaries/exact_frontier/stable_frontier` | 不存在；Tokenizer header仅encode/decode。[S02] 新trace/边界接口需要本项目实现。 |
| 每请求只执行一次完整BPE | 实际主编码加多次前缀编码。[S01] 一次tokenize区域不是一次BPE调用。 |
| 先判断 `reusePath==APPEND_FRONTIER` 再tokenize | 循环依赖。GPU路径在tokenize完成后选出。前端只能独立验证bytes/资源/切点，GPU仍复核。 |
| 当前exact token切点可用于任意未来追加 | 不成立。`encode(A)`碰巧等于当前前缀，不保证`encode(A+B)`拼接稳定。 |
| 前端与GPU frontier必须相同 | 不必要。前端缓存可能只到上次输入，GPU还持有生成输出；两者可不同，最终PreparedPrompt必须相同。 |
| 现网schema20属于44a2c6c | 基线schema19，本地overlay必须单独取证。 |
| 只做跨请求cache，单次编码暂不动 | 会留下冷启动/回退时H次前缀重算，还可能在cache命中后照样重做边界编码。先单请求修复。 |

## 1.5 审阅范围与未审阅内容

本包逐段核对了source-lock中的前端关键文件、公开PreparedPrompt、测试注册与构建条件。没有取得prepare-detail本地diff，没有在4090运行，也未对191KB的runtime/program_impl.h做无关全面审计。任务只新增前端行为，不以未审阅的GPU内部作为正确性假设。

线上report说明tokenize耗时，但不能只凭汇总认定其中99.9%就是主BPE循环。新增 `main_encode_bytes`、`boundary_encode_bytes`、`boundary_calls` 和普通片段BPE字节计数，区分“编码器慢”与“被重复调用”。
