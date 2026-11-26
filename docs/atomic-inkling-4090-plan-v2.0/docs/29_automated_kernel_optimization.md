# 29 · 自动化内核优化：有限搜索、独立验证、真实收益

> **v2来源更新：** 本篇141文件/工具链与CI详细审计基于历史`5e5c77…`；当前main为`f35d6ccc2e03a54e73e3796f415f11313e439d50`，新增#1866写覆盖修复与1D限制，详见[40](40_upstream_refresh.md)。未来K00冻结新pin并重做相关资格；原证据保持原SHA，不冒充新运行结果。

**状态：NEW / PLANNED。** 本章定义 K01–K06 要实现的离线流程；本包没有生成或执行候选 GPU 内核。来源与证明边界见[27](27_cuda_rust_source_audit.md)，宿主所有权见[28](28_custom_backend_architecture.md)，具体算子见[30](30_sm89_kernel_program.md)。

## 1. 自动化应该覆盖到哪里

把 AI 用于提出可证伪的优化假设、选择已审查模板和填写有限参数，把编译、证明检查、输入验证、测量、拒绝和资格登记交给独立的确定性程序。cuda-rust 提供编程前端、编译管线及部分安全验证能力；它没有替 Atomic 提供完整的 AI 内核搜索控制器，也没有证明搜索结果是最快实现。后者是本方案新增的工程工作。

第一轮只处理**一个已被真实 Inkling trace 证实的热点族**。不要同时搜索模型循环数、权重量化、内存分层、kernel、graph 和 speculation；这样即使结果变化，也无法判断原因。普通 CUDA C++ 候选与 Rust 候选使用相同数值、状态、资源和性能合同。Rust 语言选择本身不是性能证据。

最终优化目标是固定业务分布下的完整请求时延和可靠性。kernel 时间、tokens/s、寄存器数、occupancy、理论算力只是定位指标。变更若减少显存但使请求变慢，应单列为容量方案；不能按速度方案授予 G3。

## 2. SearchPlan：在看到候选结果前冻结

K01定义SearchPlan合同，K02产出的 `profiles/kernel-search-plan.json` 为未来文件。包内[搜索策略](../manifests/kernel-search-policy.json)提供初始提案，不代表已经在目标机器上批准或执行预算。SearchPlan 至少包含：

| 字段组 | 必须固定的内容 |
|---|---|
| 身份 | Atomic base/candidate、正式模型与草稿器、R3、完整 target/capability key、GGUF和runtime布局、基线二进制 |
| 环境 | 设备UUID/SM、实际资源、驱动、Toolkit、编译前端/依赖锁、功耗与频率观测策略 |
| 热点 | trace hash、真实dispatch、关键路径比例、命中shape分布、一个优化假设 |
| 数学/存储合同 | 输入输出、dtype/accumulate/rounding、stride/alignment、alias、状态读写、溢出和tail语义 |
| 可变因素 | 单一template family、允许参数域、编译flags、E或N分类、证明是否必需及其属性 |
| 不可变因素 | oracle/fixtures、目标模型、质量阈值、性能主终点、SLO、内存保留量、历史停止记录 |
| 数据分区 | 正确性开发集、性能探索集、独立确认集、质量holdout的hash与访问权限 |
| 搜索预算 | 候选数、构建/证明超时、CPU/GPU探索总额度、最多修正轮次 |
| 结束规则 | FAIL、BLOCKED、NO_BENEFIT、SKIPPED_WITH_EVIDENCE的适用原因；是否进入原G2–G6 |

每个候选由内容hash标识，换名字不获得新额度。失败的源码、编译日志和拒绝原因保留。权限不足或工具不存在时阻塞受影响路线，不能自动升级生产驱动、全局Rust工具链或安装未锁依赖。

### 2.1 初始候选权限

允许从已审计的小域提出 `block={64,128,256}`、`vector={1,2,4}`、`pipeline_stage={1,2}` 等参数；这些只是待收缩的候选域，实际shape、对齐、共享内存、寄存器和前端表达能力决定合法值。不得展开所有参数的笛卡尔积。

