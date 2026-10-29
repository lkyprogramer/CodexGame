# NP-RES：CPU / PCIe 分担（CFG-PCIEFRAC、`STRATA_PCIE_BALANCE`）与驻留方向（O07 / O08 / O09）（2026-10-26）

**结论：NP-RES 的零代码部分记 NO_BENEFIT，不采用任何配置；代码部分（O07 / O08）按分析判断不立项。** 本机 decode 对 CPU / PCIe 分担不敏感，最优点附近很平。

- **固定 `--pcie-frac 0.30`（已观察）：** 比 PcieAuto 快 0.3～4.2%，只有贪心 decode 组（15 对）的 CI 下限超过 1；采样负载 +0.9～1.8%。未达 3% 采用门。
- **`STRATA_PCIE_BALANCE=1`（已观察）：** 上游自带的“按实测 CPU / GPU 成本选每层 PCIe 数”模型，已含 PCIe 读挤占 DDR 的项。它把实际经 PCIe 读的 miss 从 8.2% 提到 22.3%（2.7 倍），每窗口 CPU 专家时间降 7～11%。但 GPU-reach 等待同时升 2～5%，窗口总时间只降 0.6～1.3%，组总量 0～+2.1%。
- **为什么平（推论）：**
  - 小幅分担（pcie030，实际份额 10.2% → 14.6%）时 GPU 等待几乎不变，但 CPU 专家时间只在贪心 decode 组降了 0.58 ms，其余组 ≤0.18 ms 或略升。
  - 大幅分担（pciebal，8.2% → 22.3%）时 CPU 少算的时间大半被 GPU 多等 PCIe 的时间抵掉。
  - NP-3 trace 里“PCIe 读让 CPU miss 变贵”的效应是真的，但 PcieAuto 偏保守（实际 PCIe 份额远低于名义值，见第 3 节）只损失 1～2%。
- **O08（逐 expert 三路成本调度）：** `STRATA_PCIE_BALANCE` 已经是它的逐层版本，含 v2 计划要求的 DDR / PCIe 争用项，实测 ≤2%。逐 expert 细化只能再调同层内哪几个 expert 走 PCIe，expert 大小相差在 ±30% 内，预计不足 1%。不立项（推论）。
- **O07（按省时 / 字节选驻留）：** 本机 10 种格式组合的 CPU 成本按字节几乎一致（28.3～34.2 µs/MB，±10%），PCIe 成本也与字节成正比。所以现有“按 profile 频率从高到低、slot 按字节”的装入顺序，已经近似“按省时 / 字节”排序，只在边缘有 ±10% 的重排空间。decode 命中率已达 92.7～93.5%。分析判断收益 <1%，未做离线模拟，不立项。
- **O09（overlap / async 治理）：** `STRATA_ADAPT_OVERLAP=1` 自 0.1.43.1 起已在生产（当时 +12%）。blocking / async 单因素未测，未做。

## 1. 设置

| 项 | pcie030 | pciebal |
|---|---|---|
| campaign | `pr-0-20261026-042813`（04:28～05:39 EDT） | `pr-0-20261026-053915`（05:39～06:50 EDT） |
| 状态 | COMPLETE，5 轮，AB / BA 交替 | COMPLETE，final audit PASS，5 轮 |
| base | A0 + EXACT6（PcieAuto：探测 0.34 起，serve 中按 `link / (link + 1.85 × pool 速度)` 调整） | 同左 |
| cfg | `--arg=--pcie-frac=0.30` | `--env STRATA_PCIE_BALANCE=1` |
| 题集 | `spec-42114a627786.json`（与 CFG-SPEC-S 同：spec-think / spec-answer / 贪心 decode / long-decode 4K～123K） | 同左 |
| 分析 | `tools/analysis/spec_analyze.py`；实际 PCIe 份额从每次请求的 `decode expert cache hit rate … N more read by the GPU over PCIe` 行累加 | 同左 |

**生效回执：**

- **pcie030（已观察）：**
  - cfg arm 没有任何 `PCIe share` 调整行，说明固定值生效。
  - base 的 10 个引擎寿命里，PcieAuto 停在 0.30（4 次）、0.25（4 次）、0.20（2 次）。
  - 所以这一组实际是“固定 0.30”对“0.20～0.30 随运行变化”。此前包内写的“收敛到 0.20”不准确，已改。
