# 02 · 防重复台账与重开条件

返回[总入口](../README.md) · [数据模型与测量](05_DATA_MODEL_AND_MEASUREMENT.md) · [阶段任务计划](19_PHASE_TASK_PLAN.md)。

**保留旧结论，不把旧结论扩展到新版所有机制。** 每条历史判断只在它自己的模型、分派、工作负载、资源、资格与停止合同内成立。当前任务最先拿新版可解释数据，不先选择 GU/lookup/DF2/allocator 开发题。在任何计划里重复出现同名概念时，先以本页和[固定历史基线](01_BASELINE_AND_HISTORY.md)登记查重。

## 1. 禁止重复实验台账

总重开门：每条新卡先填 **旧 ID、原否决范围、固定 donor symbol、当前目标实际 dispatch/shape/codec、独立机制差量、为何旧证据不覆盖、当前可闭合关键路径与新增成本、质量/资源前提、新 run ID、有限样本与新执行范围**。新 tag、名字、宏、tile、模型作者的 5090/3090 数字和预计收益均不能独立重开；旧报告的 adoption gate 是它自己的合同，不倒写。

| 旧路线 | 已证终态 / 禁止误报 | 允许重新取得资格所需证据 |
|---|---|---|
| A0 / reachability、EXACT6、reply/PT0、CPUSHARE4096、AUTOMAX16384、KVRES20480；P3 组合 | 历史部署事实与增量不等价。六对/12 fresh engines/276 请求固定性能场景，8 个定长场景均未过 4% 正式门；原长检索失败/链失败保留。没有组合 decode +23%、wall −9% 的实测结论。[P3][p3] · [台账][closures] | 不重新扫旧旋钮。新版如已不同路径，先以独立 source/config/active scope 审计；任何新 A/B 固定其余参数。 |
| frontier/P01、P01B、历史窄 host gap | P01 prime 103,183 输入、941 自然 EOS，两个 append NOT_RUN；P01B 新合同自然 EOS 下 1 引擎/3 请求、939 窗口、2291 native token，执行 COMPLETE、candidate INSUFFICIENT。warm 的 verify return→commit enter 全部 host 间隙为 0.1340%/0.1224%；内部 GPU/CPU expert/DMA 依赖未知。P01B 初次 append read 80,868/reuse 8,344，第二次 append read 291/reuse 89,207，PT0 条件模板可解释大部分，不推定持续缓存失效。[P01B][p01b] · [Astra][astra] | 新采集只绑定新版、缺失阶段和用户新增工作负载；不沿原 run 再取相同窗口，不把所有 host 限制成 0.13%。拿到实际 stream/event、终点依赖及 observer-off 差分才讨论未知路径。 |
| F02：GU load/layout / TG21 | `DEFERRED_NEW_EVIDENCE`，撤回原四小时 CPU 审计；老 P11 家族 kernel 时间并集 6.8911%/6.5884%，最大单格式 TG21 2.2188%/2.1287%。不是 critical exposure 或当前稳态上界。已有多列解包、codebook staging、融合 GU/SwiGLU/q8_1；未确认新的可做机制。[Astra][astra] | 实际新版暖态合法形状的暴露依赖、产物/命中绑定、新单一 mechanism、有限局部速度及新增开销支持完整请求净省 ≥4%。不把多格式拼成一条扩大合同。 |
| F03：快照 lifecycle、drop/resize、旧 async/trim/MMAP/COW | 未找到合法可删 owner 或泄漏；第二次 park 1198.2 ms/14.14% 是已观察的请求成本，非可全部删除。同步零填较小原型正确性过，但三对 CPU 完整段慢 +6.08%～+7.74%；GPU 未测，关闭。旧页逻辑容量、RSS、PSS、swap 不可相加。[F03][f03] | 真实 owner/深 checkpoint/生命周期、有效域、故障/取消和 DMA 依赖绑定，另有独立机制及净收益证据；不能重复零填题或无条件合并合法分支。 |
| F01 selected KV、F04 QSA、F05/F06/F07 新 scratch/整数 grouping/allocator | 原关闭/延期并不表示这些实现都硬件失败。已有 KV 去重/epoch/CLOCK/vector path、部分融合及 CachingPool；未获合格差量和当前关键路径。F05 group-scratch **未**由 HC 试验覆盖，仍缺资格。[Astra][astra] · [64 路线映射][v2cross] | 对应版本的新算法/owner 或阶段预算证据、区分当前 select/搬运/scratch 的累计与暴露成本、适配 SM89、保真等价才可提。旧池已存在就先核复用和热申请，禁止只改命名。 |
| P24 HC / retained expert overlap | P22 正确性/memcheck、P23 工作量门通过；601 专家净少搬 8,187,264,000 B（约 8.19 GB），P24 20 引擎/24 请求，100K TTFT +0.824%（95% CI [−0.035%, +1.804%]），完整 decode 耗时 +4.428%；不采用。全 20 引擎均有 major faults/swap，不能事后去样或归因 HC。[P24][p24] | 换模型或所谓 adaptive tail 不自动重开。先证明地址归属和 critical exposure，而非字节数/累计时间；只在不同实质机制与新冻结合同下筛选。 |
| NP3/pool、tasks 16–192、parallel quant、cost row/repark；Ada IL0 / P10 dequant / P5 VNNI / P12 gather、固定 PCIe share、KVGROW | pool/任务数等无稳健净益；VNNI 全专家 −0.152% 且 CI 跨 0；gather 全专家耗时 +33%；P10 **只有关闭态 1.2–1.7% 乐观空间，从未执行候选开启**；KVGROW ≥65K 无益。旧 PCIe nowait/lag/share 局部收益被等待抵消。[台账][closures] | 不重扫线程、ISA、nt、tile、预取、PCIe 占比、allocator。新版实际 shape/exposure 显著不同且有正交机制才另立项。 |
| SPEC3/4/5、SPECCOST、learned profile、lookup-chain2 | 微益、裁窗口同样减少提交数，或在既有题集无稳定收益；MTP4 保留为旧采用设置，而非新版 `auto` 生效证明。[台账][closures] | 只有真实任务可用的不同 proposal cost 机制；同时记每轮正式提交数、验证成本、自然 task wall、质量和采样正确性。不要扫旧 spec width/阈值。 |
| v0.2.17 B2 自适应专家层参数（`--adapt-every 2`、`--adapt-decay 0.92`）、b2 臂学到的起点 profile（2026-11-23） | 4 个 40 题臂，同会话对照 AA 0.30%。每窗口 ms 相对对照只改善 0.1%/0.2%/0.1%，过门线 4%，端到端都更低：NO_GAIN / NO_HEADROOM。生产 learned profile 与静态 profile 逐字节相同（从没保存过真实流量）。[探针结果](../../strata_4090_128k_lab/plans/B2_ADAPT_PROBE_20261123.md) | 只覆盖 prompt <32K 的门题集。不再在门题集上扫 adapt every/swaps/decay/min-gain 或起点 profile。长上下文（≥32K，Pi 主流量）可以带着新的预登记和工作负载重开 `--adapt-every`；它在 4K–32K 段有 −10% 的事后分段信号，不能当作证据。 |
| 旧 DF01 Q8 原路径 D1S/D1U | N2300 4th draft token 不匹配（CPU 212522/GPU 209087）；context `hidden_norm` 后 Q/D 替换可重现差异，无证据判定单点缺陷，`STOP_CANDIDATE_CAUSAL_BOUNDARY_CONFIRMED_NO_QUALIFIED_FIX`。D1 未过、D2 未启动，后续未用预算不是许可。[D1U][d1u] | 不换参考/放宽门/续跑同 Q8。若新版真正不同的草稿/selector 或目标状态机制与新授权成立，独立资格，不擦原失败。 |
| Strata v0.2.10 后续发布版 DFlash2 | `USER_REPORTED_PENDING_ARTIFACT_BINDING`：据后续摘要约 14 请求/2 engine，首请求 28 提议/19 接受，固定输出、EOS、短追加、保存恢复、取消功能 PASS；任务 wall 无净益，**KEEP_MTP_SPEC4**。`--plan` 和发布层资格有版本化记录，但后续 raw 未在固定 HEAD 核到，不能独立复算。Q8 原 FAIL 与发布版功能通过可以同时成立。[发布资格][dfreadiness] · [后续摘要来源][deltahist] | 未测试并非事实；不要自动 A/B。候选必须是不同的实质机制、实际加载/生效和当前独立证据，不引用 11-18 **HyperQwen** DFlash2 来替代。 |
| 旧六项长检索 / 正式 P05 | 真恢复回执不等于正确答案；P7 真复现六失败，关闭 MTP 仍同失败；较短表、明确格式或改 thinking 的控制通过只帮助归因，不能改旧 gold。P05 仍 `BLOCKED_EVIDENCE`：缺真实稳定 warm-fixed2048 原件；P01B 自然 EOS、P24 五 token append、其他 Dense 数据不可替换。[P7][p7] · [Astra][astra] | 原失败保持原状态。新绝对质量、服务协议/continuation 和相对质量门独立；任何新固定输出轨迹为明确预登记另一个合同，不倒写旧 P05。 |
| NInfer H1 / H3 W6 / K1 / Q4 / GQA / T05 / C0 / sampled-q | H1 4-gram ring K3 命中 47/128、122/141 接受（86.52%）但单位 token 慢 +4.28%～+8.11%；W6 完整轮/token 在两个样本快 ~20–23%，Java 后半慢 +13.75%，固定 W6 关闭。Conv T05 局部 −36.48% 但整 prefill −0.314%；GQA Bc64 32K 有利、128K +0.156%；其余不采纳。同机 P4 四 Chat wall 合计慢 +34.95%。[9 路线与归因][deltahist] · [11-18 最新合并核对][multi] | 仅作防重复与数据口径迁移，不把 Dense NInfer 参数/性能外推到 MoE Strata。不要改名成 lookup、宽窗、prefill fusion 或“第一次归因”重新做。 |

