# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-08T15:55:31.403831+00:00`
- Baseline: `unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Q4_K_M`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 2 / 4 (50.0%) |
| first validation success | 2 / 4 (50.0%) |
| first avg elapsed_ms | 57982.83 |
| first avg prompt_tokens | 854.25 |
| first avg completion_tokens | 1319.25 |
| first avg total_tokens | 2173.50 |
| first avg predicted_per_second | 42.72 |
| first avg files_written_count | 0.75 |
| first avg reasoning_content_length | 2264.25 |
| first avg content_length | 2956.25 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 3 / 4 (75.0%) |
| best validation success | 3 / 4 (75.0%) |
| best avg elapsed_ms | 63808.86 |
| best avg prompt_tokens | 854.25 |
| best avg completion_tokens | 1330.25 |
| best avg total_tokens | 2184.50 |
| best avg predicted_per_second | 42.72 |
| best avg files_written_count | 1.00 |
| best avg reasoning_content_length | 2296.25 |
| best avg content_length | 2987.50 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 0 / 4 (0.0%) |
| first validation success | 0 / 4 (0.0%) |
| first avg elapsed_ms | 35088.48 |
| first avg prompt_tokens | 855.25 |
| first avg completion_tokens | 1493.25 |
| first avg total_tokens | 2348.50 |
| first avg predicted_per_second | 44.68 |
| first avg files_written_count | 0.00 |
| first avg reasoning_content_length | 3367.00 |
| first avg content_length | 2645.25 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 1 / 4 (25.0%) |
| best validation success | 1 / 4 (25.0%) |
| best avg elapsed_ms | 33167.69 |
| best avg prompt_tokens | 855.25 |
| best avg completion_tokens | 1400.00 |
| best avg total_tokens | 2255.25 |
| best avg predicted_per_second | 44.69 |
| best avg files_written_count | 0.25 |
| best avg reasoning_content_length | 2624.00 |
| best avg content_length | 3157.00 |

## Per Task Snapshot

| Task | ud_q4_xl first | ud_q4_xl first ms | ud_q4_xl best | ud_q4_xl best ms | distilled_q4_k_m first | distilled_q4_k_m first ms | distilled_q4_k_m best | distilled_q4_k_m best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | validate_ok | 73113.45 | validate_ok | 73113.45 | request_ok | 41860.84 | request_ok | 41860.84 |
| agentic_python_metrics_contract | validate_ok | 41692.41 | validate_ok | 41692.41 | request_ok | 25087.76 | request_ok | 25087.76 |
| agentic_python_reconcile_pkg | request_ok | 79812.57 | request_ok | 79812.57 | request_ok | 51058.58 | validate_ok | 43375.44 |
| agentic_python_restore_bootstrap | request_ok | 37312.90 | validate_ok | 60617.01 | request_ok | 22346.73 | request_ok | 22346.73 |
