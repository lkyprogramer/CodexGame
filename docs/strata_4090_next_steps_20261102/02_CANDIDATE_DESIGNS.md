# 候选设计：只保留有独立机制的最小研究

日期：2026-11-02。设计状态：`PROPOSED / NOT_AUTHORIZED_FOR_GPU`。

本文件是后续计划的设计依据，不是开关推荐清单。任何候选都尚未获得本机新性能或质量验证。事实与来源索引见 [01](01_RESEARCH_SUMMARY.md)、[05](05_EVIDENCE_SOURCES.md)。

## 1. 全局约束

- 原冻结合同 F：GSQ-RCO IQ3_XXS 混合包、INT8 KV、resident=20480、max-context=131072、另留4096 token安全余量、spec=4、spec-min-p=0.5、会话缓存6144 MiB总预算/4 slots；其余按 P6 身份原件。
- A0 指历史生产保护对象；B 指 P6 研究基线；A1 指候选二进制关闭路径；C 指候选开启路径。统计里的 A 必须显式绑定 B 或经桥接验证的 A1。
- 不升级生产，不改 unit/NGINX/18343，不操作旧回滚树，不安装驱动/CUDA，不降低资源保护门，不关闭 thinking 或缩短上下文换取成绩。
- 只批准文档不等于批准 GPU、降精度、改服务或下载新模型。未来实验须单独批准候选、身份、预算、端口和退出方式。
- 同一轮只准入一个候选、一个主要假设、一个主指标。新引擎版本、编译器、KV、resident、词表、COUPLED 和 HC 不一起改变。
- 原六项长检索 FAIL、P05 `BLOCKED_EVIDENCE` 和 `NO_QUALIFIED_CANDIDATE` 保留；没有新证据就停止，不自动补跑。
- GPU温度达到85°C、MemAvailable低于4096 MiB、外来GPU负载、身份/预算违约或OOM即停止。本包未核查当前机器是否空闲。

## 2. 分级与准入原则

| 路线 | 允许讨论的变化 | 不能偷换的结论 |
|---|---|---|
| F / E0候选 | 同数学、同分派、同规约的表示/内存/metadata变化 | 局部字节一致不能自动证明自然执行路径一致或任务质量合格 |
| T | target固定的草稿或调度机制 | greedy通过、acceptance提高或同一权重文件，不足以证明随机采样/回滚正确 |
| Q | HC权重量化、KV精度等产品取舍 | 不属于原合同“同精度无损加速”；相对非劣和绝对质量分别验收 |
| P | 冷读或长追加Prefill的单独目标 | 不在warm Decode失败后更换主指标；不能由TTFT改善外推持续Decode |

“可审查”不等于“有资格实现”。每张卡必须先说明：相对本机基线和旧负结果的新差量、真实任务覆盖、当前完成路径中的可省成本、新增成本、资源可容纳性，以及可否达到完整请求净省至少4%的机制依据。优先考虑有至少8%暴露份额且有可信消除方式的候选；不凭空假设局部可以快2倍。[S02、S03、S20]

## 3. Q1：HC_Q8 常驻权重量化

**问题。** 保持主GGUF专家包、KV与服务策略不变，仅将四类HC投影矩阵转Q8，是否在质量可接受时减少常驻读流量/显存，继而减少CPU miss或暴露搬运？

**新差量。** P24复用的是HC临时缓冲；Q1改变的是HC权重表示。P24不是Q1的直接否证，但“腾空间不一定更快”仍是必须继承的反证。[S09、S12]

**已知实现。** 当前主线 `src/core/native_dense.cpp` 已有 `STRATA_HC_Q8`，native IQ/CUDA默认关闭。审查入口还包括 `include/strata/core/geometry.hpp`、`src/kernels/cuda/gr.cu`。先核对P6是否具有同一实现；若需移植，列出最小差量和依赖，不以整包升级代替单变量实验。

