# frontier · Astra复核与本轮文档收口

结论：**NO_QUALIFIED_CANDIDATE；停止当前冻结合同下的性能探索。** 2026-10-31，Astra独立复核后不支持继续推进F02，root采纳并撤回此前“优先做四小时F02离线资格审计”的建议。F02保留`DEFERRED_NEW_EVIDENCE`，不进入候选实现。本结论表示当前投入依据不足，不是全局`NO_GAIN`或“软件优化已穷尽”的证明。

本轮完成报告与入口收口，没有新优化采用、引擎构建、推理请求或GPU实验。生产保持停机，6144MiB/4slots、PT0、原六项FAIL和P05 `BLOCKED_EVIDENCE`保持。

## 独立复核来源与执行边界

用户明确要求“Astra xhigh再评估”。实际使用内置独立子代理`/root/astra_remaining_reassessment`，调用配置为`model=gpt-6-astra`、`reasoning_effort=xhigh`、`fork_turns=none`。当时`CODEXHOST_CLI_PATH`未配置，因此没有创建外部CodexHost线程。工具没有提供独立运行时模型/档位回读，不将调用配置写成已验证的运行时元数据。

Reviewer读取当前规则、P01B/F03报告与回执、候选卡、donor/atlas、本地源码及身份，并只读计算旧P11 SQLite区间。Reviewer没有SSH、修改文件、编译、测试、benchmark、服务启动或GPU请求。root独立复算同一两份SQLite，结果一致；这不是重新运行模型或新的性能实验。子包[复核回执](../frontier/reports/ASTRA_REASSESSMENT_20261031.md)记录相同结论。

## F02为何暂缓

[F02合同](../frontier/candidates/F02_EXACT_LOAD_LAYOUT.md)只允许一个真实热点格式、一个内核。此前整个GU-SwiGLU家族约6%–7%的累计值不能直接用于立项：它合并多个格式，且没有当前暖态依赖证明。

本次按实际engine PID/globalPid及首末输出标记裁剪，再对kernel区间求并集：

| 旧P11首末输出观测区间 | short | long |
|---|---:|---:|
| 区间长度ms | 21971.125601 | 21033.767971 |
| GU-SwiGLU全家族并集ms | 1514.049497 | 1385.792614 |
| 全家族占观测区间 | 6.8911% | 6.5884% |
| 最大单格式TG21并集ms | 487.502838 | 447.748344 |
| 最大单格式占观测区间 | **2.2188%** | **2.1287%** |

在这两个旧样本的条件模型内，即使完全删除最大格式的kernel时间，也不到4%。将五个格式拼成家族候选会扩大现有合同；整个家族也需消除约六成kernel成本才可能达到4%，尚无这样的具体load/layout机制。按[筛查政策](../frontier/docs/03_CANDIDATE_DECISION.md)，4%–8%的暴露份额通常仍不足立项，需有可信局部方案支撑净省时至少4%，不能任填局部倍率。

**这些比例仅为旧profile条件成本，不是暴露时间，也不是正常真实暖态的严格收益上界。** [P11](P11-ADA-DELTA-QUALIFICATION-20261028.md)的10264槽、采集扰动与生成轨迹不同于P01B的10272槽真实追问；首末输出观测区间也不是完整请求或逐verify窗口集合。它们削弱继续投入的理由，不支持全局否定GPU内部空间。

源码核对没有确认新的可实施差量：`row_dot2_80_sub16`已共享多列权重解包，已有codebook staging，`native_gu_swiglu_kernel`已融合GU、SwiGLU、q8_1。两次`S::apply`调用不能直接证明机器码重复读取，更不能证明重复读取位于完成路径。

核对的本地源码为`workspace/combination/dequant-side-20261028/source-evidence/src/kernels/cuda/iq_kernels.cu`，SHA256为`719f2eee24f93733778239bf7727db7a0e01b51d2841f05fb86120a7396ac8c5`，与`workspace/frontier/p01b-20261031/build/CAPTURE_BUILD.json`对应项一致。主要入口在该快照1728、1805、2860行。

因此取消原拟追加的四小时语义原型/编译产物审计。F02 GPU与CPU分支均不获得新资格；不把该暂缓改写为实测回归。

## 其余开放方向的处置

