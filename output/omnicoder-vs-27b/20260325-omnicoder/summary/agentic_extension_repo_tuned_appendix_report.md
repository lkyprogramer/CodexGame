# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.727446+00:00`
- Baseline: `bench/omnicoder-9b-q8_0`
- Candidate: `bench/omnicoder-9b-q8_0-tuned`

## Aggregate Metrics

| Metric | omnicoder_9b_q8_0 | omnicoder_9b_q8_0_tuned |
| --- | ---: | ---: |
| success / total | 6 / 6 | 6 / 6 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 22022.31 | 18871.22 |
| avg prompt_ms | 1951.23 | 1964.36 |
| avg predicted_per_second | 82.43 | 82.35 |
| avg prompt_tokens | 13654.67 | 13656.67 |
| avg reasoning_content_length | 4141.50 | 0.00 |
| avg content_length | 913.33 | 4527.33 |

## Per Task Snapshot

| Task | omnicoder_9b_q8_0 http | omnicoder_9b_q8_0 ms | omnicoder_9b_q8_0 tok/s | omnicoder_9b_q8_0 score | omnicoder_9b_q8_0_tuned http | omnicoder_9b_q8_0_tuned ms | omnicoder_9b_q8_0_tuned tok/s | omnicoder_9b_q8_0_tuned score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| java_outbox_publish_before_commit | 200 | 14649.16 | 84.82 | - | 200 | 9457.90 | 84.79 | - |
| java_retry_duplicate_side_effect | 200 | 13556.81 | 84.87 | - | 200 | 10191.08 | 84.80 | - |
| ts_boot_restore_consistency | 200 | 26416.19 | 81.23 | - | 200 | 22949.19 | 81.05 | - |
| ts_build_atomic_write_guard | 200 | 19924.00 | 82.13 | - | 200 | 23172.25 | 82.13 | - |
| ts_reconnect_circuit_breaker | 200 | 28735.79 | 81.03 | - | 200 | 22063.17 | 80.88 | - |
| ts_runtime_metrics_protocol | 200 | 28851.94 | 80.51 | - | 200 | 25393.75 | 80.43 | - |
