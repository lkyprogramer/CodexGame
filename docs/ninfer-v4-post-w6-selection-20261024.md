# W6收尾后：结合V4原候选的下一方向评估

2026-10-24。本轮为研究与准备：通过 `ssh -J jump 29` 只读核对当前源码和停机身份，复用已有实测，重新比较V4原候选。没有实施候选、构建、GPU计算、模型或HTTP请求，没有修改原计划入口、注册表或既有证据。

**下一项小范围实验建议选择长上下文T4 GQA的key tile：固定C1/W4/K3、rk4v4，将现有Bc32与单一Bc64候选比较。它属于原V4的 `kernel_candidate`，不是新增必做阶段。** 这是根据具体可改位置、实际长上下文覆盖和验证成本作出的选择，尚不能称为当前最大瓶颈或收益最大的方案。

**若优先追求较大的结构性收益，原计划里的DFlash2比继续细调kernel更值得保留；但其新增资产、状态链和容量要求明显更大。** H2草稿head、H7全局检索、K3和S0也没有被否决。当前没有证据支持某一方向同时满足“很小改动、稳定大收益”，应明确这个限制。

## 1. 原候选不是遗漏后的新待办

权威依据是V4的[可选实验](ninfer-flare-v4-md-20261021/plans/11-optional-performance-experiments.md)、[14类发布scope](ninfer-flare-v4-md-20261021/plans/03-release-scopes.md)和[任务合并关系](ninfer-flare-v4-md-20261021/plans/10-task-scope-audit.md)。DFlash2、全局检索、W8/W16、utility明确保留为可选candidate，不能统一降成“仅研究参考”。历史任务文件标为wrapper/ARCHIVED也不等于对应性能机制被删除。

下面的投入是方案量级，不是本轮实施授权或自动排队顺序；不能把各行相加成一轮完整改造。完整任务映射、状态和来源见[原候选复核](../output/ninfer-v4-post-w6-selection-20261024/v4-candidate-inventory.md)。

| 原候选 | 仍可能改善什么 | 当前选择判断 | 准备/实现量级 |
|---|---|---|---|
| K2 GDN小窗口预载 | 降低重复输入读取、等待或同步 | 已核实state常驻与滚动next-key预载，剩余Q/V/gate预载未验证。旧Record＋Fold段约0.707ms，仅作条件收益尺度，暂低于长GQA优先级 | 单一候选约0.5–2工程日 |
| K2 small-T/路由；本轮具体化为T4长GQA | 减少每层长context key循环和online softmax更新开销 | **建议下一项小实验**；有现成同kernel Bc64机制，仍有occupancy与浮点分组风险 | 可行性4–6小时；可构建补丁、驱动、BO和评审合计约6–10工程小时 |
| H2 draft head裁剪/稀疏投影 | 减少串行proposal的权重读取与投影 | 值得准备，但已存在131072行Q4 head，不能重复称首次裁剪。新profile须同时证明覆盖、接受损失和head成本 | 1–3工程日；先一个profile的离线覆盖/成本检查 |
| K3 workspace生命周期复用 | 释放真正互斥scratch，缓解容量或实际分配/恢复开销 | 无当前allocator高水位；不能承诺短C1 decode变快。需GPU最后消费者/Graph逃逸证明 | 1–2工程日 |
| K3有限投影fork/join | 缩短独立投影的关键路径 | 缺独立性及资源余量证据；不要拆已有融合来制造并行。必须包含join和争用 | 0.5–1.5工程日 |
| H3 W8 / H4 W16 | 提高每轮正式产出，减少Target轮数 | W6有平均收益但稳定性不足；既不证明更宽必败，也不足以直接升级。W16先复用W8整链技术与状态证据，生产发布资格仍独立 | W8约1–3日，W16在其后另1–3日 |
| H6 DFlash2 | 并行块draft替代串行AR，改善草稿成本和接受深度 | **结构性潜力较大，范围也较大**。匹配27B资产已存在；本机27B仍`DFlashConfig::supported=false`。先资产/特征/容量静态核查，不加载、不降context或换codec凑空间 | 静态检查约4–6小时；资产适配准备好后的实现约3–7日 |
| H7全局历史检索 | 找到请求内8192-token ring之外的有用草稿 | H1失败不能否决它。先证明ring外增量命中，再计查询、搬运、位置和DraftKV重建成本；B29没有真实token IDs，不能把其文本当完整token语料 | token-only约1–3日；feature版另依赖合格H6 |
| S0有限utility/restore规则 | 在已有合格路线中选择较便宜的宽度、backend或恢复方式 | 对C1也可能有效；不是只有并发才有用。W6产出变化是线索，但未验证width切换，不能直接复活固定W6或新增调度平台 | 有至少两条合格行为后约1–3日 |
| UP选择性/完整上游U34 | 吸收当前Chat可达的性能修复或必要耦合 | P1—P4已吸收U01—U27。剩余U28—U34尚无直接纯Chat收益证据；P5有9处冲突，不能当可构建候选。完整合并仍是条件选项 | 选择性约0.5–2日；完整约2–5日 |

