# prepare vs message_count（已有 JSONL，schema 19）

口径：4090 EDT。`prepare` 是 submit 前的 frontend 时间（`request_log.cpp`）。热请求的 prefill/queue 不是 TTFT 的主体。

数据：`ninfer-request.jsonl-2026-09-19`（内容是 9/18）、`*-2026-09-20`（内容是 9/19）、live（9/20 凌晨）。只计 `request_done`。

## 120–160K token，按消息条数

| 日 | message_count | n | prepare p50 |
|---|---|---:|---:|
| 9/18 | <120 | 15 | **2.22 s** |
| 9/18 | 120–249 | 10 | **4.68 s** |
| 9/19 | 120–249 | 34 | 11.4 s |
| 9/19 | ≥250 | 126 | **29.6 s** |
| 9/20 | 120–249 | 35 | 17.0 s |
| 9/20 | ≥250 | 9 | 5.25 s（样本少） |

9/18 ≥120K 全体：prepare p50 **3.58 s**，message_count p50 **164**（最大 236）。  
9/19 同长度档 message_count 中位升到 250+ 后，prepare 到 **30 s**。不是 TTFT 漏记 prepare：两边 JSONL 都有 `timings_seconds.prepare`。

`tool_count` 只有 0 / 1 / 13，几乎不能解释差异。

## 热路径拆分（9/19–9/20，≥120K 且命中≥90%，n=374）

| | p50 |
|---|---:|
| prefill | 0.32 s |
| queue | 0.003 s |
| prepare | 35 s（185K+ 约 89–117 s） |
| decode | ~99 t/s |

prepare 随 **整段历史长度和消息条数** 涨，不随 `computed_prefill` 涨。

## 还缺的字段

schema 19 没有 render/tokenize 分计，也没有 `content_chars` / `body_bytes` / `rendered_chars`。源码已加上 schema 20 的 `prepare_detail`，需要新镜像才能在线上看到 tokenize 是否占大头。现网镜像仍是 `44a2c6c`，未切换。