| 方向 | 当前未获资格的原因 |
|---|---|
| F01 selected-KV | 页去重、epoch pin、CLOCK、向量搬运已存在；缺当前重复读取/失效与依赖证据 |
| F04精确QSA选择 | SELECT_LONG有SM60门；缺当前score/selection暴露成本及具体SM89新差量 |
| F02 CPU布局 | dtype×nt×实现贡献未知；不能扩格式续接P5/P12 |
| F05行窗scratch | 有源码差量但偏prefill；全Dm、三路scratch最大值及冻结AUTOMAX约束仍在 |
| F06稳定整数分组 | mapped tables和部分fused grouping已存在；首次80K重读不代表read291的暖态机会 |
| F07 MMQ pool/slab | P6已有CachingPool；缺实际申请序列、热分配及预算收益证据 |
| F08/F09/F10 | 分别受质量、数值合同或兼容资产前提阻塞，不转入本轮冻结范围 |

没有一个方向提供更强的下一步依据；不为保持探索而改选另一卡。原[关闭台账](../frontier/docs/01_EVIDENCE_AND_CLOSURES.md)与[donor差量](../frontier/docs/07_DONOR_DELTA.md)保留。

## 历史终态保持

- [P01](P01-PI-WARM-DIAGNOSTIC-20261030.md)：941自然EOS触发原2048门停止，两个append `NOT_RUN`，阶段`INSUFFICIENT`；不倒写验收条件。
- [P01B](P01B-PI-WARM-DIAGNOSTIC-20261031.md)：单引擎三请求执行`COMPLETE`，候选资格`INSUFFICIENT`。窄host间隙占比0.1340%/0.1224%，只关闭该窄方向；GPU/CPU内部依赖仍`UNKNOWN`。
- [F03](F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md)：`NO_QUALIFIED_CANDIDATE`关闭。未证明泄漏或可安全删除owner；同步零填差量CPU三对总成本均更慢，不重开零填、旧async/pool、trim/MMAP或扩大COW。
- P24 HC、P5 VNNI、P12 gather、P10/P11已筛查差量、NP3等关闭结论不变。原六项长检索FAIL保留；P05仍为`BLOCKED_EVIDENCE`，没有性能或质量采用PASS。

## 复算定位与限制

输入为`workspace/combination/ada-delta-20261028/short-profile-v1-trace.sqlite`与同目录`long-profile-v1-trace.sqlite`；使用SQLite URI `mode=ro`。

| trace | engine PID | globalPid | 裁剪区间[start,end)，ns |
|---|---:|---:|---|
| short | 1460330 | 305975248551936 | [41180088642,63151214243) |
| long | 1461658 | 305997528694784 | [65723658945,86757426916) |

区间来自同目录`short-analysis-v2.json`/`long-analysis-v2.json`中`first_marker_ns`至`last_output_ns`，对应`P11_FIRST`至最后`P11_OUTPUT`。在`CUPTI_ACTIVITY_KIND_KERNEL`按`globalPid`筛选，与`StringIds.id=demangledName`连接，取符号包含`native_gu_swiglu_kernel`且与区间相交的行。将各行裁成`[max(start,lo),min(end,hi))`，按模板TG分组；排序并合并重叠区间后求长度。家族值另对全部格式求并集，不相加格式百分比。

离线复算和源码身份核对不证明GPU数值、未插桩性能、当前暖态依赖或质量非劣。没有为新方向补采样、补profiler、做语义原型或编译检查。

## 当前行动与重开条件

本轮文档收口后停止；不进入P02/P03候选开发，也不追加GPU。未来重开必须同时提供：独立新源码机制、当前真实暖态命中与可闭合依赖证据、可信局部方案及新增成本账，并支持完整请求净省时至少4%。还须说明原否决证据为何不覆盖新机制、资源/质量前提、新编号和限额合同。缺证据保持`DEFERRED_NEW_EVIDENCE`或`BLOCKED_EVIDENCE`，不自动触发新采集。

后续实施或GPU实验须由用户明确给出对应范围；本次文档授权不扩展为实验授权。

## 生产状态与本轮验证

文档收口期间仅用`jssh 29`做只读状态查询。2026-10-31 **12:40:17北京时间**（04:40:17Z）：`openclaw-qwen38-next.service`为`inactive/dead/enabled`，GPU 1MiB/42°C，无compute进程。没有写远端、启动/停止服务或运行推理；13保护文件及配置身份继续引用F03最终回执，本轮未重复hash，不将旧核验写成新核验。

文档检查记录保存在`workspace/frontier/astra-reassessment-20261031/PACKAGE_CHECKS.json`；主包/子包清单、相对链接、diff与历史保留检查的实际结果见该回执及`VALIDATION.md`。未运行无关游戏pnpm检查或native/CPU/GPU测试。
