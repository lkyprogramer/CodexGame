# 已完成Baseline与当前研究身份

## 当前结果：H3-T01 Stage A实机因新驱动初始化错误停止

`MINIMAL_VALIDATION_INCOMPLETE_DRIVER_WORKSPACE_ZERO_FAILURE`。唯一冻结r1实机已执行：6个独立Op数值/Graph场景PASS（6direct Op、6capture/12replay）；第7个GDN Record/Fold链因新驱动以合法0工作区需求构造非零Arena而Exit1，未进入链Op。产品路径已有最小容量处理，不归为W6数值或性能失败。native/Chat/warmup/wire/模型加载提交均0，完整逐bit与W4→W6 decode/TTFT收益均未建立。

24.560秒完成候选清理，GPU idle、lease free，原服务STOPPED/身份不变。原账本RUNNING/链RESERVED保留；实际进程均已退出，派生已知失败终态单列，无未知模型请求。失败链未写audit.json，已完成阶段小计18算法kernel，完整资源实际总量null并披露缺口。原始日志/账本/冻结身份已持久归档和本地SHA核验。

入口已消费，不可重启；本轮无补测或源码修改。后续只修驱动零容量与失败审计并版本化接续；复用6个PASS，不重跑旧任务，不开发W8，不改默认分派/采样/Pi32768。全部历史失败、18处G1差异和C1缺口保留，资格与发布PENDING。以下空账本/未运行等仅为历史状态。详见[实机结果与资源缺口](../../ninfer-v4-h3-w6-hardware-20261024.md)。

## 历史准备：H3-T01 Stage A冻结记录（该入口已消费）

