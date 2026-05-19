# mtp_udq4xl_spec3 测试报告

## 结论

该 lane 是本轮纯 llama.cpp 路线的最强吞吐方案：6/6 请求成功，平均生成吞吐 48.92 tok/s，中位生成吞吐 50.87 tok/s，比 mainline 基线提升约 38.5%。MTP 接受率日志显示短输出多次达到 0.95-1.00，长上下文 needle 命中。但与 mainline 一样，OpenAI 输出仍带空 `<think>` 包裹，严格格式质量扣分明显。

## 启动配置

- 机器：4090 `192.168.10.29`
- 服务端口：`18364`
- llama.cpp MTP 版本：`/home/hhtele/llama.cpp-mtp-unsloth-20260513`
- commit：`ebe4fca4b59ef8871bb07c34d148bc37fe57fadd`
- 模型：`/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf`
- 模型 SHA256：`4085665ee36d82a672a238a43f0e5643f2f0e39f2d7bd5d373f0ef10ecf53095`
- 关键参数：`-ngl 99 -c 32768 -np 1 -fa on -ctk q4_0 -ctv q4_0 --spec-type mtp --spec-draft-n-max 3 -rea off --reasoning-format none --temp 0 --top-p 1`

## 性能结果

| 指标 | 结果 |
| --- | ---: |
| case_count | 6 |
| ok_count | 6 |
| error_count | 0 |
| avg_tokens_per_sec | 48.92 |
| median_tokens_per_sec | 50.87 |
| avg_elapsed_s | 4.94 |
| long_context_pass | true |

补充日志证据：

- 短/中输出 draft acceptance rate：约 `0.94872` 到 `1.00000`。
- 32K NIAH prompt eval：`31250 tokens / 18.93s = 1650.93 tok/s`。
- 32K NIAH decode acceptance：`1.00000`。

## 人工质量评分

| Case | 评分 | 判断 |
| --- | ---: | --- |
| perf_short_cn | 4/5 | 内容合理，但带 `<think>`。 |
| perf_code | 3/5 | 代码方向合理，但 180 token 截断，返回结构与题目“函数”要求不够完整；带 `<think>`。 |
| math_reasoning_cn | 3/5 | 已推导到十位为 10 的矛盾，但输出截断，未完成最终无解结论；带 `<think>`。 |
| code_review | 4/5 | 修复和解释正确；扣分点是 `<think>`。 |
| instruction_following | 2/5 | JSON 内容合理，但不是严格 JSON-only。 |
| niah_1200_words | 4/5 | 命中 needle，但精确输出前有 `<think>`。 |

综合质量分：3.33/5。

## 记录位置

- Raw summary：`output/qwen36-4090-extreme-20260513/raw/mtp_udq4xl_spec3.summary.json`
- Raw JSONL：`output/qwen36-4090-extreme-20260513/raw/mtp_udq4xl_spec3.jsonl`
- 服务日志：`output/qwen36-4090-extreme-20260513/logs/mtp-18364.log`

## 最终判断

如果目标是“4090 单卡极限生成吞吐”，MTP lane 当前优先级最高。下一轮建议围绕 `--spec-draft-n-max` 做 1/2/3/4 梯度和不同输出长度矩阵，同时必须修正 `<think>` 清洗或禁用策略，否则质量分会被格式污染压低。