可选族包括规则地址的copy/repack、norm/residual/control/conv局部融合、固定量化的GEMV或小B GEMM、已存在图的固定shape参数化。每轮只选择一族。普通 `cp.async` 模板必须包含经过审查的wait、barrier和tail处理；生成器不能自动删同步或插入任意PTX/unsafe逃生口。

不属于本轮搜索空间的变更：R、last-loop或共享KV、LoopCD、2DSD、sampler/RNG、专家选择及tie-break、新量化、训练、CPU线程池重写、未审查的mapped relay、persistent megakernel、额外stream拓扑、生产在线下载/JIT新代码。原R/G任务有自己的合同；本章不替它们开启权限。

## 3. 先证明值得优化，再花搜索预算

从 Nsight Systems 的完整请求时间线判断真正的关键路径；再用 Nsight Compute 检查选中内核的访存、寄存器、spill、分歧、同步与指令使用。不要把重叠执行的kernel时长简单相加成请求占比。NVIDIA的[Compute指南](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)解释了采样、replay、cache与clock对观测的影响。

设某热点在原关键路径中占比为 `f`，只改善该热点且其他工作不变，热点加速为 `s`，则理想请求时延降幅为：

`reduction = f × (1 − 1/s)`，其乐观上限为 `f`。

例如纯示意：占比8%的热点即使快2倍，理想请求仅减少4%，尚不足原单项5%门槛。这不是当前Inkling测量值。融合若同时省去launch、读写或转换，需要把这些成本重新计入明确假设，再实测；不能用Amdahl公式否认融合可能，也不能凭公式宣称收益已实现。

保留完整输入条件：prefix/process/OS cache，prefill与decode，B1与已资格的B2/4/8，短/长上下文，冷启动与稳态，权重是否驻留。编译、module load、JIT、graph capture、首次repack、恢复的成本分别记录；实际请求承担的成本必须进入对应E2E。

诊断默认不改机器时钟/功耗设置。未来在确认本机工具选项后使用 `ncu --clock-control none`，记录cache/replay策略；正式PF/G3计时不挂profiler或sanitizer。工具观测使用的kernel replay结果不能充当业务请求分布。

## 4. 可执行的阶段合同

下列名称是NEW逻辑接口，不表示已经存在十个服务或模块；可由原T01 lab与T07适配器实现。

| 阶段 / producer→consumer | 动作与产物 | 必须拒绝的情形 |
|---|---|---|
| freeze / 工程代理→policy validator | 固定SearchPlan、基线、资格范围、预算和数据集 | 模型或profile不明；历史停止条件未满足；修改了阈值 |
| propose / AI→candidate validator | 输出模板ID、参数、hypothesis与spec hash | 未审计模板、非法SM/dtype、越权变化、重复内容 |
| compile / lab→隔离builder | 保存实际argv、退出码、toolchain、依赖、IR/PTX/cubin/资源报告 | 编译失败、资源超限、目标不符；不在生产context加载 |
| prove / lab→verifier/checker | 对实际MIR及属性运行检查，记录范围、假设、TCB、义务数 | 缺工具、export-only、空义务、未知/超时或未证明却声明verified |
| dynamic / lab→隔离GPU worker | 同产物运行sanitizer和算子oracle，记录actual execution | skip当pass、零launch、错设备、漏case、越界/竞态/同步错误 |
| integrate / lab→Atomic候选 | 固定输入比较每轮state、route、logits及取消/拒绝/续接 | 仅最后logit近似而状态不同；非法fallback；budget越界 |
| explore / scheduler→单GPU worker | micro→整层→完整请求，按额度筛选，收集全部失败 | 选择性删除慢例、并行性能工作、只有微基准收益 |
| confirm / 冻结候选→独立runner | 唯一候选与基线执行原确认集、质量和服务验收 | 重用已看holdout调参；只报最优者；未达原G3–G6 |
| qualify / 确定性审查器→registry writer | 校验全部原始文件/hash、身份、scope与gate | AI自报PASS、仅合法JSON、proof替代数值、缺真实4090证据 |

registry写入只创建已资格的候选generation。T12是发布候选，生产G7仍读取当时执行会话的授权；搜索器不能直接改线上dispatch。

## 5. KernelCandidate与ProofBinding

