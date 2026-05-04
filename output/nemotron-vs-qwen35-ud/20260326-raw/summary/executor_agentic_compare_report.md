# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-26T04:05:23.524026+00:00`
- Baseline: `bench/nemotron-cascade-2-30b-a3b-iq4_xs`
- Candidate: `bench/qwen35-35b-a3b-ud-q4_xl`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 8 / 8 (100.0%) |
| first JSON parse success | 6 / 8 (75.0%) |
| first validation success | 5 / 8 (62.5%) |
| first avg elapsed_ms | 4592.42 |
| first avg prompt_tokens | 795.62 |
| first avg completion_tokens | 613.12 |
| first avg total_tokens | 1408.75 |
| first avg predicted_per_second | 212.32 |
| first avg files_written_count | 1.12 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 2369.00 |
| best request success | 8 / 8 (100.0%) |
| best JSON parse success | 6 / 8 (75.0%) |
| best validation success | 5 / 8 (62.5%) |
| best avg elapsed_ms | 4592.42 |
| best avg prompt_tokens | 795.62 |
| best avg completion_tokens | 613.12 |
| best avg total_tokens | 1408.75 |
| best avg predicted_per_second | 212.32 |
| best avg files_written_count | 1.12 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 2369.00 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 8 / 8 (100.0%) |
| first JSON parse success | 7 / 8 (87.5%) |
| first validation success | 6 / 8 (75.0%) |
| first avg elapsed_ms | 4398.43 |
| first avg prompt_tokens | 817.25 |
| first avg completion_tokens | 421.12 |
| first avg total_tokens | 1238.38 |
| first avg predicted_per_second | 138.64 |
| first avg files_written_count | 1.38 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1553.12 |
| best request success | 8 / 8 (100.0%) |
| best JSON parse success | 8 / 8 (100.0%) |
| best validation success | 7 / 8 (87.5%) |
| best avg elapsed_ms | 4367.95 |
| best avg prompt_tokens | 817.25 |
| best avg completion_tokens | 420.12 |
| best avg total_tokens | 1237.38 |
| best avg predicted_per_second | 138.61 |
| best avg files_written_count | 1.50 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1551.38 |

## Per Task Snapshot

| Task | nemotron_iq4_xs first | nemotron_iq4_xs first ms | nemotron_iq4_xs best | nemotron_iq4_xs best ms | qwen35_a3b_ud_q4_xl first | qwen35_a3b_ud_q4_xl first ms | qwen35_a3b_ud_q4_xl best | qwen35_a3b_ud_q4_xl best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 3679.84 | validate_ok | 3679.84 | validate_ok | 4186.02 | validate_ok | 4186.02 |
| agentic_bash_log_triage_gz | validate_ok | 3697.54 | validate_ok | 3697.54 | validate_ok | 4489.74 | validate_ok | 4489.74 |
| agentic_python_metrics_contract | validate_ok | 5005.45 | validate_ok | 5005.45 | validate_ok | 3772.35 | validate_ok | 3772.35 |
| agentic_python_reconcile_pkg | request_ok | 6846.50 | request_ok | 6846.50 | validate_ok | 7634.12 | validate_ok | 7634.12 |
| agentic_python_replay_analyzer_patch | validate_ok | 4238.40 | validate_ok | 4238.40 | validate_ok | 3374.41 | validate_ok | 3374.41 |
| agentic_python_restore_bootstrap | validate_ok | 3760.15 | validate_ok | 3760.15 | request_ok | 2716.41 | validate_ok | 2472.52 |
| agentic_ts_metrics_contract_patch | request_ok | 5031.13 | request_ok | 5031.13 | validate_ok | 6087.41 | validate_ok | 6087.41 |
| agentic_ts_restore_bootstrap_patch | parse_ok | 4480.36 | parse_ok | 4480.36 | parse_ok | 2926.99 | parse_ok | 2926.99 |
