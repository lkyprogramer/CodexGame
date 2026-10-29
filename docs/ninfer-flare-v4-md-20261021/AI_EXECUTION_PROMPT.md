# V4当前执行入口

## 当前准备：原P4→修复P4的HTTP对照已冻结，未运行GPU

`P4_EXPORT_PUBLICATION_PIPELINE_HTTP_V1=CPU_ONLY_PREPARED_FROZEN_NOT_EXECUTED`。经jssh29复用现有controller/guardian/HTTP驱动，14项新工具CPU合同通过，真实旧日志离线核对保留原job7缺口，初审的四Chat发布终态覆盖缺口已修复，独立复审无阻塞。复用两份serve、原4个HTTP输入及P4 token/position预检，不重建、不重跑旧任务。

冻结根 `/home/hhtele/ninfer-v4-export-pipeline-prep-20261025/prepared-window-r1`；freeze SHA `0dca60d4e89be0205011b30bb8824154eca74aed209620b36337419c7edbeb4a`。账本PRISTINE/全0，runtime不存在。严格原P4→修复P4，0native、8Chat＋2内置warmup、14wire、最多10模型提交；硬1200秒/1020秒清理。实机预计6–10分钟，证据核算另20–40分钟，当前不自动执行。

最后Chat后不预等publication而发一次身份绑定SIGTERM，要求≤30秒自然exit0及四Chat声明job终态；信号发送区间区分LIVE_DRAIN、IDLE_CLOSE与不确定。缺失/重复/错配或发布失败明确不合格，缺真实source-release重叠仅记机制证据不足。可见job不必连续，不将host-only发布冒充全部可观测。

本轮GPU/模型/推理HTTP均0，原服务STOPPED身份不变，默认分派、Target采样、Pi medium/32768及全部历史失败/18G1/C1/Baseline缺口保留。真实关闭排空和性能仍未测，优化/生产资格false。后续需新的明确实机授权，不能重启旧已消费窗口。

[冻结回执、空账本、CPU/评审与实机预算](../ninfer-v4-export-pipeline-prep-20261025.md)。以下历次“当前/准备/结果”均为原样保留的历史，不覆盖本节或授予执行额度。

## 当前修复：导出与 CPU 发布解耦，CPU 与构建完成

`P14_EXPORT_PUBLICATION_PIPELINE=CPU_VERIFIED_BUILDABLE_HARDWARE_NOT_RUN`。2026-10-25经jssh29在隔离分支 `codex/p14-export-publication-20261025` 修复已观察的跨job串行阻塞：独立导出线程、单槽交接、单FIFO发布线程。lane只在真实导出结束/排空后释放，CAS/发布顺序和关闭排空合同保留；不把复制完成当发布完成，也不把三份pipeline镜像当全局内存上界。

最终树 `7477294d629edffddef713d22c2d7589493d4271`，相对P14诊断P4基点 `d002a2183d54e1562cd1f53c50cf47155b1cb38f` 仅7文件变化。BO产品构建和10项CPU合同通过，真实coalescing补证后独立复审无阻塞；P14 trace为OFF。GPU/模型/推理HTTP均0，实际TTFT收益尚未测，性能与生产资格仍false。原服务STOPPED且镜像/参数/cache身份不变，默认分派、Target采样、Pi medium/32768不变；旧失败、18G1、C1及Baseline缺口全保留。

下一窗口仅建议原P4对修复P4：0native、8新Chat＋2内置warmup、14wire、10模型，硬20分钟/第17分钟清理；预计实机6–10分钟。现有controller需窄适配两端P4、最后job终态和≤30s自然SIGTERM，再冻结新空账本，准备估1.5–3工程小时。当前未冻结、未授权执行GPU，不重启旧已消费入口或关闭实验。

[修复、验证、限制与最小实机预算](../ninfer-v4-export-pipeline-20261025.md)。下方历次“当前/准备/结果”为完整保留的历史快照，不覆盖本节或提供新执行额度。

## 最新实机结果：P1—P4整包对照已结束，发现准入等待回退

`P14_BO_P4_W4_WHOLE_PACKAGE_AND_ROUND_TRACE_V1=COMPLETED_WITH_PERFORMANCE_REGRESSIONS_AND_DISCLOSED_LIMITATIONS`。2026-10-25经jssh29执行冻结窗口，19分6.7秒结束；8native/80decode、8Chat＋2warmup、14wire、18模型提交全部记账，不再使用旧账本执行。第19分钟已清理，原服务保持停止，GPU无计算进程。

整包未形成一致提速：Java native每token成本增加2.12%；中文减少40.19%来自更多token/轮，单轮仍慢2.03%，跨版本生成内容不同。Chat短冷/短热/长冷TTFT增加313.20%/737.31%/56.80%，L2长热减少6.29%。两端均真实恢复16991tokens。四项trace轨迹与Graph见证通过，观测开销0.058%–0.359%；P4 Target主体占GPU阶段约80.1%，Fold约1.5%。

新回退已由源码与job时间关联：同一publication worker串行导出和CPU发布，前一个发布阻挡下一导出，C1准入再等待lane export。下一改造应先处理这条已观察链路，保留安全barrier和发布合同；当前仅报告，不自动开工、加请求或重开关闭实验。

BO有2次cache publication失败，旧schema缺逐job原因；P4最后job7缺发布终态。HTTP两候选按冻结stop -t2退出137/OOMfalse，不声明优雅排空通过。模型响应均完整，但性能/生产资格仍false，p95=null。217份导出文件SHA已验证；旧失败、18处G1差异、C1与Baseline缺口保留。

[完整结果、热点和证据](../ninfer-v4-p14-performance-hardware-20261025.md)。以下“当前/准备/结果”均为保留的历史记录，不授予重跑额度。

## 当前准备：P1—P4整包对照与真实整轮归因，未运行GPU

`P14_BO_P4_W4_WHOLE_PACKAGE_AND_ROUND_TRACE_V1=CPU_ONLY_PREPARED`。两端为可复现BO/O tree6022c83与最终P4 tree35d3dd9，包含legacy rk4v4-e8→midrise rk4v4的整包变化，不能冒充原B29复现或单项提速。复用原服务二进制和既有natural/owner/HTTP驱动；两端诊断BO构建、CPU合同、12项新frontend实际预检与独立集成评审完成。六对token/positions相同，长共有前缀16992 token。所有首轮构建/预检失败保留。

新窗口`/home/hhtele/ninfer-v4-p14-performance-prep-20261025/prepared-window-r1`，freeze `0712e94eb92bd65a70897c0024e80e1384a3acd846aef4d73946a9ffa7aef6ab`，账本PRISTINE/全0，无runtime。仅准备授权，不自动执行。拟议8native/≤80decode、8Chat＋2内置warmup、14wire、总≤18模型提交；native≤72capture/152replay/1376256算法kernel，HTTP原二进制不逐kernel拦截。预计12–20分钟，硬30分钟/第27分钟清理。

plain测完整轮整包成本；trace只有真实7-event Graph见证、同端token/许可轨迹一致、完整8轮且观测开销≤5%才给阶段占比。实际TTFT/缓存命中/性能仍未测，p95=null，optimization_qualification=false。原服务STOPPED，默认分派、Target采样、Pi medium/32768及18G1/C1/全部旧失败缺口不变；不重跑旧Baseline，不重开任何关闭实验。

[完整准备、基点、预算和冻结证据](../ninfer-v4-p14-performance-prep-20261025.md)。以下历次“当前/准备/结果”为保留的历史记录，不授予重跑额度。

## 当前结果：GQA Bc64已实测，性能首筛未通过并关闭

2026-10-25授权的一次固定候选实测已完成，`K2-GQA-T4-BC64=CLOSED_PERFORMANCE_GATE_FAILED`。6数值场景、12direct、6capture、240replay、504kernel全部记账，0模型/HTTP，37.319秒完成清理。数值、Graph query0重复检查和缓存guard通过；query1只验证direct。8K耗时增加14.516%，32K减少14.865%，128K增加0.156%；未满足长上下文采用门槛且8K回退超过2%。不采用、不追加调参或32K补测，不自动进入append/native/Chat。

原`FAIL_NEW_SPILL`回执保留，此次只按用户授权版本化资源准入，固定源码/二进制不变。原服务保持停止；默认分派、Target采样、Pi medium/32768、18处G1及全部历史失败/缺口不变。[实测报告与冻结/原始证据](../ninfer-v4-gqa-t4-bc64-hardware-20261025.md)。以下历次“当前/准备/未运行”为历史记录，以本节结果为准，不授予新额度。

