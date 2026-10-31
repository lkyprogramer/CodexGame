# 01 · 历史证据与关闭台账

## 必须保留的四个结论

1. 早期配置与服务修复有历史观察/部署证据，但“累计decode+23%、wall−9%”是分项相乘推算，不能作当前组合基线。
2. P3六对fresh engine、276请求没有通过正式组合门，原六项长检索失败保留。
3. P24证明HC减少工作量并未达到请求性能门。该候选已关闭。
4. 当前没有已取得性能资格的新候选；原作者一次限额诊断建议已由后续P01/P01B执行历史替代。2026-10-31经Astra复核，本轮零候选收口，不重复启动诊断。

来源：[P3](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P3-COMBINATION-KVRES-20261027.md)、[P24](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)、[历史汇总](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/SUMMARY-GAINS-20261026.md)。

## 2026-10-31 frontier实际终态

| 项目 | 保留结论与范围 |
|---|---|
| P01 | 941自然EOS触发原2048门停止，两个append NOT_RUN，INSUFFICIENT；原验收门不倒写 |
| P01B | 三请求执行COMPLETE、候选资格INSUFFICIENT；仅verify返回→commit进入窄host间隙不足4%，内部依赖仍UNKNOWN |
| F03快照复制/生命周期 | NO_QUALIFIED_CANDIDATE关闭；未证明可删owner，唯一零填差量CPU三对均更慢；不重开旧async/pool、trim/MMAP或扩大COW |
| F02 | DEFERRED_NEW_EVIDENCE；旧profile最大单格式仅2.2188%/2.1287%，无已证新机制，取消原拟四小时审计；不是当前暖态严格上界或全局NO_GAIN |
| 本轮与质量 | Astra复核后NO_QUALIFIED_CANDIDATE收口；六FAIL及P05 BLOCKED_EVIDENCE保持，不追加GPU或进入候选开发 |

证据：[Astra复核](../reports/ASTRA_REASSESSMENT_20261031.md)、[F03审阅](../reports/F03_REVIEW.md)、[P01B审阅](../reports/P01B_REVIEW.md)。完整主报告与原件位于父目录reports/workspace，旧实验失败和关闭范围不变。

## 已应用不等于正式组合通过

| 项 | 当前处理 |
|---|---|
| overlap、A0迁移、EXACT6、performance/C6 | 沿用既有基线，不重测分项、不乘收益 |
| reply token reuse、PT0 | 冻结；PT0与保留thinking下的reply reuse收益不可叠加 |
| CPUSHARE4096、AUTOMAX16384 | 冻结；长冷读热停止线仍有效 |
| KVRES20480 | 历史部署真实；P3正式增量未通过，本轮不自动撤销或再次扫描 |

来源：[A0/EXACT6部署](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-A0-EXACT6-20261025.md)、[服务部署](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-PROD-20261026.md)、[KVRES部署](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-KVRES-20261026.md)。

## 已关闭范围

| 历史项 | 证据边界 | 本包处置/重开所需新证据 |
|---|---|---|
| IL0、旧Ada表、P11新表差量 | 旧表约0.56%噪声；新差量profile条件空间约2.0–2.8%，不是正常负载严格全局上界 | 保留关闭；不同真实shape且当前暴露路径变大才新编号 |
| pool8/任务数16–192 | 无稳健收益或变慢 | 不再扫线程/任务数 |
| NP3并行quant/成本分行/减少re-park | 完整实验无益；trace纠正大固定开销假说 | 不把Maya“线程池”再命名立项 |
| learned profile、lookup-chain2 | 当前题集无稳定净益 | 不重复；新工作分布不能只凭假设 |
| MTP Q4 head、spec3/4/5、SPECCOST | 微益或每窗token同步减少 | 原策略保持；新草稿必须有不同成本机制与严格target验证 |
| trim/MMAP | 默认单会话不触发trim；轮转/部分MMAP更差 | 不切allocator、不全模型重mmap；只诊断有归属证据的活跃页压力 |
| Q2_0 down NP-1a | 微测走错真实分支，整机无益 | 不复用旧速度数字 |
| 固定PCIe分担/PCIE_BALANCE、lag2/nowait/async | 局部收益被等待抵消/持平 | 不再次扫；逐专家deadline成本仅在新证据与质量门满足时独立立项 |
| KVGROW | ≥65K无收益 | 长会话不重开相同开关 |
| P5 IQ3_S VNNI | 全专家改善−0.152%，CI跨0 | 不扩展ISA/nt/预打包作为P5续跑；全新表示机制仍先做当前资格 |
| P12 gather | 全专家+33%耗时 | 拒绝同实现，不重测 |
| P10 DEQUANT_SIDE | 关闭态乐观空间1.2–1.7%，未开候选 | 不能说“实测开启变慢”，也不因未开而强开 |
| P24 HC | TTFT +0.824%，CI跨0；decode耗时+4.428% | 当前HC不再实施/组合；GROUP_SCRATCH未被它覆盖，但仍未获资格 |
| #4040 | 可加速调用仅约decode0.8% | 不移植 |

详细来源在 [原报告索引](../sources/EVIDENCE_INDEX.md) 和 [64项映射](../history/V2_64_DIRECTION_CROSSWALK.md)。

## 为什么HC是后续设计的中心反例

P23真实减少专家H2D `8,187,264,000` bytes；原compute流暴露copy等待仅减少 `116.832126ms`。回填wall另减少 `85.325113ms`，两者不能直接相加成可省关键路径。P24完成20引擎/24请求，无失败替补：TTFT时间几何比0.991756，95%CI[0.981959,1.000352]；decode比1.044275，95%CI[1.020868,1.068783]。

这不是“缓存概念无用”的证明，而是明确否定当前HC实现/配置/负载已达到采用门。所有20引擎存在major fault及系统swap，不能唯一归因HC，不能事后剔除样本。新内存方向必须用当前warm路径的地址空间、缺页归属和暴露等待支持，不能把这些历史噪声当作已找到提速原因。

来源：[P23成本](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P23-HC-RETAINED-EXPERT-COST-20261029.md)、[P24性能](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。

## 正确性成果可以复用，但不能扩大证明范围

- P13–P21：匹配实际驻留/分派的oracle、16K有效数据逐字节核对、生命周期证据。
- P22：完整默认memcheck零错误；为诊断调整的加载/async控制不属于正式性能配置。
- P7–P9：排除gold/tokenizer/SSE等部分原因、独立llama.cpp复现；不能据16/16 argmax一致宣称模型整体质量相同。
- P5：全链同输入数值、ISA和实际命中已通过；这不替代新布局的证明。

来源：[P20/P21](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P20-P21-HC-16K-LIFECYCLE-20261029.md)、[P22](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P22-HC-MEMCHECK-20261029.md)、[P8](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P8-INDEPENDENT-LOGITS-20261028.md)、[P9](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)。

## 重开协议

重开记录至少包含：旧实验ID、原否决原因、此次变化的源码symbol/shape/输入分布、为何旧证据不覆盖新实现、当前关键路径资格、资源和质量前提、新run_id及一次样本上限。任一项缺失→DEFERRED_NEW_EVIDENCE。换commit号、换项目名、换宏名、换seed、改门槛都不是充分的新证据。
