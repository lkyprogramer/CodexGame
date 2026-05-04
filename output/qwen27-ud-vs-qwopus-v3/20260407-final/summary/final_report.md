# Qwopus v3 vs Qwen27 UD Compare Report

- Generated at (UTC): `2026-04-07T08:34:11.820240+00:00`
- Baseline: `Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Qwopus3.5-27B-v3-Q4_K_M`

## Fresh 64K Coding

| Metric | 27b_ud_q4_xl | qwopus35_27b_v3_q4_k_m |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 24101.95 | 26338.22 |
| avg tok/s | 42.30 | 44.19 |
| avg prompt_tokens | 4054.86 | 4053.86 |
| avg content_length | 3894.00 | 4555.55 |
| avg reasoning_length | 0.00 | 0.00 |

## Fresh 262K Extreme

| Metric | 27b_ud_q4_xl | qwopus35_27b_v3_q4_k_m |
| --- | ---: | ---: |
| success / total | 3 / 4 | 3 / 4 |
| success rate | 75.0% | 75.0% |
| avg elapsed_ms | 146658.55 | 165850.04 |
| avg tok/s | 26.19 | 26.98 |
| avg prompt_tokens | 196203.00 | 196202.00 |
| avg content_length | 3348.75 | 5531.00 |
| avg reasoning_length | 0.00 | 0.00 |

## Fresh Agentic

| Metric | 27b_ud_q4_xl | qwopus35_27b_v3_q4_k_m |
| --- | ---: | ---: |
| first request success | 8 / 8 | 8 / 8 |
| first JSON parse success | 8 / 8 | 0 / 8 |
| first validation success | 6 / 8 | 0 / 8 |
| best-of-2 validation success | 6 / 8 | 0 / 8 |

## Recommendation

不建议替换默认 27B coding / executor 基线；Qwopus v3 在 agentic gate 上落后于 27B UD。
