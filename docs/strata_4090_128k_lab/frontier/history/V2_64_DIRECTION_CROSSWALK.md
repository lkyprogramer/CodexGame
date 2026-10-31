# v2 的64方向逐项处置

本表是旧目录的处置映射，不是64次新实验的成绩单。`已测`、`有限筛查`、`已有覆盖`、`分析未执行`、`数值/资产前置`必须分开。用户说明这些方向已验证或因潜力不足放弃；本轮不会因为仍有源码可读就默认重开。条件卡只是定义什么新证据才足以提出独立窄差量。

旧编号与原题名取自[固定atlas](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_flashnext_4090_extreme_lab_v2/docs/05_DIRECTIONS_ATLAS.md)。每条历史测量的原报告见[证据索引](../sources/EVIDENCE_INDEX.md)及[关闭台账](../docs/01_EVIDENCE_AND_CLOSURES.md)；Fxx见[候选索引](../candidates/INDEX.md)。F01–F12当前合格数量仍为0。

| 旧编号/方向 | 证据处置 | 为什么不能照旧重跑 | v3出口 |
|---|---|---|---|
| O01 · CPU pool按expert/行块自适应切分 | 已关闭具体机制 | NP3校正后任务工作占88–90%；自适应/加权分行不能借新名重跑。 | F12，仅新暴露供给差量 |
| O02 · CPU GU→quant→down分阶段流水 | 已关闭具体机制 | 并行quant/阶段重排未建立净收益；每expert实际计算不能当同步空洞。 | F12，缺新机制即停止 |
| O03 · CPU工作量感知活跃worker与亲和性 | 已关闭具体机制 | POOL8退化，16–192任务扫描无稳定净益；原pool/亲和保持。 | 无默认续作 |
| O04 · 4216专用无VBMI的VNNI内核 | 已关闭具体实现 | P5 IQ3_S VNNI完整专家−0.152%，CI跨零；P12 gather更差；不扩格式。 | F02仅新load证据，不重做VNNI |
| O05 · 多token共享权重解包与ActQ复用 | 已有覆盖 | 多token共享解包已有；actual nt和命中须核，不能重复新增。 | F02仅融合内部差量 |
| O06 · CPU预打包布局与缓存行局部性 | 分析后未获资格 | 新同字节数布局须与P5/P12机制不同；不能双份扩内存或依赖VBMI。 | F02条件分支 |
| O07 · 按节省关键路径时间/字节选GPU专家 | 分析关闭，未实施 | NP-RES按当时成本/字节和热点分布判断不立项，未做离线模拟；必须有当前成本/字节或热点分布实质变化才可提新案。 | F08还需E1质量前置，非仅待质量放行 |
| O08 · 逐expert三路成本调度 | 分析关闭，未实施 | 原逐层PCIE_BALANCE含DDR/PCIe争用，逐expert细化按分析不立项；新复制债务/尾部必须超出已覆盖模型。 | F08还需新差量和E1质量前置 |
| O09 · adaptive tier与overlap/async成本治理 | 已测未采用 | lag2/nowait/async、固定PCIe分担无正式净收益；保留原overlap。 | 无默认续作 |
| O10 · PCIe已搬入专家直接晋升驻留 | 无新资格 | 现有驻留/cache已有复杂策略；已搬入晋升没有新的因果和完整性能证据。 | 不以HC/缓存改名重开 |
| O11 · 已有专家预取的预测与成本改进 | 已覆盖及旧负证据 | 已有预取、learned profile未过；Edge0只有保留true demand的合同可借鉴。 | F12仅具体重复物化诊断 |
| O12 · 同窗expert union与dispatch去重 | 部分已覆盖/窄差量 | 现有grouped distinct expert和fused group不能重做；剩非fused整数metadata。 | F06，偏prefill |
| O13 · 统一DRAM/PCIe拷贝优先级与配额 | 只许诊断 | 拷贝总量不是暴露成本；P23少搬8.19GB没有兑现P24性能。 | F03/F12因果诊断 |
| O14 · 会话/任务感知expert热集 | 已测未采用 | learned expert profile无稳定净益；不新造热集反复扫。 | 无默认续作 |
| O15 · prefill单group scratch与区域复用 | 具体化但未获资格 | GROUP_SCRATCH旧分析项；Maya行窗/slab仅是更窄实现参考，非已测提速。 | F05/F07，保全Dm和生命周期 |
| O16 · prefill chunk/CPU-share/stream联合规划 | 早期配置已应用 | CPUSHARE4096/AUTOMAX16384保留；不再扫chunk/CPUshare救候选。 | 配置冻结 |
| O17 · prefill copied event稀疏化与wait去重 | 已有覆盖/窄问题待证 | 不凭event数量立项；host分组需保mapped表同步与上一层消费者。 | F06/F12仅新暴露gap |
| O18 · 跨subchunk专家复用与双staging | 已有覆盖/HC关闭 | 现有ring/staging不新；P24 HC关闭，不能用双staging名义继续HC。 | 仅独立source delta可提案 |
| O19 · 现有GDN_CHUNKED与sm89分块递推 | 数值路径/延期 | 已有GDN_CHUNKED与优化；新递推/TC形状需E1证明，非sm89开关扫描。 | F09，质量前置 |
| O20 · QSA prefill tile/选择/online softmax | 部分已有/延期 | QSA已稀疏选择；只等序选择可意图E0；tile/softmax改数值为E1。 | F04或F09，不能混类 |
| O21 · GPU专家GU/SwiGLU/down局部融合 | 融合已有/窄差量 | EXACT6 GU_SWIGLU、共享解包已开；EXPDEC会压掉融合。 | F02仅保持原规约的load/layout |
| O22 · dense MMVQ形状路由及Ada表 | 筛查后关闭 | 旧Ada表未过噪声；P11差量profile条件空间仅2.0–2.8%。 | 不扫新表 |
| O23 · draft-only head量化/紧凑候选词表 | 已测未采用/延期 | MTP Q4 head采样不稳；词表/draft变化先审proposal law与兼容资产。 | F10不重跑Q4扫描 |
| O24 · 目标LM head与采样的精确路径优化 | 没有新暴露证据 | lm head/采样在现有图和kernel中；先确认完整关键路径贡献。 | F12，仅有证据才设计 |
| O25 · Graph前移host工作与metadata复用 | 已有覆盖/仅诊断 | graph/metadata机制已有；图发射次数不是可删时间。 | F12 |
| O26 · accept/commit/计数的设备端合并 | 已有覆盖/语义约束 | accept/commit涉及真实token计数和状态；新合并须证明实际等待。 | F12；改变verify则F10 |
| O27 · 已有int8 KV融合路径的向量化与复用 | 已有覆盖/窄复用 | int8 KV、选页/向量搬运已有；剩canonical不变的跨query load复用。 | F01条件分支 |
| O28 · GDN decode状态搬运与融合 | 已有覆盖/数值分类 | GDN状态优化须查实际load；改变递推/规约按E1。 | F02窄load或F09 |
| O29 · 已有split-KV的tiny-query复用与自适应segment | split已存在 | CHUNK64 split/merge和GQA复用已有；不得新建同款split-KV。 | F01只查重复resident load |
| O30 · mapped fetch与显式DMA的成本选择 | 既有KVRES路径 | 先核已有host页staging/CLOCK；不以tqLLM新commit证明缺功能。 | F01 |
| O31 · 局部persistent任务区域与手递手同步 | 缺关键路径资格 | persistent改造成本高，旧NP3不是17µs固定同步；没有暴露gap不写。 | F12，当前不立项 |
| O32 · sm89编译与资源自动调参 | 不开放自动扫描 | sm89资源分析可用于单一合格kernel；不遍历宽度/寄存器/线程表。 | F02/F04限定实现 |
| O33 · 已有成本spec策略的本机校准与细化 | 已测未采用 | SPECCOST窗口短但提交token少，每token基本不变。 | 保持spec4/min-p0.5 |
| O34 · lookup长窗与MTP深度分离 | 已测未采用 | lookup-chain2无稳定收益；不得靠少验证/短输出计更快。 | 无默认续作 |
| O35 · prompt/history lookup索引与成本门控 | 有限筛查已关闭 | #4040可加速调用仅约0.8% decode；不是值得移植的热点。 | 无默认续作 |
| O36 · 兼容Flash-Next的DFlash/EAGLE类draft | 资产/质量前置 | 未证明兼容Flash-Next的DFlash/EAGLE资产与正确采样/状态回滚。 | F10延期 |
| O37 · 完整state checkpoint与ReplaySSM | 已有状态复杂度/无资格 | checkpoint、replay收益依赖真实恢复模式，单会话warm没有新证据。 | F12仅真实恢复gap |
| O38 · 多分支draft/tree验证 | 算法/状态前置 | tree verify会改target batch、proposal和rollback；不等于深度扫描。 | F10延期 |
| O39 · RAM准入释放与无效逐出修复 | 机制成立但未采用 | #2253 trim默认单会话不触发，轮转更慢；MMAP部分场景更差。 | 不重新部署trim/MMAP |
| O40 · slots/bytes价值与压力淘汰策略 | 主场景不支持 | 会话容量/压力策略不等于单会话decode提速，cache6144/4冻结。 | 独立场景才另立计划 |
| O41 · 增量快照与dirty KV分段复用 | 主场景无资格 | 增量snapshot需真实dirty/park/restore成本；不凭容量立项。 | F03仅实际内存冗余诊断 |
| O42 · 单GPU恢复缓冲复用与copy调度 | 主场景无资格 | 恢复buffer复用若已不暴露则关闭；不能引入额外串行copy。 | F12仅实际restore gap |
| O43 · SSD冷会话快照 | 不属当前主线 | SSD冷会话snapshot不是暖态单会话的默认瓶颈。 | 独立场景延期 |
| O44 · KV/状态/graph/expert统一显存预算 | HC关闭/精细差量待证 | 不重做泛统一预算；可只查活跃对象生命周期或MMQ scratch。 | F03/F05/F07 |
| O45 · 冷snapshot无损压缩与编码 | 不属当前主线 | 冷snapshot无损编码未获warm暴露资格；压缩CPU成本必须算。 | 独立场景延期 |
| O46 · 低比特KV格式及q4lm8v接入 | 质量变化/延期 | int8转更低bit KV改变目标数值；原六FAIL未解决。 | F11独立质量速度研究 |
| O47 · K/V非对称与旋转量化 | 质量变化/延期 | K/V非对称、旋转量化需独立数值和任务质量，不能包装E0。 | F11 |
| O48 · 近期精确KV窗口+压缩历史 | 质量变化/延期 | 近期精确+历史压缩改变目标KV；128K质量前提未建立。 | F11 |
| O49 · 活跃host-KV分块stage/双缓冲 | 已经有对应机制 | KVRES20480历史应用；P3正式门未过；选页stage已实现。 | F01仅新差量 |
| O50 · 分页layout与prefix softmax状态合并 | 模型/算术适配约束 | selected QSA不是dense prefix attention；softmax归并改序要重分级。 | F01精确load或F09数值路径 |
| O51 · 前缀编辑的多级循环状态检查点 | 场景不足 | 前缀编辑checkpoint需真实Pi编辑/重读分布，不当warm decode收益。 | 独立场景延期 |
| O52 · 替代权重格式/模型包 | 模型改变/延期 | 包名IQ3_XXS与P9 IQ3_S分清；P9同错不证明量化无影响。 | F11，不换生产模型 |
| O53 · 按层/专家敏感度的混合精度 | 模型改变/延期 | 按敏感度混精需要高质量独立基准与模型资产，非当前E0主线。 | F11 |
| O54 · 专家裁剪/减少top-k/tail-skip | 明确改变计算 | 更深tail-skip/降top-k/裁专家减少真实工作也改变质量。 | F11；冻结原target行为 |
| O55 · CPU专家延后跨层合并 | 明确改变计算 | 跨层专家延后改变依赖和输出，不归类纯调度。 | F11 |
| O56 · 激活稀疏/预测跳算 | 明确改变计算 | 预测跳算/激活稀疏需漏算与任务损害边界。 | F11 |
| O57 · 额外QSA/KV筛选或压缩attention预算 | 明确改变计算 | 额外QSA筛选/KV预算压缩超出现有数学；需绝对质量。 | F11 |
| O58 · Pi上下文组织/压缩与输出协议 | 部分配置已应用/PT0 | PT0和reply reuse保留；进一步压缩是产品质量取舍。 | F11独立研究；不能计同任务更快 |
| O59 · 并发与prefill调度公平性 | 非目标负载 | 当前单会话无并发；吞吐调度不能替代单请求时延。 | 当前不立项 |
| O60 · API/tokenize/SSE/工具链固定开销 | 早期已应用/工具已改 | #1536、SSE/token计数改进保留；余量需实际端到端暴露。 | F12仅新gap |
| O61 · 内存页/allocator/NUMA与有限pin预算 | 覆盖及有限空间 | THP约85%匿名内存；trim/MMAP负证据；不改系统参数，查对象生命周期。 | F03/F07 |
| O62 · LTO/PGO与CPU调度代码布局 | 无新关键路径证据 | LTO/PGO不能凭通用百分比立项；CPU等待分清调度与实际计算。 | F12或F02限定热点 |
| O63 · 功耗/频率/热稳态的性能效率 | 已应用且有边界 | performance/C6历史应用，收益近噪声；84/85°C边界已知。 | 热证据保留，不超频降压 |
| O64 · Ada Tensor issue-rate解锁 | 未验证/平台权限不适用 | 不假设Ada issue-rate解锁已测成功；涉及driver/系统与硬件边界。 | 本包不安装patch/驱动或改系统 |

## 重新打开一个旧编号所需的证据

必须写明旧实验到底否定了哪个机制、新变化相对P6真实入口是什么、为何旧反例不再适用、当前完成路径上有多少可省成本、资源与数值如何保持。只有新仓库名、更多参数、不同微基准、更多显存节省或更高孤立kernel吞吐均不构成证据。P02独立复核并且一次只允许一个候选。

NP3否定的是其已测调度/分行/quant/repark机制，不能扩大成所有CPU数学核永远无优化；反过来，P5单格式未过也不给扩格式默认资格。P10/P11是有限筛查，不能写成已完成所有on/off实现。HC经过完整链条后性能失败，生命周期与oracle工具可复用，HC候选本身保持关闭。
