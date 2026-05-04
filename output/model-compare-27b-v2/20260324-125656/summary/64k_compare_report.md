# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-24T14:21:40.738138+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/qwen35-27b-claude46-opus-distilled-v2-q4_k_m`

## Aggregate Metrics

| Metric | 27b_ud_q4_xl | 27b_claude46_distilled_v2_q4_k_m |
| --- | ---: | ---: |
| success / total | 22 / 22 | 21 / 22 |
| success rate | 100.0% | 95.5% |
| avg elapsed_ms | 29770.86 | 29710.55 |
| avg prompt_ms | 1772.16 | 1891.93 |
| avg predicted_per_second | 42.20 | 44.21 |
| avg prompt_tokens | 4052.86 | 4227.57 |
| avg reasoning_content_length | 2588.32 | 1954.18 |
| avg content_length | 1841.55 | 2241.95 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | 27b_ud_q4_xl score | 27b_claude46_distilled_v2_q4_k_m http | 27b_claude46_distilled_v2_q4_k_m ms | 27b_claude46_distilled_v2_q4_k_m tok/s | 27b_claude46_distilled_v2_q4_k_m score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 200 | 24769.91 | 42.74 | - | 200 | 21055.13 | 44.82 | - |
| java_cache_stale_after_write | 200 | 15752.82 | 42.71 | - | 200 | 17493.07 | 44.75 | - |
| java_csv_import_partial_batch | 200 | 28775.15 | 42.69 | - | 200 | 22952.17 | 44.76 | - |
| java_enum_db_compat | 200 | 23111.47 | 42.73 | - | 200 | 24675.03 | 44.71 | - |
| java_idempotency_payment_callback | 200 | 28670.10 | 42.69 | - | 200 | 25385.39 | 44.74 | - |
| java_null_nested_config | 200 | 22447.67 | 42.69 | - | 200 | 21207.01 | 44.81 | - |
| java_optimistic_lock_missing | 200 | 26035.16 | 42.70 | - | 200 | 26651.38 | 44.73 | - |
| java_outbox_publish_before_commit | 200 | 25450.38 | 42.71 | - | 200 | 21895.66 | 44.75 | - |
| java_pagination_boundary | 200 | 23986.68 | 42.72 | - | 200 | 25457.12 | 44.82 | - |
| java_path_body_id_mismatch | 200 | 17884.78 | 42.76 | - | 200 | 36497.11 | 44.79 | - |
| java_permission_scope_trust_bug | 200 | 17771.57 | 42.70 | - | 503 | 26820.11 | - | - |
| java_retry_duplicate_side_effect | 200 | 27479.18 | 42.71 | - | 200 | 23601.70 | 44.75 | - |
| java_soft_delete_unique_email | 200 | 20616.62 | 42.72 | - | 200 | 21787.99 | 44.68 | - |
| java_transaction_partial_commit | 200 | 26028.60 | 42.79 | - | 200 | 24176.19 | 44.83 | - |
| script_bash_atomic_deploy | 200 | 34654.45 | 42.54 | - | 200 | 31789.04 | 44.75 | - |
| script_bash_log_triage | 200 | 31759.84 | 42.47 | - | 200 | 27773.25 | 44.73 | - |
| script_python_csv_reconcile | 200 | 33515.05 | 42.61 | - | 200 | 32845.96 | 44.73 | - |
| script_python_jsonl_replay_analyzer | 200 | 39242.68 | 42.60 | - | 200 | 31684.37 | 44.74 | - |
| ts_boot_restore_consistency | 200 | 48952.00 | 39.94 | - | 200 | 48793.10 | 41.69 | - |
| ts_build_atomic_write_guard | 200 | 40521.76 | 40.75 | - | 200 | 39336.65 | 42.76 | - |
| ts_reconnect_circuit_breaker | 200 | 49953.99 | 39.81 | - | 200 | 44397.27 | 41.77 | - |
| ts_runtime_metrics_protocol | 200 | 47578.99 | 39.59 | - | 200 | 57357.39 | 41.30 | - |
