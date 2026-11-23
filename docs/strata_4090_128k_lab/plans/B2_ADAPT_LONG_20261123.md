# B2 长上下文 `--adapt-every 2` 探针 · 预登记（2026-11-23）

状态：**已预登记，未运行**。运行前还要先实现 `replay` 命令（见"运行前提"）。机器可读版本：[B2_ADAPT_LONG_20261123.prereg.json](B2_ADAPT_LONG_20261123.prereg.json)，4090 上冻结为 `/data/strata-data/upgrade-gate/b2-adapt-long-20261123/PREREG.json`（只读，sha256 `28d493d5…`）。

## 问题

[上一轮探针](B2_ADAPT_PROBE_20261123.md)只覆盖 prompt <32K 的门题集，`--adapt-every 2` 在那里整体无收益。但真实 Pi 流量 63 个请求里有 59 个 ≥32K。本轮问的是：在 32K–100K 的 Pi 式工具循环里，`--adapt-every 2` 能不能让 decode 每个窗口便宜 4% 以上？

依据（都是线索，不是证据）：
- 上一轮 4K–32K 段（事后分段，每臂 52–58 个请求）：每窗口 22.40 → 20.16 ms，CPU 条目 3.57 → 2.44。<4K 段没有变化（13.99 → 14.04）。
- [v0.2.16 顺序依赖报告](../reports/V0216-SEQDEP-PCE0-20261120.md)：100K 请求在一次长读入之后，第一段 decode 的 CPU 专家条目会升高（1.75–2.03，对照 1.16）；第二段每窗口 16.4–19.8 ms，主要随 CPU 条目变化。
- 真实 Pi 流量（[v0.2.19 报告](../reports/V0219-UPGRADE-GATE-20261122.md)，按请求取中位数）：≥32K 每窗口 17.0–18.0 ms，CPU 条目 1.57–1.80，高于门题集 <4K 的 1.1。
- 推断的机制：每次读入新内容后，GPU 上的专家集合需要重新适应；自适应层调整得越频繁，回到稳态越快。长会话里每一步都有读入，所以收益可能比门题集大。这只是推断，本轮只测结果，不测机制。

## 工作负载：固定历史的 Pi 式长会话回放

文本来源：[pisim](../reports/V0217-PISIM-20261120.md) 2026-11-20 在 B2 生产上录下的两段会话（公开题目，不含任何真实用户内容）。

- **拼接**：会话 A 的全部消息，后面接会话 B 去掉 system 后的全部消息，成为一条长会话。B 的每道题本来就是以一条新用户消息开头，和 Pi 在同一会话里接着做下一件事的形状一致。
- **请求**：在每条 assistant 消息之前发一次请求，内容是它之前的全部消息，共 120 个（A 71 + B 49）。
  - 请求体：`model`、`messages`、pisim 的四个工具定义、`max_tokens 16384`、`stream false`，与 pisim 发出的一致。
  - 另加 `seed` = 20261123 + 请求序号。即便如此，放置不同也会造成数值差异，文本仍会分叉，所以靠请求数量和文本检查来控制。
- **历史固定**：每个请求的历史都用录下的消息，不用本次生成的回复。各组的 prompt 因此逐字节相同；本次生成的回复只用来测速，然后丢弃。
- **估计分布**（按录制时的 prompt 长度推算）：

  | 段 | 请求数 | 录制时生成 token |
  |---|---|---|
  | <4K | 3 | 2.0K |
  | 4K–32K | 47 | 24.3K |
  | 32K–64K | 22 | 23.5K |
  | ≥64K | 48 | 25.2K |

  最长 prompt 约 102K。前 50 个请求（<32K）作为预热，同时作为次要指标。
- **和 Pi 的差别**（局限）：
  - 历史固定，所以引擎每一步都要把录下的回复重读一遍；Pi 复用的是它自己的回复。每步的读入量因此多出几百到几千 token，和 Pi 读工具输出是同一量级，但不完全相同。
  - pisim 的系统提示只有约 800 token，工具只有 4 个；没有流式，也不经过 NGINX；只有一条会话，不切换会话。

## 设计

每次运行都启动一个全新引擎（停生产，用生产树和生产配置，参数由 `--arg` 改），按顺序发完 120 个请求，然后停引擎、恢复生产。顺序是 ABBA，用来抵消线性漂移：

| 序 | 运行 | 参数 |
|---|---|---|
| 1 | C0a `b2-control` | 无 |
| 2 | L1a `b2-adaptevery2` | `--adapt-every 2` |
| 3 | L1b `b2-adaptevery2` | `--adapt-every 2` |
| 4 | C0b `b2-control` | 无 |

不扫其他取值（every 1、swaps、decay）。本轮只检验那一条线索。

## 指标与判定