DFlash2固定资产包含约19.244亿BF16参数，紧密权重约3.85GB，尚未包含工作区、特征、KV或Graph；这不是实测加载峰值或本机可容纳证明。复用[既有固定资产核查](ninfer-v4-performance-primary-research-20261024.md)及其[配置revision](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/blob/50307d4c4cde6860d4eee73e2547cd786fe8e8a4/config.json)，本轮不下载权重。原[统一预算](ninfer-flare-v4-md-20261021/plans/08-validation-budget-and-estimate.md)是工程估算，不能直接转成新GPU额度。

## 2. 现有结果改变了哪些判断

[W6最新实测](ninfer-v4-h3-w6-resume-20261024.md)不是“完全没有提升”：Java和中文短样本单位正式token的完整轮耗时分别下降22.75%和20.38%。但Java前后半段为改善48.20%与退化13.75%，没有满足冻结稳定门槛；两路生成序列也已分叉。固定W6按用户要求关闭，不追加补测。它说明草稿产出是可能有大收益的成本项，也说明接受率/路径变化能吞掉优势。

其余具名实验——C0、gated RMSNorm CTA、correction Record/Fold、T1024卷积写QKV、请求内Lookup、随机MTP、Q4紧凑布局/五级预取——保持关闭。P1—P4没有完整旧版到新版性能AB，不能因此称无效，也不补跑旧Baseline。

这次按源码排除了三种“看起来省很多”的重复方向：

- Q6 head已经一次解码权重并跨4列复用；不是首次增加跨列复用。既有MMA与SIMT的权重舍入不同，也不能作为逐bit无风险替换。
- MTP的T1/T4重型W8投影都使用同一Tile8 MMA。把alignment输出从4列缩成1列不会自然减少75%的实际MMA指令，且许可历史KV仍须写入。
- GQA已有Tensor Core和多query/KV复用。本轮只研究具体key tile，不把已有能力算作新改造。

原K2-T02的GDN预载也已追到真实Record调用：当前代码在query readout之前加载下一token的key，state贯穿窗口驻留寄存器。更广的W4 raw输入预载估计会增加约32个32bit寄存器/线程，尚非ptxas结果。复用[K1历史计时](ninfer-v4-k1-graph-r2-20261023.md)，48层raw Record＋1次Fold约707.456μs；假设整个段快20%，相对旧B29约23ms轮指标仅约0.6%的条件尺度。它不是当前H3占比，预载也不能节省整个段。因此保留这个原候选，但不把它列为大幅decode提速的首选。[当前GDN源码见证](../output/ninfer-v4-post-w6-selection-20261024/gdn-source-sha256.json)确认两份recurrent文件与已保存源码一致。

证据分别见[当前MTP消费链](../output/ninfer-v4-post-w6-selection-20261024/mtp-source-audit.md)、[kernel核查](../output/ninfer-v4-post-w6-selection-20261024/kernel-source-audit.md)和[官方资料交叉核查](../output/ninfer-v4-post-w6-selection-20261024/primary-research.md)。独立研究曾优先考虑Q6现成SIMT/MMA对照；综合其额外BF16舍入、已复用权重及缺少明确绝对节省，本报告将其保留为备选，没有自动启动另一项实验。

## 3. 为什么这次选长上下文GQA