11-15 source-delta 保持原分层：`D1=NEW_MECHANISM_CONDITIONAL`（OSAKANA source anchor/edit repair、在合适分支避免先做后丢 proposal，仍需证明 MTP conditioning catch-up、时间净省和状态安全）；`H2=PLANNED_NOT_RUN_SOURCE_REFINED`（YASAKANI 低秩粗筛 shortlist 再重评分只是细化旧 head 计划）；`K-PAIR=SOURCE_BOUND_PAIR_P3_DELTA_UNBOUND`（同输入 Q4/Q5 pair 的实际 P3 dispatch 未绑定、sm89 `NINFER_SM86` 守卫不能假称 PDL 重叠）；`M0=UPSTREAM_IMPLEMENTED_DEPLOYMENT_UNBOUND`（Strata 已含按剩余预算和窗内 EOS 限制 committed input rows 的维护机制；避免重复实现，验证部署与下次 continuation 才是差量）。[决策摘要][deltadec] · [旧 donor 重开规则][deltareopen] · [静态验收][deltaval]。这些不是本轮四个 GPU 优化项目，也不是现在已部署。

## 2. 显式区分三种“没有做”

| 判定 | 示例 | 后续处理 |
|---|---|---|
| 已执行，无采用资格 | P24 暖态/冷读门不够；旧 DF01 Q8 D1 failed；新版 Strata DF2 用户报告功能过、墙钟不过 | 保留失败和原样本；不拿未用 GPU 额度重试，不转成 NOT_RUN。 |
| 旧档未执行或计划 | P10 未开候选；R0–R4/O0–O6/E0–E4 文档；H2；P05 缺符合原门的暖态原件 | 不能说实测变慢/硬件失败；也不能把它们加入自动跑队列。 |
| 当前部署或后续原件未知 | v0.2.16 生效的模型与 argv、DF2 后续原件、NInfer P3 projection dispatch、私有本地工作区 | 只读取得足够证据才更新对应轴；不将旧应用记录或工具 exit 0 补成现场结果。 |

