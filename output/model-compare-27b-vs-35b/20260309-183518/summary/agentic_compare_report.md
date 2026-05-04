# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-09T11:03:53.720472+00:00`
- Baseline: `bench/qwen35-27b-dense-ud-q4_xl`
- Candidate: `bench/qwen35-35b-a3b-ud-q4_xl`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 4 / 4 (100.0%) |
| first validation success | 4 / 4 (100.0%) |
| first avg elapsed_ms | 12664.11 |
| first avg prompt_tokens | 856.25 |
| first avg completion_tokens | 450.75 |
| first avg total_tokens | 1307.00 |
| first avg predicted_per_second | 42.82 |
| first avg files_written_count | 1.50 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1758.50 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 4 / 4 (100.0%) |
| best validation success | 4 / 4 (100.0%) |
| best avg elapsed_ms | 12664.11 |
| best avg prompt_tokens | 856.25 |
| best avg completion_tokens | 450.75 |
| best avg total_tokens | 1307.00 |
| best avg predicted_per_second | 42.82 |
| best avg files_written_count | 1.50 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1758.50 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 4 / 4 (100.0%) |
| first validation success | 4 / 4 (100.0%) |
| first avg elapsed_ms | 4993.29 |
| first avg prompt_tokens | 856.25 |
| first avg completion_tokens | 477.00 |
| first avg total_tokens | 1333.25 |
| first avg predicted_per_second | 138.13 |
| first avg files_written_count | 1.50 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1935.75 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 4 / 4 (100.0%) |
| best validation success | 4 / 4 (100.0%) |
| best avg elapsed_ms | 4993.29 |
| best avg prompt_tokens | 856.25 |
| best avg completion_tokens | 477.00 |
| best avg total_tokens | 1333.25 |
| best avg predicted_per_second | 138.13 |
| best avg files_written_count | 1.50 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1935.75 |

## Per Task Snapshot

| Task | 27b_dense_ud_q4_xl first | 27b_dense_ud_q4_xl first ms | 27b_dense_ud_q4_xl best | 27b_dense_ud_q4_xl best ms | 35b_a3b_ud_q4_xl first | 35b_a3b_ud_q4_xl first ms | 35b_a3b_ud_q4_xl best | 35b_a3b_ud_q4_xl best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 8506.67 | validate_ok | 8506.67 | validate_ok | 4450.45 | validate_ok | 4450.45 |
| agentic_python_metrics_contract | validate_ok | 9668.23 | validate_ok | 9668.23 | validate_ok | 3870.55 | validate_ok | 3870.55 |
| agentic_python_reconcile_pkg | validate_ok | 26384.29 | validate_ok | 26384.29 | validate_ok | 8724.76 | validate_ok | 8724.76 |
| agentic_python_restore_bootstrap | validate_ok | 6097.27 | validate_ok | 6097.27 | validate_ok | 2927.40 | validate_ok | 2927.40 |
