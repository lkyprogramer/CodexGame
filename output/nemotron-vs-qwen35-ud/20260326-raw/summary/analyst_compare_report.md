# Nemotron Thinking Specialized Report

- Generated at (UTC): `2026-03-26T04:05:23.556931+00:00`
- Baseline: `bench/nemotron-cascade-2-30b-a3b-iq4_xs-analyst`
- Candidate: `bench/qwen35-35b-a3b-ud-q4_xl-analyst`

## Aggregate

| Metric | bench/nemotron-cascade-2-30b-a3b-iq4_xs-analyst | bench/qwen35-35b-a3b-ud-q4_xl-analyst |
| --- | ---: | ---: |
| success / total | 9 / 9 | 9 / 9 |
| avg elapsed_ms | 22948.69 | 33879.56 |
| avg predicted_per_second | 175.63 | 116.51 |
| avg content_length | 5256.11 | 4930.00 |

## Family Aggregate

### bench/nemotron-cascade-2-30b-a3b-iq4_xs-analyst

| Family | success | avg ms | avg tok/s | avg content len |
| --- | ---: | ---: | ---: | ---: |
| longctx | 3/3 | 30507.68 | 139.86 | 5937.33 |
| multi_round | 3/3 | 27626.26 | 187.89 | 3972.33 |
| planning | 3/3 | 10712.14 | 199.14 | 5858.67 |

### bench/qwen35-35b-a3b-ud-q4_xl-analyst

| Family | success | avg ms | avg tok/s | avg content len |
| --- | ---: | ---: | ---: | ---: |
| longctx | 3/3 | 45081.10 | 94.58 | 5516.67 |
| multi_round | 3/3 | 40075.67 | 123.79 | 3791.33 |
| planning | 3/3 | 16481.92 | 131.16 | 5482.00 |

## Per Task Snapshot

| Task | Family | bench/nemotron-cascade-2-30b-a3b-iq4_xs-analyst ms | bench/nemotron-cascade-2-30b-a3b-iq4_xs-analyst tok/s | bench/nemotron-cascade-2-30b-a3b-iq4_xs-analyst content | bench/qwen35-35b-a3b-ud-q4_xl-analyst ms | bench/qwen35-35b-a3b-ud-q4_xl-analyst tok/s | bench/qwen35-35b-a3b-ud-q4_xl-analyst content |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| longctx_java_change_impact | longctx | 31696.78 | 137.83 | 6164.00 | 48590.56 | 92.76 | 6090.00 |
| longctx_metrics_contract | longctx | 31026.89 | 139.15 | 5822.00 | 43411.08 | 94.23 | 4687.00 |
| longctx_restore_bootstrap | longctx | 28799.36 | 142.59 | 5826.00 | 43241.68 | 96.76 | 5773.00 |
| multi_outbox_self_repair | multi_round | 17158.24 | 211.29 | 4142.00 | 24278.42 | 138.07 | 4239.00 |
| multi_reconnect_self_repair | multi_round | 32573.96 | 176.36 | 3849.00 | 50108.32 | 116.95 | 3703.00 |
| multi_restore_self_repair | multi_round | 33146.58 | 176.03 | 3926.00 | 45840.27 | 116.36 | 3432.00 |
| plan_boot_restore_gap | planning | 10351.74 | 201.38 | 5691.00 | 15013.82 | 132.19 | 5642.00 |
| plan_metrics_exposure | planning | 11806.25 | 193.83 | 6068.00 | 17995.66 | 127.87 | 5085.00 |
| plan_reconnect_fault_injection | planning | 9978.42 | 202.20 | 5817.00 | 16436.28 | 133.41 | 5719.00 |
