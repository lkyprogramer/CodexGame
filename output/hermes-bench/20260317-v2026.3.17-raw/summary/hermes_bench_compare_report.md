# Hermes v2026.3.17 Raw CLI 对比报告

## 1. 直接结论

这次升级到 `v2026.3.17 / v0.3.0` 后，**原生 Hermes CLI 明显有进步，但还不足以删掉 `hermes-safe` wrapper**。

最核心的判断是：

- `process_success`: `10 -> 19`
- `overall pass`: `14 -> 17`
- `contract_success`: `14 -> 17`
- `json_parse_success`: `11 -> 13`
- `validation_success`: `20 -> 20`

也就是说，**新版最明显改善的是“跑完能力”和“少崩能力”**，不是把所有结构化/契约问题都彻底解决。

## 2. 基线对比

| 指标 | 旧版 v0.2.0 | 新版 v0.3.0 | 变化 |
| --- | ---: | ---: | --- |
| Overall pass | 14 / 20 | 17 / 20 | +3 |
| Process success | 10 / 20 | 19 / 20 | +9 |
| Contract success | 14 / 20 | 17 / 20 | +3 |
| JSON parse success | 11 / 20 | 13 / 20 | +2 |
| Validation success | 20 / 20 | 20 / 20 | 0 |
| Terminal tool used | 11 / 20 | 16 / 20 | +5 |
| Avg elapsed_ms | 18226.19 | 51548.25 | +33322.06 |

## 3. Family 变化

| Family | 旧版 Pass | 新版 Pass | 旧版 Avg Score | 新版 Avg Score |
| --- | ---: | ---: | ---: | ---: |
| basic | 3 / 4 | 3 / 4 | 11.50 | 12.25 |
| repo_readonly | 2 / 6 | 4 / 6 | 6.50 | 10.83 |
| terminal | 3 / 4 | 4 / 4 | 12.00 | 15.00 |
| sandbox | 6 / 6 | 6 / 6 | 16.00 | 16.00 |

## 4. 关键变化任务

- `basic_status_line`: `14/True` -> `15/True`
- `basic_json_only`: `14/True` -> `15/True`
- `basic_three_bullets`: `3/False` -> `4/False`
- `repo_entrypoints_json`: `14/True` -> `15/True`
- `repo_restore_root_cause`: `13/True` -> `14/True`
- `repo_metrics_protocol_json`: `3/False` -> `15/True`
- `repo_reconnect_circuit_breaker`: `3/False` -> `8/False`
- `repo_top_gaps_json`: `3/False` -> `10/True`
- `terminal_pwd_git_status`: `3/False` -> `15/True`

## 5. 最终判断

- **有进步，但仍需要 wrapper**
- 这次升级已经显著减少了原生 CLI 的进程级失败，说明 upstream 在 provider/router、tool args、CLI 链路上确实有实质改善。
- 但它还没有把 raw Hermes 提升到“可以稳定替代 `hermes-safe`”的程度，主要剩余问题是：
  - 仍有少量严格契约题不过
  - 真实仓库只读分析仍然不够稳定
  - 超时问题仍存在（`repo_atomic_build_write_guard`）

## 6. 当前建议

- 继续保留 `hermes-safe`
- 可以把 `v2026.3.17` 作为新的 Hermes 基线版本使用
- 如果后面还要进一步减 wrapper 依赖，优先复测：
  - `repo_atomic_build_write_guard`
  - `basic_three_bullets`
  - `repo_reconnect_circuit_breaker`

## 7. 工件

- 旧基线：[`output/hermes-bench/20260315-run/bench-full/summary/hermes_bench_report.md`](/Users/luo/Documents/github/CodexGame/output/hermes-bench/20260315-run/bench-full/summary/hermes_bench_report.md)
- 新结果：[`output/hermes-bench/20260317-v2026.3.17-raw/summary/hermes_bench_report.md`](/Users/luo/Documents/github/CodexGame/output/hermes-bench/20260317-v2026.3.17-raw/summary/hermes_bench_report.md)
- 本报告：[`output/hermes-bench/20260317-v2026.3.17-raw/summary/hermes_bench_compare_report.md`](/Users/luo/Documents/github/CodexGame/output/hermes-bench/20260317-v2026.3.17-raw/summary/hermes_bench_compare_report.md)
