# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.653714+00:00`
- Baseline: `bench/omnicoder-9b-q8_0`
- Candidate: `bench/omnicoder-9b-q8_0-tuned`

## Baseline Aggregate

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

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 3 / 4 (75.0%) |
| first validation success | 3 / 4 (75.0%) |
| first avg elapsed_ms | 5509.08 |
| first avg prompt_tokens | 856.25 |
| first avg completion_tokens | 364.75 |
| first avg total_tokens | 1221.00 |
| first avg predicted_per_second | 85.00 |
| first avg files_written_count | 1.00 |
| first avg reasoning_content_length | 0.00 |
| first avg content_length | 1425.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 4 / 4 (100.0%) |
| best validation success | 4 / 4 (100.0%) |
| best avg elapsed_ms | 5499.81 |
| best avg prompt_tokens | 856.25 |
| best avg completion_tokens | 365.25 |
| best avg total_tokens | 1221.50 |
| best avg predicted_per_second | 84.99 |
| best avg files_written_count | 1.25 |
| best avg reasoning_content_length | 0.00 |
| best avg content_length | 1422.75 |

## Per Task Snapshot

| Task | omnicoder_9b_q8_0 first | omnicoder_9b_q8_0 first ms | omnicoder_9b_q8_0 best | omnicoder_9b_q8_0 best ms | omnicoder_9b_q8_0_tuned first | omnicoder_9b_q8_0_tuned first ms | omnicoder_9b_q8_0_tuned best | omnicoder_9b_q8_0_tuned best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 19187.29 | validate_ok | 19187.29 | validate_ok | 4734.30 | validate_ok | 4734.30 |
| agentic_python_metrics_contract | validate_ok | 9152.82 | validate_ok | 9152.82 | validate_ok | 4530.40 | validate_ok | 4530.40 |
| agentic_python_reconcile_pkg | validate_ok | 30778.65 | validate_ok | 30778.65 | validate_ok | 9721.93 | validate_ok | 9721.93 |
| agentic_python_restore_bootstrap | validate_ok | 10306.54 | validate_ok | 10306.54 | request_ok | 3049.68 | validate_ok | 3012.59 |
