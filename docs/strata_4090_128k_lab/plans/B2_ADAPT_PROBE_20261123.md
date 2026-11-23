# B2 自适应专家层与起点 profile 探针 · 预登记（2026-11-23）

状态：**已预登记，未运行**。机器可读版本：[B2_ADAPT_PROBE_20261123.prereg.json](B2_ADAPT_PROBE_20261123.prereg.json)，4090 上冻结为 `/data/strata-data/upgrade-gate/b2-adapt-20261123/PREREG.json`（只读，sha256 `9328aa97…`）。运行用 [upgrade_gate.py](../tools/upgrade_gate/README.md) 的 `probe` 命令。

## 问题

不换版本、不加内存，只改 B2 生产树的引擎参数，能否让 decode 每个窗口更便宜？

依据：
- decode 每个窗口 ≈ GPU 约 8 ms + CPU 专家时间（受约 36 GB/s 内存带宽限制）+ 草稿约 1.4 ms。
- v0.2.20 的 #4870 把自适应层改成 every 2 / swaps 192 / decay 0.92。同样 40 题上，每窗口 CPU 条目从 1.26 降到 1.00，但每窗口反而从 14.55 ms 变成 16.22 ms（GPU-reach 8.15 → 8.48 ms，每窗口 swap 12.96 → 20.04）。CPU 侧有空间，代价出在别处。
- v0.2.17 的默认值是 every 4 / swaps 96 / decay 0.70 / min-gain 1.5（`generate.cpp:1037-1073`）。sm_89 上没有启用 `STRATA_SPEC_ADAPT_EVERY` 预热（只对 sm_86 选择性开启）。

## 一个事实更正：生产没有"学到的 profile"

`/home/hhtele/strata-0.2.17/data/expert-profile-iq3xxs-learned.bin` 与静态 profile 逐字节相同（sha256 都是 `8f59b4aa…`）。原因：
- 周期保存只在"距上次保存满 10 分钟后的下一个请求之前"触发，Pi 那批 63 个请求只赶上了第一个请求前的一次，当时还没有任何路由计数；
- `systemctl stop` 用 `KillMode=control-group` 同时给整个 cgroup 发 SIGTERM，引擎来不及做退出保存。gate 驱动只给服务进程组发 SIGTERM，所以 gate 各臂都有退出保存。

所以"用真实流量学到的 profile"现在拿不到。本轮改用存档 b2 臂（305 题）退出时保存的 profile 做**样本内上界**：40 题测速的题目都在它的学习范围内，结果只能用来关闭这个方向，不能据此采用。

## 设计

同一会话依次跑，每臂 40 题（与 v0.2.20 测速相同的前 40 题、seed、提示和判分镜像），臂与臂之间生产会恢复：

| 臂 | 参数 | 目的 |
|---|---|---|
| C0 `b2-control` | 无 | 同会话对照；与存档 b2 前 40 题的差距就是 A-A 噪声 |
| A1 `b2-adaptevery2` | `--adapt-every 2` | swap 轮次加倍（上限和衰减不变）：多搬 |
| A2 `b2-adaptdecay092` | `--adapt-decay 0.92` | 路由计数记得更久，搬运频率不变：选得更准 |
| P1 `b2-expertprofileprofileb2armlearned` | `--expert-profile <b2 臂学到的 profile 快照>` | 起点放置的样本内上界 |
| A12（条件臂） | A1 + A2 | 只在 A1、A2 都有效、都没过门、且各自主指标都改善 ≥2% 时跑 |

命令（在 4090 的 `/data/strata-data/upgrade-gate` 下）：

```bash
P=/home/hhtele/anaconda3/bin/python
$P -B upgrade_gate.py probe b2-adapt-20261123 --limit 40                                  # C0
$P -B upgrade_gate.py probe b2-adapt-20261123 --limit 40 --arg adapt-every=2             # A1
$P -B upgrade_gate.py probe b2-adapt-20261123 --limit 40 --arg adapt-decay=0.92          # A2
$P -B upgrade_gate.py probe b2-adapt-20261123 --limit 40 \
   --arg expert-profile=/data/strata-data/upgrade-gate/b2-adapt-20261123/profile-b2arm-learned.bin   # P1
```

