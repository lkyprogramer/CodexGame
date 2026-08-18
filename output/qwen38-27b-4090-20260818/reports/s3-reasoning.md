# S3 Reasoning 控制

任务：同一套可执行题 `top_k`（禁止原地 sort）和 `clamp_sum`（None / 空 / lo>hi）。通过标准是抽出 `code` 后在本机 `exec` + 隐藏断言。

| profile | 服务预算 | topk | clamp | 思考 token（约） | 墙钟 |
|---|---:|---|---|---|---|
| medium | 16384 | PASS | PASS | 160 / 528 | 2.7s / 7.9s |
| low | 16384 | PASS | PASS | 383 / 198 | 5.4s / 3.7s |
| xhigh | 16384 | PASS | PASS | 254 / 906 | 4.3s / 12.9s |
| thinking off | 16384 | PASS | PASS | 0 / 0 | 1.0s / 1.2s |
| medium | 4096 | PASS | PASS | 248 / 755 | 3.6s / 11.2s |
| medium | 32768 | PASS | PASS | 207 / 1019 | 3.3s / 14.7s |

观察：

- 在这类短编码题上，**medium 已经够用**。xhigh 只在 clamp 上想得更久，没有更高通过率。
- low 并不稳定更短（topk 383 > medium 160），与 Petko 的观察一致。
- 关思考最快，这两题也过了；不能外推到长程 agent。S1 的 16k 切断才是 xhigh 失控场景。
- 4096 vs 16384 vs 32768：短题吃不满 16k，三档质量无差异。保留 **16384** 作为长任务保险，S1 已证明切断后仍有正文。

默认维持：`reasoning_effort=medium` + `--reasoning-budget 16384`。
