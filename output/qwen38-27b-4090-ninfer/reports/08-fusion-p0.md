# Fusion P0 实测报告

thinking=off。基线 n=3 / 221184 / rk4v4-e8：4k/64k/120k/184k decode **117 / 98 / 102 / 87.5** t/s。
A1 已结论：默认 draft=3；n=5 有害。本档验证 A2 262k、A2b L3、A3 rk2v4-e8。

## HTTP 阶梯

| 档 | 4k t/s | 64k | 120k | 184k | 184k TTFT | 184k 针 | 4k 针 |
|---|---:|---:|---:|---:|---:|---|---|
| `ninfer-c262k-l16144` | 111.8 | 110.8 | 110.0 | 87.2 | 93.8 | Y | Y |
| `ninfer-c262k-l3` | 122.8 | 102.6 | 104.1 | 93.0 | 94.6 | Y | Y |
| `ninfer-d4` | 100.9 | 101.4 | 96.1 | 94.1 | 94.0 | Y | Y |
| `ninfer-d5` | 112.3 | 104.1 | 93.1 | 76.4 | 94.6 | Y | Y |
| `ninfer-rk2-c262k` | 108.8 | 98.1 | 92.2 | 88.3 | 110.4 | Y | Y |

## cache-append

| 档 | cold TTFT | exact TTFT | append TTFT | cold cached | exact cached |
|---|---:|---:|---:|---:|---:|
| `ninfer-c262k-l16144` | 40.1 | 0.6 | 3.3 | - | 99697 |
| `ninfer-c262k-l3` | 40.4 | 0.5 | 3.3 | - | 99697 |
| `ninfer-c262k-l3-restart` | 39.7 | 0.6 | 3.3 | - | 99697 |
| `ninfer-d4` | 40.1 | 0.5 | 3.4 | - | 99697 |
| `ninfer-d5` | 40.5 | 0.5 | 3.4 | - | 99697 |
| `ninfer-rk2-c262k` | 45.0 | 0.5 | 3.9 | - | 99697 |

## Java 三题

- `ninfer-c262k-l16144`: 3/3 pass, p50=26s; java-agent-1-idempotency pi=0 v=0 38s, java-agent-2-retry-contract pi=0 v=0 24s, java-agent-3-reconnect-loop pi=0 v=0 26s
- `ninfer-rk2-c262k`: 2/3 pass, p50=25s; java-agent-1-idempotency pi=0 v=0 38s, java-agent-2-retry-contract pi=0 v=0 25s, java-agent-3-reconnect-loop pi=0 v=1 3s

## 对照与结论门槛

- 184k decode 不低于基线 87.5 的 95%（**83.1** t/s）才算 A2 速度过关。
- 184k decode < 80 或针失败 → 该档作废。
- A3 还要求 Java 3/3。
- P1 cherry-pick（E8 bfi、draft-head MMA、auto-long-anchors）本轮不重建镜像。

原始 JSON：`output/qwen38-4090-compare/results/fusion/`.