**资源假说。** 指定四类矩阵按源码计算从1200 MiB变为637.5 MiB，另有25 MiB scratch，原始字节差537.5 MiB。它不等于NVML峰值下降量、可用专家槽增加量或请求提速量；必须测实际allocation、auto cache和完整执行依赖。`HC_REQ8` 是另一开关，不得混用。

**质量风险。** 上游A4000的4995个teacher-forced位置top1一致率95.4%、aggregate KL约0.0251；Agent片段KL约0.0779。不是128K长链质量证明，也不是“仅储存压缩无损”。[S12]

**最小研究顺序。**

1. 离线列出B、A1、C的HC格式、矩阵/量化元数据与分配账；保护其余资产、词表、KV、resident和tail-skip行为。
2. 另行批准Q分支后，用相同有效输入检查有限值、状态生命周期与长链质量哨兵；Q路径不能以E0逐bit为成功门。
3. 如有硬件阶段授权，再记录实际VRAM差、专家驻留/CPU miss/暴露等待、反量化新增成本；不手工增加slot凑“显存收益”。
4. 只有机制及质量前置证据支持时，才考虑正式完整请求对照。

**停止。** 不支持冻结资产；必须升级多项组件；额外scratch或反量化抵消；只见少搬字节未见完成路径下降；长链质量退化。若选择W-N，旧自然warm探针资格仍缺则停止；若事前另批W-C或W-T，则按其独立资格门判断，不要求先解决旧P05，也不宣称解决了旧P05。工作负载定义见04第3节。结果可为 `BLOCKED_COMPATIBILITY / NO_QUALIFIED_MECHANISM / BLOCKED_EVIDENCE / BLOCKED_QUALITY`，不是继续叠加Q4挽救。

## 4. T1：语言匹配词表与纯COUPLED，分成两个实验

### T1a 草稿词表

**机制。** 只缩减/重排draft proposal的词表，减少草稿头成本；target最终词表不缩减。默认包含CJK，英文词表上游声称约省110 MiB，但中文几乎不产draft。cyrillic并非中文/Java任务的通用优选。[S13]

**先做的离线证据。** 对已有脱敏原始token序列统计中文解释、英文标识符、Java代码、JSON工具参数和复制文本的覆盖；记录词表文件hash、tokenizer hash、候选token数和未覆盖位置。token覆盖只提供上限线索，不能推算acceptance或吞吐。

**最小变化。** 首次只比较冻结默认词表与一个有覆盖依据的现有词表，不做几十种裁剪搜索，不同时开COUPLED或改spec。若必须新建词表，工具和格式本身另审，不假装已获得兼容资产。

**门槛。** 草稿头确为足够大的暴露成本，真实任务语言覆盖合适；同target采样、完整验证/回滚合同成立；净 committed tokens/完整轮次时间改善，而不是仅草稿头更快。

**停止。** 中文/工具关键token覆盖变差；target词表意外受限；draft省时被低acceptance抵消；只有短英文样本收益；需要改变任务组成才能通过。

### T1b 纯COUPLED

**机制。** `STRATA_SPEC_COUPLED=1` 在现有exact-match链中耦合随机数，提高proposal与target匹配机会。正确算法下target采样可保持不变，但实际GPU/CPU舍入、批形状、状态和RNG消耗仍需验证。[S13]

**明确排除。** 不开启GUMBEL、不切换PROB/其他接受算法、不调target temperature/top-p/top-k、不改词表与spec。不得把纯耦合、重采样和改target sampler混为一个方案。

**已有反证。** 上游3060实验acceptance约62.1%→66.9%/68%，吞吐却未稳定提高；另有持平或较慢的配对结果。提高acceptance不是准入充分条件。

**最小研究。** 先逐段审计target/proposal随机数及reject/rollback；使用已有小回放合同，不新造通用框架。只在状态与采样语义合格、真实任务预计有完整时间净益后，进入自然采样对照。输出长度差异必须以任务成功/完整耗时约束，不能称同seed就等价。

