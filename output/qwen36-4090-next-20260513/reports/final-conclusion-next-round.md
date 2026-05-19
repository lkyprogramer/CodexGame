# Qwen3.6 27B 4090 下一轮极限测试总报告

## 结论

本轮按上一版 `final-conclusion.md` 的下一轮建议完成测试，并已恢复原 systemd 服务。新的推荐策略是：

1. 吞吐极限：使用 MTP `--spec-draft-n-max=4`，本轮平均 52.26 tok/s，2048 token p50 55.63 tok/s。
2. 长上下文质量：使用 PFlash `keep_ratio=0.05` 作为默认稳妥档，`0.03` 作为极限压缩档。
3. 严格 JSON/exact-match：MTP 当前必须增加输出清洗或改 chat template；非侵入式 prompt/stop/completion endpoint 都没有解决。
4. 屏蔽项：PFlash `0.08/0.10` 和 DFlash no-compression 32K 长上下文都应暂时屏蔽。

## 汇总

| 测试项 | 最佳/结果 | 结论 |
| --- | --- | --- |
| MTP spec 矩阵 | spec=4 avg 52.26 tok/s | 当前最高吞吐 |
| MTP 格式修正 | 非侵入式方案均失败 | 需要清洗或改模板 |
| PFlash keep ratio | 0.03/0.05 质量通过 | 0.05 默认，0.03 极限 |
| PFlash 高 ratio | 0.08/0.10 BrokenPipe | 暂时屏蔽 |
| DFlash no-compression | 200 但输出 `!` | 长上下文不可用 |

## 已完成的恢复验证

- 实验进程：已停止。
- systemd：`qwen35-35b-a3b-uncensored.service` 已恢复为 `active`。
- 端口：`http://127.0.0.1:18343/v1/models` 返回原模型 `hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`。
- GPU：恢复后约 `21870 MiB used / 2347 MiB free`。

## 下一步建议

1. 对 MTP spec=4 跑并发矩阵：`-np 1/2/4`，输出长度固定 512/2048，每档 3 次重复。
2. 给 MTP 测试网关加确定性清洗：仅移除开头空 `<think>\n\n</think>\n\n`，再重跑 JSON-only 和 needle exact-match。
3. 对 PFlash `0.03/0.05` 增加真实任务：RAG 答案、跨段事实合成、代码片段定位、多 needle 顺序约束。
4. 修 PFlash `0.08/0.10` 的 daemon BrokenPipe，重点看第一次请求 `raw_tokens=1/read_eof=true` 后 daemon 是否退出。
5. 修 DFlash no-compression 的 32K EOF：先复现 `raw_first_token_ids=[0]`，再看 `build/test_dflash` 在 32K prompt 下是否主动 EOF。

## 记录位置

- Raw：`output/qwen36-4090-next-20260513/raw/`
- Logs：`output/qwen36-4090-next-20260513/logs/`
- Reports：`output/qwen36-4090-next-20260513/reports/`
- 新脚本：`scripts/qwen4090_next_round_eval.py`