`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。隔离分支codex/h3-w6-existing-route-20261024，raw基点a5ba33de…，源树`49bee647112ee171de35529028fc271494260751`；没有新commit/push。默认/诊断BO构建、16具名CPU场景和双轴集成评审通过；Spec原1项P2仅定向修订复验case11，实际CPU场景执行17次，其他15复用。默认诊断开关OFF；产品默认None/0/Full与原显式W4/K3对照均保留，候选只显式使用现有W6/K5。不开发W8、不改Target采样/缓存格式/Pi32768。

唯一实机入口`/home/hhtele/ninfer-v4-h3-w6-20261024/prepared-window-r1`，freeze `4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc`；ledger PRISTINE全0、runtime不存在。新增数值收窄7场景/9direct Op/7capture/14replay，因为原P4 GQA T6有实际PASS且28个相关源码blob相同，直接复用。native2场景/4请求，计划9≤16decode调用；6Chat＋2warmup/10wire，总12模型工作提交。全窗口包括startup的capture199、replay69646、算法kernel34652160及分方向copy/memset调用与字节上限全部冻结；不得将数值7/14误当全窗口总量。

GPU预计5–10分钟，硬20分钟、第17分钟清理；结果审计0.5–1h。本轮0 GPU/模型/HTTP，原服务STOPPED/镜像参数cache身份未变。原失败、18处G1差异、C1/其他附件缺口保留；C0/K2-T01/K1-T01/K2-T05/H1继续关闭、追加预算0。真实W6逐bit/Graph/状态/收益未验证；资格与发布仍PENDING，p95=null、optimization_qualification=false。详见[冻结回执、预算与CPU证据](../../ninfer-v4-h3-w6-stage-a-20261024.md)。以下旧选型/预算/准备状态均为历史，不构成可重用额度；GPU执行须有后续明确授权。

## 历史选型：H1收尾，H3-T01 Stage A先验证现有W6

H1-T01按用户要求`CLOSED_NO_FURTHER_MEASUREMENT`，追加预算0；原2个native逐bitPASS、4个重复保护截断失败、全部成本和资格缺口原样保留。C0/K2-T01/K1-T01/K2-T05继续关闭。

下一项仅选择`H3-T01 / A_EXISTING_W6_PILOT_ONLY`，profile `MTP_EXISTING_C1_W6_K5_VS_W4_K3_V1`：复用最大5草稿、现有六列MTP/Target/GQA/Graph，不开发W8、不叠加Lookup，不改默认分派/Target sampling/Pi32768。基点raw树a5ba33de12d75ab1e16a153020e4068094ee1757；拟议新分支尚未创建。本轮仅jssh只读核对及文档，0构建/测试/GPU/模型/HTTP。原服务STOPPED，18处G1差异、C1及全部历史失败/缺口保留。

拟议CPU≤16合同，新增T6数值8场景/10 direct Op/8 capture/16 replay，native2场景/4请求/≤16 decode调用，6 Chat＋2warmup/10wire，总≤12模型提交。数值capture/replay不包含模型启动，完整kernel/copy/Graph资源须由新驱动枚举冻结后才可执行，当前未授权GPU。工程准备8–16小时，GPU预计5–10分钟/硬20分钟/第17分钟清理，分析0.5–1小时；收益未知，10%仅为新profile正例净改善信号门槛。W8原80项总断言中的H3断言、31个发布scope及完整资格/发布继续PENDING，W6不抵扣W8资格。

[完整范围、依据与预算](../../ninfer-v4-post-h1-selection-20261024.md)。以下旧选型、准备、结果和预算均为历史，不构成当前任务或可重用额度。`p95=null`、`optimization_qualification=false`。

## 历史结果：H1-T01最小窗口完成，状态通过、无采用信号

已执行唯一冻结r3（716ccfc4e830…），250.301秒清理完成。2个native场景/4请求/6次decode-or-verify逐bitPASS；6Chat＋2warmup、10wire、总12提交全部记账。实际36capture/339replay/303561算法kernel，全部资源在冻结上限内；账本COMPLETE，无unknown或未结束请求，controller/guardian退出，GPU idle、lease free，原服务STOPPED/PID0且镜像/argv/cache身份不变。

正式Chat候选47/128轮Lookup命中（36.72%），命中draft接受122/141。复制/工具/控制的完整decode每报告token耗时分别增加6.98%/4.28%/8.11%，未获采用信号。4个正例失败的Engine终态均repetition_cycle（wire映射length），是重复fixture撞上既有保护；保留原FAIL与raw，派生解释单列，不算模型答错或改为PASS。控制样本也命中7/22，no-hit≤1%资格未建立。

本轮profile结束、追加预算0，保持MTP与默认关闭Lookup，不重跑或放宽断言；不同seed/单对样本与保护截断限制因果结论。原采样/context/Pi32768、18处G1差异、C1及旧证据缺口保留。p95=null、optimization_qualification=false。[完整命中、状态、净收益与失败原因](../../ninfer-v4-h1-hardware-20261024.md)。以下准备态、空账本与旧预算均为历史，不构成新执行授权。

## 历史准备：H1-T01 CPU补丁、BO与实机驱动

已通过jssh 29在隔离分支`codex/h1-lookup-packet-c1-w4-20261024`完成请求内整包Lookup。CPU16/16一次通过，原路径诊断、Lookup诊断及默认版三个BO构建PASS；本代理集成检查无已知阻断。原始BO头文件失败保留。真实27B消费TU的宏与对象引用已核对，默认Lookup及诊断开关关闭。

集成树`9e7c0a1f19721d0ba63db362da6d10b5cda7c8e0`，冻结SHA`716ccfc4e8308f7db34497d8edc6d6705aa1a843370b4efef1f073df42d22eb0`；runtime不存在，账本PRISTINE，GPU/模型/HTTP均0。固定C1/W4/K≤3、4gram/ring8192/16384槽；整包替换、许可后append，不改Target采样、原MTP对齐/下一轮、Graph或缓存格式。

下一步仅最小试验：2个新native状态场景/最多4次native请求、≤16次decode/verify；6个新Chat＋2warmup，10wire，共≤12模型工作提交。预计5–10分钟，硬20分钟/第17分钟清理，之后离线报告30–60分钟；当前未执行GPU。完整候选资格与发布仍独立，运行时数值/Graph/净收益均未通过。原服务STOPPED，采样/context/Pi32768、18处G1差异、C1及全部旧缺口保留；C0/K2-T01/K1-T01/K2-T05不再补测。[实现、冻结与完整预算](../../ninfer-v4-h1-t01-20261024.md)。以下旧选型与预算均为历史，不能重启旧窗口。

## 历史选型：K2-T05收尾后选择H1-T01

K2-T05状态`CLOSED_NO_FURTHER_MEASUREMENT`，追加预算0，不再补测Op/T512/native/Chat；保留逐bit及4/4 Chat PASS、完整Prefill0.314%未达1%门槛和全部原始失败/成本。C0、K2-T01、K1-T01继续关闭。

唯一新选项为`H1-T01`，状态`NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED`。从raw树a5ba33de12d75ab1e16a153020e4068094ee1757开始，不携带未采用T1024分派。固定C1/W4/K3、4gram、ring8192；只在extent3且有完整后缀时整包选Lookup，否则原MTP。索引归RequestControl，正式committed后更新；原Target采样、Graph、MTP alignment/next proposal、许可和缓存格式不变，不声称命中就跳过MTP计算。

当前只读jssh源码/证据核对和文档，0新构建/测试/GPU/模型/HTTP，分支未创建。未来拟议CPU≤16合同；GPU最多2个新native状态场景/4请求/16次decode-or-verify，加6 Chat＋2warmup/10wire，共≤12模型工作提交，预计5–10分钟，硬20/清理17；资源与驱动必须另行冻结。本提案不授权执行，不复用旧已消耗预算。工程准备16–24小时；真实Lookup收益未知，5%仅为正例decode/token信号门槛。原服务STOPPED、采样/context/Pi32768、18处G1差异与C1缺口保持，p95=null、optimization_qualification=false。[完整选型、范围与预算](../../ninfer-v4-post-k2-t05-selection-20261024.md)。本轮范围以此选择及注册表为准，以下旧状态/预算均按历史解释。

## 历史结果：Chat接续完成，4/4 PASS，未达到完整Prefill采用门槛

状态`CHAT_COMPLETED_4_PASS_NATIVE_SIGNAL_BELOW_THRESHOLD_KEEP_RAW`。2026-10-24经用户明确授权的新窗口已消费剩余4 Chat＋1 warmup／6 wire，新增native0，累计native13；旧raw warmup未重发。新冻结SHA`b9512345eb6d511d6f242aff465404907ec02dbe8661ec15d6012f0c26ade317`，接续账本COMPLETE、无unknown；原失败账本不改，旧GPU envelope不退款。请求ID已按响应头权威ID＋实例/request/Engine元组关联，7项定向CPU检查PASS，原CPU/BO证据复用。

文本和工具调用4/4 PASS且实际增量交付。TTFT文本2.296332→2.276107秒（观察改善0.881%），工具2.206091→2.198108秒（0.362%）；各仅一对、不证明稳定提速。旧12次native及完整状态/logits逐bitPASS复用并补回原始元数据，配对中位改善0.314%低于冻结1%门槛。两次warmup的OK.与精确OK断言不符，失败原样保留；夹具标点歧义不掩盖，也不放宽。

126.025秒完成候选清理，controller/guardian退出，GPU idle、lease free；原服务STOPPED，镜像/argv/cache身份及采样/context/Pi medium/32768不变。旧失败、18处G1差异、C1和Baseline缺口保留，首轮失败最终GPU总数仍null。新旧相关wire/元数据/原始logits已本地镜像，大状态完整包在远端持久保留。`p95=null`、`optimization_qualification=false`，本窗口余额0、不自动追加或恢复旧窗口。[完整报告与证据](../../ninfer-v4-k2-t05-chat-remaining-20261024.md)。以下暂停、失败和空账本仅为历史，不构成新授权。

## 历史首轮：完整Prefill因logits诊断构建缺陷停止，CPU修复完成

状态`FULL_PREFILL_CHAT_STOPPED_RAW_LOGITS_BUILD_SCOPE_CPU_REPAIRED`。唯一r2窗口已执行并关闭；raw首个warmup在提交后的导出阶段报`actual target logits capture missing`。72个原始状态段／306,659,921字节保留，原target logits与导出元数据缺失；候选、五组有效计时和Chat均未运行。不能声明完整Prefill、逐bit或TTFT通过，不能外推原算子段收益。

根因已由实际编译命令确认：tests目录source property未作用于ninfer_engine目录，模型TU缺少诊断宏。独立overlay增加`TARGET_DIRECTORY ninfer_engine`后，raw/candidate BO增量构建及实际调用方对象引用检查PASS，修复阶段0 GPU/模型/HTTP。原r2源码、四个冻结二进制、原始失败和账本保持不变；新二进制尚未冻结或实跑。

原账本保留RUNNING／raw预留6、完成0，不代表仍有进程；原始迭代日志1次RESERVED，不算6次实际执行。CUDA最终累计值未落盘，MODEL_READY检查点不能当总用量。约61.944秒完成精确候选清理，GPU idle、lease free，原服务STOPPED且镜像/参数/cache身份不变。实际Chat/warmup/wire均0，不重发失败warmup、不跳过数值门禁，不追加旧预算或重启single-use窗口。

剩余完整对照需新版本工具/账本：12 native（含两侧正确性warmup和五次测量）、4 Chat＋2 HTTP warmup、8 wire，原失败成本另列；这些不是本轮余额或自动新增授权。预计准备0.5–1小时、实机8–15分钟，20分钟硬限/第17分钟清理。旧Baseline/已通过任务/T512不重跑；18处G1差异、C1缺口、全部失败与Pi medium/32768及采样/context保留。`p95=null`、`optimization_qualification=false`。[实机失败、CPU修复与证据边界](../../ninfer-v4-k2-t05-full-prefill-hardware-20261023.md)。以下“GPU未运行/空账本”及准备预算均为历史，不能据此恢复旧窗口。

## 历史准备状态：T1024完整Prefill／Chat驱动与r2空账本当时已冻结

状态`CPU_BUILD_REVIEWED_FULL_PREFILL_CHAT_PREPARED_GPU_NOT_RUN`；当前候选树`abc974d38d861c4fa72692345aadfc8565624fa3`、raw树`a5ba33de12d75ab1e16a153020e4068094ee1757`，唯一入口`prepared-window-r2`，freeze SHA `4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d`。raw/candidate四个诊断可执行文件BO构建通过，29项新CPU检查及主代理集成评审完成。r1保留并退役，预算不叠加；原服务STOPPED，0 GPU/模型/HTTP，runtime不存在、ledger全0。

预算固定12 native Prefill、4 Chat＋2 HTTP warmup、8 wire；capture≤256、replay≤73728、算法kernel≤35651584，copy/memset调用与字节已分方向冻结。硬限20分钟、第17分钟关闭admission并清理候选；预计实机8–15分钟，当前尚未执行。tool_choice仅用已支持auto，精确工具/JSON断言不放宽；Pi medium/32768、现网采样/镜像/cache、18处G1差异、C1缺口及全部失败保留。`p95=null`、`optimization_qualification=false`。[完整预算、回执与验证边界](../../ninfer-v4-k2-t05-full-prefill-prep-20261023.md)。以下未冻结驱动/预算及旧空账本表述仅为历史，不构成新授权或余额。

## 历史接入状态：T1024候选CPU交付完成

状态`T1024_PREFILL_INTEGRATED_CPU_BUILD_REVIEWED_GPU_NOT_RUN`，候选树`9818eafa5d2660c2ea9682cc7653e6603f21ebb5`，分支`codex/k2-t05-prefill-integration-20261023`。BO构建、新增16项CPU路由/边界合同及主代理集成评审完成；精确Q/K/V地址断言已补齐，两次构建依赖失败保留。本轮0 GPU/模型/HTTP；T512不补测，其余shape及Verify/Decision/segmented保持raw，原kernel/FP64参考/state/工作区布局不改。

原服务STOPPED，采样/context/Pi medium/32768、18处G1差异、C1缺口及全部旧失败保留；不重跑旧任务。完整Prefill/Chat尚未运行，拟议12 native prefill＋4 Chat＋2 warmup＝18模型工作单位、8 wire；驱动与细粒度GPU预算尚未冻结。准备3–5工程小时，实机预计8–15分钟、建议20分钟硬限/第17分钟清理；不构成GPU或发布授权。`p95=null`、`optimization_qualification=false`。[接入报告与冻结回执](../../ninfer-v4-k2-t05-prefill-integration-20261023.md)。以下未授权产品接入、旧空账本/预算等表述按历史阶段解释，不是当前状态或余额。

## 历史实机状态：K2-T05算子段筛选完成，T1024有信号

状态`GPU_MIN_SCREEN_COMPLETED_T1024_SIGNAL_T512_TIMING_INCONCLUSIVE`。4个数值场景的完整BF16 Q/K/V及conv state逐bit、原FP64参考/guard全部PASS，T512/T1024 raw/split共4张实际Graph的函数/参数/几何/copy/依赖见证及后续逐bit全部PASS。T1024卷积＋原state更新＋raw三次提取整段配对中位下降36.4834%，5/5批更快，达到`SEGMENT_SIGNAL_NOT_K4`；T512观测下降38.4411%且5/5更快，但3批host提交占比超过冻结25%门槛，收益为INCONCLUSIVE，不放宽门槛或追加补测。

实际严格为4场景/20 direct Op/4 capture/184 replay（8 correctness＋16 warmup＋160 timing）/384算法kernel，0模型/HTTP；辅助传输均在原冻结上限内。24条reservation全部完成、无unknown。控制器6.767秒结束，候选在6.701秒清理；原服务STOPPED、GPU idle、lease free。本single-use窗口已消耗、追加预算0，禁止据历史空账本重新启动。

默认分派、采样/context/Pi medium/32768、18处G1差异和C1缺口不变，旧失败与CPU/BO原始证据保留、不重跑。仅T1024获得算子段信号，完整prefill/Chat及产品接入未授权，`p95=null`、`optimization_qualification=false`，任务资格模板仍PENDING。详见[实机报告](../../ninfer-v4-k2-t05-hardware-20261023.md)，后续边界见[任务合同](../plans/tasks/K2-T05.md)。下文CPU“GPU未运行”及旧拟议额度均为历史。


## 历史CPU准备：K2-T05构建、合同与评审完成，当时GPU未运行

状态`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。隔离分支`codex/k2-prefill-split-20261023`候选树`3ea537c00c759ef2a4577b525ae691f694ae102e`已完成BO构建、16项CPU合同（8 C++ Graph metadata＋8 Python编排）及集成评审；冻结SHA`7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc`。首轮CUDA13.2 Graph依赖API签名构建失败保留；两处改为4参数后增量构建PASS。已修复默认流reset到非阻塞Graph的同步及native非零退出的控制器失败处理。逐bit、实际Graph及收益均`NOT_RUN`，本轮0 GPU/模型/HTTP。[实施报告及冻结详情](../../ninfer-v4-k2-t05-implementation-20261023.md)。

