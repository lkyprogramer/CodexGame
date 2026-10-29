# 64项优化方向全景与实验卡

本文由`config/directions.json`生成；编号稳定，分数为工程优先级，不是速度或收益百分比。每项最终必须经过数值、场景、留出和组合门。源码符号以固定研究SHA为准，来源代码在`../sources/INDEX.md`，donor细节在`07_DONOR_RESEARCH.md`，当前实现审计在`08_KERNEL_AUDIT.md`。

## 六项先决工作（不算生产加速）

| ID | 交付 | 何时允许下一步 |
|---|---|---|
| F01 | 实机只读inventory、最新源码与历史生产分离 | 身份一致、资源足够、旧状态已对齐 |
| F02 | PR3871等实际CPU callsite微基准 | Q2_0/真实tensor路径对齐，不再测错分支 |
| F03 | perf/trace/nsys关键路径证据 | 计时闭合、overlap与wait语义明确 |
| F04 | 实验工具修复与fail-closed统计 | 本包无GPU自测通过，missing/timeout不被算赢 |
| F05 | tensor/内存/graph/KV账本 | 文件名与实际dtype分离、容量预算成立 |
| F06 | sampled/thinking/真实Pi留出与长ctx质量 | 验收语料冻结，不边调参边改题 |

## 总表