## 当前结果：T4 GQA Bc64在可行性检查结束，未运行GPU

`K2-GQA-T4-BC64`为`CLOSED_FEASIBILITY_NEW_SPILL`。隔离候选、BO构建、CPU合同和评审完成；ptxas原Bc32报告spill store/load各4B，Bc64为64B/72B，触发既定新增spill停止条件。它不是实测性能退化，也不关闭其它K2/H2/H6/H7/K3/W8/W16/utility候选。

候选树`b361766a8072943b2cde700ae12263efd16423db`；真实freezer已拒绝新增spill，未生成冻结窗口/空账本，actual direct/capture/replay/kernel/model/wire均0。单一配置结束，不扫参、不追加GPU。原服务保持停止，默认分派、Target采样、Pi medium/32768、18G1及全部旧失败/缺口不变。[结果与构建/资源证据](../ninfer-v4-gqa-t4-bc64-20261024.md)。下列历次“当前/准备/空账本”为历史，不授予新的执行额度。

## 当前结果：W6接续完成，平均收益存在但稳定性首筛未通过

`H3-T01_STAGE_A_EXISTING_W6_REMAINING_AND_NATURAL_PERFORMANCE`现为`CLOSED_FIXED_W6_PILOT_STABILITY_GATE_NOT_MET`。数值链/Graph及4native状态逐bit通过；4自然性能请求给出Java/中文推理单位token完整轮耗时下降22.75%/20.38%，但Java后半段反向增加13.75%，故冻结首筛未通过。不能把平均收益当稳定业务/HTTP提升，也不能说完全无收益。

已执行8native/81decode、0Chat/HTTP/wire；r2窗口4分58秒，55capture/88replay/95027算法kernel，所有资源未超限，候选已清理，GPU空，原服务继续停止。r1驱动layers1错误及失败成本保留；修复48层后由用户追加授权3direct和数值D2H/memset各512MiB，两个窗口累计6次direct尝试、95030算法kernel。旧6项数值PASS未重跑，旧失败/18G1/C1和Baseline缺口不变。

冻结`273b37f4ec71945d3cd0865886d0c23db2ddefdd77bfa7ce66d7ab5409904679`已消费，不得重启。源码树`a728df11f92360108a3f12bb619137dafe4eed3d`，只改隔离驱动/bench/audit，无产品默认分派、Target采样或Pi32768变动。追加预算0，不自动Chat/扫K/W8。`p95=null`、`optimization_qualification=false`，阶段拆分和allocator高水位仍未观测。[完整结果和证据](../ninfer-v4-h3-w6-resume-20261024.md)。以下历次当前/准备/空账本均为历史，不授予新预算。


## 当前选型：关闭Q4紧凑布局，补齐已有W6的完整decode实验

用户已关闭`K2-Q4-COMPACT-T4`，状态`CLOSED_NOT_ADOPTED_NO_FURTHER_EXPLORATION`，追加GPU/模型/HTTP预算0。紧凑四级/五级耗时+0.583%/+1.325%，保留原路径、原始数值证据与控制器权限失败；不再补测、扫参或进入完整模型验证。其他已关闭方向、全部失败、18处G1差异和C1缺口继续保留。

下一项只选`H3-T01_STAGE_A_EXISTING_W6_REMAINING_AND_NATURAL_PERFORMANCE`，当前`SELECTION_ONLY_NOT_IMPLEMENTED_NOT_FROZEN`。H3六项数值/Graph已通过；链在`WorkspaceArena(0)`处失败，native/Chat均未运行。复用源树`49bee647112ee171de35529028fc271494260751`及现有控制器，拟修失败链和异常审计、增加自然W4/K3对W6/K5完整轮对照，不开发W8，不恢复原已消费冻结入口。Q4/Q5共享Tile8是机会，27B Q6实际走SIMT c4/c6且成本增加；W6实际收益仍未知。

拟议无GPU准备4–6工程小时、≤6个新CPU合同；未来首筛仅失败链1场景/3direct/1capture/2replay，旧4native状态诊断固定9decode，另4自然性能请求各2warmup+16计时轮（≤72decode），合计8native/≤81decode、0Chat/HTTP/wire。Oracle状态请求不得算自然性能。完整窗口Graph/kernel/辅助传输预算尚未枚举，当前无可执行回执/账本、无GPU授权。后续窗口拟5–10分钟、硬20分钟/第17分钟清理；无净收益信号不追加Chat或扩W8。10%仅为两个prompt分别满足的后续投入门槛，不是提升预测或发布资格。

本轮仅jssh只读核对、旧证据计算与文档更新，0源码修改/构建/测试/GPU/模型/推理HTTP。原服务STOPPED、GPU空，镜像/参数/cache身份不变；默认分派、Target采样与Pi medium/32768不变。资格和发布继续独立，`p95=null`、`optimization_qualification=false`。[完整选型、收益条件和拟议预算](../ninfer-v4-post-q4-selection-20261024.md)。以下历次“当前/准备/空账本”均为历史，不能覆盖本节或重新提供额度。

## 当前结果：Q4 FFN紧凑布局首筛完成，未形成采用信号

`K2-Q4-COMPACT-T4` 最终为 `MEASUREMENT_COMPLETE_NO_ADOPTION_CONTROLLER_READBACK_FAILED`。4场景逐bit/原FP64/guard、3个Graph最小验证通过；12direct、3capture、126replay、138算法kernel全部完成且未超限，0模型/HTTP。原4级中位161.792μs，紧凑4级162.736μs（耗时+0.583%、8/32组更快），紧凑5级163.936μs（+1.325%、7/32组更快），均未达采用门槛。保留原路径，本轮结束，不追加GPU或进入完整decode/Chat。

GPU候选exit0，ledger/summary COMPLETE，310条reservation全部完成；控制器随后读取root所有的0600账本触发PermissionError、exit1。无GPU只读BO导出并校验34文件/7冻结附件，原owner/mode/失败栈保留；不能报整套工具全PASS。冻结控制器不覆盖，未来复用须先明确宿主UID/GID并验证文件所有权，不能重用已消费入口。

已消费freeze `55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717`，源码树 `ebc4158e3146b87d65ca68427377476045af4646` 保持；窗口约4.334秒，候选/guardian退出、GPU空、lease释放，原服务STOPPED身份不变。默认分派、Target采样、Pi medium/32768不变；全部失败、18处G1差异、C1缺口保留。短窗口局部结果不证明稳定退化或完整推理收益；p95=null，优化/发布资格未通过。

[完整结果、原始证据、权限失败与限制](../ninfer-v4-q4-compact-t4-hardware-20261024.md)。下文旧“准备完成/空账本/未运行”均为历史，不得据此重启已消费窗口。

## 当前交付：Q4 FFN 紧凑布局与五级预取 CPU/BO 准备完成

`K2-Q4-COMPACT-T4` 为 `CPU_BO_REVIEW_READY_GPU_UNRUN`。已在隔离分支完成默认false的共享layout、精确T4 bench-only原4级/紧凑4级/紧凑5级候选，以及复用驱动/控制器。8个新CPU合同通过；算子库、probe、原FP64参考消费测试目标与服务二进制构建通过（未跑旧测试）；独立静态集成评审无阻塞。三配置REG78、STACK/LOCAL0，SHARED29696/25600/32000。未运行GPU/模型/HTTP，不能声明逐bit或提速通过。

新源码树 `ebc4158e3146b87d65ca68427377476045af4646`，冻结根 `/home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1`，freeze `55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717`，空账本PRISTINE/used全0。后续首筛固定4场景、12direct、3capture、126replay、138算法kernel，0模型/HTTP；辅助资源详见冻结plan。硬10分钟、第7分钟清理。**本轮只交付准备，尚无实机执行；不得自动消耗预算。**

产品默认分派、Target采样、Pi medium/32768不改；原服务STOPPED，全部失败、18处G1差异、C1缺口保留。随机MTP及其他已关闭任务不再补测。先bench筛选，局部中位改善≥10%且≥12μs并至少24/32组改善，才考虑另行冻结完整Verify验证；接入须已有TextPhase::Verify＋精确T4，不能影响prefill。实测收益=null，资格/发布仍未通过。

[完整补丁、构建、资源、冻结入口与限制](../ninfer-v4-q4-compact-t4-20261024.md)。下文此前“尚未实施/当前准备/待执行”等为保留的历史快照，以本节为准，不构成重跑或新增授权。

## 当前准备：随机 MTP 已关闭，下一项为 Q4 FFN 紧凑 shared 布局

