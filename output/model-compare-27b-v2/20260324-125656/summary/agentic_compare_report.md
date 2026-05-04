# Qwen Agentic Coding Compare Report

- Generated at (UTC): `2026-03-24T14:21:40.817000+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/qwen35-27b-claude46-opus-distilled-v2-q4_k_m`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 1 / 4 (25.0%) |
| first validation success | 1 / 4 (25.0%) |
| first avg elapsed_ms | 27168.11 |
| first avg prompt_tokens | 854.25 |
| first avg completion_tokens | 1005.00 |
| first avg total_tokens | 1859.25 |
| first avg predicted_per_second | 42.80 |
| first avg files_written_count | 0.50 |
| first avg reasoning_content_length | 2263.25 |
| first avg content_length | 1680.75 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 2 / 4 (50.0%) |
| best validation success | 2 / 4 (50.0%) |
| best avg elapsed_ms | 26535.36 |
| best avg prompt_tokens | 854.25 |
| best avg completion_tokens | 993.50 |
| best avg total_tokens | 1847.75 |
| best avg predicted_per_second | 42.80 |
| best avg files_written_count | 0.75 |
| best avg reasoning_content_length | 2178.75 |
| best avg content_length | 1708.25 |

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
| first request success | 4 / 4 (100.0%) |
| first JSON parse success | 1 / 4 (25.0%) |
| first validation success | 1 / 4 (25.0%) |
| first avg elapsed_ms | 27768.96 |
| first avg prompt_tokens | 855.25 |
| first avg completion_tokens | 1103.50 |
| first avg total_tokens | 1958.75 |
| first avg predicted_per_second | 44.71 |
| first avg files_written_count | 0.25 |
| first avg reasoning_content_length | 2838.50 |
| first avg content_length | 1464.00 |
| best request success | 4 / 4 (100.0%) |
| best JSON parse success | 1 / 4 (25.0%) |
| best validation success | 1 / 4 (25.0%) |
| best avg elapsed_ms | 27768.96 |
| best avg prompt_tokens | 855.25 |
| best avg completion_tokens | 1103.50 |
| best avg total_tokens | 1958.75 |
| best avg predicted_per_second | 44.71 |
| best avg files_written_count | 0.25 |
| best avg reasoning_content_length | 2838.50 |
| best avg content_length | 1464.00 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl first | 27b_ud_q4_xl first ms | 27b_ud_q4_xl best | 27b_ud_q4_xl best ms | 27b_claude46_distilled_v2_q4_k_m first | 27b_claude46_distilled_v2_q4_k_m first ms | 27b_claude46_distilled_v2_q4_k_m best | 27b_claude46_distilled_v2_q4_k_m best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| agentic_bash_log_triage | request_ok | 20188.36 | request_ok | 20188.36 | request_ok | 22034.97 | request_ok | 22034.97 |
| agentic_python_metrics_contract | validate_ok | 31124.92 | validate_ok | 31124.92 | request_ok | 21063.65 | request_ok | 21063.65 |
| agentic_python_reconcile_pkg | request_ok | 35002.99 | request_ok | 35002.99 | request_ok | 49172.78 | request_ok | 49172.78 |
| agentic_python_restore_bootstrap | request_ok | 22356.19 | validate_ok | 19825.19 | validate_ok | 18804.45 | validate_ok | 18804.45 |