- **pciebal（已观察 + 源码）：**
  - serve 模式没有打印 balance 模型的行。`pcie model` 行只在 generate 模式结束时打印（A0 `src/program/generate.cpp:16824`）。
  - 条件 `pcie_balance()` 是：未给 `--pcie-frac`、native pack、单 GPU、`o.batch <= 0`，本配置满足；serve 中在 `n_stages == 1` 时调用 `ver.set_pcie_balance`（`generate.cpp:9165`）。
  - cfg 仍有 `PCIe share` 调整行，这是正常的。`PcieModel::pick` 在两个拟合都有足够样本之前沿用这个份额，之后才改用模型（`include/strata/core/expert_source.hpp:398-482`）。
  - 行为回执：cfg 实际经 PCIe 读的 miss 份额是 base 的 2.7 倍（第 3 节），且每窗口 CPU 专家时间下降，说明模型在工作。

## 2. 结果

成对比值 = cfg / base 的 decode tok/s，同题同轮配对，CI 为中位数 bootstrap 95%。

| 组 | pcie030 对数 | pcie030 中位数 [CI] | pciebal 对数 | pciebal 中位数 [CI] |
|---|---:|---|---:|---|
| spec-think | 40 | 1.021 [1.001, 1.034] | 40 | 1.009 [0.988, 1.018] |
| spec-answer | 40 | 1.003 [0.983, 1.026] | 39 | 1.019 [1.010, 1.032] |
| decode（贪心） | 15 | 1.042 [1.008, 1.100] | 15 | 1.012 [0.961, 1.041] |
| long-decode（贪心） | 20 | 1.009 [0.995, 1.020] | 20 | 1.006 [0.973, 1.011] |

pciebal 的 spec-answer 少一对：`spec-answer-t0-a` 有一轮不可比（`not_comparable 1`）。

组总量（总生成 token / 总 decode 时间，tok/s）：

| 组 | pcie030 base → cfg | pciebal base → cfg |
|---|---|---|
| spec-think | 134.51 → 136.87（+1.8%） | 134.80 → 135.25（+0.3%） |
| spec-answer | 146.40 → 147.68（+0.9%） | 143.86 → 146.95（+2.1%） |
| decode | 145.74 → 151.49（+3.9%） | 146.12 → 146.10（0.0%） |
| long-decode | 187.04 → 189.08（+1.1%） | 189.79 → 189.72（0.0%） |

引擎计时（ms/窗口，按窗口加权）：

| 组 | arm | 窗口 | CPU 专家 | GPU-reach 等待 |
|---|---|---:|---:|---:|
| decode | pcie030 base → cfg | 16.61 → 16.03 | 5.38 → 4.80 | 8.40 → 8.43 |
| decode | pciebal base → cfg | 16.82 → 16.60 | 5.62 → 5.05 | 8.36 → 8.66 |
| long-decode | pcie030 base → cfg | 17.85 → 17.70 | 5.27 → 5.09 | 9.32 → 9.35 |
| long-decode | pciebal base → cfg | 17.70 → 17.60 | 5.11 → 4.75 | 9.34 → 9.56 |
| spec-think 思考段 | pcie030 base → cfg | 15.10 → 15.33 | 4.09 → 4.27 | 8.41 → 8.42 |
| spec-think 思考段 | pciebal base → cfg | 15.41 → 15.29 | 4.41 → 4.05 | 8.38 → 8.60 |
| spec-answer（全部） | pcie030 base → cfg | 19.58 → 19.48 | 7.71 → 7.58 | 8.63 → 8.66 |
| spec-answer（全部） | pciebal base → cfg | 19.61 → 19.48 | 7.78 → 7.17 | 8.61 → 9.02 |

pcie030 的 spec-think 思考段每窗口提交 token 从 2.01 升到 2.08（采样差异），所以它的窗口时间略升而 tok/s 仍 +1.8%。

## 3. 名义份额与实际份额

只统计 miss 不少于 1000 的 decode 请求，每组 195 次。

| campaign | arm | 经 PCIe 读 / miss |
|---|---|---:|
| pcie030 | base（PcieAuto 0.20～0.30） | 10.2% |
| pcie030 | cfg（固定 0.30） | 14.6% |
| pciebal | base（PcieAuto） | 8.2% |
| pciebal | cfg（balance 模型） | 22.3% |

