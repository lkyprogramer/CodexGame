# 历史结论与禁止重复清单

研究截至 **2026-11-15（北京时间）**。本包是源码差量研究与未来执行规格，不是新性能实验回执。**本包硬件运行、GPU、服务启动、推理HTTP预算均为0；所有未来实验均未执行。** 旧实验的失败、已消费窗口、关闭状态和质量缺口继续有效，不能继承剩余额度。

## 1. 身份分层：源码、历史候选、部署不是同一件事

| 对象 | 固定身份 | 能证明什么 |
|---|---|---|
| NInfer公开分支 `b0-scanner` | [e0b05f7cb46adae2787be2ccbe605e1b0c9b3923](https://github.com/lkyprogramer/ninfer-4090/commit/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923) | 2026-09-30源码与G1 differential driver；不是10月P1—P4隔离树，也不是当前运行镜像。 |
| 用户实验档案 `CodexGame/4090-report` | [fbc24c2603c2eca4bfbeca628c6c2476b7516bdc](https://github.com/lkyprogramer/CodexGame/commit/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc) | 受版本控制的历史报告与计划；HEAD为11月4日PT0版本对照收口。 |
| NInfer九月B0+B1部署 | [9月30日上线记录][b01] | 历史镜像含B0/B1，不是e0b05f7重建；该回执不能证明11月15日在线身份。 |
| NInfer十月P4 | [P14实机对照][p14]：BO树6022c83a205853c65510af0b46f0dc337733cbeb、P4树35d3dd9e4aa96b1f56f2e9c55482946bd9911cde | 该隔离版本的实测，含legacy rk4v4-e8→midrise rk4v4；不能拼接成当前b0生产单因素收益。 |
| Strata上游 | [13eedf552417a6a791a7d13c6597e24300ee3a09](https://github.com/Niko1221/Strata/commit/13eedf552417a6a791a7d13c6597e24300ee3a09) | 源码当前能力；不证明用户二进制已包含。tag对象与release engine source必须分开，见本包source_lock。 |
| 当前部署 | **SOURCE_UNBOUND / null** | 未读取当前PID、运行镜像/二进制、模型/draft、完整参数及真实请求原件；不得自行补齐。 |

记忆中的三个提交均已核实存在：[fff68474e758178bd67cb0375a1f170d8007bb3b](https://github.com/lkyprogramer/CodexGame/commit/fff68474e758178bd67cb0375a1f170d8007bb3b)保存版本对照，[93f925a0b9e1bb6ae1fbf0f46c6cdb183d3c29d4](https://github.com/lkyprogramer/CodexGame/commit/93f925a0b9e1bb6ae1fbf0f46c6cdb183d3c29d4)归档旧Q8 DFlash2资格及CPU stop，[d56907ce249003b855dc043f50eb1e743ff869e3](https://github.com/lkyprogramer/CodexGame/commit/d56907ce249003b855dc043f50eb1e743ff869e3)为D1T截点离线handoff。三者均不是当前HEAD或新版服务采用证明。

## 2. 已有NInfer能力：先扣除，不重复开发

| 已有机制 | 固定证据 | 本包边界 |
|---|---|---|
| 六个dense body GEMM的INT8 activation prefill | [4090 prefill历史][perf]、[variant][variant] | 115125token、480W/CUDA13.2历史报告1739→2496.1tok/s；仅prefill A8，decode/verify仍A16。不能称本轮收益或无损量化。 |
| rotated/E8 KV、默认rk4v4-e8、262144容量 | [KV kernel][kv]、[产品合同][agents] | rk4v4读端为PackedK unpack；不把rk2 E8Root decode成本归给rk4。更低位宽不自动更快。 |
| MTP3历史配置、greedy proposal、完整Target采样与accept、131072行proposal head | [MTP执行链][mtp]、[Target verifier][verify]、[B0+B1][b01] | 进一步裁剪不等于首次裁剪。源码K≤5/W≤6已存在；不能将W6作为新实现。 |
| KV＋GDN recurrence/conv＋hidden＋MTP完整continuation，L1/L2/L3 | [cache合同][cache]、[Program事务][program] | 不是仅attention KV缓存；rollback不能只截KV而忘GDN/hidden/draft。 |
| B0单调added-token扫描、B1 selected-token restart、局部边界校验与memo | [processor][processor]、[上线记录][b01] | 不再把避免全前缀重复分词列新路线；prepare_tokens是已有诊断接口，不冒充真实serving输入。 |
| P1—P4 small-T/前端/codec/工具流隔离整合 | [10月25日复盘][retro]及[P14][p14] | 有功能/数值/Graph成果；后续已经有整包实机AB，不能继续引用更早“没有任何整包AB”作为当前结论。 |

H2现有轻头的真实链是：[variant.h::draft_head_rows=131072][vh] → [bindings.cpp绑定Q4G64_F16S的text/draft_head及I32 token映射][binding] → [TextContext::proposal_argmax][text]执行linear→argmax→proposal_remap_token_ids。它是静态131072行Q4 head，不是动态稀疏shortlist；进一步低秩筛选/稀疏投影在最终历史中仍属既有H2计划，不代表固定资料以外从未做过。

## 3. NInfer九条具名路线：范围、结果和关闭边界

以下数字全部来自**历史VERSIONED_REPORT**，未在本包重测。九行按机制归并，不把重试、shape、接续窗口拆成新路线。综合权威为[10月25日最终复盘][retro]；H1/H3分别采用较晚的最终回执。

| 路线与原合同 | 最终历史结果 | 保留状态／禁止重复 |
|---|---|---|
| C0：无SHA-NI时接OpenSSL EVP；320MiB SHA、合成L2 publication与真实L2试点 | SHA 2.1491倍、合成发布耗时−53.12%；真实两侧恢复55293token，TTFT943.552→959.943ms，但alias/输出控制不成立，INCONCLUSIVE | CPU局部有收益，TTFT未证明；原窗口关闭。不以发布解耦继续C0扫测。 |
| K2-T05：卷积直接写Q/K/V；T1024算子、完整prefill及Chat | 算子段耗时−36.4834%，完整prefill仅−0.313951%；两对Chat观察−0.881/−0.362% | 局部有效、整链门未过，保持原发布路径。不把36%当TTFT收益，不补样本。 |
| H3：已有W6/K5对W4/K3，C1、262144、rk4v4、自然proposal、真实remaining budget | [最终接续][h3]：Java/中文完整round ms/committed token改善22.75/20.38%；Java后半反向+13.75%，稳定门失败 | **已测且平均有收益，但固定W6关闭。** 不称无收益/生产提升，不追加Chat、扫K、W8。 |
| GQA：T4 Bc32/8warps→Bc64/16warps，同数学、rk4v4、8K/32K/128K | 32K耗时−14.865%，32/32对更快；8K+14.516%、128K+0.156% | 整体首筛失败，不采用，不挑32K重开。spill不是绝对否决，完整Op净结果才是依据。 |
| K2-T01：gated RMSNorm CTA128/256/512，T1/T4 | 四组配对中位改善+1.20/+5.76/−3.43/+4.98%，胜批不足 | 数值/Graph通过，无稳定采用信号，保持512。改block值不是新机制。 |
| K1：GDN correction Record＋Fold，提交1/2/4列 | 改善−1.054/−0.071/+0.181%；另增约9.785MiB记录载荷 | 同范围正确性成立、整段无益，未接产品。不只取Fold，不借新stream复活同设计。 |
| H1：请求内4-gram、8192token ring、K3整包替换，mandatory MTP仍做 | [H1最终实机][h1]：47/128轮命中；122/141 draft接受86.52%；ms/token慢6.98/4.28/8.11% | 机制工作但无净益，原profile结束。复制/工具正例撞repetition guard，保留失败但不误称新质量缺陷。 |
| 随机MTP＋完整条件q、独立proposal RNG、精确accept/residual | [最终随机q][sq]：Java/中文Program每token慢1.75/0.67%；工具每token快3.11%但整请求4.355→5.053秒、输出649→808 | 数值能力有成果，无稳定任务净益；分布/penalty/cache资格缺口仍在，方向关闭。 |
| Q4 SwiGLU紧凑shared布局、4/5级预取、T4 | 两候选耗时+0.583/+1.325%，理论仍3CTA/SM | 省shared未跨驻留档，本次不采用。换tile/阶段数重扫不是新路线。 |

H1的raw正例已达3.880/3.944正式token/轮，K3最大4。即使假定相同轨迹、相同单轮成本，**仅提高接受量**的节时空间也只有约3.01/1.39%，低于原5%信号门。这不是全部lookup永久无效，而是不能再用同K3高接受正例证明大幅收益。

W6失败不等于W16必败；但W8/W16、Suffix＋MTP、27B DFlash2、H2 head、H7 ring外检索、K3 workspace/fork-join和S0 utility都已在[extreme v2][v2]／[post-W6候选复核][post]中。v2九月修订候选保护容量200192，不是生产262144；rk8v4与DF2 W8还争同一显存余量。它们不能被冒称本包首次规划。未发现较晚回执≠从未执行。

## 4. P14已有真实归因：使用较晚结论，不能再从零做大平台

[P14][p14]对P4两个短窗的Graph归因如下，分母为完整round wall；plain/trace同端token轨迹一致，观测开销0.058%–0.359%。这替代更早“阶段成本全null”的说法，但不是当前b0/rk4v4-e8或100K+warm占比。

| 阶段 | Java | 中文 | 不能外推的内容 |
|---|---:|---:|---|
| Target主体 | 79.32% | 79.76% | 仅embedding/各层/末端norm合计；FFN/GDN/attention内部仍未知。 |
| proposal head＋AR | 9.51% | 9.56% | 不能全部归head，也不能全部移除。H2只能减少其中一部分并新增筛选成本。 |
| Target head＋accept | 6.29% | 6.32% | Target完整分布仍权威。 |
| MTP alignment | 2.35% | 2.36% | T4缩T1不自动省75% MMA，已有Tile8。 |
| commit/Fold | 1.53% | 1.47% | 理想全部消除也仅约1.5% wall；不自动重开K1。 |
| 入口出口 | 0.086% | 0.116% | 只对应本驱动窄边界，不是所有host成本。 |
| 未归因wall | 0.916% | 0.402% | 包含driver/host/等待，不是纯CPU执行。 |

P14两个native样本每轮成本均约+2%。中文单位token成本−40.19%来自该样本token/轮2.125→3.625，不是主体每轮更快；生成已分叉。四Chat wall合计+34.95%，故未证明整包普遍加速；单seed短窗不授予p95、稳定业务收益或生产资格。

### Export/publication修复已经存在

P14定位P4单publication worker：前CPU发布阻后GPU导出，后导出通过lane barrier阻C1准入；观察queue约684/1092/3036ms，queue本来含restore，不可再相加。不能把全部发布耗时归SHA。

[同日较晚隔离修复][export]已实现**导出线程＋单槽有界交接＋FIFO发布线程**，保留GPU fence、lane reader、alias CAS/合并、发布序及关闭排空。最终tree7477294d629edffddef713d22c2d7589493d4271，CPU 10/10、serve可构建，状态CPU_VERIFIED_BUILDABLE_HARDWARE_NOT_RUN。后续[HTTP对照prep][exportprep]已冻结空账本，状态CPU_ONLY_PREPARED_FROZEN_NOT_EXECUTED。

因此：实现存在，不再规划从头开发；实机queue/TTFT/内存峰值和真实drain仍未验证。不复用旧freeze直接运行，不把CPU通过改写为发布或性能PASS。

## 5. Strata闭环：已采用、已关闭、缺证据分别保留

| 历史项 | 结论与合同范围 | 本包处置 |
|---|---|---|
| A0/EXACT6、reply reuse/PT0、CPUSHARE4096、AUTOMAX16384、KVRES20480 | [关闭台账][closures]保留历史应用/部署；P3正式组合门未过，分项累计不可相乘 | 已有底座，不重做“首次调优”；当前在线身份另核。 |
| F02 GU load/layout | [Astra收口][closure]旧P11 GU-SwiGLU家族并集6.8911/6.5884%，最大TG21 2.2188/2.1287%；四小时审计撤回，DEFERRED_NEW_EVIDENCE | 不是新收益，非当前warm严格上界；不能拼格式凑4%或换tile续跑。 |
| P01/P01B | [P01B][p01b]自然EOS三请求、939窗口/2291tokens；warm verify返回→commit进入gap仅0.1340/0.1224% | COMPLETE只指采集，候选INSUFFICIENT；只关闭窄gap，GPU/CPU完成内部依赖仍UNKNOWN。 |
| P24 HC | [关闭台账][closures]20引擎24请求；少搬约8.19GB，TTFT点改善0.824%/CI跨0、decode耗时+4.428% | 不采用、不组合；少字节不等于少关键路径时间。 |
| NP3/pool/任务数、并行quant、cost row/repark | [关闭台账][closures]无稳健净益，trace纠正大固定开销假说 | 不借新donor线程池/调度名称重开。 |
| SPEC3/4/5、SPECCOST、learned profile、lookup-chain2 | [关闭台账][closures]微益或裁短窗口同步减少提交 | 保留原策略；新PR/阈值/seed不是新机制。 |
| F03、P5 VNNI、P12 gather、旧PCIe/trim/MMAP/KVGROW | [收口][closure]与[台账][closures]保留原否决、范围和未知 | 不删合法owner，不改ISA/nt/allocator名称续跑。 |
| 旧DF01 Q8资格 | [DF01合同][dfplan]：D1S n2300第4token失败，D1U只定位因果边界，无已证单点修复，STOP；D1未过/D2未开始 | 旧FAIL/reference不改，不沿未用预算续跑。 |
| 后来v0.2.10 DF2服务验收 | **USER_REPORTED_PENDING_ARTIFACT_BINDING**：14请求/2engine摘要，固定输出、EOS、短追加、保存恢复、取消通过；任务墙钟无净益，KEEP_MTP_SPEC4 | 这是已测、功能通过但不采用，不重新列未测；不可被旧Q8 FAIL覆盖，也不能把它提升为独立读raw复测。摘要未在锁定HEAD归档，保留来源级别。 |
| 六项长检索FAIL、P05 warm-fixed2048证据阻断 | 历史质量失败保留；P01B自然EOS、P24五token append不构成warm-fixed2048原件 | 恢复成功≠答案正确；新观察器/CPU合同PASS不解除。 |

## 6. 本包统一状态及其真正差量

| 卡 | 统一状态 | 可保留的窄差量／不能声称什么 |
|---|---|---|
| D1 | **NEW_MECHANISM_CONDITIONAL** | [OSAKANA copy planner][copy]的source anchor、prompt-source约束、edit repair、失败让路，以及避免先生成后丢弃neural draft，有源码机制差量。泛lookup/H1/H7并非新路线；增宽verify与省draft要分别归因。 |
| H2 | **PLANNED_NOT_RUN_SOURCE_REFINED** | [YASAKANI head源码][yhead]的低秩近似筛选→shortlist→候选集重评分，可细化既有H2；不是本包首次提出裁head，亦非原head全词表精确top-k。 |
| K-PAIR | **SOURCE_BOUND_PAIR_P3_DELTA_UNBOUND** | b0有真实small-T共输入Q4/Q5 pair；P3后续真实分派未绑定，仅源码核查卡，无GPU预算。 |
| M0 | **UPSTREAM_IMPLEMENTED_DEPLOYMENT_UNBOUND** | Strata终止窗口修复上游已有；只做当前部署身份与精确跨请求状态绑定，不重复实现或假设用户当前有bug。 |

### D1不能靠重命名越过H1

必须在同来源、同宽度条件下区别“有/无anchor与edit repair”，分开测源位置选择、重命中延迟、索引/查询成本。ring外来源属于既有H7邻域，不自动算新；W16/W64属于既有宽窗计划，不混入planner消融。OSAKANA的copy先命中能避免本轮后续drafter proposal，但**不等于免除MTP conditioning追赶**；fallback、restore、cancel时hidden/KV/position仍须正确，不能只看CPU选择标志就称GPU旧成本没执行。

### K-PAIR已经有的融合和sm89 guard

NInfer full attention已将Q/K打包为Q4 query_key、gate/V打包为Q5 gate_value；[small-T launcher][apair]仍两次launch。GDN T1..16也有[Q4/Q5独立launch][gpair]；大T GDN已有Mixed grouped MMA，gate/up已有linear_swiglu融合，a/b控制已有paired gating，不能泛称首次合并QKV/gate-up。

GDN函数虽名launch_t4_pdl，但[src/CMakeLists.txt][cmake]对arch86或89定义NINFER_SM86=1；[core/pdl.cuh][pdl]据此退化普通launch、trigger/wait为空。**4090不能凭PDL函数名宣称已重叠。** TensorFold同grid多member机制只能在P3实际目标仍保留该pair且成本有依据时讨论；不得移植不兼容codec或只把两kernel套同host wrapper冒称少launch。

### M0必须绑定committed input rows，不只是HTTP输出

[上游helper][stop]与[真实serve loop][generate]按剩余max_new和首EOS限制**已提交输入行**；最后一个已曝光output仍是下轮未消费token。调用形态为serve_stop_bound(a+1,…)-1后commit(a+1)，merged prompt窗口有意不裁，不能写成随意截前N个输出。

旧DF01合同已要求EOS、预算、有效前缀提交和草稿截断恢复，用户新版服务摘要也有PASS；但未绑定“remaining<accepted窗口＋窗内EOS＋下一请求不fallback”的精确原件。已有helper穷举CPU单测不等于跨请求continuation正确；本包不能把它重复实现当新成果。NInfer自身也已有partial-terminal hidden correction、按committed列GDN Fold和KV trim，不应首次补建。

## 7. SOURCE_UNBOUND与重开门

以下保持null/未知：当前运行二进制/完整flags；实际模型、draft及codec身份；用户报告代码148.6、混合106.5tok/s对应完整请求原件；P3最终projection分派；新版DF2全部raw；Strata当前部署是否含M0；旧材料之外是否另有后续执行。不使用5090 donor表格、旧115K prefill或P14别合同数字填空。

任何未来候选开始前至少交付一行：**固定donor symbol → 实际目标symbol/shape/codec → 旧实验ID和否决原因 → 本次机制差量 → 为什么旧证据不覆盖 → 当前关键路径成本/可省上界 → 状态/质量/资源前提 → 新授权及独立停止条件**。缺一项则DEFERRED/SOURCE_UNBOUND；换SHA、项目名、宏、seed、tile、改门槛都不是充分差量。CPU、数值、服务、性能、任务质量、采用六轴分开；本包不授予未来运行权限。

[b01]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/openclaw-qwen38-ninfer-b0-b1-20260930.md
[retro]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-retrospective-20261025.md
[p14]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-p14-performance-hardware-20261025.md
[export]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-export-pipeline-20261025.md
[exportprep]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-export-pipeline-prep-20261025.md
[h1]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-h1-hardware-20261024.md
[h3]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-h3-w6-resume-20261024.md
[sq]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-sampled-q-resume-20261024.md
[post]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/ninfer-v4-post-w6-selection-20261024.md
[v2]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/qwen38-4090-ninfer-extreme-v2.0.0/README.md
[closure]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/reports/FRONTIER-CLOSURE-ASTRA-20261031.md
[closures]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/frontier/docs/01_EVIDENCE_AND_CLOSURES.md
[p01b]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md
[dfplan]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/plans/DF01_DFLASH2_TEST_PLAN.md
[agents]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/AGENTS.md
[perf]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/docs/performance.md#rtx-4090-sm_89-long-context-prefill
[variant]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/variant.cpp
[vh]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/variant.h
[binding]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/load/bindings.cpp
[text]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/text_context_impl.h
[kv]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/kernel/gqa_attention_decode_i8.cuh
[mtp]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/mtp_impl.h
[verify]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/speculative_target_impl.h
[cache]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/docs/continuation-cache.md
[program]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/program_impl.h
[processor]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.cpp
[apair]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/attn_input_proj/q4_q5/q4_q5_attn_input_small_t.cu
[gpair]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/gdn_input_proj/q4_q5/q4_q5_gdn_input_independent.cu
[cmake]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/CMakeLists.txt
[pdl]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/core/pdl.cuh
[stop]: https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/core/serve_stop_bound.hpp
[generate]: https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/src/program/generate.cpp
[copy]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/common/speculative.cpp
[yhead]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/q35_bdraft.cu
