# luce_pflash_auto_keep005 测试报告

## 结论

该 lane 是本轮质量最稳的 Lucebox 路线：6/6 请求成功，平均生成吞吐 38.51 tok/s，中位生成吞吐 35.27 tok/s，严格 JSON 和 needle 输出都干净。PFlash 在 32K NIAH 上触发自动压缩，将 31235 token 压到 1507 token，并命中 needle。性能低于 MTP，但质量格式明显优于 llama.cpp MTP/mainline。

## 启动配置

- 机器：4090 `192.168.10.29`
- 服务端口：`18367`
- Lucebox：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash`
- 目标模型：`/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- draft：`/data/models/qwen/dflash-draft/model.safetensors`
- PFlash drafter：`/data/models/qwen/Qwen3-0.6B-BF16.gguf`
- tokenizer：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash/tokenizers/qwen36_27b`
- drafter tokenizer：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash/tokenizers/qwen3_0p6b`
- 关键参数：`DFLASH27B_KV_K=tq3_0 DFLASH27B_KV_V=tq3_0 DFLASH_FP_USE_BSA=1 DFLASH_FP_ALPHA=0.85 --budget 26 --max-ctx 32768 --ctk tq3_0 --ctv tq3_0 --fa-window 0 --prefill-compression auto --prefill-threshold 4096 --prefill-keep-ratio 0.05`

## 性能结果

| 指标 | 结果 |
| --- | ---: |
| case_count | 6 |
| ok_count | 6 |
| error_count | 0 |
| avg_tokens_per_sec | 38.51 |
| median_tokens_per_sec | 35.27 |
| avg_elapsed_s | 4.04 |
| long_context_pass | true |

PFlash 长上下文日志：

- 原始 prompt：`31235` tokens。
- 压缩后 prompt：`1507` tokens，最终请求侧 usage 为 `1521` prompt tokens。
- 压缩耗时：`score_and_compress total 1.20s`。
- 压缩比例：约 `4.8%` 保留。
- NIAH 输出：`NEEDLE_CODE_4090_MTP_DFLASH`。

## 人工质量评分

| Case | 评分 | 判断 |
| --- | ---: | --- |
| perf_short_cn | 5/5 | 内容合理，格式干净。 |
| perf_code | 3/5 | 代码方向合理，但 max token 截断，函数未完整收口。 |
| math_reasoning_cn | 3/5 | 推导到十位为 10 的矛盾，但截断在“注意”处，没有最终无解结论。 |
| code_review | 5/5 | 修复正确，解释准确，无额外格式污染。 |
| instruction_following | 5/5 | 严格 JSON-only，字段和数组数量符合要求。 |
| niah_1200_words | 5/5 | 精确命中 needle，无额外包裹。 |

综合质量分：4.33/5。

## 记录位置

- Raw summary：`output/qwen36-4090-extreme-20260513/raw/luce_pflash_auto_keep005.summary.json`
- Raw JSONL：`output/qwen36-4090-extreme-20260513/raw/luce_pflash_auto_keep005.jsonl`
- 服务日志：`output/qwen36-4090-extreme-20260513/logs/pflash-18367.log`

## 最终判断

如果目标是“质量、格式、长上下文可用性综合最强”，PFlash lane 当前优先级最高。下一轮应重点测 keep ratio `0.03/0.05/0.08/0.10` 和 NIAH 多 needle/问答类长上下文质量，确认压缩不会造成真实任务召回损失。
