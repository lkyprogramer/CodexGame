# Nemotron Thinking Specialized Report

- Generated at (UTC): `2026-03-26T03:05:53.248500+00:00`
- Baseline: `bench/nemotron-iq4-xs-no-think`
- Candidate: `bench/nemotron-iq4-xs-think`

## Aggregate

| Metric | bench/nemotron-iq4-xs-no-think | bench/nemotron-iq4-xs-think |
| --- | ---: | ---: |
| success / total | 9 / 9 | 9 / 9 |
| avg elapsed_ms | 22855.60 | 23205.54 |
| avg predicted_per_second | 175.74 | 175.64 |
| avg content_length | 5175.00 | 5846.89 |

## Family Aggregate

### bench/nemotron-iq4-xs-no-think

| Family | success | avg ms | avg tok/s | avg content len |
| --- | ---: | ---: | ---: | ---: |
| longctx | 3/3 | 30401.69 | 140.16 | 5783.33 |
| multi_round | 3/3 | 27560.00 | 187.79 | 4080.00 |
| planning | 3/3 | 10605.11 | 199.29 | 5661.67 |

### bench/nemotron-iq4-xs-think

| Family | success | avg ms | avg tok/s | avg content len |
| --- | ---: | ---: | ---: | ---: |
| longctx | 3/3 | 30503.45 | 139.76 | 6535.00 |
| multi_round | 3/3 | 28329.60 | 187.95 | 4670.67 |
| planning | 3/3 | 10783.57 | 199.22 | 6335.00 |

## Per Task Snapshot

| Task | Family | bench/nemotron-iq4-xs-no-think ms | bench/nemotron-iq4-xs-no-think tok/s | bench/nemotron-iq4-xs-no-think content | bench/nemotron-iq4-xs-think ms | bench/nemotron-iq4-xs-think tok/s | bench/nemotron-iq4-xs-think content |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| longctx_java_change_impact | longctx | 31781.65 | 138.16 | 5879.00 | 31811.25 | 137.82 | 6427.00 |
| longctx_metrics_contract | longctx | 30969.36 | 139.30 | 5847.00 | 31015.80 | 138.85 | 6669.00 |
| longctx_restore_bootstrap | longctx | 28454.05 | 143.02 | 5624.00 | 28683.30 | 142.61 | 6509.00 |
| multi_outbox_self_repair | multi_round | 16897.25 | 211.23 | 4243.00 | 18469.14 | 211.17 | 4905.00 |
| multi_reconnect_self_repair | multi_round | 32510.44 | 175.95 | 4023.00 | 32981.76 | 176.50 | 4857.00 |
| multi_restore_self_repair | multi_round | 33272.32 | 176.17 | 3974.00 | 33537.92 | 176.16 | 4250.00 |
| plan_boot_restore_gap | planning | 10334.51 | 201.51 | 5508.00 | 10388.81 | 201.35 | 6314.00 |
| plan_metrics_exposure | planning | 11497.62 | 194.20 | 5680.00 | 11820.17 | 193.99 | 6378.00 |
| plan_reconnect_fault_injection | planning | 9983.22 | 202.17 | 5797.00 | 10141.74 | 202.32 | 6313.00 |
