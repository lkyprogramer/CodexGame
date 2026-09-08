# Cold-Fusion YMQ-M quality smoke（bench_lane）

2026-09-03 23:11–23:12。200K q4 + MTP n=2，与 WORK 同配方。现网已 restore。

空 content **0/7**。空载 20306 / 3911 MiB。

| 题 | 结果 | decode | MTP accept | 备注 |
|---|---|---:|---:|---|
| S 关思考短码 | 有 `merge_sorted` | 100.8 | 0.94 | 看起来是对的归并 |
| T medium 代码 | 有 `dijkstra`+heapq | 88.5 | 0.70 | reason_len 914 |
| T empty budget | 有正文（InnoDB 隔离级别） | 84.4 | 0.65 | 空预算未掏空 content |
| A_tools | `read_file` `Agents.md` JSON 完整 | 93.3 | 0.83 | finish=tool_calls |
| A_chat | 中文回答 4090 为何不能双 27B | 76.0 | 0.53 | 装不下/offload 变慢，说得通 |
| L 28k 针 | tick/protocol/replay **全中** | 80.2 | 0.81 | |
| L 64k 针 | **全中** | 64.3 | 0.79 | |

对照 buun B0（同 WORK 旗标、另一二进制）：S 91 / T 85 / 28k 针中 / 工具成功。YMQ-M 这条 smoke **不差于、略快**，没有明显胡话或工具截断。

这不是 WorkBuddy 仓库题。只能说明：短码、工具、中文、64k 针在 200K 配置下能用。不能据此替换 WORK 当 coding 主模型。
