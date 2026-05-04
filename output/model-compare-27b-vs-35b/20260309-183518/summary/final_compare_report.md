# Qwen 27B vs 35B Executor Compare Report

- Generated at (UTC): `2026-03-09T11:23:30.032098+00:00`
- Baseline: `bench/qwen35-27b-dense-ud-q4_xl`
- Candidate: `bench/qwen35-35b-a3b-ud-q4_xl`

## Shared Service Args

```text
-ngl 99 -c 65536 -np 1 -fa on -ctk q4_0 -ctv q4_0 --temp 0.2 --top-p 0.90 --top-k 20 --min-p 0.0 --reasoning-format none --chat-template-kwargs '{"enable_thinking": false}' --host 0.0.0.0 --port 18343
```

## Coding Round

| Metric | 27b_dense_ud_q4_xl | 35b_a3b_ud_q4_xl |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 27276.88 | 9329.46 |
| avg predicted_per_second | 42.32 | 135.98 |
| rubric total score | 244 | 200 |
| rubric avg score | 11.09 | 9.09 |
| rubric pass count | 14 | 9 |

## Agentic Round

| Metric | 27b_dense_ud_q4_xl | 35b_a3b_ud_q4_xl |
| --- | ---: | ---: |
| first request success | 4 / 4 | 4 / 4 |
| first JSON parse success | 4 / 4 | 4 / 4 |
| first validation success | 4 / 4 | 4 / 4 |
| best-of-2 validation success | 4 / 4 | 4 / 4 |

## Resource Snapshot

| Round / Metric | 27b_dense_ud_q4_xl | 35b_a3b_ud_q4_xl |
| --- | ---: | ---: |
| coding avg memory.used MiB | 18777.90 | 22342.29 |
| coding max memory.used MiB | 18806 | 22356 |
| coding avg gpu util % | 76.36 | 51.07 |
| agentic avg memory.used MiB | 18806.00 | 22357.65 |
| agentic max memory.used MiB | 18806 | 22358 |
| agentic avg gpu util % | 47.08 | 28.20 |

## Task Wins

- 27b_dense_ud_q4_xl wins: `12`
- 35b_a3b_ud_q4_xl wins: `3`
- ties: `7`

## Recommendation

不建议直接替换；35B-A3B 没有在 executor 关键指标上形成足够优势。
