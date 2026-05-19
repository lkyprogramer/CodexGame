# Qwen3.6 27B 4090 极限推理测试总报告

## 结论

本轮完成 4 条 lane 的性能和质量闭环测试，并已恢复原 systemd 服务 `/etc/systemd/system/qwen35-35b-a3b-uncensored.service`。最终推荐分两条线继续：

1. 极限吞吐线：优先 `mtp_udq4xl_spec3`，平均生成吞吐 48.92 tok/s，中位 50.87 tok/s，是本轮最快方案。
2. 综合质量线：优先 `luce_pflash_auto_keep005`，平均生成吞吐 38.51 tok/s，格式最干净，32K 长上下文通过 PFlash 压缩后稳定命中。

DFlash 标准 lane 因 32K NIAH HTTP 500 暂不建议继续作为长上下文主方案；mainline Q4_K_M 保留为基线。

## 汇总表

| Lane | 成功率 | Avg tok/s | Median tok/s | Avg latency | 长上下文 | 人工质量分 | 结论 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| mainline_q4km_reasoning_off | 6/6 | 35.32 | 41.08 | 4.49s | pass | 3.33/5 | 基线，非极限候选 |
| mtp_udq4xl_spec3 | 6/6 | 48.92 | 50.87 | 4.94s | pass | 3.33/5 | 最强吞吐候选 |
| luce_dflash_budget26_tq3 | 5/6 | 25.28 | 21.23 | 4.80s | fail | 3.67/5 | 短上下文对照，不适合长上下文 |
| luce_pflash_auto_keep005 | 6/6 | 38.51 | 35.27 | 4.04s | pass | 4.33/5 | 最强综合质量候选 |

## 关键发现

- MTP 的性能收益明确：相对 mainline 平均生成吞吐提升约 38.5%，日志中 draft acceptance 多次达到 0.95-1.00。
- llama.cpp OpenAI 输出仍有空 `<think>` 包裹，即使启动参数使用了 `-rea off --reasoning-format none`；这会破坏 JSON-only 和 exact-match 测试。
- Lucebox DFlash/PFlash 输出格式更干净，质量评分明显更高。
- PFlash 对 32K NIAH 的压缩链路有效：日志显示 `31235 -> 1507 tokens`，压缩耗时约 1.20s，最终精确命中 needle。
- 标准 DFlash 未压缩长上下文路径失败：`niah_1200_words` 返回 HTTP 500，需要先修服务端长上下文稳定性。

## 下一轮建议

1. MTP 极限矩阵：测试 `--spec-draft-n-max 1/2/3/4`，每档至少覆盖 128/512/2048 输出长度，并增加 3 次重复取 p50/p95。
2. MTP 格式修正：定位 `<think>` 来源，优先测试 tokenizer chat template / server reasoning 参数 / stop sequence 后处理三种方案；修正前不要把 JSON-only 得分当成真实模型能力。
3. PFlash 质量矩阵：测试 keep ratio `0.03/0.05/0.08/0.10`，加入多 needle、摘要、事实问答、代码检索四类长上下文任务。
4. DFlash 稳定性修复：复现并修 32K no-compression HTTP 500，修复前只作为短上下文 lane。
5. 测试脚本增强：记录 finish_reason、TTFT、prompt eval tok/s、decode tok/s、显存峰值和完整 completion，避免 max token 截断污染质量评分。

## 记录位置

- Raw：`output/qwen36-4090-extreme-20260513/raw/`
- Logs：`output/qwen36-4090-extreme-20260513/logs/`
- Reports：`output/qwen36-4090-extreme-20260513/reports/`
- 测试脚本：`scripts/qwen4090_openai_eval.py`

## 恢复状态

- 实验进程：已按 PID 停止。
- systemd：`qwen35-35b-a3b-uncensored.service` 已恢复为 `active`。
- 端口：`http://127.0.0.1:18343/v1/models` 已返回原模型 `hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`。
- GPU：恢复后显存约 `21870 MiB used / 2347 MiB free`。