用户已明确随机 MTP 就此收尾，不再追加补测：`CLOSED_NOT_ADOPTED_NO_FURTHER_TESTS`。保留 q/Graph/native 最小一致性通过、Chat无稳定整体收益、旧tool中止、control两端输出耗尽和全部成本；不得重启已消费入口。

下一唯一优先准备为 `K2-Q4-COMPACT-T4`（候选代号，不新增强制阶段门禁）：仅 C1/W4 的 Q4 FFN融合SwiGLU/实际T4，移除每stage未使用的1024B Q5 high区。原4级/min3与紧凑4级/min3、紧凑5级/min3比较；首筛仅bench，完整链需既有TextPhase::Verify限界，不能用T4推断阶段；默认分派、Target采样、Pi32768、Q5/Mixed及其他shape保持。29源树仍b9d4bfb714d537e1b9a51d94d3716c9441035107；原BO静态函数REG78/SHARED29696/LOCAL0，未新增构建或运行kernel。原服务STOPPED。

拟议首筛4输入/12direct/3capture/126replay/138算法执行，0模型/推理HTTP，硬10分钟、第7分钟清理；helper memset/copy也有有限提案上限。每图4correctness＋6warmup＋32timing。**尚未实施、未冻结实机回执/账本、不构成执行授权**；只有局部逐bit/性能达到门槛才提新的完整decode窗口，不复跑旧任务。可行性先限4工程小时，补丁/BO/CPU/评审约6–10小时，驱动冻结另1–2小时。

[完整源码依据、实施边界、预算与止损](../ninfer-v4-post-sampled-selection-20261024.md)。当前收益预测=null；2%/4.5%/8%只是假定算子份额和局部改善后的情景，不能当实测。全部历史失败、18处G1差异、C1缺口及原始资料保留，性能/发布资格仍未通过。以下旧“当前/待执行”段落为历史记录，以本节为准。

## 当前结果：随机 MTP 接续完成，未形成稳定提速信号

`CONTINUATION_COMPLETE_NOT_QUALIFIED`。Graph memset 预算工具已修复；新增 CPU 5/5 PASS，复用原 BO 二进制、q/Graph/native 及已完成 Chat，未重跑。新窗口只发 6 个 Chat、7 个 wire、无新增 HTTP warmup；两窗口累计 14 次模型提交、12 个 wire，包含旧 tool 中止成本。

Java、中文推理、工具调用两端均 PASS；候选 Program 单位 token 耗时分别 +1.75%、+0.67%、−3.11%。工具题实际请求 4.355→5.053 秒，输出 649→808 token，不能报整体加速。控制题两端均耗尽 2048-token 夹具预算、只有 reasoning 无最终 content，保留 FAIL，不算有效性能胜出。每题一对、部分跨窗口、无新增 HTTP warmup，统计/性能/发布资格未通过。

新入口 `/home/hhtele/ninfer-v4-sampled-q-resume-20261024/prepared-window-r2`、freeze `8213b6427eff4be604a49b0c7c780eb0a26a96cafb1300d5f3aeda7cf90dc512` 已消费，账本 COMPLETE。162.739 秒清理，候选退出、GPU 空、lease 释放，原服务 STOPPED、身份不变。默认分派、Target 采样、Pi medium/32768 不改；所有旧失败、18 处 G1 差异与 C1 缺口保留。不得重启旧/新已消费入口或自动追加样本。

[完整结果、资源、原始证据与限制](../ninfer-v4-sampled-q-resume-20261024.md)。92 项原始文件及 22 项本地冻结 SHA 核验，独立工具/结果评审无阻塞。p95=null、optimization_qualification=false。以下各轮“当前/未运行”说明均为历史快照，不构成当前待办、空账本或执行授权。

## 当前结果：随机MTP q与状态通过，Chat因冻结资源预算不足中止

`MINIMAL_VALIDATION_INCOMPLETE_CHAT_AUDIT_MEMSET_BUDGET_EXHAUSTED`。冻结r1已消费：数值4/4、8direct/4capture/8replay PASS，q最大误差2.64e-8；native4请求/8decode及真实partial/cancel与direct/Graph状态PASS_BITWISE。greedy warmup/Java/中文推理完整PASS，tool因阶段memset_calls65536封顶、进程exit95中断；raw control和candidate Chat未启动，性能有效对数0，收益null。

准备时沿用64K memset cap却未核算Graph节点×replay，是预算推导失误；审计在下一次GPU调用前拒绝。164.736秒已清理，GPU空、lease释放、原服务STOPPED身份不变；没有默认分派/Target/Pi32768变更。总模型提交8/14、wire5/12；原RUNNING/RESERVED账本和所有失败保留，当前没有存活请求。不得重启旧入口、重跑已通过数值/native或自动追加请求/预算。

[完整结果、失败原因、资源与缺口](../ninfer-v4-sampled-q-hardware-20261024.md)。原始state远端只读归档，本机98项证据SHA核验；全部历史失败、18处G1差异和C1缺口保留。分布/性能/发布资格未通过。以下准备说明为历史快照，不能当空账本或执行授权。

## 当前交付：随机MTP完整q与实机窗口准备已冻结，尚未执行

分支`codex/sampled-q-hwprep-20261024`，树`b9d4bfb714d537e1b9a51d94d3716c9441035107`。raw/候选BO、新FP64参考4/4、新profile/ledger5/5通过；前轮CPU12组复用未重跑，两路评审开放0。本轮GPU/模型/HTTP均0，原服务STOPPED，默认分派、Target与Pi32768不改。

唯一新入口`/home/hhtele/ninfer-v4-sampled-q-hwprep-20261024/prepared-window-r1`，freeze`a0cef613dcd81bff75c9a6ed36f4f0aa294d42d2ab58ecd327f75b1347722d2f`，空账本全0、无runtime。冻结4场景/8direct/4capture/8replay、4native/≤12decode、8Chat＋2warmup/12wire、总≤14提交；全窗口GPU资源包含startup，硬20分钟、第17分钟清理。后续执行需明确GPU授权，不得运行已消费旧H3入口。预计窗口10–20分钟，结果分析30–60分钟。

[冻结回执、资源上限、缺口与验证](../ninfer-v4-sampled-q-hwprep-20261024.md)。完整q/状态诊断复用原控制器；自然partial未出现应记缺口，不新增请求。Program计时不等于完整round wall，所有GPU/分布/性能/发布资格未通过。以下旧“当前”说明保留为历史快照，以本节和新回执为准。

## 当前交付：固定W4随机MTP＋精确q的CPU/BO候选

隔离分支`codex/sampled-q-w4-20261024`、源树`f557ab41f68105a629344c2acb5adb6f9a38c783`已完成可构建补丁：默认OFF/候选ON BO均PASS，新增CPU12/12，两路评审P1/P2已关闭；保留r1失败。原服务STOPPED，GPU/模型/HTTP均0，Target与Pi32768不改。现行默认仍greedy，新路线仅显式构建、fresh/cache off；缓存/分布/状态/性能/发布资格未通过。

[交付、补丁与最小实机提案](../ninfer-v4-sampled-q-20261024.md)。仅CPU产物冻结；完整q的native诊断和全窗口GPU资源尚待适配/冻结，不可运行旧H3入口或把建议预算当执行授权。沿用现有控制器，不新建框架。下面历史研究与失败记录保留。

## 当前工作：性能复盘与sampled-q候选准备（未实施）

本轮已结合原始证据、29源码及固定上游资料复盘：局部优化缺关键路径份额、实验夹具与真实收益错位、驱动缺陷反复消耗窗口，均需纠正。唯一优先准备的新假设为C1/W4/K3 sampled MTP＋真实稀疏q接受修正，范围中等，收益未知；不能称为已证明的“最大收益/最小改动”。既有greedy＋Target sampling和131072优化头不重复开发；DFlash2匹配27B资产已存在，但适配范围大。

状态`RESEARCH_AND_CONTRACT_PREPARED_NOT_IMPLEMENTED`：无引擎补丁/BO/GPU/模型请求，仅8项离线有理数参考（不证明CUDA/随机数/状态资格）。现行delta-q合同保持权威，新general-q只是独立候选提案；必须携带实际完整条件q、保持Target参数和支持、独立proposal RNG，首筛cache off不抵扣缓存发布资格。原服务STOPPED，所有旧失败、18处G1差异及C1缺口保留。

后续候选范围与提出的单窗预算见[复盘与准备包](../ninfer-v4-performance-reset-20261024.md)；完整GPU资源尚未冻结，不授予执行权。不要重启已消费H3入口，不自动补测W6，不重跑旧任务，不新增另一套controller。下面原H3硬件结论仍有效，准备排序不改变原验收状态或历史账本。

