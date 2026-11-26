# 31 · K00–K07：受限自动优化与局部后端实施任务

> **v2来源更新：** 本篇141文件/工具链与CI详细审计基于历史`5e5c77…`；当前main为`f35d6ccc2e03a54e73e3796f415f11313e439d50`，新增#1866写覆盖修复与1D限制，详见[40](40_upstream_refresh.md)。未来K00冻结新pin并重做相关资格；原证据保持原SHA，不冒充新运行结果。

> **For agentic workers:** 先读 [AGENTS](../AGENTS.md)、[27来源审计](27_cuda_rust_source_audit.md)、[28后端架构](28_custom_backend_architecture.md)、[29自动优化](29_automated_kernel_optimization.md)、[30 SM89程序](30_sm89_kernel_program.md)。K00–K07是可选增量任务，G0–G7是资格gate，AX01–AX28是测试ID，三者不可混用。本文定义未来实施，未实现lab、编译器适配或backend，也未运行GPU。

**Goal:** 让AI在固定目标与有限预算内提出局部kernel候选，经独立证明/动态/模型/业务证据形成可审查、可回退的Atomic能力行。  
**Architecture:** Atomic既有C++/ggml-cuda持有context、stream、arena、模型状态与事务；优先加载固定SM89 AOT cubin；cuda-oxide、普通CUDA C++与可选Tile分别资格。  
**Spec:** [05架构](05_architecture.md)、[08算子](08_sm89_kernels.md)、[13正确性](13_correctness_quality.md)、[14统计](14_benchmarks.md)、[28–30](28_custom_backend_architecture.md)。

## 1. 状态、依赖与不变量

v1.2合计32个任务、96项计划测试、32篇专题文档。K00–K06初始`NOT_RUN`，K07初始`DEFERRED`；新增28项AX全部`NOT_RUN`。原48项与GX20项继续有效。没有现场工具/模型/硬件时，受影响执行行才记`BLOCKED`；不能因为cuda-oxide仍是preview，或因已合入的hardening历史，而把全部K任务预先标BLOCKED。[27](27_cuda_rust_source_audit.md)

固定Atomic `fb69fff02101b048a0a165a3b502712dd2ca978f`、正式Mini/R3、per-loop KV/conv、单active generation、Vision Off和全驻留优先。RTX4090 24GB、64GB host是目标；CPU、OS、驱动、Toolkit、实际容量和独占条件以T00为准。既有guards、资源余量、质量与性能门不降低。

| 任务 | 直接依赖 | 条件依赖 / 范围 |
|---|---|---|
| K00 | T01 | T01已依赖T00；既有只读来源审计可作为输入，不等于K00运行探针完成 |
| K01 | K00 | 定义合同和失败出口，缺GPU时仍可完成有范围的CPU工具交付 |
| K02 | K00、T04、T05 | 使用spec shape加T06；使用tiering加T09对应能力 |
| K03 | K01、K02 | 只消费已冻结的热点、模板、参数域与工具链 |
| K04 | K01、K02、K03 | 使用spec/budget时分别要求T06/T09对应能力 |
| K05 | K03、K04、T03、T05 | 所选spec/budget机制必须先有T06/T09相关资格 |
| K06 | K05、T10、T11 | 只确认实际承诺的长context、缓存、服务profile |
| K07 | K02、K05、K06 | 新DECISION满足明确触发证据才启动，不成为默认T12依赖 |

机器权威为[task-graph.json](../manifests/task-graph.json)。K链不依赖T07整体先完成；K02消费T02–T05已资格基线，K04/K05沿T07代码触点工作，成果供T07/T12复用。也不把K任务反向设为T07必选依赖，避免循环。已启用的新spec、预算、布局或专家分组必须已有独立基础资格；不能让K搜索器和基础机制互相依赖对方尚未产生的证据。

任务交付完成与能力PASS分开。K02交付“关键路径收益上界不足”的审查结果、K03交付明确未支持范围、K06以NO_BENEFIT结案，都可成为有效任务收尾。实际被选入服务的候选必须具有对应G2/G3/G4/G5/G6证据；生产G7仍按当时会话授权，不由搜索器签发。