复用B29原始CSV作离线分析，没有新请求：同copy_patch、O512、cold、production-sampling参考中，`timing_decode/speculative_rounds`从P256约22.78ms到P131072约29.26ms，P253952约34.28ms。它是旧B29聚合字段，不是当前H3逐kernel时间，也不是可靠round wall，不能把全部增量归因给GQA。见[离线计算](../output/ninfer-v4-post-w6-selection-20261024/baseline-context-observation.json)。

39条HTTP200的Pi teacher-forced记录中，26条prompt≥8192、7条≥32768、5条≥131072，中位16011、最大259511。HTTP200不代表质量通过；另5条已知容量/语料拒绝继续保留。这说明长上下文在既有证据中确实出现，不证明线上频率或新候选覆盖全部Pi。见[逐条长度与输入SHA](../output/ninfer-v4-post-w6-selection-20261024/baseline-pi-context-coverage.json)。

当前源码的实际差异如下：

| 项目 | 原T4路径 | 单一拟议候选 |
|---|---|---|
| 模型形状 | 24 Q heads、4 KV heads、group6、head_dim256 | 相同 |
| key tile | Bc32，8 warps，MinBlocks2 | Bc64，16 warps，MinBlocks1 |
| arena | static | dynamic |
| 长度 | 8192 / 32768 / 131072 visible keys | 完全相同；位置N−4..N−1 |
| KV codec、split policy | rk4v4、原规则 | 保持；不为结果改split规则 |
| 比较单位 | partial＋reduce整Op | 同样整Op，不只取partial |

源码已有T6在2K–8K使用Bc64，但更长context又回到Bc32；这也是重要反向证据，不能把T6路线当T4长context已经成功。Bc64减少key-loop/online更新次数，不减少KV总字节或主要有效QK/PV算术。共享内存按源码数组推导约43,648B→78,992B，尚未含编译对齐；更低CTA驻留、register和同步成本可能抵消全部收益。必须在BO资源检查后才判断候选是否可运行。

范围限定在已有launcher/kernel的显式实验入口及已有Op bench；不改产品默认分派，不复制Flare运行时，不改Target sampler/codec/资产。确切源码见[launcher](../output/ninfer-v4-post-w6-selection-20261024/source/src/ops/launcher/gqa_attention_decode.cu)与[kernel](../output/ninfer-v4-post-w6-selection-20261024/source/src/ops/kernel/gqa_attention_decode_i8.cuh)。

## 4. 数值与真实调用边界

Bc64改变online softmax分组和中间舍入，**不能承诺原/候选跨route逐bit一致**。这不是放宽旧实验断言：新假设从开始就采用现有GQA公共FP64合同，三项原阈值保持`relative_l2=3.15e-3`、`gross_absolute=1.1e-3`、`gross_relative_to_max_reference=2.2e-3`，复用原checker逻辑，不自行重解释为三个简单AND。候选自身direct/Graph必须逐bit，编码cache及输入字节不变。任何数值门失败即停，不调整容差。原threshold来源为[现有conformance](../output/ninfer-v4-post-w6-selection-20261024/source/tests/ops/test_gqa_attention.cpp)，数学定义见[公共合同](../output/ninfer-v4-post-w6-selection-20261024/source/include/ninfer/ops/gqa_attention.h)。

真实Target调用的是`ops::gqa_attention` append-and-attend，C1/W4带`valid_columns`和`table_rows`，使用`MultiBatch=false, Masked=true`。公共`gqa_attention_cached`没有这两个指针，不能冒充真实Target模板。首筛需要在bench编译作用域复用内部launcher并保持同样masked模板；它仍使用CPU预填cache、`writes_cache=false`，**只能证明共享计算候选，不能证明append集成或完整decode收益**。

复用`ninfer_causal_softmax_attention_bench`的计时/Graph框架和原FP64 oracle；当前bench零cache、bf16/int8默认扫描不能直接算本实验。只加有限rk4v4 profile，预先在CPU生成合法非零cache、Q及FP64结果并绑定SHA。不要默认跑A4 segmented benchmark，不引入第二套控制器。若内部入口维护合同要求独立编译target，只隔离target，仍复用现有owner/控制器/审计。

