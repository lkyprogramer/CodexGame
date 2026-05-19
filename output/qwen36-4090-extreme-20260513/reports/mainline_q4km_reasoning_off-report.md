# mainline_q4km_reasoning_off 测试报告

## 结论

该 lane 可作为未启用推测解码的 Q4_K_M 基线：6/6 请求成功，平均生成吞吐 35.32 tok/s，中位生成吞吐 41.08 tok/s，32K NIAH 命中。质量侧主要问题是 OpenAI 输出仍带空 `<think>` 包裹，导致严格 JSON/精确字符串场景需要后处理或服务端禁用修正；数学题在 220 token 限制下截断在结论前，不能算完整正确。

## 启动配置

- 机器：4090 `192.168.10.29`
- 服务端口：`18360`
- llama.cpp：`/home/hhtele/llama.cpp-qwen36-main-20260513`
- commit：`856c3adac1709be15e1ea2529a0e89f742d25fe0`
- 模型：`/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- 关键参数：`-ngl 99 -c 32768 -np 1 -fa on -ctk q4_0 -ctv q4_0 -rea off --reasoning-format none --temp 0 --top-p 1`

## 性能结果

| 指标 | 结果 |
| --- | ---: |
| case_count | 6 |
| ok_count | 6 |
| error_count | 0 |
| avg_tokens_per_sec | 35.32 |
| median_tokens_per_sec | 41.08 |
| avg_elapsed_s | 4.49 |
| long_context_pass | true |

## 人工质量评分

| Case | 评分 | 判断 |
| --- | ---: | --- |
| perf_short_cn | 4/5 | 列表内容合理，但带空 `<think>` 包裹。 |
| perf_code | 3/5 | 代码方向合理，但输出被 max token 截断且带 `<think>`。 |
| math_reasoning_cn | 3/5 | 推导到十位为 10，已暴露无解关键矛盾，但截断在“注意”处，没有给最终无解结论。 |
| code_review | 4/5 | 正确指出 `sort()` 原地修改并给出 `sorted()` 修复；扣分点是 `<think>` 包裹。 |
| instruction_following | 2/5 | JSON 内容本身可解析，但外层 `<think>` 使其不满足“只输出 JSON”。 |
| niah_1200_words | 4/5 | 命中 needle，但输出带 `<think>`，精确抽取需要清洗。 |

综合质量分：3.33/5。

## 记录位置

- Raw summary：`output/qwen36-4090-extreme-20260513/raw/mainline_q4km_reasoning_off.summary.json`
- Raw JSONL：`output/qwen36-4090-extreme-20260513/raw/mainline_q4km_reasoning_off.jsonl`
- 服务日志：`output/qwen36-4090-extreme-20260513/logs/mainline-18360-reasoning-off.log`

## 最终判断

适合保留为基准线，不适合作为极限性能候选。后续若继续使用 llama.cpp 主线，需要解决空 `<think>` 包裹和短 max_tokens 截断对质量评估的污染。