## 2. 公共consumer合同

以下名称和文件均为**NEW逻辑接口**，不是上游现成功能。字段定义以28–30与新增机器合同为准，K01负责把调用方、消费者、错误码和版本绑定落实。可以在少量模块实现，不要求每个接口一个新服务。

| 接口 / consumer | 输入 | 输出与拒绝合同 |
|---|---|---|
| `propose_candidates` / lab policy validator | SearchPlan、去敏TraceSummary、模板catalog、stop registry | CandidateSpec列表；只允许修改候选；无执行/registry写权限 |
| `compile_candidate` /隔离builder | CandidateSpec、ToolchainLock、完整依赖、输出目录 | BuildRecord，含实际argv、退出、产物/ABI/资源hash；不触及生产context |
| `check_proof_binding` /固定verifier与checker | BuildRecord、实际verified/emitted IR、KernelContract、ProofPolicy | 每属性status、义务数量、假设/TCB/未证链；不把导出成功当证明 |
| `resolve_kernel` /只读registry | 完整CapabilityKey、op/tensor/layout/shape、artifact revision | SelectedKernel或NoMatch；没有enqueue，合法NoMatch可走原实现 |
| `prepare_invocation` /局部bridge | SelectedKernel、BorrowedExecution、tensor views、适用的RouteIndexContract | ABI/launch与lease/event均明确的PreparedInvocation；失败说明是否zero-submission |
| `enqueue_invocation` /原backend stream | PreparedInvocation、expected epoch/address generation | 一次性SubmissionTicket；只表示SUBMITTED，不表示完成 |
| `resolve_ticket` /原backend完成管理 | ticket、当前epoch、completion event | NOT_READY/READY/FAULT；FAULT保留原CUDA错误且sticky |
| `consume_ready_output` /原Atomic事务 | READY ticket、有效事务、原模型与停止条件 | 由原流程消费输出；kernel不直接提交token/tool |
| `retire_resources` /原回收器 | graph/module/buffer leases与末次event | 待回收/已回收；Drop、取消、超时不是GPU完成证据 |
| `qualify_candidate` /独立审查器 | 冻结候选、raw runs、G2–G6需要的全部证据、比较合同 | gate与能力范围；AI生成器不能修改判分与签发G7 |

proof状态使用`NOT_REQUESTED / NOT_RUN / PROVED_SCOPED / FAILED / UNKNOWN / UNSUPPORTED / ERROR`；资格未评估使用`NOT_ASSESSED`。这两个维度不替代原task/run/gate状态。普通C++路线可显式NOT_REQUESTED；要求verified的候选缺证、超时或未知不能成为PROVED_SCOPED，也不能悄悄转换路线继续沿用旧能力身份。

运行接口检查固定宽度参数ABI、设备/context、allocation bounds、alignment、stride、别名、整数溢出、资源与图generation。MoE动态index的范围/offset/scatter合同和浮点route内容正确性分别验证。Runtime/Driver互操作不转移所有权；Rust借用不覆盖C++外部写入或GPU异步寿命。[28](28_custom_backend_architecture.md)

## K00 · 来源、工具链、SM89与证明能力探针

**依赖 / 初始状态：** T01；NOT_RUN。**类型：** optional_reference。**产出gate输入：** G0、G2。  
**输入：** 27固定源码/CI审计、T00 inventory、Atomic/source-lock、候选前端需求。  
**Files NEW：** `profiles/kernel-toolchains.lock.json`、`profiles/kernel-frontend-capabilities.json`、`tools/inkling-lab/kernel_probe.py`、`tests/inkling_lab/test_kernel_probe.py`、`evidence/K00/`。

**输出 / consumer：** `ProbeRecord`交给K01/K02，包含source/工具链hash、frontend、实际target/PTX版本、feature支持、编译/证明/实际执行/skip分别计数、设备inventory及原始命令。源码支持、作者CI、CPU证明、4090执行是不同证据；未知driver/JIT组合不自填PASS。

