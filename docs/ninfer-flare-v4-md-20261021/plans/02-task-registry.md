# 唯一执行注册表：纯Chat推理性能

## 当前准备：原P4→修复P4的HTTP对照已冻结，未运行GPU

`P4_EXPORT_PUBLICATION_PIPELINE_HTTP_V1=CPU_ONLY_PREPARED_FROZEN_NOT_EXECUTED`。经jssh29复用现有controller/guardian/HTTP驱动，14项新工具CPU合同通过，真实旧日志离线核对保留原job7缺口，初审的四Chat发布终态覆盖缺口已修复，独立复审无阻塞。复用两份serve、原4个HTTP输入及P4 token/position预检，不重建、不重跑旧任务。

冻结根 `/home/hhtele/ninfer-v4-export-pipeline-prep-20261025/prepared-window-r1`；freeze SHA `0dca60d4e89be0205011b30bb8824154eca74aed209620b36337419c7edbeb4a`。账本PRISTINE/全0，runtime不存在。严格原P4→修复P4，0native、8Chat＋2内置warmup、14wire、最多10模型提交；硬1200秒/1020秒清理。实机预计6–10分钟，证据核算另20–40分钟，当前不自动执行。

最后Chat后不预等publication而发一次身份绑定SIGTERM，要求≤30秒自然exit0及四Chat声明job终态；信号发送区间区分LIVE_DRAIN、IDLE_CLOSE与不确定。缺失/重复/错配或发布失败明确不合格，缺真实source-release重叠仅记机制证据不足。可见job不必连续，不将host-only发布冒充全部可观测。

本轮GPU/模型/推理HTTP均0，原服务STOPPED身份不变，默认分派、Target采样、Pi medium/32768及全部历史失败/18G1/C1/Baseline缺口保留。真实关闭排空和性能仍未测，优化/生产资格false。后续需新的明确实机授权，不能重启旧已消费窗口。

[冻结回执、空账本、CPU/评审与实机预算](../../ninfer-v4-export-pipeline-prep-20261025.md)。以下历次“当前/准备/结果”均为原样保留的历史，不覆盖本节或授予执行额度。

## 当前修复：导出与 CPU 发布解耦，CPU 与构建完成

`P14_EXPORT_PUBLICATION_PIPELINE=CPU_VERIFIED_BUILDABLE_HARDWARE_NOT_RUN`。2026-10-25经jssh29在隔离分支 `codex/p14-export-publication-20261025` 修复已观察的跨job串行阻塞：独立导出线程、单槽交接、单FIFO发布线程。lane只在真实导出结束/排空后释放，CAS/发布顺序和关闭排空合同保留；不把复制完成当发布完成，也不把三份pipeline镜像当全局内存上界。

最终树 `7477294d629edffddef713d22c2d7589493d4271`，相对P14诊断P4基点 `d002a2183d54e1562cd1f53c50cf47155b1cb38f` 仅7文件变化。BO产品构建和10项CPU合同通过，真实coalescing补证后独立复审无阻塞；P14 trace为OFF。GPU/模型/推理HTTP均0，实际TTFT收益尚未测，性能与生产资格仍false。原服务STOPPED且镜像/参数/cache身份不变，默认分派、Target采样、Pi medium/32768不变；旧失败、18G1、C1及Baseline缺口全保留。

下一窗口仅建议原P4对修复P4：0native、8新Chat＋2内置warmup、14wire、10模型，硬20分钟/第17分钟清理；预计实机6–10分钟。现有controller需窄适配两端P4、最后job终态和≤30s自然SIGTERM，再冻结新空账本，准备估1.5–3工程小时。当前未冻结、未授权执行GPU，不重启旧已消费入口或关闭实验。

[修复、验证、限制与最小实机预算](../../ninfer-v4-export-pipeline-20261025.md)。下方历次“当前/准备/结果”为完整保留的历史快照，不覆盖本节或提供新执行额度。

## 最新实机结果：P1—P4整包对照已结束，发现准入等待回退

`P14_BO_P4_W4_WHOLE_PACKAGE_AND_ROUND_TRACE_V1=COMPLETED_WITH_PERFORMANCE_REGRESSIONS_AND_DISCLOSED_LIMITATIONS`。2026-10-25经jssh29执行冻结窗口，19分6.7秒结束；8native/80decode、8Chat＋2warmup、14wire、18模型提交全部记账，不再使用旧账本执行。第19分钟已清理，原服务保持停止，GPU无计算进程。

整包未形成一致提速：Java native每token成本增加2.12%；中文减少40.19%来自更多token/轮，单轮仍慢2.03%，跨版本生成内容不同。Chat短冷/短热/长冷TTFT增加313.20%/737.31%/56.80%，L2长热减少6.29%。两端均真实恢复16991tokens。四项trace轨迹与Graph见证通过，观测开销0.058%–0.359%；P4 Target主体占GPU阶段约80.1%，Fold约1.5%。

新回退已由源码与job时间关联：同一publication worker串行导出和CPU发布，前一个发布阻挡下一导出，C1准入再等待lane export。下一改造应先处理这条已观察链路，保留安全barrier和发布合同；当前仅报告，不自动开工、加请求或重开关闭实验。

BO有2次cache publication失败，旧schema缺逐job原因；P4最后job7缺发布终态。HTTP两候选按冻结stop -t2退出137/OOMfalse，不声明优雅排空通过。模型响应均完整，但性能/生产资格仍false，p95=null。217份导出文件SHA已验证；旧失败、18处G1差异、C1与Baseline缺口保留。

[完整结果、热点和证据](../../ninfer-v4-p14-performance-hardware-20261025.md)。以下“当前/准备/结果”均为保留的历史记录，不授予重跑额度。

## 当前准备：P1—P4整包对照与真实整轮归因，未运行GPU

`P14_BO_P4_W4_WHOLE_PACKAGE_AND_ROUND_TRACE_V1=CPU_ONLY_PREPARED`。两端为可复现BO/O tree6022c83与最终P4 tree35d3dd9，包含legacy rk4v4-e8→midrise rk4v4的整包变化，不能冒充原B29复现或单项提速。复用原服务二进制和既有natural/owner/HTTP驱动；两端诊断BO构建、CPU合同、12项新frontend实际预检与独立集成评审完成。六对token/positions相同，长共有前缀16992 token。所有首轮构建/预检失败保留。

新窗口`/home/hhtele/ninfer-v4-p14-performance-prep-20261025/prepared-window-r1`，freeze `0712e94eb92bd65a70897c0024e80e1384a3acd846aef4d73946a9ffa7aef6ab`，账本PRISTINE/全0，无runtime。仅准备授权，不自动执行。拟议8native/≤80decode、8Chat＋2内置warmup、14wire、总≤18模型提交；native≤72capture/152replay/1376256算法kernel，HTTP原二进制不逐kernel拦截。预计12–20分钟，硬30分钟/第27分钟清理。

plain测完整轮整包成本；trace只有真实7-event Graph见证、同端token/许可轨迹一致、完整8轮且观测开销≤5%才给阶段占比。实际TTFT/缓存命中/性能仍未测，p95=null，optimization_qualification=false。原服务STOPPED，默认分派、Target采样、Pi medium/32768及18G1/C1/全部旧失败缺口不变；不重跑旧Baseline，不重开任何关闭实验。

[完整准备、基点、预算和冻结证据](../../ninfer-v4-p14-performance-prep-20261025.md)。以下历次“当前/准备/结果”为保留的历史记录，不授予重跑额度。

## 当前结果：GQA Bc64已实测，性能首筛未通过并关闭

2026-10-25授权的一次固定候选实测已完成，`K2-GQA-T4-BC64=CLOSED_PERFORMANCE_GATE_FAILED`。6数值场景、12direct、6capture、240replay、504kernel全部记账，0模型/HTTP，37.319秒完成清理。数值、Graph query0重复检查和缓存guard通过；query1只验证direct。8K耗时增加14.516%，32K减少14.865%，128K增加0.156%；未满足长上下文采用门槛且8K回退超过2%。不采用、不追加调参或32K补测，不自动进入append/native/Chat。

原`FAIL_NEW_SPILL`回执保留，此次只按用户授权版本化资源准入，固定源码/二进制不变。原服务保持停止；默认分派、Target采样、Pi medium/32768、18处G1及全部历史失败/缺口不变。[实测报告与冻结/原始证据](../../ninfer-v4-gqa-t4-bc64-hardware-20261025.md)。以下历次“当前/准备/未运行”为历史记录，以本节结果为准，不授予新额度。

## 当前结果：T4 GQA Bc64在可行性检查结束，未运行GPU

`K2-GQA-T4-BC64`为`CLOSED_FEASIBILITY_NEW_SPILL`。隔离候选、BO构建、CPU合同和评审完成；ptxas原Bc32报告spill store/load各4B，Bc64为64B/72B，触发既定新增spill停止条件。它不是实测性能退化，也不关闭其它K2/H2/H6/H7/K3/W8/W16/utility候选。

候选树`b361766a8072943b2cde700ae12263efd16423db`；真实freezer已拒绝新增spill，未生成冻结窗口/空账本，actual direct/capture/replay/kernel/model/wire均0。单一配置结束，不扫参、不追加GPU。原服务保持停止，默认分派、Target采样、Pi medium/32768、18G1及全部旧失败/缺口不变。[结果与构建/资源证据](../../ninfer-v4-gqa-t4-bc64-20261024.md)。下列历次“当前/准备/空账本”为历史，不授予新的执行额度。

## 当前结果：W6接续完成，平均收益存在但稳定性首筛未通过

`H3-T01_STAGE_A_EXISTING_W6_REMAINING_AND_NATURAL_PERFORMANCE`现为`CLOSED_FIXED_W6_PILOT_STABILITY_GATE_NOT_MET`。数值链/Graph及4native状态逐bit通过；4自然性能请求给出Java/中文推理单位token完整轮耗时下降22.75%/20.38%，但Java后半段反向增加13.75%，故冻结首筛未通过。不能把平均收益当稳定业务/HTTP提升，也不能说完全无收益。

已执行8native/81decode、0Chat/HTTP/wire；r2窗口4分58秒，55capture/88replay/95027算法kernel，所有资源未超限，候选已清理，GPU空，原服务继续停止。r1驱动layers1错误及失败成本保留；修复48层后由用户追加授权3direct和数值D2H/memset各512MiB，两个窗口累计6次direct尝试、95030算法kernel。旧6项数值PASS未重跑，旧失败/18G1/C1和Baseline缺口不变。

冻结`273b37f4ec71945d3cd0865886d0c23db2ddefdd77bfa7ce66d7ab5409904679`已消费，不得重启。源码树`a728df11f92360108a3f12bb619137dafe4eed3d`，只改隔离驱动/bench/audit，无产品默认分派、Target采样或Pi32768变动。追加预算0，不自动Chat/扫K/W8。`p95=null`、`optimization_qualification=false`，阶段拆分和allocator高水位仍未观测。[完整结果和证据](../../ninfer-v4-h3-w6-resume-20261024.md)。以下历次当前/准备/空账本均为历史，不授予新预算。


## 当前选型：关闭Q4紧凑布局，补齐已有W6的完整decode实验

用户已关闭`K2-Q4-COMPACT-T4`，状态`CLOSED_NOT_ADOPTED_NO_FURTHER_EXPLORATION`，追加GPU/模型/HTTP预算0。紧凑四级/五级耗时+0.583%/+1.325%，保留原路径、原始数值证据与控制器权限失败；不再补测、扫参或进入完整模型验证。其他已关闭方向、全部失败、18处G1差异和C1缺口继续保留。

下一项只选`H3-T01_STAGE_A_EXISTING_W6_REMAINING_AND_NATURAL_PERFORMANCE`，当前`SELECTION_ONLY_NOT_IMPLEMENTED_NOT_FROZEN`。H3六项数值/Graph已通过；链在`WorkspaceArena(0)`处失败，native/Chat均未运行。复用源树`49bee647112ee171de35529028fc271494260751`及现有控制器，拟修失败链和异常审计、增加自然W4/K3对W6/K5完整轮对照，不开发W8，不恢复原已消费冻结入口。Q4/Q5共享Tile8是机会，27B Q6实际走SIMT c4/c6且成本增加；W6实际收益仍未知。

拟议无GPU准备4–6工程小时、≤6个新CPU合同；未来首筛仅失败链1场景/3direct/1capture/2replay，旧4native状态诊断固定9decode，另4自然性能请求各2warmup+16计时轮（≤72decode），合计8native/≤81decode、0Chat/HTTP/wire。Oracle状态请求不得算自然性能。完整窗口Graph/kernel/辅助传输预算尚未枚举，当前无可执行回执/账本、无GPU授权。后续窗口拟5–10分钟、硬20分钟/第17分钟清理；无净收益信号不追加Chat或扩W8。10%仅为两个prompt分别满足的后续投入门槛，不是提升预测或发布资格。

本轮仅jssh只读核对、旧证据计算与文档更新，0源码修改/构建/测试/GPU/模型/推理HTTP。原服务STOPPED、GPU空，镜像/参数/cache身份不变；默认分派、Target采样与Pi medium/32768不变。资格和发布继续独立，`p95=null`、`optimization_qualification=false`。[完整选型、收益条件和拟议预算](../../ninfer-v4-post-q4-selection-20261024.md)。以下历次“当前/准备/空账本”均为历史，不能覆盖本节或重新提供额度。

## 当前结果：Q4 FFN紧凑布局首筛完成，未形成采用信号

`K2-Q4-COMPACT-T4` 最终为 `MEASUREMENT_COMPLETE_NO_ADOPTION_CONTROLLER_READBACK_FAILED`。4场景逐bit/原FP64/guard、3个Graph最小验证通过；12direct、3capture、126replay、138算法kernel全部完成且未超限，0模型/HTTP。原4级中位161.792μs，紧凑4级162.736μs（耗时+0.583%、8/32组更快），紧凑5级163.936μs（+1.325%、7/32组更快），均未达采用门槛。保留原路径，本轮结束，不追加GPU或进入完整decode/Chat。

GPU候选exit0，ledger/summary COMPLETE，310条reservation全部完成；控制器随后读取root所有的0600账本触发PermissionError、exit1。无GPU只读BO导出并校验34文件/7冻结附件，原owner/mode/失败栈保留；不能报整套工具全PASS。冻结控制器不覆盖，未来复用须先明确宿主UID/GID并验证文件所有权，不能重用已消费入口。

已消费freeze `55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717`，源码树 `ebc4158e3146b87d65ca68427377476045af4646` 保持；窗口约4.334秒，候选/guardian退出、GPU空、lease释放，原服务STOPPED身份不变。默认分派、Target采样、Pi medium/32768不变；全部失败、18处G1差异、C1缺口保留。短窗口局部结果不证明稳定退化或完整推理收益；p95=null，优化/发布资格未通过。

[完整结果、原始证据、权限失败与限制](../../ninfer-v4-q4-compact-t4-hardware-20261024.md)。下文旧“准备完成/空账本/未运行”均为历史，不得据此重启已消费窗口。

## 当前交付：Q4 FFN 紧凑布局与五级预取 CPU/BO 准备完成

`K2-Q4-COMPACT-T4` 为 `CPU_BO_REVIEW_READY_GPU_UNRUN`。已在隔离分支完成默认false的共享layout、精确T4 bench-only原4级/紧凑4级/紧凑5级候选，以及复用驱动/控制器。8个新CPU合同通过；算子库、probe、原FP64参考消费测试目标与服务二进制构建通过（未跑旧测试）；独立静态集成评审无阻塞。三配置REG78、STACK/LOCAL0，SHARED29696/25600/32000。未运行GPU/模型/HTTP，不能声明逐bit或提速通过。

新源码树 `ebc4158e3146b87d65ca68427377476045af4646`，冻结根 `/home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1`，freeze `55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717`，空账本PRISTINE/used全0。后续首筛固定4场景、12direct、3capture、126replay、138算法kernel，0模型/HTTP；辅助资源详见冻结plan。硬10分钟、第7分钟清理。**本轮只交付准备，尚无实机执行；不得自动消耗预算。**

产品默认分派、Target采样、Pi medium/32768不改；原服务STOPPED，全部失败、18处G1差异、C1缺口保留。随机MTP及其他已关闭任务不再补测。先bench筛选，局部中位改善≥10%且≥12μs并至少24/32组改善，才考虑另行冻结完整Verify验证；接入须已有TextPhase::Verify＋精确T4，不能影响prefill。实测收益=null，资格/发布仍未通过。

[完整补丁、构建、资源、冻结入口与限制](../../ninfer-v4-q4-compact-t4-20261024.md)。下文此前“尚未实施/当前准备/待执行”等为保留的历史快照，以本节为准，不构成重跑或新增授权。

## 当前准备：随机 MTP 已关闭，下一项为 Q4 FFN 紧凑 shared 布局

用户已明确随机 MTP 就此收尾，不再追加补测：`CLOSED_NOT_ADOPTED_NO_FURTHER_TESTS`。保留 q/Graph/native 最小一致性通过、Chat无稳定整体收益、旧tool中止、control两端输出耗尽和全部成本；不得重启已消费入口。

下一唯一优先准备为 `K2-Q4-COMPACT-T4`（候选代号，不新增强制阶段门禁）：仅 C1/W4 的 Q4 FFN融合SwiGLU/实际T4，移除每stage未使用的1024B Q5 high区。原4级/min3与紧凑4级/min3、紧凑5级/min3比较；首筛仅bench，完整链需既有TextPhase::Verify限界，不能用T4推断阶段；默认分派、Target采样、Pi32768、Q5/Mixed及其他shape保持。29源树仍b9d4bfb714d537e1b9a51d94d3716c9441035107；原BO静态函数REG78/SHARED29696/LOCAL0，未新增构建或运行kernel。原服务STOPPED。

拟议首筛4输入/12direct/3capture/126replay/138算法执行，0模型/推理HTTP，硬10分钟、第7分钟清理；helper memset/copy也有有限提案上限。每图4correctness＋6warmup＋32timing。**尚未实施、未冻结实机回执/账本、不构成执行授权**；只有局部逐bit/性能达到门槛才提新的完整decode窗口，不复跑旧任务。可行性先限4工程小时，补丁/BO/CPU/评审约6–10小时，驱动冻结另1–2小时。

[完整源码依据、实施边界、预算与止损](../../ninfer-v4-post-sampled-selection-20261024.md)。当前收益预测=null；2%/4.5%/8%只是假定算子份额和局部改善后的情景，不能当实测。全部历史失败、18处G1差异、C1缺口及原始资料保留，性能/发布资格仍未通过。以下旧“当前/待执行”段落为历史记录，以本节为准。

## 当前结果：随机 MTP 接续完成，未形成稳定提速信号

`CONTINUATION_COMPLETE_NOT_QUALIFIED`。Graph memset 预算工具已修复；新增 CPU 5/5 PASS，复用原 BO 二进制、q/Graph/native 及已完成 Chat，未重跑。新窗口只发 6 个 Chat、7 个 wire、无新增 HTTP warmup；两窗口累计 14 次模型提交、12 个 wire，包含旧 tool 中止成本。

Java、中文推理、工具调用两端均 PASS；候选 Program 单位 token 耗时分别 +1.75%、+0.67%、−3.11%。工具题实际请求 4.355→5.053 秒，输出 649→808 token，不能报整体加速。控制题两端均耗尽 2048-token 夹具预算、只有 reasoning 无最终 content，保留 FAIL，不算有效性能胜出。每题一对、部分跨窗口、无新增 HTTP warmup，统计/性能/发布资格未通过。

新入口 `/home/hhtele/ninfer-v4-sampled-q-resume-20261024/prepared-window-r2`、freeze `8213b6427eff4be604a49b0c7c780eb0a26a96cafb1300d5f3aeda7cf90dc512` 已消费，账本 COMPLETE。162.739 秒清理，候选退出、GPU 空、lease 释放，原服务 STOPPED、身份不变。默认分派、Target 采样、Pi medium/32768 不改；所有旧失败、18 处 G1 差异与 C1 缺口保留。不得重启旧/新已消费入口或自动追加样本。

[完整结果、资源、原始证据与限制](../../ninfer-v4-sampled-q-resume-20261024.md)。92 项原始文件及 22 项本地冻结 SHA 核验，独立工具/结果评审无阻塞。p95=null、optimization_qualification=false。以下各轮“当前/未运行”说明均为历史快照，不构成当前待办、空账本或执行授权。

## 当前结果：随机MTP q与状态通过，Chat因冻结资源预算不足中止

`MINIMAL_VALIDATION_INCOMPLETE_CHAT_AUDIT_MEMSET_BUDGET_EXHAUSTED`。冻结r1已消费：数值4/4、8direct/4capture/8replay PASS，q最大误差2.64e-8；native4请求/8decode及真实partial/cancel与direct/Graph状态PASS_BITWISE。greedy warmup/Java/中文推理完整PASS，tool因阶段memset_calls65536封顶、进程exit95中断；raw control和candidate Chat未启动，性能有效对数0，收益null。

准备时沿用64K memset cap却未核算Graph节点×replay，是预算推导失误；审计在下一次GPU调用前拒绝。164.736秒已清理，GPU空、lease释放、原服务STOPPED身份不变；没有默认分派/Target/Pi32768变更。总模型提交8/14、wire5/12；原RUNNING/RESERVED账本和所有失败保留，当前没有存活请求。不得重启旧入口、重跑已通过数值/native或自动追加请求/预算。

[完整结果、失败原因、资源与缺口](../../ninfer-v4-sampled-q-hardware-20261024.md)。原始state远端只读归档，本机98项证据SHA核验；全部历史失败、18处G1差异和C1缺口保留。分布/性能/发布资格未通过。以下准备说明为历史快照，不能当空账本或执行授权。

## 当前交付：随机MTP完整q与实机窗口准备已冻结，尚未执行

分支`codex/sampled-q-hwprep-20261024`，树`b9d4bfb714d537e1b9a51d94d3716c9441035107`。raw/候选BO、新FP64参考4/4、新profile/ledger5/5通过；前轮CPU12组复用未重跑，两路评审开放0。本轮GPU/模型/HTTP均0，原服务STOPPED，默认分派、Target与Pi32768不改。

唯一新入口`/home/hhtele/ninfer-v4-sampled-q-hwprep-20261024/prepared-window-r1`，freeze`a0cef613dcd81bff75c9a6ed36f4f0aa294d42d2ab58ecd327f75b1347722d2f`，空账本全0、无runtime。冻结4场景/8direct/4capture/8replay、4native/≤12decode、8Chat＋2warmup/12wire、总≤14提交；全窗口GPU资源包含startup，硬20分钟、第17分钟清理。后续执行需明确GPU授权，不得运行已消费旧H3入口。预计窗口10–20分钟，结果分析30–60分钟。

[冻结回执、资源上限、缺口与验证](../../ninfer-v4-sampled-q-hwprep-20261024.md)。完整q/状态诊断复用原控制器；自然partial未出现应记缺口，不新增请求。Program计时不等于完整round wall，所有GPU/分布/性能/发布资格未通过。以下旧“当前”说明保留为历史快照，以本节和新回执为准。

## 当前交付：固定W4随机MTP＋精确q的CPU/BO候选

隔离分支`codex/sampled-q-w4-20261024`、源树`f557ab41f68105a629344c2acb5adb6f9a38c783`已完成可构建补丁：默认OFF/候选ON BO均PASS，新增CPU12/12，两路评审P1/P2已关闭；保留r1失败。原服务STOPPED，GPU/模型/HTTP均0，Target与Pi32768不改。现行默认仍greedy，新路线仅显式构建、fresh/cache off；缓存/分布/状态/性能/发布资格未通过。

[交付、补丁与最小实机提案](../../ninfer-v4-sampled-q-20261024.md)。仅CPU产物冻结；完整q的native诊断和全窗口GPU资源尚待适配/冻结，不可运行旧H3入口或把建议预算当执行授权。沿用现有控制器，不新建框架。下面历史研究与失败记录保留。

## 当前工作：性能复盘与sampled-q候选准备（未实施）

本轮已结合原始证据、29源码及固定上游资料复盘：局部优化缺关键路径份额、实验夹具与真实收益错位、驱动缺陷反复消耗窗口，均需纠正。唯一优先准备的新假设为C1/W4/K3 sampled MTP＋真实稀疏q接受修正，范围中等，收益未知；不能称为已证明的“最大收益/最小改动”。既有greedy＋Target sampling和131072优化头不重复开发；DFlash2匹配27B资产已存在，但适配范围大。

状态`RESEARCH_AND_CONTRACT_PREPARED_NOT_IMPLEMENTED`：无引擎补丁/BO/GPU/模型请求，仅8项离线有理数参考（不证明CUDA/随机数/状态资格）。现行delta-q合同保持权威，新general-q只是独立候选提案；必须携带实际完整条件q、保持Target参数和支持、独立proposal RNG，首筛cache off不抵扣缓存发布资格。原服务STOPPED，所有旧失败、18处G1差异及C1缺口保留。

后续候选范围与提出的单窗预算见[复盘与准备包](../../ninfer-v4-performance-reset-20261024.md)；完整GPU资源尚未冻结，不授予执行权。不要重启已消费H3入口，不自动补测W6，不重跑旧任务，不新增另一套controller。下面原H3硬件结论仍有效，准备排序不改变原验收状态或历史账本。

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

默认分派、采样/context/Pi medium/32768、18处G1差异和C1缺口不变，旧失败与CPU/BO原始证据保留、不重跑。仅T1024获得算子段信号，完整prefill/Chat及产品接入未授权，`p95=null`、`optimization_qualification=false`，任务资格模板仍PENDING。详见[实机报告](../../ninfer-v4-k2-t05-hardware-20261023.md)，后续边界见[任务合同](tasks/K2-T05.md)。下文CPU“GPU未运行”及旧拟议额度均为历史。


## 历史CPU准备：K2-T05构建、合同与评审完成，当时GPU未运行