## 当前结果：H3-T01 Stage A实机因新驱动初始化错误停止

`MINIMAL_VALIDATION_INCOMPLETE_DRIVER_WORKSPACE_ZERO_FAILURE`。唯一冻结r1实机已执行：6个独立Op数值/Graph场景PASS（6direct Op、6capture/12replay）；第7个GDN Record/Fold链因新驱动以合法0工作区需求构造非零Arena而Exit1，未进入链Op。产品路径已有最小容量处理，不归为W6数值或性能失败。native/Chat/warmup/wire/模型加载提交均0，完整逐bit与W4→W6 decode/TTFT收益均未建立。

24.560秒完成候选清理，GPU idle、lease free，原服务STOPPED/身份不变。原账本RUNNING/链RESERVED保留；实际进程均已退出，派生已知失败终态单列，无未知模型请求。失败链未写audit.json，已完成阶段小计18算法kernel，完整资源实际总量null并披露缺口。原始日志/账本/冻结身份已持久归档和本地SHA核验。

入口已消费，不可重启；本轮无补测或源码修改。后续只修驱动零容量与失败审计并版本化接续；复用6个PASS，不重跑旧任务，不开发W8，不改默认分派/采样/Pi32768。全部历史失败、18处G1差异和C1缺口保留，资格与发布PENDING。以下空账本/未运行等仅为历史状态。详见[实机结果与资源缺口](../ninfer-v4-h3-w6-hardware-20261024.md)。

## 历史准备：H3-T01 Stage A冻结记录（该入口已消费）

