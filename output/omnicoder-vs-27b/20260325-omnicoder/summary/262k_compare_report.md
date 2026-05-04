# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-25T15:26:21.405158+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/omnicoder-9b-q8_0`

## Aggregate Metrics

| Metric | 27b_ud_q4_xl | omnicoder_9b_q8_0 |
| --- | ---: | ---: |
| success / total | 3 / 4 | 3 / 4 |
| success rate | 75.0% | 75.0% |
| avg elapsed_ms | 229353.15 | 142210.12 |
| avg prompt_ms | 148406.96 | 54806.24 |
| avg predicted_per_second | 26.35 | 57.57 |
| avg prompt_tokens | 196201.00 | 196201.00 |
| avg reasoning_content_length | 3419.75 | 2361.75 |
| avg content_length | 1684.25 | 2995.50 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | 27b_ud_q4_xl score | omnicoder_9b_q8_0 http | omnicoder_9b_q8_0 ms | omnicoder_9b_q8_0 tok/s | omnicoder_9b_q8_0 score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| extreme_java_change_impact_longctx | 200 | 297135.41 | 26.11 | - | 200 | 178035.05 | 57.19 | - |
| extreme_reconcile_script_longctx | 400 | 104986.59 | - | - | 400 | 88135.02 | - | - |
| extreme_restore_bootstrap_longctx | 200 | 256623.98 | 26.48 | - | 200 | 150780.98 | 57.83 | - |
| extreme_runtime_metrics_longctx | 200 | 258666.61 | 26.45 | - | 200 | 151889.42 | 57.68 | - |
