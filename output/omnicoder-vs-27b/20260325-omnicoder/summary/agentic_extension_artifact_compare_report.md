# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.532162+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/omnicoder-9b-q8_0`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 3 / 4 (75.0%) |
| first validation success | 3 / 4 (75.0%) |
| first avg elapsed_ms | 31558.53 |
| first avg prompt_tokens | 776.25 |
| first avg completion_tokens | 1273.00 |
| first avg total_tokens | 2049.25 |
| first avg predicted_per_second | 42.77 |
| first avg files_written_count | 1.25 |
| first avg reasoning_content_length | 3800.75 |
| first avg content_length | 1354.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 3 / 4 (75.0%) |
| best validation success | 3 / 4 (75.0%) |
| best avg elapsed_ms | 31558.53 |
| best avg prompt_tokens | 776.25 |
| best avg completion_tokens | 1273.00 |
| best avg total_tokens | 2049.25 |
| best avg predicted_per_second | 42.77 |
| best avg files_written_count | 1.25 |
| best avg reasoning_content_length | 3800.75 |
| best avg content_length | 1354.00 |

## Candidate Aggregate

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

## Per Task Snapshot

| Task | 27b_ud_q4_xl first | 27b_ud_q4_xl first ms | 27b_ud_q4_xl best | 27b_ud_q4_xl best ms | omnicoder_9b_q8_0 first | omnicoder_9b_q8_0 first ms | omnicoder_9b_q8_0 best | omnicoder_9b_q8_0 best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage_gz | validate_ok | 31236.90 | validate_ok | 31236.90 | validate_ok | 15362.45 | validate_ok | 15362.45 |
| agentic_python_replay_analyzer_patch | validate_ok | 22328.72 | validate_ok | 22328.72 | validate_ok | 12237.24 | validate_ok | 12237.24 |
| agentic_ts_metrics_contract_patch | validate_ok | 42336.63 | validate_ok | 42336.63 | request_ok | 17145.82 | request_ok | 17145.82 |
| agentic_ts_restore_bootstrap_patch | request_ok | 30331.86 | request_ok | 30331.86 | parse_ok | 8194.38 | parse_ok | 8194.38 |