`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。隔离分支codex/h3-w6-existing-route-20261024，raw基点a5ba33de…，源树`49bee647112ee171de35529028fc271494260751`；没有新commit/push。默认/诊断BO构建、16具名CPU场景和双轴集成评审通过；Spec原1项P2仅定向修订复验case11，实际CPU场景执行17次，其他15复用。默认诊断开关OFF；产品默认None/0/Full与原显式W4/K3对照均保留，候选只显式使用现有W6/K5。不开发W8、不改Target采样/缓存格式/Pi32768。

唯一实机入口`/home/hhtele/ninfer-v4-h3-w6-20261024/prepared-window-r1`，freeze `4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc`；ledger PRISTINE全0、runtime不存在。新增数值收窄7场景/9direct Op/7capture/14replay，因为原P4 GQA T6有实际PASS且28个相关源码blob相同，直接复用。native2场景/4请求，计划9≤16decode调用；6Chat＋2warmup/10wire，总12模型工作提交。全窗口包括startup的capture199、replay69646、算法kernel34652160及分方向copy/memset调用与字节上限全部冻结；不得将数值7/14误当全窗口总量。

GPU预计5–10分钟，硬20分钟、第17分钟清理；结果审计0.5–1h。本轮0 GPU/模型/HTTP，原服务STOPPED/镜像参数cache身份未变。原失败、18处G1差异、C1/其他附件缺口保留；C0/K2-T01/K1-T01/K2-T05/H1继续关闭、追加预算0。真实W6逐bit/Graph/状态/收益未验证；资格与发布仍PENDING，p95=null、optimization_qualification=false。详见[冻结回执、预算与CPU证据](../ninfer-v4-h3-w6-stage-a-20261024.md)。以下旧选型/预算/准备状态均为历史，不构成可重用额度；GPU执行须有后续明确授权。

## 历史选型：H1收尾，H3-T01 Stage A先验证现有W6

H1-T01按用户要求`CLOSED_NO_FURTHER_MEASUREMENT`，追加预算0；原2个native逐bitPASS、4个重复保护截断失败、全部成本和资格缺口原样保留。C0/K2-T01/K1-T01/K2-T05继续关闭。

下一项仅选择`H3-T01 / A_EXISTING_W6_PILOT_ONLY`，profile `MTP_EXISTING_C1_W6_K5_VS_W4_K3_V1`：复用最大5草稿、现有六列MTP/Target/GQA/Graph，不开发W8、不叠加Lookup，不改默认分派/Target sampling/Pi32768。基点raw树a5ba33de12d75ab1e16a153020e4068094ee1757；拟议新分支尚未创建。本轮仅jssh只读核对及文档，0构建/测试/GPU/模型/HTTP。原服务STOPPED，18处G1差异、C1及全部历史失败/缺口保留。

拟议CPU≤16合同，新增T6数值8场景/10 direct Op/8 capture/16 replay，native2场景/4请求/≤16 decode调用，6 Chat＋2warmup/10wire，总≤12模型提交。数值capture/replay不包含模型启动，完整kernel/copy/Graph资源须由新驱动枚举冻结后才可执行，当前未授权GPU。工程准备8–16小时，GPU预计5–10分钟/硬20分钟/第17分钟清理，分析0.5–1小时；收益未知，10%仅为新profile正例净改善信号门槛。W8原80项总断言中的H3断言、31个发布scope及完整资格/发布继续PENDING，W6不抵扣W8资格。

[完整范围、依据与预算](../ninfer-v4-post-h1-selection-20261024.md)。以下旧选型、准备、结果和预算均为历史，不构成当前任务或可重用额度。`p95=null`、`optimization_qualification=false`。

## 历史结果：H1-T01最小窗口完成，状态通过、无采用信号

已执行唯一冻结r3（716ccfc4e830…），250.301秒清理完成。2个native场景/4请求/6次decode-or-verify逐bitPASS；6Chat＋2warmup、10wire、总12提交全部记账。实际36capture/339replay/303561算法kernel，全部资源在冻结上限内；账本COMPLETE，无unknown或未结束请求，controller/guardian退出，GPU idle、lease free，原服务STOPPED/PID0且镜像/argv/cache身份不变。

正式Chat候选47/128轮Lookup命中（36.72%），命中draft接受122/141。复制/工具/控制的完整decode每报告token耗时分别增加6.98%/4.28%/8.11%，未获采用信号。4个正例失败的Engine终态均repetition_cycle（wire映射length），是重复fixture撞上既有保护；保留原FAIL与raw，派生解释单列，不算模型答错或改为PASS。控制样本也命中7/22，no-hit≤1%资格未建立。

本轮profile结束、追加预算0，保持MTP与默认关闭Lookup，不重跑或放宽断言；不同seed/单对样本与保护截断限制因果结论。原采样/context/Pi32768、18处G1差异、C1及旧证据缺口保留。p95=null、optimization_qualification=false。[完整命中、状态、净收益与失败原因](../ninfer-v4-h1-hardware-20261024.md)。以下准备态、空账本与旧预算均为历史，不构成新执行授权。

## 历史准备：H1-T01 CPU补丁、BO与实机驱动

已通过jssh 29在隔离分支`codex/h1-lookup-packet-c1-w4-20261024`完成请求内整包Lookup。CPU16/16一次通过，原路径诊断、Lookup诊断及默认版三个BO构建PASS；本代理集成检查无已知阻断。原始BO头文件失败保留。真实27B消费TU的宏与对象引用已核对，默认Lookup及诊断开关关闭。

集成树`9e7c0a1f19721d0ba63db362da6d10b5cda7c8e0`，冻结SHA`716ccfc4e8308f7db34497d8edc6d6705aa1a843370b4efef1f073df42d22eb0`；runtime不存在，账本PRISTINE，GPU/模型/HTTP均0。固定C1/W4/K≤3、4gram/ring8192/16384槽；整包替换、许可后append，不改Target采样、原MTP对齐/下一轮、Graph或缓存格式。

下一步仅最小试验：2个新native状态场景/最多4次native请求、≤16次decode/verify；6个新Chat＋2warmup，10wire，共≤12模型工作提交。预计5–10分钟，硬20分钟/第17分钟清理，之后离线报告30–60分钟；当前未执行GPU。完整候选资格与发布仍独立，运行时数值/Graph/净收益均未通过。原服务STOPPED，采样/context/Pi32768、18处G1差异、C1及全部旧缺口保留；C0/K2-T01/K1-T01/K2-T05不再补测。[实现、冻结与完整预算](../ninfer-v4-h1-t01-20261024.md)。以下旧选型与预算均为历史，不能重启旧窗口。

## 历史选型：K2-T05收尾后选择H1-T01

K2-T05状态`CLOSED_NO_FURTHER_MEASUREMENT`，追加预算0，不再补测Op/T512/native/Chat；保留逐bit及4/4 Chat PASS、完整Prefill0.314%未达1%门槛和全部原始失败/成本。C0、K2-T01、K1-T01继续关闭。

唯一新选项为`H1-T01`，状态`NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED`。从raw树a5ba33de12d75ab1e16a153020e4068094ee1757开始，不携带未采用T1024分派。固定C1/W4/K3、4gram、ring8192；只在extent3且有完整后缀时整包选Lookup，否则原MTP。索引归RequestControl，正式committed后更新；原Target采样、Graph、MTP alignment/next proposal、许可和缓存格式不变，不声称命中就跳过MTP计算。

当前只读jssh源码/证据核对和文档，0新构建/测试/GPU/模型/HTTP，分支未创建。未来拟议CPU≤16合同；GPU最多2个新native状态场景/4请求/16次decode-or-verify，加6 Chat＋2warmup/10wire，共≤12模型工作提交，预计5–10分钟，硬20/清理17；资源与驱动必须另行冻结。本提案不授权执行，不复用旧已消耗预算。工程准备16–24小时；真实Lookup收益未知，5%仅为正例decode/token信号门槛。原服务STOPPED、采样/context/Pi32768、18处G1差异与C1缺口保持，p95=null、optimization_qualification=false。[完整选型、范围与预算](../ninfer-v4-post-k2-t05-selection-20261024.md)。本轮范围以此选择及注册表为准，以下旧状态/预算均按历史解释。

## 历史结果：Chat接续完成，4/4 PASS，未达到完整Prefill采用门槛

状态`CHAT_COMPLETED_4_PASS_NATIVE_SIGNAL_BELOW_THRESHOLD_KEEP_RAW`。2026-10-24经用户明确授权的新窗口已消费剩余4 Chat＋1 warmup／6 wire，新增native0，累计native13；旧raw warmup未重发。新冻结SHA`b9512345eb6d511d6f242aff465404907ec02dbe8661ec15d6012f0c26ade317`，接续账本COMPLETE、无unknown；原失败账本不改，旧GPU envelope不退款。请求ID已按响应头权威ID＋实例/request/Engine元组关联，7项定向CPU检查PASS，原CPU/BO证据复用。

文本和工具调用4/4 PASS且实际增量交付。TTFT文本2.296332→2.276107秒（观察改善0.881%），工具2.206091→2.198108秒（0.362%）；各仅一对、不证明稳定提速。旧12次native及完整状态/logits逐bitPASS复用并补回原始元数据，配对中位改善0.314%低于冻结1%门槛。两次warmup的OK.与精确OK断言不符，失败原样保留；夹具标点歧义不掩盖，也不放宽。

126.025秒完成候选清理，controller/guardian退出，GPU idle、lease free；原服务STOPPED，镜像/argv/cache身份及采样/context/Pi medium/32768不变。旧失败、18处G1差异、C1和Baseline缺口保留，首轮失败最终GPU总数仍null。新旧相关wire/元数据/原始logits已本地镜像，大状态完整包在远端持久保留。`p95=null`、`optimization_qualification=false`，本窗口余额0、不自动追加或恢复旧窗口。[完整报告与证据](../ninfer-v4-k2-t05-chat-remaining-20261024.md)。以下暂停、失败和空账本仅为历史，不构成新授权。

## 历史首轮：完整Prefill因logits诊断构建缺陷停止，CPU修复完成

状态`FULL_PREFILL_CHAT_STOPPED_RAW_LOGITS_BUILD_SCOPE_CPU_REPAIRED`。唯一r2窗口已执行并关闭；raw首个warmup在提交后的导出阶段报`actual target logits capture missing`。72个原始状态段／306,659,921字节保留，原target logits与导出元数据缺失；候选、五组有效计时和Chat均未运行。不能声明完整Prefill、逐bit或TTFT通过，不能外推原算子段收益。

根因已由实际编译命令确认：tests目录source property未作用于ninfer_engine目录，模型TU缺少诊断宏。独立overlay增加`TARGET_DIRECTORY ninfer_engine`后，raw/candidate BO增量构建及实际调用方对象引用检查PASS，修复阶段0 GPU/模型/HTTP。原r2源码、四个冻结二进制、原始失败和账本保持不变；新二进制尚未冻结或实跑。

原账本保留RUNNING／raw预留6、完成0，不代表仍有进程；原始迭代日志1次RESERVED，不算6次实际执行。CUDA最终累计值未落盘，MODEL_READY检查点不能当总用量。约61.944秒完成精确候选清理，GPU idle、lease free，原服务STOPPED且镜像/参数/cache身份不变。实际Chat/warmup/wire均0，不重发失败warmup、不跳过数值门禁，不追加旧预算或重启single-use窗口。

剩余完整对照需新版本工具/账本：12 native（含两侧正确性warmup和五次测量）、4 Chat＋2 HTTP warmup、8 wire，原失败成本另列；这些不是本轮余额或自动新增授权。预计准备0.5–1小时、实机8–15分钟，20分钟硬限/第17分钟清理。旧Baseline/已通过任务/T512不重跑；18处G1差异、C1缺口、全部失败与Pi medium/32768及采样/context保留。`p95=null`、`optimization_qualification=false`。[实机失败、CPU修复与证据边界](../ninfer-v4-k2-t05-full-prefill-hardware-20261023.md)。以下“GPU未运行/空账本”及准备预算均为历史，不能据此恢复旧窗口。

## 历史准备状态：T1024完整Prefill／Chat驱动与r2空账本当时已冻结

状态`CPU_BUILD_REVIEWED_FULL_PREFILL_CHAT_PREPARED_GPU_NOT_RUN`；当前候选树`abc974d38d861c4fa72692345aadfc8565624fa3`、raw树`a5ba33de12d75ab1e16a153020e4068094ee1757`，唯一入口`prepared-window-r2`，freeze SHA `4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d`。raw/candidate四个诊断可执行文件BO构建通过，29项新CPU检查及主代理集成评审完成。r1保留并退役，预算不叠加；原服务STOPPED，0 GPU/模型/HTTP，runtime不存在、ledger全0。

预算固定12 native Prefill、4 Chat＋2 HTTP warmup、8 wire；capture≤256、replay≤73728、算法kernel≤35651584，copy/memset调用与字节已分方向冻结。硬限20分钟、第17分钟关闭admission并清理候选；预计实机8–15分钟，当前尚未执行。tool_choice仅用已支持auto，精确工具/JSON断言不放宽；Pi medium/32768、现网采样/镜像/cache、18处G1差异、C1缺口及全部失败保留。`p95=null`、`optimization_qualification=false`。[完整预算、回执与验证边界](../ninfer-v4-k2-t05-full-prefill-prep-20261023.md)。以下未冻结驱动/预算及旧空账本表述仅为历史，不构成新授权或余额。

## 历史接入状态：T1024候选CPU交付完成

状态`T1024_PREFILL_INTEGRATED_CPU_BUILD_REVIEWED_GPU_NOT_RUN`，候选树`9818eafa5d2660c2ea9682cc7653e6603f21ebb5`，分支`codex/k2-t05-prefill-integration-20261023`。BO构建、新增16项CPU路由/边界合同及主代理集成评审完成；精确Q/K/V地址断言已补齐，两次构建依赖失败保留。本轮0 GPU/模型/HTTP；T512不补测，其余shape及Verify/Decision/segmented保持raw，原kernel/FP64参考/state/工作区布局不改。

原服务STOPPED，采样/context/Pi medium/32768、18处G1差异、C1缺口及全部旧失败保留；不重跑旧任务。完整Prefill/Chat尚未运行，拟议12 native prefill＋4 Chat＋2 warmup＝18模型工作单位、8 wire；驱动与细粒度GPU预算尚未冻结。准备3–5工程小时，实机预计8–15分钟、建议20分钟硬限/第17分钟清理；不构成GPU或发布授权。`p95=null`、`optimization_qualification=false`。[接入报告与冻结回执](../ninfer-v4-k2-t05-prefill-integration-20261023.md)。以下未授权产品接入、旧空账本/预算等表述按历史阶段解释，不是当前状态或余额。

## 历史实机状态：K2-T05算子段筛选完成，T1024有信号

状态`GPU_MIN_SCREEN_COMPLETED_T1024_SIGNAL_T512_TIMING_INCONCLUSIVE`。4个数值场景的完整BF16 Q/K/V及conv state逐bit、原FP64参考/guard全部PASS，T512/T1024 raw/split共4张实际Graph的函数/参数/几何/copy/依赖见证及后续逐bit全部PASS。T1024卷积＋原state更新＋raw三次提取整段配对中位下降36.4834%，5/5批更快，达到`SEGMENT_SIGNAL_NOT_K4`；T512观测下降38.4411%且5/5更快，但3批host提交占比超过冻结25%门槛，收益为INCONCLUSIVE，不放宽门槛或追加补测。

实际严格为4场景/20 direct Op/4 capture/184 replay（8 correctness＋16 warmup＋160 timing）/384算法kernel，0模型/HTTP；辅助传输均在原冻结上限内。24条reservation全部完成、无unknown。控制器6.767秒结束，候选在6.701秒清理；原服务STOPPED、GPU idle、lease free。本single-use窗口已消耗、追加预算0，禁止据历史空账本重新启动。

默认分派、采样/context/Pi medium/32768、18处G1差异和C1缺口不变，旧失败与CPU/BO原始证据保留、不重跑。仅T1024获得算子段信号，完整prefill/Chat及产品接入未授权，`p95=null`、`optimization_qualification=false`，任务资格模板仍PENDING。详见[实机报告](../ninfer-v4-k2-t05-hardware-20261023.md)，后续边界见[任务合同](plans/tasks/K2-T05.md)。下文CPU“GPU未运行”及旧拟议额度均为历史。


## 历史CPU准备：K2-T05构建、合同与评审完成，当时GPU未运行

状态`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。隔离分支`codex/k2-prefill-split-20261023`候选树`3ea537c00c759ef2a4577b525ae691f694ae102e`已完成BO构建、16项CPU合同（8 C++ Graph metadata＋8 Python编排）及集成评审；冻结SHA`7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc`。首轮CUDA13.2 Graph依赖API签名构建失败保留；两处改为4参数后增量构建PASS。已修复默认流reset到非阻塞Graph的同步及native非零退出的控制器失败处理。逐bit、实际Graph及收益均`NOT_RUN`，本轮0 GPU/模型/HTTP。[实施报告及冻结详情](../ninfer-v4-k2-t05-implementation-20261023.md)。

