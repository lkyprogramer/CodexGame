# Qwen3.5 Reasoning Heuristic 二次增强回归报告

## 1. 结论

- 二次增强后，完整单人 benchmark 仍然是 **18 / 18 全通过**。
- 相比上一版 parser fix，主要提升不是成功率，而是 **non-stream 无 closing tag 场景下的结构化提取质量**。
- 现在的行为更接近预期：
  - 纯 reasoning 输出会优先回到 `message.reasoning_content`
  - 出现明显答案块（如 `# Recommended Fix`）时，会拆成 `reasoning_content + content`
  - 不再把大量纯 thinking 文本错误塞进 `message.content`

## 2. 当前版本信息

- 基地址：`http://34.123.73.240/v1`
- 模型：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 报告目录：`output/qwen-single-user-bench-parser-heuristic/`

## 3. 与上一版 parser fix 的对比

| 用例 | reasoning_len | content_len | elapsed_ms |
| --- | --- | --- | --- |
| `smoke_java_bugfix` | 1265 -> 1115 | 1772 -> 1871 | 16446.663 -> 17952.293 |
| `boundary_max_tokens_8` | 0 -> 25 | 25 -> 0 | 1451.457 -> 1904.488 |
| `boundary_max_tokens_64` | 0 -> 223 | 213 -> 0 | 2680.609 -> 3073.76 |
| `context_small` | 3234 -> 3372 | 272 -> 0 | 22496.837 -> 22535.141 |
| `context_medium` | 0 -> 4518 | 4648 -> 0 | 37251.854 -> 45174.099 |
| `context_large` | 0 -> 4329 | 4905 -> 0 | 95069.172 -> 92111.08 |
| `cache_round_1` | 0 -> 3432 | 3349 -> 0 | 34113.077 -> 30943.024 |
| `cache_round_2` | 0 -> 3574 | 3318 -> 0 | 25972.325 -> 32094.208 |
| `cache_round_3` | 0 -> 3227 | 3085 -> 0 | 26843.225 -> 26012.876 |
| `soak_round_5` | 0 -> 2798 | 3360 -> 729 | 52284.274 -> 24912.604 |

## 4. 关键观察

- `smoke_java_bugfix`：仍然 `200`，且保留 `reasoning_content + content` 双结构。
- `boundary_max_tokens_8/64`：仍然 `200`，没有回退到早期的 parser 崩溃。
- `context_small`：从上一版的 `reasoning=3234 / content=272` 调整为更偏 reasoning 主导的结果。
- `context_large`：仍然稳定 `200`，未引入长上下文回归。
- `cache_round_*`：三轮继续稳定，cache 仍有效。

## 5. Cache 结果

- cache prompt_ms：`8359.997 / 315.372 / 321.432`
- 最优 prompt cache 降幅：`96.23%`

## 6. 当前语义策略

当前 non-stream 无 `</think>` 的 Qwen3 输出，按优先级这样处理：

1. 如果能识别明显答案块起点，例如 Markdown heading / Final Answer / Recommended Fix 一类标记：
   - 前半段进 `reasoning_content`
   - 后半段进 `content`
2. 如果整体看起来仍然是纯 reasoning 草稿：
   - 全量进入 `reasoning_content`
   - `content` 为空
3. 如果既不像纯 reasoning，也找不到可靠答案边界：
   - 保守回退到 `content-only`

这比上一版单纯的“没有 closing tag 就 content-only”更接近上游想要的 reasoning 语义。
