# Qwen3.5-27B vs Qwen3.6-27B Evaluation Report

- Generated at (UTC): `2026-04-23T03:16:18.281539+00:00`
- Baseline: `Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `Qwen3.6-27B-UD-Q5_K_XL`
- Output root: `/Users/luo/Documents/github/CodexGame/output/qwen35-27b-vs-qwen36-27b-q5xl/20260423-095434`

## Download And Integrity

| Item | Value |
| --- | --- |
| ModelScope repo | `unsloth/Qwen3.6-27B-GGUF` |
| Candidate file | `Qwen3.6-27B-UD-Q5_K_XL.gguf` |
| Remote path | `/data/models/qwen/Qwen3.6-27B-UD-Q5_K_XL.gguf` |
| Remote size bytes | `20038256864` |
| Remote sha256 | `ac310abf2895aa397121bad6c0be89466af41f0f1606a21c1131b110eeb19d0e` |
| Checksum match | `True` |

## Smoke

### Qwen3.5-27B-UD-Q4_K_XL

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
| 64k_short_no_think | 200 | True | 5 | 0 |
| 64k_20k_no_think | 200 | True | 5 | 0 |
| 64k_short_thinking | 200 | True | 0 | 410 |

### Qwen3.6-27B-UD-Q5_K_XL

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
| 64k_short_no_think | 200 | True | 5 | 0 |
| 64k_20k_no_think | 200 | True | 5 | 0 |
| 64k_short_thinking | 200 | True | 0 | 386 |
| 128k_short_no_think | 200 | True | 5 | 0 |

## 64K Coding

| Metric | Qwen3.5-27B-UD-Q4_K_XL | Qwen3.6-27B-UD-Q5_K_XL |
| --- | ---: | ---: |
| success / total | 22 / 22 | 22 / 22 |
| success rate | 100.0% | 100.0% |
| avg elapsed_ms | 24883.35 | 29023.45 |
| avg tok/s | 42.30 | 38.41 |
| avg prompt_tokens | 4054.86 | 4054.86 |
| avg content chars | 3777.55 | 4158.14 |
| avg reasoning chars | 0.00 | 0.00 |

## 262K Extreme

| Metric | Qwen3.5-27B-UD-Q4_K_XL | Qwen3.6-27B-UD-Q5_K_XL |
| --- | ---: | ---: |
| success / total | 3 / 4 | 0 / 0 |
| success rate | 75.0% | 0.0% |
| avg elapsed_ms | 158489.96 | - |
| avg tok/s | 26.31 | - |
| startup/capacity failure | `-` | `TimeoutError("Timed out waiting for bench/qwen36-27b-ud-q5_xl: ConnectionResetError(54, 'Connection reset by peer')")` |

## Agentic

| Metric | Qwen3.5-27B-UD-Q4_K_XL | Qwen3.6-27B-UD-Q5_K_XL |
| --- | ---: | ---: |
| first validation success | 7 / 8 | 7 / 8 |
| best validation success | 7 / 8 | 7 / 8 |
| first JSON parse success | 8 / 8 | 8 / 8 |
| best JSON parse success | 8 / 8 | 8 / 8 |
| avg elapsed_ms | 12138.92 | 12919.69 |
| avg tok/s | 42.86 | 38.90 |

## GPU Snapshot

| Phase | Model | Avg mem MiB | Max mem MiB | Avg GPU % | Max GPU % |
| --- | --- | ---: | ---: | ---: | ---: |
| 64k | Qwen3.5-27B-UD-Q4_K_XL | 18778.17 | 18806 | 79.54 | 100 |
| 64k | Qwen3.6-27B-UD-Q5_K_XL | 20912.26 | 20940 | 81.60 | 100 |
| 262k | Qwen3.5-27B-UD-Q4_K_XL | 23158.87 | 23276 | 78.61 | 100 |
| 262k | Qwen3.6-27B-UD-Q5_K_XL | - | - | - | - |
| agentic | Qwen3.5-27B-UD-Q4_K_XL | 18713.60 | 18716 | 58.94 | 98 |
| agentic | Qwen3.6-27B-UD-Q5_K_XL | 20848.38 | 20850 | 67.36 | 95 |

## Recommendation

Qwen3.6-27B Q5 XL should not replace the current default until the 262K capacity failure is resolved. Use the 64K and agentic results only as short-context quality evidence.

## Manual Review Artifacts

- `summary/coding_score_packet.md`
- `summary/coding_score_packet.json`
- `summary/coding_manual_rubric_template.json`