## 3. 存量 source delta 的底线

- **Strata donor catalogue 已存在。** 11-10 的 samir-vllm 是预算、分页临时内存生命周期、正反例的参考；Nabo 是实测→产物→计数器→证伪方法。不是移植 allocator、scheduler、JAX/Pallas 或迁移 CUDA kernel 的立项理由。[既有增补][addreadme]
- **D1/H2 的目标是 Dense NInfer。** K3 n-gram 仍受既有 acceptance headroom 与 MTP mandatory cost 约束；source-anchor 与 edit-repair 先分别消融。H2 对同候选重评分、采样权威及随机流约束单列，不把粗筛说成精确 full-vocab 检索。[旧 donor 重开规则][deltareopen]
- **P14 已做过真实短窗口归因。** 主体约 79.32%/79.76%，draft head+AR 约 9.51%/9.56%，commit/Fold 约 1.53%/1.47%。这些是旧 NInfer 观测、不是本轮 Strata 的份额；P4 原四 Chat wall +34.95% 继续保留。[归因与后续][deltahist]
- **M0 不等同裁切输出字符串。** 作用点为合法提交的输入行；已曝光的最后 output 通常是下一轮未消费 token。已有上游实现就只验真正运行的版本是否在 EOS/剩余额度边界与后续继续处正好处理；不重写同一 helper 作为新优化成果。

