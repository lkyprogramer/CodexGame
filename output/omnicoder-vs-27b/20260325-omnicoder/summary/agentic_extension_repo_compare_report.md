# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.491763+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/omnicoder-9b-q8_0`

## Aggregate Metrics

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| success / total | 6 / 6 | 6 / 6 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 38907.80 | 22022.31 |
| avg prompt_ms | 5824.47 | 1951.23 |
| avg predicted_per_second | 41.03 | 82.43 |
| avg prompt_tokens | 13654.67 | 13654.67 |
| avg reasoning_content_length | 1578.00 | 4141.50 |
| avg content_length | 3607.50 | 913.33 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | 27b_ud_q4_xl score | omnicoder_9b_q8_0 http | omnicoder_9b_q8_0 ms | omnicoder_9b_q8_0 tok/s | omnicoder_9b_q8_0 score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_outbox_publish_before_commit | 200 | 22254.15 | 42.79 | - | 200 | 14649.16 | 84.82 | - |
| java_retry_duplicate_side_effect | 200 | 26141.61 | 42.77 | - | 200 | 13556.81 | 84.87 | - |
| ts_boot_restore_consistency | 200 | 48404.44 | 40.02 | - | 200 | 26416.19 | 81.23 | - |
| ts_build_atomic_write_guard | 200 | 40456.17 | 40.89 | - | 200 | 19924.00 | 82.13 | - |
| ts_reconnect_circuit_breaker | 200 | 44292.40 | 40.04 | - | 200 | 28735.79 | 81.03 | - |
| ts_runtime_metrics_protocol | 200 | 51898.03 | 39.66 | - | 200 | 28851.94 | 80.51 | - |