- [ ] 固定NVIDIA主干`f35d6ccc2e03a54e73e3796f415f11313e439d50`，核对#1857/#1866已合入并覆盖新反例；不自动更新main或切换未经审计release。各Rust workspace、Lean、LLVM、CUDA/ptxas/libdevice、可选tileiras分别锁。
- [ ] 建立普通C++、cuda-oxide SIMT、可选Tile能力行；当前CuTe Rust preview拒绝SM89，当前Tile FP8限制不能被Ada硬件FP8支持覆盖。
- [ ] 写AX01/AX02/AX07/AX18负例：错误target、缺Lean静默skip、export-only、零GPU launch、假PASS与资源超限。
- [ ] 在条件满足后使用32的现有source命令做最小safe_vecadd编译/证明/实际4090运行；显式SM89，新构建目录，无Lean缓存。没有实际launch/输出断言不能填GPU执行通过。
- [ ] 把与Atomic无关的B200/5090示例保留为来源；不要求在4090强行跑Blackwell示例来“补齐测试”。

**命令性质：** 现有上游命令见[32§4](32_kernel_validation_runbook.md)；K00新增probe与CPU测试当前不存在，未来命令为`python3 -m unittest discover -s tests/inkling_lab -p test_kernel_probe.py -v`。缺依赖列清单，不自动安装或升级整机。

**DoD：** 每一选定前端都有固定版本、实际支持/不支持/未知边界、raw artifacts、真实测试/skip数量和独立审查；完成来源/CPU范围不能授4090能力。**停止：** 不匹配pin、错误SM、未允许检查绕过立即FAIL；现场条件缺失只BLOCKED对应执行。**测试：** AX01、AX02、AX07、AX18；复用TC01/TC02、GX01/GX18/GX20。

## K01 · 搜索、产物、证明和资格合同

**依赖 / 初始状态：** K00；NOT_RUN。**类型：** optional_tooling。**产出gate输入：** G0、G2。  
**输入：** K00能力表、28–30接口、原run/gate/validation-policy。  
**Files NEW：** `tools/inkling-lab/kernel_contracts.py`、`tools/inkling-lab/kernel_policy.py`、`tests/inkling_lab/test_kernel_contracts.py`、候选/搜索/证明/registry schemas及负例fixtures；修改T01验证器但不改变原阈值。

**输出 / consumer：** versioned SearchPlan、CandidateSpec、KernelContract、ProofBinding、RouteIndexContract、BuildRecord、RegistryEntry；K03/K04/K06消费。新`kernel_search.py --plan PLAN --out DIR`由K03实现，K01先冻结输入/输出/退出码；不虚构原`lab.py`已支持search kind。

- [ ] 写AX01–AX10、AX18、AX26/AX27的能失败fixture；覆盖哈希、完整dependency closure、proof义务数量、空集合、skip、目标/阈值篡改与旧缓存。
- [ ] 将proof每属性结果、TCB/公理、实际verified/emitted IR、编译flags、PTX/cubin/symbol/ABI和执行资格分别记录；哈希关联不等于编译器已被证明。
- [ ] 定义动态索引producer/consumer前提；只证明地址范围不证明float route/top-k内容正确。禁止把未声明pointer、unsupported lowering或未知义务当成功。
- [ ] 实现严格输入/文件hash/实际测试数量/证据类型校验；语义验证器核对schema不能表达的关系。生成器不得写oracle/threshold/registry/原日志。
- [ ] 沿原0/1/2/3退出合同：0指定工具操作真实完成且检查通过；1已执行失败；2缺能力/环境/未实现；3输入或版本合同非法。工具exit0不授G2/G3/G7。
- [ ] 同步task/run枚举、catalog与示例；顶层additionalProperties:false的旧合同不能靠塞未知字段绕过。GPU suites尚未实现须明确返回2。

