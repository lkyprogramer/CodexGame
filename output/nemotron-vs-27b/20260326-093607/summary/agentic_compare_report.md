# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-26T02:20:17.086506+00:00`
- Baseline: `bench/qwen35-27b-dense-ud-q4_xl`
- Candidate: `bench/nemotron-cascade-2-30b-a3b-iq4_xs`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 8 / 8 (100.0%) |
| first JSON parse success | 8 / 8 (100.0%) |
| first validation success | 7 / 8 (87.5%) |
| first avg elapsed_ms | 11338.17 |
| first avg prompt_tokens | 817.25 |
| first avg completion_tokens | 408.50 |
| first avg total_tokens | 1225.75 |
| first avg predicted_per_second | 42.83 |
| first avg files_written_count | 1.50 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1547.00 |
| best request success | 8 / 8 (100.0%) |
| best JSON parse success | 8 / 8 (100.0%) |
| best validation success | 7 / 8 (87.5%) |
| best avg elapsed_ms | 11338.17 |
| best avg prompt_tokens | 817.25 |
| best avg completion_tokens | 408.50 |
| best avg total_tokens | 1225.75 |
| best avg predicted_per_second | 42.83 |
| best avg files_written_count | 1.50 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1547.00 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 8 / 8 (100.0%) |
| first JSON parse success | 6 / 8 (75.0%) |
| first validation success | 5 / 8 (62.5%) |
| first avg elapsed_ms | 4138.85 |
| first avg prompt_tokens | 795.62 |
| first avg completion_tokens | 602.50 |
| first avg total_tokens | 1398.12 |
| first avg predicted_per_second | 212.11 |
| first avg files_written_count | 1.50 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 2228.50 |
| best request success | 8 / 8 (100.0%) |
| best JSON parse success | 8 / 8 (100.0%) |
| best validation success | 7 / 8 (87.5%) |
| best avg elapsed_ms | 4339.10 |
| best avg prompt_tokens | 795.62 |
| best avg completion_tokens | 656.38 |
| best avg total_tokens | 1452.00 |
| best avg predicted_per_second | 212.13 |
| best avg files_written_count | 1.88 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 2439.50 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl first | 27b_ud_q4_xl first ms | 27b_ud_q4_xl best | 27b_ud_q4_xl best ms | nemotron_cascade_2_30b_a3b_iq4_xs first | nemotron_cascade_2_30b_a3b_iq4_xs first ms | nemotron_cascade_2_30b_a3b_iq4_xs best | nemotron_cascade_2_30b_a3b_iq4_xs best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 7877.46 | validate_ok | 7877.46 | request_ok | 3287.85 | validate_ok | 4071.76 |
| agentic_bash_log_triage_gz | validate_ok | 9255.70 | validate_ok | 9255.70 | validate_ok | 4700.32 | validate_ok | 4700.32 |
| agentic_python_metrics_contract | validate_ok | 9215.40 | validate_ok | 9215.40 | validate_ok | 4590.48 | validate_ok | 4590.48 |
| agentic_python_reconcile_pkg | validate_ok | 24866.29 | validate_ok | 24866.29 | request_ok | 5440.60 | validate_ok | 6258.66 |
| agentic_python_replay_analyzer_patch | validate_ok | 9008.05 | validate_ok | 9008.05 | validate_ok | 4154.37 | validate_ok | 4154.37 |
| agentic_python_restore_bootstrap | validate_ok | 6112.69 | validate_ok | 6112.69 | validate_ok | 2407.51 | validate_ok | 2407.51 |
| agentic_ts_metrics_contract_patch | validate_ok | 17164.92 | validate_ok | 17164.92 | validate_ok | 4199.01 | validate_ok | 4199.01 |
| agentic_ts_restore_bootstrap_patch | parse_ok | 7204.85 | parse_ok | 7204.85 | parse_ok | 4330.69 | parse_ok | 4330.69 |
