# NInfer Pi Java 三题 + tools 环

时间：2026-09-07 11:54–11:58。Pi 本机 `nvm v22.19.0`，thinking off。NInfer `qwen3.8-27b` `:18030` concurrency=1。`verify.sh` 未改。测完 restore WORK。

## 结果（全过）

| 项 | pi | verify | 测试未改 | 改了生产代码 | 耗时 |
|---|---:|---:|---|---|---:|
| HTTP tools 冒烟 | — | `tool_calls` `read_file AGENTS.md` | — | — | ~1s |
| T-tools 环（list/grep/read/verify.sh） | 0 | — | — | 不改代码 | ~20s |
| java-agent-1-idempotency | 0 | **0 PASS OrderServiceTest** | true | true | 46s |
| java-agent-2-retry-contract | 0 | **0 PASS RetryingClientTest** | true | true | 40s |
| java-agent-3-reconnect-loop | 0 | **0 PASS ReconnectCoordinatorTest** | true | true | 28s |

Pi 每轮带 **7 个 tools**，`sha_tools` 全程 `ee4c0b57…`。agent-3 末轮 prompt 已到 **~18k**（日志+多文件），HTTP 200。

## 现网

`openclaw/Qwen3.8-27B-WORK` active，NInfer 容器已删。未切默认。

## 和资格测合在一起

容量（185k 针、110 t/s）+ **Pi Java 三题全过** + **tools 协议/工具环**。仍不是 8 小时会话证明，但是 NInfer 报告里的发布门槛（Java + tools + 200K 真吃进去）本机都有实测。
