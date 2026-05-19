# luce_dflash_budget26_tq3 测试报告

## 结论

该 lane 不适合作为当前 4090 极限测试主线：短/中输出可用且输出格式干净，但 32K NIAH 触发 HTTP 500，最终 5/6 成功，平均生成吞吐 25.28 tok/s，中位生成吞吐 21.23 tok/s。失败日志显示长上下文未启用 PFlash 压缩时，31250 prompt tokens 走 DFlash 标准路径，随后服务端返回 500。

## 启动配置

- 机器：4090 `192.168.10.29`
- 服务端口：`18366`
- Lucebox：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash`
- 目标模型：`/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- draft：`/data/models/qwen/dflash-draft/model.safetensors`
- tokenizer：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash/tokenizers/qwen36_27b`
- 关键参数：`DFLASH27B_KV_K=tq3_0 DFLASH27B_KV_V=tq3_0 --budget 26 --max-ctx 32768 --ctk tq3_0 --ctv tq3_0 --fa-window 2048 --daemon`

## 性能结果

| 指标 | 结果 |
| --- | ---: |
| case_count | 6 |
| ok_count | 5 |
| error_count | 1 |
| avg_tokens_per_sec | 25.28 |
| median_tokens_per_sec | 21.23 |
| avg_elapsed_s | 4.80 |
| long_context_pass | false |

失败记录：

- `niah_1200_words`：HTTP 500。
- 日志记录：`prompt_tokens=31250`，`compression_fired=false`，随后服务端异常。

## 人工质量评分

| Case | 评分 | 判断 |
| --- | ---: | --- |
| perf_short_cn | 5/5 | 内容合理，格式干净。 |
| perf_code | 3/5 | 代码方向合理，但 max token 截断，函数未完整收口。 |
| math_reasoning_cn | 3/5 | 推导到十位为 10 的矛盾，但截断在“注意”处，没有最终无解结论。 |
| code_review | 5/5 | 修复正确，解释准确，无额外格式污染。 |
| instruction_following | 5/5 | 严格 JSON-only，字段和数组数量符合要求。 |
| niah_1200_words | 1/5 | 请求失败，未产出答案。 |

综合质量分：3.67/5。

## 记录位置

- Raw summary：`output/qwen36-4090-extreme-20260513/raw/luce_dflash_budget26_tq3.summary.json`
- Raw JSONL：`output/qwen36-4090-extreme-20260513/raw/luce_dflash_budget26_tq3.jsonl`
- 服务日志：`output/qwen36-4090-extreme-20260513/logs/dflash-18366.log`

## 最终判断

DFlash 标准路径可作为短输出质量对照，不应作为长上下文极限测试方案。若继续推进，需要先修 32K prompt 无压缩路径的 500，或明确将 DFlash 标准 lane 限定在短上下文。
