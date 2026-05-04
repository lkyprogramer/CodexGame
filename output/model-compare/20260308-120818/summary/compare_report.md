# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-08T04:44:52.117443+00:00`
- Baseline: `unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Jackrong Qwen3.5-27B Claude-4.6 Opus Distilled Q4_K_M`

## Aggregate Metrics

| Metric | ud_q4_xl | distilled_q4_k_m |
| --- | ---: | ---: |
| success / total | 9 / 10 | 10 / 10 |
| success rate | 90.0% | 100.0% |
| avg elapsed_ms | 25601.08 | 26341.27 |
| avg prompt_ms | 2341.88 | 2157.32 |
| avg predicted_per_second | 42.15 | 44.17 |
| avg prompt_tokens | 5413.89 | 4911.70 |
| avg reasoning_content_length | 1841.80 | 1341.60 |
| avg content_length | 1872.00 | 2643.60 |

## Per Task Snapshot

| Task | ud_q4_xl http | ud_q4_xl ms | ud_q4_xl tok/s | ud_q4_xl score | distilled_q4_k_m http | distilled_q4_k_m ms | distilled_q4_k_m tok/s | distilled_q4_k_m score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 0 | 5862.06 | - | 14 | 200 | 15990.21 | 44.83 | 14 |
| java_enum_db_compat | 200 | 23919.38 | 42.80 | 11 | 200 | 20237.62 | 44.82 | 11 |
| java_null_nested_config | 200 | 22511.44 | 42.76 | 13 | 200 | 23829.70 | 44.81 | 15 |
| java_optimistic_lock_missing | 200 | 29423.33 | 42.80 | 14 | 200 | 27563.73 | 44.79 | 14 |
| java_pagination_boundary | 200 | 26695.02 | 42.81 | 8 | 200 | 21432.03 | 44.81 | 15 |
| java_path_body_id_mismatch | 200 | 18699.03 | 42.85 | 12 | 200 | 20918.20 | 44.81 | 13 |
| java_soft_delete_unique_email | 200 | 18150.31 | 42.82 | 14 | 200 | 19849.05 | 44.82 | 13 |
| java_transaction_partial_commit | 200 | 19331.13 | 42.86 | 15 | 200 | 20536.57 | 44.89 | 15 |
| ts_boot_restore_consistency | 200 | 45394.80 | 39.99 | 8 | 200 | 47419.83 | 41.74 | 7 |
| ts_runtime_metrics_protocol | 200 | 46024.30 | 39.63 | 12 | 200 | 45635.75 | 41.36 | 14 |
