# Qwen Coding Compare Report

- Generated at (UTC): `2026-03-08T05:55:08.072491+00:00`
- Baseline: `unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Jackrong Qwen3.5-27B Claude-4.6 Opus Distilled Q4_K_M`

## Aggregate Metrics

| Metric | ud_q4_xl | distilled_q4_k_m |
| --- | ---: | ---: |
| success / total | 2 / 4 | 3 / 4 |
| success rate | 50.0% | 75.0% |
| avg elapsed_ms | 146037.57 | 183827.53 |
| avg prompt_ms | 149449.85 | 150145.70 |
| avg predicted_per_second | 26.30 | 27.13 |
| avg prompt_tokens | 197296.50 | 196202.00 |
| avg reasoning_content_length | 2189.75 | 2450.00 |
| avg content_length | 1091.25 | 1786.50 |

## Per Task Snapshot

| Task | ud_q4_xl http | ud_q4_xl ms | ud_q4_xl tok/s | ud_q4_xl score | distilled_q4_k_m http | distilled_q4_k_m ms | distilled_q4_k_m tok/s | distilled_q4_k_m score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| extreme_java_change_impact_longctx | 200 | 274160.50 | 26.14 | - | 200 | 209599.41 | 26.92 | - |
| extreme_reconcile_script_longctx | 400 | 45683.04 | - | - | 400 | 64024.75 | - | - |
| extreme_restore_bootstrap_longctx | 200 | 240455.83 | 26.47 | - | 200 | 243739.55 | 27.24 | - |
| extreme_runtime_metrics_longctx | 0 | 23850.91 | - | - | 200 | 217946.40 | 27.24 | - |
