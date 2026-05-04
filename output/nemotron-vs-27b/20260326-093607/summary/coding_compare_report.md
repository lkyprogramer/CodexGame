# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-26T02:20:17.046970+00:00`
- Baseline: `bench/qwen35-27b-dense-ud-q4_xl`
- Candidate: `bench/nemotron-cascade-2-30b-a3b-iq4_xs`

## Aggregate Metrics

| Metric | 27b_ud_q4_xl | nemotron_cascade_2_30b_a3b_iq4_xs |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 25388.13 | 6287.40 |
| avg prompt_ms | 1755.18 | 501.58 |
| avg predicted_per_second | 42.32 | 209.26 |
| avg prompt_tokens | 4054.86 | 3793.36 |
| avg reasoning_content_length | 0.00 | 0.00 |
| avg content_length | 3955.09 | 4013.77 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | 27b_ud_q4_xl score | nemotron_cascade_2_30b_a3b_iq4_xs http | nemotron_cascade_2_30b_a3b_iq4_xs ms | nemotron_cascade_2_30b_a3b_iq4_xs tok/s | nemotron_cascade_2_30b_a3b_iq4_xs score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 200 | 18589.37 | 42.87 | - | 200 | 3276.39 | 213.20 | - |
| java_cache_stale_after_write | 200 | 15621.18 | 42.78 | - | 200 | 4193.45 | 212.68 | - |
| java_csv_import_partial_batch | 200 | 18391.98 | 42.78 | - | 200 | 6300.45 | 212.48 | - |
| java_enum_db_compat | 200 | 13021.00 | 42.87 | - | 200 | 3761.99 | 213.05 | - |
| java_idempotency_payment_callback | 200 | 26487.35 | 42.74 | - | 200 | 5138.66 | 212.41 | - |
| java_null_nested_config | 200 | 19156.36 | 42.85 | - | 200 | 5403.46 | 210.78 | - |
| java_optimistic_lock_missing | 200 | 25867.68 | 42.80 | - | 200 | 6041.06 | 212.48 | - |
| java_outbox_publish_before_commit | 200 | 25947.57 | 42.76 | - | 200 | 4845.35 | 212.79 | - |
| java_pagination_boundary | 200 | 22287.06 | 42.85 | - | 200 | 5327.77 | 212.60 | - |
| java_path_body_id_mismatch | 200 | 19538.03 | 42.87 | - | 200 | 4628.93 | 213.01 | - |
| java_permission_scope_trust_bug | 200 | 15085.33 | 42.79 | - | 200 | 3887.85 | 213.02 | - |
| java_retry_duplicate_side_effect | 200 | 25877.64 | 42.76 | - | 200 | 5173.89 | 212.43 | - |
| java_soft_delete_unique_email | 200 | 23226.58 | 42.81 | - | 200 | 6029.07 | 213.11 | - |
| java_transaction_partial_commit | 200 | 17964.22 | 42.88 | - | 200 | 5724.44 | 212.92 | - |
| script_bash_atomic_deploy | 200 | 23110.18 | 42.77 | - | 200 | 7049.69 | 212.37 | - |
| script_bash_log_triage | 200 | 28338.58 | 42.73 | - | 200 | 6550.88 | 212.19 | - |
| script_python_csv_reconcile | 200 | 31898.01 | 42.73 | - | 200 | 7324.99 | 212.06 | - |
| script_python_jsonl_replay_analyzer | 200 | 28695.82 | 42.74 | - | 200 | 7287.38 | 212.18 | - |
| ts_boot_restore_consistency | 200 | 38302.64 | 40.00 | - | 200 | 11017.90 | 193.73 | - |
| ts_build_atomic_write_guard | 200 | 38411.03 | 40.92 | - | 200 | 8416.83 | 199.23 | - |
| ts_reconnect_circuit_breaker | 200 | 37972.10 | 40.04 | - | 200 | 9363.58 | 193.70 | - |
| ts_runtime_metrics_protocol | 200 | 44749.08 | 39.61 | - | 200 | 11578.84 | 191.31 | - |