### 邻接 Dense NInfer 的已测机制（防止借名重跑）

下表数值均是历史、版本化测量，不能作为 Strata/Ada 当前代价；更多上下文和原实验链接在[九路线回溯][deltahist]。

| 旧 ID | 实际边界 | 禁止将什么改名后当成新机制 |
|---|---|---|
| H1 请求内 K3 查找 | 47/128 轮命中、122/141 接受；三组 ms/token 慢 +6.98%/+4.28%/+8.11%。raw 正例已有 3.880/3.944 正式 token/轮，K3 上限 4；同成本下接受位点剩余收益空间仅约 3.01%/1.39%。 | 同 n-gram/K3 替换、没有减掉必做 neural proposal 的 lookup。来源约束/edit repair 可以是差量，但只能先证明路径和净成本。 |
| H3 固定 W6/K5 | Java/中文完整轮 ms/token 快 22.75%/20.38%，Java 后半慢 13.75%，稳定门没过。 | 固定 W6 不是未测，W8/W16 也早已有宽窗计划；不只摘有利的短窗口。 |
| C0 SHA/OpenSSL | 流式 SHA 2.1491×、合成 publish 时间 −53.12%；真实 L2 恢复 55,293 tokens 时 TTFT 943.552→959.943 ms，alias/输出控制不成立。 | 没有证据证明“更快 SHA 加快真实 TTFT”。晚些隔离的双线程导出/有界交接/FIFO publish 是 CPU/build 已做，真实机尚未按合同比较，不从零开发。 |
| K2-T05 卷积/KV 布局 | 算子约 −36.4834%，整 prefill −0.313951%，两对 Chat 观察 −0.881/−0.362%。 | 不把算子百分比当用户 TTFT，也不补同条件样本。 |
| GQA T4 Bc64 | 32K 时间 −14.865%，8K +14.516%、128K +0.156%，整体筛查失败。 | 不挑 32K 变新结论；spill 计数本身不是净收益。 |
| K1 GDN Record/Fold 和 K2-T01 RMSNorm | K1 三提交宽度仅 −1.054/−0.071/+0.181% 改善且多约 9.785 MiB；K2-T01 四组改善 +1.20/+5.76/−3.43/+4.98%，胜批不足。 | 不拆掉主工作仅用 Fold 小微测，不靠换 stream、CTA 重新登记。 |
| 采样 MTP / Q4 layout | 完整 proposal q+独立 RNG 的 Java/中文单位 token 慢 1.75%/0.67%；工具单位 token 快但整任务 4.355→5.053 s。Q4 紧凑预取两候选慢 +0.583%/+1.325%，理论驻留仍为 3 CTA/SM。 | 随机分布/penalty/缓存门不可旁路；不以格式布局换名重扫同 prefetch。 |

