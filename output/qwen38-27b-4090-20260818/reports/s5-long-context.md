# S5 长上下文交叉事实

不是 marker 原样返回。prompt 里在 25/50/75% 位置插入 `tick_ms=200`、`protocol=v1`、`replay_dir=data/replay`，要求拼出 product。

| lane | 目标 | 实际 prompt tokens | pass | decode tok/s | 墙钟 |
|---|---:|---:|---|---:|---:|
| 64K q8 | 8K | 6874 | True | 89.3 | 5.5s |
| 64K q8 | 32K | 27144 | True | 78.8 | 14.2s |
| 64K q8 | 56K | 47404 | True | 68.4 | 25.2s |
| 32K f16 | 8K | 6874 | True | 91.5 | 5.4s |
| 32K f16 | 28K | 23759 | True | 93.2 | 12.2s |

- q8 在约 47K 真实交叉题上 **全部做对**。本轮没有复现 mmike87 的“量化 KV 变蠢”，至少在 64K 内、这类事实拼接上没有。
- f16 32K 对照同样全对，decode 略快，显存 19994 MiB。24GB 上 f16 扩不到 100K，只作质量对照。
- 64K q8 工作默认成立。不把 128K 当生产默认（08-17 已证明只剩约 665 MiB）。
