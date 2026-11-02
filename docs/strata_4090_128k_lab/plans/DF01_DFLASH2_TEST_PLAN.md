# DF01 · Flash-Next / RTX4090 DFlash2完整测试方案

当前状态：**2026-11-02 D1T最终根因未定位，按用户要求停止当前候选。** 见[D1T停止回执](../reports/DF01-D1T-FINAL-CPU-STOP-20261102.md)及[Astra唯一终审](../reports/DF01-D1T-ASTRA-REVIEW-20261102.md)。D1T完成最后一轮纯CPU审计及唯一一次Astra xhigh终审。冻结CPU尾部逐bit复现；同GPU行CPU尾部7/7匹配，最大概率差6.71e-7，确认前向行差经相同尾部导致候选排序翻转。首个错误算子和最终根因仍未定位，无可证实单点修复；按用户要求STOP_CANDIDATE，停止当前DFlash2候选排查与后续测试。原FAIL/参考/硬门保持，D1未通过，GPU/完整backbone/生成0，D2未开始，生产继续停机。 以下旧阶段与预算只作追溯，不授权新定位或实验。

较早状态：**2026-11-02 D1S按冻结v2执行，在n2300 token硬门失败，D1未通过。** 见[D1S报告](../reports/DF01-D1S-V2-QUALIFICATION-20261102.md)。D1S绑定冻结v2后执行1个GPU程序、4组夹具、0生成。n32/n2048/n2064通过v2 drafter硬门；n2300为6/7 token一致，第4项实际209087、参考212522，selector token 3触发exit1后停止。置信度差只作诊断，原token门及其余硬门不改。后12组和六次生成未运行，无重跑/替补，GPU窗口2.119秒。原FAIL/原四组参考保持，D1未通过，D2未开始，生产继续停机。 根因未确认，不自动继续CPU修复、GPU或D2。

较早状态：**2026-11-02 D1Q完成v2最小分类适配与CPU验证，D1未放行。** 见[D1Q回执](../reports/DF01-D1Q-V2-ADAPTER-20261102.md)和[源码](../tools/dflash2_v2/README.md)。D1Q完成v2最小分类适配及CPU检查。仅完整drafter置信度绝对差为诊断；原行/token、概率有限值/范围、独立selector、target采样、提交状态和EOS硬门保留。原四组参考及旧FAIL不改，独立GPU程序只编译/链接，GPU/完整模型前向/生成0。最终身份为FINAL_FREEZE.json，D1命令为COMMANDS_V2.json，全部execute=false；D1未放行、D2未开始，生产继续停机。 新GPU批次必须另获授权并绑定最终清单和新预算；不得忽略旧exit1。

较早状态：**2026-11-02 D1P完成纯CPU合同复核，后续默认exact-match置信度差改为诊断项；D1未放行。** 见[D1P报告](../reports/DF01-D1P-EXACT-MATCH-CONTRACT-20261102.md)与[合同v2](DF01_D1_EXACT_MATCH_V2.md)。target采样、有效前缀提交、EOS及其余硬门保持；原FAIL/gold和D1O统一参考失败不改。源码与104976组有限模型/三负例检查通过，GPU/模型前向/生成0。旧程序未改，v2适配与GPU硬门未完成，不忽略旧exit1、不进入D2，生产继续停机。

较早状态：**2026-11-02 D1O完成CPU排查，统一新参考回归失败，不采用。** 见[D1O报告](../reports/DF01-D1O-N2048-CPU-AUDIT-20261102.md)。Astra xhigh同GPU rows重算尾部误差4.77e-7，差异定位到drafter前向行。来源顺序RMS/RoPE/分块attention组合在n2048离线原门通过（maxp差0.0386763），但同实现n32回归失败（0.0853075）。四次CPU完整前向及全部正负结果保留，首个n2048偏离算子未确认；GPU/生成0，不修改原D1N FAIL/gold，不按context选规则，不进入D2。生产继续停机。

较早状态：**2026-11-02 D1N补验在n2048概率门失败，完整D1未完成。** 见[D1N报告](../reports/DF01-D1N-REMAINING-QUALIFICATION-20261102.md)。四组修正CPU参考及输入身份在14分52秒内冻结，965项身份核对后GPU实际1程序/2组夹具/0生成。n32回归通过；n2048第2项概率差0.079903543超原0.05后停止，后14组及六生成NOT_RUN。无重跑/补样本，不改原门、gold或历史FAIL，不进入D2，生产继续停机。