状态`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。隔离分支`codex/k2-prefill-split-20261023`候选树`3ea537c00c759ef2a4577b525ae691f694ae102e`已完成BO构建、16项CPU合同（8 C++ Graph metadata＋8 Python编排）及集成评审；冻结SHA`7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc`。首轮CUDA13.2 Graph依赖API签名构建失败保留；两处改为4参数后增量构建PASS。已修复默认流reset到非阻塞Graph的同步及native非零退出的控制器失败处理。逐bit、实际Graph及收益均`NOT_RUN`，本轮0 GPU/模型/HTTP。[实施报告及冻结详情](../../ninfer-v4-k2-t05-implementation-20261023.md)。

未来最小预算仍为4数值、20 direct Op、4 capture、184 replay、384算法kernel、0模型/HTTP；辅助传输现已冻结：H2D 508次/4447860736字节、D2D 128次/7929856字节、D2H 768次/5386141696字节，raw段copy另限direct12/capture6/replay276，不能与辅助传输混算。预计2–5分钟，硬限10分钟、第7分钟清理。当前账本PRISTINE且所有计数0、无runtime；GPU执行需单独授权。旧选型中“辅助传输待枚举/null”仅为历史，不是当前缺口或无限额度。

K1-T01/C0/K2-T01继续关闭、追加预算0，不启动K1-T02。原数学、FP64阈值、state和默认分派保留，采样/context/Pi medium/32768不变，原服务STOPPED；18处G1差异、C1缺口及全部失败保留。20任务/4门禁/80断言、31 scope为可选库，任务资格仍PENDING，`p95=null`、`optimization_qualification=false`。下文旧成绩/预算保留，不据此重跑旧任务或授予产品资格。

## 历史选型范围：K1收尾，下一项仅选定K2-T05

K1-T01已由用户收尾，追加预算0；保留`GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW`及全部失败/缺口，不启动K1-T02产品接入。C0、K2-T01继续关闭，不重跑已通过任务。

唯一下项为[K2-T05普通Prefill卷积直接写连续Q/K/V](tasks/K2-T05.md)，状态`NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED`；复用源树`41a913488b0138fe868a8321d2f6a86ce83e313f`。先做bench-only限定shape候选，不改默认分派。本次选型不授予CPU实施或GPU执行授权；范围、待冻结传输预算和8–16工程小时估计见[选型报告](../../ninfer-v4-post-k1-selection-20261023.md)。

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

19项任务是可选择实验库，4门禁区分开发、归因、候选资格与发布。K0归因与C0-T01 CPU阶段已完成，实际记录见execution_evidence及[C0报告](../../ninfer-v4-c0-20261023.md)。任务status保留PENDING资格模板；不表示已通过的CPU应重跑，C0的Chat收益未证明且已关闭，追加补测预算0；下一项K2-T01仅选定未实施，任务及门禁模板不变。历史r2实机已完成：8Chat全部PASS、12wire/10提交含2warmup，345.047秒安全收尾；Chat性能INCONCLUSIVE。r1拒绝、CPU/准备期均分别保留，不重跑。

此前新增CPU证据修复了前缀夹具；14个新/受影响Python测试与8＋2个CPU前缀用例通过。该CPU阶段新pilot只准备、双轴评审已闭合、未运行GPU/HTTP/模型请求；后续r3已授权执行并关闭，不回写r2结果，不授予V04/K4或发布资格。

```json
{
  "schema": "ninfer.plan.md.v4.chat-perf.2",
  "as_of": "2026-10-23",
  "delivery": "CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN",
  "source": {
    "B": "44a2c6c3392c9d51e76a895ed97bf1867530d252",
    "O": "e0b05f7cb46adae2787be2ccbe605e1b0c9b3923",
    "U": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "H": "30dba4f11b577e1f7699ec0b2947d6fe9d5ea997",
    "qualified_p6_commit": null,
    "flare": "47581ccac82660953a5b59cb04b2750d64edc97d",
    "flashinfer_dependency": "622cec10eb75da189f4dadddabc2d142a33cd211",
    "qualified_kernel_commit": null
  },
  "execution_evidence": {
    "K2_GPU_screen": {
      "status": "GPU_SCREEN_COMPLETED_NO_SIGNAL_KEEP_512",
      "report": "../../ninfer-v4-k2-hardware-20261023.md",
      "freeze_sha256": "37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e",
      "source_tree": "13223b2b2989d0cf580715b197b276d74acffc86",
      "actual_counts": {
        "numeric_cases": 8,
        "direct_Op": 22,
        "Graph_capture": 6,
        "correctness_replay": 12,
        "warmup_replay": 60,
        "timing_replay": 1920,
        "Graph_replay_total": 1992,
        "native_model_admissions": 0,
        "model_submissions": 0,
        "HTTP": 0
      },
      "correctness": "PASS",
      "timing_metric": "HOST_SUBMITTED_SINGLE_NODE_GRAPH_REPLAY_NOT_PURE_KERNEL",
      "paired_batches": 5,
      "results": [
        {
          "T": 1,
          "CTA": 128,
          "median_improvement_percent": 1.2026,
          "faster_batches": 3,
          "status": "NO_SIGNAL"
        },
        {
          "T": 1,
          "CTA": 256,
          "median_improvement_percent": 5.7554,
          "faster_batches": 3,
          "status": "NO_SIGNAL"
        },
        {
          "T": 4,
          "CTA": 128,
          "median_improvement_percent": -3.4272,
          "faster_batches": 2,
          "status": "NO_SIGNAL"
        },
        {
          "T": 4,
          "CTA": 256,
          "median_improvement_percent": 4.9825,
          "faster_batches": 3,
          "status": "NO_SIGNAL"
        }
      ],
      "gate": "median_improvement>=10percent_AND_faster_batches>=4of5",
      "gate_satisfied": false,
      "controller_elapsed_seconds": 1.568326749,
      "owners": "CANDIDATE_GUARDIAN_CONTROLLER_EXITED",
      "GPU_compute_apps": "EMPTY",
      "original_service": "STOPPED",
      "action": "STOP_CURRENT_CTA_EXPERIMENT_KEEP_DEFAULT_512",
      "product_dispatch_changes": 0,
      "conditional_full_round": "NOT_ENTERED_NO_WINNER",
      "additional_budget": 0,
      "automatic_retry": false,
      "kernel_potential_exhaustively_disproved": false,
      "p95": null,
      "optimization_qualification": false,
      "runtime_present": true,
      "ledger_status": "COMPLETED",
      "single_use_consumed": true,
      "unresolved_reservations": 0,
      "raw_archive_sha256": "d6f31831d6731b25ea9fe3ad51db59018c52c66aaa48c3e2fc391c49a234a9a7",
      "original_evidence_files_verified": 20,
      "summary": "output/ninfer-v4-k2-hardware-20261023/final-summary.json",
      "new_evidence_gaps": [],
      "historical_cpu_stdout_disclosure": "CPU19_STRUCTURED_OBSERVATION_ONLY_RAW_STDOUT_NOT_SAVED"
    },
    "K2_CPU_implementation": {
      "status": "CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN",
      "branch": "codex/k2-gated-rmsnorm-20261023",
      "engineering_base_tree": "4d31af405fca9c70bd39a71257f83f4eeebbd0bc",
      "report": "../../ninfer-v4-k2-implementation-20261023.md",
      "probe": "ninfer_k2_gated_rmsnorm_probe",
      "probe_is_independent_of_old_plain_bench": true,
      "uses_original_warp_template_CTA": [
        128,
        256,
        512
      ],
      "shares_existing_double_oracle": true,
      "product_src_and_default_dispatch_changes": 0,
      "old_test": "COMPILE_ONLY_DO_NOT_EXECUTE_OLD_SUITE",
      "build_checks_review": "PASS_CPU_ONLY_GPU_NOT_RUN",
      "exact_hashes": {
        "candidate_tree": "13223b2b2989d0cf580715b197b276d74acffc86",
        "freeze_sha256": "37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e",
        "probe_sha256": "37ed2da07ebf489549c743fa92104a9aeea8c851e13715cae1615f8ac458bf5a",
        "patch_sha256": "3ab8e6f8003327b0b1e027b8d2807149bc081cf321a35287d52055e28fbd1037"
      },
      "new_GPU_HTTP_model_requests": 0,
      "future_probe_budget": {
        "cases": 8,
        "direct_Op": 22,
        "capture": 6,
        "replay": 1992,
        "correctness_replay": 12,
        "warmup_replay": 60,
        "timing_replay": 1920,
        "fallback": [
          "T1_unaligned",
          "T5_aligned"
        ],
        "model_admissions": 0,
        "model_submissions": 0,
        "HTTP": 0,
        "hard_seconds": 600,
        "cleanup_seconds": 420,
        "estimated_GPU_minutes": [
          2,
          5
        ],
        "execution_authorized": false
      },
      "controller_cpu_checks": {
        "unique_scenarios": 23,
        "initial_run": 19,
        "post_review_targeted": 4,
        "old_suites_run": 0
      },
      "native_CPU_CLI_checks": 11,
      "source_product_files_unchanged": 583,
      "review_findings": "FIXED_AND_REVIEWED",
      "prepared_root": "/home/hhtele/ninfer-v4-k2-20261023/prepared-window-r1",
      "runtime_present": false,
      "timing_metric": "host-submitted single-node Graph replay event elapsed, not isolated kernel latency"
    },
    "C0_closeout": {
      "status": "CLOSED_NO_FURTHER_MEASUREMENT",
      "user_decision": "C0先收尾，不再追加补测",
      "C0_CPU_result": "RETAINED_WITH_DISCLOSED_LIMITATIONS",
      "actual_L2_recovery": "PASS_RETAINED",
      "TTFT_benefit": "NOT_DEMONSTRATED_INCONCLUSIVE",
      "additional_test_budget": 0,
      "automatic_resumption": false,
      "no_old_window_restart": true,
      "original_summary": "output/ninfer-v4-c0-ttft-pilot-20261023/final-summary.json",
      "original_summary_sha256": "1b1d6ba4a39c5c8305f76f684b2e2baff449547e915f66b022be3c3aaa5f681c",
      "runtime_archive_sha256": "e3b19b9b915c5f3952df18d4e4d0ef3b8132cddb88c4a00600ec6167ff2e4844",
      "all_owner_processes_exited": true,
      "original_service_running": false,
      "original_GPU_service_policy": "KEEP_STOPPED_UNTIL_USER_REQUEST",
      "new_tests_GPU_HTTP_model_requests": 0,
      "p95": null,
      "optimization_qualification": false,
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED"
    },
    "K2_selection": {
      "status": "NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED",
      "task": "K2-T01",
      "candidate_scope": "kernel_candidate",
      "profile": "SM89_GATED_D128_H48_T1_T4_CTA_V1",
      "title": "D128 gated RMSNorm small-T CTA映射实验",
      "selection_basis": "SOURCE_CONFIRMED_EXECUTION_GEOMETRY_WITH_BOUNDED_FALSIFIABLE_COST_NOT_MEASURED_DOMINANT_HOTSPOT",
      "engineering_base_tree": "4d31af405fca9c70bd39a71257f83f4eeebbd0bc",
      "original_P4_reference_tree": "35d3dd9e4aa96b1f56f2e9c55482946bd9911cde",
      "C0_closed_no_extra_test": true,
      "C0_adopted_to_production": false,
      "runtime_identity_receipt": "remote-read-only-snapshot.json",
      "why_selected": [
        "真实27B每个GDN层已有融合gated RMSNorm，48层、D128、48heads。",
        "当前aligned gated small-T统一512线程，每warp一row，T1仅3CTA；同一kernel改128/256线程可试12/6CTA。",
        "当前MTP K3，verify width=K+1=4，仅选T1/T4，不扩W6/W8或prefill矩阵。",
        "无需新模型、权重、缓存格式、workspace或采样算法；CPU构建后可先以0模型请求筛掉无收益候选。"
      ],
      "implementation_scope": [
        "仅同一个 rmsnorm_warp_bf16x2_kernel<Gated,Block> 的512基线/128/256候选；保留行内归约、SiLU、乘法与BF16舍入。",
        "首补丁只提供bench/test内部候选，原产品分派保持原样；实测胜者才进入SM89隔离候选的静态shape路由。",
        "仅BF16 aligned D128 rows48/192；partial T2/T3、大prefill、unaligned、其它维度及epilogue维持原路。",
        "扩展已有rmsnorm_bench支持真实gate输入、显式原512对照、冻结循环预算、Graph/计时/route-hit输出。",
        "复用现有独立double oracle/阈值与guard检查；另外要求对相同输入的旧新BF16逐字节相同。",
        "仅构建受影响Op、bench、定向测试和必要产品集成目标；最多4个构建worker，不重跑旧Baseline/旧G1/P3矩阵。"
      ],
      "driver_cautions": [
        "现有candidate-b128/b256只接受plain，未传gate，不能直接当gated实验。",
        "现有--control是payload带宽对照，不能当真实512 RMSNorm算法基线。",
        "gdn_layer_bench是35B hidden2048/heads32/W8，不能认证27B hidden5120/heads48。",
        "target_mtp_round_bench默认BF16、动态小context、未显式生产sampling，不能直接冒作现况整轮资格。"
      ],
      "first_probe_budget": {
        "new_numeric_scenarios_max": 8,
        "normal_nearzero_saturated_gate": 6,
        "fallback_scenarios": 2,
        "T": [
          1,
          4
        ],
        "D": 128,
        "heads": 48,
        "CTA_configs": [
          512,
          128,
          256
        ],
        "direct_Op_calls_max": 22,
        "Graph_captures_max": 6,
        "correctness_single_node_replays_max": 12,
        "timing_configs": 6,
        "warmup_replays_per_config": 10,
        "timing_batches_per_config": 5,
        "timed_replays_per_batch": 64,
        "timing_replays_total_max": 1980,
        "Graph_replays_total_max": 1992,
        "native_model_request_admissions_max": 0,
        "HTTP_wire_max": 0,
        "model_submissions_max": 0,
        "GPU_hard_seconds": 600,
        "GPU_cleanup_seconds": 420,
        "estimated_GPU_minutes": [
          2,
          5
        ],
        "iterations_are_tiny_Op_not_model_requests": true
      },
      "first_probe_gates": {
        "numeric": "existing oracle criterion unchanged + exact old/new BF16 output + guard/input integrity",
        "route": "actual Gated T1/T4 route observed; no fallback or payload-control substitution",
        "performance": "same inputs and graphs,5interleaved batches; >=10% median singleOp improvement and >=4/5 batches faster on a selected production-reachable shape",
        "stop": "no stable gain/numeric mismatch/resource regression => STOP_KEEP_OLD_ROUTE; no extra configurations or retries for better result",
        "production_MTP_claim": "T1-only win without actual T1 route hits cannot establish current MTP3 production benefit"
      },
      "conditional_complete_round_gate": {
        "when": "only after first-probe winner, not development admission",
        "real_27B_driver_preparation_required": true,
        "native_request_admissions_proposed_max": 2,
        "decode_batch_round_calls_proposed_max": 24,
        "per_variant_warmup_rounds": 2,
        "per_variant_measured_rounds": 10,
        "HTTP_wire_proposed_max": 0,
        "sampling_Pi_context": "unchanged production semantics, context262144, medium/output32768; no tiny-context/BF16 substitute",
        "includes": "same input/state/RNG entitlement; actual route, draft+verify+commit+sync, effective licensed tokens and total round cost",
        "Graph_capture_replay_budget": null,
        "Graph_budget_null_reason": "new bounded production-config native driver not prepared; exact internal graph calls must be enumerated and frozen before execution",
        "engineering_hours_extra": [
          1,
          2
        ],
        "estimated_GPU_minutes": [
          5,
          10
        ],
        "GPU_hard_seconds_proposed": 900,
        "GPU_cleanup_seconds_proposed": 720,
        "adoption": "no complete-round gain => retain experiment, no Chat/K4/production speedup claim",
        "not_current_execution_authorization": true
      },
      "combined_GPU_hard_minutes_if_both_future_stages_authorized_max": 25,
      "expected_gain": {
        "single_Op_goal_reduction_fraction": 0.1,
        "measured_norm_share": null,
        "whole_round_or_Chat_gain": null,
        "reason": "no kernel profile/current norm share; more CTA is a mechanism, not measured throughput guarantee",
        "Amdahl_formula": "S_total = 1 / ((1-f_norm) + f_norm / S_norm)"
      },
      "estimated_time": {
        "CPU_patch_build_targeted_checks_review_hours": [
          3,
          5
        ],
        "conditional_full_round_driver_hours_extra": [
          1,
          2
        ],
        "full_round_validation_not_a_development_prerequisite": true
      },
      "not_selected": [
        {
          "candidate": "L2 PagedKV borrowed payload view",
          "reason": "decode-ahead exists; no prepare hits/inline counters to prove copy in synchronous .603s; original1.3GB snapshot no longer exists; do not repeat asynchronous C0 inference"
        },
        {
          "candidate": "GDN correction",
          "reason": "unknown op share, extra records/stores/state transaction and memory; higher first-proof cost"
        },
        {
          "candidate": "Q4/Q5 wider new tiles / W8/W16 / DFlash2 / lookup",
          "reason": "larger arithmetic/state/asset or acceptance risks; no better current low-cost proof than bounded CTA trial"
        },
        {
          "candidate": "workspace/utility/full upstream",
          "reason": "no new capacity or multiple-qualified-route issue; remaining upstream lacks direct text benefit evidence"
        }
      ],
      "current_turn_execution": {
        "read_only_ssh": true,
        "product_changes": 0,
        "builds_or_tests": 0,
        "GPU_HTTP_model_requests": 0
      },
      "original_GPU_service": "KEEP_STOPPED",
      "sampling_Pi_budget": "UNCHANGED",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED",
      "all_historical_failures": "PRESERVED",
      "p95": null,
      "optimization_qualification": false,
      "production_release": "NOT_RUN"
    },
    "research_base_tree": "35d3dd9e4aa96b1f56f2e9c55482946bd9911cde",
    "base_HEAD": "e0b05f7cb46adae2787be2ccbe605e1b0c9b3923",
    "commit_created": false,
    "research_base_report": "../../ninfer-v4-p4-chat-recheck-20261023.md",
    "P4_minimum": "PASS_WITH_DISCLOSED_LIMITATIONS",
    "full_performance_qualification": false,
    "production_release": "NOT_RUN",
    "G1_differences": 18,
    "C1_attachment_gap": "PRESERVED",
    "original_service": "STOPPED_DO_NOT_RESTORE",
    "p95": null,
    "optimization_qualification": false,
    "K0": {
      "status": "MINIMUM_ATTRIBUTION_COMPLETE_WITH_GPU_TRACE_GAPS",
      "report": "../../ninfer-v4-k0-20261023.md",
      "receipt": "../../../output/ninfer-v4-k0-20261023/final-summary.json",
      "selected_candidate": "cpu_sha_candidate",
      "source_and_binary_identity": "LIVE_VERIFIED_1235_SOURCE_FILES_AND_SERVE_SHA",
      "GPU_profile": "NOT_RUN_NULL",
      "K0_sampling_and_Pi_budget": "UNCHANGED",
      "new_CPU_diagnostic_only": true,
      "product_implementation_authorized": false,
      "model_HTTP_GPU_executed": 0
    },
    "C0": {
      "status": "CPU_PHASE_PASS_WITH_DISCLOSED_LIMITATIONS_AWAITING_CHAT",
      "report": "../../ninfer-v4-c0-20261023.md",
      "receipt": "../../../output/ninfer-v4-c0-20261023/final-summary.json",
      "candidate_tree": "4d31af405fca9c70bd39a71257f83f4eeebbd0bc",
      "commit_created": false,
      "CPU_budget_used": {
        "scenarios": 31,
        "comparisons": 58,
        "timing_pairs": 7
      },
      "BO_dependency_closure": "PASS",
      "build": "PASS",
      "integrated_review": "STANDARDS_AND_SPEC_PASS_READ_ONLY",
      "bulk_hash_speedup": 2.1490972160774096,
      "publication_reduction": 0.5312240548892977,
      "first_EVP_ms": 1.90378,
      "GPU_model_HTTP_executed": 0,
      "Chat_service_qualification": false,
      "p95": null,
      "optimization_qualification": false
    },
    "C0_hardware_preparation": {
      "status": "PREPARATION_AND_INTEGRATION_REVIEW_PASS_GPU_NOT_EXECUTED",
      "driver_tree": "0e5efa0fd62d60a90060b9896a1d4e115495e879",
      "product_tree": "4d31af405fca9c70bd39a71257f83f4eeebbd0bc",
      "report": "../../ninfer-v4-c0-hw-prep-20261023.md",
      "receipt": "../../../output/ninfer-v4-c0-hw-prep-20261023/preparation-receipt.json",
      "freeze_sha256": "b09cb8d9ac7adc8f63af562ca6221a5f1522896c4aab8904b0d931f87aabffe7",
      "new_driver_tests_unique": 57,
      "new_driver_test_executions": 62,
      "budget": {
        "new_Chat_max": 8,
        "builtin_warmup_max": 2,
        "model_submissions_max": 10,
        "wire_max": 12,
        "cleanup_seconds": 720,
        "hard_seconds": 900,
        "direct_Op": 0,
        "capture": 0,
        "replay": 0
      },
      "actual_GPU_HTTP_model": 0,
      "original_service": "STOPPED_UNCHANGED",
      "new_GPU_authorized": false,
      "actual_budget_used": {
        "wire": 0,
        "model_requests": 0,
        "model_submissions": 0,
        "builtin_warmup": 0
      },
      "p95": null,
      "optimization_qualification": false
    },
    "C0_hardware_execution": {
      "status": "INCONCLUSIVE_PRE_ADMISSION_FIXTURE_REJECTION",
      "report": "../../ninfer-v4-c0-hardware-20261023.md",
      "receipt": "../../../output/ninfer-v4-c0-hardware-20261023/final-summary.json",
      "freeze_sha256": "b09cb8d9ac7adc8f63af562ca6221a5f1522896c4aab8904b0d931f87aabffe7",
      "window_id": "c0-sha-pilot-20261023-r1",
      "reserved_budget": {
        "wire": 2,
        "model_requests": 1,
        "model_submissions": 2,
        "builtin_warmup": 1
      },
      "actual": {
        "wire": 2,
        "Chat_HTTP_attempts": 1,
        "Chat_HTTP400": 1,
        "Chat_model_admissions": 0,
        "builtin_warmup_submissions": 1,
        "model_submissions": 1,
        "new_direct_Op": 0,
        "new_capture": 0,
        "new_replay": 0
      },
      "elapsed_seconds": 301.7480082990078,
      "original_service": "STOPPED_DO_NOT_RESTORE",
      "collector_gap": "original outcome/stage absent; complete pre-admission400 reconciled separately; original ledger unchanged",
      "eligible_service_pairs": 0,
      "p95": null,
      "optimization_qualification": false,
      "K4_qualified": false
    },
    "C0_hardware_execution_r2": {
      "status": "MINIMUM_CHAT_AND_LIFECYCLE_PASS_PERFORMANCE_INCONCLUSIVE",
      "report": "../../ninfer-v4-c0-hardware-20261023-r2.md",
      "receipt": "../../../output/ninfer-v4-c0-hardware-20261023-r2/final-summary.json",
      "driver_tree": "b8431b377d4e990c254437c1e10dfb714079b5d7",
      "freeze_sha256": "7b7682a9904cb807268e2b2fd52d88d741a7b3194da022d43bae813b65d2a338",
      "actual_budget": {
        "new_Chat": 8,
        "wire": 12,
        "builtin_warmup": 2,
        "total_model_submissions": 10,
        "direct_Op": 0,
        "capture": 0,
        "replay": 0
      },
      "elapsed_seconds": 345.0472260359966,
      "all_Chat_PASS": true,
      "handoff_cleanup": "PASS",
      "performance_status": "INCONCLUSIVE_NO_QUALIFYING_SERVICE_PAIRS",
      "eligible_pairs": 0,
      "p95": null,
      "optimization_qualification": false,
      "K4_qualified": false,
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED",
      "r1_failures_and_gaps": "PRESERVED_UNCHANGED"
    },
    "C0_l2_repair_CPU": {
      "status": "CPU_REPAIR_AND_REVIEW_CLOSED_GPU_NOT_RUN",
      "report": "../../ninfer-v4-c0-l2-preflight-20261023.md",
      "root_cause": "FIXTURE_AUTO_TO_NONE_REMOVED_TOOLS_PREFIX",
      "product_changes": 0,
      "historical_prefix_cases": {
        "passed": 8,
        "original_LCP": 1,
        "repaired_LCP": [
          55483,
          55562
        ],
        "safe_checkpoints": [
          55481,
          55560
        ]
      },
      "controlled_branch_first_revision": "POSITIVE_FAILED_LCP_55291_BELOW_55293_PRESERVED",
      "controlled_branch_repaired": {
        "passed": 2,
        "LCP": 55295,
        "safe_checkpoint": 55293,
        "synthetic_assistant_is_input_not_seed_output": true
      },
      "new_or_affected_Python_CPU_tests_passed": 14,
      "final_integrated_review": "STANDARDS_AND_SPEC_FINDINGS_CLOSED_READ_ONLY",
      "actual_GPU_HTTP_model": 0,
      "image_import_verified": false,
      "TTFT_benefit_verified": false,
      "pilot": {
        "profile": "CONTROLLED_PREFIX_BRANCH_TTFT_V1",
        "authorization": "PREPARATION_NOT_AUTHORIZED",
        "order": [
          "P4",
          "C0"
        ],
        "new_Chat_max": 4,
        "builtin_warmup_max": 2,
        "total_model_submissions_max": 6,
        "wire_max": 10,
        "telemetry_wire_max": 4,
        "conditional_erase_wire_max": 2,
        "direct_Op": 0,
        "capture": 0,
        "replay": 0,
        "estimated_minutes": [
          6,
          10
        ],
        "cleanup_seconds": 720,
        "hard_seconds": 900,
        "seed_done_delay_seconds": 10.0,
        "delay_tolerance_seconds": 0.15,
        "maximum_result": "PILOT_TTFT_SIGNAL_NOT_K4"
      },
      "original_service": "STOPPED_DO_NOT_RESTORE",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED",
      "all_previous_failures": "PRESERVED_UNCHANGED",
      "Chat_service_qualification": false,
      "p95": null,
      "optimization_qualification": false,
      "K4_qualified": false,
      "driver_tree": "130bcf5414fc89d971f368fc81e9aafdda7753dd",
      "freeze_sha256": "1b0f1c596aa15f5e41d337f139d936c51ac52131ecd6d3c5efabc1e384127dd1",
      "receipt": "../../../output/ninfer-v4-c0-l2-preflight-20261023/preparation-receipt.json",
      "execution_authorized": false
    },
    "C0_TTFT_pilot_r3": {
      "status": "COMPLETED_SAFE_CLEANUP",
      "report": "../../ninfer-v4-c0-ttft-pilot-20261023.md",
      "summary": "../../../output/ninfer-v4-c0-ttft-pilot-20261023/final-summary.json",
      "profile": "CONTROLLED_PREFIX_BRANCH_TTFT_V1",
      "order": [
        "P4",
        "C0"
      ],
      "new_Chat_passed": 4,
      "wire": 10,
      "model_submissions_including_warmup": 6,
      "builtin_warmup": 2,
      "wall_seconds": 246.142777927,
      "driver_tree": "130bcf5414fc89d971f368fc81e9aafdda7753dd",
      "frozen_tool_files_verified": 21,
      "freeze_sha256": "1b0f1c596aa15f5e41d337f139d936c51ac52131ecd6d3c5efabc1e384127dd1",
      "request_raw_hashes_verified": true,
      "branches": {
        "P4": {
          "source": "l2",
          "restored_tokens": 55293,
          "P": 55374,
          "computed_prefill": 81,
          "restored_bytes": 1333980256,
          "client_semantic_TTFT_seconds": 0.943552271,
          "queue_seconds": 0.618971645,
          "seed_export_bytes": 1333034412,
          "post_copy_publication_seconds": 14.37246595,
          "alias_kind": "stable_prefix"
        },
        "C0": {
          "source": "l2",
          "restored_tokens": 55293,
          "P": 55374,
          "computed_prefill": 81,
          "restored_bytes": 1336349835,
          "client_semantic_TTFT_seconds": 0.959943143,
          "queue_seconds": 0.641931568,
          "seed_export_bytes": 1335401900,
          "post_copy_publication_seconds": 7.060492013,
          "alias_kind": "routed_session"
        }
      },
      "performance_status": "INCONCLUSIVE_TTFT_CONTROL_NOT_SATISFIED",
      "control_failures": [
        "P4_ALSO_DEEP_L2",
        "BOTH_QUEUE_ABOVE_50MS",
        "SEED_EXPORT_BYTE_SHAPES_DIFFER"
      ],
      "observed_C0_TTFT_change_percent": 1.737,
      "TTFT_benefit_verified": false,
      "publication_observation": "DESCRIPTIVE_N1_APPROX_50_87_PERCENT_LOWER_NOT_STRICT_PAIR_NOT_TTFT_BENEFIT",
      "unknown_requests": 0,
      "unfinished_exports": 0,
      "new_attachment_gaps": 0,
      "candidate_processes": "EXITED",
      "GPU_compute_processes": "EMPTY",
      "original_service": "STOPPED_DO_NOT_RESTORE",
      "window": "SINGLE_USE_CONSUMED_DO_NOT_RESTART",
      "failures": "NONE_THIS_RUN_ALL_HISTORICAL_FAILURES_PRESERVED",
      "sampling_and_Pi_32768": "UNCHANGED",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED",
      "V04_verified": false,
      "p95": null,
      "optimization_qualification": false,
      "K4_qualified": false,
      "hypothesis_correction": "FINAL_PUBLICATION_UNFINISHED_DOES_NOT_EXCLUDE_EARLIER_STABLE_PREFIX_RESTORE",
      "queue_metric": "ADMITTED_MINUS_SUBMITTED_INCLUDES_RESTORE_ADMISSION_NOT_PROOF_OF_EXTERNAL_CONTENTION",
      "independent_evidence_review": "READ_ONLY_NO_BLOCKING_FINDINGS_NO_TESTS_EXECUTED"
    },
    "K2_closeout": {
      "status": "CLOSED_NO_FURTHER_MEASUREMENT",
      "task": "K2-T01",
      "user_decision": "K2-T01就此收尾，不再追加补测",
      "result": "GPU_SCREEN_COMPLETED_NO_SIGNAL_KEEP_512",
      "numeric": "PASS",
      "Graph": "PASS",
      "performance": "NO_SIGNAL_ALL_FOUR",
      "default_route": "KEEP_512",
      "additional_budget": 0,
      "automatic_retry": false,
      "conditional_complete_round": "NOT_STARTED_NO_WINNER",
      "original_summary": "output/ninfer-v4-k2-hardware-20261023/final-summary.json",
      "original_summary_sha256": "795a9c858055b88f3e0f5ebd1789ac84ad71dc183cad5a6dc2f61de49a6ed285",
      "original_archive_sha256": "d6f31831d6731b25ea9fe3ad51db59018c52c66aaa48c3e2fc391c49a234a9a7",
      "current_archive_sha256": "d6f31831d6731b25ea9fe3ad51db59018c52c66aaa48c3e2fc391c49a234a9a7",
      "frozen_inputs_still_match": true,
      "source_tree": "13223b2b2989d0cf580715b197b276d74acffc86",
      "original_service": "KEEP_STOPPED",
      "current_GPU_empty": true,
      "all_historical_failures": "PRESERVED",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED",
      "current_turn_GPU_HTTP_model_build_test_calls": 0
    },
    "K1_selection": {
      "status": "NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED",
      "task": "K1-T01",
      "profile": "SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1",
      "scope": "BENCH_ONLY_GDN_RECURRENT_RECORD_PLUS_ALL_LAYER_FOLD",
      "title": "GDN correction records：复用已算修正量，先做48层Record＋Fold对照",
      "engineering_base_tree": "4d31af405fca9c70bd39a71257f83f4eeebbd0bc",
      "current_read_source_tree": "13223b2b2989d0cf580715b197b276d74acffc86",
      "P4_reference_tree": "35d3dd9e4aa96b1f56f2e9c55482946bd9911cde",
      "next_branch": "NOT_CREATED_THIS_READ_ONLY_TURN",
      "K2_closed": true,
      "C0_closed": true,
      "source_witnesses": 17,
      "selection_basis": "SOURCE_CONFIRMED_RECOMPUTATION_AND_BOUNDED_FALSIFIABLE_SEGMENT_NOT_MEASURED_DOMINANT_HOTSPOT",
      "reason": [
        "现有Record与Fold复用同一递推，均归一化key并重算exp(g)、state·key、delta。",
        "当前27B C1/MTP3为W4，48个GDN层；先不加载模型即可覆盖真实heads/dim/物理记录容量。",
        "Q4/Q5已有small-T MMA/split-K，传输已有合并/双slot，workspace已一次分配；缺少新增改造的直接归因。",
        "K2 host-submitted单节点Graph无稳定信号；新首证改为每图完整48 recurrent Record＋1all-layer Fold，不重复K2。"
      ],
      "existing_optimizations_not_new": [
        "compact raw records",
        "one all-layer fold launch",
        "FP32 persistent recurrent state",
        "next-key preloading",
        "Q4/Q5 small-T MMA",
        "pinned transfer batching",
        "startup workspace arena"
      ],
      "implementation_scope": [
        "在隔离分支新增内部typed correction layout及Record/Fold候选，保留raw代码与独立池；首补丁不接Engine/Program、不改默认分派。",
        "从原helper实际FP32运算点保存normalized key、alpha、delta；保持原normalization/exp/warp reduction/beta/FMA/舍入和state update顺序，不移植不同数学。",
        "候选Record只写correction平面，raw对照只写raw平面；两个pool可共存但不双写；若以后产品需双写，重新计入整段成本，不能继承此结果。",
        "conv平面保留各自独立存储并预置相同冻结输入，normalized key和alpha/delta的writer按现有head/tile去重，禁止data race。",
        "复用既有FP64 gdn_ref及原阈值，另严格比较recurrent readout BF16、正式FP32 state与conv逐bit，guard及未写suffix。",
        "首驱动仅C=1物理record row、W4、48layers/Hk16/Hv48/D128，不用旧bench固定capacity8/slots11，也不加载权重/更改context。",
        "新增最多16个CPU合同场景，受影响BO构建与独立集成评审；复用旧证据，不执行旧suite/Baseline/G1/已过题目。"
      ],
      "entry_gate_split": {
        "bench_development": "confirmed recomputation + bounded typed contract; current selected hypothesis, no measured hotspot prerequisite",
        "product_integration": "requires bitwise+FP64, actual segment net gain/bytes and separately authorized K1-T02 runtime route/permit/epoch/cancel validation",
        "complete_round_and_publication": "separate later gates; no winner means stop"
      },
      "excluded": [
        "Engine default route",
        "Program commit/epoch/slot ownership changes",
        "Target sampler/RNG/proposal changes",
        "cache/codec/model formats",
        "K3 workspace aliasing",
        "W8/W16/DFlash/Lookup scope expansion",
        "complete Target Verify/full-model-round claims from isolated Op"
      ],
      "resource_estimates": {
        "kind": "DERIVED_PAYLOAD_NOT_MEASURED_ALLOCATION",
        "C": 1,
        "W": 4,
        "layers": 48,
        "raw_bytes": 7151616,
        "correction_bytes": 10260480,
        "correction_additional_bytes_conservative": 10260480,
        "raw_plus_correction_bytes": 17412096,
        "persistent_state_bytes_per_copy": 150994944,
        "alignment_Graph_other_workspace": "EXCLUDED_FROM_PAYLOAD",
        "state_traffic_removed": false,
        "loaded_model_headroom_unknown": true
      },
      "first_probe_budget": {
        "kind": "PROPOSED_ONLY_NOT_EXECUTION_AUTHORIZATION",
        "numeric_cases_max": 8,
        "cases": [
          {
            "name": "normal-commit0",
            "family": "normal",
            "commit": 0,
            "valid": 4
          },
          {
            "name": "normal-commit1",
            "family": "normal",
            "commit": 1,
            "valid": 4
          },
          {
            "name": "normal-commit2",
            "family": "normal",
            "commit": 2,
            "valid": 3
          },
          {
            "name": "normal-commit3",
            "family": "normal",
            "commit": 3,
            "valid": 4
          },
          {
            "name": "normal-commit4",
            "family": "normal",
            "commit": 4,
            "valid": 4
          },
          {
            "name": "stress-commit0",
            "family": "stress",
            "commit": 0,
            "valid": 4
          },
          {
            "name": "stress-commit2",
            "family": "stress",
            "commit": 2,
            "valid": 2
          },
          {
            "name": "stress-commit4",
            "family": "stress",
            "commit": 4,
            "valid": 4
          }
        ],
        "variants": [
          "raw",
          "correction_only"
        ],
        "layers": 48,
        "record_Op_calls_per_variant_group": 48,
        "all_layer_Fold_Op_calls_per_variant_group": 1,
        "Op_calls_per_variant_group": 49,
        "direct_Op_calls_max": 784,
        "timing_commit_counts": [
          1,
          2,
          4
        ],
        "Graph_captures_max": 6,
        "algorithm_kernel_nodes_per_graph": 49,
        "algorithm_kernel_nodes_captured_total": 294,
        "correctness_replays_per_config": 2,
        "warmup_replays_per_config": 4,
        "timing_batches_per_config": 5,
        "timing_replays_per_batch": 8,
        "correctness_replays_total": 12,
        "warmup_replays_total": 24,
        "timing_replays_total": 240,
        "Graph_replays_total_max": 276,
        "algorithm_kernel_executions_max": 14308,
        "model_submissions_max": 0,
        "HTTP_wire_max": 0,
        "GPU_expected_minutes": [
          3,
          8
        ],
        "GPU_hard_seconds": 900,
        "GPU_cleanup_seconds": 720,
        "state_reset": "immutable same initial state before each paired batch, D2D outside timed event; rolling in-graph recurrence matched between variants",
        "ordering": "five paired batches, raw/correction AB/BA alternation; record CUDA segment event and host submission wall",
        "data_transfer_calls_and_bytes": null,
        "data_transfer_null_reason": "driver not prepared; must enumerate, bound and freeze initialization/reset/export memcpy counts and bytes before GPU execution",
        "implicit_helper_compute": "no uncounted compute warmup/reset kernels; unexpected nodes or changed census fail closed",
        "stress_inputs": "per-head/layer nearzero keys, finite nonpositive g decay including extremes, beta in [0,1], represented BF16/FP32 inputs; no invalid positive-g overflow fixture",
        "mask_and_suffix_checks": "check Record invalid-output zeroing and unwritten-record canaries before poisoning rejected suffix; then Fold prefix result must be unchanged; commit3 covers first generic conv-history branch"
      },
      "first_probe_acceptance": {
        "correctness": "existing FP64 tolerances unchanged AND exact raw/correction readout/state/conv + masks/guards",
        "performance": "Record48+Fold1 complete operator segment median paired improvement>=10percent AND at least4of5 paired batches faster",
        "no_zero_commit_performance_claim": true,
        "signal": "SEGMENT_SIGNAL_NOT_K4",
        "no_signal_or_numeric_failure": "STOP_KEEP_RAW_NO_EXTRA_CONFIG_OR_RETRY",
        "runtime_qualification": "NOT_GRANTED_BY_OPERATOR_BENCH; Op commit0 is not Program cancellation/epoch/permit qualification"
      },
      "risk": [
        "extra record store/load may outweigh saved dot/exp; no reduction to existing state reads/writes",
        "historical repository shuffle optimizations near0percent suggest memory-bound risk; not a current29 trace",
        "record stores may change NVCC contraction/register allocation; FP64 tolerance cannot replace FP32 exact clone",
        "this graph excludes conv/input projection, attention/MLP, proposal/sampling and host permit; recurrent readout is not full Target verify output"
      ],
      "current_GDN_segment_share": null,
      "whole_round_or_Chat_gain": null,
      "expected_gain": "UNMEASURED; 10percent is adoption threshold, not forecast",
      "estimated_time": {
        "CPU_patch_oracle_BO_review_hours": [
          6,
          12
        ],
        "bounded_driver_freeze_hours": [
          2,
          4
        ],
        "total_engineering_hours": [
          8,
          16
        ],
        "GPU_first_probe_minutes": [
          3,
          8
        ],
        "conditional_Runtime_K1_T02_additional_days": [
          1,
          2
        ],
        "conditional_Runtime_execution_budget": "NOT_FROZEN_NOT_AUTHORIZED; enumerate real context/Graph/model admissions before any run"
      },
      "not_selected": [
        {
          "candidate": "Q4/Q5 routing",
          "reason": "already small-T optimized; no newly measured tile bottleneck"
        },
        {
          "candidate": "GDN preloading",
          "reason": "already next-key preload; unproven wider preload and register pressure"
        },
        {
          "candidate": "CPU/cache/workspace",
          "reason": "C0 closed; restore attribution absent, transfer batching and arena already implemented"
        },
        {
          "candidate": "full upstream/advanced proposal routes",
          "reason": "no stronger low-cost mechanism/evidence; retain optional library, not this scope"
        }
      ],
      "original_service": "KEEP_STOPPED",
      "sampling_context_Pi": "UNCHANGED_MEDIUM_32768",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED_UNRESOLVED",
      "all_historical_failures": "PRESERVED",
      "current_turn": {
        "remote_access": "jssh 29",
        "read_only": true,
        "product_changes": 0,
        "builds_or_tests": 0,
        "GPU_HTTP_model_requests": 0,
        "source_witness_files_matched": 17
      },
      "p95": null,
      "optimization_qualification": false,
      "production_release": "NOT_RUN",
      "record_writing_strategy": "RAW_REFERENCE_WRITES_RAW_ONLY; CANDIDATE_WRITES_CORRECTION_ONLY; BOTH_POOLS_ALLOCATED; NO_SIMULTANEOUS_DUAL_WRITE"
    },
    "K1_CPU_implementation": {
      "status": "CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN",
      "report": "../../ninfer-v4-k1-implementation-20261023.md",
      "branch": "codex/k1-correction-records-20261023",
      "base_product_tree": "4d31af405fca9c70bd39a71257f83f4eeebbd0bc",
      "candidate_tree": "1f26afd245e2f6fca5d7e2bee34ec07839ef62bf",
      "BO_image": "sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251",
      "CPU_scenarios_passed": 16,
      "CPU_scenario_split": {
        "CXX": 8,
        "Python": 8
      },
      "freeze_sha256": "4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105",
      "probe_sha256": "5978092c268e1cf19481dfada20df66b0d45e143fffe8e0de83e41edf0dde726",
      "source_files_changed": 15,
      "unchanged_base_files": 1235,
      "GPU_HTTP_model_requests": 0,
      "hardware_budget": {
        "algorithm_kernels": 14308,
        "captures": 6,
        "direct_ops": 784,
        "model_submissions": 0,
        "numeric_scenarios": 8,
        "replays": 276,
        "wire": 0
      },
      "transfer_limits": {
        "d2d_bytes": 19704905728,
        "d2d_calls": 128,
        "d2h_bytes": 30979424768,
        "d2h_calls": 896,
        "h2d_bytes": 3174503944,
        "h2d_calls": 847
      },
      "cleanup_seconds": 720,
      "hard_seconds": 900,
      "reference_scope": {
        "independent_fp64_layers": [
          0
        ],
        "layer_distinct_state_and_conv": true,
        "raw_bitwise_layers": 48
      },
      "actual_GPU_numeric_Graph_performance": "NOT_RUN",
      "current_ledger": "PRISTINE",
      "runtime_present": false,
      "qualification": "NOT_GRANTED",
      "original_service": "KEEP_STOPPED",
      "optimization_qualification": false
    },
    "K1_GPU_screen": {
      "status": "PARTIAL_NUMERIC_PASS_GRAPH_WITNESS_FAILED_NO_TIMING",
      "report": "../../ninfer-v4-k1-hardware-20261023.md",
      "freeze_sha256": "4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105",
      "candidate_tree": "1f26afd245e2f6fca5d7e2bee34ec07839ef62bf",
      "profile": "SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1",
      "numeric_scenarios_passed": 8,
      "direct_ops_completed": 784,
      "direct_algorithm_kernels_completed": 784,
      "bitwise_raw_correction": {
        "FP32_state": "PASS_ALL_48_LAYERS",
        "conv": "PASS_ALL_48_LAYERS",
        "BF16_readout": "PASS_ALL_48_LAYERS"
      },
      "independent_fp64_layers": [
        0
      ],
      "fp64_reference": "PASS_EXISTING_ORACLE",
      "guard_suffix": "PASS",
      "capture_reserved": 1,
      "captures_completed": 0,
      "replays_completed": 0,
      "failure": "unexpected Fold function/geometry",
      "failure_scope": "FIRST_RAW_COMMIT1_CAPTURE_FUNCTION_GEOMETRY_WITNESS",
      "failure_attribution": "UNRESOLVED_NODE_PARAMETERS_NOT_PRINTED_RECORD_FUNCTION_ADDRESS_MISMATCH_ALSO_POSSIBLE",
      "Graph_correctness": "NOT_ESTABLISHED",
      "Record_Fold_net_gain": null,
      "timing": "NOT_RUN",
      "model_submissions": 0,
      "wire": 0,
      "window_duration_seconds_approx": 7,
      "current_ledger_status": "RUNNING_PRESERVED_FAILURE_STATE_NOT_ACTIVE_PROCESS",
      "window": "TERMINATED_SINGLE_USE_DO_NOT_RESTART",
      "candidate": "EXITED",
      "original_service": "STOPPED",
      "GPU": "IDLE",
      "lease": "FREE",
      "cpu_implementation_evidence": "HISTORICAL_UNCHANGED",
      "frozen_initial_ledger": "UNCHANGED",
      "next_scope": "GRAPH_WITNESS_DIAGNOSTIC_FIX_AND_FRESH_UNFINISHED_GRAPH_BUDGET_ONLY",
      "automatic_GPU_execution": false,
      "repeat_passed_numeric": false,
      "qualification": "PENDING",
      "optimization_qualification": false
    },
    "K1_Graph_R2": {
      "status": "GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW",
      "profile": "SM89_GDN_CORRECTION_C1_W4_L48_GRAPH_ONLY_R2",
      "source_tree": "41a913488b0138fe868a8321d2f6a86ce83e313f",
      "freeze_sha256": "29c89db3f440cea8b8620e0728dd9220c7c3366782fbc408b283e5aedd9e0969",
      "report": "../../ninfer-v4-k1-graph-r2-20261023.md",
      "CPU_metadata_scenarios": 8,
      "CPU_tool_scenarios": 8,
      "numeric_cases_reused": 8,
      "numeric_cases_new": 0,
      "actual_counts": {
        "direct_Op": 0,
        "Graph_capture": 6,
        "correctness_replay": 12,
        "warmup_replay": 24,
        "timing_replay": 240,
        "Graph_replay_total": 276,
        "algorithm_kernels": 13524,
        "model_submissions": 0,
        "HTTP": 0
      },
      "graph_witness": "PASS_49_NODES_PER_CAPTURE",
      "graph_bitwise": "PASS_ALL_48_LAYERS",
      "FP64_reference": "PASS_LAYER0_GRAPH_CORRECTNESS",
      "ledger_status": "COMPLETE",
      "unknown_outcomes": false,
      "paired_batches": 5,
      "timing_metric": "HOST_SUBMITTED_RECORD48_FOLD1_SEGMENT_NOT_FULL_VERIFY",
      "results": [
        {
          "commit": 1,
          "median_improvement_fraction": -0.010539891533988795,
          "faster_batches": 0,
          "status": "NO_SEGMENT_SIGNAL"
        },
        {
          "commit": 2,
          "median_improvement_fraction": -0.000713768465217422,
          "faster_batches": 0,
          "status": "NO_SEGMENT_SIGNAL"
        },
        {
          "commit": 4,
          "median_improvement_fraction": 0.001809313596551461,
          "faster_batches": 3,
          "status": "NO_SEGMENT_SIGNAL"
        }
      ],
      "wall_seconds_approx": 10.7,
      "next": "KEEP_RAW_NO_K1_T02_PRODUCT_INTEGRATION_NO_MORE_GPU",
      "optimization_qualification": false,
      "p95": null,
      "old_failure_evidence": "PRESERVED_NODE_PARAMETER_GAP_NOT_BACKFILLED"
    },
    "K1_closeout": {
      "status": "CLOSED_NO_FURTHER_MEASUREMENT",
      "task": "K1-T01",
      "closed_by": "USER_EXPLICIT_INSTRUCTION",
      "additional_GPU_numeric_direct_capture_replay_model_HTTP_budget": 0,
      "Graph_result": "GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW",
      "numeric_evidence": "REUSED_8_SCENARIOS_ALL_48_LAYERS_BITWISE_PASS",
      "timing_segment": "48 recurrent Record + 1 all-layer Fold; host submission gaps included; not full Verify or Chat",
      "median_improvement_pct_by_commit": {
        "1": -1.0539891534,
        "2": -0.0713768465,
        "4": 0.1809313597
      },
      "faster_batches_by_commit": {
        "1": 0,
        "2": 0,
        "4": 3
      },
      "decision": "KEEP_RAW_DO_NOT_START_K1_T02",
      "first_Graph_failure": "PRESERVED_RESERVED_UNKNOWN_AND_MISSING_ACTUAL_NODE_PARAMETERS",
      "source_tree": "41a913488b0138fe868a8321d2f6a86ce83e313f",
      "freeze_sha256": "29c89db3f440cea8b8620e0728dd9220c7c3366782fbc408b283e5aedd9e0969",
      "original_artifacts": [
        {
          "path": "output/ninfer-v4-k1-graph-r2-20261023/final-summary.json",
          "sha256": "0adf7f1c901b800c4cdffcdad18664cb850c53b267083492d625f888055a6077"
        },
        {
          "path": "output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/native-summary.json",
          "sha256": "a35f6e488bc2d0aa9762ffb4eaa74ca95cba468ae1ccf522cc4754491ed9a292"
        },
        {
          "path": "output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/budget-ledger.json",
          "sha256": "e8b2264f00b5cec7e6afa72503f8c1bfc04a00e788f5bfe65ef271e45f7215b8"
        },
        {
          "path": "output/ninfer-v4-k1-hardware-20261023/final-summary.json",
          "sha256": "a45a641d32e7823f00ae123a9d35a25e94d987eb6033f7076aba200e1bcb5b25"
        }
      ],
      "report": "../../ninfer-v4-post-k1-selection-20261023.md"
    },
    "K2_T05_selection": {
      "status": "NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED",
      "task": "K2-T05",
      "profile": "SM89_GDN_PREFILL_C10240_SPLIT_QKV_T65_T128_T512_T1024_V1",
      "candidate_scope": "prefill_conv_split_candidate",
      "hypothesis": "Write ordinary prefill convolution BF16 results directly into contiguous Q/K/V outputs, eliminating qkv_c write/read and 3 D2D extraction operations.",
      "source_tree": "41a913488b0138fe868a8321d2f6a86ce83e313f",
      "source_root": "/home/hhtele/ninfer-v4-k1-graph-r2-20261023/source",
      "source_verification": "12 files matched live jssh 29 and persistent local witness bytes",
      "production_prefill_chunk": 1024,
      "dimensions": {
        "C": 10240,
        "Q": 2048,
        "K": 2048,
        "V": 6144,
        "GDN_layers": 48
      },
      "scope": {
        "first_patch": "BENCH_ONLY_NO_PRODUCT_DEFAULT_DISPATCH_CHANGE",
        "phase": "ordinary nonsegmented Prefill only",
        "tokens": "T>64 and <=1024 for this profile",
        "dtype": "BF16 input/weights/outputs/conv state; FP32 accumulation",
        "alignment_bytes": 4,
        "implementation": "Reuse pairs arithmetic and BF16 rounding, change only final output address mapping; preserve separate state update kernel and stream ordering.",
        "state_cases": "Four numeric cases cover same-address and separate input/output state, nonzero history, finite data, guards and immutable inputs.",
        "oracle": "Extract/reuse unique existing FP64 causal_conv_oracle and existing tolerances; bitwise compare full BF16 Q/K/V and conv state independently.",
        "excluded": [
          "decode and T<=64",
          "Verify/snapshot/segmented routes",
          "MTP policy or Target sampling",
          "workspace arena reuse/removal",
          "new weights/codecs",
          "product runtime integration",
          "old suites or Baseline reruns"
        ]
      },
      "theoretical_logical_traffic": {
        "T": 1024,
        "intermediate_payload_bytes": 20971520,
        "removed_write_plus_read_bytes_per_layer": 41943040,
        "removed_write_plus_read_bytes_48_layers": 2013265920,
        "final_QKV_write_retained": true,
        "actual_HBM_bytes": null,
        "allocator_or_peak_memory_saving": null
      },
      "proposed_budget": {
        "numeric_scenarios_max": 4,
        "numeric_T": [
          65,
          128,
          512,
          1024
        ],
        "direct_Op_max": 20,
        "direct_algorithm_kernel_max": 16,
        "Graph_shapes": [
          512,
          1024
        ],
        "Graph_routes": [
          "raw",
          "split"
        ],
        "Graph_capture_max": 4,
        "Graph_correctness_replays_max": 8,
        "Graph_warmup_replays_max": 16,
        "Graph_timing_replays_max": 160,
        "Graph_total_replays_max": 184,
        "algorithm_kernel_executions_max": 384,
        "expected_baseline_Graph_copy_operations": 276,
        "host_extract_calls_direct": 12,
        "host_extract_calls_capture": 6,
        "auxiliary_compute_kernel_max": 0,
        "helper_transfers_counts_and_bytes": null,
        "helper_transfer_gap": "Driver not implemented. Enumerate reset/guards/exports H2D/D2D/D2H calls and bytes before a GPU freeze; null is not unlimited.",
        "model_submissions_max": 0,
        "HTTP_wire_max": 0,
        "GPU_expected_minutes": [
          2,
          5
        ],
        "GPU_hard_minutes": 10,
        "cleanup_start_minute": 7
      },
      "CPU_contracts_max": 16,
      "engineering_hours": [
        8,
        16
      ],
      "timing_contract": {
        "segment": "Output convolution + state update + baseline three extraction copies versus split-output convolution + unchanged state update",
        "method": "CUDA-event segment measurement; fixed graph replay batches, AB/BA 5 paired batches x8; reset/check/transfers outside timed range, host wall separately; do not infer pure kernel gain from host gap.",
        "known_unknown": "Host dispatch bubbles may still influence event duration; report event and host wall separately, inconclusive if unstable, no unbudgeted extra repetitions.",
        "Graph_witness": "Freeze expected two algorithm nodes per graph and 3 raw copies/0 candidate copies; actual post-capture node types/identity/geometry/copy parameters must be checked on GPU; unexpected hidden nodes fail closed.",
        "timing_shape_scope": [
          512,
          1024
        ]
      },
      "signal_gate": {
        "segment_median_gain_min": 0.1,
        "faster_paired_batches_min": 4,
        "paired_batches": 5,
        "all_bitwise_guards_oracle_required": true,
        "adoption": "SEGMENT_SIGNAL_NOT_K4",
        "failure_or_no_signal": "STOP_KEEP_ORIGINAL_NO_AUTOMATIC_MORE_TESTS",
        "end_to_end_gain": null,
        "full_prefill_and_Chat_qualification": "SEPARATE_FUTURE_AUTHORIZATION_NOT_DEVELOPMENT_PREREQUISITE"
      },
      "alternatives": {
        "Lookup": "Possible decode benefit, especially Pi; lower priority until actual token hit evidence and full fused-prefix/state cost are established. Existing greedy proposal + Target exact sampling is already implemented.",
        "workspace": "No current allocator high-water/capacity attribution, first patch does not alias arenas.",
        "Q4_Q5": "Existing MMA/split-K paths exist; no isolated hotspot timing identifying a better first change.",
        "K1_K2_C0": "Closed; no more tests and no product integration inferred."
      },
      "preserved": [
        "18 G1 differences",
        "C1 attachment gap",
        "all failures and missing attachments",
        "Baseline original 278/28/250 and rejected/gap distinctions",
        "sampling/context/Pi medium/32768",
        "original GPU service STOPPED_DO_NOT_RESTORE"
      ],
      "new_execution_this_selection": {
        "product_tests": 0,
        "builds": 0,
        "GPU_Op": 0,
        "model_requests": 0,
        "HTTP": 0,
        "graders": 0,
        "remote_source_edits": 0,
        "production_changes": 0
      },
      "authorization": "READ_ONLY_SELECTION_AND_LOCAL_DOCUMENTATION_ONLY; implementation and GPU execution require their own user scope",
      "p95": null,
      "optimization_qualification": false
    },
    "K2_T05_CPU_implementation": {
      "status": "CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN",
      "task": "K2-T05",
      "profile": "SM89_GDN_PREFILL_C10240_SPLIT_QKV_T65_T128_T512_T1024_V1",
      "base_tree": "41a913488b0138fe868a8321d2f6a86ce83e313f",
      "candidate_tree": "3ea537c00c759ef2a4577b525ae691f694ae102e",
      "branch": "codex/k2-prefill-split-20261023",
      "freeze_sha256": "7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc",
      "probe_sha256": "b1679dd61eee7eae0a3990129f32a0e8a0af8262fdb23e43d10dbef49aea7c19",
      "prepared_root": "/home/hhtele/ninfer-v4-k2-t05-20261023/prepared-window-r1",
      "CPU_contract_scenarios_passed": {
        "CPP_Graph_metadata": 8,
        "Python_orchestration": 8,
        "total": 16
      },
      "BO_build": "PASS_RELEASE_CUDA13.2_SM89_27B_ONLY_RUNC_NO_GPU_NETWORK_MAX4",
      "initial_build_failure_preserved": "CUDA13.2 Graph dependency API: two old 3-argument calls corrected to 4 arguments; build-r1 exit1 retained; build-r2 PASS",
      "review_status": "PASS_AFTER_FIX",
      "review_fixes": [
        "Default-stream reset synchronized before nonblocking Graph replay outside timing",
        "Candidate exit!=0 persists result and fails controller",
        "CPU metadata terminology corrected",
        "CUDA13.2 dependency query API signature fixed"
      ],
      "source_preservation": "Raw FP32 accumulation helper, raw output kernel, state kernel, default launcher and FP64 oracle body/criterion unchanged; default wrapper/runtime unchanged",
      "future_GPU_budget": {
        "numeric_scenarios": 4,
        "direct_ops": 20,
        "captures": 4,
        "replays": 184,
        "algorithm_kernels": 384,
        "model_submissions": 0,
        "wire": 0
      },
      "future_transfer_limits": {
        "d2d_bytes": 7929856,
        "d2d_calls": 128,
        "d2h_bytes": 5386141696,
        "d2h_calls": 768,
        "h2d_bytes": 4447860736,
        "h2d_calls": 508
      },
      "future_segment_copy_limits": {
        "capture_calls": 6,
        "direct_calls": 12,
        "replay_nodes": 276
      },
      "future_replay_breakdown": {
        "correctness": 8,
        "warmup": 16,
        "timing": 160
      },
      "future_GPU_minutes": {
        "expected": [
          2,
          5
        ],
        "hard": 10,
        "cleanup": 7
      },
      "current_ledger_status": "PRISTINE",
      "all_current_GPU_counters_zero": true,
      "current_runtime_exists": false,
      "new_GPU_Op_model_HTTP": 0,
      "actual_GPU_bitwise_Graph_and_performance": "NOT_RUN",
      "p95": null,
      "optimization_qualification": false,
      "original_service": "STOPPED_DO_NOT_RESTORE",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "closed_tasks_additional_budget": {
        "C0": 0,
        "K2_T01": 0,
        "K1_T01": 0
      },
      "GPU_execution_requires_new_authorization": true
    },
    "K2_T05_GPU_screen": {
      "status": "GPU_MIN_SCREEN_COMPLETED_T1024_SIGNAL_T512_TIMING_INCONCLUSIVE",
      "task": "K2-T05",
      "profile": "SM89_GDN_PREFILL_C10240_SPLIT_QKV_T65_T128_T512_T1024_V1",
      "source_tree": "3ea537c00c759ef2a4577b525ae691f694ae102e",
      "freeze_sha256": "7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc",
      "probe_sha256": "b1679dd61eee7eae0a3990129f32a0e8a0af8262fdb23e43d10dbef49aea7c19",
      "numeric_unique_T": [
        65,
        128,
        512,
        1024
      ],
      "numeric_bitwise_QKV_BF16_state_original_FP64_guard": "PASS",
      "Graph_capture_actual": "4_PASS_RAW_2_KERNEL_3_COPY_SPLIT_2_KERNEL",
      "Graph_actual_kernel_arguments_geometry_copy_dependencies": "PASS",
      "Graph_correctness_warmup_and_timing_bitwise": "PASS",
      "actual_counts": {
        "numeric_scenarios": 4,
        "direct_ops": 20,
        "captures": 4,
        "replays": 184,
        "algorithm_kernels": 384,
        "model_submissions": 0,
        "wire": 0
      },
      "replay_breakdown": {
        "correctness": 8,
        "warmup": 16,
        "timing": 160
      },
      "measurements": [
        {
          "tokens": 512,
          "raw_event_median_us": 36.18000075221062,
          "split_event_median_us": 22.784000262618065,
          "median_paired_improvement_fraction": 0.3844112872792871,
          "faster_batches": 5,
          "total_batches": 5,
          "host_gate_failed_batches_zero_based": [
            1,
            2,
            3
          ],
          "host_submit_event_ratios": [
            {
              "raw": 0.09544983217804374,
              "split": 0.1057100839871311
            },
            {
              "raw": 0.17821567604360877,
              "split": 0.34806380747843063
            },
            {
              "raw": 0.23085414412489066,
              "split": 0.26901004781219723
            },
            {
              "raw": 0.06382812534585934,
              "split": 0.31970884197683613
            },
            {
              "raw": 0.22884764538032012,
              "split": 0.10269622896433198
            }
          ],
          "segment_signal": false,
          "status": "TIMING_INCONCLUSIVE_HOST_SUBMISSION_GATE"
        },
        {
          "tokens": 1024,
          "raw_event_median_us": 64.0840008854866,
          "split_event_median_us": 40.70400074124336,
          "median_paired_improvement_fraction": 0.36483365303645104,
          "faster_batches": 5,
          "total_batches": 5,
          "host_gate_failed_batches_zero_based": [],
          "host_submit_event_ratios": [
            {
              "raw": 0.05027640301824746,
              "split": 0.05636867256964818
            },
            {
              "raw": 0.0372844404558225,
              "split": 0.07289875098459063
            },
            {
              "raw": 0.050663971586320015,
              "split": 0.05982827131615298
            },
            {
              "raw": 0.037262088135620014,
              "split": 0.07772131406075924
            },
            {
              "raw": 0.13583303816843495,
              "split": 0.05752476866687103
            }
          ],
          "segment_signal": true,
          "status": "SEGMENT_SIGNAL_NOT_K4"
        }
      ],
      "timing_scope": "Convolution output + unchanged state update + raw three D2D extracts; CUDA-event segment with host submission reported; no full GDN layer/prefill/model/Chat gain claim",
      "native_qualification": "SEGMENT_SIGNAL_ONE_SHAPE_NOT_K4",
      "transfer_used": {
        "d2d_bytes": 2725888,
        "d2d_calls": 44,
        "d2h_bytes": 1153720320,
        "d2h_calls": 240,
        "h2d_bytes": 1134373888,
        "h2d_calls": 214
      },
      "transfer_limits": {
        "d2d_bytes": 7929856,
        "d2d_calls": 128,
        "d2h_bytes": 5386141696,
        "d2h_calls": 768,
        "h2d_bytes": 4447860736,
        "h2d_calls": 508
      },
      "segment_copy_used": {
        "capture_calls": 6,
        "direct_calls": 12,
        "replay_nodes": 276
      },
      "ledger": "COMPLETE",
      "unresolved_reservations": 0,
      "controller_wall_seconds": 6.766933801001869,
      "cleanup_seconds_from_launch": 6.701097593992017,
      "cleanup_limit_seconds": 420,
      "hard_limit_seconds": 600,
      "original_service": "STOPPED_IDENTITY_UNCHANGED",
      "GPU_idle": true,
      "GPU_lease_free": true,
      "window_consumed": true,
      "additional_GPU_budget": 0,
      "product_default_dispatch": "UNCHANGED",
      "product_integration_authorized": false,
      "sampling_context_Pi": "UNCHANGED_MEDIUM_32768",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "old_failures": "PRESERVED_NO_RERUN",
      "p95": null,
      "optimization_qualification": false,
      "full_prefill_and_Chat_gain": null,
      "new_unknown_outcomes": false,
      "archive": {
        "status": "IMMUTABLE_HARDWARE_EVIDENCE_ARCHIVED",
        "archive": "/home/hhtele/ninfer-v4-k2-t05-20261023/k2-t05-hardware-r1-evidence.tar.gz",
        "bytes": 299737,
        "sha256": "aae1f54f298327f20c4c7b409ab6e3cdabecf5c1fde738714265777263c6a98c",
        "freeze_sha256": "7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc",
        "source_tree": "3ea537c00c759ef2a4577b525ae691f694ae102e",
        "original_service": "STOPPED",
        "ledger": "COMPLETE",
        "actual_counts": {
          "algorithm_kernels": 384,
          "captures": 4,
          "direct_ops": 20,
          "model_submissions": 0,
          "numeric_scenarios": 4,
          "replays": 184,
          "wire": 0
        },
        "GPU_idle": true
      }
    },
    "K2_T05_T1024_prefill_integration": {
      "status": "T1024_PREFILL_INTEGRATED_CPU_BUILD_REVIEWED_GPU_NOT_RUN",
      "branch": "codex/k2-t05-prefill-integration-20261023",
      "HEAD": "e0b05f7cb46adae2787be2ccbe605e1b0c9b3923",
      "base_tree": "3ea537c00c759ef2a4577b525ae691f694ae102e",
      "candidate_tree": "9818eafa5d2660c2ea9682cc7653e6603f21ebb5",
      "changed_files": {
        "tests/CMakeLists.txt": "5b347842112d84a7163d7215a4331d3d0dd286141137d1722b80cb1cbc81c412",
        "tests/test_k2_prefill_integration.cpp": "3d6e121b358c43e85478183b3716f3f55371e4952b0d53249c550e8c5ecfc1c0",
        "src/ops/launcher/causal_conv1d.h": "6d054c17793a4182f5c6c8c775c25d6b2d29801a6b63134d7094824f9c3f687c",
        "src/ops/launcher/causal_conv1d.cu": "99d64faca91cae958f7d995ae1c87a195023ef52c3f028d8e34e418dfbbb46f3",
        "src/ops/launcher/k2_prefill_split.h": "f45f8d268a4ca0287a4bf43e741ec85cba3565ccc4edff843b950de69bcda4fa",
        "src/ops/wrapper/causal_conv1d_silu.cpp": "7e42b408296b1eb2bb2bc083e9e25c48540599563ca1fefc3adaff1078d5daab",
        "src/targets/qwen3_8/impl/runtime/gdn_convolution.h": "9fbf85c958b27ab9b095a93c60d42fff67ab13542ea26bccfb888411b0c2ecaa",
        "src/targets/qwen3_8/impl/runtime/text_context_impl.h": "b9c3c4ffd36119f70c23d98508ae7a395c84b3e13daea7c1e88fda8590150564",
        "include/ninfer/ops/causal_conv1d_silu.h": "6bfbdcb89ed38b2ea1c34a7f167a48f841a3537b60775d1ba4210f8b29a0743d",
        "bench/ops/k2_prefill_split_probe.cu": "67415a04ae86d379e92dc28bc4bc5f9fb40368005add28fc16fb89052f4d2783"
      },
      "unchanged_base_files_verified": 1255,
      "kernel_file_sha256": "9ea1a7b6cdf09f933e3b1b58209efa30b495eecbe986c69740a133261e4cbd5a",
      "FP64_reference_sha256": "2c3374537745477d4e26833a40936729058fdec62ed8bdab23488ceab0d9212c",
      "split_launcher_body_unchanged": true,
      "raw_wrapper_bodies_unchanged": true,
      "BO_image": "sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251",
      "binaries": {
        "build/apps/ninfer-serve": "9eec3fab2477d698c539e033899d59cd916b543c7672eaf9c9511eba2d00e063",
        "build/bench/ninfer_k2_prefill_split_probe": "5742a8cb4e3a14c967ba2855d61562c2cea3a251b8abf33fd180c54d3cbb1637",
        "build/tests/ninfer_k2_prefill_integration_cpu_test": "68445d8a41139733f64a7eee66f8fad89c191416b58a4007243385bfaaafd262"
      },
      "CPU_unique_scenarios": 16,
      "CPU_executions": 2,
      "second_execution_reason": "Review added exact Q/K/V address forwarding assertions; only the changed CPU target rebuilt and rerun",
      "prior_tests_executed": false,
      "GPU_model_HTTP_executed": 0,
      "patch_sha256": "07dd225acb8a119c8376d695e7197525005a98155c72528ac3f7f45891808749",
      "original_service": "STOPPED_DO_NOT_RESTORE",
      "production_sampling_context_Pi_unchanged": true,
      "p95": null,
      "optimization_qualification": false,
      "source_commit_created": false,
      "freeze_sha256": "99b44b0a2d3bc0eec40c342a29827bdaba16f0c1373b69523fcb707a51ff2f61",
      "archive_sha256": "aa93ab02f9b3134bc903ad26d313c0d40cac681bc198705eee57823d468692ad",
      "review_status": "PASS_AFTER_FIX_SELF_INTEGRATION_REVIEW",
      "runtime_route": "NONSEGMENTED_PREFILL_C10240_Q2048_K2048_V6144_EXACT_T1024_ONLY",
      "new_CPU_unique_scenarios": 16,
      "T512_additional_tests": 0,
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "prior_Baseline_Op_numerical_Graph_campaigns_rerun": false,
      "future_validation": {
        "status": "PROPOSED_ONLY_DRIVER_NOT_FROZEN_GPU_NOT_AUTHORIZED",
        "order": "raw source 3ea537c00c759ef2a4577b525ae691f694ae102e then new T1024 integration source; isolated processes only",
        "native_full_prefill": {
          "unique_scenarios": 1,
          "prompt_tokens": 8193,
          "full_chunks_expected": 8,
          "tail_tokens_expected": 1,
          "warmup_per_variant": 1,
          "measured_per_variant": 5,
          "total_prefill_iterations": 12,
          "state_and_logits_comparison": "export first measured iteration outside timing; compare all GDN FP32 state, BF16 conv history, logical attention KV and logits, not nondeterministic envelope bytes",
          "sampling": "prefill only, no synthetic greedy sampling replacement",
          "route_witness": "actual launch witness in diagnostic driver; candidate 384 split launches per iteration (8 x 48), raw zero; tail stays raw",
          "evidence_reused": "old Op numeric, FP64, Graph; no T512 or old standalone Op campaign"
        },
        "chat_completions": {
          "unique_cases": [
            "long-prefix streaming text",
            "long-prefix streaming named tool_choice JSON arguments"
          ],
          "measured_requests_per_variant": 2,
          "measured_requests_total": 4,
          "warmup_submissions_total": 2,
          "readiness_wire_total": 2,
          "wire_total_including_warmup": 8,
          "measurements": [
            "server full prefill time",
            "client TTFT",
            "server first token time",
            "raw SSE",
            "resolved sampling",
            "request IDs and cache outcomes"
          ],
          "policy": "same production sampler and medium reasoning; fresh validation workload, not Pi; existing Pi output32768 unchanged; fixed bodies and token lengths must be frozen before execution"
        },
        "total_model_work_units_including_native_prefill_and_warmup": 18,
        "native_prefill_units": 12,
        "HTTP_model_submissions_including_warmup": 6,
        "wire_total": 8,
        "direct_standalone_Op_tests": 0,
        "T512_additional_tests": 0,
        "new_capture_replay_algorithm_kernel_transfer_limits": null,
        "enumeration_gap": "full-model Graph capture/replay and helper transfers depend on actual frozen driver and existing engine warmup; enumerate and freeze before requesting GPU execution, no unbounded implicit budget",
        "context": 262144,
        "prefill_chunk": 1024,
        "continuation_cache": "off in isolated validation process; original directory untouched",
        "prefix_reuse": false,
        "capacity_failure": "stop and preserve evidence, do not lower context or silently retry",
        "proposed_GPU_minutes": {
          "expected": [
            8,
            15
          ],
          "hard": 20,
          "cleanup_start": 17
        },
        "driver_and_budget_preparation_engineer_hours": [
          3,
          5
        ],
        "analysis_hours_after_execution": [
          0.5,
          1
        ],
        "full_prefill_signal": "all payload/state checks pass; median prefilling improvement >=1%, >=4/5 matched ordinal comparisons faster, no matched regression >3%; ordered cohorts are not AB/BA interleaving",
        "Chat_signal": "two functional checks per variant must pass; four measured requests establish smoke behavior only, no p95 or population TTFT speedup claim",
        "failure_or_no_signal": "preserve full evidence and keep raw as release default, no automatic budget addition",
        "segment_only_estimate_ms_per_full_chunk": 1.12224,
        "estimate_limit": "(64.084-40.704)us x48; different median estimators, not measured full-model savings, no promised percent",
        "production_service": "KEEP_STOPPED",
        "optimization_qualification": false,
        "p95": null
      }
    },
    "K2_T05_full_prefill_preparation": {
      "status": "CPU_BUILD_REVIEWED_FULL_PREFILL_CHAT_PREPARED_GPU_NOT_RUN",
      "candidate_tree": "abc974d38d861c4fa72692345aadfc8565624fa3",
      "raw_tree": "a5ba33de12d75ab1e16a153020e4068094ee1757",
      "prepared_root": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-window-r2",
      "freeze_sha256": "4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d",
      "binaries": {
        "raw": {
          "native": "2a24425b7d9684c25ab5b7e17b4a130b3c41e628ba96775da82f01593bac2768",
          "server": "ce4f0a2b1e43edad2cf414253de1d979057527cffdb7cd6635e6d5676bd061f8"
        },
        "candidate": {
          "native": "182f92e1d3ae97ac9c1fcccb05ff5fe323e45cac9f1c639e830874fe98b1a665",
          "server": "472844774df9856d31fb683a6716cb59c073de5d7b3dbb3c8dff571991f299a3"
        }
      },
      "budget": {
        "native_prefill": 12,
        "chat": 4,
        "HTTP_warmup": 2,
        "wire": 8
      },
      "model_work_units": 18,
      "GPU_global_limits": {
        "algorithm_kernels": 35651584,
        "captured_copy_calls": 2097152,
        "captured_kernel_calls": 3145728,
        "captures": 256,
        "d2d_bytes": 4535485464576,
        "d2d_calls": 2228224,
        "d2h_bytes": 68719476736,
        "d2h_calls": 393216,
        "direct_kernels": 3145728,
        "h2d_bytes": 274877906944,
        "h2d_calls": 393216,
        "memset_bytes": 274877906944,
        "memset_calls": 196608,
        "replays": 73728
      },
      "cleanup_seconds": 1020,
      "hard_seconds": 1200,
      "current_ledger": "PRISTINE_ALL_ZERO",
      "runtime_exists": false,
      "CPU_unique_scenarios": 29,
      "original_service": "STOPPED_GPU_IDLE",
      "new_GPU_model_HTTP": 0,
      "GPU_execution_authorized": false,
      "p95": null,
      "optimization_qualification": false,
      "revision": "r2",
      "retired_preparation_root": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-window-r1",
      "retired_freeze_sha256": "21dd87cc278b97de600344f14deba4e66bdc3a084a7db171e22cba2d7e7d20f5",
      "old_budget_additive": false,
      "source_identity_sha256": "14d59a21ff9a0504dbaedec7ebaa51c8f0caa767163f69bd65670f921ddad5de",
      "metadata_archive_sha256": "47214575b49fe95d5228cb485d105d200f08725e39b80860560afc28b9ef9003",
      "shared_remote_binary_archive": {
        "status": "IMMUTABLE_PREPARATION_ARCHIVED_GPU_NOT_RUN",
        "archive": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/k2-full-prefill-prepared-cpu-delivery-r2.tar.gz",
        "bytes": 624614966,
        "sha256": "167a4c543d2752d5045096b60d9fe82177b1db9f5bf0e4c7bb9d2b2c32d281e1",
        "freeze_sha256": "21dd87cc278b97de600344f14deba4e66bdc3a084a7db171e22cba2d7e7d20f5",
        "candidate_tree": "b0d33593474879d467bc4fb0a5eefecfc28f5b92",
        "raw_tree": "56cf2e4837f77bb2683401e3785e18e5b8688755",
        "binary_count": 4,
        "current_ledger": "PRISTINE_ALL_ZERO",
        "runtime_exists": false,
        "original_service": "STOPPED_GPU_IDLE",
        "GPU_model_HTTP": 0
      },
      "binary_payload_unchanged_in_r2": true,
      "model_sha256": "eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e",
      "review_status": "PASS_AFTER_FIX_ROOT_REVIEW_NOT_INDEPENDENT",
      "budget_versions_additive": false,
      "T512_additional_tests": 0,
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "old_Baseline_or_passed_GPU_tasks_rerun": false,
      "actual_GPU_validation": "NOT_RUN",
      "expected_GPU_minutes": [
        8,
        15
      ],
      "analysis_hours": [
        0.5,
        1
      ]
    },
    "K2_T05_full_prefill_hardware_r1": {
      "status": "FULL_PREFILL_CHAT_STOPPED_RAW_LOGITS_BUILD_SCOPE_CPU_REPAIRED",
      "report": "docs/ninfer-v4-k2-t05-full-prefill-hardware-20261023.md",
      "evidence": "output/ninfer-v4-k2-t05-full-prefill-hardware-20261023",
      "root": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-window-r2",
      "freeze_sha256": "4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d",
      "candidate_tree": "abc974d38d861c4fa72692345aadfc8565624fa3",
      "raw_tree": "a5ba33de12d75ab1e16a153020e4068094ee1757",
      "failure": "actual target logits capture missing",
      "actual_native_attempts": 1,
      "native_fully_completed_records": 0,
      "native_phase_reserved": 6,
      "native_phase_completed": 0,
      "valid_timing_pairs": 0,
      "new_Chat": 0,
      "HTTP_warmup": 0,
      "HTTP_wire": 0,
      "raw_state_segments": 72,
      "raw_state_bytes": 306659921,
      "original_state_and_logits_metadata_exists": false,
      "original_target_logits_exists": false,
      "final_CUDA_totals": null,
      "final_CUDA_totals_reason": "last durable audit is MODEL_READY before failed prefill",
      "root_ledger_status": "RUNNING_PRESERVED_WITH_RESERVED_PHASE_NOT_AN_ACTIVE_PROCESS",
      "full_state_and_logits_bitwise": "NOT_RUN",
      "full_prefill_gain": null,
      "Chat_TTFT_gain": null,
      "elapsed_to_cleanup_seconds": 61.943788373,
      "failure_evidence_archive_sha256": "f477f2a8bfa1616b8a09b5a5978e7215891c72b626b6ba1f867451ebfe092a7f",
      "CPU_repair": "TARGET_DIRECTORY ninfer_engine; actual compile commands and model object caller references verified",
      "CPU_repair_binaries": {
        "candidate": {
          "native": "8cc216fae114a7beec9ccb0d1c2b9e3eaf8332207ed6078fc18c1f7f0e52ab9a",
          "server": "707e78f6c81d51ebbe8e1b52b9e7ac814930c674734b81a805e4a7ec41267e4d"
        },
        "raw": {
          "native": "dfdb4de2e276aa660331e9a5790d3d57b011a70b293e6d290309214c647ca03b",
          "server": "15940f58088b83a5831f2ec38eee3e62338ea0e536462320d7ada24257e86bc0"
        }
      },
      "CPU_repair_GPU_model_HTTP": 0,
      "repair_GPU_freeze_or_execution": false,
      "window_closed": true,
      "original_service": "STOPPED_IDENTITY_AND_CACHE_UNCHANGED",
      "gpu_idle": true,
      "lease_free": true,
      "sampling_context_Pi_unchanged": true,
      "old_Baseline_or_T512_rerun": false,
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "qualification": "NOT_ACCEPTED_DIAGNOSTIC_DRIVER_FAILURE",
      "p95": null,
      "optimization_qualification": false
    },
    "K2_T05_Chat_remaining_20261024": {
      "status": "CHAT_COMPLETED_4_PASS_NATIVE_SIGNAL_BELOW_THRESHOLD_KEEP_RAW",
      "report": "docs/ninfer-v4-k2-t05-chat-remaining-20261024.md",
      "evidence": "output/ninfer-v4-k2-t05-chat-remaining-20261024",
      "root": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-chat-r4-20261024",
      "freeze_sha256": "b9512345eb6d511d6f242aff465404907ec02dbe8661ec15d6012f0c26ade317",
      "new_budget_used": {
        "native_prefill": 0,
        "chat": 4,
        "HTTP_warmup": 1,
        "wire": 6
      },
      "cumulative_native": 13,
      "native_replayed": false,
      "old_raw_warmup_replayed": false,
      "Chat_pass_count": 4,
      "Chat_measured_count": 4,
      "new_warmup_status": "FAIL_MODEL_BEHAVIOR",
      "old_warmup_status": "FAIL_MODEL_BEHAVIOR",
      "warmup_note": "Exact OK assertion retained; Reply OK. fixture has punctuation ambiguity; both actual outputs OK. remain failures.",
      "native_bitwise": "PASS_BITWISE_REUSED_AND_RAW_HASHES_REVERIFIED",
      "native_paired_median_gain": 0.003139511109142555,
      "native_signal_threshold": 0.01,
      "native_signal": false,
      "TTFT": {
        "text": {
          "raw_seconds": 2.296331834,
          "candidate_seconds": 2.276106725,
          "observed_gain": 0.008807572451220947
        },
        "tool": {
          "raw_seconds": 2.206091377,
          "candidate_seconds": 2.19810808,
          "observed_gain": 0.003618751735867014
        }
      },
      "TTFT_pair_count": 2,
      "stable_TTFT_improvement_proven": false,
      "request_ID_contract": "Authoritative response x-request-id plus server-instance/request/Engine tuple; client operation label stored separately",
      "CPU_new_request_ID_checks": 7,
      "old_passed_test_suites_rerun": false,
      "new_BO_builds": 0,
      "original_service": "STOPPED_IDENTITY_AND_CACHE_UNCHANGED",
      "GPU_idle": true,
      "lease_free": true,
      "unknown_requests": false,
      "elapsed_to_cleanup_seconds": 126.024570944,
      "new_window_finished": true,
      "additional_budget": 0,
      "full_state_archive": {
        "bytes": 477417758,
        "path": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/hardware-r4-complete-state-evidence.tar.gz",
        "sha256": "e828bc57799d095389d0333692bb86ec14917a69a8aae86231feb3d95e0752ee"
      },
      "local_full_state_payload": false,
      "local_new_wire_and_metadata_complete": true,
      "recovered_prior_native_metadata_and_logits": "ORIGINAL_BYTES_FROM_REMOTE_NOT_REGENERATED",
      "first_native_failure_final_GPU_totals": null,
      "first_native_failure_gap": "MODEL_READY checkpoint only; original target logits absent",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "sampling_context_Pi": "UNCHANGED",
      "p95": null,
      "optimization_qualification": false
    },
    "K2_T05_closeout_20261024": {
      "task": "K2-T05",
      "status": "CLOSED_NO_FURTHER_MEASUREMENT",
      "additional_budget": 0,
      "completed_Chat": 4,
      "Chat_PASS": 4,
      "native_cumulative": 13,
      "native_bitwise": "PASS_REUSED",
      "full_prefill_paired_gain": 0.003139511109142555,
      "frozen_adoption_threshold": 0.01,
      "threshold_signal": false,
      "TTFT_observations": {
        "text": 0.008807572451220947,
        "tool": 0.003618751735867014
      },
      "old_failures_and_costs": "PRESERVED",
      "warmup_failures": "PRESERVED_OK_DOT_VS_OK",
      "default_release": "KEEP_RAW",
      "candidate_branch": "RETAINED_AS_EVIDENCE_NOT_PROMOTED",
      "followup_T512_Op_native_Chat_Baseline_grader": 0,
      "p95": null,
      "optimization_qualification": false,
      "prior_artifacts": {
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-k2-t05-chat-remaining-20261024/analysis.json": "aee6643b3325cc265574a0c143714fe73eb14935d8c88d55c1c381dc2404740c",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-k2-t05-chat-remaining-20261024/execution-core.json": "6333bdca25eb010a613a93160737401bc2f0958857f2a72f471c04936f10e9c9",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-k2-t05-chat-remaining-20261024/delivery-validation.json": "c7c00ac9747ea21586c7622cad7b5938345a4f4de73ccad38b3883d158c7b4b1",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-k2-t05-chat-remaining-20261024/DELIVERY-RECEIPT.json": "f2dbe560e941c257446a23e2620b1baab615a427e48730efda7bb015ba27e8a5"
      },
      "original_report": "/Users/luo/Documents/github/CodexGame/docs/ninfer-v4-k2-t05-chat-remaining-20261024.md",
      "original_report_sha256": "5ab63e4b466da8b2c5d68cb875afd4129d70d3c0e6ecfb37310192e0d7328880",
      "report": "docs/ninfer-v4-post-k2-t05-selection-20261024.md"
    },
    "H1_T01_selection_20261024": {
      "task": "H1-T01",
      "status": "NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED",
      "profile": "REQUEST_LOCAL_LOOKUP_PACKET_C1_W4_K3_N4_RING8192_V1",
      "base_root": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/raw-source",
      "base_tree": "a5ba33de12d75ab1e16a153020e4068094ee1757",
      "base_branch": "codex/k2-t05-full-prefill-raw-20261023",
      "proposed_branch": "codex/h1-lookup-packet-c1-w4-20261024",
      "branch_created": false,
      "rationale": "Change proposal quality and Target round count after three kernel/record experiments lacked qualifying whole-request gain; actual Lookup hit rate remains unmeasured.",
      "proposal": {
        "C": 1,
        "W": 4,
        "K_max": 3,
        "ngram": 4,
        "history_ring_tokens": 8192,
        "index_slots": 16384,
        "index_host_bytes_max": 524288,
        "diagnostic_buffer_bytes_max": 262144,
        "selection": "Only when existing extent==3 and a full3-token continuation exists: choose a complete Lookup packet; otherwise preserve the full original MTP packet.",
        "source": "Only current request verified prompt and formally licensed ledger IDs; no rejected drafts or other requests.",
        "injection": "Existing host current_drafts ingress before speculative_prepare_verify_inputs and Target verification.",
        "ownership": "RequestControl owns ephemeral index. Explicit reset at request bind, terminal/clear/error; rebuild after restore. Not retained or serialized with SequenceState.",
        "updates": "Use actual permitted committed count after resolve, never accepted_drafts+1.",
        "preserved": "Original Target sampler/processors/RNG/bonus, W4 Graph, MTP alignment and next proposals, permit/fold/cache formats.",
        "MTP_draft_compute_skipped": false,
        "default_dispatch_changed": false,
        "new_GPU_workspace": false
      },
      "excluded": [
        "partial token-by-token fusion",
        "COPY/proposal skip",
        "new speculative backend",
        "W8/W16",
        "DFlash2",
        "global retrieval",
        "vocabulary trimming",
        "utility scheduler",
        "online tuner",
        "production switch",
        "old task reruns"
      ],
      "CPU": {
        "new_contract_cases_max": 16,
        "cases": [
          "empty history",
          "extent below3 bypass",
          "exact4gram with3 following committed IDs",
          "short following suffix fallback",
          "source end boundary",
          "never read uncommitted future",
          "deterministic latest legal source",
          "hash collision exact token check",
          "ring eviction and wrap",
          "append only final permitted commits",
          "no-hit MTP packet unchanged",
          "remaining1 bypass",
          "remaining2 bypass",
          "new request and lane reset",
          "restore rebuild from verified current prefix",
          "fixed memory and source-index bounds"
        ],
        "BO": "reuse pinned toolchain/deps; affected targets only",
        "new_GPU_model_HTTP_before_separate_execution_authorization": 0
      },
      "proposed_GPU_pilot": {
        "native_state_scenarios_max": 2,
        "native_request_submissions_max": 4,
        "native_decode_or_verify_calls_max": 16,
        "native_scenarios": [
          "Lookup-selected packet equal to MTP: bitwise verify/state/conv and next-step equality",
          "Different Lookup packet with rejection/partial permit: canonical Target-prefix state and next-step consistency"
        ],
        "new_measured_Chat_max": 6,
        "Chat_AB_pairs": 3,
        "HTTP_warmup_max": 2,
        "HTTP_model_submissions_max": 8,
        "wire_max": 10,
        "total_model_work_submissions_max": 12,
        "standalone_old_Op_or_Graph_scenarios": 0,
        "Chat_cases": [
          "new code-copy positive control",
          "new repeated structured tool/code output",
          "new low-repetition control"
        ],
        "context": 262144,
        "Pi_medium_output_budget_unchanged": 32768,
        "new_Chat_fixture_max_tokens": 2048,
        "GPU_resource_envelope": {
          "algorithm_kernels": 35651584,
          "captured_copy_calls": 2097152,
          "captured_kernel_calls": 3145728,
          "captures": 256,
          "d2d_bytes": 4535485464576,
          "d2d_calls": 2228224,
          "d2h_bytes": 68719476736,
          "d2h_calls": 393216,
          "direct_kernels": 3145728,
          "h2d_bytes": 274877906944,
          "h2d_calls": 393216,
          "memset_bytes": 274877906944,
          "memset_calls": 196608,
          "replays": 73728
        },
        "resource_note": "Proposed finite per-window ceiling, not an executable ledger or permission. New driver must enumerate actual capture/replay/kernel/copy paths and freeze all bounds; never reuse a consumed K2 root.",
        "expected_minutes": [
          5,
          10
        ],
        "hard_minutes": 20,
        "cleanup_start_minute": 17,
        "actual_execution_authorized": false
      },
      "adoption": {
        "signal_only": true,
        "positive_case_decode_wall_per_token_reduction_min": 0.05,
        "no_hit_overhead_tolerance_max": 0.01,
        "requires_real_route_hit": true,
        "all_index_update_transfer_verify_alignment_commit_costs_included": true,
        "no_hit_or_no_net_gain": "NO_SIGNAL_KEEP_MTP; no automatic extra fixtures or width increase",
        "Target_distribution_and_full_state_release_qualification": "H1-T07 and K4 remain independent; not a prerequisite for CPU development"
      },
      "expected_gain": null,
      "expected_gain_reason": "No real Lookup hit/acceptance or complete-round overhead measurements exist;5% is a signal threshold, not a forecast.",
      "estimated_engineer_hours": {
        "CPU_patch_BO_targeted_checks_review": [
          12,
          16
        ],
        "driver_and_freeze": [
          4,
          8
        ],
        "total": [
          16,
          24
        ],
        "post_GPU_analysis": [
          0.5,
          1
        ]
      },
      "new_measurements_or_implementation_this_selection": 0,
      "original_service": "KEEP_STOPPED",
      "G1_differences": 18,
      "C1_attachment_gap": "PRESERVED",
      "p95": null,
      "optimization_qualification": false,
      "report": "docs/ninfer-v4-post-k2-t05-selection-20261024.md"
    },
    "H1_T01_CPU_implementation_20261024": {
      "BO_builds_passed": 3,
      "C1_gap": "PRESERVED",
      "CPU16_sha256": "3ce596931dcf2a68c02b0bebdfbb39207ba5490a89da6f39006c391e3605d4c8",
      "CPU_cases": 16,
      "G1_differences": 18,
      "GPU_model_HTTP": 0,
      "all_prepared_payload_files_verified": true,
      "archive": "/home/hhtele/ninfer-v4-h1-t01-20261024/H1-T01-CPU-PREPARATION-EVIDENCE-r3.tar.gz",
      "archive_bytes": 609074332,
      "archive_sha256": "2eec57721f0ff8eec43bd84f231f3c1abcb3f55d81dc21eac591c72f0ba2f59e",
      "freeze_sha256": "716ccfc4e8308f7db34497d8edc6d6705aa1a843370b4efef1f073df42d22eb0",
      "frozen_root": "/home/hhtele/ninfer-v4-h1-t01-20261024/prepared-window-r3",
      "old_evidence_untouched": true,
      "optimization_qualification": false,
      "original_service": "STOPPED_IDENTITY_UNCHANGED",
      "p95": null,
      "patch_sha256": "207eb4988ec4664eef8ac672eca945e0a7119a5bc745e6f9125f35f31fad55af",
      "raw_build_failure_retained": true,
      "review_sha256": "f988f7fcad95d51b8f1b1de7c90df10639c02093de7954252222451d9335f566",
      "source_identity_sha256": "5c236f63dfdffd10b36b59ca733b36039aa18f8e9dd6ed344cdcccb861c92c6d",
      "source_tree": "9e7c0a1f19721d0ba63db362da6d10b5cda7c8e0",
      "status": "COMPLETE_CPU_IMPLEMENTATION_BO_REVIEW_AND_FREEZE_GPU_NOT_RUN",
      "report": "docs/ninfer-v4-h1-t01-20261024.md",
      "review": "root integrated review; not independent",
      "CPU_contract_execution": "16 cases once",
      "minimal_GPU_plan": "NOT_RUN"
    },
    "H1_T01_hardware_20261024": {
      "status": "MINIMAL_STATE_PASS_NO_ADOPTION_SIGNAL_GUARD_CONFLICT",
      "report": "docs/ninfer-v4-h1-hardware-20261024.md",
      "freeze_sha256": "716ccfc4e8308f7db34497d8edc6d6705aa1a843370b4efef1f073df42d22eb0",
      "source_tree": "9e7c0a1f19721d0ba63db362da6d10b5cda7c8e0",
      "native": {
        "cases": [
          {
            "case": 1,
            "next_MTP_equal": true,
            "real_hit": true,
            "same_packet": true,
            "same_prefix": true,
            "state_equal": true,
            "status": "PASS_BITWISE",
            "terminal_partial_observed": true,
            "verify_equal": true
          },
          {
            "case": 2,
            "next_MTP_equal": null,
            "real_hit": true,
            "same_packet": false,
            "same_prefix": true,
            "state_equal": true,
            "status": "PASS_BITWISE",
            "terminal_partial_observed": false,
            "verify_equal": true
          }
        ],
        "status": "PASS_BITWISE"
      },
      "Lookup": {
        "rounds": 128,
        "eligible": 128,
        "hits": 47,
        "accepted": 122,
        "drafted": 141,
        "committed": 169,
        "hit_rate": 0.3671875,
        "acceptance_rate": 0.8652482269503546
      },
      "pairs": [
        {
          "case": "copy",
          "server_decode_per_reported_token_cost_increase": 0.06982226681300241,
          "observed_round_wall_per_committed_token_cost_increase": 0.07202678746549052,
          "no_hit_control_qualified": false,
          "quality_pair_valid": false,
          "frozen_5_percent_gain_signal": false,
          "raw_committed_per_round": 3.8796992481203008,
          "candidate_committed_per_round": 3.6231884057971016,
          "hypothetical_constant_round_cost_time_gain_ceiling": 0.03007518796992481,
          "ceiling_assumptions": "same token trajectory and round cost, each round can commit at most4; a bound, not observed gain"
        },
        {
          "case": "tool",
          "server_decode_per_reported_token_cost_increase": 0.04284889373580114,
          "observed_round_wall_per_committed_token_cost_increase": 0.042948472591263886,
          "no_hit_control_qualified": false,
          "quality_pair_valid": false,
          "frozen_5_percent_gain_signal": false,
          "raw_committed_per_round": 3.9444444444444446,
          "candidate_committed_per_round": 3.7837837837837838,
          "hypothetical_constant_round_cost_time_gain_ceiling": 0.01388888888888884,
          "ceiling_assumptions": "same token trajectory and round cost, each round can commit at most4; a bound, not observed gain"
        },
        {
          "case": "control",
          "server_decode_per_reported_token_cost_increase": 0.08109475267974786,
          "observed_round_wall_per_committed_token_cost_increase": 0.07661705137054531,
          "no_hit_control_qualified": false,
          "quality_pair_valid": true,
          "frozen_5_percent_gain_signal": false,
          "raw_committed_per_round": 3.1875,
          "candidate_committed_per_round": 2.9545454545454546,
          "hypothetical_constant_round_cost_time_gain_ceiling": 0.203125,
          "ceiling_assumptions": "same token trajectory and round cost, each round can commit at most4; a bound, not observed gain"
        }
      ],
      "quality": {
        "new_Chat_PASS": 2,
        "new_Chat_guard_truncated": 4,
        "warmup_PASS": 2,
        "original_FAILURE_records_preserved": true,
        "reason": "Engine repetition_cycle maps to Chat length; repeated positive fixtures conflict with unchanged existing guard. Do not relabel as raw model-quality failure or grant PASS."
      },
      "used": {
        "HTTP_warmup": 2,
        "chat": 6,
        "native_requests": 4,
        "wire": 10
      },
      "native_calls": 6,
      "resource_actual": {
        "algorithm_kernels": 303561,
        "captured_copy_calls": 4896,
        "captured_kernel_calls": 29016,
        "captures": 36,
        "d2d_bytes": 6726602752,
        "d2d_calls": 4978,
        "d2h_bytes": 704411952,
        "d2h_calls": 1123,
        "direct_kernels": 30327,
        "h2d_bytes": 71607687220,
        "h2d_calls": 4880,
        "memset_bytes": 4970159588,
        "memset_calls": 50464,
        "replays": 339
      },
      "elapsed_to_cleanup_seconds": 250.301079047,
      "runtime_complete": true,
      "unresolved": 0,
      "additional_budget": 0,
      "original_service": "KEEP_STOPPED",
      "full_archive": {
        "bytes": 635290233,
        "path": "/home/hhtele/ninfer-v4-h1-t01-20261024/H1-T01-hardware-r3-runtime-complete.tar.gz",
        "sha256": "3a824214d966f9e034c3f54d1b14b6eaf3f463a84dec6098c7f0ea5af034c952"
      },
      "metadata_archive": {
        "bytes": 5871680,
        "path": "/home/hhtele/ninfer-v4-h1-t01-20261024/H1-T01-hardware-r3-metadata.tar.gz",
        "sha256": "e4f049099340d3f53cb1dfcd06fa1be76aeec2e38f85b47e66184f56dcada487"
      },
      "p95": null,
      "optimization_qualification": false
    },
    "H1_T01_closeout_20261024": {
      "task": "H1-T01",
      "status": "CLOSED_NO_FURTHER_MEASUREMENT",
      "authority": "User explicitly closed H1-T01 on2026-10-24; no further measurement",
      "additional_budget": 0,
      "adopted": false,
      "qualification": false,
      "used": {
        "HTTP_warmup": 2,
        "chat": 6,
        "native_requests": 4,
        "wire": 10
      },
      "native": {
        "cases": [
          {
            "case": 1,
            "next_MTP_equal": true,
            "real_hit": true,
            "same_packet": true,
            "same_prefix": true,
            "state_equal": true,
            "status": "PASS_BITWISE",
            "terminal_partial_observed": true,
            "verify_equal": true
          },
          {
            "case": 2,
            "next_MTP_equal": null,
            "real_hit": true,
            "same_packet": false,
            "same_prefix": true,
            "state_equal": true,
            "status": "PASS_BITWISE",
            "terminal_partial_observed": false,
            "verify_equal": true
          }
        ],
        "status": "PASS_BITWISE"
      },
      "quality": {
        "new_Chat_PASS": 2,
        "new_Chat_guard_truncated": 4,
        "warmup_PASS": 2,
        "original_FAILURE_records_preserved": true,
        "reason": "Engine repetition_cycle maps to Chat length; repeated positive fixtures conflict with unchanged existing guard. Do not relabel as raw model-quality failure or grant PASS."
      },
      "raw_failure_labels_unchanged": true,
      "prior_artifacts": {
        "/Users/luo/Documents/github/CodexGame/docs/ninfer-v4-h1-hardware-20261024.md": "7005cc2653fd448b00ff82ad7bbcc17e931285619c5eacb3c20b67d9cfcdb9af",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-h1-t01-hardware-20261024/analysis.json": "fed03094749927ebfcd8ca72a29122e0126ac252ab1de181a3024d0c9707ffd6",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-h1-t01-hardware-20261024/validation.json": "de325dc0403532a1aa709afc0d9efede4ad64175a5a487b1c5035e75641558cb",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-h1-t01-hardware-20261024/DELIVERY-RECEIPT.json": "a4c9e60e8543230e2116bf3a6ebe0edcbf51d2d0b6e048b4b81eb9c011b702eb",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-h1-t01-hardware-20261024/hardware-r3-final-readback.json": "a8879097608b6b2c96e22db53675ebdaefccf5783818c5b5750501558ba22e38",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-h1-t01-hardware-20261024/hardware-r3-archive-receipt.json": "d31a6e1df863132ac89eb5b82836aaf01ca5b9e8cf5672436cb71ad9e49fbc85",
        "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-h1-t01-hardware-20261024/remote/budget-ledger.json": "349982f87915389f6dd684b5257c7d9de41d00ef7b17713039acf42556502e2e"
      },
      "live_readback": "/Users/luo/Documents/github/CodexGame/output/ninfer-v4-post-h1-selection-20261024/remote/live-snapshot.json",
      "all_previous_failures_and_gaps_preserved": true,
      "report": "docs/ninfer-v4-post-h1-selection-20261024.md"
    },
    "H3_T01_existing_W6_selection_20261024": {
      "status": "NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED",
      "task": "H3-T01",
      "stage": "A_EXISTING_W6_PILOT_ONLY",
      "profile": "MTP_EXISTING_C1_W6_K5_VS_W4_K3_V1",
      "base_tree": "a5ba33de12d75ab1e16a153020e4068094ee1757",
      "base_branch": "codex/k2-t05-full-prefill-raw-20261023",
      "proposed_branch": "codex/h3-w6-existing-route-20261024",
      "branch_created": false,
      "proposal": {
        "C": 1,
        "baseline_W": 4,
        "baseline_K": 3,
        "candidate_W": 6,
        "candidate_K": 5,
        "existing_implementation_reused": true,
        "new_W8_support": false,
        "new_kernel": false,
        "Lookup": false,
        "default_dispatch_changed": false,
        "Target_sampling_changed": false,
        "Pi_output_budget": 32768,
        "MTP_alignment_and_next_proposals_retained": true,
        "cache_format_changed": false,
        "full_Target_vocabulary": 248320,
        "optimized_existing_draft_head": 131072
      },
      "CPU": {
        "new_contract_cases_max": 16,
        "cases": [
          "K3 default remains unchanged",
          "Existing K5 accepted; K6/K7 rejected in current MTP",
          "C1/W6 current-draft and next-draft strides5",
          "Verify/rope/licensed dimensions6 and no hidden W4 clamp",
          "Full262144 context and output headroom contract unchanged",
          "Test-only logical-extent0 reference preserves physicalW6",
          "Oracle packet injected before Target verify, never bypasses acceptance",
          "Exact acceptance depths0..5 and licensed1..6",
          "remaining1 clamps commit without reducing requested output",
          "remaining2 clamps commit without reducing requested output",
          "Terminal partial Fold/state/conv/KV transaction",
          "Request reset and cancellation clear diagnostic-only packet",
          "Same positional RNG/sampling processors, Target full vocabulary",
          "Expected unique-code output passes unchanged RepetitionGuard on real tokenizer",
          "Expected unique-row tool JSON passes unchanged RepetitionGuard",
          "Packet override and diagnostic macro absent from ordinary default build"
        ],
        "old_P3_or_Baseline_reruns": 0
      },
      "proposed_GPU_pilot": {
        "actual_execution_authorized": false,
        "new_T6_numeric_scenarios_max": 8,
        "numeric_scenarios": [
          "T6 Q5 residual K6144",
          "T6 Q5 residual K17408",
          "T6 Q4 SwiGLU",
          "T6 attention input projection",
          "T6 GDN input projection",
          "T6 Q6 full Target head N248320/K5120",
          "C1/W6 rk4v4 GQA attention",
          "C1/W6 raw GDN conv Record + recurrent Record + Fold"
        ],
        "numeric_direct_Op_max": 10,
        "numeric_captures_max": 8,
        "numeric_replays_including_warmup_max": 16,
        "numeric_microbenchmark_sweeps": 0,
        "native_state_scenarios_max": 2,
        "native_request_submissions_max": 4,
        "native_decode_or_verify_calls_max": 16,
        "planned_native_calls": 9,
        "native_scenarios": [
          "Same physicalW6 extent0 Target reference6 sequential decode calls; K5 packet taken from first5 real Target IDs; candidate1 fullW6 round accepts5 and permits6; same-prefix logits/state/conv/KV and nextMTP comparison",
          "Same physicalW6 extent0 reference1 call; candidate1 fullW6 packet reusing Target oracle, terminal permit1; compare common-prefix column0 and permitted canonical state; discard unlicensed next drafts"
        ],
        "new_measured_Chat_max": 6,
        "Chat_AB_pairs": 3,
        "HTTP_warmup_max": 2,
        "HTTP_model_submissions_max": 8,
        "health_wire_max": 2,
        "wire_max": 10,
        "total_model_work_submissions_max": 12,
        "model_process_loads_proposed_max": 3,
        "Chat_cases": [
          "Fresh unique-line code fixture, W4/W6 pair",
          "Fresh unique-row named-tool JSON fixture, W4/W6 pair",
          "Fresh low-repetition control, W4/W6 pair"
        ],
        "context": 262144,
        "native_requested_output_tokens": 32768,
        "new_Chat_fixture_max_tokens": 2048,
        "Pi_medium_output_budget_unchanged": 32768,
        "GPU_resource_envelope": null,
        "resource_reason": "Only scenario/direct/capture/replay scopes proposed here. All model startup/capture/replay/algorithm-kernel/copy/memset and byte ceilings must be enumerated by the new driver and frozen before any GPU execution. No executable ledger or implicit resource authorization.",
        "expected_minutes": [
          5,
          10
        ],
        "hard_minutes": 20,
        "cleanup_start_minute": 17
      },
      "estimate": {
        "CPU_BO_driver_review_engineer_hours": [
          8,
          16
        ],
        "GPU_expected_minutes": [
          5,
          10
        ],
        "GPU_hard_minutes": 20,
        "result_analysis_hours": [
          0.5,
          1
        ]
      },
      "adoption_signal": {
        "valid_positive_complete_decode_cost_reduction_min": 0.1,
        "control_regression_max": 0.05,
        "metric": "complete decode wall / actual committed tokens; report service wall and TTFT separately",
        "signal_is_not_qualification": true,
        "formula": "(R6/G6)/(R4/G4); with R6/R4=1.2 and G4=3.9, break-even G6>4.68; 10% time reduction requires G6>=5.2",
        "expected_gain": null
      },
      "independent_qualification": {
        "existing_W8_named_assertions_and_scopes_unchanged": true,
        "W6_pilot_does_not_pass_W8": true,
        "Target_distribution_RNG_cancel_restore_stability_and_release": "PENDING; not a development prerequisite; no candidate or publication qualification claimed"
      },
      "excluded": [
        "No W8/W16 implementation",
        "No H1 rerun or Lookup stacking",
        "No archived norm/correction/T1024 reruns or routing adoption",
        "No new draft head pruning, DFlash2/global retrieval/utility/upstream business features"
      ],
      "new_measurements_or_implementation_this_selection": 0,
      "original_service": "KEEP_STOPPED",
      "G1_differences": 18,
      "C1_gap": "PRESERVED",
      "p95": null,
      "optimization_qualification": false,
      "expected_gain": null,
      "report": "docs/ninfer-v4-post-h1-selection-20261024.md"
    },
    "H3_T01_existing_W6_CPU_preparation_20261024": {
      "CPU11_targeted_revision_pass": true,
      "GPU_global_limits": {
        "algorithm_kernels": 34652160,
        "captured_copy_calls": 1622016,
        "captured_kernel_calls": 2646016,
        "captures": 199,
        "d2d_bytes": 4518305595392,
        "d2d_calls": 2211840,
        "d2h_bytes": 154618822656,
        "d2h_calls": 376832,
        "direct_kernels": 2646016,
        "h2d_bytes": 257698037760,
        "h2d_calls": 376832,
        "memset_bytes": 309237645312,
        "memset_calls": 212992,
        "replays": 69646
      },
      "Pi_output_budget": 32768,
      "base_tree": "a5ba33de12d75ab1e16a153020e4068094ee1757",
      "branch": "codex/h3-w6-existing-route-20261024",
      "budget": {
        "HTTP_warmup": 2,
        "chat": 6,
        "native_requests": 4,
        "wire": 10
      },
      "candidate_tree": "49bee647112ee171de35529028fc271494260751",
      "default_dispatch_changed": false,
      "freeze_sha256": "4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc",
      "ledger": "PRISTINE_ALL_ZERO",
      "named_CPU_scenarios": 16,
      "new_GPU_model_HTTP": 0,
      "new_numeric": {
        "captures": 7,
        "direct_Op": 9,
        "replays": 14,
        "scenarios": 7
      },
      "optimization_qualification": false,
      "original_service": "STOPPED_IDENTITY_UNCHANGED",
      "p95": null,
      "reused_P4_GQA_T6": true,
      "review_open_findings": 0,
      "root": "/home/hhtele/ninfer-v4-h3-w6-20261024/prepared-window-r1",
      "runtime_exists": false,
      "sampling_changed": false,
      "status": "CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN",
      "time": "2026-10-24T08:03:35.287599+00:00",
      "report": "docs/ninfer-v4-h3-w6-stage-a-20261024.md",
      "evidence": "output/ninfer-v4-h3-w6-20261024/remote-final/evidence/preparation-receipt.json"
    },
    "H3_T01_existing_W6_hardware_r1_20261024": {
      "status": "MINIMAL_VALIDATION_INCOMPLETE_DRIVER_WORKSPACE_ZERO_FAILURE",
      "report": "docs/ninfer-v4-h3-w6-hardware-20261024.md",
      "evidence": "output/ninfer-v4-h3-w6-hardware-20261024/analysis.json",
      "freeze_sha256": "4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc",
      "original_ledger_status": "RUNNING",
      "failed_phase": "numeric-chain",
      "full_window_resource_actual": null
    }
  },
  "tasks": [
    {
      "id": "PERF-READY",
      "phase": "ENTRY",
      "kind": "gate",
      "title": "已有P4证据的开发准入，非性能资格",
      "depends_on": [],
      "status": "PENDING",
      "document": "plans/phases/PERF-READY.md",
      "conditions": [
        "P4研究树/BO/模型与原证据身份匹配，原始失败和缺口保留。",
        "完整P0/P6/上游功能/其它协议资格不是开发前置。",
        "每轮实现或GPU请求需对应当次用户授权，原服务保持停止。"
      ]
    },
    {
      "id": "K0-GATE",
      "phase": "K0",
      "kind": "gate",
      "title": "单个实验的归因和预算准入",
      "depends_on": [
        "K0-T04"
      ],
      "status": "PENDING",
      "document": "plans/phases/K0-GATE.md",
      "conditions": [
        "K0调用链、最小归因和选择合同已记录。",
        "仅选择一个主假设及适用的最小预算，不自动启动所有实验。"
      ]
    },
    {
      "id": "K4-QUALIFIED",
      "phase": "K4",
      "kind": "qualification_gate",
      "title": "选中候选隔离资格",
      "depends_on": [
        "K4-T01"
      ],
      "status": "PENDING",
      "document": "plans/phases/K4-QUALIFIED.md",
      "conditions": [
        "选中scope的适用断言通过且证据绑定同一集成候选。",
        "收益/质量/资源合同达标；不等于任何生产部署授权。"
      ]
    },
    {
      "id": "K4-GATE",
      "phase": "K4",
      "kind": "publication_gate",
      "title": "独立生产发布与实际回退门禁",
      "depends_on": [
        "K4-QUALIFIED"
      ],
      "status": "PENDING",
      "document": "plans/phases/K4-GATE.md",
      "conditions": [
        "未来用户明确授权生产操作，冻结原镜像、argv、模型、cache/rollback工件。",
        "候选资格与生产环境差异已验证，发布/实测回退/用户服务交还单独记账。",
        "当前要求原服务停止，不执行启动/发布/回退演练。"
      ]
    },
    {
      "id": "K0-T01",
      "phase": "K0",
      "kind": "task",
      "title": "复用P4身份，定位真实Chat执行链",
      "depends_on": [
        "PERF-READY"
      ],
      "status": "PENDING",
      "optional": false,
      "document": "plans/tasks/K0-T01.md",
      "hypothesis": "把已有可构建P4作为研究起点，避免重新审计或合并全上游。",
      "source_task_ids": [
        "H0-T01",
        "K0-T01",
        "P0-T01",
        "P0-T02"
      ],
      "readiness": "复用证据可做只读核对；当前授权仍仅修订文档。",
      "modify": [
        "源码调用图、现有shape/Graph目录；不新增产品接口"
      ],
      "implementation": [
        "只读核对P4树、模型/codec/BO与已有报告哈希，复用现有构建、G1和实机结果。",
        "追踪纯文本Chat到tokenizer、cache、prefill、proposal/verify/commit，列出真正可达路径及现有采样合同。",
        "列出原始18处G1差异、C1缺口和容量尾轮异常；只有选中改动触及时做定向补证。"
      ],
      "tests": [
        "输入身份不符则停止该候选，不把P5未评审树当P4。",
        "Baseline/P0—P4原始证据不改写、不重复执行。",
        "调用图区分纯文本、媒体与决策分支，不把media-only move优化声称为文本收益。",
        "新记录明确research base与完整资格/生产状态的区别。"
      ],
      "assertion_ids": [
        "CHATPERF-K0-T01-V01",
        "CHATPERF-K0-T01-V02",
        "CHATPERF-K0-T01-V03",
        "CHATPERF-K0-T01-V04"
      ],
      "planned_budget": {},
      "estimated_effort": "1–2工程小时"
    },
    {
      "id": "K0-T02",
      "phase": "K0",
      "kind": "task",
      "title": "最小归因与容量尾轮观测",
      "depends_on": [
        "K0-T01"
      ],
      "status": "PENDING",
      "optional": false,
      "document": "plans/tasks/K0-T02.md",
      "hypothesis": "用一套op/round/service关联定位瓶颈，不重复建设H0/K0观测框架。",
      "source_task_ids": [
        "H0-T02",
        "H0-T03",
        "H0-T04",
        "H0-T05",
        "H0-T06",
        "K0-T02"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "现有trace/请求与job关联；仅缺失的必要观测"
      ],
      "implementation": [
        "先离线分析已完成Baseline/P2/P4证据，不能由decode占比推断GDN或GEMM热点。",
        "若后续获准测量，仅选冷长prefill、warm decode和工具流各一个代表shape，配对同身份；使用已有NVTX/导出。",
        "97fc7be6不重发；在新合成边界场景记录remaining/frontier、main/aux entitlement、ceiling/free pages和finish原因。"
      ],
      "tests": [
        "op、完整round与service wall能关联；不可观测字段为null+原因。",
        "历史context_capacity与SSE length分别保留，不误归因物理OOM。",
        "请求、warmup、代理上游、失败、重试及native迭代都进入同一账本。",
        "不裁剪context或Pi输出，不重发结果未知请求。"
      ],
      "assertion_ids": [
        "CHATPERF-K0-T02-V01",
        "CHATPERF-K0-T02-V02",
        "CHATPERF-K0-T02-V03",
        "CHATPERF-K0-T02-V04"
      ],
      "planned_budget": {
        "wire_max": 12,
        "client_model_requests_max": 8,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 10,
        "gpu_minutes_max": 30,
        "native_shapes_max": 3,
        "native_calls_max": 33,
        "traces_max": 2
      },
      "estimated_effort": "离线1–2小时；后续获准GPU约15–30分钟"
    },
    {
      "id": "K0-T04",
      "phase": "K0",
      "kind": "task",
      "title": "选择一个实验并冻结净收益合同",
      "depends_on": [
        "K0-T02"
      ],
      "status": "PENDING",
      "optional": false,
      "document": "plans/tasks/K0-T04.md",
      "hypothesis": "按可优化份额、投入与资源决定实验，避免把所有研究路线变成必做。",
      "source_task_ids": [
        "K0-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "实验选择/预算/报告桶合同"
      ],
      "implementation": [
        "按归因排序core kernel、workspace、Lookup、上游或高级草稿候选，选一项主假设。",
        "冻结一个candidate scope、固定模型/Target采样、shape、对照、质量/资源门槛及失败止损预算。",
        "复用共同的K4验收；不要求该实验未触及的路线先通过或发布。"
      ],
      "tests": [
        "被选实验有可达路径和总成本假设；无热点/资产时记录不选择原因。",
        "预算是该实验总额，跨任务共享；不把各任务上限相加。",
        "候选资格与生产发布分开，所有新模型/GPU/训练/下载成本都需其对应授权。",
        "采用门槛预先声明，统计不足为INCONCLUSIVE；不把HTTP200或接受率当提速。"
      ],
      "assertion_ids": [
        "CHATPERF-K0-T04-V01",
        "CHATPERF-K0-T04-V02",
        "CHATPERF-K0-T04-V03",
        "CHATPERF-K0-T04-V04"
      ],
      "planned_budget": {},
      "estimated_effort": "1工程小时；在K0总计2–5小时内"
    },
    {
      "id": "K1-T01",
      "phase": "K1",
      "kind": "task",
      "title": "GDN correction记录及独立数值参考",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/K1-T01.md",
      "hypothesis": "减少raw fold的重复点积/归一化/衰减计算，代价是更多store和记录空间。",
      "source_task_ids": [
        "K0-T03",
        "K1-T01",
        "K1-T02"
      ],
      "readiness": "C1/W4/L48 CPU候选、BO、16合同和集成评审已授权完成并冻结；GPU逐bit/Graph/段级首筛未运行，任务资格仍PENDING；K1-T02与发布独立。",
      "modify": [
        "既有GDN helper、typed record布局及对应Op；不改Target/codec"
      ],
      "implementation": [
        "从NInfer当前计算点记录FP32 normalized key、delta、alpha，保留conv记录与当前运算顺序。",
        "复用现有all-layer fold；先保守独立池，记录layout/encoding/Graph fingerprint，不假定可alias。",
        "独立FP64数学参考与raw逐bit参考分开；只覆盖选中C1/W4及边界Op，不把全C/W矩阵挡在首补丁前。"
      ],
      "tests": [
        "verify输出、state和conv逐bit等于同编译配置raw；独立oracle未被修改迁就候选。",
        "有效/无效suffix、count0/1/2/full与尺寸/别名错误受控，不读未写记录。",
        "数学点积、beta舍入、FMA与更新顺序保持；额外store未改变数值路径。",
        "实际记录与峰值显存计入成本；不把统一fold或紧凑记录算新增收益。"
      ],
      "assertion_ids": [
        "CHATPERF-K1-T01-V01",
        "CHATPERF-K1-T01-V02",
        "CHATPERF-K1-T01-V03",
        "CHATPERF-K1-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "estimated_effort": "1–2工程日；与K1-T02共用一次实验预算",
      "selected_profile_budget": {
        "profile": "SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1",
        "budget": {
          "algorithm_kernels": 14308,
          "captures": 6,
          "direct_ops": 784,
          "model_submissions": 0,
          "numeric_scenarios": 8,
          "replays": 276,
          "wire": 0
        },
        "transfer_limits": {
          "d2d_bytes": 19704905728,
          "d2d_calls": 128,
          "d2h_bytes": 30979424768,
          "d2h_calls": 896,
          "h2d_bytes": 3174503944,
          "h2d_calls": 847
        },
        "reference_scope": {
          "independent_fp64_layers": [
            0
          ],
          "layer_distinct_state_and_conv": true,
          "raw_bitwise_layers": 48
        },
        "cleanup_seconds": 720,
        "hard_seconds": 900,
        "authorization": "NOT_AUTHORIZED_PREPARATION_ONLY",
        "historical_planned_budget_is_not_additional_allowance": true
      }
    },
    {
      "id": "K1-T02",
      "phase": "K1",
      "kind": "task",
      "title": "Correction提交事务与整轮净收益",
      "depends_on": [
        "K1-T01"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/K1-T02.md",
      "hypothesis": "只有Verify+Commit整轮和服务净收益成立才采用。",
      "source_task_ids": [
        "K1-T03",
        "K1-T04",
        "K1-T05"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "现有Program许可、fold rows与Graph选择；不新建提交权威"
      ],
      "implementation": [
        "按现有commit_columns/epoch/slot生命周期重放已许可前缀，count0不读state或records。",
        "覆盖取消、stop/尾轮、部分许可、拒绝suffix与restore后的下一轮，失败不二次fold。",
        "确认现网Target sampling实际命中correction；比较raw与correction同shape完整round，包含记录写入。"
      ],
      "tests": [
        "未许可/重复fold/错epoch或slot不修改正式状态，conv推进与原路径一致。",
        "Target sampling、processor、RNG、输出预算不变；只greedy命中不给sampling资格。",
        "整轮计时包含verify、store、同步、fold与fallback；无完整route-hit不给新路径性能结论。",
        "容量与headroom无倒退；双池新增空间照实记账，不因fold更快就采用。"
      ],
      "assertion_ids": [
        "CHATPERF-K1-T02-V01",
        "CHATPERF-K1-T02-V02",
        "CHATPERF-K1-T02-V03",
        "CHATPERF-K1-T02-V04"
      ],
      "planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "estimated_effort": "1–2工程日；GPU pilot约20–45分钟"
    },
    {
      "id": "K2-T01",
      "phase": "K2",
      "kind": "task",
      "title": "一个实测SM89热点的最小kernel实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/K2-T01.md",
      "hypothesis": "针对真实prefill或small-T热点改一个执行形状，不把三个kernel项目串行排满。",
      "source_task_ids": [
        "K2-T01",
        "K2-T02",
        "K2-T03",
        "K2-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "选中的gated norm/GDN preload/Q4-Q5/prefill现有kernel与静态路由"
      ],
      "implementation": [
        "由热点在D128 gated norm的CTA映射、GDN预载、Q4/Q5 small-T或冷prefill中选一个；不重复实现已有融合。",
        "每热点最多三个静态配置，固定SM89和现有权重/scale/数学，保留可回退原路由。",
        "短Op对照后只将赢家纳入完整Graph/round/Chat；GPU型号未匹配不得套用Flare SM120配置。"
      ],
      "tests": [
        "独立数值参考与原算子比较，保持已有精度/数值合同，不为PASS放宽阈值。",
        "Graph捕获与真实route-hit一致，未资格shape保持原路径。",
        "无端到端净收益或资源占用倒退则保留原实现，不能仅报微基准。",
        "不新增codec/权重格式/35B目标资格，不把Ada误写为不支持FP8。"
      ],
      "assertion_ids": [
        "CHATPERF-K2-T01-V01",
        "CHATPERF-K2-T01-V02",
        "CHATPERF-K2-T01-V03",
        "CHATPERF-K2-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "estimated_effort": "0.5–2工程日；pilot约15–45分钟"
    },
    {
      "id": "K2-T05",
      "phase": "K2",
      "kind": "task",
      "title": "普通Prefill卷积直接写连续Q/K/V的最小实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/K2-T05.md",
      "hypothesis": "Write ordinary prefill convolution BF16 results directly into contiguous Q/K/V outputs, eliminating qkv_c write/read and 3 D2D extraction operations.",
      "source_task_ids": [
        "K2-T05"
      ],
      "readiness": "CLOSED_NO_FURTHER_MEASUREMENT; additional budget0, not adopted or promoted.",
      "modify": [
        "隔离候选真实Prefill仅T1024路由接入公开Ops；其他shape/phase/raw和现网保持不变。"
      ],
      "implementation": [
        "family gdn_mix → gdn_convolve_qkv → fixed-shape public Op; C10240/Q2048/K2048/V6144、T1024、非分段Prefill。",
        "复用原split/state kernel和连续QKV workspace，不改数学/FP64/事务/stream/allocator/codec/sampling。",
        "BO Release CUDA13.2 SM89 27B-only build PASS；新增16个唯一CPU合同PASS，主代理集成评审问题已修复。",
        "旧Op数值/Graph证据复用、T512追加0，历史首轮raw导出失败保留；后续完整Prefill逐bit及4Chat已完成，候选/生产门禁独立。"
      ],
      "tests": [
        "完整BF16 Q/K/V输出与conv state逐bit等于raw；复用既有FP64 oracle和阈值，保持pairs数学、FP32累加及BF16舍入。",
        "仅ordinary Prefill C10240、T>64且<=1024及限定对齐可达候选；实际Graph节点身份、几何及copy参数见证通过，其它路由保留原路径。",
        "卷积、state更新和raw三次提取copy完整计入段级对照；算法kernel与辅助传输次数及字节分开记账，净收益不冒充完整Prefill或Chat收益。",
        "无信号、逐bit或资源检查失败即停止并保留原路径；完整Prefill、Chat候选资格与生产发布独立，不自动追加测试。"
      ],
      "assertion_ids": [
        "CHATPERF-K2-T05-V01",
        "CHATPERF-K2-T05-V02",
        "CHATPERF-K2-T05-V03",
        "CHATPERF-K2-T05-V04"
      ],
      "planned_budget": null,
      "selection_profile": "SM89_GDN_PREFILL_C10240_SPLIT_QKV_T65_T128_T512_T1024_V1",
      "selection_budget": {
        "numeric_scenarios_max": 4,
        "numeric_T": [
          65,
          128,
          512,
          1024
        ],
        "direct_Op_max": 20,
        "direct_algorithm_kernel_max": 16,
        "Graph_shapes": [
          512,
          1024
        ],
        "Graph_routes": [
          "raw",
          "split"
        ],
        "Graph_capture_max": 4,
        "Graph_correctness_replays_max": 8,
        "Graph_warmup_replays_max": 16,
        "Graph_timing_replays_max": 160,
        "Graph_total_replays_max": 184,
        "algorithm_kernel_executions_max": 384,
        "expected_baseline_Graph_copy_operations": 276,
        "host_extract_calls_direct": 12,
        "host_extract_calls_capture": 6,
        "auxiliary_compute_kernel_max": 0,
        "helper_transfers_counts_and_bytes": null,
        "helper_transfer_gap": "Driver not implemented. Enumerate reset/guards/exports H2D/D2D/D2H calls and bytes before a GPU freeze; null is not unlimited.",
        "model_submissions_max": 0,
        "HTTP_wire_max": 0,
        "GPU_expected_minutes": [
          2,
          5
        ],
        "GPU_hard_minutes": 10,
        "cleanup_start_minute": 7
      },
      "CPU_contracts_max": 16,
      "estimated_effort": "已按用户要求收尾，追加测量预算0；保留原证据，不自动补测或进入K4。",
      "signal_gate": {
        "segment_median_gain_min": 0.1,
        "faster_paired_batches_min": 4,
        "paired_batches": 5,
        "all_bitwise_guards_oracle_required": true,
        "adoption": "SEGMENT_SIGNAL_NOT_K4",
        "failure_or_no_signal": "STOP_KEEP_ORIGINAL_NO_AUTOMATIC_MORE_TESTS",
        "end_to_end_gain": null,
        "full_prefill_and_Chat_qualification": "SEPARATE_FUTURE_AUTHORIZATION_NOT_DEVELOPMENT_PREREQUISITE"
      },
      "selection_evidence": "output/ninfer-v4-post-k1-selection-20261023/selection.json",
      "historical_bench_implementation": [
        "仅ordinary nonsegmented Prefill，C10240、T>64且<=1024、4-byte aligned；BF16 input/weights/QKV/state，FP32累加。",
        "复用现有pairs数学、BF16舍入与唯一FP64 causal_conv_oracle，仅改最终Q/K/V输出地址映射；保留独立state更新kernel和stream顺序。",
        "数值覆盖T65/128/512/1024、same-address及separate state、非零history、finite data、guards和输入不变；Graph仅T512/1024 raw/split。",
        "计时对比raw卷积＋state更新＋三次提取copy与split卷积＋原state更新；五批AB/BA配对，reset/check/导出在计时外，event与host wall分别报告。",
        "decode/T<=64、Verify/snapshot/segmented、MTP/Target sampling、workspace arena与运行时产品接入均不纳入本补丁。"
      ],
      "historical_bench_estimated_effort": "8–16工程小时；拟议GPU 2–5分钟、硬限10分钟、第7分钟清理；未授权实施或执行。",
      "current_integration_evidence": "output/ninfer-v4-k2-t05-prefill-integration-20261023/integration-core.json",
      "future_full_prefill_Chat_budget_proposal": {
        "status": "PROPOSED_ONLY_DRIVER_NOT_FROZEN_GPU_NOT_AUTHORIZED",
        "order": "raw source 3ea537c00c759ef2a4577b525ae691f694ae102e then new T1024 integration source; isolated processes only",
        "native_full_prefill": {
          "unique_scenarios": 1,
          "prompt_tokens": 8193,
          "full_chunks_expected": 8,
          "tail_tokens_expected": 1,
          "warmup_per_variant": 1,
          "measured_per_variant": 5,
          "total_prefill_iterations": 12,
          "state_and_logits_comparison": "export first measured iteration outside timing; compare all GDN FP32 state, BF16 conv history, logical attention KV and logits, not nondeterministic envelope bytes",
          "sampling": "prefill only, no synthetic greedy sampling replacement",
          "route_witness": "actual launch witness in diagnostic driver; candidate 384 split launches per iteration (8 x 48), raw zero; tail stays raw",
          "evidence_reused": "old Op numeric, FP64, Graph; no T512 or old standalone Op campaign"
        },
        "chat_completions": {
          "unique_cases": [
            "long-prefix streaming text",
            "long-prefix streaming named tool_choice JSON arguments"
          ],
          "measured_requests_per_variant": 2,
          "measured_requests_total": 4,
          "warmup_submissions_total": 2,
          "readiness_wire_total": 2,
          "wire_total_including_warmup": 8,
          "measurements": [
            "server full prefill time",
            "client TTFT",
            "server first token time",
            "raw SSE",
            "resolved sampling",
            "request IDs and cache outcomes"
          ],
          "policy": "same production sampler and medium reasoning; fresh validation workload, not Pi; existing Pi output32768 unchanged; fixed bodies and token lengths must be frozen before execution"
        },
        "total_model_work_units_including_native_prefill_and_warmup": 18,
        "native_prefill_units": 12,
        "HTTP_model_submissions_including_warmup": 6,
        "wire_total": 8,
        "direct_standalone_Op_tests": 0,
        "T512_additional_tests": 0,
        "new_capture_replay_algorithm_kernel_transfer_limits": null,
        "enumeration_gap": "full-model Graph capture/replay and helper transfers depend on actual frozen driver and existing engine warmup; enumerate and freeze before requesting GPU execution, no unbounded implicit budget",
        "context": 262144,
        "prefill_chunk": 1024,
        "continuation_cache": "off in isolated validation process; original directory untouched",
        "prefix_reuse": false,
        "capacity_failure": "stop and preserve evidence, do not lower context or silently retry",
        "proposed_GPU_minutes": {
          "expected": [
            8,
            15
          ],
          "hard": 20,
          "cleanup_start": 17
        },
        "driver_and_budget_preparation_engineer_hours": [
          3,
          5
        ],
        "analysis_hours_after_execution": [
          0.5,
          1
        ],
        "full_prefill_signal": "all payload/state checks pass; median prefilling improvement >=1%, >=4/5 matched ordinal comparisons faster, no matched regression >3%; ordered cohorts are not AB/BA interleaving",
        "Chat_signal": "two functional checks per variant must pass; four measured requests establish smoke behavior only, no p95 or population TTFT speedup claim",
        "failure_or_no_signal": "preserve full evidence and keep raw as release default, no automatic budget addition",
        "segment_only_estimate_ms_per_full_chunk": 1.12224,
        "estimate_limit": "(64.084-40.704)us x48; different median estimators, not measured full-model savings, no promised percent",
        "production_service": "KEEP_STOPPED",
        "optimization_qualification": false,
        "p95": null
      },
      "full_prefill_prepared_evidence": "output/ninfer-v4-k2-t05-full-prefill-prep-20261023/preparation-core.json",
      "full_prefill_prepared_budget": {
        "budget": {
          "native_prefill": 12,
          "chat": 4,
          "HTTP_warmup": 2,
          "wire": 8
        },
        "model_work_units": 18,
        "GPU_global_limits": {
          "algorithm_kernels": 35651584,
          "captured_copy_calls": 2097152,
          "captured_kernel_calls": 3145728,
          "captures": 256,
          "d2d_bytes": 4535485464576,
          "d2d_calls": 2228224,
          "d2h_bytes": 68719476736,
          "d2h_calls": 393216,
          "direct_kernels": 3145728,
          "h2d_bytes": 274877906944,
          "h2d_calls": 393216,
          "memset_bytes": 274877906944,
          "memset_calls": 196608,
          "replays": 73728
        },
        "cleanup_seconds": 1020,
        "hard_seconds": 1200,
        "freeze_sha256": "4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d",
        "prepared_root": "/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-window-r2"
      },
      "full_prefill_hardware_evidence": "output/ninfer-v4-k2-t05-full-prefill-hardware-20261023/execution-core.json",
      "Chat_remaining_evidence": "output/ninfer-v4-k2-t05-chat-remaining-20261024/execution-core.json",
      "closeout_evidence": "output/ninfer-v4-post-k2-t05-selection-20261024/K2-T05-closeout.json"
    },
    {
      "id": "K3-T01",
      "phase": "K3",
      "kind": "task",
      "title": "按GPU最后消费者复用workspace",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/K3-T01.md",
      "hypothesis": "在已测到工作区限制容量/长上下文时减少峰值，或减少实际分配成本。",
      "source_task_ids": [
        "K3-T01",
        "K3-T02",
        "K3-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "现有workspace plan、typed view与Graph地址；不建新allocator"
      ],
      "implementation": [
        "从选中shape的实际producer/consumer事件列生命期，CPU返回不代表GPU消费结束。",
        "只合并可证明互斥区间，选配置后重新绑定视图并在Graph捕获前冻结地址。",
        "覆盖逃逸输出、async D2H、cancel、capture/replay与恢复；不依赖correction先完成。"
      ],
      "tests": [
        "同live区间不alias，跨流最后consumer完成才复用。",
        "Graph视图地址与encoding/shape绑定稳定，调优后不悬挂旧view。",
        "实际可用容量/峰值显存或分配wall有改善且Chat延迟无倒退。",
        "无真实容量/分配瓶颈则停止，不用理论payload差额冒充实测释放。"
      ],
      "assertion_ids": [
        "CHATPERF-K3-T01-V01",
        "CHATPERF-K3-T01-V02",
        "CHATPERF-K3-T01-V03",
        "CHATPERF-K3-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "estimated_effort": "1–2工程日；pilot约20–45分钟"
    },
    {
      "id": "K3-T02",
      "phase": "K3",
      "kind": "task",
      "title": "有限独立投影fork/join实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/K3-T02.md",
      "hypothesis": "仅当两个真实独立投影处在关键路径且资源有余量时尝试重叠。",
      "source_task_ids": [
        "K3-T03"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "既有投影调用点、独立scratch和join事件"
      ],
      "implementation": [
        "不拆开已融合的GDN normalization/control投影。",
        "从实测MTP窄独立分支选一处，比较串行与双流，join纳入同Graph及下游依赖。",
        "比较完整Graph资源争用、同步和workspace增量，无收益保持串行。"
      ],
      "tests": [
        "分支无数据依赖，两个scratch及逃逸输出生命周期不重叠误用。",
        "capture/replay、cancel和后续consumer均等待正确join。",
        "包含同步和资源争用的完整Graph/round有净收益。",
        "不因Flare使用双流就强行启用；无独立关键路径可记录NOT_SELECTED。"
      ],
      "assertion_ids": [
        "CHATPERF-K3-T02-V01",
        "CHATPERF-K3-T02-V02",
        "CHATPERF-K3-T02-V03",
        "CHATPERF-K3-T02-V04"
      ],
      "planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "estimated_effort": "0.5–1.5工程日；pilot约20–45分钟"
    },
    {
      "id": "H1-T01",
      "phase": "H1",
      "kind": "task",
      "title": "有界Lookup与既有MTP同宽融合",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H1-T01.md",
      "hypothesis": "在重复代码/工具上下文增加每轮提交量，索引与融合开销必须被抵消。",
      "source_task_ids": [
        "H1-T01",
        "H1-T02",
        "H1-T03",
        "H1-T04",
        "H1-T05",
        "H1-T06"
      ],
      "readiness": "CLOSED_NO_FURTHER_MEASUREMENT; additional0; all failures/costs/gaps preserved, not adopted.",
      "modify": [
        "request-local有界索引与现有proposal/verify接口"
      ],
      "implementation": [
        "首个形状C1/W4、K≤3，复用原MTP，索引上限与append增量成本明确。",
        "Lookup替换后后续列必须按最终融合前缀重算Target verify，不能复用旧MTP前缀logits。",
        "no-hit走原MTP，实际命中与fallback成本单列；不先做COPY skip、TokenTree或全局特征库。"
      ],
      "tests": [
        "索引更新、查找、搬运、verify、alignment、commit全部计入完整round。",
        "命中来源/接受深度可核对；不命中不能给Lookup资格。",
        "有界内存、不跨请求串用身份；cancel/restore/尾轮按原状态合同。",
        "在相同Target采样和输出上限下服务wall净改善，工具输出合同不回退。"
      ],
      "assertion_ids": [
        "CHATPERF-H1-T01-V01",
        "CHATPERF-H1-T01-V02",
        "CHATPERF-H1-T01-V03",
        "CHATPERF-H1-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 10,
        "client_model_requests_max": 6,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 8,
        "native_request_submissions_max": 4,
        "total_model_work_submissions_max": 12,
        "gpu_minutes_max": 20,
        "cleanup_start_minute": 17,
        "native_shapes_max": 2,
        "native_calls_max": 16,
        "traces_max": 4
      },
      "estimated_effort": "已收尾，追加预算0。",
      "selection_profile": "REQUEST_LOCAL_LOOKUP_PACKET_C1_W4_K3_N4_RING8192_V1",
      "selection_budget": {
        "native_state_scenarios_max": 2,
        "native_request_submissions_max": 4,
        "native_decode_or_verify_calls_max": 16,
        "native_scenarios": [
          "Lookup-selected packet equal to MTP: bitwise verify/state/conv and next-step equality",
          "Different Lookup packet with rejection/partial permit: canonical Target-prefix state and next-step consistency"
        ],
        "new_measured_Chat_max": 6,
        "Chat_AB_pairs": 3,
        "HTTP_warmup_max": 2,
        "HTTP_model_submissions_max": 8,
        "wire_max": 10,
        "total_model_work_submissions_max": 12,
        "standalone_old_Op_or_Graph_scenarios": 0,
        "Chat_cases": [
          "new code-copy positive control",
          "new repeated structured tool/code output",
          "new low-repetition control"
        ],
        "context": 262144,
        "Pi_medium_output_budget_unchanged": 32768,
        "new_Chat_fixture_max_tokens": 2048,
        "GPU_resource_envelope": {
          "algorithm_kernels": 35651584,
          "captured_copy_calls": 2097152,
          "captured_kernel_calls": 3145728,
          "captures": 256,
          "d2d_bytes": 4535485464576,
          "d2d_calls": 2228224,
          "d2h_bytes": 68719476736,
          "d2h_calls": 393216,
          "direct_kernels": 3145728,
          "h2d_bytes": 274877906944,
          "h2d_calls": 393216,
          "memset_bytes": 274877906944,
          "memset_calls": 196608,
          "replays": 73728
        },
        "resource_note": "Proposed finite per-window ceiling, not an executable ledger or permission. New driver must enumerate actual capture/replay/kernel/copy paths and freeze all bounds; never reuse a consumed K2 root.",
        "expected_minutes": [
          5,
          10
        ],
        "hard_minutes": 20,
        "cleanup_start_minute": 17,
        "actual_execution_authorized": false
      },
      "CPU_contracts_max": 16,
      "selection_evidence": "output/ninfer-v4-post-k2-t05-selection-20261024/selection.json",
      "historical_planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "implementation_evidence": "output/ninfer-v4-h1-t01-20261024/DELIVERY-RECEIPT-r3.json",
      "freeze_sha256": "716ccfc4e8308f7db34497d8edc6d6705aa1a843370b4efef1f073df42d22eb0",
      "runtime_qualification": "2_NATIVE_SCENARIOS_PASS; CHAT_GUARD_CONFLICT_NO_PERFORMANCE_SIGNAL; FULL_QUALIFICATION_PENDING",
      "CPU_contracts_executed": 16,
      "hardware_evidence": "output/ninfer-v4-h1-t01-hardware-20261024/analysis.json",
      "additional_budget": 0,
      "executed_budget": {
        "HTTP_warmup": 2,
        "chat": 6,
        "native_requests": 4,
        "wire": 10
      },
      "closeout_evidence": "output/ninfer-v4-post-h1-selection-20261024/H1-T01-closeout.json"
    },
    {
      "id": "H1-T07",
      "phase": "H1",
      "kind": "task",
      "title": "复用统一Target sampling与状态资格",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H1-T07.md",
      "hypothesis": "草稿路线可不同，接受与正式状态只能由同一Target合同决定。",
      "source_task_ids": [
        "H1-T07"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "既有sampler/processor/RNG/commit及独立分布测试；不是新增采样器"
      ],
      "implementation": [
        "deterministic greedy proposal使用q=delta；Target仍T1/top_p.95/top_k20，固定processor顺序。",
        "接受p(d)，拒绝在剔除d后的Target残差采样；全接受bonus按现有规则。",
        "按最终前缀验证mixed来源、0/1概率、top-p边界、mask/penalty支持集、RNG消费、stop和部分许可。"
      ],
      "tests": [
        "独立分布与负例拒绝stale logits、错processor和错RNG；单seed文本一致不是分布证明。",
        "需要stochastic q的候选必须提供真实条件q及独立正确性证明，否则限deterministic草稿。",
        "许可、epoch、slot、conv/state和下一轮衔接正确；bonus/anchor/显示token不与commit_columns混淆。",
        "复用不变合同的既有测试，只为新shape/route补证；不改Target/Pi32768。"
      ],
      "assertion_ids": [
        "CHATPERF-H1-T07-V01",
        "CHATPERF-H1-T07-V02",
        "CHATPERF-H1-T07-V03",
        "CHATPERF-H1-T07-V04"
      ],
      "planned_budget": {},
      "estimated_effort": "新路线定向0.5–1.5工程日；与所选实验共用GPU预算"
    },
    {
      "id": "H2-T01",
      "phase": "H2",
      "kind": "task",
      "title": "草稿词表头裁剪或稀疏投影实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H2-T01.md",
      "hypothesis": "只有draft-head占比实测明显时，减少投影计算可能提高净吞吐。",
      "source_task_ids": [
        "H2-T01",
        "H2-T02",
        "H2-T03",
        "H2-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "现有draft head、token mapping与静态配置；不裁剪Target词表"
      ],
      "implementation": [
        "冻结覆盖率/映射/显存开销，先一个head profile和同宽对照。",
        "不能把被裁剪草稿词表当Target支持集，Target分布仍完整。",
        "比较head节省、接受率变化及整个draft+verify+commit成本。"
      ],
      "tests": [
        "draft token映射无歧义、目标支持集和概率未裁剪。",
        "route-hit与独立数值/分布及状态检查覆盖实际候选。",
        "覆盖/接受深度的下降计入收益，不能只比较head GEMM。",
        "无可测head瓶颈或净收益即停止，不把多个profile全量资格设为必做。"
      ],
      "assertion_ids": [
        "CHATPERF-H2-T01-V01",
        "CHATPERF-H2-T01-V02",
        "CHATPERF-H2-T01-V03",
        "CHATPERF-H2-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 48,
        "client_model_requests_max": 32,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 34,
        "gpu_minutes_max": 60,
        "native_shapes_max": 6,
        "native_calls_max": 126,
        "traces_max": 2
      },
      "estimated_effort": "1–3工程日；pilot约20–45分钟"
    },
    {
      "id": "H3-T01",
      "phase": "H3",
      "kind": "task",
      "title": "W8整链扩宽实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H3-T01.md",
      "hypothesis": "较宽验证在接受增长抵过verify/alignment/Graph成本时可减少Target轮数。",
      "source_task_ids": [
        "H3-T01",
        "H3-T02",
        "H3-T03",
        "H3-T04"
      ],
      "readiness": "MINIMAL_VALIDATION_INCOMPLETE_DRIVER_WORKSPACE_ZERO_FAILURE",
      "modify": [
        "既有MTP/Attention/GDN/Graph容量与state映射"
      ],
      "implementation": [
        "先冻结当前W4对照与列语义，W8只选一个C1 shape。",
        "GDN Op接受T≤16不是整链支持证据；检查Attention、MTP、Graph、record/frontier及request headroom。",
        "先构建/host容量合同，再同Target sampling实际命中并比较完整round。"
      ],
      "tests": [
        "所有实际组件支持W8，没有截断context/输出或隐藏fallback。",
        "各接受深度和尾轮remaining1/2、cancel/partial permit状态正确。",
        "新宽度的Target分布、RNG与commit_columns映射合格。",
        "接受tokens/s和服务wall净改善，宽度和显存增加成本完整计入。"
      ],
      "assertion_ids": [
        "CHATPERF-H3-T01-V01",
        "CHATPERF-H3-T01-V02",
        "CHATPERF-H3-T01-V03",
        "CHATPERF-H3-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 10,
        "client_model_requests_max": 6,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 8,
        "native_request_submissions_max": 4,
        "total_model_work_submissions_max": 12,
        "gpu_minutes_max": 20,
        "cleanup_start_minute": 17,
        "native_shapes_max": 2,
        "native_calls_max": 16,
        "new_T6_numeric_scenarios_max": 7,
        "numeric_direct_Op_max": 9,
        "numeric_captures_max": 7,
        "numeric_replays_including_warmup_max": 14,
        "actual_execution_authorized": false
      },
      "estimated_effort": "本窗口已因驱动初始化错误结束；剩余先修驱动零容量/异常审计，再冻结接续；原预算不可自动重用。",
      "selection_profile": "MTP_EXISTING_C1_W6_K5_VS_W4_K3_V1",
      "selected_stage": "A_EXISTING_W6_PILOT_ONLY",
      "selection_evidence": "output/ninfer-v4-post-h1-selection-20261024/selection.json",
      "CPU_contracts_max": 16,
      "pilot_budget": {
        "profile": "MTP_EXISTING_C1_W6_K5_VS_W4_K3_V1",
        "native_requests": 4,
        "chat": 6,
        "HTTP_warmup": 2,
        "HTTP_model_submissions": 8,
        "model_work_units": 12,
        "wire": 10,
        "native_cases": 2,
        "native_decode_calls_max": 16,
        "prefill_chunk": 1024,
        "context": 262144,
        "native_requested_output_budget": 32768,
        "Chat_fixture_output_budget": 2048,
        "Pi_output_budget_unchanged": 32768,
        "phases": [
          "numeric-q5",
          "numeric-swiglu",
          "numeric-q6",
          "numeric-attn",
          "numeric-gdn",
          "numeric-chain",
          "native-w6",
          "chat-raw",
          "chat-candidate"
        ],
        "graph_nodes_per_definition_max": 8192,
        "hard_seconds": 1200,
        "cleanup_seconds": 1020,
        "new_direct_Op_scenarios": 7,
        "numeric_direct_Op": 9,
        "numeric_captures": 7,
        "numeric_replays": 14,
        "old_task_reruns": 0,
        "native_process_limits": {
          "algorithm_kernels": 1048576,
          "captured_copy_calls": 524288,
          "captured_kernel_calls": 524288,
          "captures": 64,
          "d2d_bytes": 68719476736,
          "d2d_calls": 65536,
          "d2h_bytes": 17179869184,
          "d2h_calls": 65536,
          "direct_kernels": 524288,
          "h2d_bytes": 68719476736,
          "h2d_calls": 65536,
          "memset_bytes": 68719476736,
          "memset_calls": 32768,
          "replays": 4096
        },
        "chat_process_limits": {
          "algorithm_kernels": 16777216,
          "captured_copy_calls": 524288,
          "captured_kernel_calls": 1048576,
          "captures": 64,
          "d2d_bytes": 2199023255552,
          "d2d_calls": 1048576,
          "d2h_bytes": 17179869184,
          "d2h_calls": 131072,
          "direct_kernels": 1048576,
          "h2d_bytes": 68719476736,
          "h2d_calls": 131072,
          "memset_bytes": 68719476736,
          "memset_calls": 65536,
          "replays": 32768
        },
        "numeric_process_limits": {
          "captures": 2,
          "replays": 4,
          "direct_kernels": 4096,
          "captured_kernel_calls": 4096,
          "algorithm_kernels": 8192,
          "captured_copy_calls": 8192,
          "h2d_calls": 8192,
          "h2d_bytes": 8589934592,
          "d2d_calls": 8192,
          "d2d_bytes": 8589934592,
          "d2h_calls": 8192,
          "d2h_bytes": 17179869184,
          "memset_calls": 8192,
          "memset_bytes": 17179869184
        },
        "actual_GPU_execution_authorized": false,
        "native_planned_decode_calls": 9,
        "reused_GQA_T6": {
          "status": "P4_PASS_REUSED_NOT_RERUN",
          "report": "docs/ninfer-v4-p4-hardware-20261023.md",
          "original_case": "rk4v4:A1-A2-A3:T6;base61;seed1701",
          "captures": 2,
          "replays": 4
        },
        "runtime_resource_note": "All startup/Graph/kernel/copy/state/reset costs charged to exact per-process counters; upper ceilings, not expected usage. Semantic target Op count9 excludes capture declarations. GQA standalone case is reused.",
        "paths_counted": [
          "materialize full model3 times",
          "all startup captures",
          "Target full width4/6",
          "mandatory MTP alignment and K3/K5 next proposals",
          "native extent0 and actual Target oracle before verify",
          "actual BF16 verify D2H9 matrices",
          "canonical state export4 requests",
          "numerical weights/reset/readback/Graph replay",
          "CPU prefill and native reference calls",
          "HTTP warmup and normal Chat",
          "failure and cleanup costs"
        ],
        "p95": null,
        "optimization_qualification": false,
        "full_GPU_resource_limits": {
          "algorithm_kernels": 34652160,
          "captured_copy_calls": 1622016,
          "captured_kernel_calls": 2646016,
          "captures": 199,
          "d2d_bytes": 4518305595392,
          "d2d_calls": 2211840,
          "d2h_bytes": 154618822656,
          "d2h_calls": 376832,
          "direct_kernels": 2646016,
          "h2d_bytes": 257698037760,
          "h2d_calls": 376832,
          "memset_bytes": 309237645312,
          "memset_calls": 212992,
          "replays": 69646
        }
      },
      "W6_does_not_qualify_original_W8_assertions": true,
      "conditional_W8_budget": {
        "wire_max": 48,
        "client_model_requests_max": 32,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 34,
        "gpu_minutes_max": 60,
        "native_shapes_max": 6,
        "native_calls_max": 126,
        "traces_max": 2
      },
      "historical_W6_selection_pilot_budget": {
        "actual_execution_authorized": false,
        "new_T6_numeric_scenarios_max": 8,
        "numeric_scenarios": [
          "T6 Q5 residual K6144",
          "T6 Q5 residual K17408",
          "T6 Q4 SwiGLU",
          "T6 attention input projection",
          "T6 GDN input projection",
          "T6 Q6 full Target head N248320/K5120",
          "C1/W6 rk4v4 GQA attention",
          "C1/W6 raw GDN conv Record + recurrent Record + Fold"
        ],
        "numeric_direct_Op_max": 10,
        "numeric_captures_max": 8,
        "numeric_replays_including_warmup_max": 16,
        "numeric_microbenchmark_sweeps": 0,
        "native_state_scenarios_max": 2,
        "native_request_submissions_max": 4,
        "native_decode_or_verify_calls_max": 16,
        "planned_native_calls": 9,
        "native_scenarios": [
          "Same physicalW6 extent0 Target reference6 sequential decode calls; K5 packet taken from first5 real Target IDs; candidate1 fullW6 round accepts5 and permits6; same-prefix logits/state/conv/KV and nextMTP comparison",
          "Same physicalW6 extent0 reference1 call; candidate1 fullW6 packet reusing Target oracle, terminal permit1; compare common-prefix column0 and permitted canonical state; discard unlicensed next drafts"
        ],
        "new_measured_Chat_max": 6,
        "Chat_AB_pairs": 3,
        "HTTP_warmup_max": 2,
        "HTTP_model_submissions_max": 8,
        "health_wire_max": 2,
        "wire_max": 10,
        "total_model_work_submissions_max": 12,
        "model_process_loads_proposed_max": 3,
        "Chat_cases": [
          "Fresh unique-line code fixture, W4/W6 pair",
          "Fresh unique-row named-tool JSON fixture, W4/W6 pair",
          "Fresh low-repetition control, W4/W6 pair"
        ],
        "context": 262144,
        "native_requested_output_tokens": 32768,
        "new_Chat_fixture_max_tokens": 2048,
        "Pi_medium_output_budget_unchanged": 32768,
        "GPU_resource_envelope": null,
        "resource_reason": "Only scenario/direct/capture/replay scopes proposed here. All model startup/capture/replay/algorithm-kernel/copy/memset and byte ceilings must be enumerated by the new driver and frozen before any GPU execution. No executable ledger or implicit resource authorization.",
        "expected_minutes": [
          5,
          10
        ],
        "hard_minutes": 20,
        "cleanup_start_minute": 17
      },
      "implementation_evidence": "output/ninfer-v4-h3-w6-20261024/remote-final/evidence/source-identity.json",
      "freeze_sha256": "4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc",
      "preparation_evidence": "output/ninfer-v4-h3-w6-20261024/remote-final/evidence/preparation-receipt.json",
      "CPU_contracts_executed": 16,
      "CPU_case_invocations": 17,
      "CPU_targeted_revision_cases": [
        11
      ],
      "runtime_qualification": "6 independent Op numeric/Graph cases PASS; chain setup FAIL; native bitwise/W4-W6 decode NOT_RUN; W8 qualification PENDING",
      "GPU_executed_budget": {
        "HTTP_warmup": 0,
        "chat": 0,
        "native_requests": 0,
        "wire": 0,
        "numeric_attempted_scenarios": 7,
        "numeric_PASS_scenarios": 6,
        "numeric_direct_Op_completed": 6,
        "captures_completed": 6,
        "replays_completed": 12,
        "native_decode_calls": 0
      },
      "hardware_evidence": "output/ninfer-v4-h3-w6-hardware-20261024/analysis.json",
      "hardware_authorization": {
        "window": "prepared-window-r1",
        "authorized": true,
        "terminal": "FAILED_CLEANED",
        "additional_execution_budget": 0
      },
      "unmeasured_scope": [
        "chain numerical/bitwise and Graph",
        "native W6 full/partial permit bitwise",
        "W4-W6 full decode and Chat quality"
      ]
    },
    {
      "id": "H4-T01",
      "phase": "H4",
      "kind": "task",
      "title": "W16按需扩宽实验",
      "depends_on": [
        "H3-T01"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H4-T01.md",
      "hypothesis": "W8仍受验证轮数限制且接受曲线有余量时才试W16；收益不随宽度线性增长。",
      "source_task_ids": [
        "H4-T01",
        "H4-T02",
        "H4-T03",
        "H4-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "整链W16容量及Graph；首轮不做COPY skip或新tree算法"
      ],
      "implementation": [
        "复用已检查W8链，静态排除记录/Attention/Graph/页额不足。",
        "W8 pilot未合格或接受增长已饱和则暂不选择W16。",
        "W16与已合格W8使用同一主假设、相同Target合同和配对请求。"
      ],
      "tests": [
        "W8技术证据已完成且可复用，不为W16重复全W8验收。",
        "GDN、MTP、Attention、Graph、KV和许可/尾轮都覆盖实际W16。",
        "没有输出/context缩减或采样近似；容量不足保留失败并停止。",
        "W16相对W8净收益超过新增成本，否则不采用。"
      ],
      "assertion_ids": [
        "CHATPERF-H4-T01-V01",
        "CHATPERF-H4-T01-V02",
        "CHATPERF-H4-T01-V03",
        "CHATPERF-H4-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 48,
        "client_model_requests_max": 32,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 34,
        "gpu_minutes_max": 60,
        "native_shapes_max": 6,
        "native_calls_max": 126,
        "traces_max": 2
      },
      "estimated_effort": "W8后1–3工程日；pilot约30–60分钟"
    },
    {
      "id": "H6-T01",
      "phase": "H6",
      "kind": "task",
      "title": "DFlash2匹配27B资产的块草稿实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H6-T01.md",
      "hypothesis": "并行块草稿可能减少串行draft时间并提高接受长度，但伴随额外模型/特征/KV成本。",
      "source_task_ids": [
        "H6-T01",
        "H6-T02",
        "H6-T03",
        "H6-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "匹配27B companion加载、特征/草稿通路与既有Target verifier"
      ],
      "implementation": [
        "先核验checkpoint不可变revision、tokenizer/tensor manifest、license与SM89显存静态预算；没有资产先停，禁止训练或用35B资产冒充。",
        "先一个可容纳宽度；无需先完成Lookup、词表头、W16、kernel发布。",
        "优先deterministic proposal复用q=delta；若用stochastic draft须有真实条件q和相应证明。"
      ],
      "tests": [
        "精确27B模型/层/特征/词表绑定成立，public DFlash论文不能代替本项目DFlash2资格。",
        "独立数值、Target分布、RNG、许可/rollback与restore覆盖实际route。",
        "权重、feature ingress、draft KV、Graph、GPU显存和fallback成本均计入。",
        "有实际draft命中和完整服务净收益才继续；无兼容资产则明确BLOCKED_ASSET且不耗GPU。"
      ],
      "assertion_ids": [
        "CHATPERF-H6-T01-V01",
        "CHATPERF-H6-T01-V02",
        "CHATPERF-H6-T01-V03",
        "CHATPERF-H6-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 64,
        "client_model_requests_max": 48,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 50,
        "gpu_minutes_max": 90,
        "native_shapes_max": 6,
        "native_calls_max": 126,
        "traces_max": 2
      },
      "estimated_effort": "资产就绪后3–7工程日；pilot约45–90分钟；等待/训练未估入"
    },
    {
      "id": "H7-T01",
      "phase": "H7",
      "kind": "task",
      "title": "全局历史草稿检索实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/H7-T01.md",
      "hypothesis": "长历史中有局部ring以外的高价值重复片段时，检索可能提高命中和接受。",
      "source_task_ids": [
        "H7-T01",
        "H7-T02",
        "H7-T03",
        "H7-T04"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "已有索引/record边界内的token或feature检索；不建通用向量服务"
      ],
      "implementation": [
        "先离线测bounded ring外命中分布、候选长度和索引/搬运成本。",
        "token-only检索不强制依赖DFlash2；若设计需要DFlash feature重放，才绑定已合格H6资产/feature合同。",
        "有界内存与eviction，显式统计DraftKV重建、位置/模型身份和跨请求隔离，不自动扩成持久全局平台。"
      ],
      "tests": [
        "负例拒绝tokenizer/model/position/feature identity不符及无效旧记录。",
        "全部来源都由最终前缀Target验证，绝不直接提交检索结果。",
        "索引、查询、搬运、重建与verify总成本低于收益，局部Lookup对照保留。",
        "未发现ring外有效命中或搬运成本过大即停止，不要求所有请求建立全局索引。"
      ],
      "assertion_ids": [
        "CHATPERF-H7-T01-V01",
        "CHATPERF-H7-T01-V02",
        "CHATPERF-H7-T01-V03",
        "CHATPERF-H7-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 48,
        "client_model_requests_max": 32,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 34,
        "gpu_minutes_max": 60,
        "native_shapes_max": 6,
        "native_calls_max": 126,
        "traces_max": 2
      },
      "estimated_effort": "token路径1–3工程日；feature路径合格H6后再加1–3日；pilot约30–60分钟"
    },
    {
      "id": "S0-T01",
      "phase": "S0",
      "kind": "task",
      "title": "Utility/restore成本驱动的有限策略实验",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/S0-T01.md",
      "hypothesis": "当backend/宽度/恢复成本随请求变化时，选择更便宜的合格路线可能提升C1和混合负载性能。",
      "source_task_ids": [
        "S0-T01",
        "S0-T02",
        "S0-T03",
        "S0-T04",
        "S0-T05"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "现有选择点的一条有限规则或固定表；不引入新调度平台"
      ],
      "implementation": [
        "先离线评估可选路线的实际round成本、utility和restore成本是否有变化；成本稳定则不选择。",
        "只比较既有合格backend/width；并发收益主张才增最小混合负载，不把多租户QoS/fairness做必做功能。",
        "先固定规则与原策略AB，不训练RL，不等所有高级算法或H5生产发布。"
      ],
      "tests": [
        "只能选择当前已资格route，不能由调度器绕过sampling/容量/状态门禁。",
        "CPU决策、同步、恢复和cache miss的全服务成本进入分母。",
        "cancel/公平进度与原硬边界不退化，不改变业务优先级或采样。",
        "C1收益和混合负载收益分别验证；平均acceptance更高不替代实际wall更低。"
      ],
      "assertion_ids": [
        "CHATPERF-S0-T01-V01",
        "CHATPERF-S0-T01-V02",
        "CHATPERF-S0-T01-V03",
        "CHATPERF-S0-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 48,
        "client_model_requests_max": 32,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 34,
        "gpu_minutes_max": 60,
        "native_shapes_max": 6,
        "native_calls_max": 126,
        "traces_max": 2
      },
      "estimated_effort": "已有≥2合格可选策略时1–3工程日；pilot约30–60分钟"
    },
    {
      "id": "UP-T01",
      "phase": "UP",
      "kind": "task",
      "title": "上游性能改动选择性或完整合并对照",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/UP-T01.md",
      "hypothesis": "上游的缓存、prefill、small-T与共享路径可能提速；合并范围必须由真实收益/依赖支持。",
      "source_task_ids": [
        "P5-T01",
        "P5-T05",
        "P6-T01"
      ],
      "readiness": "候选入口保留；本轮未找到U28—U34纯文本Chat直接提速证据，完整合并当前不优先。",
      "modify": [
        "固定O/U与P4之间必要共享路径；不以协议/UI完整性扩验收"
      ],
      "implementation": [
        "复用本轮U01—U34源码审计：U01—U27已在P1—P4吸收，性能收益尚需配对；U28—U34余量见专项报告。",
        "默认选择有纯Chat收益或必要耦合依赖的最小改动；若拆分成本/风险更高，允许从干净P4分支建立完整U34候选，先与P4配对；选择性版本已有适用证据时再复用其对照，不强制三版本新测试。",
        "完整合并携带的未启用API/UI是源码范围，不变成开发/性能验收必做；共享格式变化必须验证缓存隔离，不覆盖原cache目录。"
      ],
      "tests": [
        "每个被选改动有当前纯Chat调用可达证据、性能假设或必要耦合依赖；提交名不能代替源码判断。",
        "保留18处G1差异及已修复前端/增量流/并发合同；不采用P5未评审树冒充可构建候选。",
        "对实际触及的共享状态/缓存版本、取消/故障和Chat做必要验证，完整merge不等于所有模型/协议重新全验。",
        "完整版计入构建、内存、cache冷启动/迁移与服务wall；无净收益或更大回归则用选择性版本或P4。"
      ],
      "assertion_ids": [
        "CHATPERF-UP-T01-V01",
        "CHATPERF-UP-T01-V02",
        "CHATPERF-UP-T01-V03",
        "CHATPERF-UP-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 32,
        "client_model_requests_max": 24,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 26,
        "gpu_minutes_max": 45,
        "native_shapes_max": 4,
        "native_calls_max": 84,
        "traces_max": 2
      },
      "estimated_effort": "选择性0.5–2工程日；完整U34预计2–5工程日（含9冲突重做/评审），pilot20–45分钟"
    },
    {
      "id": "K4-T01",
      "phase": "K4",
      "kind": "task",
      "title": "选中候选的一次共同资格与可复现报告",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": false,
      "document": "plans/tasks/K4-T01.md",
      "hypothesis": "只为真实选中且改变的路径做共同验收，不在K2/K3/H5/H8重复整套矩阵。",
      "source_task_ids": [
        "K4-T01",
        "K4-T02",
        "H5-T01",
        "H5-T02",
        "H5-T03",
        "H8-T03",
        "H8-T05"
      ],
      "readiness": "K0确认该路径有可测瓶颈后选择；未获实施授权。",
      "modify": [
        "定向测试、配对比较、报告与回退工件；不部署"
      ],
      "implementation": [
        "scope显式指定该节点的branch依赖；测试同一集成树、镜像、模型与配置，不能拼不同候选PASS。",
        "只补新路径数值/状态/资源、Chat流与Target分布缺口；复用没变路径的已通过证据。",
        "一次AB/BA或随机顺序配对服务测量；新holdout仅在主张编程质量/任务wall时执行新任务，不重跑旧题或grader。",
        "冻结可回退原路由，报告实际P/O/cache、route hit、round/service wall、峰值与全部失败成本；p95无适当样本继续null。"
      ],
      "tests": [
        "微基准、完整round和Chat服务结论分开，净收益包含所有新增成本且命中真实route。",
        "选中路径适用的独立数值/采样/许可/资源/容量与Chat合同全过，不要求未启用功能资格。",
        "预声明收益/质量门槛达到，样本不足或不可观察项如实INCONCLUSIVE；不得宣称旧Baseline已优化通过。",
        "完整证据及回退工件哈希可复现；C1缺口、18差异、失败/拒绝成本和未来发布未授权状态披露。"
      ],
      "assertion_ids": [
        "CHATPERF-K4-T01-V01",
        "CHATPERF-K4-T01-V02",
        "CHATPERF-K4-T01-V03",
        "CHATPERF-K4-T01-V04"
      ],
      "planned_budget": {},
      "estimated_effort": "小候选0.5–1工程日；在其pilot总预算内，扩大统计/长上下文另冻结"
    },
    {
      "id": "C0-T01",
      "phase": "C0",
      "kind": "task",
      "title": "统一SHA-256的非SHA-NI CPU路径加速",
      "depends_on": [
        "K0-GATE"
      ],
      "status": "PENDING",
      "optional": true,
      "document": "plans/tasks/C0-T01.md",
      "hypothesis": "减少实际缓存快照内容寻址/发布中的CPU标量SHA成本；实际Chat收益需独立证明。",
      "source_task_ids": [],
      "readiness": "CPU补丁及BO闭合已通过；最小实机驱动/空账本/无GPU验证与双轴评审已完成，GPU请求尚未执行，需后续明确授权。",
      "modify": [
        "src/artifact/sha256.h/.cpp统一API内部的非SHA-NI后端；保留SHA-NI及精确update/finish语义。",
        "以现有libcrypto3的EVP为首选成熟后端候选；CMake及隔离构建/运行依赖闭合，BO原镜像不修改。",
        "不另造cache哈希器，不跳过/截断SHA256，不改content serialization、digest、TTL、alias/CAS、缓存格式、缓存目录或采样。",
        "仅为实际新backend增加定向分块/边界/坏数据/等价与性能测试，不重跑旧Baseline、已过native或grader。"
      ],
      "implementation": [
        "复用artifact::Sha256权威，固定libcrypto3后端及BO头文件/运行库绑定，原SHA-NI路径保持。",
        "先完成可构建CPU补丁、精确等价/坏数据/分段update和有限吞吐验证，不改变任何缓存或Target合同。",
        "对异步发布后的实际缓存就绪/等待做以后获准的新场景验证，禁止把背景耗时直接宣称每请求提速。"
      ],
      "tests": [
        "所有分段update/finish、边界与canonical content ID逐字节一致，损坏输入仍被拒绝。",
        "原SHA-NI路线及小buffer/冷provider初始化不出现未披露回退，BO依赖和服务二进制可构建。",
        "同构建原实现与候选的大块CPU哈希>=1.7x、缓存publication目标降低>=30%，失败与启动成本全部保留。",
        "实际cache-constrained Chat服务收益另测；只CPU微基准通过不给推理/发布资格，不重跑历史任务。"
      ],
      "assertion_ids": [
        "CHATPERF-C0-T01-V01",
        "CHATPERF-C0-T01-V02",
        "CHATPERF-C0-T01-V03",
        "CHATPERF-C0-T01-V04"
      ],
      "planned_budget": {
        "wire_max": 12,
        "client_model_requests_max": 8,
        "warmup_submissions_max": 2,
        "total_model_submissions_max": 10,
        "gpu_minutes_max": 15,
        "native_shapes_max": 0,
        "native_calls_max": 0,
        "traces_max": 0
      },
      "estimated_effort": "准备已完成；实机预计8–15分钟，900秒硬窗口，720秒开始仅清理候选；不重跑旧CPU。"
    }
  ],
  "release_scopes": [
    {
      "scope_id": "attribution_only",
      "mode": "research",
      "include_ids": [
        "PERF-READY",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K0-GATE"
      ],
      "dependency_overrides": {},
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "PERF-READY"
      ]
    },
    {
      "scope_id": "correction_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K1-T01",
        "K1-T02",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K1-T01",
          "K1-T02"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K1-T01",
        "K1-T02",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "correction",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "correction_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K1-T01",
        "K1-T02",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K1-T01",
          "K1-T02"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K1-T01",
        "K1-T02",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "correction",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "kernel_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T01",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K2-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T01",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "kernel",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "kernel_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T01",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K2-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T01",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "kernel",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "workspace_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T01",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K3-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T01",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "workspace",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "workspace_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T01",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K3-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T01",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "workspace",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "projection_overlap_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T02",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K3-T02"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T02",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "projection_overlap",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "projection_overlap_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T02",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K3-T02"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K3-T02",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "projection_overlap",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "lookup_candidate",
      "mode": "candidate",
      "include_ids": [
        "H1-T01",
        "H1-T07",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H1-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "H1-T01",
        "H1-T07",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "lookup",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "lookup_publication",
      "mode": "publication",
      "include_ids": [
        "H1-T01",
        "H1-T07",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H1-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "H1-T01",
        "H1-T07",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "lookup",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "draft_head_candidate",
      "mode": "candidate",
      "include_ids": [
        "H1-T07",
        "H2-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H2-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "H1-T07",
        "H2-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "draft_head",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "draft_head_publication",
      "mode": "publication",
      "include_ids": [
        "H1-T07",
        "H2-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H2-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "H1-T07",
        "H2-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "draft_head",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "w8_candidate",
      "mode": "candidate",
      "include_ids": [
        "H1-T07",
        "H3-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H3-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "H1-T07",
        "H3-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "w8",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "w8_publication",
      "mode": "publication",
      "include_ids": [
        "H1-T07",
        "H3-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H3-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "H1-T07",
        "H3-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "w8",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "w16_candidate",
      "mode": "candidate",
      "include_ids": [
        "H1-T07",
        "H3-T01",
        "H4-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H3-T01",
          "H4-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "H1-T07",
        "H3-T01",
        "H4-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "w16",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "w16_publication",
      "mode": "publication",
      "include_ids": [
        "H1-T07",
        "H3-T01",
        "H4-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H3-T01",
          "H4-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "H1-T07",
        "H3-T01",
        "H4-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "w16",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "dflash2_candidate",
      "mode": "candidate",
      "include_ids": [
        "H1-T07",
        "H6-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H6-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "H1-T07",
        "H6-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "dflash2",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "dflash2_publication",
      "mode": "publication",
      "include_ids": [
        "H1-T07",
        "H6-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H6-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "H1-T07",
        "H6-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "dflash2",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "global_retrieval_candidate",
      "mode": "candidate",
      "include_ids": [
        "H1-T07",
        "H7-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H7-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "H1-T07",
        "H7-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "global_retrieval",
      "conditional_dependencies": {
        "feature_backed_retrieval": "H6-T01 evidence only if feature reconstruction is chosen",
        "utility_routes": "only already qualified selectable routes; no all-route prerequisite"
      }
    },
    {
      "scope_id": "global_retrieval_publication",
      "mode": "publication",
      "include_ids": [
        "H1-T07",
        "H7-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "H7-T01",
          "H1-T07"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "H1-T07",
        "H7-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "global_retrieval",
      "conditional_dependencies": {
        "feature_backed_retrieval": "H6-T01 evidence only if feature reconstruction is chosen",
        "utility_routes": "only already qualified selectable routes; no all-route prerequisite"
      }
    },
    {
      "scope_id": "utility_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "S0-T01"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "S0-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "S0-T01"
      ],
      "variant": "utility",
      "conditional_dependencies": {
        "feature_backed_retrieval": "H6-T01 evidence only if feature reconstruction is chosen",
        "utility_routes": "only already qualified selectable routes; no all-route prerequisite"
      }
    },
    {
      "scope_id": "utility_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "S0-T01"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "S0-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "S0-T01"
      ],
      "variant": "utility",
      "conditional_dependencies": {
        "feature_backed_retrieval": "H6-T01 evidence only if feature reconstruction is chosen",
        "utility_routes": "only already qualified selectable routes; no all-route prerequisite"
      }
    },
    {
      "scope_id": "upstream_selective_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "UP-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "variant": "upstream_selective",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "upstream_selective_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "UP-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "variant": "upstream_selective",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "upstream_full_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "UP-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "variant": "upstream_full",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "upstream_full_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "UP-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY",
        "UP-T01"
      ],
      "variant": "upstream_full",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "cpu_sha_candidate",
      "mode": "candidate",
      "include_ids": [
        "C0-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "C0-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "C0-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "cpu_sha",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "cpu_sha_publication",
      "mode": "publication",
      "include_ids": [
        "C0-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "C0-T01"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "C0-T01",
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "cpu_sha",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "prefill_conv_split_candidate",
      "mode": "candidate",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T05",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K2-T05"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": false,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T05",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "prefill_conv_split",
      "conditional_dependencies": {}
    },
    {
      "scope_id": "prefill_conv_split_publication",
      "mode": "publication",
      "include_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T05",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "dependency_overrides": {
        "K4-T01": [
          "K2-T05"
        ]
      },
      "requires_future_implementation_authorization": true,
      "requires_future_production_authorization": true,
      "resolved_node_ids": [
        "K0-GATE",
        "K0-T01",
        "K0-T02",
        "K0-T04",
        "K2-T05",
        "K4-GATE",
        "K4-QUALIFIED",
        "K4-T01",
        "PERF-READY"
      ],
      "variant": "prefill_conv_split",
      "conditional_dependencies": {}
    }
  ],
  "scope_contract": {
    "no_automatic_dependency_closure": true,
    "candidate_forbidden_ids": [
      "K4-GATE"
    ],
    "excluded_feature_tasks": [
      "P5-T02",
      "P5-T03",
      "P5-T04"
    ],
    "optional_performance_experiments": [
      "C0-T01",
      "H2-T01",
      "H3-T01",
      "H4-T01",
      "H6-T01",
      "H7-T01",
      "K3-T02",
      "S0-T01",
      "UP-T01",
      "K2-T05"
    ],
    "budget_authorization": "PROPOSED_ONLY_NOT_ADDITIVE",
    "feature_work_is_not_acceptance_requirement": true
  },
  "governing_documents": [
    "AI_EXECUTION_PROMPT.md",
    "plans/00-master-plan.md",
    "plans/02-task-registry.md",
    "plans/03-release-scopes.md",
    "plans/08-validation-budget-and-estimate.md",
    "design/08-target-sampling-and-baseline.md",
    "plans/11-optional-performance-experiments.md",
    "research/06-upstream-performance-assessment.md"
  ],
  "research_preparation_20261024": {
    "status": "RESEARCH_AND_CONTRACT_PREPARED_NOT_IMPLEMENTED",
    "candidate": "C1_W4_K3_SAMPLED_MTP_EXACT_SPARSE_Q",
    "report": "docs/ninfer-v4-performance-reset-20261024.md",
    "preparation": "output/ninfer-v4-performance-reset-20261024/preparation.json",
    "performance_gain": null,
    "production_code_changed": false,
    "GPU_execution_authorized": false,
    "legacy_tasks_and_assertions_unchanged": true,
    "scope": "Research advisory and proposed future isolated contract; no new implementation task, release gate, or executable GPU budget"
  },
  "sampled_q_implementation_20261024": {
    "status": "CPU_BUILD_REVIEW_COMPLETE_GPU_NOT_RUN",
    "source_tree": "f557ab41f68105a629344c2acb5adb6f9a38c783",
    "report": "docs/ninfer-v4-sampled-q-20261024.md",
    "receipt": "output/ninfer-v4-sampled-q-20261024/evidence/CPU-DELIVERY-RECEIPT.json",
    "CPU": {
      "run": 12,
      "failed": 0
    },
    "default_candidate_BO": "PASS",
    "review_open_findings": 0,
    "GPU_model_HTTP": 0,
    "GPU_budget_frozen": false,
    "optimization_qualification": false,
    "production_release": "PENDING",
    "legacy_tasks_unchanged": true
  },
  "sampled_q_hardware_preparation_20261024": {
    "status": "FROZEN_READY_FOR_AUTHORIZED_MINIMAL_GPU_WINDOW_NOT_RUN",
    "source_tree": "b9d4bfb714d537e1b9a51d94d3716c9441035107",
    "freeze_SHA256": "a0cef613dcd81bff75c9a6ed36f4f0aa294d42d2ab58ecd327f75b1347722d2f",
    "report": "docs/ninfer-v4-sampled-q-hwprep-20261024.md",
    "receipt": "output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/PREPARATION-DELIVERY-RECEIPT.json",
    "CPU_reused": 12,
    "new_numeric_reference_PASS": 4,
    "new_profile_PASS": 5,
    "GPU_model_HTTP": 0,
    "budget": {
      "HTTP_warmup": 2,
      "chat": 8,
      "native_requests": 4,
      "wire": 12
    },
    "GPU_execution_authorized": false,
    "budget_frozen": true,
    "original_service": "KEEP_STOPPED",
    "optimization_qualification": false,
    "legacy_tasks_unchanged": true
  },
  "sampled_q_minimal_hardware_20261024": {
    "status": "MINIMAL_VALIDATION_INCOMPLETE_CHAT_AUDIT_MEMSET_BUDGET_EXHAUSTED",
    "report": "docs/ninfer-v4-sampled-q-hardware-20261024.md",
    "summary": "output/ninfer-v4-sampled-q-hardware-20261024/final-summary.json",
    "freeze_consumed": "a0cef613dcd81bff75c9a6ed36f4f0aa294d42d2ab58ecd327f75b1347722d2f",
    "numeric": "4_PASS_8_DIRECT_4_CAPTURE_8_REPLAY",
    "native": "4_REQUEST_8_DECODE_PASS_BITWISE",
    "raw_formal_pass": 2,
    "raw_tool": "ABORTED_AUDIT_MEMSET_CAP",
    "candidate_Chat": "NOT_STARTED",
    "model_submissions": 8,
    "wire": 5,
    "cleanup_elapsed_seconds": 164.736202135,
    "optimization_qualification": false,
    "additional_budget": 0,
    "original_service": "KEEP_STOPPED",
    "all_prior_failures_preserved": true,
    "legacy_tasks_unchanged": true
  },
  "sampled_q_continuation_20261024": {
    "status": "CONTINUATION_COMPLETE_NOT_QUALIFIED",
    "report": "docs/ninfer-v4-sampled-q-resume-20261024.md",
    "summary": "output/ninfer-v4-sampled-q-resume-20261024/final-summary.json",
    "freeze_consumed": "8213b6427eff4be604a49b0c7c780eb0a26a96cafb1300d5f3aeda7cf90dc512",
    "new_CPU_PASS": 5,
    "new_GPU_numeric_native": 0,
    "BO": "REUSED_IDENTICAL_BINARIES",
    "new_Chat": 6,
    "new_HTTP_warmup": 0,
    "new_wire": 7,
    "cumulative_model_submissions": 14,
    "cumulative_wire": 12,
    "old_aborted_attempts_preserved": 1,
    "numeric_native": "REUSED_PASS_NOT_RERUN",
    "three_quality_pairs": "PASS_BOTH",
    "control": "BOTH_FAIL_OUTPUT_LIMIT_REASONING_ONLY",
    "program_unit_time_change": {
      "java": 0.017534362614614718,
      "reasoning": 0.006690667825605789,
      "tool": -0.031119393156713526
    },
    "complete_decode_net_gain": null,
    "cleanup_elapsed_seconds": 162.738572117,
    "original_service": "KEEP_STOPPED",
    "optimization_qualification": false,
    "p95": null,
    "additional_budget": 0,
    "all_prior_failures_preserved": true,
    "legacy_tasks_unchanged": true
  },
  "sampled_q_closure_20261024": {
    "status": "CLOSED_NOT_ADOPTED_NO_FURTHER_TESTS",
    "source": "EXPLICIT_USER_REQUEST",
    "previous_result": "sampled_q_continuation_20261024",
    "all_results_and_failures_preserved": true,
    "no_additional_budget": true
  },
  "post_sampled_selection_20261024": {
    "status": "PREPARATION_COMPLETE_NOT_IMPLEMENTED_NOT_EXECUTABLE",
    "scope_id": "K2-Q4-COMPACT-T4",
    "integration_boundary": "BENCH_ONLY_FIRST_THEN_EXISTING_VERIFY_AND_EXACT_T4_REQUIRED",
    "report": "docs/ninfer-v4-post-sampled-selection-20261024.md",
    "preparation": "output/ninfer-v4-post-sampled-selection-20261024/preparation.json",
    "proposed_budget": "output/ninfer-v4-post-sampled-selection-20261024/proposed-budget.json",
    "base_tree": "b9d4bfb714d537e1b9a51d94d3716c9441035107",
    "profiles": [
      "original_s4_b3",
      "compact_s4_b3",
      "compact_s5_b3"
    ],
    "new_builds": 0,
    "new_GPU_model_HTTP": 0,
    "new_source_changes": 0,
    "new_mandatory_stage_gates": 0,
    "new_executable_ledger": false,
    "actual_performance_gain": null,
    "original_service": "KEEP_STOPPED",
    "optimization_qualification": false,
    "all_prior_failures_preserved": true,
    "legacy_tasks_unchanged": true
  },
  "q4_compact_t4_preparation_20261024": {
    "status": "CPU_BO_REVIEW_READY_GPU_UNRUN",
    "scope_id": "K2-Q4-COMPACT-T4",
    "report": "docs/ninfer-v4-q4-compact-t4-20261024.md",
    "source_tree": "ebc4158e3146b87d65ca68427377476045af4646",
    "freeze_sha256": "55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717",
    "remote_window": "/home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1",
    "CPU_new_cases": 8,
    "CPU_passed": 8,
    "build": "PASS_BO_SM89_NO_GPU",
    "review": "NO_BLOCKING_STATIC_FINDINGS",
    "ledger": "PRISTINE",
    "GPU_executions": 0,
    "model_HTTP": 0,
    "old_tests_rerun": 0,
    "phase_boundary": "BENCH_ONLY; future runtime requires existing Verify plus exact T4",
    "GPU_budget": {
      "numeric_scenarios": 4,
      "direct": 12,
      "captures": 3,
      "replays": 126,
      "algorithm_kernels": 138,
      "model": 0,
      "HTTP": 0,
      "hard_seconds": 600,
      "cleanup_seconds": 420
    },
    "default_dispatch_changed": false,
    "Target_sampling_changed": false,
    "Pi_budget_changed": false,
    "original_service": "KEEP_STOPPED",
    "all_failures_G1_18_C1_gap_preserved": true,
    "actual_performance_gain": null,
    "optimization_qualification": false
  },
  "q4_compact_t4_hardware_20261024": {
    "status": "MEASUREMENT_COMPLETE_NO_ADOPTION_CONTROLLER_READBACK_FAILED",
    "scope_id": "K2-Q4-COMPACT-T4",
    "report": "docs/ninfer-v4-q4-compact-t4-hardware-20261024.md",
    "source_tree": "ebc4158e3146b87d65ca68427377476045af4646",
    "freeze_sha256": "55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717",
    "ledger": "COMPLETE_CONSUMED",
    "candidate_exit": 0,
    "controller_exit": 1,
    "numerical": "PASS_BITWISE_FP64_GUARDS",
    "Graph": "PASS",
    "profiles": [
      {
        "name": "original4",
        "median_us": 161.79199516773224,
        "latency_increase_percent": -0.0,
        "saved_us": 0.0,
        "paired_groups_faster": 0,
        "screening_signal": false,
        "resources": {
          "local_bytes": 0,
          "max_threads": 256,
          "registers": 78,
          "static_shared": 29696,
          "theoretical_active_blocks_per_SM": 3
        }
      },
      {
        "name": "compact4",
        "median_us": 162.73599863052368,
        "latency_increase_percent": 0.5834673475735187,
        "saved_us": -0.9440034627914429,
        "paired_groups_faster": 8,
        "screening_signal": false,
        "resources": {
          "local_bytes": 0,
          "max_threads": 256,
          "registers": 78,
          "static_shared": 25600,
          "theoretical_active_blocks_per_SM": 3
        }
      },
      {
        "name": "compact5",
        "median_us": 163.93599659204483,
        "latency_increase_percent": 1.3251591477624542,
        "saved_us": -2.1440014243125916,
        "paired_groups_faster": 7,
        "screening_signal": false,
        "resources": {
          "local_bytes": 0,
          "max_threads": 256,
          "registers": 78,
          "static_shared": 32000,
          "theoretical_active_blocks_per_SM": 3
        }
      }
    ],
    "used": {
      "algorithm_kernels": 138,
      "captures": 3,
      "d2d_bytes": 0,
      "d2d_calls": 0,
      "d2h_bytes": 4148224,
      "d2h_calls": 13,
      "device_allocated_bytes": 363596800,
      "direct_ops": 12,
      "h2d_bytes": 98386944,
      "h2d_calls": 10,
      "helper_compute_kernels": 0,
      "memset_bytes": 37044092928,
      "memset_calls": 138,
      "model_submissions": 0,
      "numeric_scenarios": 4,
      "replays": 126,
      "wire": 0
    },
    "adoption": "KEEP_ORIGINAL4_NO_FURTHER_GPU_OR_MODEL_WINDOW",
    "permission_defect": "Root mode0600 terminal JSON unreadable to host; original failure preserved, read-only export reconciled completed results; frozen controller unchanged",
    "no_unresolved_operations": true,
    "old_tests_rerun": 0,
    "default_dispatch_changed": false,
    "Target_sampling_changed": false,
    "Pi_budget_changed": false,
    "original_service": "KEEP_STOPPED",
    "optimization_qualification": false,
    "full_decode_Chat_gain": null,
    "all_failures_G1_18_C1_gap_preserved": true
  },
  "q4_compact_user_closure_20261024": {
    "scope_id": "K2-Q4-COMPACT-T4",
    "status": "CLOSED_NOT_ADOPTED_NO_FURTHER_EXPLORATION",
    "added_GPU_model_HTTP_budget": 0,
    "old_result": "MEASUREMENT_COMPLETE_NO_ADOPTION_CONTROLLER_READBACK_FAILED",
    "evidence": "output/ninfer-v4-q4-compact-t4-hardware-20261024/final-summary.json",
    "sha256": "b75e58234d3e403f2bcc5a16dfd0b0d6e1d46dae016d92c72548997eb5f97662",
    "original_failure_and_permissions_preserved": true
  },
  "post_q4_next_selection_20261024": {
    "status": "SELECTION_ONLY_NOT_IMPLEMENTED_NOT_FROZEN",
    "scope_id": "H3-T01_STAGE_A_EXISTING_W6_REMAINING_AND_NATURAL_PERFORMANCE",
    "report": "docs/ninfer-v4-post-q4-selection-20261024.md",
    "preparation": "output/ninfer-v4-post-q4-selection-20261024/selection.json",
    "proposed_budget": "output/ninfer-v4-post-q4-selection-20261024/proposed-budget.json",
    "source_tree": "49bee647112ee171de35529028fc271494260751",
    "reused_numeric_Graph_cases": 6,
    "proposed_native_requests": 8,
    "proposed_decode_calls": 81,
    "full_window_resource_limits_frozen": false,
    "executable_ledger_created": false,
    "new_source_changes": 0,
    "new_builds_tests_GPU_model_HTTP": 0,
    "actual_performance_gain": null,
    "original_service": "KEEP_STOPPED",
    "default_dispatch_Target_sampling_Pi_budget_unchanged": true,
    "all_prior_failures_preserved": true,
    "legacy_tasks_unchanged": true,
    "new_mandatory_stage_gates": 0,
    "optimization_qualification": false
  },
  "w6_resume_implementation_and_hardware_20261024": {
    "status": "CLOSED_FIXED_W6_PILOT_STABILITY_GATE_NOT_MET",
    "scope": "H3-T01_STAGE_A_EXISTING_W6_REMAINING_AND_NATURAL_PERFORMANCE",
    "report": "docs/ninfer-v4-h3-w6-resume-20261024.md",
    "source_tree": "a728df11f92360108a3f12bb619137dafe4eed3d",
    "freeze_sha256": "273b37f4ec71945d3cd0865886d0c23db2ddefdd77bfa7ce66d7ab5409904679",
    "native_requests": 8,
    "decode_calls": 81,
    "HTTP_wire": 0,
    "numeric": "PASS",
    "state": "PASS_BITWISE",
    "pairs": [
      {
        "candidate_decode_tokens_per_round": 4.25,
        "candidate_measured_rounds": 16,
        "candidate_seconds_per_committed_token": 0.006021370529411763,
        "case": "java",
        "chronological_halves_reduction": [
          0.48197594217567497,
          -0.13754216201853597
        ],
        "complete_round_token_cost_reduction": 0.22746895463560168,
        "pilot_signal": false,
        "raw_decode_tokens_per_round": 3.0,
        "raw_measured_rounds": 16,
        "raw_seconds_per_committed_token": 0.007794341166666666,
        "sufficient_for_pilot_signal": true
      },
      {
        "candidate_decode_tokens_per_round": 5.25,
        "candidate_measured_rounds": 16,
        "candidate_seconds_per_committed_token": 0.004849683166666667,
        "case": "reasoning",
        "chronological_halves_reduction": [
          0.1593085607305662,
          0.24083823954626282
        ],
        "complete_round_token_cost_reduction": 0.20377264016821872,
        "pilot_signal": true,
        "raw_decode_tokens_per_round": 3.8125,
        "raw_measured_rounds": 16,
        "raw_seconds_per_committed_token": 0.0060908270819672134,
        "sufficient_for_pilot_signal": true
      }
    ],
    "pilot_signal": false,
    "additional_budget": 0,
    "next_action": "CLOSE_FIXED_W6_WITHOUT_ADDITIONAL_MEASUREMENT",
    "r2_window_seconds": 297.884335454,
    "r2_actual_resources": {
      "algorithm_kernels": 95027,
      "captured_copy_calls": 7488,
      "captured_kernel_calls": 45328,
      "captures": 55,
      "d2d_bytes": 5137309696,
      "d2d_calls": 3028,
      "d2h_bytes": 1229026832,
      "d2h_calls": 942,
      "device_allocation_bytes": 116536932357,
      "device_allocation_calls": 30,
      "direct_kernels": 23303,
      "h2d_bytes": 89571449760,
      "h2d_calls": 5596,
      "memset_bytes": 5609952228,
      "memset_calls": 16738,
      "replays": 88
    },
    "r1_failure": "INVALID_ONE_LAYER_DRIVER_GEOMETRY_PRESERVED_AND_REPAIRED",
    "r1_direct_Op_attempted": 3,
    "r2_direct_Op_attempted": 3,
    "supplemental_budget_explicitly_authorized": true,
    "old_six_numeric_cases_reused_not_rerun": true,
    "new_product_default_changes": false,
    "default_dispatch_Target_sampling_Pi_budget_unchanged": true,
    "original_service": "KEEP_STOPPED",
    "GPU_compute_pids": [],
    "cleanup": "VERIFIED",
    "all_prior_failures_and_gaps_preserved": true,
    "new_mandatory_tasks_or_gates": 0,
    "p95": null,
    "optimization_qualification": false,
    "stage_attribution_complete": false,
    "allocator_highwater_bytes": null
  }
}
```


## C0 r3最小TTFT pilot已完成，收益归因不成立

[实跑报告](../../ninfer-v4-c0-ttft-pilot-20261023.md)与[机器汇总](../../../output/ninfer-v4-c0-ttft-pilot-20261023/final-summary.json)记录P4→C0已完成：4个新Chat全部PASS、10wire、6次模型提交含2warmup，246.142777927秒安全收尾；没有本轮失败。21份冻结工具SHA及request/raw哈希核验通过。原服务STOPPED、候选退出、GPU空，未知请求/未完成导出/新增附件缺口均0。冻结目录已single-use消耗，禁止重启或追加样本；上文准备预算及全0状态仅为历史，不是余额或当前待办。

两端branch均真实source=l2，恢复55293 tokens，实际P=55374、computed_prefill=81；P4/C0恢复字节1333980256/1336349835。客户端首个非空语义delta TTFT为0.943552271/0.959943143秒，C0本次观察约慢1.737%，n=1不能形成稳定回退或收益结论。冻结分析保持`INCONCLUSIVE_TTFT_CONTROL_NOT_SATISFIED`：P4同样深L2、两端queue为0.618971645/0.641931568秒均超过50ms、seed export为1333034412/1335401900字节不等。不放宽对照断言，不把L2恢复成功等同C0独有收益。

post-copy publication为14.372465950/7.060492013秒，描述性降低约50.87%；它不是严格配对，也不等同TTFT获益。V04仍未证实，p95=null、optimization_qualification=false、K4=false；无正式性能或发布资格。采样及Pi medium/32768不变，18处G1差异、C1附件缺口及全部历史失败保留。不再把本次scope列为待开工或自动补测任务。

进一步源/日志复核修正了实验假设：P4命中`stable_prefix`，C0命中`routed_session`；执行器先发布boundary alias再发布session，最终publication_finished_ns表示二者全部完成。因此P4可在最终publication完成前已经恢复深前缀，原“最终发布未完即无任何可恢复深前缀”的假设错误。queue指标是admitted−submitted，恢复发生在admit之前，包含恢复/准入开销，不能将其超50ms归咎于外部排队竞争。冻结门槛仍原样判不满足，不改gate或补发。独立原始证据只读复核无阻断：10组request/raw SHA与长度相符、4个SSE各1个DONE且finish为tool_calls、21冻结SHA一致；复核未运行测试。
