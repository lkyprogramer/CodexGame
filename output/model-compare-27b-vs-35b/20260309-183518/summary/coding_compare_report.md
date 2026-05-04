# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-09T11:03:53.675329+00:00`
- Baseline: `bench/qwen35-27b-dense-ud-q4_xl`
- Candidate: `bench/qwen35-35b-a3b-ud-q4_xl`

## Aggregate Metrics

| Metric | 27b_dense_ud_q4_xl | 35b_a3b_ud_q4_xl |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 27276.88 | 9329.46 |
| avg prompt_ms | 1739.10 | 847.07 |
| avg predicted_per_second | 42.32 | 135.98 |
| avg prompt_tokens | 4054.86 | 4054.86 |
| avg reasoning_content_length | 0.00 | 0.00 |
| avg content_length | 3910.82 | 3736.23 |

## Per Task Snapshot

| Task | 27b_dense_ud_q4_xl http | 27b_dense_ud_q4_xl ms | 27b_dense_ud_q4_xl tok/s | 27b_dense_ud_q4_xl score | 35b_a3b_ud_q4_xl http | 35b_a3b_ud_q4_xl ms | 35b_a3b_ud_q4_xl tok/s | 35b_a3b_ud_q4_xl score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 200 | 11606.10 | 42.86 | - | 200 | 5525.98 | 137.26 | - |
| java_cache_stale_after_write | 200 | 15252.64 | 42.81 | - | 200 | 5715.65 | 137.22 | - |
| java_csv_import_partial_batch | 200 | 20444.98 | 42.82 | - | 200 | 9153.74 | 137.38 | - |
| java_enum_db_compat | 200 | 12662.98 | 42.86 | - | 200 | 4235.17 | 138.32 | - |
| java_idempotency_payment_callback | 200 | 34839.62 | 42.78 | - | 200 | 9202.81 | 137.51 | - |
| java_null_nested_config | 200 | 22444.34 | 42.79 | - | 200 | 6134.85 | 137.44 | - |
| java_optimistic_lock_missing | 200 | 25953.49 | 42.81 | - | 200 | 8948.92 | 137.49 | - |
| java_outbox_publish_before_commit | 200 | 29343.51 | 42.77 | - | 200 | 5460.44 | 138.93 | - |
| java_pagination_boundary | 200 | 22415.73 | 42.82 | - | 200 | 7816.80 | 138.78 | - |
| java_path_body_id_mismatch | 200 | 17325.54 | 42.87 | - | 200 | 6354.59 | 139.18 | - |
| java_permission_scope_trust_bug | 200 | 11899.60 | 42.81 | - | 200 | 4617.64 | 135.14 | - |
| java_retry_duplicate_side_effect | 200 | 19440.09 | 42.82 | - | 200 | 13943.88 | 138.16 | - |
| java_soft_delete_unique_email | 200 | 23590.03 | 42.82 | - | 200 | 4523.66 | 138.67 | - |
| java_transaction_partial_commit | 200 | 20840.95 | 42.86 | - | 200 | 6993.36 | 137.25 | - |
| script_bash_atomic_deploy | 200 | 25725.17 | 42.77 | - | 200 | 10374.20 | 138.24 | - |
| script_bash_log_triage | 200 | 28381.98 | 42.76 | - | 200 | 9849.33 | 136.84 | - |
| script_python_csv_reconcile | 200 | 31967.93 | 42.76 | - | 200 | 11861.68 | 137.00 | - |
| script_python_jsonl_replay_analyzer | 200 | 30572.84 | 42.77 | - | 200 | 10652.20 | 138.48 | - |
| ts_boot_restore_consistency | 200 | 43173.43 | 40.01 | - | 200 | 16268.18 | 127.91 | - |
| ts_build_atomic_write_guard | 200 | 38889.18 | 40.88 | - | 200 | 14438.61 | 130.77 | - |
| ts_reconnect_circuit_breaker | 200 | 69035.01 | 40.03 | - | 200 | 15831.77 | 127.99 | - |
| ts_runtime_metrics_protocol | 200 | 44286.25 | 39.66 | - | 200 | 17344.64 | 125.59 | - |