较早状态：**2026-11-02 D1M修正CPU参考后，原首组保存原件的离线数值门通过；完整D1未完成。** 见[D1M报告](../reports/DF01-D1M-CPU-REFERENCE-CLOSURE-20261102.md)。新增GPU/生成0，真除＋来源一致卷积＋planar整数GEMM组合使token7/7一致，最大概率差0.0451068低于原0.05；未改原门、gold或历史FAIL。原C++比较器及三负例控制通过，Astra xhigh独立复核接受该单夹具边界。其他资格夹具、target-state及六生成仍未运行，D2未开始。生产保持停机，后续恢复等待用户明确要求。

较早状态：**2026-11-02 D1L定位并修复首个CPU量化算子缺陷，完整夹具仍失败。** 见[D1L报告](../reports/DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)。实际1 GPU程序/原首组1夹具/0生成、无重跑，逐层323项采集；Astra xhigh核实CPU反除双舍入导致tap q60而原生59，改真除后5项CPU检查通过。修后token5/7、最大概率差0.0718193仍超门，D1继续BLOCKED_NUMERICAL_ORACLE；原FAIL/gold保持，不进入D2。生产保持停机，后续优先使用现有原件纯CPU核对。

较早[D1回执](../reports/DF01-D1-QUALIFICATION-20261102.md)保留首组失败、后15组/六次生成NOT_RUN及当时恢复生产的记录。

较早[D0B回执](../reports/DF01-D0B-CPU-READY-20261102.md)保留CPU_preparation_ready=true；CPU准备通过不代表GPU资格通过。

较早的[D0实际回执](../reports/DF01-D0-PREPARATION-20261102.md)保留BLOCKED_PREPARATION，不改写5947/81-token短样本和缺失夹具的结果。

历史方案状态：2026-10-31为PLAN_ONLY，当时未授权下载或实验。本方案按用户提供的新证据制定；DFlash2作为独立草稿算法获得一次限额资格筛查的建议，DSpark不进入实施队列。本文件只规定新编号DF01，不倒写历史失败或复活已关闭微内核方向。

## 1. 以前做过什么，哪些尚未测