**命令性质：** `python3 -m unittest discover -s tests/inkling_lab -p test_kernel_contracts.py -v`为PLANNED_AFTER_K01；现有包内工具自检见32§3，不冒充此测试。  
**DoD：** 非法/空/陈旧/篡改/未执行证据全部不能获得资格，合法的普通未证明C++与scoped proof路线可分别记录；独立审查所有失败出口。**停止：** 无法区分证明范围、源码与执行产物则受影响路线BLOCKED。**测试：** AX01–AX10、AX18、AX26、AX27；TC01/TC02、GX01/GX20。

## K02 · 单热点、有限搜索域与成本计划

**依赖 / 初始状态：** K00、T04、T05；NOT_RUN。**条件：** spec形状另需T06，tiering另需T09相应能力。**产出gate输入：** G2、G3、G4。  
**输入：** 正式Mini/R3串行基线、T03资产、T04完整profile容量、T05状态合同、K00工具能力。  
**Files NEW：** `profiles/kernel-search-plan.json`、`profiles/kernel-template-catalog.json`、`profiles/kernel-stop-registry.json`、`evidence/K02/`；trace字段接T01，不先建立新runtime。

**输出 / consumer：** 不可变SearchPlan与TraceBundle交K03；包含一个热点、真实shape、critical-path占比、Amdahl上界、语义/E/N类别、参数域、主终点、开发/确认集hash、资源与搜索限额。

- [ ] Systems先观察完整请求；Compute只分析必要热点。记录真实physical/visit/phase、dtype/quant/stride/alias、B/P/N、sort/gather/scatter、搬运、launch/sync和图成本。
- [ ] 若关键路径比例f不足以支持原5%请求收益门，不扩成大型工程；多kernel重叠不能重复加算f。
- [ ] 首轮只选一个family。先B1；T06资格后才有B2/4/8；prefill只选真实允许ubatch及尾块。block/vector/stage参数从实际几何和SM89资源缩小，不穷举全部组合。
- [ ] AI不能改变R、量化、KV、采样、guard或测试门；FP8/new quant、persistent、mapped relay、整后端和历史无收益CPU pool/overlap不自动进入候选。
- [ ] 冻结初始预算提案：总≤24个不同候选，≤4个GPU微基准、≤2个E2E探索、1个冻结holdout赢家；初始加最多两轮有profiler因果依据修正，共用总额。可提案CPU探索2h/GPU探索4h、每compile/proof5min，全部在看结果前根据T00决定，不构成付费授权。
- [ ] 确认与G2/G4/G5/G6另留预算，不能删测以适应探索限额。历史stop条目需新Inkling trace、新机制差异和新experiment_id才重开。

**命令性质：** 使用已安装Nsight官方命令及T01实际runner，具体argv冻结进plan；采样设置见32§6。新search命令尚未实现，不在本阶段声称可以运行。  
**DoD：** 热点、可证伪假设、参数域、停止与确认计划可被第三方复核；trace与正式timing区分。**停止：** 没有足够收益空间NO_BENEFIT；没有隔离条件BLOCKED；不继续堆热点。**测试：** AX02–AX06、AX24–AX26；PF02/PF04/PF07、GX19。

## K03 · 受限生成、编译与证明绑定

**依赖 / 初始状态：** K01、K02；NOT_RUN。**类型：** optional_optimization。**产出gate输入：** G0、G2。  
**输入：** SearchPlan、固定模板、K00前端能力、K01合同、独立oracle。  
**Files NEW：** `tools/inkling-lab/kernel_search.py`、`tools/inkling-lab/kernel_build.py`、`tools/inkling-lab/kernel_proof.py`、`tests/inkling_lab/test_kernel_search.py`；只有选中family才创建对应CUDA C++/Rust模板和独立build目录。

**输出 / consumer：** CandidateSpec、BuildRecord、ProofBinding、不可变PTX/cubin与ABI清单交K04/K05；每失败候选也有reason/raw artifact，搜索历史不覆写。

