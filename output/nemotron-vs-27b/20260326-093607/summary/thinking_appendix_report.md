# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-26T02:20:17.121326+00:00`
- Baseline: `bench/nemotron-cascade-2-30b-a3b-iq4_xs`
- Candidate: `bench/nemotron-cascade-2-30b-a3b-iq4_xs-thinking`

## Aggregate Metrics

| Metric | nemotron_cascade_2_30b_a3b_iq4_xs | nemotron_cascade_2_30b_a3b_iq4_xs_thinking |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 6287.40 | 6939.81 |
| avg prompt_ms | 501.58 | 501.97 |
| avg predicted_per_second | 209.26 | 209.10 |
| avg prompt_tokens | 3793.36 | 3793.36 |
| avg reasoning_content_length | 0.00 | 0.00 |
| avg content_length | 4013.77 | 4901.68 |

## Per Task Snapshot

| Task | nemotron_cascade_2_30b_a3b_iq4_xs http | nemotron_cascade_2_30b_a3b_iq4_xs ms | nemotron_cascade_2_30b_a3b_iq4_xs tok/s | nemotron_cascade_2_30b_a3b_iq4_xs score | nemotron_cascade_2_30b_a3b_iq4_xs_thinking http | nemotron_cascade_2_30b_a3b_iq4_xs_thinking ms | nemotron_cascade_2_30b_a3b_iq4_xs_thinking tok/s | nemotron_cascade_2_30b_a3b_iq4_xs_thinking score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_audit_success_on_failure | 200 | 3276.39 | 213.20 | - | 200 | 5814.78 | 212.41 | - |
| java_cache_stale_after_write | 200 | 4193.45 | 212.68 | - | 200 | 5145.46 | 212.31 | - |
| java_csv_import_partial_batch | 200 | 6300.45 | 212.48 | - | 200 | 6315.63 | 212.50 | - |
| java_enum_db_compat | 200 | 3761.99 | 213.05 | - | 200 | 5514.03 | 212.91 | - |
| java_idempotency_payment_callback | 200 | 5138.66 | 212.41 | - | 200 | 6204.90 | 212.30 | - |
| java_null_nested_config | 200 | 5403.46 | 210.78 | - | 200 | 5414.62 | 210.92 | - |
| java_optimistic_lock_missing | 200 | 6041.06 | 212.48 | - | 200 | 6055.89 | 212.60 | - |
| java_outbox_publish_before_commit | 200 | 4845.35 | 212.79 | - | 200 | 6103.82 | 212.17 | - |
| java_pagination_boundary | 200 | 5327.77 | 212.60 | - | 200 | 5404.67 | 212.66 | - |
| java_path_body_id_mismatch | 200 | 4628.93 | 213.01 | - | 200 | 5362.84 | 212.90 | - |
| java_permission_scope_trust_bug | 200 | 3887.85 | 213.02 | - | 200 | 5729.81 | 212.60 | - |
| java_retry_duplicate_side_effect | 200 | 5173.89 | 212.43 | - | 200 | 6181.13 | 212.48 | - |
| java_soft_delete_unique_email | 200 | 6029.07 | 213.11 | - | 200 | 5630.28 | 212.72 | - |
| java_transaction_partial_commit | 200 | 5724.44 | 212.92 | - | 200 | 5848.94 | 212.61 | - |
| script_bash_atomic_deploy | 200 | 7049.69 | 212.37 | - | 200 | 7041.89 | 212.44 | - |
| script_bash_log_triage | 200 | 6550.88 | 212.19 | - | 200 | 6860.11 | 212.29 | - |
| script_python_csv_reconcile | 200 | 7324.99 | 212.06 | - | 200 | 7382.95 | 211.97 | - |
| script_python_jsonl_replay_analyzer | 200 | 7287.38 | 212.18 | - | 200 | 7308.21 | 212.04 | - |
| ts_boot_restore_consistency | 200 | 11017.90 | 193.73 | - | 200 | 11160.11 | 193.77 | - |
| ts_build_atomic_write_guard | 200 | 8416.83 | 199.23 | - | 200 | 9800.24 | 198.91 | - |
| ts_reconnect_circuit_breaker | 200 | 9363.58 | 193.70 | - | 200 | 10783.45 | 193.35 | - |
| ts_runtime_metrics_protocol | 200 | 11578.84 | 191.31 | - | 200 | 11612.15 | 191.43 | - |
