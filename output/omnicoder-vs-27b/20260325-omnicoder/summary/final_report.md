# OmniCoder-9B Q8_0 vs 27B Dense Report

- Generated at (UTC): `2026-03-25T15:26:21.876335+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/omnicoder-9b-q8_0`

## Download

- ModelScope repo: `Tesslate/OmniCoder-9B-GGUF`
- file: `omnicoder-9b-q8_0.gguf`
- size: `9527501120`
- sha256: `3bb360f0d5bf788503dcd751e704760173298a35b26602dfb939474d87745732`
- downloaded this run: `False`

## Fair Profile: 64K Coding

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| success / total | 19 / 22 | 22 / 22 |
| success rate | 86.4% | 100.0% |
| avg elapsed_ms | 30121.34 | 15760.70 |
| avg predicted_per_second | 42.17 | 84.20 |
| avg reasoning_content_length | 2099.05 | 4036.82 |
| avg content_length | 1785.36 | 482.73 |

## Fair Profile: 262K Extreme

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| success / total | 3 / 4 | 3 / 4 |
| success rate | 75.0% | 75.0% |
| avg elapsed_ms | 229353.15 | 142210.12 |
| avg predicted_per_second | 26.35 | 57.57 |

## Fair Profile: Agentic Main

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| first validation success | 2 / 4 | 4 / 4 |
| best-of-2 validation success | 3 / 4 | 4 / 4 |
| best-of-2 json parse success | 3 / 4 | 4 / 4 |
| best-of-2 avg elapsed_ms | 28388.55 | 17356.32 |

## Fair Profile: Agentic Extension

### Repo reasoning subset

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| success / total | 6 / 6 | 6 / 6 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 38907.80 | 22022.31 |
| avg predicted_per_second | 41.03 | 82.43 |

### Artifact delivery subset

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| first validation success | 3 / 4 | 2 / 4 |
| best validation success | 3 / 4 | 2 / 4 |
| best json parse success | 3 / 4 | 3 / 4 |
| best avg elapsed_ms | 31558.53 | 13234.97 |

## OmniCoder Tuned Appendix

### Main agentic

| Metric | fair OmniCoder | tuned OmniCoder |
| --- | ---: | ---: |
| first validation success | 4 / 4 | 3 / 4 |
| best validation success | 4 / 4 | 4 / 4 |
| best avg elapsed_ms | 17356.32 | 5499.81 |

### Repo reasoning subset

| Metric | fair OmniCoder | tuned OmniCoder |
| --- | ---: | ---: |
| success / total | 6 / 6 | 6 / 6 |
| avg elapsed_ms | 22022.31 | 18871.22 |
| avg predicted_per_second | 82.43 | 82.35 |

### Artifact delivery subset

| Metric | fair OmniCoder | tuned OmniCoder |
| --- | ---: | ---: |
| first validation success | 2 / 4 | 1 / 4 |
| best validation success | 2 / 4 | 1 / 4 |
| best avg elapsed_ms | 13234.97 | 5875.62 |

## Startup Summary

| Round | Model | avg startup ms | avg idle GPU MiB | avg idle GPU util % |
| --- | --- | ---: | ---: | ---: |
| 64k | 27b_ud_q4_xl | - | - | - |
| 64k | omnicoder_9b_q8_0 | - | - | - |
| 262k | 27b_ud_q4_xl | - | - | - |
| 262k | omnicoder_9b_q8_0 | - | - | - |

## Recommendation

不建议替换 27B dense 为默认 coding / executor 基线；OmniCoder 在 same-param agentic gate 上没有形成优势。

### Notes

- same-param agentic gate 未过：OmniCoder 在主 agentic 或 artifact delivery 上落后于 27B dense。


## 64K Coding Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl status | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | omnicoder_9b_q8_0 http | omnicoder_9b_q8_0 status | omnicoder_9b_q8_0 ms | omnicoder_9b_q8_0 tok/s |
| --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |
| java_audit_success_on_failure | 503 | fail | 28510.89 | - | 200 | ok | 12978.95 | 84.85 |
| java_cache_stale_after_write | 200 | ok | 25315.19 | 42.70 | 200 | ok | 10641.26 | 84.93 |
| java_csv_import_partial_batch | 200 | ok | 19835.11 | 42.69 | 200 | ok | 14146.20 | 84.93 |
| java_enum_db_compat | 200 | ok | 22754.43 | 42.74 | 200 | ok | 14396.25 | 84.93 |
| java_idempotency_payment_callback | 200 | ok | 29051.55 | 42.68 | 200 | ok | 13736.24 | 84.81 |
| java_null_nested_config | 200 | ok | 23561.76 | 42.72 | 200 | ok | 12971.66 | 84.76 |
| java_optimistic_lock_missing | 200 | ok | 26434.51 | 42.72 | 200 | ok | 13890.84 | 84.93 |
| java_outbox_publish_before_commit | 200 | ok | 28595.69 | 42.69 | 200 | ok | 13551.60 | 84.90 |
| java_pagination_boundary | 503 | fail | 23165.59 | - | 200 | ok | 11734.30 | 84.91 |
| java_path_body_id_mismatch | 200 | ok | 23281.78 | 42.77 | 200 | ok | 13081.46 | 85.03 |
| java_permission_scope_trust_bug | 200 | ok | 14401.54 | 42.75 | 200 | ok | 12919.73 | 84.89 |
| java_retry_duplicate_side_effect | 503 | fail | 28565.82 | - | 200 | ok | 14605.01 | 84.89 |
| java_soft_delete_unique_email | 200 | ok | 18993.35 | 42.75 | 200 | ok | 12333.52 | 84.90 |
| java_transaction_partial_commit | 200 | ok | 27218.23 | 42.81 | 200 | ok | 13292.05 | 84.95 |
| script_bash_atomic_deploy | 200 | ok | 31860.62 | 42.69 | 200 | ok | 15910.79 | 84.83 |
| script_bash_log_triage | 200 | ok | 32270.24 | 42.71 | 200 | ok | 15831.31 | 84.84 |
| script_python_csv_reconcile | 200 | ok | 32012.84 | 42.65 | 200 | ok | 16490.60 | 84.79 |
| script_python_jsonl_replay_analyzer | 200 | ok | 33814.85 | 42.69 | 200 | ok | 18179.99 | 84.86 |
| ts_boot_restore_consistency | 200 | ok | 46679.42 | 39.91 | 200 | ok | 21990.38 | 81.01 |
| ts_build_atomic_write_guard | 200 | ok | 41108.62 | 40.88 | 200 | ok | 22640.75 | 82.13 |
| ts_reconnect_circuit_breaker | 200 | ok | 52374.20 | 40.03 | 200 | ok | 25123.63 | 81.01 |
| ts_runtime_metrics_protocol | 200 | ok | 52863.33 | 39.58 | 200 | ok | 26288.96 | 80.38 |