未来最小预算仍为4数值、20 direct Op、4 capture、184 replay、384算法kernel、0模型/HTTP；辅助传输现已冻结：H2D 508次/4447860736字节、D2D 128次/7929856字节、D2H 768次/5386141696字节，raw段copy另限direct12/capture6/replay276，不能与辅助传输混算。预计2–5分钟，硬限10分钟、第7分钟清理。当前账本PRISTINE且所有计数0、无runtime；GPU执行需单独授权。旧选型中“辅助传输待枚举/null”仅为历史，不是当前缺口或无限额度。

K1-T01/C0/K2-T01继续关闭、追加预算0，不启动K1-T02。原数学、FP64阈值、state和默认分派保留，采样/context/Pi medium/32768不变，原服务STOPPED；18处G1差异、C1缺口及全部失败保留。20任务/4门禁/80断言、31 scope为可选库，任务资格仍PENDING，`p95=null`、`optimization_qualification=false`。下文旧成绩/预算保留，不据此重跑旧任务或授予产品资格。

## 历史选型范围：K1收尾，下一项仅选定K2-T05

K1-T01已由用户收尾，追加预算0；保留`GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW`及全部失败/缺口，不启动K1-T02产品接入。C0、K2-T01继续关闭，不重跑已通过任务。

唯一下项为[K2-T05普通Prefill卷积直接写连续Q/K/V](../plans/tasks/K2-T05.md)，状态`NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED`；复用源树`41a913488b0138fe868a8321d2f6a86ce83e313f`。先做bench-only限定shape候选，不改默认分派。本次选型不授予CPU实施或GPU执行授权；范围、待冻结传输预算和8–16工程小时估计见[选型报告](../../ninfer-v4-post-k1-selection-20261023.md)。