### 独立保留版本比较的入参和结论

- **U01 / U01R1，v0.2.3 vs v0.2.7：** 原轮 PT0 计数遗漏产生 `USAGE_DRIFT`，实际两请求后停止，十项 NOT_RUN，B 未执行。修复后的独立授权轮三组/12 请求，编码两臂 3/3、工具 3/3 vs 2/3，没有稳定升级收益；阶段不能合并拼多样本。[旧版本配对][u01r]
- **v0.2.10 PT0，非 DF2：** 三对仅两条会话（NSO 重复），同输入 Java 暖态速度下降、两臂任务 0/3，暂不移植 #1536，历史旧服务随后恢复。新版源若确实不同也必须隔离出 V 轴，不反复移植同 #1536 作性能新路线。[旧 PT0 配对][pt]

## 4. 重开记录最少要交付的证据

| 字段 | 合格内容 |
|---|---|
| `historical_scope` | 老机制、源码、目标、真实 dispatch、条件和证据级别；明确哪条旧结论不能覆盖现提案。 |
| `premise_delta` | 一个新符号/形状/存储或调度机制，预先写出否证观测；重新构建、换卡名、换微基准不算。 |
| `critical_evidence` | R 基线当前运行的重复或暴露成本，关键路径与事件/依赖链闭合，或可证无需继续；同时列新增开销、重叠和未知。 |
| `projected_net` | 用该阶段真实暴露比例和可复现的局部成本估算；理想上界都无足够空间即止，不把范围内全部工作假设为可删。 |
| `new_experiment_scope` | 序号、独立风险/正确性检查、经用户另行授权的最小预算、有限停止条件、与已关闭组去重结果。 |

**正式采用门（仅面向新候选）：** 配对主指标是预登记的完整时间；相对改善至少 `max(4%, 2×A/A 噪声)` **且 95% CI 上界的 candidate/baseline 时间比不超过 `1−max(0.04,2×AA)`**，非主指标在冻结非劣范围内，资源/任务质量/continuation 另验。点估计看起来更好、接受率提升或多搬/少搬都不替代置信边界。旧 P24、P3、DF01 等使用历史原门，不倒写。

若没有条件合格候选，产出 `DEFERRED_NEW_EVIDENCE` 或 `NO_QUALIFIED_CANDIDATE` 并保留实际观测。**无候选是可交付结果，不补第七对，不强拉 2048 token，不横向扫旧 atlas。**

[multi]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/qwen38-27b-4090-130k-multisession-20261118.md
[u01r]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/U01R1-VERSION-COMPARISON-20261031.md
[pt]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/V0210-PT0-VERSION-COMPARISON-20261104.md
[astra]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/FRONTIER-CLOSURE-ASTRA-20261031.md
[dfreadiness]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/DFLASH2-V0210-READINESS-20261103.md
[closures]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/docs/01_EVIDENCE_AND_CLOSURES.md
[deltadec]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/docs/00_DECISION_SUMMARY.md
[deltahist]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/docs/01_HISTORY_AND_NO_REPEAT.md
[deltareopen]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/docs/14_PREVIOUS_DONORS_AND_REOPEN_RULES.md
[deltaval]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/evidence/VERIFICATION.md
[addreadme]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_foundation_kernel_evidence_addendum_20261110/README.md
[p3]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/P3-COMBINATION-KVRES-20261027.md
[p01b]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md
[f03]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md
[v2cross]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/history/V2_64_DIRECTION_CROSSWALK.md
[p24]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md
[d1u]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/DF01-D1U-N2300-CAUSAL-STOP-20261103.md
[p7]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/P7-LONG-RETRIEVAL-ROOTCAUSE-20261028.md