未来最小预算仍为4数值、20 direct Op、4 capture、184 replay、384算法kernel、0模型/HTTP；辅助传输现已冻结：H2D 508次/4447860736字节、D2D 128次/7929856字节、D2H 768次/5386141696字节，raw段copy另限direct12/capture6/replay276，不能与辅助传输混算。预计2–5分钟，硬限10分钟、第7分钟清理。当前账本PRISTINE且所有计数0、无runtime；GPU执行需单独授权。旧选型中“辅助传输待枚举/null”仅为历史，不是当前缺口或无限额度。

K1-T01/C0/K2-T01继续关闭、追加预算0，不启动K1-T02。原数学、FP64阈值、state和默认分派保留，采样/context/Pi medium/32768不变，原服务STOPPED；18处G1差异、C1缺口及全部失败保留。20任务/4门禁/80断言、31 scope为可选库，任务资格仍PENDING，`p95=null`、`optimization_qualification=false`。下文旧成绩/预算保留，不据此重跑旧任务或授予产品资格。

## 历史选型范围：K1收尾，下一项仅选定K2-T05

K1-T01已由用户收尾，追加预算0；保留`GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW`及全部失败/缺口，不启动K1-T02产品接入。C0、K2-T01继续关闭，不重跑已通过任务。

唯一下项为[K2-T05普通Prefill卷积直接写连续Q/K/V](plans/tasks/K2-T05.md)，状态`NEXT_CANDIDATE_SELECTED_NOT_IMPLEMENTED`；复用源树`41a913488b0138fe868a8321d2f6a86ce83e313f`。先做bench-only限定shape候选，不改默认分派。本次选型不授予CPU实施或GPU执行授权；范围、待冻结传输预算和8–16工程小时估计见[选型报告](../ninfer-v4-post-k1-selection-20261023.md)。

当前注册表为20任务/4门禁/80断言、31个scope（15 candidate＋15 publication＋1 research）的可选实验库，并非本次全执行计划；当前只选K2-T05。原服务保持STOPPED，采样/context/Pi medium/32768、18处G1差异与C1附件缺口不变，`p95=null`、`optimization_qualification=false`。以下旧选型、预算与成绩按各历史阶段解释，不构成当前余额或新增授权。

## 历史状态：K1-T01 Graph通过，无段级净收益信号，保留raw

状态`GRAPH_PASS_NO_SEGMENT_SIGNAL_KEEP_RAW`。本轮Graph-only补测已完成并关闭；profile为`SM89_GDN_CORRECTION_C1_W4_L48_GRAPH_ONLY_R2`，源树`41a913488b0138fe868a8321d2f6a86ce83e313f`，冻结SHA`29c89db3f440cea8b8620e0728dd9220c7c3366782fbc408b283e5aedd9e0969`。raw函数地址由真实launch TU导出，实际Graph节点参数在断言前耐久落盘；8个CPU元数据场景与8个工具场景共16项定向验证PASS，独立集成评审无阻断。

复用旧8个数值场景及其SHA，不重跑。新执行6次capture、276次replay（12 correctness＋24 warmup＋240 timing）、13524次算法kernel；0 direct Op、0新增数值场景、0模型/HTTP。6图各49节点均`WITNESS_PASS`；Graph correctness、warmup与timing全48层raw/correction逐bit比较均PASS，layer0原FP64参考在Graph correctness通过。新账本`COMPLETE`且无unknown；不回写旧失败账本或补造旧节点参数。

48 Record＋1 Fold的5批配对中位改善：commit1为−1.0540%（0/5批更快），commit2为−0.0714%（0/5），commit4为＋0.1809%（3/5）。三组均未达到“改善≥10%且至少4/5批更快”，结论`NO_SEGMENT_SIGNAL`。计时含host投递gap，仅代表该算子段，不是完整Target Verify或模型整轮收益。保留raw，不进入K1-T02产品接入，不追加GPU测试。

窗口约10.70秒结束；原服务STOPPED、GPU idle、lease free。15分钟硬限和第12分钟清理上限未触及。默认分派、采样/context/Pi medium/32768、18处G1差异、C1附件缺口及全部历史失败保留。C0/K2保持关闭；所有任务资格status仍PENDING，`optimization_qualification=false`、`p95=null`。详见[本轮Graph补测报告](../ninfer-v4-k1-graph-r2-20261023.md)。下文首筛失败、CPU准备及旧预算均为历史，不能据其重启窗口、追加测试或授予发布资格。

## 历史首筛：K1-T01数值通过、Graph见证失败、未计时

状态`PARTIAL_NUMERIC_PASS_GRAPH_WITNESS_FAILED_NO_TIMING`。本轮唯一执行冻结SHA`4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105`、源树`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`的窗口；profile仍为`SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1`。8个数值场景全部PASS，784次direct Op及对应784次算法kernel完成。全48层raw/correction的FP32 state、conv和BF16 readout逐bit一致；layer0既有独立FP64参考及guard/suffix检查通过。该结论仅覆盖本次C1/W4直接执行场景，不授予完整候选或生产资格。

首个raw commit1 capture在函数/几何见证检查报`unexpected Fold function/geometry`：1次capture已预留但未完成，replay为0，Graph正确性、稳定性及Record＋Fold净收益均无结果。实际node参数未打印，Record函数地址不匹配也可进入同一错误分支；不能据此认定真实Fold几何错误或数值失败，更不能将未计时写成无收益。

原冻结上限8场景/784 direct Op/6 capture/276 replay（含warmup）/14308算法kernel未扩大，0模型/HTTP。窗口约7秒后终止并清理候选；候选exited、原服务STOPPED、GPU idle、lease free。当前ledger保留失败现场的`RUNNING`，不能回写`COMPLETE`；冻结回执、初始空账本、CPU证据及全部失败不改。窗口已经结束，禁止重启或重跑已通过8个数值场景。

下一步仅修复Graph见证及诊断，再另冻未完成Graph的工具和预算；不自动发GPU请求。默认分派、采样/context/Pi medium/32768、18处G1差异、C1附件缺口保持不变。K1-T01及K4资格仍PENDING，`optimization_qualification=false`；K1-T02运行时事务与整轮验证独立，C0/K2保持关闭。详见[本轮实机报告](../ninfer-v4-k1-hardware-20261023.md)。以下CPU准备和更早预算均为历史，不能作为当前空账本或余额。

## 历史K1-T01 CPU准备：候选已冻结、当时GPU未运行