当前注册表为20任务/4门禁/80断言、31个scope（15 candidate＋15 publication＋1 research）的可选实验库，并非本次全执行计划；当前只选K2-T05。原服务保持STOPPED，采样/context/Pi medium/32768、18处G1差异与C1附件缺口不变，`p95=null`、`optimization_qualification=false`。以下旧选型、预算与成绩按各历史阶段解释，不构成当前余额或新增授权。

## 历史状态：K1-T01 Graph通过，无段级净收益信号，保留raw

状态`GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW`。本轮Graph-only补测已完成并关闭；profile为`SM89_GDN_CORRECTION_C1_W4_L48_GRAPH_ONLY_R2`，源树`41a913488b0138fe868a8321d2f6a86ce83e313f`，冻结SHA`29c89db3f440cea8b8620e0728dd9220c7c3366782fbc408b283e5aedd9e0969`。raw函数地址由真实launch TU导出，实际Graph节点参数在断言前耐久落盘；8个CPU元数据场景与8个工具场景共16项定向验证PASS，独立集成评审无阻断。

复用旧8个数值场景及其SHA，不重跑。新执行6次capture、276次replay（12 correctness＋24 warmup＋240 timing）、13524次算法kernel；0 direct Op、0新增数值场景、0模型/HTTP。6图各49节点均`WITNESS_PASS`；Graph correctness、warmup与timing全48层raw/correction逐bit比较均PASS，layer0原FP64参考在Graph correctness通过。新账本`COMPLETE`且无unknown；不回写旧失败账本或补造旧节点参数。