## 5. 最小预算、收益门槛与停止点

这是**拟议预算，尚未冻结、不可执行**。辅助传输、分配、memset、cold-flush上限待实际驱动枚举；不得继承已消耗的W6或其它实验额度。

| 项目 | 拟议首筛上限 |
|---|---:|
| 新数值场景 | 3长度×2份Q输入＝6 |
| direct Op | 原/候选各一遍，共12 |
| capture | 每长度原/候选各一个，共6；Graph使用该长度第一份Q |
| replay | 每图2次正确性＋6 warmup＋32计时，共240 |
| 算法kernel执行 | `(12+240)×2`＝504；capture内12个kernel节点另记 |
| native / model / HTTP / wire | 0 / 0 / 0 / 0 |
| GPU窗口 | 预估2–5分钟；硬限10分钟，第7分钟清理候选 |
| 辅助传输/分配/flush | 尚未冻结，完成枚举与审查前不运行 |

BO之前先核实模板可达、arena、资源上限、numerical checker和固定输入；可行性检查控制4–6工程小时。可构建补丁、最小驱动、CPU准备、BO和集成评审总计约6–10工程小时，含前述检查，不相加成10–16小时。若仅生成代码相同、资源明显超限或必须改公共API/默认/codec才能做，就停止，不扩成参数扫表。

拟议性能止损应同时看绝对值和相对值：128K整Op中位耗时至少下降15%且每层至少节省60μs，32个AB/BA配对至少24个改善；8K/32K中位退化不得超过2%。这些是**待冻结的投入门槛，不是实测预期或统计置信结论**。原/候选都使用同一冷flush策略，flush辅助成本独立计账，不偷偷让其中一条缓存更热。任一数值/Graph/预算失败都先保全，不靠选择性删除失败样本通过。

60μs×16个Target attention层约0.96ms/轮，只是每层省时都能传递时的算术尺度；不能据旧B29约29ms轮指标宣称当前H3一定提速3.3%。当前真实Attention占比、整轮收益、TTFT和质量影响均未知。若Op首筛胜出，下一阶段才准备实际append、valid-prefix、页表行/未写区域、KV字节和native整轮验证，届时另定最小预算；完整采样/质量与生产发布门禁继续独立。首筛无信号就关闭这一具名tile，不扫更多组合。

## 6. 当前交付与证据边界

29只读见证时间为`2026-10-24T13:38:50Z`，来源`/home/hhtele/ninfer-v4-h3-w6-resume-20261024/repair-r2/source`，分支`codex/h3-w6-resume-fixture-r2-20261024`，tree `a728df11f92360108a3f12bb619137dafe4eed3d`匹配原freeze。原服务为`STOPPED_IDENTITY_UNCHANGED`，GPU compute列表为空；这是该快照时刻状态。8个未跟踪AppleDouble元数据文件原样保留，不能称整个checkout clean。模型stat匹配冻结见证，本轮未重新hash大权重，也不以stat冒充新权重哈希。

已保存[远端readback](../output/ninfer-v4-post-w6-selection-20261024/remote-readback.json)、[15份源码SHA](../output/ninfer-v4-post-w6-selection-20261024/source-sha256.json)、[7份补充源码SHA](../output/ninfer-v4-post-w6-selection-20261024/additional-source-sha256.json)、2份GDN源码SHA、原候选清单与各独立审阅。已有本地Q4源码只在对应文件SHA相同或明确标为历史见证时复用；实际H3 runtime差异已分开处理。

本轮不改V4原入口或任务注册表，不把这份研究报告变成已启动的开发任务。拟议选择和资源机器记录见[selection](../output/ninfer-v4-post-w6-selection-20261024/selection.json)与[proposed-budget](../output/ninfer-v4-post-w6-selection-20261024/proposed-budget.json)。文档/证据校验见[validation](../output/ninfer-v4-post-w6-selection-20261024/validation.json)。没有新构建、CPU产品回归、GPU或模型验证，不能报候选PASS。

18处G1差异、C1附件缺口、Baseline原始失败/损坏raw、全部旧实验失败及证据缺口继续保留。`p95=null`、`optimization_qualification=false`。原服务保持停止；本轮未启动或清理任何远端进程。
