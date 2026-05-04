# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-26T04:05:23.486663+00:00`
- Baseline: `bench/nemotron-cascade-2-30b-a3b-iq4_xs`
- Candidate: `bench/qwen35-35b-a3b-ud-q4_xl`

## Aggregate Metrics

| Metric | nemotron_iq4_xs | qwen35_a3b_ud_q4_xl |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 6241.97 | 9008.55 |
| avg prompt_ms | 501.09 | 844.69 |
| avg predicted_per_second | 209.68 | 135.94 |
| avg prompt_tokens | 3793.36 | 4054.86 |
| avg reasoning_content_length | 0.00 | 0.00 |
| avg content_length | 3883.95 | 3867.00 |

## Per Task Snapshot

| Task | nemotron_iq4_xs http | nemotron_iq4_xs ms | nemotron_iq4_xs tok/s | nemotron_iq4_xs score | qwen35_a3b_ud_q4_xl http | qwen35_a3b_ud_q4_xl ms | qwen35_a3b_ud_q4_xl tok/s | qwen35_a3b_ud_q4_xl score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 200 | 3915.91 | 213.86 | - | 200 | 5033.85 | 138.06 | - |
| java_cache_stale_after_write | 200 | 4227.10 | 212.73 | - | 200 | 4978.71 | 136.98 | - |
| java_csv_import_partial_batch | 200 | 4813.94 | 212.95 | - | 200 | 8572.69 | 138.11 | - |
| java_enum_db_compat | 200 | 4459.55 | 213.75 | - | 200 | 4339.39 | 136.09 | - |
| java_idempotency_payment_callback | 200 | 6393.36 | 212.71 | - | 200 | 8338.68 | 137.64 | - |
| java_null_nested_config | 200 | 5565.15 | 211.62 | - | 200 | 7715.97 | 136.84 | - |
| java_optimistic_lock_missing | 200 | 6116.09 | 213.22 | - | 200 | 7682.78 | 138.82 | - |
| java_outbox_publish_before_commit | 200 | 4189.11 | 213.38 | - | 200 | 6297.59 | 136.45 | - |
| java_pagination_boundary | 200 | 5325.00 | 212.94 | - | 200 | 7687.61 | 138.21 | - |
| java_path_body_id_mismatch | 200 | 4307.84 | 213.46 | - | 200 | 6662.51 | 137.93 | - |
| java_permission_scope_trust_bug | 200 | 3769.33 | 213.53 | - | 200 | 4586.29 | 138.42 | - |
| java_retry_duplicate_side_effect | 200 | 4732.60 | 213.08 | - | 200 | 8825.88 | 138.21 | - |
| java_soft_delete_unique_email | 200 | 4030.08 | 213.57 | - | 200 | 8068.13 | 137.78 | - |
| java_transaction_partial_commit | 200 | 5708.13 | 212.84 | - | 200 | 7125.02 | 137.49 | - |
| script_bash_atomic_deploy | 200 | 7066.71 | 212.90 | - | 200 | 10208.42 | 138.08 | - |
| script_bash_log_triage | 200 | 6597.27 | 212.59 | - | 200 | 9548.70 | 137.94 | - |
| script_python_csv_reconcile | 200 | 7336.92 | 211.92 | - | 200 | 10695.28 | 137.68 | - |
| script_python_jsonl_replay_analyzer | 200 | 7317.44 | 212.30 | - | 200 | 9381.58 | 138.40 | - |
| ts_boot_restore_consistency | 200 | 10983.89 | 194.23 | - | 200 | 16269.87 | 127.28 | - |
| ts_build_atomic_write_guard | 200 | 9804.31 | 199.69 | - | 200 | 14330.27 | 130.86 | - |
| ts_reconnect_circuit_breaker | 200 | 9015.81 | 193.95 | - | 200 | 14835.02 | 127.45 | - |
| ts_runtime_metrics_protocol | 200 | 11647.75 | 191.84 | - | 200 | 17003.90 | 125.98 | - |