48 Record＋1 Fold的5批配对中位改善：commit1为−1.0540%（0/5批更快），commit2为−0.0714%（0/5），commit4为＋0.1809%（3/5）。三组均未达到“改善≥10%且至少4/5批更快”，结论`NO_SEGMENT_SIGNAL`。计时含host投递gap，仅代表该算子段，不是完整Target Verify或模型整轮收益。保留raw，不进入K1-T02产品接入，不追加GPU测试。

窗口约10.70秒结束；原服务STOPPED、GPU idle、lease free。15分钟硬限和第12分钟清理上限未触及。默认分派、采样/context/Pi medium/32768、18处G1差异、C1附件缺口及全部历史失败保留。C0/K2保持关闭；所有任务资格status仍PENDING，`optimization_qualification=false`、`p95=null`。详见[本轮Graph补测报告](../../ninfer-v4-k1-graph-r2-20261023.md)。下文首筛失败、CPU准备及旧预算均为历史，不能据其重启窗口、追加测试或授予发布资格。

## 历史首筛：K1-T01数值通过、Graph见证失败、未计时

状态`PARTIAL_NUMERIC_PASS_GRAPH_WITNESS_FAILED_NO_TIMING`。本轮唯一执行冻结SHA`4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105`、源树`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`的窗口；profile仍为`SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1`。8个数值场景全部PASS，784次direct Op及对应784次算法kernel完成。全48层raw/correction的FP32 state、conv和BF16 readout逐bit一致；layer0既有独立FP64参考及guard/suffix检查通过。该结论仅覆盖本次C1/W4直接执行场景，不授予完整候选或生产资格。

首个raw commit1 capture在函数/几何见证检查报`unexpected Fold function/geometry`：1次capture已预留但未完成，replay为0，Graph正确性、稳定性及Record＋Fold净收益均无结果。实际node参数未打印，Record函数地址不匹配也可进入同一错误分支；不能据此认定真实Fold几何错误或数值失败，更不能将未计时写成无收益。

原冻结上限8场景/784 direct Op/6 capture/276 replay（含warmup）/14308算法kernel未扩大，0模型/HTTP。窗口约7秒后终止并清理候选；候选exited、原服务STOPPED、GPU idle、lease free。当前ledger保留失败现场的`RUNNING`，不能回写`COMPLETE`；冻结回执、初始空账本、CPU证据及全部失败不改。窗口已经结束，禁止重启或重跑已通过8个数值场景。

下一步仅修复Graph见证及诊断，再另冻未完成Graph的工具和预算；不自动发GPU请求。默认分派、采样/context/Pi medium/32768、18处G1差异、C1附件缺口保持不变。K1-T01及K4资格仍PENDING，`optimization_qualification=false`；K1-T02运行时事务与整轮验证独立，C0/K2保持关闭。详见[本轮实机报告](../../ninfer-v4-k1-hardware-20261023.md)。以下CPU准备和更早预算均为历史，不能作为当前空账本或余额。

## 历史K1-T01 CPU准备：候选已冻结、当时GPU未运行

