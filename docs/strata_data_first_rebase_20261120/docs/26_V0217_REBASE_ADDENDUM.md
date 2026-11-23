# 26｜v0.2.17 重基线补遗（2026-11-20）

状态：**ADDENDUM**。本包正文（00–25）锁定的是 v0.2.16 研究快照，原文和原验证回执不改。本文件记录：上游发布 v0.2.17 后的新锁定点、4090 现场已有的实测结论如何回填到本包的问题和候选，以及评估方法的修正。授权边界仍以 [AGENTS](../AGENTS.md) 和用户当轮授权为准。

## 1. 新锁定点

| 项 | 值 |
|---|---|
| release | v0.2.17，发布于 2026-11-20T08:24:35Z（北京时间 16:24） |
| annotated tag 对象 | `028e6826bdb152be2d0579818c2ede6fe7da984c` |
| tag commit | `12d491da4a6904eb49aaa6f2f63ec4b1a17582e3` |
| 当时 main | `3142b66b96e9c0e775e30f620b11b191a1427c2a`（tag 之后 3 个提交，只涉及路径注释、Windows CI 和 Docker 构建，不涉及 engine 或 telemetry） |
| 版本 | app/terminal 0.2.17，engine/control 0.1.63 |
| 相对 v0.2.16 | 278 个提交，468 个文件，+30005/−11950 |
| 4090 自编引擎 | CUDA 12.3、sm_89，`build/strata` sha256 `df2d006b2adc7ad12f169d6839587ff7efc134f5873ba52c238fe207201b32a5`；与官方 cuda12/cuda13 发布包是不同身份 |

机器可读记录见 [source_lock.json](../evidence/source_lock.json) 的 `strata_v0217` 项。原 `strata`（v0.2.16）项保留为历史锁。

## 2. v0.2.16 → v0.2.17 中与本机相关的变化

