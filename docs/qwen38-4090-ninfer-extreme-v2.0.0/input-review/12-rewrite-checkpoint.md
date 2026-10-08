# OpenClaw rewrite / turn-checkpoints 8

镜像 `44a2c6c`。A 无 ring，B `--turn-checkpoints 8`。测完应已 restore 现网。

## A baseline

| tag | prompt | reused | % | path | TTFT | draft acc | cache_source |
|---|---:|---:|---:|---|---:|---|---|
| A-warm | 60272 | 60254 | 100.0 | restore_user_turn_anchor | 0.895 | 24/22 | l1 |
| A-T1-append | 60551 | 60270 | 99.5 | restore_turn_checkpoint | 1.07 | 36/18 | l1 |

## B checkpoints=8

| tag | prompt | reused | % | path | TTFT | draft acc | cache_source |
|---|---:|---:|---:|---|---:|---|---|
| B-warm | 60272 | 0 | 0.0 | full_reset | 21.153 | 29/21 | none |
| B-T1-append | 60551 | 60270 | 99.5 | restore_turn_checkpoint | 1.12 | 41/17 | l1 |
| B-T2-newest-user | 60291 | 0 | 0.0 | full_reset | 21.03 | 25/22 | none |
| B-T3-recent-2 | 59374 | 0 | 0.0 | full_reset | 20.839 | 25/22 | none |
| B-T4-early | 59402 | 0 | 0.0 | full_reset | 21.104 | 35/19 | none |
| B-T5-recent-5 | 56135 | 0 | 0.0 | full_reset | 19.892 | 24/22 | none |

## B gates

- **T1 append：PASS**（A/B 都是 99.5%，TTFT ~1.1s，path=`restore_turn_checkpoint`，L1）。
- **Newest-user 干净探针：PASS，而且不需要 `--turn-checkpoints 8`。**  
  A-warm 把最后一条 user 从 calibrate 改成任务句：`restore_user_turn_anchor` **100%**，TTFT **0.90s**，L1。
- **B-T2/T3 形式门 FAIL**（reuse 0，`full_reset`，TTFT ~21s）。这两发是在 **同一 slot 上紧接 T1 之后的旁路 rewind**。T1 只比 warm 多 ~281 token，ring 的 4096 合并会把 warm 的 user-anchor 折进 T1 检查点，再回到「warm+reminder」就变成 cold。这是测试串行方式的问题，不能据此说 `restore_user_turn_anchor` 无效。
- T4/T5 `full_reset`：允许失败。
- **不要因为 B-T2 串行结果去移植 auto-long-anchor。** 干净 newest-user 已经走引擎自带的 user-turn anchor。Checkpoint 8 对「T1 之后再 rewind 到另一条近史分支」没有救回来；若 OpenClaw 是 append / 只改最新 user 且中间没有另一条更长分支，现网 rolling-tool + user-anchor 已经够。

## 结论（给现网）

- 生产 **先不要改** `--turn-checkpoints 8`（未证明对 T2 串行 rewind 有收益；干净 T2 不需要它）。
- 生产 **可以加** `--request-log-jsonl`（本轮 JSONL 字段齐，P0 成立）。需你批准再改 `production-18343.sh`。
- auto-long-anchor：**不必作为下一优先级**，除非真实 OpenClaw 抓到「改根 user / 中间 40k 以前」且 path 一直是 `full_reset`。

## C soak Java

- 3/3 pass; java-agent-1-idempotency 32s, java-agent-2-retry-contract 21s, java-agent-3-reconnect-loop 31s

## D rk8v4 200192

- 184k decode=**103.7 t/s** TTFT=92.2s 针中（rk4 medium 对照 98.5 t/s / 94s）
- 4k/64k/120k：145 / 129 / 117 t/s，针全中
- Java 3/3（上一轮 soak 同镜像）
- **不淘汰**：速度未掉 >10%，针+Java 过。代价是窗口 200192 vs 现网 262144。不当默认。
