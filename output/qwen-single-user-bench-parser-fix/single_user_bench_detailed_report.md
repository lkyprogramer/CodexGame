# Qwen3.5 Reasoning Parser 修复回归报告

## 1. 范围

- 目标模型：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 网关地址：`http://34.123.73.240/v1`
- 当前服务：`thinking=true`，已移除 `--reasoning-format none`
- 本轮压测目录：`output/qwen-single-user-bench-parser-fix/`

## 2. 直接结论

- 这次源码修复后，单人压测 **18 / 18 全部成功**。
- 之前原始 reasoning 版本只有 **6 / 18** 成功；`--reasoning-format none` workaround 是 **18 / 18**。
- 现在达到的状态是：
  - 保留 thinking mode
  - 简单请求重新恢复 `message.reasoning_content`
  - 真实 coding non-stream 请求不再出现 `500 Failed to parse input at pos ...`
  - streaming 请求继续稳定

## 3. 成功率对比

| 版本 | 成功数 | 总数 | 成功率 |
| --- | ---: | ---: | ---: |
| 原始 reasoning 版本 | 6 | 18 | 33.3% |
| workaround (`reasoning-format none`) | 18 | 18 | 100.0% |
| 本次 parser 修复版 | 18 | 18 | 100.0% |

## 4. 关键变化

- `smoke_java_bugfix`：原始 reasoning 版本会失败，本次修复后 `200`。
- `boundary_max_tokens_8` / `64`：本次都返回 `200`，没有再触发解析崩溃。
- `context_small` / `context_large`：分别在 `5230` 和 `64929` prompt tokens 下稳定返回 `200`。
- `cache_round_1..3`：全部成功，且 prompt cache 继续生效。
- `soak_round_1..5`：全部成功，单人顺序使用没有出现 parser 级异常。

## 5. 长上下文结果

| 用例 | prompt_tokens | elapsed_ms | predicted_per_second | reasoning_len | content_len |
| --- | ---: | ---: | ---: | ---: | ---: |
| `context_small` | 5230 | 22496.84 | 42.00274330417206 | 3234 | 272 |
| `context_medium` | 19728 | 37251.85 | 40.152157856953856 | 0 | 4648 |
| `context_large` | 64929 | 95069.17 | 35.394341702919945 | 0 | 4905 |

## 6. Cache 与单人连续使用

- cache 三轮总耗时：`34113.08 / 25972.33 / 26843.22 ms`
- cache prompt_ms：`8333.878 / 317.82 / 318.995 ms`
- prompt cache 最优下降比例：`96.19%`
- soak 五轮全部成功，最长单次耗时：`52284.27 ms`

## 7. 行为语义

- 对 **存在可靠 `</think>` 分界** 的响应：继续返回 `message.reasoning_content`。
- 对 **没有可靠 closing tag 的真实 coding thinking 输出**：不再报 `500`，而是保守降级到 `message.content`。
- 对 **streaming**：保持现有 reasoning delta 行为，不再因为最终闭合失败把请求打成 500。

## 8. 当前线上判断

这版已经达到比 `reasoning-format none` 更好的线上状态：

- 稳定性与 workaround 一样，都是 `18 / 18`
- 但语义更完整，简单请求重新有 `reasoning_content`
- 对 Precise coding tasks，真实 non-stream 请求已经从 500 恢复到 200

仍然需要保守说明的一点：

- 对没有 closing tag 的长 reasoning 输出，non-stream 最终会落到 `content-only`，而不是强行猜测 `reasoning_content` 边界。
- 这是本次修复的刻意策略，优先保证稳定和不 500。
