# Qwen3.5-27B vs Qwen3.6-27B 128K Coding/Agentic Evaluation

- Generated at (UTC): `2026-04-23T04:26:37.293370+00:00`
- Baseline: `Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Qwen3.6-27B-UD-Q5_K_XL`
- Output root: `/Users/luo/Documents/github/CodexGame/output/qwen35-27b-vs-qwen36-27b-q5xl-128k/20260423-113141`

## Smoke

### Qwen3.5-27B-UD-Q4_K_XL

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
| 128k_short_no_think | 200 | True | 5 | 0 |
| 128k_20k_no_think | 200 | True | 5 | 0 |
| 128k_short_thinking | 200 | True | 0 | 393 |

### Qwen3.6-27B-UD-Q5_K_XL

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
| 128k_short_no_think | 200 | True | 5 | 0 |
| 128k_20k_no_think | 200 | True | 5 | 0 |
| 128k_short_thinking | 200 | True | 0 | 386 |

## 128K Coding

| Metric | Qwen3.5-27B-UD-Q4_K_XL | Qwen3.6-27B-UD-Q5_K_XL |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 24657.87 | 27675.82 |
| avg tok/s | 42.27 | 38.42 |
| avg prompt_tokens | 4054.86 | 4054.86 |
| avg content chars | 3736.86 | 3949.09 |

## 128K Agentic

| Metric | Qwen3.5-27B-UD-Q4_K_XL | Qwen3.6-27B-UD-Q5_K_XL |
| --- | ---: | ---: |
| first validation success | 7 / 8 | 7 / 8 |
| best validation success | 7 / 8 | 7 / 8 |
| first JSON parse success | 8 / 8 | 8 / 8 |
| best JSON parse success | 8 / 8 | 8 / 8 |
| avg elapsed_ms | 11117.34 | 12823.83 |
| avg tok/s | 42.80 | 38.86 |

## GPU Snapshot

| Phase | Model | Avg mem MiB | Max mem MiB | Avg GPU % | Max GPU % |
| --- | --- | ---: | ---: | ---: | ---: |
| coding | Qwen3.5-27B-UD-Q4_K_XL | 19928.89 | 19958 | 81.38 | 100 |
| coding | Qwen3.6-27B-UD-Q5_K_XL | 22063.62 | 22092 | 82.97 | 100 |
| agentic | Qwen3.5-27B-UD-Q4_K_XL | 19865.43 | 19868 | 65.74 | 95 |
| agentic | Qwen3.6-27B-UD-Q5_K_XL | 22000.29 | 22002 | 66.70 | 95 |

## Manual Review Artifacts

- `summary/coding_score_packet.md`
- `summary/coding_score_packet.json`
- `summary/coding_manual_rubric_template.json`
- `summary/agentic_score_packet.md`
- `summary/agentic_score_packet.json`
- `summary/agentic_manual_rubric_template.json`

## Manual Quality Summary

人工复核结果见 `summary/manual_quality_report.md` 和 `summary/manual_quality_scores.json`。综合 coding + agentic 任务质量，Qwen3.5 得分 `254.5/300`，Qwen3.6 得分 `248.8/300`。结论：**Qwen3.5-27B-UD-Q4_K_XL 略优，暂不建议把 Qwen3.6-27B-UD-Q5_K_XL 替换为默认 coding/agentic executor**。