- [ ] 先测试权限、去重、预算、timeout、zero-tests、编译失败和proof未知出口；同content hash不通过改名重试。
- [ ] 普通C++候选与cuda-oxide证明候选分别编译；proof候选要求`CUDA_OXIDE_REQUIRE_LEAN=1`、`CUDA_OXIDE_NO_LEAN_CACHE=1`且拒绝export-only与device-debug旁路。fresh构建确保Cargo没有跳过需要重新验证的kernel。
- [ ] 记录完整编译链、依赖、flags/算术模式、实际target/PTX版本、资源、symbol和参数ABI；原语受SM89与frontend双重白名单限制。
- [ ] 证明逐属性报告，不把0义务、inspection、缓存marker、UNKNOWN/ERROR或未运行当PROVED_SCOPED。证明错误不能在原verified身份下静默退成普通候选。
- [ ] 初版优先SM89 AOT cubin；可选Tile只按已探明范围使用，必要JIT在隔离worker prewarm，capture前load完毕。CuTe SM89不支持保持拒绝。
- [ ] 只将满足静态准入的有限候选送K04；此阶段不直接把候选写进生产registry。

**命令性质：** source参考命令见32§4；`python3 tools/inkling-lab/kernel_search.py --plan profiles/kernel-search-plan.json --out evidence/K03-search`是**PLANNED_AFTER_K03**，runner当前不存在。其build-only/动态阶段由冻结plan指定，不能因执行该命令就跳过K04/K05依赖。  
**DoD：** 候选与实际产物/证明绑定可重现；错误能关闭对应路线；没有新运行期编译器/allocator。**停止：** 超预算停止；非法硬件/算术/模板立即拒绝；工具缺失BLOCKED，数学义务失败FAILED原因，未知UNKNOWN原因，均不授证明资格。**测试：** AX01–AX10、AX18；GX01/GX20。

## K04 · ggml-cuda 局部注入、ABI与异步所有权

**依赖 / 初始状态：** K01、K02、K03；NOT_RUN。**条件：** 所用spec/budget基础须有T06/T09资格。**产出gate输入：** G2、G4。  
**输入：** 固定cubin/PTX、KernelContract/ABI、原backend与T05 lease/事务合同。  
**现有触点：** `ggml/src/ggml-cuda/ggml-cuda.cu`与选中的算子分派，原allocator/graph/expert/context。  
**Files NEW：** `ggml/src/ggml-cuda/inkling-kernel-bridge.h/.cu`（选中后创建）、`tests/test-inkling-kernel-bridge.cpp`；必要时极薄Rust host shim，首版不要求它。

**输出 / consumer：** 实现resolve→prepare→enqueue→resolve_ticket→retire；由原Atomic事务消费READY输出。借用现有context/stream/arena；manifest不命中时仅在无提交且无污染的边界走原合格实现。

- [ ] 写AX11–AX17/AX27：参数packing/宽度、错误设备/context、借用资源错误销毁、early Drop、跨stream缺wait、graph过期module、capture失败与异步错误。
- [ ] 首版采用明确scalar、pointer、length/stride ABI；不凭Rust签名猜ptr/len/byval参数，也不跨C边界传Vec/slice/trait object/closure/panic。
- [ ] 所有allocation使用原ledger reserve，module、graph、pinned、arena和输入输出lease纳入generation。图缓存键包含artifact/contract/ABI/shape/address generation。
- [ ] `enqueue`仅返回SUBMITTED，completion event与原错误检查成功后才READY。每ticket唯一，跨请求旧epoch不能复活。
- [ ] 取消/异常只撤销未提交，已提交保活至drain/retire；执行错误sticky，禁止在污染context上原位fallback。无法确认GPU停止时不释放地址。
- [ ] 原bridge保留fallback，module prewarm/load在capture前，切换首版采用排空后新generation，不先造热更新服务。

**命令性质：** `ctest --test-dir build-inkling4090 -R '^test-inkling-kernel-bridge$' --output-on-failure --no-tests=error`为**PLANNED_AFTER_K04**；测试必须注册CTest，缺测试不能成功。  
**DoD：** 无借用资源被错误销毁、无过期图/地址、错误可在token/tool提交前阻断；真实GPU断言和CPU协议测试分别登记。**停止：** 任一污染/越界/悬挂引用立即FAIL并隔离candidate。**测试：** AX11–AX17、AX24、AX27；TC15/TC17/TC19/TC23、GX07/GX12/GX13。

