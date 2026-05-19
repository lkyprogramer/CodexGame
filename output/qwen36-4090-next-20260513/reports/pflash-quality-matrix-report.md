# PFlash keep-ratio 质量矩阵报告

## 结论

PFlash `keep_ratio=0.03` 和 `0.05` 都通过 4 类长上下文质量任务；`0.03` 更激进，压缩到约 900 token 仍能命中全部质量点，端到端略快；`0.05` 输出更完整稳健。`0.08` 和 `0.10` 出现严重稳定性问题：第一条请求输出 `!`，后续请求 HTTP 500，日志显示 daemon `BrokenPipeError`。

本轮 PFlash 复测为了绕过 prefix/full-cache startup sync timeout，使用了 `--prefix-cache-slots 0 --prefill-cache-slots 0`；因此结果反映 PFlash 压缩质量和单请求稳定性，不代表缓存命中后的最终吞吐。

## 测试配置

- Lucebox：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash`
- 目标模型：`/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- draft：`/data/models/qwen/dflash-draft/model.safetensors`
- drafter：`/data/models/qwen/Qwen3-0.6B-BF16.gguf`
- 固定参数：`--budget 26 --max-ctx 32768 --ctk tq3_0 --ctv tq3_0 --fa-window 0 --prefill-compression auto --prefill-threshold 4096`
- 缓存参数：`--prefix-cache-slots 0 --prefill-cache-slots 0`
- 任务：多 needle、摘要、事实问答、代码检索。

## 结果

| keep_ratio | 成功率 | Avg tok/s | Median tok/s | 质量命中 | 压缩后 token 规模 | 结论 |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 0.03 | 4/4 | 3.64 | 3.94 | 全部命中 | 约 903-928 | 最激进且可用 |
| 0.05 | 4/4 | 3.31 | 3.61 | 全部命中 | 约 1511-1536 | 更稳妥的推荐档 |
| 0.08 | 1/4 | 0.10 | 0.10 | 未命中 | 首条约 2496 | 不可用 |
| 0.10 | 1/4 | 0.09 | 0.09 | 未命中 | 首条约 3104 | 不可用 |

## 人工质量评分

| keep_ratio | 多 needle | 摘要 | 事实问答 | 代码检索 | 综合 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.03 | 4/5 | 5/5 | 5/5 | 4/5 | 4.5/5 |
| 0.05 | 4/5 | 5/5 | 5/5 | 4/5 | 4.5/5 |
| 0.08 | 1/5 | 1/5 | 1/5 | 1/5 | 1.0/5 |
| 0.10 | 1/5 | 1/5 | 1/5 | 1/5 | 1.0/5 |

扣分说明：

- 0.03/0.05 多 needle 和代码检索使用了 markdown fence 包裹，内容正确但不是严格“只输出目标值”。
- 0.08/0.10 第一条返回 `!`，后续 3 条 HTTP 500，不能作为质量通过。

## 稳定性证据

0.08/0.10 日志均出现：

```text
BrokenPipeError: [Errno 32] Broken pipe
```

触发位置：

```text
scripts/_prefill_hook.py, line 144, compress_text_via_daemon
_send_and_ack(..., "park target\n")
```

## 记录位置

- Raw：`output/qwen36-4090-next-20260513/raw/pflash_keep*_quality_matrix_nocache.*`
- Logs：`output/qwen36-4090-next-20260513/logs/pflash_keep*_quality_matrix_nocache.log`
- 启动失败日志：`output/qwen36-4090-next-20260513/logs/pflash_keep003_quality_matrix.log`

## 最终判断

PFlash 推荐保留两档：`0.03` 作为极限压缩质量档，`0.05` 作为稳妥默认档。`0.08/0.10` 在修复 daemon BrokenPipe 前应屏蔽。