状态`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。用户已授权在29隔离分支完成K1-T01：C1/W4/L48 correction Record/Fold候选、驱动、BO构建、16个CPU合同（8 C++＋8 Python）与独立评审均完成。候选树`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`；冻结SHA`4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105`。无GPU/模型/HTTP请求。raw接口和默认分派保留；共享helper同表达式capture与内部链接改动不能静态证明GPU逐bit一致。

profile为`SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1`。实机驱动采用48层不同state/conv种子，将对全层raw/correction逐bit比较；独立FP64仅layer0沿用旧oracle与阈值，当前均未实跑。双池独立，候选不双写raw；10,260,480字节correction是新增payload，不是显存节约。首筛仅48 Record＋1 Fold，不是完整Target Verify/模型整轮。

未来冻结上限为8数值场景、784 direct Op、6 capture、276 replay（12 correctness＋24 warmup＋240 timing），每图49算法节点、总执行14308；0模型/HTTP。传输独立上限：H2D847次/3174503944字节、D2D128次/19704905728字节、D2H896次/30979424768字节，含guard/reset/export，无helper compute或memset。预计3–8分钟，第12分钟清理、15分钟硬限。工具和空账本已冻结，GPU执行仍须单独授权，不能自动接续。

段级五批中位改善≥10%且≥4/5批更快才有`SEGMENT_SIGNAL_NOT_K4`；无信号/数值失败停止保留raw。K1-T02许可/epoch/取消、真实Target sampling、整轮及发布继续独立。C0、K2保持关闭、追加预算0。原服务停止、采样/context/Pi medium/32768、18处G1差异、C1附件缺口及全部历史失败不变。详见[本轮实施报告](../ninfer-v4-k1-implementation-20261023.md)。以下旧阶段记录及通用32wire/84native模板均为历史，不能相加为本窗口额度。


## 历史K2实机结果：无信号，保留512并停止本轮

状态：`GPU_SCREEN_COMPLETED_NO_SIGNAL_KEEP_512`。[本轮实机报告](../ninfer-v4-k2-hardware-20261023.md)。冻结SHA `37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e`，源树`13223b2b2989d0cf580715b197b276d74acffc86`。8个数值场景、22次direct Op全部PASS，6次capture及12次正确性replay PASS；含warmup共1992次replay，0模型提交/准入、0HTTP。

128/256相对512的5批配对中位改善：T1分别+1.2026%（3/5批更快）、+5.7554%（3/5）；T4分别−3.4272%（2/5）、+4.9825%（3/5）。四组均`NO_SIGNAL`，未满足预定“改善≥10%且至少4/5批更快”。计时对象为host-submitted单节点Graph replay，不是纯kernel时间，不能外推整轮/Chat收益或彻底否定kernel优化潜力。

完整控制窗口耗时1.568326749秒，候选、guardian和controller均已退出，GPU空，原服务STOPPED。停止本轮CTA实验，保留默认512，产品dispatch不改；不进入“有赢家后”的整轮验证，额外预算0，不自动重试。原冻结窗口已single-use消耗，runtime存在、账本COMPLETED；禁止重启。以下CPU准备、选型和拟议预算仅为历史，不构成待执行或余额。C0仍关闭；18处G1差异、C1附件缺口与全部历史失败保留，采样/context/Pi medium/32768不变。19任务/4门禁/76断言与PENDING资格模板不改，p95=null、optimization_qualification=false。

## 历史CPU准备（前次选型与C0段落保留）

状态：`CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN`。用户已授权本轮K2-T01 CPU实施，在`codex/k2-gated-rmsnorm-20261023`隔离分支、工程基点`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`已完成补丁、BO增量构建和集成评审；不是新增GPU执行授权。本段取代下文历史“仅选定未实施”的当前含义，旧选型与失败记录原样保留。BO无GPU增量构建通过；新增CPU合同19＋4项及CLI检查11项通过，独立集成评审问题已修复并闭合。GPU数值/性能/真实清理尚未运行，不能替代候选或生产资格。

本轮采用独立`ninfer_k2_gated_rmsnorm_probe`，不扩展旧plain bench。复用原warp模板的128/256/512线程配置，使用真实gate，并共享既有double oracle；产品`src`及默认dispatch完全不改。编译旧test以检查集成，不执行已通过旧suite，不重跑Baseline或旧任务。

未来GPU首轮拟议预算为8 case、22 direct Op、6 capture、1992 replay（12 correctness＋60 warmup＋1920 timing）；fallback为T1 unaligned和T5 aligned。0模型提交/准入、0HTTP；预计2–5分钟，600秒硬截止，第420秒清理。工具和全0账本已冻结，执行仍待单独授权，本轮未执行。C0保持`CLOSED_NO_FURTHER_MEASUREMENT`、追加预算0；18处G1差异、C1附件缺口和全部历史失败保持原样，原GPU服务停止、采样/context/Pi medium/32768不变。

[本轮实施报告](../ninfer-v4-k2-implementation-20261023.md)为最终事实入口；冻结SHA为`37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e`，补丁树为`13223b2b2989d0cf580715b197b276d74acffc86`。当前无runtime；不将CPU通过记成候选性能/生产资格。计时是含主机投递间隔的单节点Graph replay信号，不是纯kernel latency。以下早期选型、预算与执行记录均按其历史阶段解释。

## 历史选型决定：C0关闭、K2-T01当时仅选定未实施

C0按用户决定收尾，状态`CLOSED_NO_FURTHER_MEASUREMENT`，追加补测预算0，不再重启旧窗口或自动接续。已通过的CPU及实际L2恢复证据保留；TTFT收益仍为INCONCLUSIVE，不能从工程继承推出生产采纳。18处G1差异、C1附件缺口及全部旧失败不变。原GPU服务保持停止，采样/context及Pi medium/32768不变。

下一项选择`K2-T01`：SM89、BF16 aligned D128、48 heads，真实T1/T4下的已有gated RMSNorm CTA映射。当前512线程对应T1仅3个CTA；128/256线程候选对应12/6个CTA，是可证伪的执行几何假设，不是已测最大热点或整机收益保证。当前MTP K3的verify为K+1=4，不扩T6/W8/W16。工程基点为C0树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`，仅继承代码；P4原参考树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`保留，两者均无新增性能/生产资格。

首补丁只增加bench/test候选，产品默认dispatch保持不变。复用同一warp数学、SiLU、乘法和BF16舍入，不新增fusion、workspace、autotune或模型/权重格式；实测胜者才进入SM89隔离候选的静态限定shape路由。现有bench的candidate-b128/b256未传真实gate，`--control`只是payload带宽对照，都不能冒充本次gated/原512算法对照。

本轮只读ssh核对和文档选型，未实施补丁、构建、测试或GPU/HTTP/模型请求；实施及GPU验证均待对应授权。当前选择和范围不把完整round验证当开工前置。

[本轮选择报告](../ninfer-v4-k2-selection-20261023.md)；具体预算见[K2合同](plans/tasks/K2-T01.md)。以下C0准备/执行段落为历史，不构成余额或待办。

历史r3状态：C0_TTFT_PILOT_R3_COMPLETED_INCONCLUSIVE。已按授权完成P4→C0最小实机补测，4Chat全部PASS、10wire、6次模型提交含2warmup，246.142777927秒安全收尾。两端均实际深L2恢复，但冻结对照合同不成立，不能证明TTFT收益。原GPU服务保持STOPPED，候选退出/GPU空、未知请求及未完成导出均0、无新增附件缺口；18处G1差异、C1缺口和全部历史失败保留。[本轮报告](../ninfer-v4-c0-ttft-pilot-20261023.md)。

1. 读取[总计划](plans/00-master-plan.md)、[当前证据](research/05-completed-baseline-and-current-state.md)、[注册表](plans/02-task-registry.md)和[统一预算](plans/08-validation-budget-and-estimate.md)。直连`ssh 29`是后续指定通道；当前不用旧jssh/跳板约束阻塞。
2. 原研究参考为P4树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`；本次K2工程基点为上述C0树，HEAD O不代表这些树已提交。复用Baseline/BO/G1/P1—P4证据，先核对精确身份；不得使用未评审P5导入树`f871d242438333d3b74264a411a9fd3ec80884f3`。
3. 只做K0需要的最小调用链/归因，已有资料不重复采集。K0-GATE不依赖correction独有数值oracle、完整P6、完整上游合并、其它协议或UI。完整验收不挡开发，但新路径的适用正确性验证不能删除。
4. 从14个candidate scope选一个：cpu_sha/kernel/correction/workspace/projection_overlap/lookup/draft_head/w8/w16/dflash2/global_retrieval/utility/upstream_selective/upstream_full。它们不是顺序待办，不自动补全所有分支或跑所有组合。W16需W8技术证据；feature检索才需要匹配H6，utility只选已合格route。
5. 冻结本次实验输入、单一候选、可构建补丁范围、所选断言、真实route/shape、原始证据、请求/迭代/显存/时间总预算和止损。新GPU/模型/资产/生产动作需对应授权，不能继承历史窗口余额或把每任务预算相加。
6. 用既有sampler/processor/RNG/许可/提交权威；greedy proposal与Target production sampling分开。保持T1/top_p.95/top_k20、Pi medium/32768及context，不能为容量或失败降低。DFlash2无精确27B资产先停，不训练、不套35B资格。
7. 交付可构建补丁与最小必要验证，修复集成评审发现的问题。没有新改动/失败/现实缺口就停止重复测试。只在选中路径触及G1/C1/格式/状态时补定向证据，原18差异和C1缺口不回写。
8. K4-T01在同一集成树上做一次共同资格；包含所有新增开销、实际route-hit、完整round和Chat wall。单kernel/接受率/HTTP200不是整体验收。宣称质量或任务收益才用新holdout，不能重跑历史题或grader来提成绩。
9. K4-QUALIFIED是隔离候选结论；K4-GATE是以后另获授权的生产发布和实际回退。原GPU服务保持停止，候选测量结束只清理候选，除非用户更改要求，不自动恢复原服务。
10. 任何未知请求/结果先核对durable记录、响应ID、SSE done、队列/进程与owner；不自动重发。保留原失败、拒绝、成本与缺失附件，不造日志或改旧分母。

