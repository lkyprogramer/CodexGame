# CFG-KVGROW（v2 O44）：`STRATA_KV_GROW=1`（2026-10-26）

**结论：未过门，不采用。** 收益集中在中短上下文，长上下文基本没有：
- 回答段 1.032 [1.017, 1.051]，过门；
- 思考段 1.013 [0.991, 1.044]，CI 跨 1。思考约占单会话生成量的 2/3，是主要负载；
- 长 decode 逐档：32K +8.5%，65K 持平，123K −0.6%。

原因是机制本身：K/V 按实际用到的 cell 占显存，上下文越长，交还给 K/V 的专家槽越多。到 114K 时，K/V 已占 1.47 GiB，几乎全部还回去了。

你的单会话从约 10K 一路涨到 128K，大约一半轮次在 64K 以上，所以 KVGROW 平均下来约 +1～2%。

它的优点是**没有 prefill 代价**：冷读 4K～123K 的 TTFT 为 0.969～1.003。如果将来 CFG-KVRES 因为追问读入的代价被否，KVGROW 可以作为低风险的备选，但收益低于 3% 的门。

## 1. 设置

| 项 | 值 |
|---|---|
| campaign | `pr-0-20261026-132026`（13:20～14:30 EDT），COMPLETE，final audit PASS，`engine_unmatched` 空，`not_comparable` 0 |
| base | A0 + EXACT6，生产归一化配置（K/V 全驻显存，9420 个专家槽） |
| cfg | `--env STRATA_KV_GROW=1`（等同 `--kv-grow`；与 `--kv-resident` 互斥；要求单卡、有 `--expert-profile`、arena 模式，29 都满足） |
| cfg 启动回执 | `elastic K/V: 16384 of 131072 cells in VRAM (0.25 of 1.68 GiB)`；`expert cache 10296 slots, 16.69 GiB of VRAM` |
| 运行中的增长 / 交还 | 例如 `K/V grown to 114688 cells (1.47 GiB); the expert cache gave 309 slots for it, 98 hotter experts moved to colder ...`；遇到短上下文请求时 `K/V trimmed to 8192 cells; 755 slots back to the expert cache, refilled from the profile` |
| 题集 / 轮次 | `spec-42114a627786`，5 轮配对，与 CFG-ADAPT、CFG-KVRES 相同 |

## 2. 结果

### 2.1 配对 decode tok/s（cfg / base）

| 组 | n | 中位 [95% CI] | 组内总 tok/s（base → cfg） |
|---|---:|---|---|
| spec-think | 40 | 1.013 [0.991, 1.044] | 136.70 → 138.90（+1.6%） |
| spec-answer | 40 | **1.032 [1.017, 1.051]** | 146.90 → 152.43（+3.8%） |
| long-decode | 20 | 1.022 [0.994, 1.059] | 188.29 → 194.09（+3.1%） |
| decode（短） | 15 | 1.027 [0.997, 1.062] | 148.28 → 148.76（+0.3%） |

长 decode 逐档：

| 上下文 | 中位 [95% CI] |
|---|---|
| 4K | 1.047 [0.951, 1.212] |
| 32K | **1.085 [1.053, 1.106]** |
| 65K | 1.004 [0.923, 1.065] |
| 123K | 0.994 [0.972, 1.006] |

### 2.2 窗口构成

| arm | ms / 窗口 | CPU 专家条目 / 层窗口 | swap / 窗口 | 槽位 |
|---|---:|---:|---:|---:|
| base | 17.512 | 1.999 | 18.6 | 9420 |
| cfg | 17.120（−2.2%） | 1.843（−7.8%） | 17.8 | 10296（初始） |

分组：
- 思考段窗口 15.25 → 14.91 ms：CPU 专家 −0.34 ms，等 GPU 不变。没有 KV 流式，所以没有 CFG-KVRES 那样多出来的 GPU 等待。
- 回答段 19.25 → 18.87 ms。
- 长 decode 17.70 → 17.23 ms。

### 2.3 冷读 TTFT（long-decode 题的首次读入，中位，配对比）

| 上下文 | base | cfg | 比 |
|---|---:|---:|---:|
| 4K | 2.94 s | 2.84 s | 0.969 |
| 32K | 11.01 s | 10.73 s | 0.973 |
| 65K | 21.70 s | 21.34 s | 0.987 |
| 123K | 41.00 s | 41.12 s | 1.003 |

## 3. 与 CFG-KVRES 对比

| 项 | CFG-KVRES（`--kv-resident 20480`） | CFG-KVGROW |
|---|---|---|
| 专家槽 | 固定 10290 | 初始 10296，随上下文交还；114K 时基本还完 |
| decode | 四组 +2.8%～+4.4%，CI 都在 1 以上；65K / 123K 仍 +3% | 思考段 +1.3%（CI 跨 1），回答段 +3.2%；≥65K 无收益 |
| 冷读 | 32K～123K 慢 8～13% | 持平 |
| 追问读入 | 补测中 | 未测（无 KV 流式，预计无代价，推断） |
| 内存 | 多 1.55 GiB pinned RAM | 不变 |

## 4. 数据

- 29 `workspace/results/pr-0-20261026-132026/`。
- 脚本：`workspace/o09/kvgrow.sh`；统计：`tools/analysis/spec_analyze.py`、`tools/analysis/adapt_cost.py`。
