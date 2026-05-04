# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-24T14:21:40.775559+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/qwen35-27b-claude46-opus-distilled-v2-q4_k_m`

## Aggregate Metrics

| Metric | 27b_ud_q4_xl | 27b_claude46_distilled_v2_q4_k_m |
| --- | ---: | ---: |
| success / total | 2 / 4 | 3 / 4 |
| success rate | 50.0% | 75.0% |
| avg elapsed_ms | 246500.86 | 228609.78 |
| avg prompt_ms | 146291.20 | 149900.60 |
| avg predicted_per_second | 26.48 | 27.12 |
| avg prompt_tokens | 194563.00 | 196202.00 |
| avg reasoning_content_length | 3690.50 | 581.00 |
| avg content_length | 0.00 | 3808.50 |

## Per Task Snapshot

| Task | 27b_ud_q4_xl http | 27b_ud_q4_xl ms | 27b_ud_q4_xl tok/s | 27b_ud_q4_xl score | 27b_claude46_distilled_v2_q4_k_m http | 27b_claude46_distilled_v2_q4_k_m ms | 27b_claude46_distilled_v2_q4_k_m tok/s | 27b_claude46_distilled_v2_q4_k_m score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| extreme_java_change_impact_longctx | 503 | 302766.54 | - | - | 200 | 288193.41 | 26.94 | - |
| extreme_reconcile_script_longctx | 400 | 127952.17 | - | - | 400 | 92557.85 | - | - |
| extreme_restore_bootstrap_longctx | 200 | 268618.15 | 26.49 | - | 200 | 274448.78 | 27.23 | - |
| extreme_runtime_metrics_longctx | 200 | 286666.57 | 26.47 | - | 200 | 259239.09 | 27.19 | - |