| ID | 方向 | 类别 | 轨道 | 状态 | 分数 |
|---|---|---|---|---|---:|
| [O01](#o01) | CPU pool按expert/行块自适应切分 | CPU | E/N | 优先 | 83 |
| [O02](#o02) | CPU GU→quant→down分阶段流水 | CPU | E/N | 条件 | 74 |
| [O03](#o03) | CPU工作量感知活跃worker与亲和性 | CPU | E | 条件 | 70 |
| [O04](#o04) | 4216专用无VBMI的VNNI内核 | CPU | N | 条件 | 68 |
| [O05](#o05) | 多token共享权重解包与ActQ复用 | CPU | E/N | 优先 | 77 |
| [O06](#o06) | CPU预打包布局与缓存行局部性 | CPU | E/N | 条件 | 60 |
| [O07](#o07) | 按节省关键路径时间/字节选GPU专家 | 驻留 | E/N | 优先 | 77 |
| [O08](#o08) | 逐expert三路成本调度 | 驻留 | N | 条件 | 74 |
| [O09](#o09) | adaptive tier与overlap/async成本治理 | 驻留 | E/N | 优先 | 75 |
| [O10](#o10) | PCIe已搬入专家直接晋升驻留 | 驻留 | E/N | 暂缓 | 50 |
| [O11](#o11) | 已有专家预取的预测与成本改进 | 驻留 | E/N | 研究 | 59 |
| [O12](#o12) | 同窗expert union与dispatch去重 | 驻留 | E/N | 条件 | 62 |
| [O13](#o13) | 统一DRAM/PCIe拷贝优先级与配额 | 传输 | E | 条件 | 68 |
| [O14](#o14) | 会话/任务感知expert热集 | 驻留 | E/N | 研究 | 58 |
| [O15](#o15) | prefill单group scratch与区域复用 | Prefill | E/N | 优先 | 77 |
| [O16](#o16) | prefill chunk/CPU-share/stream联合规划 | Prefill | E/N | 优先 | 76 |
| [O17](#o17) | prefill copied event稀疏化与wait去重 | Prefill | E | 条件 | 54 |
| [O18](#o18) | 跨subchunk专家复用与双staging | Prefill | E/N | 条件 | 63 |
| [O19](#o19) | 现有GDN_CHUNKED与sm89分块递推 | Prefill | N | 条件 | 78 |
| [O20](#o20) | QSA prefill tile/选择/online softmax | GPU | N | 条件 | 57 |
| [O21](#o21) | GPU专家GU/SwiGLU/down局部融合 | GPU | E/N | 条件 | 57 |
| [O22](#o22) | dense MMVQ形状路由及Ada表 | GPU | E/N | 已测搁置 | 63 |
| [O23](#o23) | draft-only head量化/紧凑候选词表 | Spec | N | 条件 | 60 |
| [O24](#o24) | 目标LM head与采样的精确路径优化 | GPU | E/N | 条件 | 60 |
| [O25](#o25) | Graph前移host工作与metadata复用 | Runtime | E | 条件 | 56 |
| [O26](#o26) | accept/commit/计数的设备端合并 | Runtime | E/N | 条件 | 54 |
| [O27](#o27) | 已有int8 KV融合路径的向量化与复用 | GPU | N | 增量条件 | 60 |
| [O28](#o28) | GDN decode状态搬运与融合 | GPU | E/N | 条件 | 57 |
| [O29](#o29) | 已有split-KV的tiny-query复用与自适应segment | GPU | N | 条件 | 69 |
| [O30](#o30) | mapped fetch与显式DMA的成本选择 | 传输 | E/N | 条件 | 62 |
| [O31](#o31) | 局部persistent任务区域与手递手同步 | Runtime | E/N | 研究 | 43 |
| [O32](#o32) | sm89编译与资源自动调参 | GPU | E/N | 条件 | 59 |
| [O33](#o33) | 已有成本spec策略的本机校准与细化 | Spec | N | 优先 | 75 |
| [O34](#o34) | lookup长窗与MTP深度分离 | Spec | N | 优先 | 75 |
| [O35](#o35) | prompt/history lookup索引与成本门控 | Spec | E/N | 条件 | 65 |
| [O36](#o36) | 兼容Flash-Next的DFlash/EAGLE类draft | Spec | N | 研究 | 55 |
| [O37](#o37) | 完整state checkpoint与ReplaySSM | 状态 | E/N | 条件 | 63 |
| [O38](#o38) | 多分支draft/tree验证 | Spec | N | 研究 | 44 |
| [O39](#o39) | RAM准入释放与无效逐出修复 | 会话 | E | 优先 | 86 |
| [O40](#o40) | slots/bytes价值与压力淘汰策略 | 会话 | E | 优先 | 71 |
| [O41](#o41) | 增量快照与dirty KV分段复用 | 会话 | E | 条件 | 63 |
| [O42](#o42) | 单GPU恢复缓冲复用与copy调度 | 会话 | E | 条件 | 62 |
| [O43](#o43) | SSD冷会话快照 | 会话 | E | 条件 | 58 |
| [O44](#o44) | KV/状态/graph/expert统一显存预算 | 内存 | E/N | 条件 | 60 |
| [O45](#o45) | 冷snapshot无损压缩与编码 | 会话 | E | 研究 | 47 |
| [O46](#o46) | 低比特KV格式及q4lm8v接入 | KV | N/Q | 质量实验 | 72 |
| [O47](#o47) | K/V非对称与旋转量化 | KV | N/Q | 质量实验 | 64 |
| [O48](#o48) | 近期精确KV窗口+压缩历史 | KV | N/Q | 质量实验 | 61 |
| [O49](#o49) | 活跃host-KV分块stage/双缓冲 | KV | E/N | 条件 | 63 |
| [O50](#o50) | 分页layout与prefix softmax状态合并 | KV | E/N | 研究 | 52 |
| [O51](#o51) | 前缀编辑的多级循环状态检查点 | 会话 | E | 条件 | 63 |
| [O52](#o52) | 替代权重格式/模型包 | 量化 | Q | 质量实验 | 64 |
| [O53](#o53) | 按层/专家敏感度的混合精度 | 量化 | Q | 研究 | 60 |
| [O54](#o54) | 专家裁剪/减少top-k/tail-skip | 模型 | Q | 质量实验 | 68 |
| [O55](#o55) | CPU专家延后跨层合并 | 模型 | Q | 质量实验 | 70 |
| [O56](#o56) | 激活稀疏/预测跳算 | 模型 | Q | 研究 | 42 |
| [O57](#o57) | 额外QSA/KV筛选或压缩attention预算 | 模型 | Q | 研究 | 53 |
| [O58](#o58) | Pi上下文组织/压缩与输出协议 | 应用 | Q | 独立层 | 64 |
| [O59](#o59) | 并发与prefill调度公平性 | 服务 | E/N | 条件 | 63 |
| [O60](#o60) | API/tokenize/SSE/工具链固定开销 | 服务 | E | 条件 | 66 |
| [O61](#o61) | 内存页/allocator/NUMA与有限pin预算 | 系统 | E | 条件 | 65 |
| [O62](#o62) | LTO/PGO与CPU调度代码布局 | 编译 | E/N | 研究 | 52 |
| [O63](#o63) | 功耗/频率/热稳态的性能效率 | 系统 | E/N | 条件 | 57 |
| [O64](#o64) | Ada Tensor issue-rate解锁 | 系统 | X | 研究 | 51 |

## 逐项可执行实验卡

<a id="o01"></a>
### O01 — CPU pool按expert/行块自适应切分

**范围：**CPU；E/N轨道；优先。评分(P/F/E/C/R)=5/5/4/3/2，总83。

**收益机理：**减少每层少量miss被16worker过度分发与全局汇合；保留大任务行并行。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**真实IQ2_XS/IQ4_NL与IQ2_XXS/Q2_0；miss0/1/2/多，nt1..8；测dispatch/barrier/compute及window。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；只改worker数或micro快而window不快；POOL8旧败不得重标成功。

**证据与任务：**UP_POOL;DONOR_D01；[对应实施计划](../plans/P01_CPU_POOL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o02"></a>
### O02 — CPU GU→quant→down分阶段流水

**范围：**CPU；E/N轨道；条件。评分(P/F/E/C/R)=5/5/3/4/3，总74。

**收益机理：**在每expert可用结果上启动下一阶段，减少全局GU完成后主线程串行量化的停顿。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**保持每token quantizer和combine顺序；构造慢expert、0row、取消、抢占和epoch复用测试。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；数据依赖无法并行，或nt权重复用损失抵消barrier收益。

**证据与任务：**UP_POOL;DONOR_D03；[对应实施计划](../plans/P01_CPU_POOL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o03"></a>
### O03 — CPU工作量感知活跃worker与亲和性

**范围：**CPU；E轨道；条件。评分(P/F/E/C/R)=3/5/3/2/2，总70。

**收益机理：**保持持久池，只给实际有工作的worker发任务；给host调度留核，不重复静态POOL8。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**固定拓扑比较expert/task粒度、SMT/物理核；测C-state已固定时的wake与tail。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；仅低线程synthetic快；已有POOL8负例在真实形状重现。

**证据与任务：**UP_POOL;DONOR_D01；[对应实施计划](../plans/P01_CPU_POOL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o04"></a>
### O04 — 4216专用无VBMI的VNNI内核

**范围：**CPU；N轨道；条件。评分(P/F/E/C/R)=4/5/3/4/3，总68。

**收益机理：**隔离TU，用实际支持的AVX512F/BW/DQ/VL/VNNI做目标dtype解包和dot；禁止放宽旧门控。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先修真实Q2_0 bench；CPU反汇编（objdump/llvm-objdump）检查VBMI/VPOPCNTDQ不存在；4216真机测试与频率记录。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；真实nt1已到DDR上限、AVX512降频抵消、只改旧错误bench。

**证据与任务：**UP_ISA;DONOR_D02;PR3871；[对应实施计划](../plans/P06_CPU_ISA.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o05"></a>
### O05 — 多token共享权重解包与ActQ复用

**范围：**CPU；E/N轨道；优先。评分(P/F/E/C/R)=4/5/4/3/2，总77。

**收益机理：**在同layer/expert合法columns内复用解包与激活量化；补现有multi-token未覆盖处。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**使用实测每expert nt分布，统计重复字节、grouping开销和accepted/window。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；大部分nt=1且分组开销更大；现有路径已覆盖。

**证据与任务：**UP_POOL;DONOR_D03；[对应实施计划](../plans/P01_CPU_POOL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o06"></a>
### O06 — CPU预打包布局与缓存行局部性

**范围：**CPU；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/3/3，总60。

**收益机理：**按真实row/block调整静态pack，减少跨页读取/重复scale解码；不改变权重值。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**同时计算预打包RAM峰值、冷/暖cache、启动成本和长运行总wall。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；展开权重挤出RAM热集或只改善LLC热micro。

**证据与任务：**UP_NATIVE;DONOR_D03；[对应实施计划](../plans/P06_CPU_ISA.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o07"></a>
### O07 — 按节省关键路径时间/字节选GPU专家

**范围：**驻留；E/N轨道；优先。评分(P/F/E/C/R)=5/5/3/3/3，总77。

**收益机理：**以避开的CPU/PCIe时间、大小、复用、迁移成本评分，而非仅hit count；沿用真实router。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**同路由trace离线模拟再A/B，报告CPUstall/bytes moved/hit和每层分配。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；命中率增而wall退化；热集抖动或挤占KV/graph。

**证据与任务：**UP_EXPERT;DONOR_D04;DALI；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o08"></a>
### O08 — 逐expert三路成本调度

**范围：**驻留；N轨道；条件。评分(P/F/E/C/R)=5/5/3/4/3，总74。

**收益机理：**resident GPU、CPU原位算、搬运后GPU计算三路，按当前队列完工时间贪心分配。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**真实dtype/nt成本表，decode/prefill分开；测决策开销和预测误差。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；调度开销超过省时；复制Mixtral指数枚举；DDR/PCIe争用未建模。

**证据与任务：**DONOR_D05;DALI;SCHE；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o09"></a>
### O09 — adaptive tier与overlap/async成本治理

**范围：**驻留；E/N轨道；优先。评分(P/F/E/C/R)=4/5/4/3/3，总75。

**收益机理：**显式治理已有策略，不重复发明；按CPU/DDR竞争与phase稳定性选择。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**保持当前overlap基线；分离blocking/async/overlap单因素，记录effective资格与64窗状态。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；为新模式关闭既有overlap才显快但总代价更高；自然负载阶段偏差。

**证据与任务：**UP_ASYNC;UP_GENERATE；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o10"></a>
### O10 — PCIe已搬入专家直接晋升驻留

**范围：**驻留；E/N轨道；暂缓。评分(P/F/E/C/R)=3/2/3/3/3，总50。

**收益机理：**复用已经支付的搬运，把高价值专家保留在VRAM；需解决与overlap的epoch冲突。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先证明当前低PCIe share仍有候选数；适配slot所有权与inflight读者。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；现配置不适用、必须牺牲overlap或流量太小。

**证据与任务：**PR2964;UP_EXPERT；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o11"></a>
### O11 — 已有专家预取的预测与成本改进

**范围：**驻留；E/N轨道；研究。评分(P/F/E/C/R)=4/4/2/4/3，总59。

**收益机理：**主线已有RouterLookahead/ForesightSwap和FileExpertSource预取；改进预测/资格/配额，预测只影响提前搬运，不漏算真实路由。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**precision/useful bytes、被挤出专家、copy排队、longctx争用；错预测回退。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；预取污染热集；需要改变router或少算专家才有收益。

**证据与任务：**DALI;HYBRIMOE;DONOR_D06；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o12"></a>
### O12 — 同窗expert union与dispatch去重

**范围：**驻留；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/3/2，总62。

**收益机理：**同一合法verify窗口去除重复metadata和重复读取，保留各token权重。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**trace确认重复比例，测nt分组与ordering；不跨因果依赖token乱合并。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；现有resident plan已实现；grouping成本大于重复开销。

**证据与任务：**UP_VERIFY;DONOR_D03；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o13"></a>
### O13 — 统一DRAM/PCIe拷贝优先级与配额

**范围：**传输；E轨道；条件。评分(P/F/E/C/R)=4/4/3/3/2，总68。

**收益机理：**active KV/必要expert优先，prefetch/checkpoint限速，控制同一DDR上的竞争。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**128K同时restore与decode；记录bytes、queue、RSS和关键请求延迟。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；没有后台copy竞争；限速只拖慢恢复。

**证据与任务：**DONOR_D09;UP_EXPERT；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o14"></a>
### O14 — 会话/任务感知expert热集

**范围：**驻留；E/N轨道；研究。评分(P/F/E/C/R)=3/4/2/3/2，总58。

**收益机理：**在全局热度中保留任务/会话分布信息，减少Java任务切换时污染；有容量与滞回界。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**A/B任务交替、冷启动与warm分开，留出新任务避免profile过拟合。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；稳态profile已无收益；会话切换频率不足或缓存分割浪费。

**证据与任务：**UP_EXPERT;HYBRIMOE；[对应实施计划](../plans/P03_RESIDENCY_AND_SCHEDULING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o15"></a>
### O15 — prefill单group scratch与区域复用

**范围：**Prefill；E/N轨道；优先。评分(P/F/E/C/R)=4/5/4/3/2，总77。

**收益机理：**缩小GU/H/Hq及hyper-connection临时区，允许更大合法chunk，降低权重重传。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**极端路由偏斜、尾组、FP16fallback拒绝、最大ctx；记录恢复decode热集成本。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；4090当前auto chunk不受scratch约束，或更大chunk抬高TTFT/驱逐成本。

**证据与任务：**PR4039;UP_PREFILL；[对应实施计划](../plans/P05_CUDA_PREFILL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o16"></a>
### O16 — prefill chunk/CPU-share/stream联合规划

**范围：**Prefill；E/N轨道；优先。评分(P/F/E/C/R)=4/5/3/2/2，总76。

**收益机理：**根据当前RAM/VRAM/专家负载选择chunk；从已有MAX3072和auto出发。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**短agent新增token与冷8/32/64/122K分组；测完整轮而非只prefill。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；只是把较大prompt变更小或改变输出；已有auto足够。

**证据与任务：**UP_PREFILL;DONOR_D07；[对应实施计划](../plans/P05_CUDA_PREFILL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o17"></a>
### O17 — prefill copied event稀疏化与wait去重

**范围：**Prefill；E轨道；条件。评分(P/F/E/C/R)=2/3/3/2/2，总54。

**收益机理：**以实际消费组为单位发event，删除无人等待的标记与重复slot等待。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**CUDA/Linux事件成本先测；slot环回、慢copy、最后部分组、错误路径。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；Windows/HIP大收益在Linux不出现；测量份额过低。

**证据与任务：**PR4005;UP_PREFILL；[对应实施计划](../plans/P05_CUDA_PREFILL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o18"></a>
### O18 — 跨subchunk专家复用与双staging

**范围：**Prefill；E/N轨道；条件。评分(P/F/E/C/R)=4/4/3/4/3，总63。

**收益机理：**保留有效layer-major/grouping，减少同expert在相邻subchunk重复过PCIe。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**分析完整prompt专家字节和激活峰值；预热/释放/重建cache全计时。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；激活/scratch装不下，回收成本超过收益。

**证据与任务：**DONOR_D07;UP_PREFILL；[对应实施计划](../plans/P05_CUDA_PREFILL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o19"></a>
### O19 — 现有GDN_CHUNKED与sm89分块递推

**范围：**Prefill；N轨道；条件。评分(P/F/E/C/R)=4/5/4/2/3，总78。

**收益机理：**测试已有STRATA_GDN_CHUNKED=1的32-token FP32 chunk recurrence；与GDN_CHUNK区分。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**T阈值和chunk边界、128SM资格、长state/logits误差、真prefill比例。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；舍入漂移不达门；分块和occupancy开销大于递推收益。

**证据与任务：**UP_GDN;KERNEL_K18；[对应实施计划](../plans/P05_CUDA_PREFILL.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o20"></a>
### O20 — QSA prefill tile/选择/online softmax

**范围：**GPU；N轨道；条件。评分(P/F/E/C/R)=3/4/3/4/3，总57。

**收益机理：**移植FA2/Ada适用分块，保留原QSA selected cell、mask与位置语义。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**冷长prompt、all-mask/空段/极值、实际KV格式；检测额外scratch。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；需要把稀疏QSA换成dense attention；copy/CPU才是主瓶颈。

**证据与任务：**UP_QSA;DONOR_D14；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o21"></a>
### O21 — GPU专家GU/SwiGLU/down局部融合

**范围：**GPU；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/4/3，总57。

**收益机理：**按真实IQ矩阵融合可复用读/写，保留中间量化语义；不跨CPU依赖。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**micro + 实际nt1/2/4分布；寄存器、spill、SMEM与window。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；occupancy下降、nt小且原核已融合、只减少launch却不改善关键路径。

**证据与任务：**UP_CUDA;UP_NATIVE；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o22"></a>
### O22 — dense MMVQ形状路由及Ada表

**范围：**GPU；E/N轨道；已测搁置。评分(P/F/E/C/R)=2/4/4/2/2，总63。

**收益机理：**仅在最新trace出现新热点形状时再修表；已测IL0/IL89无收益保留。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**比较实际调用比例与旧profile，先算Amdahl最大收益。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；分布未变或差异仍落A/A噪声，不重新跑全套。

**证据与任务：**H_DIAG;H_CFG;UP_CUDA；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o23"></a>
### O23 — draft-only head量化/紧凑候选词表

**范围：**Spec；N轨道；条件。评分(P/F/E/C/R)=3/4/3/3/3，总60。

**收益机理：**只减少drafter成本，target最终验证和sampler语义保留；当前MTPQ4收益边缘。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**真实greedy/采样分别测accept与总wall；若采样要求q分布则保持完整校正。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；减少draft耗时却降低接受率；假设greedy正确性可自动推广随机采样。

**证据与任务：**DONOR_D17;DONOR_D22;H_CFG；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o24"></a>
### O24 — 目标LM head与采样的精确路径优化

**范围：**GPU；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/3/3，总60。

**收益机理：**tile/vocab reduction/GPU采样融合，保留目标完整概率或有证明的受限采样合同。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**大词表、ties、top-k/top-p/min-p/penalty、tools/thinking；测head份额。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；裁词表改变target分布；head份额低或CPU专家更贵。

**证据与任务：**UP_SAMPLER;UP_CUDA；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o25"></a>
### O25 — Graph前移host工作与metadata复用

**范围：**Runtime；E轨道；条件。评分(P/F/E/C/R)=2/4/3/3/2，总56。

**收益机理：**在已排队图执行时准备下一轮可提前的信息，复用稳定plan，不改接受依赖。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**host trace与window gap；graph key变化、指针寿命、cancel和epoch。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；旧窗口空隙约1.2%且新测仍小；只是换语言/runtime。

**证据与任务：**DONOR_D15;DONOR_D25;UP_VERIFY；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o26"></a>
### O26 — accept/commit/计数的设备端合并

**范围：**Runtime；E/N轨道；条件。评分(P/F/E/C/R)=2/4/3/3/3，总54。

**收益机理：**合并真正多余的D2H/小kernel bookkeeping，保持accepted state与输出同步。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**accept0/1/all、EOS/tool stop、拒绝后GDN/KV/MTP一致。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；相关时间份额过低，或失去取消响应。

**证据与任务：**DONOR_D21;UP_VERIFY；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o27"></a>
### O27 — 已有int8 KV融合路径的向量化与复用

**范围：**GPU；N轨道；增量条件。评分(P/F/E/C/R)=2/5/4/4/3，总60。

**收益机理：**主线load8_q8已就地读取int8+scale；只研究向量load、访存合并、跨query复用等增量，保持现有字节合同。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**固定KV字节检查QK/PV和logits；测临时内存、读流量、长窗口。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；重复发明已有load8_q8，或新核spill/重复读抵消收益。

**证据与任务：**DONOR_D11;UP_QSA；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o28"></a>
### O28 — GDN decode状态搬运与融合

**范围：**GPU；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/4/3，总57。

**收益机理：**借鉴状态tile、双缓冲、sm89 cp.async；保持FP32主状态、实际投影/量化舍入与递推次序。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**长teacher-forced与spec rollback；共享内存≤本机上限，occupancy实测。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；直接搬sm90 bulk/TMA/PDL路径；state流量/时间份额不足。

**证据与任务：**DONOR_D18;KERN_GDN；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o29"></a>
### O29 — 已有split-KV的tiny-query复用与自适应segment

**范围：**GPU；N轨道；条件。评分(P/F/E/C/R)=3/5/4/3/3，总69。

**收益机理：**主线已有CHUNK=64分块/merge及STRATA_QSA_SPLIT_ATTN int8 TensorCore路径；先核实际命中与数值，再研究交集复用/segment/merge增量。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**q1..8、32/64/96/122K、选中blocks不规则、max scratch与merge成本。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；不适用于模型选中KV语义；重复读/merge让长窗更慢。

**证据与任务：**DONOR_D10;UP_QSA；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o30"></a>
### O30 — mapped fetch与显式DMA的成本选择

**范围：**传输；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/3/2，总62。

**收益机理：**按blob大小/contiguity/竞争选择mapped kernel或固定pinned staging显式copy。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**真实PCIe3链路、DDR竞争、coldpage、多个expert；纳入CPU唤醒与cache污染。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；当前选择已在甜点区；新增pin/memcpy开销超省时。

**证据与任务：**UP_EXPERT;DONOR_D08；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o31"></a>
### O31 — 局部persistent任务区域与手递手同步

**范围：**Runtime；E/N轨道；研究。评分(P/F/E/C/R)=3/3/2/5/4，总43。

**收益机理：**只选择无CPU依赖的局部GPU区域尝试persistent/合并，避免整引擎重写。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**SM驻留/饥饿、threadblock资源、不同T、错误恢复；host关键路径不变时观察净收益。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；GPU wait来自真实CPU算力；常驻kernel占SM妨碍expert/attention。

**证据与任务：**DONOR_D27;MPK；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o32"></a>
### O32 — sm89编译与资源自动调参

**范围：**GPU；E/N轨道；条件。评分(P/F/E/C/R)=2/4/3/2/2，总59。

**收益机理：**按实际kernel测block/warps/register/SMEM/L2访问策略，保留shape白名单。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**检查SASS和spill，固定compiler；micro和真实混合shape留出。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；重复旧Ada表无益；更激进fast-math改变数值而未重分类。

**证据与任务：**NVIDIA_ADA;UP_CMAKE；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o33"></a>
### O33 — 已有成本spec策略的本机校准与细化

**范围：**Spec；N轨道；优先。评分(P/F/E/C/R)=4/5/4/3/3，总75。

**收益机理：**DraftPolicy已有context分桶/EMA/概率校准/stale探测；先验证现STRATA_SPEC_COST，再增量加入CPU miss、tier与graph内存成本。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**真实Pi sampled/thinking、长context；决策开销、振荡、T切换state与graph。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；只针对复制题更快；通用Java/长窗退化或控制器过拟合。

**证据与任务：**DONOR_D16;UP_DRAFT；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o34"></a>
### O34 — lookup长窗与MTP深度分离

**范围：**Spec；N轨道；优先。评分(P/F/E/C/R)=4/5/4/3/3，总75。

**收益机理：**copy/edit可用lookup8/16，MTP仍spec4；按内存限制只捕获少量额外图。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**PR相同GSQ-RCO IQ3_XXS但2060Super数据仅参考；在4090测extra graph挤出专家和longctx。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；LOOKUP2已在生成题无益；copy/edit占比低或CPU nt成本抵消接受数。

**证据与任务：**PR4040;DONOR_D20；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o35"></a>
### O35 — prompt/history lookup索引与成本门控

**范围：**Spec；E/N轨道；条件。评分(P/F/E/C/R)=3/4/3/2/2，总65。

**收益机理：**减少候选检索成本并按实际成功率选择lookup/MTP；真实文本只用合法prefix。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**复制、局部修改、重复但后缀不同、没有重复的任务；记录lookup费用。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；仅训练/自复述数据有益，真实任务不复制。

**证据与任务：**DONOR_D20;UP_DRAFT；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o36"></a>
### O36 — 兼容Flash-Next的DFlash/EAGLE类draft

**范围：**Spec；N轨道；研究。评分(P/F/E/C/R)=5/3/2/5/4，总55。

**收益机理：**独立研究更强draft/低秩head；需匹配target hidden/tokenizer/训练，不能用27B权重替代。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先证明可用训练/权重和许可；small-context协议再128K；包含draft显存。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；无匹配draft，训练预算超范围或草稿成本抵消；source-available代码不能无条件copy。

**证据与任务：**EAGLE4;DONOR_D19；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o37"></a>
### O37 — 完整state checkpoint与ReplaySSM

**范围：**状态；E/N轨道；条件。评分(P/F/E/C/R)=4/4/3/4/3，总63。

**收益机理：**先量化实际rollback/copy成本，再用精确checkpoint+raw transition重放减少历史状态保存。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**GDN+conv+KV+hidden+MTP成事务；accept0/all、回滚、cancel、跨block。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；原成本很小、replay计算更贵，或近似逆更新被冒充exact。

**证据与任务：**DONOR_D18;DONOR_D23;UP_SNAPSHOT；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o38"></a>
### O38 — 多分支draft/tree验证

**范围：**Spec；N轨道；研究。评分(P/F/E/C/R)=4/2/2/5/4，总44。

**收益机理：**树父状态显式化，提高候选覆盖；不同分支GDN不能共用线性更新状态。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先小树oracle，parent/permutation/mask/rollback，计算与KV内存全计。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；4090资源不足、CPU专家分支膨胀或缺匹配draft。

**证据与任务：**DONOR_D19;EAGLE4；[对应实施计划](../plans/P04_SPEC_AND_LOOKUP.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o39"></a>
### O39 — RAM准入释放与无效逐出修复

**范围：**会话；E轨道；优先。评分(P/F/E/C/R)=5/5/4/2/2，总86。

**收益机理：**必要时trim freed heap；先判断可回收容量能否满足，避免清空缓存仍拒绝。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**复现实际park/refuse；latest guarded donor/pinned保护；post-capture floor；trim延迟。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；本机无拒绝/重prefill事件；trim/pagefault让净收益为负。

**证据与任务：**PR2253;UP_CACHE;H_DEPLOY；[对应实施计划](../plans/P02_CACHE_ADMISSION.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o40"></a>
### O40 — slots/bytes价值与压力淘汰策略

**范围：**会话；E轨道；优先。评分(P/F/E/C/R)=4/5/3/3/3，总71。

**收益机理：**保护昂贵长前缀，区分slot与bytes压力；不直接照搬永久缩容默认。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**长主会话+短子任务burst、等长冲突、guarded/pinned、RAM恢复；策略2x2消融。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；提高hit却妨碍活跃任务；永久缩容掩盖临时压力或telemetry失效。

**证据与任务：**PR4031;UP_CACHE；[对应实施计划](../plans/P02_CACHE_ADMISSION.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o41"></a>
### O41 — 增量快照与dirty KV分段复用

**范围：**会话；E轨道；条件。评分(P/F/E/C/R)=4/4/3/4/3，总63。

**收益机理：**保留已存在16MiB段与unchanged-prefix复用，只补真实dirty范围及完整状态原子性。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**相同tokens但不同KV/state不得复用；编辑前缀、spec拒绝、snapshot竞争。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；主线已有同等机制；metadata/引用计数复杂度超过copy收益。

**证据与任务：**UP_SNAPSHOT;DONOR_D24；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o42"></a>
### O42 — 单GPU恢复缓冲复用与copy调度

**范围：**会话；E轨道；条件。评分(P/F/E/C/R)=3/4/3/3/2，总62。

**收益机理：**只抽取可用于单卡的host shuttle复用/分段copy；多stage线程本机不直接适用。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**capture/restore/slot-copy完整字节与异常传播；measure峰值RSS/TTFT。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；直接照搬4x4090收益；临时区已复用或RAM更紧。

**证据与任务：**PR4002;UP_SNAPSHOT；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o43"></a>
### O43 — SSD冷会话快照

**范围：**会话；E轨道；条件。评分(P/F/E/C/R)=4/3/3/4/3，总58。

**收益机理：**RAM容不下但prefill昂贵时，将完整冷snapshot存盘；版本/校验和原子写。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**实际SSD延迟、read/write bytes、热冷分开；断电式不完整文件/模型变更拒绝。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；恢复不比重prefill快、SSD空间/写放大过高；热会话被频繁写盘。

**证据与任务：**PR3341;UP_CONVFILE；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o44"></a>
### O44 — KV/状态/graph/expert统一显存预算

**范围：**内存；E/N轨道；条件。评分(P/F/E/C/R)=4/4/3/5/3，总60。

**收益机理：**ExpertCache已有open_segmented/shrink/grow/set_vmm；增量是跨KV/GDN/draft/graph统一lease和预算，先证明静态分区浪费。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**最坏128K+spec+restore+prefill scratch，all-or-none lease、graph地址不悬空。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；虚拟内存操作/碎片管理成本高、当前无浪费；不能回收live映射。

**证据与任务：**KERN_POOL;DONOR_D09;UP_EXPERT；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o45"></a>
### O45 — 冷snapshot无损压缩与编码

**范围：**会话；E轨道；研究。评分(P/F/E/C/R)=2/3/2/3/2，总47。

**收益机理：**压缩只用于冷RAM/SSD快照，恢复字节完全一致；不是活跃KV新精度。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**真实int8/FP32状态压缩比与CPU解码耗时、peak双份内存。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；低比特数据难压缩，CPU增加成本超过IO节省。

**证据与任务：**UP_CONVFILE;DONOR_D24；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o46"></a>
### O46 — 低比特KV格式及q4lm8v接入

**范围：**KV；N/Q轨道；质量实验。评分(P/F/E/C/R)=5/5/3/4/4，总72。

**收益机理：**主线已有rotatedQ4_0与k8v4，先资格验证；PR4068 exact-cell扩展另审CUDA，单独衡量codec/精度及驻留收益。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先当前int8身份不变；4bit长轨迹/工具/Java与q4lm8v边界；CUDA实测。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；只在HIP验证；128K质量失败或新格式慢；不能直接替换int8基线。

**证据与任务：**PR4068;DONOR_Q02；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o47"></a>
### O47 — K/V非对称与旋转量化

**范围：**KV；N/Q轨道；质量实验。评分(P/F/E/C/R)=5/4/3/5/4，总64。

**收益机理：**主线已有旋转q4/hybrid；仅研究KIVI式分组轴、K4V2等未覆盖布局，拟合真实QSA统计，不套dense27B表。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**旋转/scale/残差的全链路验证，长工具任务非劣，实际字节和kernel吞吐。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；旋转开销/误差放大、缺对应sm89kernel、量化校准污染留出。

**证据与任务：**DONOR_Q03;TQLLM;HYPERQWEN；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o48"></a>
### O48 — 近期精确KV窗口+压缩历史

**范围：**KV；N/Q轨道；质量实验。评分(P/F/E/C/R)=4/4/3/4/4，总61。

**收益机理：**保留近期/异常cell高精度，历史更低精度；额外tier必须纳入原子snapshot。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**窗口跨界、环回、spec拒绝、长检索首中尾、exact-window不是整模型exact。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；额外meta/copy抵消节省；历史信息任务明显下降。

**证据与任务：**PR4068;DONOR_Q02；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o49"></a>
### O49 — 活跃host-KV分块stage/双缓冲

**范围：**KV；E/N轨道；条件。评分(P/F/E/C/R)=4/4/3/4/3，总63。

**收益机理：**只搬实际访问的KV块，固定pinned/staging并与计算重叠，和专家搬运共享配额。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先确认当前KV驻留；128K有效bytes、PCIe与DDR争用、OOM和pagefault。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；当前KV全GPU驻留；真正PCIe字节下界已到；多搬无用block。

**证据与任务：**DONOR_D12;UP_QSA；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o50"></a>
### O50 — 分页layout与prefix softmax状态合并

**范围：**KV；E/N轨道；研究。评分(P/F/E/C/R)=3/3/3/4/3，总52。

**收益机理：**共享prefix多query可复用读/plan；分段attention用LSE正确合并，不能直接相加输出。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**不同query、空段/allmask、稀疏索引、page边界与多会话。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；单请求并无重复读机会，或现有tile已共享。

**证据与任务：**DONOR_D13;DONOR_D15；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o51"></a>
### O51 — 前缀编辑的多级循环状态检查点

**范围：**会话；E轨道；条件。评分(P/F/E/C/R)=4/4/3/4/3，总63。

**收益机理：**为长上下文中间编辑保留少量明确位置的GDN/conv/MTP快照，减少从零重算。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**编辑发生在检查点前后，精确匹配token/template/model；记录存储与减少prefill。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；edit位置分布无复用价值，snapshot开销吃掉收益。

**证据与任务：**KERN_POOL;DONOR_D23;UP_CACHE；[对应实施计划](../plans/P11_COPY_AND_STATE.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o52"></a>
### O52 — 替代权重格式/模型包

**范围：**量化；Q轨道；质量实验。评分(P/F/E/C/R)=5/4/3/5/4，总64。

**收益机理：**用更合适的实际bpw/格式换取驻留或更高效CPU/GPU解码；每个包独立baseline。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**总模型任务质量、tensor inventory、实际peak、CPU量化路径与conversion版本。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；仅文件更小但内核更慢；拿dense27B格式强套FlashNext；改模型不披露。

**证据与任务：**DONOR_Q01;TQLLM;EXLLAMA；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o53"></a>
### O53 — 按层/专家敏感度的混合精度

**范围：**量化；Q轨道；研究。评分(P/F/E/C/R)=5/4/2/5/4，总60。

**收益机理：**对高敏感/高频层保精度，低敏感层减位宽；同时优化驻留价值。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**校准集与留出严格分离、每tensordtype/scale冻结，任务非劣。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；小校准集过拟合；新增格式爆炸或无法维护实际kernel。

**证据与任务：**DONOR_Q01;UP_NATIVE；[对应实施计划](../plans/P08_KV_AND_MEMORY.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o54"></a>
### O54 — 专家裁剪/减少top-k/tail-skip

**范围：**模型；Q轨道；质量实验。评分(P/F/E/C/R)=5/4/3/3/5，总68。

**收益机理：**减少实际专家工作可大幅减计算/流量，但改变模型；现有近似也要显式记录。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**每层路由质量、代码/工具/长上下文与原模型对照；报告速度-质量曲线。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；包装成无损；只用perplexity或短问答证明Java能力。

**证据与任务：**PR2690;DONOR_Q07；[对应实施计划](../plans/P10_RESEARCH_BRANCHES.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o55"></a>
### O55 — CPU专家延后跨层合并

**范围：**模型；Q轨道；质量实验。评分(P/F/E/C/R)=5/5/3/4/5，总70。

**收益机理：**轻权重CPU结果下一层再加可隐藏等待，但改变网络依赖与输出。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**teacher-forced完整trajectory、自由生成、长期工具任务；与减少专家分离。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；质量门失败；将它混入E轨道或默认打开。

**证据与任务：**PR2690;DONOR_Q07；[对应实施计划](../plans/P10_RESEARCH_BRANCHES.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o56"></a>
### O56 — 激活稀疏/预测跳算

**范围：**模型；Q轨道；研究。评分(P/F/E/C/R)=4/2/2/5/5，总42。

**收益机理：**研究可证明零值跳过或可容忍近似；MoE路由稀疏不等于ReLU神经元稀疏。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先测真实activation分布与可省work；误预测召回/质量和predictor成本。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；模型没有适用稀疏性、需改训超范围或预测成本过大。

**证据与任务：**POWERINFER;DONOR_Q07；[对应实施计划](../plans/P10_RESEARCH_BRANCHES.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o57"></a>
### O57 — 额外QSA/KV筛选或压缩attention预算

**范围：**模型；Q轨道；研究。评分(P/F/E/C/R)=5/3/2/5/5，总53。

**收益机理：**在已有QSA之上进一步减少访问块，只作为显式质量交换。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**全长任务首中尾、跨文件、periodic弱点、selector召回与端到端。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；假设训练好的稀疏结构还能无代价二次裁剪。

**证据与任务：**DONOR_Q06;UP_QSA；[对应实施计划](../plans/P10_RESEARCH_BRANCHES.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o58"></a>
### O58 — Pi上下文组织/压缩与输出协议

**范围：**应用；Q轨道；独立层。评分(P/F/E/C/R)=4/4/3/3/4，总64。

**收益机理：**减少重复模板/工具噪声或压缩历史可缩任务wall，但改变请求语义；与引擎优化分开。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**工具结果可恢复、Java任务非劣、总token与召回成本；冻结compaction策略。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；靠更短上下文获得速度却声称131072同输入引擎提速。

**证据与任务：**H_PI;UP_SERVE；[对应实施计划](../plans/P09_SERVING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o59"></a>
### O59 — 并发与prefill调度公平性

**范围：**服务；E/N轨道；条件。评分(P/F/E/C/R)=4/4/3/4/3，总63。

**收益机理：**独立测试1/2/4真实并发，避免长prefill阻塞短请求；吞吐与单用户延迟分开。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**固定总上下文/显存，取消/队首阻塞/p99/任务完成量；状态隔离。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；多卡batch-group PR直接套单卡；吞吐增但用户延迟不可接受。

**证据与任务：**UP_SERVE;UP_GENERATE；[对应实施计划](../plans/P09_SERVING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o60"></a>
### O60 — API/tokenize/SSE/工具链固定开销

**范围：**服务；E轨道；条件。评分(P/F/E/C/R)=2/5/3/2/1，总66。

**收益机理：**测真实NGINX缓冲、flush、token计数和Python处理，消除已证实重复工作。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**direct与代理路径成对；首reasoning/visible/tool分开；不修改生成语义。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；服务开销很小；把thinking隐藏时间误当kernel慢。

**证据与任务：**UP_SERVE;H_PI；[对应实施计划](../plans/P09_SERVING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o61"></a>
### O61 — 内存页/allocator/NUMA与有限pin预算

**范围：**系统；E轨道；条件。评分(P/F/E/C/R)=3/4/3/2/2，总65。

**收益机理：**在已有85%THP基础查剩余fault/碎片，按拓扑first-touch；allocator实验与trim分开。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**实际NUMA拓扑、minor/major fault、RSS、memlock、cgroup和内存压力。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；重复开THP/性能调频已做项；mlock占满64GB或侵占缓存。

**证据与任务：**H_NP0;UP_MEMORY；[对应实施计划](../plans/P09_SERVING.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o62"></a>
### O62 — LTO/PGO与CPU调度代码布局

**范围：**编译；E/N轨道；研究。评分(P/F/E/C/R)=2/4/2/3/2，总52。

**收益机理：**只在profile显示host指令/分支/dispatch占比时做版本固定PGO；保留数值flags。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**训练profile和留出分开、构建可重现、冷/热路径和binary identity。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；收益落噪声；-ffast-math被混入编译优化。

**证据与任务：**UP_CMAKE;UP_POOL；[对应实施计划](../plans/P07_GPU_KERNELS.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o63"></a>
### O63 — 功耗/频率/热稳态的性能效率

**范围：**系统；E/N轨道；条件。评分(P/F/E/C/R)=2/4/3/2/3，总57。

**收益机理：**基线记录stock功率/频率/温度；只在授权维护试验比较稳定功率上限与散热状态。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**同任务正确性、持续30分钟频率/能耗/吞吐，所有arm同host配置。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；仅短boost赢；热降频/不稳定；把CSTATE旧收益重复计入。

**证据与任务：**NVIDIA_ADA;H_DEPLOY；[对应实施计划](../plans/P10_RESEARCH_BRANCHES.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。

<a id="o64"></a>
### O64 — Ada Tensor issue-rate解锁

**范围：**系统；X轨道；研究。评分(P/F/E/C/R)=4/3/3/5/5，总51。

**收益机理：**公开4090证据针对FP16/BF16→FP32 Tensor发射；INT8/dp4a不随之提升。

**前置：**F01–F06与该实施计划的依赖已满足；先证明当前基线尚未覆盖该机制。历史无收益项只有热点或条件改变才重新晋级。

**最小先导实验：**先统计目标FP16/BF16 Tensor关键路径份额与本机驱动兼容；独立维护环境匹配功率A/B。

**实施顺序：**读取源码与donor合同→增加能击穿错误实现的测试→实现默认关闭的局部候选→micro+数值→同输入场景A/B→独立留出。研究项先实现可否证的spike，不一次重写整引擎。

**验收与退出：**沿用质量/统计门；主要decode是CPU/IQ/dp4a；没有安全恢复路径/匹配驱动验证；绝不承诺2倍推理。

**证据与任务：**GPU_UNLOCK；[对应实施计划](../plans/P10_RESEARCH_BRANCHES.md)。提交`templates/EXPERIMENT_REPORT.md`，包含原始失败、成本和未运行项。
