# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-08T05:55:08.073117+00:00`
- Baseline: `unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Jackrong Qwen3.5-27B Claude-4.6 Opus Distilled Q4_K_M`

## Aggregate Metrics

| Metric | ud_q4_xl | distilled_q4_k_m |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 29788.06 | 27112.57 |
| avg prompt_ms | 1745.98 | 1776.73 |
| avg predicted_per_second | 42.33 | 44.29 |
| avg prompt_tokens | 4052.86 | 4053.86 |
| avg reasoning_content_length | 2656.55 | 1376.50 |
| avg content_length | 1877.73 | 2986.45 |

## Per Task Snapshot

| Task | ud_q4_xl http | ud_q4_xl ms | ud_q4_xl tok/s | ud_q4_xl score | distilled_q4_k_m http | distilled_q4_k_m ms | distilled_q4_k_m tok/s | distilled_q4_k_m score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 200 | 24777.59 | 42.84 | - | 200 | 19893.09 | 44.84 | - |
| java_cache_stale_after_write | 200 | 23595.77 | 42.80 | - | 200 | 22736.21 | 44.78 | - |
| java_csv_import_partial_batch | 200 | 21886.53 | 42.79 | - | 200 | 25884.03 | 44.82 | - |
| java_enum_db_compat | 200 | 24717.08 | 42.83 | - | 200 | 16692.01 | 44.85 | - |
| java_idempotency_payment_callback | 200 | 28006.35 | 42.79 | - | 200 | 25173.79 | 44.81 | - |
| java_null_nested_config | 200 | 23545.99 | 42.81 | - | 200 | 21451.89 | 44.82 | - |
| java_optimistic_lock_missing | 200 | 25422.24 | 42.84 | - | 200 | 21988.04 | 44.85 | - |
| java_outbox_publish_before_commit | 200 | 25964.42 | 42.79 | - | 200 | 24511.70 | 44.83 | - |
| java_pagination_boundary | 200 | 22342.34 | 42.82 | - | 200 | 21387.29 | 44.83 | - |
| java_path_body_id_mismatch | 200 | 22307.82 | 42.86 | - | 200 | 21243.83 | 44.83 | - |
| java_permission_scope_trust_bug | 200 | 28028.28 | 42.77 | - | 200 | 22225.37 | 44.83 | - |
| java_retry_duplicate_side_effect | 200 | 25964.83 | 42.80 | - | 200 | 24001.35 | 44.80 | - |
| java_soft_delete_unique_email | 200 | 22464.55 | 42.82 | - | 200 | 18832.77 | 44.85 | - |
| java_transaction_partial_commit | 200 | 25099.54 | 42.86 | - | 200 | 24674.88 | 44.87 | - |
| script_bash_atomic_deploy | 200 | 30647.56 | 42.79 | - | 200 | 29316.20 | 44.80 | - |
| script_bash_log_triage | 200 | 28415.28 | 42.79 | - | 200 | 27114.14 | 44.79 | - |
| script_python_csv_reconcile | 200 | 36454.46 | 42.77 | - | 200 | 30520.76 | 44.78 | - |
| script_python_jsonl_replay_analyzer | 200 | 32928.00 | 42.78 | - | 200 | 19498.00 | 44.79 | - |
| ts_boot_restore_consistency | 200 | 49509.52 | 40.01 | - | 200 | 43392.43 | 41.76 | - |
| ts_build_atomic_write_guard | 200 | 42043.61 | 40.94 | - | 200 | 38386.49 | 42.75 | - |
| ts_reconnect_circuit_breaker | 200 | 45261.48 | 40.08 | - | 200 | 41679.16 | 41.78 | - |
| ts_runtime_metrics_protocol | 200 | 45954.00 | 39.65 | - | 200 | 55873.08 | 41.39 | - |
