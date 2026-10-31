# Strata / RTX4090 / 128K：下一轮极限优化的可执行边界

## 2026-10-31当前收口结论

P01/P01B诊断与F03审计已结束。Astra独立复核建议停止当前冻结合同下的性能探索，root采纳：当前NO_QUALIFIED_CANDIDATE，F02保持DEFERRED_NEW_EVIDENCE，取消原拟四小时审计。旧profile按实际PID/输出区间求并集，最大单格式TG21仅占2.2188%/2.1287%，且无已证load/layout新机制；该数据不是当前真实暖态严格上界，不外推全局NO_GAIN。详见[Astra回执](reports/ASTRA_REASSESSMENT_20261031.md)；完整报告位于父目录`reports/FRONTIER-CLOSURE-ASTRA-20261031.md`。

P01短输出停止、P01B执行COMPLETE/资格INSUFFICIENT、F03 NO_QUALIFIED_CANDIDATE、六FAIL和P05 BLOCKED_EVIDENCE保留。当前性能探索收口，不追加GPU或候选开发；6144MiB/4slots及PT0保持。生产随后按用户明确要求恢复运行，12:50:44为active/running/enabled、模型已加载；回执在父目录`reports/PRODUCTION-RESTORE-20261031.md`，旧停机记录保留原时间。未来重开须有独立新机制、当前真实暖态命中与可闭合依赖、可信净省时≥4%依据，并明确执行范围。

**以下1–6节保留2026-10-30作者原研究及当时建议，不代表当前待办。** 原研究基于固定仓库报告及源码，当时未连接目标机、未运行GPU推理、未修改生产；其中“一次诊断”建议已由后续P01/P01B执行历史替代，不可重复启动。

## 1. 结论：还有条件性空间，但没有已获资格的新性能候选

目前最值得做的下一步，是一次有上限的暖态长会话decode关键路径诊断。它要回答“实际阻塞下一批target token提交的工作是什么，其中还有多少能在不改变目标计算的前提下消除”。只有答案支持一个具体改造，才进入native实现。

这轮源码研究没有发现一个可直接移植并合理承诺本机收益的新开关或现成内核。多个看似新颖的方向，Strata当前基线已经有对应实现；另一些只在不同硬件、模型、精度或prefill阶段成立。Maya确实提供了三个有源码差量的窄实现参考，但它们尚未证明能改善当前主场景。完整排序如下。

| 层级 | 后续工作 | 当前结论 |
|---|---|---|
| 唯一下一次硬件动作 | 单引擎100K prime→两次真实warm append单会话的完成路径、活跃内存、必要KV与供给等待诊断 | 值得一次限额诊断；不是性能候选 |
| 需新热点证据 | 既有融合内的无损load/layout、canonical QSA读取复用/等序选择、实际重复驻留生命周期 | 可定义严格合同，当前不能开始实现 |
| 有具体donor差量，偏prefill | Maya中间group scratch、稳定整数分组、MMQ尺寸分级/slab | 保留条件分支；没有本机性能资格 |
| 数值/资产前置未满足 | CPU/GPU成本调度、TC数值核、兼容草稿/tree | 延期；原六项FAIL与正式质量前提仍在 |
| 独立产品研究 | 更低KV精度、少expert/top-k、进一步tail-skip、跳算、改模型/压缩上下文 | 改变目标质量；不能算本轮无损引擎提速 |

这不是对“所有软件优化都已穷尽”的证明。它是对当前证据能支持什么投入的判断。若唯一诊断没有发现新的足够大暴露成本，应以`NO_QUALIFIED_CANDIDATE`结束；不把未实现方向重新排成一轮全量开发清单。[历史处置](docs/01_EVIDENCE_AND_CLOSURES.md)、[64项逐项映射](history/V2_64_DIRECTION_CROSSWALK.md)、[候选合同](candidates/INDEX.md)。

## 2. 历史结果如何改变后续研究方式

### 2.1 搬运少了，完整请求仍可能更慢