原始计划只作溯源：[范围审计](plans/10-task-scope-audit.md)。当前入口不得从baseline-v3旧P5/P6/H/S链恢复待办。文档验证命令见[检查器](evidence/validate-documentation.py.md)，文档PASS不代表产品PASS。

当前进度：[C0结果](../ninfer-v4-c0-20261023.md)、[累计账本](../../output/ninfer-v4-c0-20261023/cpu-ledger.json)及[后续实机提案](../../output/ninfer-v4-c0-20261023/proposed-hardware-budget.json)。候选树4d31af405fca9c70bd39a71257f83f4eeebbd0bc；CPU大块hash约2.149×、合成publication降低53.12%，首次EVP约1.904ms。不要重跑已过CPU/K0或旧任务。Chat服务收益未证明，K4候选及生产门禁未通过。


历史准备进度（0请求仅指准备期，现已被下述执行记录替代）：[实机准备结果](../ninfer-v4-c0-hw-prep-20261023.md)。冻结driver tree0e5efa0f，窗口`/home/hhtele/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1`；新驱动57唯一离线测试通过，旧CPU不重跑。预算8新Chat＋2内置warmup=10提交，4次telemetry加Chat总12wire，720秒关准入并仅清候选、900秒硬截止。该历史准备期当时全0、authorization=NOT_AUTHORIZED；窗口现已关闭，不再启动。

历史r1/r2驱动：copy时间只在publication完成日志里可见，当时按真实seed SSE DONE+1秒调度、事后关联copy/publication，不等待导出才发续轮。归因须基线实际no_alias完整prefill、候选实际L2且减少prefill；否则INCONCLUSIVE。已知seed质量失败可零成本记录依赖未发，未知/传输缺口禁止接续及重发。只支持Chat Completions；原服务保持停止，参数与Pi预算不变。该历史8/10/12预算及DONE+1秒方案不再作为当前执行合同。

r1执行后的历史待修记录（后续已由r2完成，不是当前剩余工作）：完整400/raw/账本与缺失outcome/stage均保留，外置核对证明无Chat admission。先版本化修复具名tool_choice夹具与准入前拒绝终态处理，必要CPU回归/新冻结预计30–60分钟；本次没有实施该修复或启动第二窗口。新GPU对照不能自动重发本次请求或沿用旧账本。

历史r2实机已完成：无未知请求/悬置导出/新增原始运行附件缺口；两端目标续轮均preflight_rejected、未L2恢复，随机输出/P/O/queue不同，不能声称Chat提速。CPU与功能结果直接复用，不重跑已过任务、不追加请求寻找好样本。完整性能与发布继续独立，原服务保持停止。


## 历史r3冻结合同：现已授权执行并消耗

使用`CONTROLLED_PREFIX_BRANCH_TTFT_V1`，按P4→C0顺序。每端只运行一个新seed和一个相同固定branch；branch的assistant是明确标注的合成输入，不冒充seed真实输出，也不宣称真实工具结果续轮。seed完成后按其durable digest条件仅erase候选retained GPU lane，不删除L2；branch固定在seed SSE DONE+10.0秒±150ms发送，过时停止，不自适应等待或补发。

新预算为4个Chat＋2个内置warmup=6次模型提交；4个telemetry＋2个条件erase＋4个Chat=10wire，0新增native Op/capture/replay。预计6–10分钟，第720秒开始清理候选，第900秒硬截止。上述为执行前冻结预算，现已消耗并关闭，不继承旧窗口余额，也不形成新的待执行额度。

只有相同请求字节/实际P/采样和export形状、两端queue≤50ms、P4浅命中≤512且computed_prefill≥P−512、C0实际L2恢复字节>0且深命中≥45000并computed_prefill≤P−45000，同时P4发布晚于branch客户端发送、C0发布早于发送，才比较首个非空content/reasoning/tool delta的客户端TTFT；保留服务端TTFT。发送时间不冒充真实cache lookup时点。TTFT下降≥5%最多记为n=1的`PILOT_TTFT_SIGNAL_NOT_K4`，其余INCONCLUSIVE。原完整Chat配对断言不放宽；CPU前缀证明不代表image import或TTFT收益已验证，V04仍未证明，不外推完整Chat、质量、p95、K4或发布资格。

冻结根`/home/hhtele/ninfer-v4-c0-l2-preflight-20261023/prepared-window-l2-r3`；driver tree `130bcf5414fc89d971f368fc81e9aafdda7753dd`，21份文件，freeze SHA `1b0f1c596aa15f5e41d337f139d936c51ac52131ecd6d3c5efabc1e384127dd1`。[冻结回执](../../output/ninfer-v4-c0-l2-preflight-20261023/preparation-receipt.json)记录准备时账本全0、无runtime/state、authorization=NOT_AUTHORIZED_PREPARATION_ONLY；这是历史准备状态。用户随后授权本次执行，窗口现为single-use已消耗，禁止再次启动或发额外样本。两轴评审已闭合，产品1239文件与C0树一致。


## C0 r3最小TTFT pilot已完成，收益归因不成立

[实跑报告](../ninfer-v4-c0-ttft-pilot-20261023.md)与[机器汇总](../../output/ninfer-v4-c0-ttft-pilot-20261023/final-summary.json)记录P4→C0已完成：4个新Chat全部PASS、10wire、6次模型提交含2warmup，246.142777927秒安全收尾；没有本轮失败。21份冻结工具SHA及request/raw哈希核验通过。原服务STOPPED、候选退出、GPU空，未知请求/未完成导出/新增附件缺口均0。冻结目录已single-use消耗，禁止重启或追加样本；上文准备预算及全0状态仅为历史，不是余额或当前待办。

两端branch均真实source=l2，恢复55293 tokens，实际P=55374、computed_prefill=81；P4/C0恢复字节1333980256/1336349835。客户端首个非空语义delta TTFT为0.943552271/0.959943143秒，C0本次观察约慢1.737%，n=1不能形成稳定回退或收益结论。冻结分析保持`INCONCLUSIVE_TTFT_CONTROL_NOT_SATISFIED`：P4同样深L2、两端queue为0.618971645/0.641931568秒均超过50ms、seed export为1333034412/1335401900字节不等。不放宽对照断言，不把L2恢复成功等同C0独有收益。

post-copy publication为14.372465950/7.060492013秒，描述性降低约50.87%；它不是严格配对，也不等同TTFT获益。V04仍未证实，p95=null、optimization_qualification=false、K4=false；无正式性能或发布资格。采样及Pi medium/32768不变，18处G1差异、C1附件缺口及全部历史失败保留。不再把本次scope列为待开工或自动补测任务。

进一步源/日志复核修正了实验假设：P4命中`stable_prefix`，C0命中`routed_session`；执行器先发布boundary alias再发布session，最终publication_finished_ns表示二者全部完成。因此P4可在最终publication完成前已经恢复深前缀，原“最终发布未完即无任何可恢复深前缀”的假设错误。queue指标是admitted−submitted，恢复发生在admit之前，包含恢复/准入开销，不能将其超50ms归咎于外部排队竞争。冻结门槛仍原样判不满足，不改gate或补发。独立原始证据只读复核无阻断：10组request/raw SHA与长度相符、4个SSE各1个DONE且finish为tool_calls、21冻结SHA一致；复核未运行测试。