包内新增[候选记录Schema](../manifests/kernel-candidate-contract.json)及[NOT_RUN示例](../manifests/kernel-candidate-example.json)。它们与原 `run-contract.json`、`gate-contract.json`并存：候选记录保存编译/证明/实际执行事实，run保存某次测试，gate保存资格决定。候选顶层 `qualification` 固定为 `NOT_ASSESSED`，禁止把编译或证明结果写成自动上线决定。

### 5.1 必须绑定的证据

1. **语义与范围**：spec、KernelContract、参数ABI、shape/layout/alias/launch范围、输入输出及状态effects的hash。Host侧检查证明前提；device动态索引另有producer范围合同与错误传播。
2. **源与编译**：候选源、template、完整依赖锁、宏/前端/MIR转写器/LLVM、Rust、Lean、Toolkit/ptxas/libdevice、精确flags；记录实际验证IR和发射IR。C++/SIMT链保存PTX/cubin；Tile链保存Tile IR、bytecode、tileiras身份和cubin，不要求并不存在的PTX。SASS按可获得性记录，不能伪造缺失文件hash。
3. **证明**：属性/定理、假设、允许公理、实际检查命令/退出码、非零义务总数、已证/失败/未知数、checker日志hash；可信组件和未证明链接显式列出。
4. **执行**：SM/UUID、driver、执行种类、真实launch计数、输入输出、oracle、完成event及原始记录hash。`compile_only`、`ptx_static_check`、`arch_skipped`与`actual_gpu_execution`分别记账。

`proof.status` 使用 `NOT_REQUESTED / NOT_RUN / PROVED_SCOPED / FAILED / UNKNOWN / UNSUPPORTED / ERROR`。这不扩充原task/gate状态机。普通C++可用NOT_REQUESTED走原动态资格；要求verified的方案遇到UNKNOWN不能降格后继续沿用相同身份。显式改为普通路线须另建计划与能力key，并保存失败历史。

`PROVED_SCOPED`只说明指定模型与假设下的属性。不得标成“浮点正确”“模型等价”“所有unsafe已消除”“整个编译器已证明”或“机器码最快”。`0 sorryAx`仍允许受登记的Lean基础公理；它不代表零可信基。源→MIR→PTX→cubin的hash链证明产物身份对应，**不证明每步编译语义保持**。当前证明范围与TCB见27。

本版候选Schema对Tile成功构建要求 `tile_ir / tile_bytecode / tileiras / cubin`，`ptx`可为null；`AOT_CUBIN`在此表示进入Atomic资格与capture前已经完成预热并冻结的cubin，而非保证上游首次调用没有JIT。C++/SIMT成功构建要求PTX。实际验证与发射IR按对应前端解释，不能为了通过Schema伪造另一条编译链的中间产物。

### 5.2 防止错误复用

更改源码、模板、编译flags、依赖、MIR转写器、证明前提、ABI、shape范围或机器产物都使相关证据失效。更换driver/JIT路径、实际设备或runtime布局至少重新验证受影响的执行、数值和性能资格。固定cubin与PTX-only JIT是不同路径；不能把旧cubin的实测资格传给未知JIT结果。

Proof checker必须验证实际非空义务、每项已证、`sorryAx=0`、公理白名单、无unchecked/export-only/debug绕过，并核对绑定的MIR/hash。仅存在 `.verified` 标记或 `lean-export` exit0不充分。编译/证明的外层wall timeout与内存额度由controller执行；UNKNOWN、超时或OOM保存原因后结束，不提升为PASS。

JSON Schema仅能检查字段和有限条件。它无法核对文件内容、义务求和、证据真实性、完整alias范围、实际GPU型号或性能统计；这些是K01/T01语义验证器的任务。示例全null/NOT_RUN，不填合成测量。

## 6. 动态检查与循环模型的额外要求

[Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/)的memcheck/racecheck/initcheck/synccheck覆盖不同错误，`error-exitcode`默认0。因此未来runner显式设置非零错误退出码并验证被测case和实际kernel覆盖。工具无报告不代表所有arena子分配或global跨stream所有权安全；另用边界redzone/alias/lease/epoch oracle，先证明这些oracle能被故意坏例触发。