## K05 · Sanitizer、数值、循环状态与资源资格

**依赖 / 初始状态：** K03、K04、T03、T05；NOT_RUN。**条件：** 所选spec/budget另需T06/T09资格。**产出gate输入：** G2、G4、G5。  
**输入：** 已绑定的同一candidate产物、独立reference、冻结tolerance、真实shape/route fixtures与资源profile。  
**Files NEW：** `tests/test-inkling-kernel-runtime.cpp`、`profiles/kernel-candidate.json`；扩展原T07 `tests/test-inkling-kernels.cpp`及T05/T10状态测试，避免第二套循环状态owner。

**输出 / consumer：** 原始sanitizer、operator/model/state/资源records交K06与原gate审查器；每case包含实际执行/skip、输入hash、actual dispatch、失败最小复现。

- [ ] 先memcheck，再racecheck/initcheck/synccheck，设置非零`--error-exitcode`并核对实际kernel/case覆盖；0测试、过滤掉全部kernel或仅打印PASS不能通过。
- [ ] 注入global/arena内部越界、alignment、shared race、未初始化、divergent barrier、cp.async时序与跨stream寿命负例。racecheck不被视为global/FFI所有权证明。
- [ ] 跑0/1、tile±1、非整块尾、实际每dtype/quant/stride/alias和支持B；E保留精确映射，N用既定容差/route/logit/质量；不事后放宽。
- [ ] MoE动态ID/offset/scatter范围与浮点top-k/tie/weight内容分证，非法index不越界且禁止commit；不能静默clamp。
- [ ] 同teacher-forced输入对照24physical/48visit映射、全部per-loop KV/conv/controller；按原TC/GX完成reject、EOS、cancel、save/restore后续接及RNG账本。
- [ ] 重测完整profile容量：module/graph/workspace/repack/pinned/staging同时存在，包含JIT/编译host峰值；GPU/host保留量不缩水，不能靠swap。

**命令性质：** 原生`compute-sanitizer`工具入口见32§5；未来`lab.py qualify --suite G2/G4`分别执行，命令与manifest见32§7。测试suite未实现保持BLOCKED，不生成空PASS。  
**DoD：** 相关新AX与原TC/GX真实执行、原始结果及首个偏差可定位；N质量按T03/T12原流程，局部数值不提前授完整G5。**停止：** 第一个正确性、budget、NaN、截断、错误tool/状态异常停止所有性能计分；修复后受影响依赖测试重新资格。**测试：** AX18–AX24、AX28及适用AX11–17；原TC04–TC23、GX03/07–11/13/15/17/18。

## K06 · 独立确认、registry与回退交付

**依赖 / 初始状态：** K05、T10、T11；NOT_RUN。**类型：** optional_qualification。**产出gate输入：** G2、G3、G4、G5、G6。  
**输入：** 已过正确性/资源门的候选、原baseline、冻结SearchPlan/holdout、完整服务profile。  
**Files NEW：** `profiles/kernel-paired.json`、`profiles/kernel-registry.json`、`tests/inkling_lab/test_kernel_registry.py`、`evidence/K06/`；原T12聚合消费，不变更G7授权。

**输出 / consumer：** `qualify_candidate`签出的范围化gate、immutable registry条目、fallback generation与TASK/EXPERIMENT/DECISION；T12仅选择有完整资格的条目。

- [ ] 最多2个E2E探索者中冻结一个winner与shape dispatch，再打开独立确认集。多winner/反复查看/重选必须新holdout或事前多重比较规则，不能选每个95%CI里最好者。
- [ ] 正式timing不挂profiler/sanitizer，均衡AB/BA、每5对anchor、相同cold/warm与P/N；所有超时/失败/回退请求计入原统计。
- [ ] 每primary cell探索12pairs，确认≥30独立case、≥3时间块、≥10000次case/stratum配对bootstrap；沿原5%/10%中位数、p95与绝对SLO门。
- [ ] 质量仍150 Java/300工具及非劣/重大错误零容忍；tail/soak仍原≥200requests、8h且≥200requests。候选需要的长context证据不能被短算子smoke代替。
- [ ] 测registry旧driver/module/ABI/layout/shape/graph/预算变更失效、禁用candidate与排空切换；恢复在同预算合格路径，从committed prefix重建，不重复工具副作用。
- [ ] 记录维护成本、搜索/编译/证明总成本、探索vs确认偏差、失败数量；不把最快microbenchmark包装成升级理由。

