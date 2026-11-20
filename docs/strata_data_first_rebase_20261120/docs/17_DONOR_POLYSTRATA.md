# PolyStrata：先量实际 MoE 行填充，拒绝在 Ada 搬动归约顺序

固定 [PolyStrata `3e16421`](https://github.com/simplexai-labs/PolyStrata/tree/3e1642161198c50ff1abed4046f4e4f476099dbb) = [v0.1.45-poly.10](https://github.com/simplexai-labs/PolyStrata/releases/tag/v0.1.45-poly.10)。本机新基线未绑定，历史 Qwen3.8-Flash-Next GSQ-RCO IQ3_XXS 两分片、Xeon Silver 4216、PCIe Gen3 ×16，不能替成 Tiel/Qwen3.6 或文中 AMD 配置。

## 和当前 Strata 比，不和 fork 祖先比

[官方 GitHub compare](https://api.github.com/repos/Niko1221/Strata/compare/58ee3227720629ff2e41d640165ebe89c880dfef...3e1642161198c50ff1abed4046f4e4f476099dbb)：共同祖先是 `477ac13cbe8e582c20484871ce459d20d82df09d`（2026-10-16 UTC），对 `58ee322` 已是 `diverged`、Poly ahead 685 / behind 5396，不是现行 Strata 的简单子集。GitHub metadata `fork=false` 不否定共享提交历史。
Poly 是双引擎：[README 的引擎归属](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/README.md#L23-L31) 明列 Flash-Next 用 inherited `strata`；Flint/Qwen3.6/Tiel/GLM/DeepSeek 等另用 `strata-poly`。下面 `src/poly` 的性能结果不能算进 Flash-Next。

## #149：分 launch 为了少算填充，收益和位同条件分开

[PR149](https://github.com/simplexai-labs/PolyStrata/pull/149)，[解析台阶和参数](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/src/poly/engine.cpp#L2677-L2703)、[每类边界构造](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/src/poly/engine.cpp#L4374-L4425)、[parity test](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/src/poly/mmq_tiles_test.cu)。

1. 旧版一组 staged experts 把最大的专家排给统一 MMQ tile；其他专家实际 token 行远少，计算中有无贡献的 padding。
2. `STRATA_POLY_STAGED_TILES=8,16,32` 按真实有效行把一轮分成 ≤8、≤16、≤32、>32 四类，每类各发 gate/up 和 down；resident 不改原本自己的分类，unset/invalid 保留单 launch。
3. 著名的 43% 是 AMD case 的“实际路由行 / tile 计算逻辑列”，不是 GPU 全局利用率。某层样本 staged 约214 experts，行数中位 15、最大 463；对该形状若给 16-wide tile，估计填充效率 79%，具体分类还耗额外 launch/队列与 bounds 表。
4. GPU 有没有 stream-k 决定等价性。没有 stream-k 的同实现路径可比到位；有 stream-k 时切分受 launch tile count 影响，改 launch 就可能改浮点相加顺序，不是仅去掉无效行。

| 证据 | 硬件/模型/口径 | 可作何结论 |
|---|---|---|
| 未分类 → `8,16,32` | RX5700XT 8GB gfx1010 Windows，Tiel-Coder-35B-A3B UD-Q4_K_XL / q8_0 KV / 384MiB reserve，18932-token 冷 prompt，各新启引擎两轮 | 246.9/248.5 → 272.8/270.9 prompt tok/s，约 +10%。非 CUDA、非 Flash-Next，且不是 decode |
| 归约反例 | RTX PRO 6000，Qwen3.6 32K，冻专家 placement，256-token answer | 后几位有差异，greedy 在 token 180 分叉；这足以否决直接移植为 4090 exact 机制 |

来源：[条件、读数和负例](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/docs/DETAILS.md#L2515-L2555)。未见该分组实现的 4090 Flash-Next 现行合同对照。不要引用 AMD bitwise 验证为 CUDA guarantee。

### 当前 Strata 已有的边界

- [真实 prefill dispatch](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/prefill/prefill.cpp#L5973-L6146) 已在 staged/resident 选择多种 MMQ/fused 路径；[staged group rule](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/include/strata/prefill/staged_group_rule.hpp) 描述 NVIDIA staged fused group 默认及支持性。
- [fused tile rules](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/include/strata/prefill/fused_tile_rule.hpp) 已按硬件代际、量化、staged/resident 与 expert 行密度做运行路径/尺寸选择。不同 `launch grid → routed logical tiles` 映射也不同；不能一律做 `ceil(rows/64)` 就宣布 padding。
- 历史工作区借用、连续套娃 prefill 参数和 HC 负例仍保持关闭。C02 的问题是“一次实际 launch 的有用/逻辑发射行与时间差”，不是让专家 cache 或临时区再大一点。

## C02：一次有界 census，不提交任何候选 kernel

1. 用现行合同静态记录CUDA build、arch、pack实际quant、kernel/tactic、chunk、staged/resident；优先复用128K总窗内合法长prefill原件（P0锁定输入长度，如约100K）。warm tool suffix仅在既有轨迹或获批CASE支持时纳入；不扫tiles、不加新runtime策略开关。
2. 边界分层 `phase / layer / staging_round / group / class / kernel`，每次记录 router 有效 expert 行分布、实际 `grid / tile_rows / covered logical rows`、extra launches、copy/event ready、GPU kernel duration 与 critical 区间重叠。
3. 在真实 dispatch 的各自模型上算有效/逻辑填充；用关键路径原始 wall 统计给出即使填充完全可消除的端到端上界。小 kernel 的 padding 高不代表请求可见收益；缺实际逻辑 tile 或关键时间字段，明确为不可定价。
4. 比对上游已存在的 tile/fused 规则。如果当前量化已绕过受益 path，或 allocation/CPU/PCIe/attention 才是实际瓶颈，结束。不借 Poly 的数据来填本机空位。

不立项条件：低于 **至少 4% 且超过 2× A/A 噪声** 的门槛；收益已被当前规则覆盖；代价依赖重排 NVIDIA stream-k；或实际日志无法复原真实路径。上界跨门也只是下一轮提出“保留归约顺序”的设计条件，不能自动实现或跑参数矩阵。

### 记账字段与反证

| 组 | 最小字段 | 有用的反证 |
|---|---|---|
| 路径标识 | `model_hash`, `quant`, `phase`, `layer`, `kernel_id`, `tactic`, `staged/resident`, `chunk` | 同一包的层/格式可能有不同 kernel，不能只看全局一个 “MMQ 已开” |
| 逻辑工作 | 有效专家行数统计、拥有这些行的 group、实际 tile/grid、logical covered rows、launch 次数 | shape 上发射行数与其 tile kernel 的处理范围不一致时，不计算伪占用率 |
| 时间 | 进入临界路径起止、GPU overlap、copy/等待、有效墙钟、CPU launch cost | 论证只从 SUM kernel time 得到而总时间没动，不能称机会 |
| 精确性 | 当前累加次序约束、同一 shape 的稳定性、不做候选 patch | 有 stream-k 重排则是 no-go，不能用“只差一点”放宽合同 |

在汇总里分 cold prefill 与 warm continuation。前者可能被搬运和持续大 MMQ 淹没，后者可能走 staged 小块完全不同的路径；用总平均容易同时掩盖两边。
讨论“GPU 能有多快”时，以请求 wall 为分母；若 pad-heavy window 占整个请求 2%，去掉该 window 的全部耗时也过不了性能门，即使里面有 90% 空填充。

## 另外几项不要误归类为 Flash-Next 优化

- [#158 scratch alias](https://github.com/simplexai-labs/PolyStrata/pull/158)，[对齐与 layout helper](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/src/poly/q35_scratch_arena.hpp)：Qwen35 recurrent 和 full-attention 临时族互斥，使用较大的对齐共享区。4060 Laptop 8GB/WSL2/Tiel UD-Q4_K_XL、110k、B=2048 节省 188.4MiB，作者未见 notable PP/TG 增益。只有当前已有 workspace route 记录 allocator 余量就好，别展成复测。
- [#176 multi-GPU pool](https://github.com/simplexai-labs/PolyStrata/pull/176) 解除了两个独立卡上的 VMM pool 限制，Linux ROCm 还依赖 #175；2×RX5700XT/Tiel/262k 初始 resident 4053→5768、聊天 +2–6%。[原日志包](https://github.com/simplexai-labs/PolyStrata/tree/3e1642161198c50ff1abed4046f4e4f476099dbb/bench/results/2026-11-15-community-2x-rx5700xt-linux-cyber-tiel-ud-q4-k-xl/runs/pr176-vram-pool) 有 JSON。单 4090 不具有相同 multi-device 前提。
- [.10 的持久前缀](https://github.com/simplexai-labs/PolyStrata/commit/6b0aeeb0b1ae5af8f8c13ba87d5cfdb1c9aa8e34) 是 strata-poly 单会话。`SAVE/RESTORE` 和 `PIN` 验 model/engine/KV；原 agent 12,541 tokens、7 tools、Qwen3.6 UD-Q3_K_M、32 output，TTFT 1.88–2.12→0.24–0.38，已命中 checkpoint 的对照 0.62–0.95，文件 318–433MiB。[负例](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/docs/DETAILS.md#L929-L977)：37 个相同读取分段对照同答，但 fresh 一次性读 vs 保存前缀、分段读中 real agent 8/12 有分叉。上游本已有 [message-boundary cache](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/docs/MESSAGE_BOUNDARY_CACHE.md) 与其他缓存路径，故仅在实际 restart/miss/restore 占主导且等价性合同独立时诊断。

### 结果记录如何收口

- `NO_GO: active-path-disjoint`：当前真实包走不同路径；不借其他量化测试“能不能复现”。
- `NO_GO: cost-too-small`：关键路径上限不足；即使 padding 从推算上能彻底消除也停。
- `NO_GO: arithmetic-reorders`：已知改动不能保原样归约；不通过设容差、换采样把它变成主线成功。
- `INSUFFICIENT: shape-unobserved`：需要真实发射几何或计时缺口；如果额外观测过重，保留未决，不加架构改造。
- `OBSERVED: opportunity-needs-design`：只保留可支持同一代数/相加次序的进一步设计机会；不代表已经过 A/B 闸门。

物化输出只需按 dispatch 分类的填充/不可归因比例、关键等待和候选 status，参照 [05_DATA_MODEL_AND_MEASUREMENT.md](05_DATA_MODEL_AND_MEASUREMENT.md)、[18_CANDIDATES_AND_STOP_RULES.md](18_CANDIDATES_AND_STOP_RULES.md)。
