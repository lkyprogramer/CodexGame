# Nemotron Thinking Specialized Report

- Generated at (UTC): `2026-03-26T03:07:39.637395+00:00`
- Baseline: `bench/nemotron-iq4-xs-think-parser-control`
- Candidate: `bench/nemotron-iq4-xs-think`

## Aggregate

| Metric | bench/nemotron-iq4-xs-think-parser-control | bench/nemotron-iq4-xs-think |
| --- | ---: | ---: |
| success / total | 3 / 3 | 9 / 9 |
| avg elapsed_ms | 24749.59 | 23205.54 |
| avg predicted_per_second | 171.00 | 175.64 |
| avg content_length | 5770.67 | 5846.89 |

## Family Aggregate

### bench/nemotron-iq4-xs-think-parser-control

| Family | success | avg ms | avg tok/s | avg content len |
| --- | ---: | ---: | ---: | ---: |
| longctx | 1/1 | 28766.21 | 142.57 | 6176.00 |
| multi_round | 1/1 | 33806.05 | 176.30 | 4673.00 |
| planning | 1/1 | 11676.51 | 194.14 | 6463.00 |

### bench/nemotron-iq4-xs-think

| Family | success | avg ms | avg tok/s | avg content len |
| --- | ---: | ---: | ---: | ---: |
| longctx | 3/3 | 30503.45 | 139.76 | 6535.00 |
| multi_round | 3/3 | 28329.60 | 187.95 | 4670.67 |
| planning | 3/3 | 10783.57 | 199.22 | 6335.00 |

## Per Task Snapshot

| Task | Family | bench/nemotron-iq4-xs-think-parser-control ms | bench/nemotron-iq4-xs-think-parser-control tok/s | bench/nemotron-iq4-xs-think-parser-control content | bench/nemotron-iq4-xs-think ms | bench/nemotron-iq4-xs-think tok/s | bench/nemotron-iq4-xs-think content |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| longctx_java_change_impact | longctx | - | - | - | 31811.25 | 137.82 | 6427.00 |
| longctx_metrics_contract | longctx | - | - | - | 31015.80 | 138.85 | 6669.00 |
| longctx_restore_bootstrap | longctx | 28766.21 | 142.57 | 6176.00 | 28683.30 | 142.61 | 6509.00 |
| multi_outbox_self_repair | multi_round | - | - | - | 18469.14 | 211.17 | 4905.00 |
| multi_reconnect_self_repair | multi_round | - | - | - | 32981.76 | 176.50 | 4857.00 |
| multi_restore_self_repair | multi_round | 33806.05 | 176.30 | 4673.00 | 33537.92 | 176.16 | 4250.00 |
| plan_boot_restore_gap | planning | - | - | - | 10388.81 | 201.35 | 6314.00 |
| plan_metrics_exposure | planning | 11676.51 | 194.14 | 6463.00 | 11820.17 | 193.99 | 6378.00 |
| plan_reconnect_fault_injection | planning | - | - | - | 10141.74 | 202.32 | 6313.00 |