**命令性质：** T01的validate/run/qualify/compare配合K06新profiles，均为**PLANNED_AFTER_K06**，见32§7；当前文档包不包含这些实现。  
**DoD：** 独立确认与原门证据可复核、registry只能命中实际已资格范围、回退演练完成，交付T12可审查候选。**停止：** 质量/状态/资源失败立即隔离；两轮有证据修正后无净益NO_BENEFIT；样本/尾证据不足BLOCKED/INSUFFICIENT_EVIDENCE，不自动续预算或改阈值。**测试：** AX25–AX28及受影响AX；PF01–PF08、QC01–QC08、原SV与GX19/GX20。

## K07 · 独立ggml backend的条件原型

**依赖 / 初始状态：** K02、K05、K06；DEFERRED。**类型：** conditional_research。**产出gate输入：** 受选范围的G2–G6。  
**输入：** 已完成局部bridge/资格经验、剩余关键路径、现有接口限制、维护预算。  
**Files NEW仅在启动后：** `profiles/custom-backend-prototype.json`、backend ADR、op/buffer/event/copy/alias支持矩阵及隔离原型；具体代码路径由ADR冻结，不先创建整个backend。

**开启证据必须同时具备：** 局部路线已检验所有权与fallback；多个相邻算子的dispatch/sync/转换仍有跨原G3门的实测空间；现有backend最小partition/fusion方案确有明确接口限制；完整op matrix、资源与维护成本可审查。“使用Rust”或单个MMA更快不构成触发。K06局部候选NO_BENEFIT不自动授权整后端，需新因果证据。

**接口 / consumer：** 对原ggml scheduler提供`supports_op`、buffer类型、tensor get/set/copy、view/alias、sync/events、graph_compute与partition/fallback；依旧由Atomic持有模型、GGUF、循环状态、预算、事务、server。未支持组合在调度/加载前拒绝。

- [ ] P0：冻结完整接口矩阵和边界，逐项定义原oracle与fallback成本。
- [ ] P1：仅一个有界子图/固定shape，同context接入，先测ABI、copy、arena、event、graph和错误寿命。
- [ ] P2：正式Mini串行完整forward与loop/state/取消恢复，不夹带新量化/spec/R或新模型。
- [ ] P3：对最佳局部backend候选跑原G2/G3/G4/G5/G6与全E2E，不只对未优化baseline；跨backend搬运与调度全部计时。
- [ ] 每阶段给独立停止决定；无收益及时结案，不能因为已投入重构就扩展产品范围。

**命令性质：** 无现成“启动独立backend”命令；具体build/test/launch须在ADR中定义后标PLANNED并实现，禁止猜上游flag。  
**DoD：** 可交付继续DEFERRED、明确NO_BENEFIT、或经所选能力完整资格的受限原型；不自动意味着替换生产。**停止：** 不满足触发、op coverage/状态无法证明、预算/维护成本超出，保持DEFERRED/BLOCKED；最多两轮有profiler依据修正后无益停止。**测试：** 复用AX01–AX28中适用项和原全部所需能力测试；每扩展op/shape增加实际断言，不能用复用ID冒称全部覆盖。

## 3. 共同收尾

按原templates保存TASK、EXPERIMENT、DECISION、真实argv、输入/产物hash、raw日志、失败case、资源轨迹与gate。未执行项为NOT_RUN，缺条件为BLOCKED；CPU工具、proof、作者CI与target_4090分别标证据类型。搜索与确认使用不同数据，旧失败不删除，候选graph/module/arena安全退役。28项AX定义与命令边界集中在[32验证手册](32_kernel_validation_runbook.md)。
