# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.452154+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/omnicoder-9b-q8_0`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 2 / 4 (50.0%) |
| first validation success | 2 / 4 (50.0%) |
| first avg elapsed_ms | 31297.66 |
| first avg prompt_tokens | 854.25 |
| first avg completion_tokens | 1232.25 |
| first avg total_tokens | 2086.50 |
| first avg predicted_per_second | 42.74 |
| first avg files_written_count | 0.75 |
| first avg reasoning_content_length | 3456.25 |
| first avg content_length | 1473.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 3 / 4 (75.0%) |
| best validation success | 3 / 4 (75.0%) |
| best avg elapsed_ms | 28388.55 |
| best avg prompt_tokens | 854.25 |
| best avg completion_tokens | 1132.00 |
| best avg total_tokens | 1986.25 |
| best avg predicted_per_second | 42.75 |
| best avg files_written_count | 1.00 |
| best avg reasoning_content_length | 3052.75 |
| best avg content_length | 1469.25 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 4 / 4 (100.0%) |
| first validation success | 4 / 4 (100.0%) |
| first avg elapsed_ms | 17356.32 |
| first avg prompt_tokens | 854.25 |
| first avg completion_tokens | 1172.25 |
| first avg total_tokens | 2026.50 |
| first avg predicted_per_second | 84.90 |
| first avg files_written_count | 1.00 |
| first avg reasoning_content_length | 3412.75 |
| first avg content_length | 1476.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 4 / 4 (100.0%) |
| best validation success | 4 / 4 (100.0%) |
| best avg elapsed_ms | 17356.32 |
| best avg prompt_tokens | 854.25 |
| best avg completion_tokens | 1172.25 |
| best avg total_tokens | 2026.50 |
| best avg predicted_per_second | 84.90 |
| best avg files_written_count | 1.00 |
| best avg reasoning_content_length | 3412.75 |
| best avg content_length | 1476.00 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl first | 27b_ud_q4_xl first ms | 27b_ud_q4_xl best | 27b_ud_q4_xl best ms | omnicoder_9b_q8_0 first | omnicoder_9b_q8_0 first ms | omnicoder_9b_q8_0 best | omnicoder_9b_q8_0 best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 26002.88 | validate_ok | 26002.88 | validate_ok | 19187.29 | validate_ok | 19187.29 |
| agentic_python_metrics_contract | request_ok | 18604.08 | request_ok | 18604.08 | validate_ok | 9152.82 | validate_ok | 9152.82 |
| agentic_python_reconcile_pkg | validate_ok | 49629.25 | validate_ok | 49629.25 | validate_ok | 30778.65 | validate_ok | 30778.65 |
| agentic_python_restore_bootstrap | request_ok | 30954.43 | validate_ok | 19318.01 | validate_ok | 10306.54 | validate_ok | 10306.54 |