P23证明HC真实保留了601个专家、专家H2D减少8,187,264,000 bytes；但报告中的暴露copy wait只少116.832126ms。refill wall的85.325113ms属于另一个量，不能直接相加当收益。P24正式对照最终得到100K TTFT改善0.824%，95% CI为[−0.035%,1.804%]；完整decode耗时反而增加4.428%。这个结果已经关闭HC性能候选。[P23](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P23-HC-RETAINED-EXPERT-COST-20261029.md)、[P24](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。

后续每项内存、cache、预取或scratch方案，都必须连通四层证据：减少什么工作，减少是否位于完成路径，是否产生新的资源/分派成本，完整请求最终是否更快。少搬GB、少分配GiB、局部kernel快一倍，只能证明其中一层。

P24所有20个引擎都出现major fault/system swap记录，说明下一轮有必要关注内存竞争及实际活跃页；这并不证明HC导致了swap，也不允许把有swap的样本事后剔除。只有关联到native地址空间和真实等待链，才能进一步解释因果。[P24](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。

### 2.2 微基准必须命中实际路径，数值通过必须与性能分开

NP-1a命中了引擎不走的分支；P5的IQ3_S VNNI在完整专家六对中改善−0.152%，CI跨零；P12 AVX2 gather完整专家耗时增加33%。这些结果不给扩格式、扩nt或再做gather默认资格。NP3也已经把早期“17µs固定同步”解释修正为主要是真实任务工作，不能再以旧归因为理由重写pool。[NP0/NP-1a](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-T7-NP0-20261025.md)、[P5](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P5-GU-VNNI-PROBE-20261027.md)、[P12](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P12-GU-GATHER-PROBE-20261028.md)、[NP3](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-NP3-TRACE-20261026.md)。

P13–P22建立的匹配分派oracle、有效区域逐字节比对、生命周期及memcheck经验可以复用；它们没有因为HC性能失败而失去价值。但这些工具证明的是数值、内存安全和执行合同，不会让候选自动获得速度或质量通过。[oracle](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P14-P15-NUMERICAL-REPLAY-ORACLE-20261029.md)、[生命周期](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P20-P21-HC-16K-LIFECYCLE-20261029.md)、[memcheck](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P22-HC-MEMCHECK-20261029.md)。

### 2.3 保留实际部署历史，也保留后来未通过的结论

生产记录仍是v0.2.3及早期配置/服务调整；KVRES在10月26日实际部署过，但P3的完整组合复测没有通过正式性能与质量门。不能删除部署事实，也不能用早期筛查覆盖P3。原六项长检索FAIL继续保留；P8/P9支持问题与当前模型/提示条件有关，但没有充分拆分基础模型和量化的影响。[部署记录](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-KVRES-20261026.md)、[P3](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P3-COMBINATION-KVRES-20261027.md)、[P8](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P8-INDEPENDENT-LOGITS-20261028.md)、[P9](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)。

“累计decode +23%、墙钟−9%”不作为新基准或整体实测。当前最有价值的基础，是一个更可信的对照体系及已排除方向，而不是一个可继续相乘的收益数字。

## 3. 这台机器的真正约束

本机不仅是一张4090：还有Xeon Silver4216、2×32GB DDR4、15个CPU pool worker，以及必须容纳现模型和128K状态的RAM/VRAM预算。模型包标为GSQ-RCO IQ3_XXS，内部专家格式混合；48层中36层GDN、12层QSA，每层512专家top10。不能用dense模型、不同CPU或另一IQ3_S包的瓶颈代替实际调用链。[环境](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/docs/02_ENVIRONMENT.md)、[P5](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P5-GU-VNNI-PROBE-20261027.md)。

QSA的selected attention宽度上限约2051，而非每次对128K全部历史做dense attention；已有split/merge、GQA和host页缓存。旧CPU微测曾接近当时DDR读带宽，但不是当前所有warm请求都达带宽下界的证明。下一次诊断需要分开实际expert计算、必要KV/expert搬运、GPU resident计算、主机供给与commit等待。[QSA接口](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/include/strata/kernels/qsa.hpp)、[现有attention](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_decode_attn.cu)。

局部收益的条件模型是：

`整体时间下降 = 暴露份额 × (1 − 1/局部加速比) − 新增不重叠成本/完整时间`。

例如暴露份额6%、局部快2倍、新增成本占0.5%，整体只省2.5%。这是推导算例，不能当实测预测。重叠CPU/GPU/copy区间不能简单相加；加快本来就先完成的一侧，可能不改变join时刻。[架构与上界](docs/02_ARCHITECTURE_AND_LIMITS.md)。

4090为SM89，必须在CUDA12.3和已有工具链能力内设计。Hopper/Blackwell的特定指令或执行机制不能靠删除架构宏获得；也不通过更新驱动、改内核模块、超频或改系统设置扩大本任务范围。[资源合同](docs/08_RESOURCE_AND_SM89.md)、[NVIDIA Ada指南](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)。

## 4. 外部引擎真正提供了什么

### tqLLM：新host-KV代码不等于本机缺失功能

对旧v2 pin到当前源码的差量检查显示，tqLLM确有compact selected-KV gather/cache更新。但Strata A0与P6的`kv_stream.cu`是同一个Git blob，已包含4cell页去重、epoch pin、CLOCK和向量搬运；P6的KVRES20480也已实际开启。直接移植“先聚到GPU再attention”的收益假说已经被现有覆盖削弱。[tqLLM实现](https://github.com/turbo-tan/tqllm/blob/b35b2ce9df8927c672f888651946849219a0effa/src/models/qwen/qwen4exp/qwen4exp_qsa.cu)、[P6现有实现](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/kernels/cuda/kv_stream.cu)。

后续若保留F01，只能针对证明存在的额外失效或resident attention内部重复load。注意resolve epoch仅保护本轮页，有效页跨epoch应继续命中；错误地每轮清缓存会制造新的退化。[F01](candidates/F01_KV_SELECTED_REUSE.md)。

### Maya：三个具体差量，三个明确否决条件

| 方向 | 拟保留的窄实现 | 关键否决条件 |
|---|---|---|
| F05中间scratch行窗 | 按原expert group生命周期复用GU/H/Xq/Hq；保留全Dm、原MMQ shape与K10 combine | MoE不是scratch union最大项；收益只来自改chunk/规约；更少借槽却未减少暴露成本 |
| F06稳定整数分组 | GPU count/rank → 原host placement/base/bounds → GPU scatter | 实际已走fused；mapped host成本被覆盖；新增扫描、发布和同步更贵 |
| F07 MMQ尺寸分级/slab | 先sizeclass；确有预算收益后再做带epoch/base/range/fence的借还 | 现有缓存已足够；sizeclass增加持有内存；稳态没有alloc；无法证明消费者完成 |

这些差量来自Maya GLM和共享prefill组件的具体函数，不是把整个Maya引擎当兼容补丁。完整GLM窗口combine会改浮点累加顺序；稳定GPU分组仍需要host计划和同步；slab也没有增加物理显存。它们主要影响prefill/长append，不能自动接替暖decode目标。[Maya prefill](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)、[整数分组](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/kernels/cuda/glm_batch.cu)、[MMQ pool](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/prefill/ggml_cuda_host.cu)、[详细对照](docs/07_DONOR_DELTA.md)。

### Edge0：预测路由与精确预取必须分开

Edge0 MLX路径可用训练的预测IDs/scores代替真实gate；实际专家未命中staged slots时还可能映射到零overflow。这会改变目标专家计算，属于Q。Windows resolver则保留true gate，并有ready/inflight/cold及原mmap fallback，是值得参考的精确需求合同。但其Win32 CPU IO不是Strata CUDA expert staging的现成实现。[MLX prerouter](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/python/src/edge0/prerouter/install.py)、[staged实现](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/python/src/edge0/streaming/layer.py)、[Windows resolver](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/windows/serve/prefetch.cc)。

Strata内部的GU融合、共享解包、QSA split和图执行已经存在；llama.cpp、HyperQwen、elpis、kern、spark可提供布局或验证方法，但没有新增同机同模型性能证据。F02/F04/F09/F10已把实际入口、ISA、数值、资源和停止条件写成候选卡，而非给出无依据的百分比预测。[引擎差量全表](docs/07_DONOR_DELTA.md)。

## 5. 下一步如何执行，如何及时结束

整合后的唯一初始诊断上限是1个引擎、3个工作请求、3600秒总墙钟，包括加载、冷却、采集和收尾。100K prime 后两次真实Pi短追问append，按用户决定记录实际新读量；各目标/上限2048输出，每请求最多600秒，预留120秒收尾。总输入加输出预算加4096余量不得超过131072。预算不是必须凑满的配额，条件不够时保留部分结果并停止。[诊断合同](docs/04_WARM_DECODE_DIAGNOSTIC.md)。

研究基线锁为P6 v0.2.7隔离树及其原六文件Python port，生产仍是v0.2.3保护对象。保持EXACT6、overlap、CPUSHARE4096、AUTOMAX16384、KVRES20480、reply reuse/PT0、spec4及采样配置。必须恢复原始资产和构建manifest，不能以最新main或P24 HC二进制代替。[P6](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P6-V027-BASELINE-20261028.md)、[身份锁](sources/LOCK.json)。

采集不能为了方便而打开会改变执行图的`STRATA_VERIFY_PROFILE`；设置0也不够，需删除该键并核实际PID环境。不同引擎的prime可能生成不同历史，同seed不保证轨迹相同，因此离线先冻结渲染配方，prime后才记录实际history/token hash。不同轨迹可以各自诊断，不能把时间差唯一解释为插桩开销，也不能从插桩臂推出无插桩的严格上界。[数值与轨迹合同](docs/05_NUMERICS_AND_QUALITY.md)、[P01](plans/P01_DIAGNOSTIC.md)。

本包用8个Phase、32个Task连接准备、诊断、候选选择、最小实现、数值/资源、正式性能、质量和归还。Phase串行，同Phase无冲突Task可以并行，目标GPU始终串行。任何硬门失败立即走P07；候选为0是正常终态。没有前置资格就不会自动进入下一卡。[执行DAG](plans/INDEX.md)。

## 6. “极致”如何落实到验收，而不是无限试验

本包把低层改造分为E0、E1、Q。E0要求在同输入、同实际分派下，canonical有效中间值、最终logits和全部相关状态逐字节一致；物理layout改变时先映射到逻辑坐标。若释放scratch改变了自然chunk、MMQ shape或CPU/GPU归属，则局部E0不能证明自然路径还是E0。E1需要数值和任务质量证据；Q单独研究质量速度取舍。[数值合同](docs/05_NUMERICS_AND_QUALITY.md)。

正式P05开跑前还必须有稳定warm探针的实际原件；当前资料未替该探针建立资格，缺失则不启动校准和主批次。若使用已验证的受控状态重放，须另列实验合同，不代替自然任务质量。

正式性能主场景固定为100K级warm append、2048输出探针、主指标decode_ms，六对fresh-engine。A/A噪声在候选结果前用同指标冻结；新门为主时间比95% CI上界≤`1−max(4%,2×A/A噪声)`，TTFT和wall的CI上界各≤1.02。该规则是本轮新政策，不反推修改P3或P24的原门。六对完整枚举46656个整对log-ratio bootstrap重采样；token/window不当独立样本。[统计协议](docs/06_BENCHMARK_PROTOCOL.md)。

4%的资格/改善门及8%的优先暴露份额是控制本轮投入的工程选择，不是宣称1%真实收益没有价值。下调门槛应事前形成新的目标、噪声和成本预算；不能在候选只快1%后改门挽救，也不能将多个未独立通过的小项相乘。当前资料不支持直接承诺最终tok/s或可叠加提速幅度。

真实任务另按成功与预算封顶时间评价，不能把更短回答或早EOS当加速。原六FAIL始终单列；两臂都错可能相对非劣，却仍不满足绝对质量。即使E0和性能研究通过，也最多得到`RESEARCH_RESULT_ONLY`，不会自动变成生产采用。[质量工具原规范](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/tools/QUALITY_GATE_README.md)。

## 7. 交付内容与使用方式

本包已合并到`docs/strata_4090_128k_lab/frontier`，从[START_HERE_AI.md](START_HERE_AI.md)开始。离线先执行`./run.sh validate`与`./run.sh test`。具体命令和能力边界见[工具说明](tools/README.md)。

本包包含完整规范、十二张条件卡、旧64项映射、源码/报告身份账、阶段任务、数据模板，以及可运行的区间并集、六对统计、文档与SHA256检查工具。随包fixture全部合成，并有P24舍入数字的方向性反例；不会被描述成新硬件样本。

live采集适配器没有伪装成已实现的一键执行器。P00/P01明确列出如何绑定原lab runner、保护/资源锁、SSE、窗口日志、oracle和评分器，以及最小需要新增的接口。原始模型、二进制、配置凭据和私有workspace原件不在包中；缺失时停在`BLOCKED_EVIDENCE`，不虚构输入。[工具绑定](docs/10_HARNESS_BINDINGS.md)、[执行限制](docs/11_LIMITATIONS.md)、[最终交付验证](VALIDATION.md)。

这份文档集合的完成条件，是让下一位执行AI知道每一步为什么值得做、具体改哪里、怎样证明、何时停止，并且能在没有合格候选时正确收口。它不以完成所有方向、重新开启生产或把GPU占满作为进展。