## 指标与判定

- **主指标**：`SMOKE-<arm>.json` 里 `per_window_same_tasks['smoke:<arm>']['all']['ms_win']`，即 40 题全部请求的 decode 每窗口毫秒数，按窗口数加权。它和 prodlog 的"按请求取中位数"不是同一口径，不能与以前报告里的分段表直接比。存档 b2 前 40 题：14.55 ms（<4K 13.91，4K–32K 24.61）。
- **次要指标**：同题端到端 tok/s（存档 b2 为 130.6）、分段每窗口毫秒数；用 GPU-reach、CPU ms、CPU 条目、每窗口 swap、adapt join、overlap 等待来解释机制。
- **文本检查**：每窗口 token 数和接受率只取决于文本，与放置无关（存档 b2 为 1.97 和 0.678）。
- **A-A 噪声**：AA = |C0 主指标 − 14.55| / 14.55。
- **环境停止**：C0 的主指标或端到端速度与存档 b2 相差超过 5%，判 STOP_ENV，不跑其他臂，先查原因。
- **过门**：同时满足三条：
  1. 主指标 ≤ C0 ×（1 − max(4%, 2×AA)）；
  2. 端到端 tok/s 高于 C0；
  3. 每窗口 token 数与 C0 相差不超过 5%（不满足判 INCONCLUSIVE，不算过门）。
- **有效性**：
  - A1：每窗口 swap 至少是 C0 的 1.5 倍，否则说明参数没生效，判 INVALID。
  - A2：引擎能启动，且日志里没有 adapt-decay 越界警告。v0.2.17 会解析这个参数（`generate.cpp:3980`），但 `--help` 里没有列出，工具会给出一条预期内的警告。
  - P1：引擎日志的 profile 行是快照路径。
  - 所有臂：rows 无错误、没有触发守卫；基础设施失败最多重跑一次。
- **质量**：只记录 40 题的通过数，不作判定（40 题判不了非劣）。
- **KL 不跑**：`quant_quality.py` 固定了 `--expert-cache 1 --adapt-every 100000`，看不到放置和自适应层的变化。这些参数只改变某个专家在 GPU 还是 CPU 上算，而生产本来每次运行都在变。

## 结论分支

- **自适应参数**：
  - 过门的臂（A1、A2、A12）中取主指标改善最大的一个进入第二阶段：同一 probe 命令去掉 `--limit`，跑 305 题完整臂（停生产约 2 小时）。
  - 第二阶段要求任务门 NONINFERIORITY_ESTABLISHED（margin 5%，与存档 b2 配对），且整臂 decode tok/s 比 b2 高至少 4%。通过后改生产配置仍需用户确认，并备份、准备回滚。
  - 都不过门：B2 上的自适应参数判 NO_GAIN，不再扫其他取值。
- **起点 profile**：
  - P1 不过门：起点 profile 方向判 NO_HEADROOM（上界都不够）。
  - P1 过门：仍不能采用。下一步要拿到真实流量的样本外 profile，这需要改生产配置（例如缩短 `--expert-profile-save-every`），另行请示。

## 预算与边界

- 每臂停生产约 35–40 分钟（v0.2.20 测速为 39 分钟），C0 到 P1 共约 2.5 小时，条件臂再加 40 分钟。
- 在 Pi 空闲时运行，臂与臂之间生产恢复。
- 不启用 `STRATA_STAGE_PIN` 和 `STRATA_ROUTE_RESIDENT`（工具会拒绝）；不写生产树和 `strata-0.1.43.1`；失败记录全部保留。

## 冻结身份

| 项 | sha256 |
|---|---|
| 引擎 `/home/hhtele/strata-0.2.17/engine/strata` | `df2d006b…` |
| 生产配置（与存档 b2 臂一致，已核对） | `d7ee52b0…` |
| `upgrade_gate.py` | `3a2c5037…` |
| `gate17.py`（冻结驱动） | `517d1689…` |
| 原任务门预登记 | `8159d090…` |
| 存档 b2 rows | `d2c4a7f5…` |
| P1 profile 快照 | `891d7c75…` |