状态`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。用户已授权在29隔离分支完成K1-T01：C1/W4/L48 correction Record/Fold候选、驱动、BO构建、16个CPU合同（8 C++＋8 Python）与独立评审均完成。候选树`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`；冻结SHA`4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105`。无GPU/模型/HTTP请求。raw接口和默认分派保留；共享helper同表达式capture与内部链接改动不能静态证明GPU逐bit一致。

profile为`SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1`。实机驱动采用48层不同state/conv种子，将对全层raw/correction逐bit比较；独立FP64仅layer0沿用旧oracle与阈值，当前均未实跑。双池独立，候选不双写raw；10,260,480字节correction是新增payload，不是显存节约。首筛仅48 Record＋1 Fold，不是完整Target Verify/模型整轮。

未来冻结上限为8数值场景、784 direct Op、6 capture、276 replay（12 correctness＋24 warmup＋240 timing），每图49算法节点、总执行14308；0模型/HTTP。传输独立上限：H2D847次/3174503944字节、D2D128次/19704905728字节、D2H896次/30979424768字节，含guard/reset/export，无helper compute或memset。预计3–8分钟，第12分钟清理、15分钟硬限。工具和空账本已冻结，GPU执行仍须单独授权，不能自动接续。

段级五批中位改善≥10%且≥4/5批更快才有`SEGMENT_SIGNAL_NOT_K4`；无信号/数值失败停止保留raw。K1-T02许可/epoch/取消、真实Target sampling、整轮及发布继续独立。C0、K2保持关闭、追加预算0。原服务停止、采样/context/Pi medium/32768、18处G1差异、C1附件缺口及全部历史失败不变。详见[本轮实施报告](../../ninfer-v4-k1-implementation-20261023.md)。以下旧阶段记录及通用32wire/84native模板均为历史，不能相加为本窗口额度。


## 历史K2实机结果：无信号，保留512并停止本轮

状态：`GPU_SCREEN_COMPLETED_NO_SIGNAL_KEEP_512`。[本轮实机报告](../../ninfer-v4-k2-hardware-20261023.md)。冻结SHA `37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e`，源树`13223b2b2989d0cf580715b197b276d74acffc86`。8个数值场景、22次direct Op全部PASS，6次capture及12次正确性replay PASS；含warmup共1992次replay，0模型提交/准入、0HTTP。

128/256相对512的5批配对中位改善：T1分别+1.2026%（3/5批更快）、+5.7554%（3/5）；T4分别−3.4272%（2/5）、+4.9825%（3/5）。四组均`NO_SIGNAL`，未满足预定“改善≥10%且至少4/5批更快”。计时对象为host-submitted单节点Graph replay，不是纯kernel时间，不能外推整轮/Chat收益或彻底否定kernel优化潜力。

完整控制窗口耗时1.568326749秒，候选、guardian和controller均已退出，GPU空，原服务STOPPED。停止本轮CTA实验，保留默认512，产品dispatch不改；不进入“有赢家后”的整轮验证，额外预算0，不自动重试。原冻结窗口已single-use消耗，runtime存在、账本COMPLETED；禁止重启。以下CPU准备、选型和拟议预算仅为历史，不构成待执行或余额。C0仍关闭；18处G1差异、C1附件缺口与全部历史失败保留，采样/context/Pi medium/32768不变。19任务/4门禁/76断言与PENDING资格模板不改，p95=null、optimization_qualification=false。

## 历史CPU准备（前次选型与C0段落保留）

状态：`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。用户已授权本轮K2-T01 CPU实施，在`codex/k2-gated-rmsnorm-20261023`隔离分支、工程基点`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`已完成补丁、BO增量构建和集成评审；不是新增GPU执行授权。本段取代下文历史“仅选定未实施”的当前含义，旧选型与失败记录原样保留。BO无GPU增量构建通过；新增CPU合同19＋4项及CLI检查11项通过，独立集成评审问题已修复并闭合。GPU数值/性能/真实清理尚未运行，不能替代候选或生产资格。

本轮采用独立`ninfer_k2_gated_rmsnorm_probe`，不扩展旧plain bench。复用原warp模板的128/256/512线程配置，使用真实gate，并共享既有double oracle；产品`src`及默认dispatch完全不改。编译旧test以检查集成，不执行已通过旧suite，不重跑Baseline或旧任务。

未来GPU首轮拟议预算为8 case、22 direct Op、6 capture、1992 replay（12 correctness＋60 warmup＋1920 timing）；fallback为T1 unaligned和T5 aligned。0模型提交/准入、0HTTP；预计2–5分钟，600秒硬截止，第420秒清理。工具和全0账本已冻结，执行仍待单独授权，本轮未执行。C0保持`CLOSED_NO_FURTHER_MEASUREMENT`、追加预算0；18处G1差异、C1附件缺口和全部历史失败保持原样，原GPU服务停止、采样/context/Pi medium/32768不变。

[本轮实施报告](../../ninfer-v4-k2-implementation-20261023.md)为最终事实入口；冻结SHA为`37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e`，补丁树为`13223b2b2989d0cf580715b197b276d74acffc86`。当前无runtime；不将CPU通过记成候选性能/生产资格。计时是含主机投递间隔的单节点Graph replay信号，不是纯kernel latency。以下早期选型、预算与执行记录均按其历史阶段解释。

## 历史选型决定：C0关闭、K2-T01当时仅选定未实施

C0按用户决定收尾，状态`CLOSED_NO_FURTHER_MEASUREMENT`，追加补测预算0，不再重启旧窗口或自动接续。已通过的CPU及实际L2恢复证据保留；TTFT收益仍为INCONCLUSIVE，不能从工程继承推出生产采纳。18处G1差异、C1附件缺口及全部旧失败不变。原GPU服务保持停止，采样/context及Pi medium/32768不变。

下一项选择`K2-T01`：SM89、BF16 aligned D128、48 heads，真实T1/T4下的已有gated RMSNorm CTA映射。当前512线程对应T1仅3个CTA；128/256线程候选对应12/6个CTA，是可证伪的执行几何假设，不是已测最大热点或整机收益保证。当前MTP K3的verify为K+1=4，不扩T6/W8/W16。工程基点为C0树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`，仅继承代码；P4原参考树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`保留，两者均无新增性能/生产资格。

