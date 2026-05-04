# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.325796+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/omnicoder-9b-q8_0`

## Aggregate Metrics

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| success / total | 19 / 22 | 22 / 22 |
| success rate | 86.4% | 100.0% |
| avg elapsed_ms | 30121.34 | 15760.70 |
| avg prompt_ms | 2015.15 | 590.36 |
| avg predicted_per_second | 42.17 | 84.20 |
| avg prompt_tokens | 4628.74 | 4052.86 |
| avg reasoning_content_length | 2099.05 | 4036.82 |
| avg content_length | 1785.36 | 482.73 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | 27b_ud_q4_xl score | omnicoder_9b_q8_0 http | omnicoder_9b_q8_0 ms | omnicoder_9b_q8_0 tok/s | omnicoder_9b_q8_0 score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 503 | 28510.89 | - | - | 200 | 12978.95 | 84.85 | - |
| java_cache_stale_after_write | 200 | 25315.19 | 42.70 | - | 200 | 10641.26 | 84.93 | - |
| java_csv_import_partial_batch | 200 | 19835.11 | 42.69 | - | 200 | 14146.20 | 84.93 | - |
| java_enum_db_compat | 200 | 22754.43 | 42.74 | - | 200 | 14396.25 | 84.93 | - |
| java_idempotency_payment_callback | 200 | 29051.55 | 42.68 | - | 200 | 13736.24 | 84.81 | - |
| java_null_nested_config | 200 | 23561.76 | 42.72 | - | 200 | 12971.66 | 84.76 | - |
| java_optimistic_lock_missing | 200 | 26434.51 | 42.72 | - | 200 | 13890.84 | 84.93 | - |
| java_outbox_publish_before_commit | 200 | 28595.69 | 42.69 | - | 200 | 13551.60 | 84.90 | - |
| java_pagination_boundary | 503 | 23165.59 | - | - | 200 | 11734.30 | 84.91 | - |
| java_path_body_id_mismatch | 200 | 23281.78 | 42.77 | - | 200 | 13081.46 | 85.03 | - |
| java_permission_scope_trust_bug | 200 | 14401.54 | 42.75 | - | 200 | 12919.73 | 84.89 | - |
| java_retry_duplicate_side_effect | 503 | 28565.82 | - | - | 200 | 14605.01 | 84.89 | - |
| java_soft_delete_unique_email | 200 | 18993.35 | 42.75 | - | 200 | 12333.52 | 84.90 | - |
| java_transaction_partial_commit | 200 | 27218.23 | 42.81 | - | 200 | 13292.05 | 84.95 | - |
| script_bash_atomic_deploy | 200 | 31860.62 | 42.69 | - | 200 | 15910.79 | 84.83 | - |
| script_bash_log_triage | 200 | 32270.24 | 42.71 | - | 200 | 15831.31 | 84.84 | - |
| script_python_csv_reconcile | 200 | 32012.84 | 42.65 | - | 200 | 16490.60 | 84.79 | - |
| script_python_jsonl_replay_analyzer | 200 | 33814.85 | 42.69 | - | 200 | 18179.99 | 84.86 | - |
| ts_boot_restore_consistency | 200 | 46679.42 | 39.91 | - | 200 | 21990.38 | 81.01 | - |
| ts_build_atomic_write_guard | 200 | 41108.62 | 40.88 | - | 200 | 22640.75 | 82.13 | - |
| ts_reconnect_circuit_breaker | 200 | 52374.20 | 40.03 | - | 200 | 25123.63 | 81.01 | - |
| ts_runtime_metrics_protocol | 200 | 52863.33 | 39.58 | - | 200 | 26288.96 | 80.38 | - |