**停止。** 无法证明当前接受算法的target保持；状态回滚不完整；自然路径变化无法归因；acceptance上升而完整耗时不降。

## 5. Q2：先k8v4取舍，再决定是否研究q4_0

**目的。** 将KV带宽/驻留/主存占用与质量放在一张前沿图上，而不是把Q4当默认升级。k8v4保留K为INT8、V用旋转Q4；也改变数值，不享有无损豁免。[S10、S11]

**最小对照。**

- Q2a：int8 → k8v4，resident固定20480，其余不变。
- Q2b：只有另行批准且Q2a证据支持继续时，int8 → q4_0，resident仍固定20480。
- “用节省预算扩大resident到32768”是后续独立实验，不能与格式变化同轮归因；auto expert cache的自然变化作为结果登记。

**预期资源，不是速度承诺。** 在20480 resident、12个QSA层的主KV项，int8/k8v4/q4分别247.5/191.25/135 MiB；主存逻辑全长和snapshot副本另算。不要把全逻辑KV差额当成显存释放。

**质量警示。** 官方Q2_0包上的q4文档PPL约+8%（1K）、+12%（8K），KL为INT8的2.6–4.2倍；needle5/5不替代100K代码/工具/长链质量。不能外推成我们的确定损害幅度，也不能视为无损。[S11]

**最小质量分层。** 中英证据检索、远距离标识符/精确复制、Java多文件修改与编译测试、工具JSON/参数、长链恢复、120K边界；失败分类与原六FAIL分列。PPL/KL只作诊断，不替代任务成功。

**停止。** 发生新的关键任务失败；只能靠减thinking/压上下文恢复；时间增益达不到预注册门；质量样本不足。若原六FAIL未解决，即使相对非劣也不得宣称生产READY。

## 6. T2：#4928 Lookup长窗口，仅面向实际复制/编辑

**新机制。** 长匹配才扩展验证窗口，MTP按块回放，预捕获图，并在服务端按tokens/ms比较宽/窄路径。PR需要wide build，`STRATA_LOOKUP=1`，仅single-slot路径。最大16个verify位置不等于spec4固定4倍；原spec4可能已有额外suffix位置。[S15]

**外部证据边界。** PR4928截至核查open/unmerged；2×P40复制任务约+23%、98.8%acceptance是作者场景结果，不能当4090结果。5090并未普遍获益，vision有约7%回退；Pascal大batch的长窗口错误通过门控规避，不是所有路径已修好。

**为何不能直接重开。** 旧#4040在本机负载可覆盖调用只约Decode0.8%，旧lookup2也无稳定收益。必须证明新PR扩大了真实copy/edit任务中的覆盖或消除了不同成本，不能只换PR编号。

**先做的离线判定。** 对既有输出/上下文做不改变执行的长匹配覆盖统计，区分固定文本、局部编辑、生成性代码和工具交互；计入查找成本、宽窗拒绝浪费、graph显存与额外kernel加载。不上传私有源码/转录。

**后续最小研究。** 固定PR head与编译标记，A1关闭/C开启；先验证off路径与B桥接，再验证on路径target提交、KV/GDN/PLE回滚、取消和下一请求。用真实任务加一个复制阳性对照，不能只用阳性对照声明产品收益。

**停止。** 真实分布覆盖不足；只在合成复制有效；编译/graph成本压缩专家缓存并抵消；无法维持单会话范围；跨batch/vision兼容性需要大规模修复。

## 7. T3：DFlash2与accepted-prefix成本，当前只保留服务化审查

**当前硬阻塞。** 固定main的 `strata_control/drafting.py` 中 `ENGINE_SERVES_DFLASH2=False`，服务路径会回退MTP。one-shot CLI成绩不代表Pi服务可用。PR4937仍open/unmerged，其主要运行证据是AMD gfx1201并发路径，CUDA未测；不能直接翻转布尔门或整包合并。[S14]