首补丁只增加bench/test候选，产品默认dispatch保持不变。复用同一warp数学、SiLU、乘法和BF16舍入，不新增fusion、workspace、autotune或模型/权重格式；实测胜者才进入SM89隔离候选的静态限定shape路由。现有bench的candidate-b128/b256未传真实gate，`--control`只是payload带宽对照，都不能冒充本次gated/原512算法对照。

本轮只读ssh核对和文档选型，未实施补丁、构建、测试或GPU/HTTP/模型请求；实施及GPU验证均待对应授权。当前选择和范围不把完整round验证当开工前置。

[本轮选择报告](../../ninfer-v4-k2-selection-20261023.md)；具体预算见[K2合同](../plans/tasks/K2-T01.md)。以下C0准备/执行段落为历史，不构成余额或待办。

本页只整理已观察结果，当前文档修订不重跑产品检查。原报告和回执为真源；旧运行时状态按对应时点解释，不在一个页面累加互相冲突的“最新”。

## P4研究基点

[P4最终Chat补测报告](../../ninfer-v4-p4-chat-recheck-20261023.md)与[机器汇总](../../../output/ninfer-v4-p4-chat-recheck-20261023-r2/final-summary.json)：树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`，HEAD仍O`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，不声称新提交或merge ancestry已完成。BO image `sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，CUDA13.2/SM89/Release。

数值8场景/36 direct Op、14 capture/28 replay及缓存场景5 PASS复用。两个Chat补测PASS：2模型请求/5wire/含warmup3提交，114.356786秒，native工具参数38 UTF8 bytes、代理9个参数delta；首参数早于同server done约228.824ms。这是最小功能证据，不是与B29的性能提升比较。两次P4窗口累计6模型提交，旧失败保留。

原GPU服务按用户要求停止，候选已清理、当次GPU空；原镜像/参数/cache身份未改，后续不自动恢复。P5导入已中断，未构建、未GPU/HTTP/model/grader，不作为研究基点。完整P2/P3/P4/P6/统计与生产资格未取得。18处G1严格字段差异、P2两次失败与C1末次telemetry HTTP附件缺口继续保留。

## 完整Baseline事实

[最终报告](../../../output/ninfer-baseline-29-20261020/FINAL-REPORT.md)：278逻辑项=250新采集+28复用；旧8题7PASS/1FAIL，Gson r3 FAIL8/10、JavaParser PASS4/4，完整8+2为8PASS/2FAIL。r2 Gson policy-aborted及部分评分单独记成本。44Pi中39HTTP200，1容量拒绝、4冻结非法arguments拒绝均不合格性能样本；另2Responses option拒绝不是协议成功。旧513行、3损坏raw、原gap不改。

最终备份5624远端文件/534本地证据；66条编程wire request/raw完整。63个有历史SHA附件中10个同字节重建、53个无法恢复；另8个缺失无独立SHA、22个derived-only。CLI/patch/identity/summary/grader附件缺口不由SSE替代。p95=null、optimization_qualification=false；真实token IDs/逐token ITL/可靠reasoning token拆分/round wall/allocator高水位不可观察，保留null+原因。

## 性能与失败归因边界

| 描述性集合 | 请求elapsed合计 | prefill合计 | decode合计 / 占比 |
|---|---:|---:|---:|
| Core sampling158行 | 5479.518s | 4700.413s | 759.300s / 13.86% |
| Long O8192 12行 | 975.280s | 444.441s | 528.332s / 54.17% |
| Pi HTTP200 39行 | 1694.473s | 497.900s | 1190.622s / 70.27% |

含复用观察、span可能重叠，不是实际总wall/流量权重/p95或kernel归因。P253952冷TTFT约153.030s、warm .238s；说明冷prefill和warm decode要分开优化，不能仅据此选GDN fold。

97fc7be6：P31421、请求O32768、实际O32767，335.820s，reasoning121620chars，content/tool0。SSE length与server context_capacity并存、KV增长curtailment+1；直接证据是KV增长截停，不是已证OOM或正常用满预算。长内部自检不等于已证token循环。后续只能用新边界夹具补足remaining/frontier/main-aux页额/ceiling/free pages观测，不重发旧请求、不缩减Pi预算。

Gson r2旧白名单中止与r3完整FAIL8/10分开；r3已可恢复工具反馈并正常stop，不能继续归因旧policy。两个失败selector及原hidden日志缺失，无法认定float/double或具体回归。RE003题面未要求trim而hidden首断言要求，原FAIL保留；旧夹具不具备事务能力归因资格，后续断言未执行不能报PASS。

历史深度分析见[冻结V3分析](../baseline-v3/research/04-completed-baseline-assessment.md)。保留原成绩，未来质量主张使用新冻结holdout与一致题面/oracle，不重跑旧题、grader或篡改分母。

## K0当前增量

[K0报告](../../ninfer-v4-k0-20261023.md)已通过直连ssh29确认P4树/1235文件/serve二进制及原服务停止。原构建/实机证据复用，新增CPU合成探针定位无SHA指令CPU的缓存内容指纹成本；当前选择C0-T01。未修改产品、未发GPU/模型/HTTP/grader请求，GPU Op/逐轮时间线与真实Chat收益仍缺，不能将CPU参考2.12倍写成推理提速。

## C0 CPU实际进度

[C0报告](../../ninfer-v4-c0-20261023.md)：统一SHA非SHA-NI路径补丁及BO闭合、构建、双轴评审完成，31/58/7定向CPU通过；候选树4d31af40。未改P4其余1229个既存文件，原P4全部1235 blob保留；18G1差异与C1缺口不变。CPU收益不能代替Chat服务收益；本轮0GPU/模型/HTTP请求，原服务仍停止。

## C0 r1历史实机窗口

[执行结果](../../ninfer-v4-c0-hardware-20261023.md)：首Chat的named tool_choice被准入前400拒绝，C0未启动；实际2wire/1内置warmup/0Chat入模。原outcome/stage缺口、控制器二次错误均保留并外置核对。约302秒安全清理，原服务仍停止，CPU结果不变，Chat收益INCONCLUSIVE。不能将历史准备的0请求或自动分析NOT_EXECUTED当作完全未执行。

## C0 r2历史实机结果

[补测](../../ninfer-v4-c0-hardware-20261023-r2.md)完成：15定向CPU/双轴评审和8Chat功能/自动接续/安全收尾PASS。实际12wire、10提交含2warmup，345.047秒，原服务停止/GPU空。有效Chat性能配对0：两端目标续轮均preflight_rejected且无L2恢复，随机历史/P/O不同。启动108.233→56.926秒、相同A导出postcopy发布15.032→7.267秒只是各n=1描述性观察，不能归因净收益。137远端文件完整核验，本轮无新增原始运行附件缺口；r1和旧G1/C1缺口保留。


## 历史L2前缀CPU定位

[报告](../../ninfer-v4-c0-l2-preflight-20261023.md)：auto→none使翻译后的有效工具集合为空并移除# Tools，历史4对真实输入的原始token/type/position LCP为1。保留auto后8个正反CPU用例通过，LCP55483/55562覆盖安全checkpoint55481/55560；这解释metadata preflight拒绝，不将未观测的image字段断言为已核实。未发现需要修改产品的证据。

固定branch首版正例LCP55291低于checkpoint55293，保留失败；以明确synthetic assistant输入隔开用户回合后2个正反用例通过，正例LCP55295覆盖55293。14个新/受影响PythonCPU回归通过，最终双轴评审已闭合，无剩余阻断发现。本轮产品0变更、GPU/HTTP/模型0，未实测image import或TTFT，V04未证明。旧失败、18G1、C1及r1/r2结果不回写。

历史准备阶段冻结新4Chat/6提交含2warmup/10wire的固定输入TTFT pilot（现已由下文r3执行并关闭），预计6–10分钟，720/900秒清理/硬限，原服务保持停止。它以DONE+10秒±150ms、保留L2的条件GPU lane erase及真实深恢复证据控制随机历史/排队/发布时间混杂；最多n=1 PILOT_TTFT_SIGNAL_NOT_K4，不代替完整Chat/质量/p95/K4/发布。


## C0 r3最小TTFT pilot已完成，收益归因不成立

[实跑报告](../../ninfer-v4-c0-ttft-pilot-20261023.md)与[机器汇总](../../../output/ninfer-v4-c0-ttft-pilot-20261023/final-summary.json)记录P4→C0已完成：4个新Chat全部PASS、10wire、6次模型提交含2warmup，246.142777927秒安全收尾；没有本轮失败。21份冻结工具SHA及request/raw哈希核验通过。原服务STOPPED、候选退出、GPU空，未知请求/未完成导出/新增附件缺口均0。冻结目录已single-use消耗，禁止重启或追加样本；上文准备预算及全0状态仅为历史，不是余额或当前待办。

两端branch均真实source=l2，恢复55293 tokens，实际P=55374、computed_prefill=81；P4/C0恢复字节1333980256/1336349835。客户端首个非空语义delta TTFT为0.943552271/0.959943143秒，C0本次观察约慢1.737%，n=1不能形成稳定回退或收益结论。冻结分析保持`INCONCLUSIVE_TTFT_CONTROL_NOT_SATISFIED`：P4同样深L2、两端queue为0.618971645/0.641931568秒均超过50ms、seed export为1333034412/1335401900字节不等。不放宽对照断言，不把L2恢复成功等同C0独有收益。

post-copy publication为14.372465950/7.060492013秒，描述性降低约50.87%；它不是严格配对，也不等同TTFT获益。V04仍未证实，p95=null、optimization_qualification=false、K4=false；无正式性能或发布资格。采样及Pi medium/32768不变，18处G1差异、C1附件缺口及全部历史失败保留。不再把本次scope列为待开工或自动补测任务。

进一步源/日志复核修正了实验假设：P4命中`stable_prefix`，C0命中`routed_session`；执行器先发布boundary alias再发布session，最终publication_finished_ns表示二者全部完成。因此P4可在最终publication完成前已经恢复深前缀，原“最终发布未完即无任何可恢复深前缀”的假设错误。queue指标是admitted−submitted，恢复发生在admit之前，包含恢复/准入开销，不能将其超50ms归咎于外部排队竞争。冻结门槛仍原样判不满足，不改gate或补发。独立原始证据只读复核无阻断：10组request/raw SHA与长度相符、4个SSE各1个DONE且finish为tool_calls、21冻结SHA一致；复核未运行测试。