本包此前做过[#3322源码/资格检查](../prs/10_PR3322.md)，保留了DFlash2单卡CLI支持、服务回退、资产及显存风险记录；[Gate P0](../reports/GATE-P0-20261025.md)和config/experiments.json仍记录下载未批准、BLOCKED_DFLASH2_DOWNLOAD_NOT_APPROVED。**在本包报告及原件索引中未找到29上Flash-Next DFlash2的有效性能A/B；不能将BLOCKED说成实测无收益。** 旧PR被prepare/apply检查过，也不表示其drafter已执行。

MTP spec3/4/5、Q4 head、SPECCOST、lookup的关闭结果不覆盖更换草稿网络及生成算法；HC/F02的负结果也不覆盖它。U01R1是两个版本在原MTP下的比较，不是DFlash2比较。上述历史结论全部保留。

DFlash2还可能通过减少target验证轮数节省verify成本，现有MTP的draft耗时占比不是它的收益上界。新增机制仍需按完整decode和真实资源代价验证，不能从接受率或公开硬件数字直接晋级。

主代理本次只读jssh 29确认生产active/running/enabled，核对A0/P6源码及指定数据目录文件头，未运行引擎、未下载权重。现有四份同名资产为GGUF：

| 所查现有文件 | metadata | 本次用途 |
|---|---|---|
| /data/models/qwen/qwen38-lucebox/qwen38-dflash2-f16.gguf | qwen35-dflash-draft，5120 hidden，5层，3849350176bytes | 不符合native Flash-Next loader |
| 同目录qwen38-dflash2-q8_0.gguf | 同上，2045471776bytes | 不符合native Flash-Next loader |
| /data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q4_K_M.gguf | dflash，5120 hidden，5层，1143006752bytes | 27B路线，不能混用 |
| 同目录Qwen3.8-27B-DFlash2-Q2_K.gguf | 同上，705431072bytes | 27B路线，不能混用 |

A0/P6的native loader要求**DF2P v1、hidden2560、Q heads32、KV heads8、head_dim128、selector rank256**；上述GGUF的格式和hidden均不符。所查/data/strata-data、/data/models及hhtele HF缓存未确认可用Flash-Next原生pack；这是有限路径/metadata核查，不是全机不存在资产的证明。另一个NInfer/27B方向的目录或权重存在，不构成本机本模型已经测过的证据。

## 2. 来源、实验版本与范围

完整第一方核查见[来源报告](../reports/DFLASH2-SOURCE-REVIEW-20261031.md)。关键冻结身份：

- 主实验基线：A0/v0.2.3及现有生产EXACT6、reply/PT移植；优先复用同SHA native 819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d。生产树只读，在独立实验树运行。
- P6/v0.2.7只作源码参考；本次不为DFlash2升级引擎。主代理逐SHA核对A0/P6的drafting.py、core/dflash2.cpp、CUDA dflash2.cu、两个dflash2.hpp、packer及draft_cap.hpp七文件相同；generate.cpp整体不同，不据此宣称两版所有执行行为相同。
- 官方checkpoint：incoai/Qwen3.8-Flash-Next-DFlash2，revision **a22a1744e85c17364dcc54a6a420af7135d4c7f6**，Apache-2.0。config.json 1236bytes；model.safetensors 1206140008bytes，SHA256 **d6723f2a359eaf33ec0c95f22ae8edda896774020c552296a85e1913b4d3186f**。从固定文件生成单一Q8 DF2P候选，不能下载resolve/main或把27B GGUF重命名。
- 指定主线c62d5e3a15b40ea51c96aae9e8d36928965f53ab只作来源，不更换A0基线。#3322已closed/unmerged，不能整分支移植722文件，也不把该分支NVFP4收益算到当前实现。
- DSpark只记录：社区checkpoint的长上下文accepted长度未优于MTP7，上传/接受率/速度来自不同训练step，Strata Qwen缺接入；当前不下载、不移植、不列并列候选。

官方GB300/FP8/SGLang相对MTP约12.9%–24.2%的增量，是来源信号；消费卡有正有负，不能预测本机收益。DFlash2源码预算约1.0–1.2GiB，ring几何80.625MiB、feature容量估算100MiB，并不代表实际峰值或净增量。文件大小、常驻字节、加载峰值和专家槽损失分开记账。

**服务边界：** A0/P6/指定主线均禁止DFlash2的--serve、--batch和layer split，Control为ENGINE_SERVES_DFLASH2=False。CLI通过只能形成CLI研究结果，不能说明Pi/API已经获益。初筛不删除这些guard、不开发服务适配。

## 3. 阶段、预算与决策

各阶段独立登记；后续预算不是当前授权，也不是通过前一阶段后自动开跑的额度。每阶段首个基础设施/资源硬门失败即收口；普通模型错误保留，不补样本。

| 阶段 | 目标和交付 | 明确上限 | 进入下一阶段的条件 |
|---|---|---|---|
| D0 CPU/资产资格 | SOURCE_AUDIT、ASSETS、CLI_COMMANDS、INPUTS、METRICS、PREREGISTRATION | 最多1工作日；本阶段0 GPU | 能力、资产、计数、采样与资源合同明确；没有必要新框架 |
| D1 机制/正确性 | 实际命中、pack/target/commit与采样证据 | 最多60分钟；2个原生GPU正确性程序（总≤16 fixture）＋6次CLI生成 | 真DFlash2、无回退；正确性/资源无阻断 |
| D2 有限筛查 | 一次噪声校准＋两种cap的固定矩阵 | 最多3小时；6次MTP A/A＋16次CLI对照＝22次生成 | 唯一cap有可信净信号，主长上下文未失败 |
| D3 正式CLI性能 | 留出主场景6对＋支持场景4对 | 最多1工作日；20次CLI生成 | 主时间门通过，TTFT/整请求与支持层无重要回归 |
| D4 CLI任务质量 | 原失败与留出代码/工具语义 | 最多1工作日；18题×2臂＝36次生成 | 无新增失败且质量证据足够；否则仅RESEARCH_RESULT_ONLY |
| D5 服务可行性与验收 | 状态生命周期设计、实现、API/Pi验证 | 先≤2工作日CPU设计审计；后续GPU须独立范围，最小API阶段≤24次POST | 完整状态/取消/恢复成立，性能及正式质量门均满足 |

**原完整维护窗口提案覆盖D1+D2：最多30个GPU进程，其中28次自由生成＋2个有界原生正确性程序，总≤4小时，至少预留10分钟恢复。** 2026-11-02实际新增授权收窄为D1、≤60分钟；不自动进入D2。 D0准备在生产运行时完成；缺资产或采样证据就在停机前结束。

进入D3/D4后，服务前CLI累计上限84次生成＋2个正确性程序；D5若单独授权再增加≤24次API POST（含无效请求/取消，不隐去计数）。各阶段不可挪用剩余额度做临时扫参。时间先耗尽则剩余NOT_RUN，失败/OOM/短输出不替补。

## 4. D0：停生产前把合同补齐

### 4.1 能力、资产与隔离

1. 只读核A0实际binary/build receipt/CMake定义与DFlash2符号；源码存在或--help列出参数不等于binary含STRATA_HAVE_DFLASH2。能力未知记BLOCKED_CAPABILITY。
2. 先查指定draft目录的文件magic、metadata与SHA；只有没有合格现有产物且用户授权获取资产时，才获取上述固定config/safetensors并用固定packer转换。新增下载约1.21GB；源文件、Q8 pack、必要参考与raw总新增磁盘预算≤6GiB，开始前可用磁盘≥8GiB。网络/哈希失败至多一次不同方式恢复，仍失败即关闭本次准备。
3. 核target架构、hidden2560、vocab248320、tokenizer/特殊token hash、taps[5,15,25,35,45]、mask248077、rope/window、selector及head/draft_vocab映射。两个模型名称相似不能代替合同。
4. 如需两点host计时或原binary缺必要构建能力，只在隔离A0树最小构建；原工具链CUDA12.3/sm89/Release和mandatory开关不变，两臂使用**同一个实验二进制**，先验证关闭路径。不能拿原MTP二进制对新候选二进制而不验证编译差量。
5. 原生CLI适配器另建最窄入口，不绕过现有通用runner的--mtp冻结门。继承原生产target参数/环境白名单，只移除serve/传输模式所必需的参数、重定向写入路径、加入tokens-file/max-new/draft差量；NATIVE_COMMANDS.json逐项列出增删及理由。

### 4.2 采样资格

生产相关设置为temperature1/top_p0.95/top_k20、xhigh，经原模板/PT0渲染；CLI不存在的reasoning参数不能杜撰成flag。DFlash2 selector置信度不是目标采样概率。

本机U01R1实际环境中STRATA_SPEC_PROB、STRATA_SPEC_COUPLED、STRATA_SPEC_GATE_PICK及STRATA_VERIFY_PROFILE均未设置。继续白名单继承，禁止为追速度新增这些概率模式、forced continuation、skip组件或更深tail-skip。

源码中DFlash2 proposal由df2.draft生成，某些PROB分支仍可能将mtp.spec_q交给verifier；**DFlash2+PROB正确性UNKNOWN，本方案拒绝该组合**，不将其定为已复现bug。默认exact-match分支也须明确目标逐位置采样、RNG推进、所有processors、拒绝后重采样与commit/rollback的实际算法。

确定性proposal＋目标独立采样的正确性证明，与随机proposal的p/q/拒绝残差证明分开，不一律索要不存在的DFlash2 q，也不只引用论文。用实际共享采样原语做小分布枚举/统计负例及首拒、中拒、全拒、全接受/EOS/状态测试；没有可审阅路径则BLOCKED_SAMPLING，仅可交付greedy机制研究，不能继续生产采样性能阶段。

跨fresh engine输出不逐bit已是既有事实，不能要求相同seed整段文本相等；也不能据此豁免同输入/同实际dispatch的target数值与状态检查。沿用P13–P21匹配路径的方法，必要变化按E1记录。

### 4.3 输入、计数与终止

冻结以下4个选择集单元，另留出D3主/支持及D4任务集，候选结果不能用于更换样本：

| 单元 | 实际渲染输入 | 内容和评分用途 |
|---|---|---|
| S-C | 约8K，允许6–10K | 原计划为Pi风格代码；D0B按新增授权使用superuser源码构造，实际7907 |
| S-R | 约8K，允许6–10K | 普通解释或推理 |
| L-C（主单元） | 96–120K | 真实Pi R04代码修改历史，实际104207；原103183样本归类为L-R |
| L-R | 96–120K | 长文档解释/推理，独立于代码样本 |

D0从现有Pi历史按完整turn边界选择满足长度/内容条件的样本，保留原请求；缺某类则标缺失并在启动前收口或给出明确合成替代标签，不剪错答历史、填充提示或伪称真实流量。CLI只得到模板化token投影，不执行工具，也不能声称Pi/API工具链已验收。

2026-11-02用户新增授权参考两个代码仓库补齐输入。D0B只替换缺失单元：S-C7907、D3-S-C6717来自hhtele-superuser，D3-L-C105962来自lishuedu-data-sync。来源明确标为repository_constructed_not_pi_session，固定HEAD、完整文件清单、SHA与取样计数全部保留。未重复文件或填充，选择过程没有观察候选输出。原四项有效Pi投影继续复用。

每项保存原session/entry来源、脱敏规则、完整messages/tools/template kwargs、PT0计数环境、rendered token IDs及SHA、gold/语义检查和EOS/turn-stop规则。沿用U01R1修复：CPU计数环境必须匹配runtime；native输入ID数与tokens-file字节身份闭合，不把batched prefill的N−若干尾token错认为未读prompt。

D1/D2每次自由生成max-new=2048，思考/正文均计入真实committed token；保留真实EOS/turn终止。主代码单元须≥1024实际输出及≥128个完整verify轮；不够则INSUFFICIENT，不关EOS、不补文字、不换容易长输出的题。解释题短EOS照存，只作有限支持。完整输入＋输出预算＋4096≤131072；120K输入122880时仍可容纳2048输出。--max-context 128K不等于实际填充128K。

### 4.4 指标：先修采集合同再跑

CLI已有prompt/output原生ID列表、DFlash2轮数、窗口/接受直方图与draft汇总，优先复用，不从文本重新分词。必须通过启动DFlash2 drafter on、最终非零df2.rounds、实际开关/pack身份、无MTP回退提示四项同时确认命中；未命中即FAIL_ACTIVATION，不作为DFlash2性能样本。

已知CLI的decode打印采用逐轮total_ms累加，最后ver.wait_commit位于累加之外；**不能直接当完整decode连续墙钟**。在隔离树增加至多必要的host边界时间戳：目标prefill完成/进入首个生成所需初始化前，至最后必要commit及线程join完成后；明确首次bind/prepare/graph初始化是否在边界内，两臂一致，保留冷启动成本。无新增CUDA调用、同步、GPU event或执行图节点，测量后统一导出；若无法闭合，指标UNKNOWN，不开正式性能。

主指标t_token=完整decode连续墙钟ms/实际committed tokens（thinking与正文均计，EOS策略一致）；同时报告相反单位tok/s。CLI完整wall从子进程启动到正常结束，分列加载、prefill/TTFT、decode和退出；不能将其冒称HTTP请求wall。已有native decode累加、CPU专家/draft/verify/copy分项仅辅助，不能相加当可省墙钟。

窗口T直方图、每轮提交与接受率、fallback、actual slots、GPU常驻/峰值、native RSS/PSS/Swap、MemAvailable/fault、CPU专家与必要copy计数都留原件；没有可见字段标UNKNOWN。逐窗写盘/STRATA_SPEC_TRACE、DF2_PROFILE等仅限D1诊断，不进D2/D3正式计时；不为填齐表格加一个全新大型trace系统。

## 5. D1：历史v1合同与后续v2入口

后续默认exact-match资格分类以[合同v2](DF01_D1_EXACT_MATCH_V2.md)为准；仅完整drafter置信度绝对差改为诊断，目标采样、提交状态、EOS及其余硬门保持。旧GPU程序仍按v1退出；独立v2适配、CPU正负例及最终封存已在D1Q完成，不改原binary或FAIL。当前没有GPU执行授权，也不改判原FAIL。以下保留原v1设计与历史预算，用于追溯。

两项原生正确性程序只用锁定fixture，合计≤16项：固定packer与reference的stage/selector/前驱语义、2048/2064环边界；以及target verifier有效输出、首/中/全拒绝、EOS、commit所需KV/GDN/PLE/MTP状态。先核现有dflash2_parity、draft_cap_test、spec_prob_test及参考脚本的实际参数、CPU/GPU依赖，不能把test目标存在当已通过。Q8 draft与其量化后参考比较，不要求Q8草稿逐bit等于BF16；target不允许被换量化。

D0B已编译7+9共16组资格夹具。四组Q8参考按32/2048/2064/2300 context和seed1/2/3/4冻结，使用实际Q8 pack与来源匹配的激活量化；初版FP32激活参考保留但不执行。独立selector加token/概率硬断言；目标程序要求DFlash2和target taps实际启用，检查host sampler参考与KV/GDN/PLE/index/MTP状态。CPU比较器通过不等于原生GPU通过。细节与binary身份见[D0B回执](../reports/DF01-D0B-CPU-READY-20261102.md)。

然后仅执行3对：greedy S-C MTP4/DF-cap4；生产采样S-C MTP4/DF-cap4；生产采样L-C MTP4/DF-cap8。总6次生成用于资格，不是性能显著性样本。校验真实开启、非零轮数、raw IDs/结束/资源、无回退；基线必须实际走MTP而非普通AR。

主资源比较采用同一4090总预算及既有安全余量、各自正常auto专家缓存。DFlash权重/环/特征/head仍连同MTP fallback驻留，净挤出专家的成本必须计入，禁止宣称卸载MTP释放950MiB。先按原974MiB预留核实际分配；如实现确需候选专用1900，D0预先声明并记作DFlash真实成本，MTP主臂仍保留原974。没有预登记的资源调整则停止，不临场改预算救OOM。固定同槽数只可另立诊断，不进入本次主预算。

缺显存、触发85°C/4096MiB、pack/shape不符、自动回退MTP、capture OOM后自动缩小window均终止该配置资格，不把内部降cap后的结果冒充原cap；保留原件，不替换失败样本。target数值、采样或状态错误立即结束整个候选。

## 6. D2：只选一个cap，禁止宽扫

在D0冻结全部配置、选择规则与数据后，先做3对MTP/MTP A/A（6次fresh CLI），使用预先冻结的D3主长代码probe。噪声ε=各对主ms/token时间比偏离1的绝对值中位数，门m=max(4%,2ε)。不能用旧HTTP噪声替代；短输出导致probe不稳定就BLOCKED_EVIDENCE，不继续找容易的probe。

随后4个选择单元分别做一对MTP4 vs DF-cap4、一对MTP4 vs DF-cap8，共8对/16次生成。按预登记相邻配对交替先后，各单元两组相反顺序；每次fresh engine。MTP始终spec4/min-p0.5；DF4为spec4/draft-cap4，DF8为spec8/draft-cap8，draft-conf保持0、沿用min-p0.5，不扫confidence、min-p、量化、线程、预算。

spec/draft-cap是verify行数上限，含anchor；DF始终计算7提案，cap4最多用3、cap8最多用7，阈值可能让实际窗口更短。必须报告实际T，不能把设cap8当实际每轮验证8行。默认控制策略和公开最佳cap5只作先验，本轮仅4/8两个预设，不看到结果后补5/6/7。

D2是有限筛查，不作统计PASS。晋级需：L-C完整ms/token点改善≥max(8%,2ε)且机制命中，S-C不出现超过max(2%,2ε)的明显恶化，无新增正确性/资源问题；S-R/L-R用于检查适用范围，不与代码收益相乘。两cap均满足时按L-C主指标选唯一者；近似打平选择较小cap。只有短档快、主长档无益则关闭当前128K候选，不换主指标。高噪声/缺字段/短输出记INSUFFICIENT并止步，不加样本。

8%是为后续服务工程设置的**新有限筛查余量**，4%仍是正式最低时间改善门；两者均非预测收益，不追溯重判旧实验。

## 7. D3：正式CLI统计，仍不等于Pi采用

只保留选中的一个cap、同一Q8 pack、同一binary与正常auto缓存资源。主场景为独立留出的约100K长代码，输出自然达到固定2048方可配对；D2已先核MTP probe资格，候选早EOS同样导致INSUFFICIENT，不补样本。冷CLI没有warm append状态，不调用旧P05 warm runner伪造warm证据。

主6对fresh engine，顺序AC/CA/CA/AC/AC/CA，共12次CLI；独立S-C、L-R各2对支持，共8次，总20。正式臂删除逐窗trace、PROFILE、dump、固定续写和诊断调度键，不能仅设0；同一个最小host边界计时用于两臂。若删除诊断键改变了D2校准环境，A/A不得复用，本阶段先BLOCKED并另列校准预算，不能藏加6次。

对每对r=(DF完整ms/token)/(MTP完整ms/token)，用整对log ratio六对精确bootstrap（6^6=46656）输出95% CI；主门CI上界≤1−m，其中m=max(0.04,2ε)事前冻结。4%时间下降相当于至少约4.17%吞吐提升，不把二者混写。主场景TTFT及CLI完整wall的时间比CI上界≤1.02；支持层仅描述/异常筛查，不用两对声称2%正式非劣。支持层明显恶化>max(2%,2ε)保留INSUFFICIENT，不隐去。

不得以kernel快、draft ms下降、accepted比例或tokens/round单项晋级。关系式仅用于解释：ms/token比=(每轮完整墙钟比)/(每轮实际提交token比)，新增显存带来的专家/传输成本已在完整墙钟中。实际结果始终从总提交数与连续时间直接计算，不相加CPU/GPU累计时间。

## 8. D4：任务与数值边界

36次CLI质量生成：原六个长检索冻结body/原gold、4个独立严格工具语义case、8个独立代码任务，每题MTP/DF各一次。输入来源、留出划分及gold在D0冻结，不与cap选择集共享。长任务输出预算按131072−4096−真实输入夹住，采样/EOS不变；失败记事前预算B的restricted time-to-success，不能把早失败当更快完成。model代码仍只在原受限Docker评分，工具不执行外部副作用。

这是质量筛查，不是正式2pp非劣；六个旧变体也不都算独立任务。现有quality_gate的正式非劣所需独立任务量另列成本，不许把36次请求或token当作足够样本。已知六FAIL继续原样显示，不因推测解码理论或两臂同错而改成PASS。

任何新增task失败、重复/丢token、错EOS、proposal q来源不明、完整状态不符，都停止采用。即使CLI性能过门，质量未满足时最高RESEARCH_RESULT_ONLY/BLOCKED_QUALITY，不能由CLI切换生产。

## 9. D5：服务集成是另一项工程

只有D3有稳定价值且用户明确选择服务工程时，才先做≤2工作日CPU设计审计，交付每个owner与恢复边界：target taps、DF ring/KV/位置、selector缓存、MTP fallback、graph地址、会话ID与epoch、预算/失败/取消、prefill与prompt-cache/checkpoint/park/restore/编辑失效。无法说明完整生命周期就输出BLOCKED_SERVE，保持guard，不硬接旧PR。

必须实现草稿状态如何随target提交、截断、丢弃与恢复的合同；合法旧分支不能直接删，不能靠增预算、更改PT0或现有缓存槽数规避。CPU故障注入覆盖关键分配、提交与取消边界；模拟PASS不冒称GPU/DMA验收。

若随后获GPU/API验收授权，最小24次POST：两臂各12步，依次为真实长prime、真实append、side分支、返回旧分支、编辑前缀、取消一请求、取消后追问、无效预算请求、错误后恢复、另一分支prime、旧分支restore、最终追问。无效请求与取消也计数；每步保留真实历史与usage，不伪造固定同hash性能配对。加入本机真实Pi客户端的工具结构解析与限定沙箱读/改文件，未跑真实客户端则明确NOT_RUN。

candidate API的每个有效生成请求都须证明DF实际命中，而非Control/engine回到MTP；将缺少状态时明确降级的事件单列，不能把fallback结果当DF收益。GPU中途DMA故障等未覆盖项保持NOT_RUN。随后如要正式API性能和独立质量验收，另立预算/留出集，不能拿24步冒称正式采用。

## 10. 运行保护、回滚与最终输出

D1、D1C和D1R按用户指令使用ssh 29；D1C/D1R按新授权保持停机，后续恢复等待用户要求；未来GPU阶段按对应新授权选择连接方式，进入前核原生产unit/13保护SHA、在途请求、唯一GPU归属、磁盘及输入身份；只停已授权原服务，单GPU串行。生产/回滚目录、NGINX、系统/CUDA/驱动及Pi配置只读，CLI不监听服务端口。GPU85°C、MemAvailable4096MiB、context131072及4096预留为硬门，所有采样/失败/swap保留。

当前D1N/D1O/D1P/D1Q/D1S/D1T按用户新授权保持停机。监督器只清理本run拥有的进程，不调用服务start/stop，结束后核对inactive/dead及保护SHA；恢复等待用户明确要求。

**以下为原临时停机窗口的历史恢复合同，不适用于D1N/D1O/D1P/D1Q/D1S/D1T：** 专用监督器在正常、超时或异常时先收回本run拥有且PID/starttime/exe匹配的进程，再恢复原v0.2.3 unit。若有不属于本run的GPU进程，不杀对方，报告HAND_BACK_FAILED并处理可确认归属的部分，不能宣称恢复成功。恢复以active/running、health loaded、正确模型/131072、NGINX认证边界、13保护SHA、实验进程退出为准，不能只看systemctl start exit0。

最终分别输出source/asset、mechanism、sampling/numeric、performance、absolute/relative quality、resources、serve、production状态。附实际launch/生成/POST数量、所有NOT_RUN、actual IDs与请求hash、真实DF轮数、资源/slots、原件manifest、选择/留出结果及独立复核。性能胜利不自动授权部署。

2026-10-31方案制定当次仅完成来源与本机只读核查。2026-11-02的D0首次检查受阻，此后按新增授权完成D0B的CPU缺口修复。D0B之后，用户单独授权D1。D1已按首组概率检查失败收口并恢复原生产；实际1项GPU程序，0次自由生成。D2及服务接入未执行，无commit或push。随后单独授权的D1C CPU审计/可确认修复完成，原GPU根因仍未确认，生产按新要求保持停机。新GPU复测或生产恢复均须按后续明确要求执行。

D1R随后按独立授权完成唯一GPU单夹具诊断：原门失败、actual rows/tail已采集，差异定位到drafter前向，首个分歧算子未确认。CPU修复未消除整段差异，旧失败与冻结金标保持，不继续GPU或D2。

D1L后续独立授权完成逐层采集与首个CPU planar反除修复，Astra xhigh复核接受最小修复；完整前向仍失败。当前只保留现有原件，不自动追加GPU或D2，生产保持停机。

D1M随后按独立CPU-only授权复用D1L原件，修正参考的卷积/GEMM算术顺序。原首组保存原件对独立新参考满足原数值门，完整D1未完成；本轮GPU/生成0。CPU参考版本单独保留，不覆盖原gold、不倒写旧FAIL，不自动追加资格夹具或进入D2，生产继续停机。

D1N随后按单独授权完成四组新参考冻结与有界GPU补验，n32回归PASS，n2048 selector probability 1绝对差0.079903543超0.05后停止。实际1程序/2组夹具/0生成，无重跑/替补，余14组与六次生成未运行。D1仍不放行，旧FAIL/gold保持，D2未开始，生产保持停机。

D1O随后按单独CPU-only授权完成n2048尾部与来源算术审计。新固定组合n2048离线满足原门，同实现n32回归失败，因此没有合格统一新参考。原D1N FAIL/gold及其余NOT_RUN保持，本轮GPU/生成0，不进入D2，生产继续停机。

D1P按新增30分钟纯CPU授权完成默认exact-match合同复核；完整drafter置信度差可在后续v2分类为诊断，其余硬门及旧FAIL保持。v2适配未实现，GPU硬门未运行，D1未放行，D2未开始，生产继续停机。

D1Q按新增纯CPU授权完成v2最小适配、CPU分类/原硬门负例、原四组参考身份及新源码/binary/D1命令封存。仅置信度绝对差为诊断；原FAIL与参考保持。GPU/完整模型前向/生成0，D1未放行，D2未开始，生产继续停机。

D1S按新增2程序/16夹具/六生成/60分钟授权执行，实际1程序/4夹具/0生成，前三组通过、n2300第4项token失败后停止。GPU窗口2.119秒，后12夹具与六生成未运行，无重跑或补样本；原FAIL与参考保持，D1未通过，不进入D2，生产继续停机。

D1T按最后一轮30分钟纯CPU授权及唯一Astra xhigh终审收口：尾部同输入复现，差异定位到前向行，但首个错误算子和最终根因未确认，无可证实单点修复；按用户要求停止当前候选，不再追加定位或实验。完整backbone/GPU/生成0，原FAIL与参考保持，D1未通过，D2未开始，生产继续停机。