| 变化 | 对 4090 + IQ3_XXS | 依据 |
|---|---|---|
| `STRATA_ROUTE_TAIL_SKIP` 从 CUDA 上默认 rank 7 改为默认关闭 | **必须显式设为 7**，才能与生产（0.2.3）和 v0.2.16 基线保持同一行为；关闭后 decode 慢 12%～20% | 实测，见 §4 |
| `STRATA_POOL_DEP` 默认开启（逐位一致） | CPU 专家每条目耗时低约 2%～3%（弱证据）；Q2_0 down 行不走这条路径 | 源码 `pool.cpp`；实测 |
| verify 窗口卡顿、PLE 读取看门狗、工具调用解析、thinking 预算别名、停止串等修复 | 有益，未单独测 | release notes |
| 17 GB 内存预算、按 PCIe 调整 CPU prefill 份额、`ADAPT_FETCH=2`、sm_120 默认开关、AVX-512 K-quant 行 | **不适用**：只针对 UD-Q4 模型或 cc 12.x 显卡；本机 CPU 专家是 IQ2/IQ4_NL/Q2_0 | 源码中的生效条件 |
| telemetry / monitor | telemetry 只增加了 Windows/AMD/Intel 的硬件传感器适配；Monitor 增加了 helper-cache 和 peer 卡采样；serve 修正了恢复后缓存数字清零的问题（\`a73ef2419\`）。[04](04_STRATA_METRICS_AUDIT.md) 的结论（够看健康、不够做因果对照）不变 | 源码 diff |
| `/metrics` 新字段 | diff 中没有新增指标字段，也未发现与 [05](05_DATA_MODEL_AND_MEASUREMENT.md) 的缺口字段对应的新增项 | 源码 diff |

## 3. 现场证据回填

均为 4090 实测，报告在 `strata_4090_128k_lab/reports/`。

| 本包条目 | 原状态 | 回填 | 新状态 |
|---|---|---|---|
| O02 解码依赖链（ready-hit、CPU/DMA） | DATA_REQUIREMENT | 100K decode 每窗口 ≈ GPU-reach 约 9 ms（各版本一致，nsys 证实 GPU 每 token 工作量相同）+ 主机 CPU 专家时间（随 CPU 条目数线性变化）+ 草稿约 1.4 ms。可变成本几乎全部在 CPU 专家路径，受约 36 GB/s 内存带宽限制。来源：V0216-DECODE100K-NSYS-QUALITY、V0216-SEQDEP-PCE0、V0217-MIGRATION-TAILSKIP | **L0 已回答主问题**；P2.3 的 round/shape 新 hook 不需要（NOT_NEEDED），除非出现新问题 |
| C01 suffix 二级索引 | CONDITIONAL_OFFLINE_ONLY | 文档类长上下文负载中 lookup 窗口只占 3.9%～7.4%，关闭 suffix 草稿（SD0）后速度不变。agent 复制/编辑负载（W09）改用公开 Exercism 题的 Pi 式会话做离线反事实（不涉及用户内容）：加 8-gram 索引按 oracle 上界只省 0.19% 的窗口（write/edit 请求 0.28%），原因是被挤出的旧源一个 token 后就会被 trigram 重新命中。来源：V0217-C01-OFFLINE | **NO_HEADROOM**，关闭 |
| C02 MoE padding census | OBSERVATION_ONLY | 未做；prefill 在 v0.2.17 上与 v0.2.16 持平 | 不变，优先级低 |
| 新基线 | 未建立 | B2 = v0.2.17 + PT0/#1536（[补丁](../../strata_4090_128k_lab/patches/v0217-pt0-reply-reuse.patch)）+ `--lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct` + `STRATA_ROUTE_TAIL_SKIP=7`；与 B1 相比速度、分叉复用和质量筛查都持平 | DATA_VALID；任务级配对门对精确路由非劣（V0217-AGENT-GATE） |
| 尾部跳过 | 未列入 | 上游已有的配置项，不是新算法；按 [23](23_DECISION_AND_BUDGET.md) 属于"上游已含机制、现场未开启"的配置生效诊断。teacher-forced KL：rank 7 为 0.047（重复运行 KL=0），见 V0217-TAILSKIP-KL。任务级配对门（305 道公开题，预登记 margin 5%）：对精确路由非劣性成立，损害上界 1.62%，同一负载下快 1.16 倍，见 V0217-AGENT-GATE | ALREADY_PRESENT；作为基线配置固定为 7，任务级非劣已证实 |

## 4. 尾部跳过开或关（v0.2.17，同一构建，各 n=4 序列段）

| 指标 | rank 7（B2） | 关闭（TS0） | 变化 |
|---|---|---|---|
| c100k decode tok/s | 134.0 | 117.1 | −12.6% |
| d3k / c32k / f10k decode tok/s | 145.4 / 147.7 / 143.6 | 121.1 / 118.0 / 121.3 | −15.5%～−20.1% |
| prefill ms（d3k / c32k / f10k / c100k） | 3138 / 7292 / 3797 / 20865 | 3030 / 7272 / 3798 / 20911 | c32k、f10k、c100k 在 ±0.3% 内，d3k −3.4%（小样本） |
| CPU 条目 / 层·窗口（c100k 两段） | 1.52 / 1.93 | 1.98 / 2.96 | +30% / +53% |
| CPU ms / 条目 | 3.03 / 2.98 | 3.20 / 3.10 | 基本不变 |
| 质量筛查（corpus + chain） | 21/23、8/8（seed 7、11） | 21/23、8/8（seed 7、11） | 筛查灵敏度不足以检出 KL 0.0126 量级的差异 |

## 5. 评估方法修正（补充 [10](10_EVALUATION_AND_STATS.md)）

1. **长上下文 tok/s 会被文本轨迹混淆。** greedy 输出随前序请求和专家放置变化：42 次序列运行出现 20 种开头，接受率在 0.65～0.80 之间浮动，c100k tok/s 在 118～152 之间。重启服务也只能固定开头约 1000～1200 字符。
2. **版本和开关对照的主指标改为与文本无关的量**：每窗口 ms、每 CPU 条目的主机耗时、每窗口 CPU 条目数、GPU-reach、prefill ms 和复用 token 数。tok/s 只作辅助。若需要 tok/s 级结论，用 teacher forcing 固定文本，或每臂 ≥20 条不同轨迹。
3. 若沿用 max(4%, 2×AA) 门，AA 应在同一类指标上估计。按 tok/s 估计的 AA 会被文本混淆放大，100K 场景几乎无法过门。

## 6. 下一项允许动作

- 用 B2 作为后续所有对照的基线；正文中"v0.2.16 / 64524fb9"的锁定点，改为以本文件 §1 为准。
- P0–P1 的文档和适配工作照常，但 P2.0 的 L0 已回答 O02 主问题，P2.3 不再预设。
- 生产已于 2026-11-20 按用户授权切换到 B2（[切换回执](../../strata_4090_128k_lab/reports/V0217-PRODUCTION-SWITCH-20261120.md)），目前保持运行。正式质量门原先缺 gold 题集、状态为 BLOCKED，现由[任务级配对质量门](../../strata_4090_128k_lab/reports/V0217-AGENT-GATE-20261120.md)补上：exercism/python 和 HumanEval 共 305 道公开题，按 [10](10_EVALUATION_AND_STATS.md) 的配对二项口径用 `quality_gate.py` 判定。margin 定为 5% 并写明理由：2% 需要至少 183 题且零不一致，采样解码下做不到；实测损害上界为 1.62%。
- C01 已按 oracle 上界关闭（NO_HEADROOM，见 [C01 离线反事实](../../strata_4090_128k_lab/reports/V0217-C01-OFFLINE-20261120.md)），不再需要 W09 内容采集；C02 维持观测级。
- 配置取舍（[结论](../../strata_4090_128k_lab/reports/V0217-PT-THINKING-20261120.md)）：尾部跳过保持 rank 7；thinking 保持 PT0，因为 PT1 虽能免去每条新用户消息后的重读（Pi 式负载中约占 11% 时间），但在真实 Pi 历史上会让 prompt 变大 10 倍。
- 后续任何版本或开关变更按两层门判定：先过 teacher-forced KL（数值级），再过任务级配对门（每臂约 2 小时）。tok/s 只作辅助，与 §5 一致。版本升级的流程已脚本化为 [upgrade_gate.py](../../strata_4090_128k_lab/tools/upgrade_gate/README.md)，并已用 v0.2.17 自身自检。
- v0.2.19（engine 0.1.65）已按此流程评估：任务质量非劣，但它新增的 sm_89 默认开关会让 decode 慢 13%；关掉 `VERIFY_DEVICE_HITS` 后也只是持平。因此不升级，基线仍为 B2，见 [V0219-UPGRADE-GATE](../../strata_4090_128k_lab/reports/V0219-UPGRADE-GATE-20261122.md)。
- v0.2.20（engine 0.1.66）只做了 40 题测速：采样对齐后慢 9.9%，不进完整门，见 [V0220-UPGRADE-GATE](../../strata_4090_128k_lab/reports/V0220-UPGRADE-GATE-20261123.md)。这一轮补充一条评估方法：tok/s 除了受文本轨迹影响（§5），还会受服务端采样默认值影响。上游 #6536 把不带采样参数的 MTP 请求改成 greedy，草稿接受率随之上升，单看 tok/s 会误判为加速。版本对照必须核对接受率和 `/props` 中的默认采样参数。