- **已观察：** 实际份额远低于名义份额。固定 0.30 时只有 14.6% 的 miss 走 PCIe。
- **源码：** 每层的 PCIe 数是 `(nmiss * pcie_num) >> 8`，向下取整（`src/core/expert_source.cpp:4879`）。decode 每层每窗口平均只有约 1.7 个 miss（[#3871 报告](P2-PR3871-20261026.md) 第 4 节），份额 0.30 时 1～3 个 miss 的层都取整为 0。
- **推论：**
  - `STRATA_PCIE_MIN1`（≥2 个 miss 时至少给 PCIe 一个）就是针对这个取整的开关。balance 模型不受份额取整限制，每层自由选 0..nmiss，已经覆盖了这块空间，结果仍 ≤2%。所以 `STRATA_PCIE_MIN1` 不再单独测。
  - 想多拿收益只能靠更大的分担，而分担越大 GPU 侧等待越长。上面两组已经覆盖到 22% 的实际份额，窗口时间变化不到 1.3%。

## 4. 判断

- **CFG-PCIEFRAC：** NO_BENEFIT（低于 3% 门）。贪心 decode 组 +3.9～4.2% 是单组 15 对，CI 下限 1.008，同组在 pciebal 里是 0.0%，且两次 base 的 PcieAuto 停点不同（0.20～0.30）。不能作为采用依据。
- **`STRATA_PCIE_BALANCE=1`：** NO_BENEFIT（低于门）。spec-answer 组 CI 不跨 1（+1.9%），其余组跨 1。它是 opt-in，有 64 层一次的探索翻转，没有足够收益承担额外的行为变化。
- **NP-RES 零代码部分结束。** CPU / PCIe 分担不是本机 decode 的杠杆。

## 5. 代码方向的分析（未实测）

**O07：按“省下的关键路径时间 / 字节”选驻留专家**

- **现状（源码）：** expert cache 是 9420 个按字节分配的 slot（`open_sized`），按 profile 频率从高到低装入（`generate.cpp:6310` 附近 `shrink_to`：“the profile's hottest experts first”）。
- **成本按字节（已观察，[#3871](P2-PR3871-20261026.md) 第 3 节表格，nt=1，16 线程吞吐）：**
  - 每 MB 成本在 28.3 µs（IQ2_S / IQ4_NL）到 34.2 µs（IQ3_S / Q2_0）之间，±10%。
  - PCIe 路径的成本是字节 / 12.3 GB/s ≈ 81 µs/MB，同样与字节成正比。
- **推论：**
  - 背包最优按“频率 × 每字节成本”排序。每字节成本近乎常数时，这等价于按频率排序，也就是现在的做法。
  - 新策略只会在热度边缘、按 ±10% 的成本差重排少量 expert。这些 expert 频率最低，decode 命中率已经是 92.7～93.5%。
  - 预计窗口时间变化 <1%，低于噪声。
- **决定：** 不做 v2 P03-02 要求的离线 trace 模拟。只有 pack 换成每字节成本差异大的混合格式时才重新评估。

**O08：逐 expert 三路成本调度**

- **决定：** 见结论。上游逐层版本（`STRATA_PCIE_BALANCE`）已建模 DDR / PCIe 争用，实测 ≤2%；不立项。

**O09：overlap / async 治理**

- **现状：** overlap 已在生产基线（`STRATA_ADAPT_OVERLAP=1`）。
- **决定：** blocking / async 单因素未测，不在本轮执行。v2 P03-04 要求先记录 `requested / effective / reason` 再分 arm；本轮的分担实验显示 CPU / PCIe 这条资源线最优点很平，预期 O09 的收益同样有限（假设，未验证）。

## 6. 数据

- **29 上：**
  - `workspace/results/pr-0-20261026-042813/`（pcie030）
  - `workspace/results/pr-0-20261026-053915/`（pciebal）
  - 驱动脚本 `workspace/npres/pcie.sh`，日志 `workspace/npres/pcie.log`
- **本节第 3 节的统计：** 用 `decode expert cache hit rate: … (H hits / L lookups); P more read by the GPU over PCIe` 行，按请求累加 P /（L − H），只取 L − H ≥ 1000 的请求。
- **未做：**
  - O07 离线模拟。
  - O09 blocking / async 单因素。
  - `STRATA_PCIE_MIN1` 单独 arm（被 balance arm 覆盖，见第 3 节）。