**预算反证。** 4060 Ti案例额外约1026 MiB DFlash同时保留约1049 MiB MTP，cache从3594降至3027；16K输入/16K输出，DFlash42.85 vs MTP47.64 tok/s。它不是4090/100K结论，却足以否定“新draft必快”。

**值得问的具体问题。** target tap、accepted-prefix replay与草稿资源能否避免重复常驻；额外head/body、KV和缓存损失是否小于少做verify的收益；single-session需求是否真的需要多并发serving改造。Strata已存在accepted-only MTP catch-up，不得再把它本身列为新发明。[S16]

**重新准入所需。** 有固定版本、真实CUDA SM89 served路径、兼容Flash-Next草稿资产、24GB/64GB完整资源账、随机采样与取消/回滚合同、以及本机任务覆盖的明确证据。缺任一项，保留 `BLOCKED_SERVING / BLOCKED_ASSET / BLOCKED_RESOURCE`，不下载巨型资产试运气。

## 8. P1：F05行窗scratch，必须另立Prefill目标

**机制。** P6非fused路径的GU/H/Xq/Hq按T×K分配，行窗可缩小部分临时量；它不是HC临时缓冲，也不是通用allocator重写。F06稳定整数grouping、F07 sizeclass/slab只作各自独立候选，不能一起打包。[S20]

**严格边界。** 保留全Dm、Qwen top10原combine、MMQ形状、row/scatter顺序、stream-K与规约。16384×10×2560×FP32的Dm单项仍为1.5625 GiB，这是保留尺寸，不是节省量。若为了行窗必须拆MMQ或改变自然chunk/分派，应重新分级，不再宣称整机E0。

**准入资料。** 真实任务冷读/长追加占比；现有分配尺寸序列与生命周期；可删除峰值而非闲置截屏；borrow/refill暴露成本；兼容AUTO_MAX16384及短→长→短、取消/重入。当前read291的warm追加不提供大Prefill机会。

**停止。** 原基线已复用该区；必须改Dm/规约；仅减少理论scratch未减少暴露等待；为获得收益必须把主指标从warm偷偷改成cold。旧F03零填、P24和通用pool项目不随本卡重开。

## 9. 不作为本轮候选的“看起来还有空间”

| 想法 | 暂不立项原因 |
|---|---|
| 复制tandem的Q8输入复用或deferred catch-up | Strata已有对应结构；额外共享/路由去重也有opt-in，先找真实新差量 |
| 直接换FreeToken或照搬semantic-anchor cache | 支持RTX40但Flash-Next文档的PLE pinned RAM达47.7 GiB；还缺同资产、100K任务、64GB资源证明。语义锚点只作会话层参照，不重开旧F03 |
| 照搬Basalt/Infernix整套引擎 | 当前主要目标SM120/120a；4090是SM89，编译、kernel与草稿策略不同 |
| 强制adapt-async或常驻RAM权重副本 | 当前已有条件默认、lend/retain/refill；旧Xeon反证保留 |
| 跨层动态expert cache配额 | 与已有same-layer替换不同，可能涉及异构尺寸、地址/graph稳定性；无必要性证据，非低风险参数 |
| 扫PCIe=0.19/0.30、线程数、spec=3…6 | 旧扫描已经收口；spec6未测不等于自动值得测 |
| 用route tail-skip提速 | 跳过专家改变target；冻结原行为，不能包装成无损cache优化 |

## 10. 当前决策

默认停在N0离线证据整理。若用户下一轮接受独立Q分支，优先只审Q1；若只允许原合同F，则继续收口，等待独立新机制证据。T1/T2不是Q1失败后的自动接力队列。

本轮没有预期提升承诺，也没有“全部跑完”的总任务。执行授权、资源预算、质量标准和探针资格未齐全时，正确交付是带原因的 `BLOCKED`，不是更多测速。
