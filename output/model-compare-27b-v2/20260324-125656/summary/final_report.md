# Qwen3.5-27B Distilled v2 Compare Report

- Generated at (UTC): `2026-03-24T14:33:36.204981+00:00`
- Baseline: `bench/qwen35-27b-ud-q4_xl`
- Candidate: `bench/qwen35-27b-claude46-opus-distilled-v2-q4_k_m`

## Fresh 64K Coding

| Metric | 27b_ud_q4_xl | 27b_claude46_distilled_v2_q4_k_m |
| --- | ---: | ---: |
| success / total | 22 / 22 | 21 / 22 |
| success rate | 100.0% | 95.5% |
| avg elapsed_ms | 29770.86 | 29710.55 |
| avg tok/s | 42.20 | 44.21 |
| avg prompt_tokens | 4052.86 | 4227.57 |
| avg content_length | 1841.55 | 2241.95 |
| avg reasoning_length | 2588.32 | 1954.18 |
| rubric total score | 244 | 230 |
| rubric avg score | 11.09 | 10.45 |
| rubric pass count | 14 | 15 |

## Fresh 262K Extreme

| Metric | 27b_ud_q4_xl | 27b_claude46_distilled_v2_q4_k_m |
| --- | ---: | ---: |
| success / total | 2 / 4 | 3 / 4 |
| success rate | 50.0% | 75.0% |
| avg elapsed_ms | 246500.86 | 228609.78 |
| avg tok/s | 26.48 | 27.12 |
| avg prompt_tokens | 194563.00 | 196202.00 |
| avg content_length | 0.00 | 3808.50 |
| avg reasoning_length | 3690.50 | 581.00 |

## Fresh Agentic

| Metric | 27b_ud_q4_xl | 27b_claude46_distilled_v2_q4_k_m |
| --- | ---: | ---: |
| first request success | 4 / 4 | 4 / 4 |
| first JSON parse success | 1 / 4 | 1 / 4 |
| first validation success | 1 / 4 | 1 / 4 |
| best-of-2 validation success | 2 / 4 | 1 / 4 |

## Historical Reference

- old v1 64K report: `output/model-compare-v2/20260308-130031/64k/summary/compare_report.md`
- old v1 262K report: `output/model-compare-v2/20260308-130031/262k/summary/compare_report.md`
- old v1 agentic report: `output/model-compare-agentic/20260308-232041/summary/agentic_compare_report.md`

## Recommendation

不建议仅凭这轮结果直接替换默认 27B coding 基线；需要把 fresh v2 结果与旧版 v1 历史报告一起看。