- **主指标**：每次运行中 prompt ≥32K 的全部请求（32K–64K 与 ≥64K 合并），decode 每窗口毫秒数，按窗口数加权（`window_stats` 的口径）。每组取两次运行的平均。
- **次要指标**：≥32K 的 decode tok/s（引擎 generated / gen_ms）；分段（32K–64K、≥64K、<32K 预热段）每窗口毫秒数；GPU-reach、CPU ms、CPU 条目、每窗口 swap、adapt join、overlap 等待，用来解释机制。
- **文本检查**：≥32K 的每窗口 token 数和接受率。
- **A-A 噪声**：AA = |C0a − C0b| / mean(C0a, C0b)，按主指标计算。
- **噪声停止**：AA > 5% 判 NOISY。结论为 INCONCLUSIVE，不采用，也不在本预登记下加跑。
- **过门**：同时满足以下四条：
  1. mean(L1) ≤ mean(C0) × (1 − max(4%, 2×AA))；
  2. max(L1a, L1b) < min(C0a, C0b)，即两次 L 运行都比两次 C 运行快；
  3. ≥32K decode tok/s 的 mean(L1) 高于 mean(C0)；
  4. ≥32K 每窗口 token 数 mean(L1)/mean(C0) 与 1 相差不超过 5%，不满足判 INCONCLUSIVE（文本混杂），不算过门。
- **有效性**：
  - L 运行的引擎启动行带 `--adapt-every 2`，C 运行不带；
  - 120 个请求都正常返回，引擎日志里的请求数也是 120，按顺序一一对应；
  - 没有触发资源守卫；
  - 基础设施失败的那次运行最多重跑一次，失败记录保留。
  - 不再用"swap 是否增加"判断参数是否生效。上一轮证明这条规则不成立：换入数受 min-gain 限制，不随轮次加倍。
- **质量**：本轮不判。回放不判分，文本不可比。

## 结论分支

- **过门**：进入第二阶段。
  - 用 `upgrade_gate.py probe b2-adapt-long-20261123 --arg adapt-every=2`（不带 `--limit`）跑 305 题完整臂，停生产约 2 小时。
  - 要求任务门 NONINFERIORITY_ESTABLISHED（margin 5%，与存档 b2 配对），而且整臂 decode tok/s 不比 b2 慢 2% 以上（门题集是短 prompt，这里只要求不变慢）。
  - 都满足后，改生产配置（在 args 里加 `--adapt-every 2`）仍需用户确认，并做备份、准备回滚（恢复原配置文件后 restart）。
  - 改完以后，用 prodlog 观察真实 Pi 的 ≥32K 每窗口毫秒数，这一步只观察，不作判定。
- **不过门**：长上下文下的 `--adapt-every` 也判 NO_GAIN，在防重复台账里关闭。
- **NOISY 或 INCONCLUSIVE**：如实记录，不采用；要重测需要新的预登记，并且要先找到噪声来源。

## 运行前提（本预登记不包含实现）

1. 在 `upgrade_gate.py` 里加 `replay LABEL --run NAME [--arg FLAG[=VALUE]]`，复用现有组件：
   - `production_stopped()`、`apply_arg_specs` 和 `_ArmTree` 改配置；
   - `gate17.start_server/stop_server` 起停引擎，端口 18089，退出时保存 profile；
   - 资源守卫同 gate17 的 arm；
   - 用 `engine_requests` 和 `window_stats` 取每窗口数据。
   - 先用 CPU 单测，再空跑构建：生成 `REPLAY.json`，确认 120 个请求、分段与上表一致。
2. 第一次运行前，把 `replay` 实现的 sha256 和 `REPLAY.json` 的 sha256 写进只读的 `ADDENDUM.json`；之后两者都不得改动。
3. 判定由冻结的评估脚本机械计算，规则和本页相同。
4. 用户同意停生产后，在 Pi 空闲时运行。

## 预算与边界

- 每次运行：引擎启动约 35 s，回放约 15–20 分钟（录制时共生成 75K token，按约 130 tok/s 加上读入时间估计）。4 次共约 70–80 分钟停生产，每次之间生产恢复。
- 不启用 `STRATA_STAGE_PIN` 和 `STRATA_ROUTE_RESIDENT`；不写生产树和 `strata-0.1.43.1`；失败记录全部保留。

## 冻结身份

| 项 | sha256 |
|---|---|
| 引擎 `/home/hhtele/strata-0.2.17/engine/strata` | `df2d006b…` |
| 生产配置（与存档 b2 臂一致） | `d7ee52b0…` |
| `gate17.py`（冻结驱动） | `517d1689…` |
| `upgrade_gate.py`（加 replay 之前） | `3a2c5037…` |
| pisim `run/session-A.json` | `51fb4bc2…` |
| pisim `run/session-B.json` | `9ba0101f…` |
| pisim `pisim.py`（工具定义和请求体的来源） | `14531846…` |
| pisim `run/RESULT.json`（估计分布的来源） | `33ada24d…` |
