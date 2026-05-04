# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-04-07T08:33:47.459556+00:00`
- Baseline: `Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Qwopus3.5-27B-v3-Q4_K_M`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 8 / 8 (100.0%) |
| first JSON parse success | 8 / 8 (100.0%) |
| first validation success | 6 / 8 (75.0%) |
| first avg elapsed_ms | 9779.00 |
| first avg prompt_tokens | 817.25 |
| first avg completion_tokens | 395.88 |
| first avg total_tokens | 1213.12 |
| first avg predicted_per_second | 42.84 |
| first avg files_written_count | 1.38 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1487.25 |
| best request success | 8 / 8 (100.0%) |
| best JSON parse success | 8 / 8 (100.0%) |
| best validation success | 6 / 8 (75.0%) |
| best avg elapsed_ms | 9779.00 |
| best avg prompt_tokens | 817.25 |
| best avg completion_tokens | 395.88 |
| best avg total_tokens | 1213.12 |
| best avg predicted_per_second | 42.84 |
| best avg files_written_count | 1.38 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1487.25 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 8 / 8 (100.0%) |
| first JSON parse success | 0 / 8 (0.0%) |
| first validation success | 0 / 8 (0.0%) |
| first avg elapsed_ms | 45615.27 |
| first avg prompt_tokens | 816.25 |
| first avg completion_tokens | 2013.38 |
| first avg total_tokens | 2829.62 |
| first avg predicted_per_second | 44.63 |
| first avg files_written_count | 0.00 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 7530.75 |
| best request success | 8 / 8 (100.0%) |
| best JSON parse success | 0 / 8 (0.0%) |
| best validation success | 0 / 8 (0.0%) |
| best avg elapsed_ms | 45615.27 |
| best avg prompt_tokens | 816.25 |
| best avg completion_tokens | 2013.38 |
| best avg total_tokens | 2829.62 |
| best avg predicted_per_second | 44.63 |
| best avg files_written_count | 0.00 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 7530.75 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl first | 27b_ud_q4_xl first ms | 27b_ud_q4_xl best | 27b_ud_q4_xl best ms | qwopus35_27b_v3_q4_k_m first | qwopus35_27b_v3_q4_k_m first ms | qwopus35_27b_v3_q4_k_m best | qwopus35_27b_v3_q4_k_m best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 6824.89 | validate_ok | 6824.89 | request_ok | 40734.11 | request_ok | 40734.11 |
| agentic_bash_log_triage_gz | validate_ok | 8269.08 | validate_ok | 8269.08 | request_ok | 40817.19 | request_ok | 40817.19 |
| agentic_python_metrics_contract | validate_ok | 4823.17 | validate_ok | 4823.17 | request_ok | 41043.54 | request_ok | 41043.54 |
| agentic_python_reconcile_pkg | validate_ok | 25370.35 | validate_ok | 25370.35 | request_ok | 49841.39 | request_ok | 49841.39 |
| agentic_python_replay_analyzer_patch | validate_ok | 7661.91 | validate_ok | 7661.91 | request_ok | 42880.52 | request_ok | 42880.52 |
| agentic_python_restore_bootstrap | validate_ok | 4880.66 | validate_ok | 4880.66 | request_ok | 49784.36 | request_ok | 49784.36 |
| agentic_ts_metrics_contract_patch | parse_ok | 14167.84 | parse_ok | 14167.84 | request_ok | 49995.65 | request_ok | 49995.65 |
| agentic_ts_restore_bootstrap_patch | parse_ok | 6234.10 | parse_ok | 6234.10 | request_ok | 49825.39 | request_ok | 49825.39 |