数学oracle、内存安全oracle、事务oracle分开。规则repack可验证逐元素精确映射；改变归约次序、累加、dequant/fusion通常按N类审查。MoE必须核对真实expert IDs、route weights、slot/group/scatter对应、near-tie和各loop路径。证明“有效索引下不越界”没有证明router实际产生了正确的有效索引。

同一组物理权重可跨loop复用；KV、conv、位置、有效长度、滑窗、loop消息、DSpark特征、RNG与接受前缀继续遵守05/07/13，不因新内核而共用。拒绝、EOS、取消、续接和异步失败均应测试。完整模型实际改变的数值/状态范围决定相关TC/GX/QC重跑集合；AX不能替代原48+20项。

## 7. 搜索成本与统计纪律

建议第一轮上限：一个热点族；初始方案加最多两轮有profiler因果依据的修正；累计24个不同候选，最多4个进入GPU microbench，2个进入E2E探索，1个进入独立确认。探索CPU编译/证明累计wall预算2小时、目标GPU探索4小时，单候选compile和proof分别5分钟；这些是**可在看数据前调整的策略提案**，不是已测最优值、租机授权或全部验收限时。完整确认、数值/质量/soak另有预算，不能删测以塞进探索额度。

编译可在不干扰服务的资源范围内并行；累计wall耗用按每项实际耗用相加，不把并行当作免费额度。GPU性能worker始终1个。timeout后的候选被隔离；无法确认device已完成时按28退役，不能释放在途地址。

沿用[14统计合同](14_benchmarks.md)与机器policy：探索12 pairs/cell；确认至少30独立case、3时间块、10000次配对bootstrap；同case重复和不同seed不新增独立样本。平衡AB/BA，原每5pairs anchor、漂移处理、完整失败记录保持。

一次确认只评估一个预先冻结的赢家；看到holdout后改tile/shape分派/阈值/赢家，就不能继续把该数据称为独立确认。多赢家或序贯决策必须事前登记多重比较/序贯方法与新样本预算。探索最大加速和独立确认效果分别报告。

原门槛不变：单项预登记加权中位数时延降低至少5%且CI支持正收益；主力迁移至少10%；关键p95回退≤5%且满足绝对SLO；Java150/工具300独立case及2/1个百分点非劣规则；至少8小时并完成200真实请求的soak。正式业务基准、完整资源和服务范围以原13/14/20及validation-policy为准。

统计所有真实请求，包括未命中候选和fallback。报告shape覆盖率、dispatch命中率、fallback原因、资源峰值和冷启动影响。微基准快而完整请求不达门槛可NO_BENEFIT结案，不因此自动启动独立后端重写。

## 8. 停止、恢复和可复用成果

`stop_registry`记录family、目标、experiment ID、失败/无收益原因、原始证据和重新开启所需条件。新编程语言、形式证明或不同项目的跑分，不足以重新开启此前无收益的CPU pool、launch overlap或DFlash2方案；必须有新的Inkling trace与变化的成本结构。

正确性/资源错误立即停止性能计分并隔离候选。预算不足以完成资格则BLOCKED；受限搜索已经完成且未达到收益则NO_BENEFIT；平台明确不支持则记录UNSUPPORTED原因并有据跳过受影响路线。最终task枚举仍按AGENTS，不把具体reason_code冒充状态。

即使没有性能收益，也可交付可复用的合同、坏例、工具链探针、布局分析、proof边界与失败证据。它们提高后续优化可靠性，但不应在性能结论中折算成不存在的加速。

下一步按[31任务](31_kernel_tasks.md)和[32测试运行手册](32_kernel_validation_runbook.md)实施；本次全部K/AX目标执行状态保持NOT_RUN，K07保持DEFERRED。

## v2.0 · Magnitude补充：证据与编译缓存分离

借鉴其tuning文档的coverage、失败和停止原因记录，维持本包SearchPlan预算及独立holdout。compiled artifact key与qualification key分离；改变driver、compiler、layout、shape域、模型表示或资源配置时按影响面重验，缓存命中不能恢复旧PASS或授予新搜索预算。上游precision文档对per-row storage-noise阈值仍列开放问题，不能替换本包N类误差、Java/tool质量与E2E门。M02/MGX11只扩展原K清单，不另建资格registry。[41](41_magnitude_source_audit.md)。
