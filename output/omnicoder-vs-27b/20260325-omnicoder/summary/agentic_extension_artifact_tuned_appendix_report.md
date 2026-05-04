# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.799985+00:00`
- Baseline: `bench/omnicoder-9b-q8_0`
- Candidate: `bench/omnicoder-9b-q8_0-tuned`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 3 / 4 (75.0%) |
| first validation success | 2 / 4 (50.0%) |
| first avg elapsed_ms | 13234.97 |
| first avg prompt_tokens | 776.25 |
| first avg completion_tokens | 1021.50 |
| first avg total_tokens | 1797.75 |
| first avg predicted_per_second | 84.87 |
| first avg files_written_count | 0.75 |
| first avg reasoning_content_length | 2851.50 |
| first avg content_length | 1249.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 3 / 4 (75.0%) |
| best validation success | 2 / 4 (50.0%) |
| best avg elapsed_ms | 13234.97 |
| best avg prompt_tokens | 776.25 |
| best avg completion_tokens | 1021.50 |
| best avg total_tokens | 1797.75 |
| best avg predicted_per_second | 84.87 |
| best avg files_written_count | 0.75 |
| best avg reasoning_content_length | 2851.50 |
| best avg content_length | 1249.00 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 2 / 4 (50.0%) |
| first validation success | 1 / 4 (25.0%) |
| first avg elapsed_ms | 5875.62 |
| first avg prompt_tokens | 778.25 |
| first avg completion_tokens | 347.75 |
| first avg total_tokens | 1126.00 |
| first avg predicted_per_second | 85.01 |
| first avg files_written_count | 0.50 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1288.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 2 / 4 (50.0%) |
| best validation success | 1 / 4 (25.0%) |
| best avg elapsed_ms | 5875.62 |
| best avg prompt_tokens | 778.25 |
| best avg completion_tokens | 347.75 |
| best avg total_tokens | 1126.00 |
| best avg predicted_per_second | 85.01 |
| best avg files_written_count | 0.50 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1288.00 |

## Per Task Snapshot

| Task | omnicoder_9b_q8_0 first | omnicoder_9b_q8_0 first ms | omnicoder_9b_q8_0 best | omnicoder_9b_q8_0 best ms | omnicoder_9b_q8_0_tuned first | omnicoder_9b_q8_0_tuned first ms | omnicoder_9b_q8_0_tuned best | omnicoder_9b_q8_0_tuned best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage_gz | validate_ok | 15362.45 | validate_ok | 15362.45 | request_ok | 9694.76 | request_ok | 9694.76 |
| agentic_python_replay_analyzer_patch | validate_ok | 12237.24 | validate_ok | 12237.24 | validate_ok | 4326.74 | validate_ok | 4326.74 |
| agentic_ts_metrics_contract_patch | request_ok | 17145.82 | request_ok | 17145.82 | parse_ok | 5764.85 | parse_ok | 5764.85 |
| agentic_ts_restore_bootstrap_patch | parse_ok | 8194.38 | parse_ok | 8194.38 | request_ok | 3716.11 | request_ok | 3716.11 |
