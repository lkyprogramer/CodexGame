# 27 · NVIDIA CUDA Rust：版本、SM89能力与形式验证边界

> **v2来源更新：** 本篇141文件/工具链与CI详细审计基于历史`5e5c77…`；当前main为`f35d6ccc2e03a54e73e3796f415f11313e439d50`，新增#1866写覆盖修复与1D限制，详见[40](40_upstream_refresh.md)。未来K00冻结新pin并重做相关资格；原证据保持原SHA，不冒充新运行结果。

**版本：1.2 · 审计日期：2026-11-25。** 本文依据公开原文、固定提交源码、发布记录及GitHub Actions原始日志编写。本轮只做来源审计和工程设计，没有安装目标工具链、构建内核、连接4090、运行Inkling或部署服务。本文中的外部CI成功与作者跑分，均不改变本机测试的 `NOT_RUN` 状态。

## 1. 采用结论与证据口径

NVIDIA CUDA Rust值得纳入本包的自定义内核研究，但目前不能替代Atomic已有的Inkling执行器。最容易控制范围的接入方式是：**Atomic继续拥有模型、状态、预算和调度；从真实热点选择单个算子，使用固定SIMT编译器生成SM89设备产物，再通过ABI、资源生命周期、数值、状态和性能资格。** Tile是另一条候选路线；当前CuTe Rust preview的架构白名单直接排除SM89。[CR01]、[CR12]、[CR15]、[CR16]

文章中的Lean验证已经有可运行实现、负例及编译CI，并非只有设计草图。但它证明的是特定MIR模型上的列明安全性质，不能证明完整模型数学正确、最终机器码语义正确或性能最优。它可以成为候选筛选的额外关卡，不能替代GPU测试和业务验收。[PF01]、[PF02]、[PF04]

本文使用以下口径，执行状态仍遵守根目录AGENTS.md：

| 证据类别 | 本文含义 | 不能据此宣称 |
|---|---|---|
| 源码事实 | 固定commit中存在明确实现、目标表或拒绝逻辑 | 本机已构建、GPU已执行 |
| 外部CPU CI | 已读取对应run/job日志，确认实际执行的编译或证明检查 | SM89正确性、无race、实际吞吐量 |
| 外部GPU CI | 日志中有具体GPU与测试执行证据 | 用户4090通过，或最新main的所有路径通过 |
| 作者性能声明 | 特定设备、形状和实现的公开测量 | 本机收益、Inkling端到端收益 |
| 工程推断/设计 | 本包根据上述事实提出的接入和停止规则 | 上游已提供该Atomic adapter |
| `NOT_RUN` | 本包尚未执行该资格 | 用零、mock或CPU绿测试填补结果 |

“源码不支持”是能力原因，不新增任务状态。例如CuTe/SM89任务应标 `DEFERRED` 并记录架构不支持；目标机器或工具不可用时标 `BLOCKED`。

## 2. 固定版本、发布与squash合入

| 身份 | 已核查版本 | 使用规则 |
|---|---|---|
| 本文审计main | `5e5c77b19a4b3204d6542bab2f0fde2a4eed824b`；2026-11-23 15:43:36 UTC | 本文所有源码能力均绑定此commit |
| cuda-oxide最新发布 | `cuda-oxide/v0.4.0` → `9d0c9bfbc954a9a29565ab81b78da70f054d8e04`；2026-11-11 | 不把main新增验证能力自动归给此发布 |
| cutile-rs最新发布 | `cutile-rs/v0.5.0` → `e706cab335828f6be1a6d5990e7a9c2ce08e1cb0`；2026-11-05 | annotated tag须解析到最终commit |
| release/v0.5.x分支 | `deecff63f4a6d28de1054c73b03e13f41c730ab8` | 与v0.5.0 tag不是同一身份 |
| proof hardening分支 | `fix/oxide-proofs-hardening@b569d9bc9f79ebe6d186cf9b177cb00311739bcc` | PR #1857已经合入main，不重复拼补丁 |

以上发布和分支身份来自[发布API][CR04]、[固定main提交][CR02]及[PR #1857][CR03]。根README仍称early-stage research，cuda-oxide仍属alpha/preview；release元数据中的 `prerelease=false` 不构成生产成熟证明。[CR01]、[CR33]

### #1857已合入，ahead/behind不能替代源码比较

固定main提交本身就是#1857的squash合入。该PR于2026-11-23 15:43:37 UTC显示merged。保留的修复分支相对main的compare结果为 `ahead=2 / behind=1 / diverged`，但本次分别读取递归tree，逐路径比较5350个blob，**差异为零**。因此，分支SHA不同不代表修复未进入main。[CR02]、[CR03]

后续工程必须锁commit、Cargo.lock和编译工具身份。禁止将浮动main、自动更新结果或另一release的产物混进同一次实验。版本改变后重新判断能力和资格，不能只修改来源表日期。

## 3. 四套组件必须分开判断

| 组件 | 固定源码能确认的能力 | RTX4090/SM89采用判断 |
|---|---|---|
| **cuda-oxide原生SIMT** | Rust经MIR/IR生成PTX；显式SM89目标；warp/shared/MMA/cp.async原语 | 可进入局部算子构建实验；本机编译、运行和Inkling资格均 `NOT_RUN` |
| **cutile-rs Tile** | Tile IR目标registry含SM89；baseline最低emitted Tile IR为13.2 | 可研究受支持dtype和非TMA模板；不代表全部kernel可在4090使用 |
| **cute-rs-preview** | CuTe MLIR exporter只接受 `sm_100a/103a/107a/120a` | 当前SM89被显式拒绝，相关路线 `DEFERRED`；不通过改字符串绕过 |
| **cuda-core / cuda-async** | context、stream、buffer、event、graph、foreign handle等共享宿主API | 可参考或通过窄接口借用；第一阶段不接管Atomic分配器、账本、图池和服务调度 |
| **SIMT Lean preview** | 在PostMem2Reg处证明选定安全义务并删除已证明冗余检查 | 可选证明资格；不自动覆盖Tile/CuTe、所有unsafe或C++宿主 |
| **Inkling完整后端** | 审查范围内未见与Atomic正式R3、GGUF量化、原生DSpark状态事务匹配的完整适配 | 仍需本包实现；不能从通用GPU库功能表推定现成支持 |

SIMT、Tile与CuTe判断分别来自目标表、Tile feature registry和CuTe exporter构造函数。[CR12]、[CR15]、[CR16]、[CR17] **cutile-rs与cute-rs-preview不是同一项目子系统。** CUTLASS C++或其他CuTe实现能运行Ada，也不能给当前Rust preview授予SM89资格。

### SM89原语与模板矩阵

| 能力 | 固定源码/架构限制 | 本包处理 |
|---|---|---|
| warp索引、shuffle、ballot、reduction、shared | SIMT接口存在；shared初始未初始化 | 候选仍须验证mask、参与线程、初始化和同步 |
| `ldmatrix`、FP16/BF16 `mma.sync.m16n8k16` | 前者SM75+；后者SM80+/PTX7.0+，API有unsafe合同 | SM89可研究；packing、lane布局、对齐和累加语义另验 [CR18] |
| 普通global→shared `cp.async` | 4/8/16B等形式，SM80+，有commit/wait接口 | SM89可研究；不能遗漏issuer completion、跨线程barrier和地址寿命 [CR19] |
| Tile普通f16/bf16/f32 | baseline接受SM89；具体模板有自己的限制 | 逐模板确认；现有f16 GEMM有非TMA模式，但其输出f32不能冒充f16版本 [CR12]、[CR27] |
| Tile FP8 | registry将FP8类型门槛设为SM90+ | 当前Tile/SM89拒绝；Ada硬件有FP8不等于这个软件路径支持 [CR12]、[CR13] |
| Tile NVFP4/block-scaled MMA | SM100+、Tile IR13.3+ | 4090不采用；软件解码是另一实现与精度合同 [CR12] |
| TMA、cluster、DSMEM、PDL | 对应Hopper及更新架构路径；Tile相关feature有独立gate | 4090不得启用，不靠改target获得硬件能力 [CR12]、[CR17] |
| wgmma、tcgen05、TMEM、CLC | 相应Hopper/Blackwell及更高专用路径 | 不复制到SM89；B200共享内存与流水资源也不适用 |

host Future/async、stream/event异步传输、设备cp.async是三层不同机制。任何一层都不会自动完成Atomic专家staging的预算、lease、取消drain和失败context退役协议。

## 4. Rust、CUDA、LLVM与driver分别冻结

### 4.1 工具链输入

| 路线 | 固定源码条件 | 复现记录要求 |
|---|---|---|
| cuda-oxide SIMT | stable Rust **1.99.1**，含rust-src/rustc-dev/llvm-tools等组件 | 记录精确rustc/backend身份；stable不代表任意rustc版本可替换 [CR05] |
| shared host workspace | stable Rust **1.98.0** | 不与SIMT workspace pin混用 [CR06] |
| cutile-rs | checkout pin **1.98.0**；README最低声明 **1.89+** | 复现固定checkout使用其pin；最低声明不是实验pin [CR07]、[CR08] |
| SIMT CUDA构建 | Toolkit **13.0+**；LLVM **21+**且含NVPTX，Clang/libclang等 | 保存实际llc/ptxas/NVVM/nvJitLink/libdevice；当前CI使用LLVM23 [CR09] |
| shared binding | `MIN_CUDA_VERSION=13000`，根据本机CUDA header生成绑定 | header版本也是输入，不能只写driver版本 [CR10] |
| Tile SM89 | emitted Tile IR baseline最低 **13.2** | 锁tileiras版本、实际emitted IR和目标，不以安装目录名代替 [CR12]、[CR14] |
| CuTe preview | CUTLASS compiler **4.8.1**与对应MLIR profile | 该pin仍不使SM89可用 [CR15] |
| Lean proof | `leanprover/lean4:v4.33.1` | 保存proof库、生成Lean和实际执行日志 [PF14] |

LLVM版本必须随实际PTX/intrinsic需求核对：README的LLVM21+是可选发现/部分路径声明，不能作为所有kernel的统一保证；当前完整examples CI使用LLVM23，并明确其PTX9.1及特定packed-FP8需求。较早的ldmatrix/stmatrix相关路径曾要求22。SM89目标并不会自动使所有低版本LLVM合法；K00冻结实际前端、指令集与可工作的组合。[CR09]、[CI01]

SIMT/Tile文档的测试平台包含Ubuntu24.04；用户现场OS、driver和Toolkit仍需T00采集。不得因引入研究工具链而自动升级Atomic现有生产环境。[CR08]、[CR09]

### 4.2 Driver不能只比较一个版本号

源码中的shared loader，在 `cuDriverGetVersion` 成功时只拒绝runtime CUDA major小于编译header major。此检查不等于每个可选symbol、PTX版本和GPU特性都兼容。[CR11]

| 信息 | 准确解释 |
|---|---|
| NVIDIA CUDA13.x通用minor compatibility最低分支R580 | 有新feature和PTX JIT限制，不能据此保证所有13.x产物运行 [CR31] |
| CUDA13.2 GA官方完整对应Linux driver 595.45.04+ | 发布配套信息，不是本次测出的Tile/4090最低driver [CR32] |
| SM89目标表记录PTX floor 7.8 | 特定指令/生成路径可以抬高最终版本；必须读取实际PTX `.version/.target` [CR16] |
| NVVM/nvJitLink生成路径 | 可能输出比普通LLVM路径更新的PTX；旧driver JIT可能报222/unsupported PTX [CR09] |
| 离线CUBIN | 可以免去该产物的运行时PTX JIT，但仍须匹配SM、driver feature、entry ABI和context |

本次未得到“Tile13.2 + RTX4090 + R580”专项运行证据，精确最低兼容组合保持未知。未来验收要锁实际产物和工具链组合，不要求用户为未经测量的收益先升级驱动。

## 5. 与Atomic C++/ggml的真实接点

**工程建议：首选独立PTX/CUBIN模块边界。** 保留Atomic对权重、GGUF、KV/conv、logical visit、DSpark、CUDA stream/event、graph和budget ledger的所有权；Rust工具链只贡献候选设备kernel。上游确有artifact层、PTX/CUBIN加载及materialize/finalizer接口，但没有因此提供本包所需的Atomic adapter。[CR20]、[CR23]

需要Rust host或Tile JIT时，再考虑窄的 `extern "C"` 桥接。上游的borrowed context/stream、`RawDeviceBuffer::borrowed_from_raw_parts`、`DeviceAllocation`和event完成期保活可作为基础。**borrowed不等于转移销毁权，owner token也不能阻止C++另一处提前释放或并发写入。** 外部地址、范围、context、alias、epoch/generation、event和graph引用要与Atomic现有账本统一。[CR21]、[CR22]

接入前必须输出可审查的entry ABI：symbol、参数顺序、位宽、size/alignment、aggregate offset、长度/stride、const参数及产物hash。Rust slice常被展开为pointer/length，by-value aggregate又可能作为一个byval参数；不能凭Rust源码签名猜测C++的 `kernelParams`。首版避免在C边界传Rust容器、trait object或closure，升级compiler后重新核对ABI。[CR20]

仓库存在C++与Rust双向device FFI/LTOIR例子，但公开示例的验证环境/默认脚本为RTX5090/SM120；**SM89 device FFI资格仍未取得**。只有确实需要跨语言device函数复用时，才增加nvJitLink、LTOIR和符号ABI的复杂度。[CR24]

Tile的JIT、specialization和cache还要记录cold/hot成本、capture前warmup、编译失败及旧产物失效。外部CUDA kernel可共享stream，不代表两套allocation或graph cache自动统一。[CR25]

具体桥接、fallback和故障处理由 [28 后端架构](28_custom_backend_architecture.md)定义；本节提供来源能力，不宣称桥接已经实现。

## 6. Lean验证实际证明的内容

[文章原文][PF01]链接的实现就是当前仓库中的 `oxide-proofs-preview` 和 `lean-exporter`。编译器在PostMem2Reg后、循环展开和LLVM/PTX lowering前生成Lean的 `MirFunc/ControlFlowCfg`，构造验证条件，使用Lean内的符号执行、分析和 `mir_vc/omega` 完成证明。成功后只删除登记为已证明冗余的 `mir.assert`。这不是通用SMT优化器，也不是已经提供AI性能搜索controller。[PF04]、[PF05]

| 义务 | 证明覆盖 | 仍须独立验收 |
|---|---|---|
| `no_oob_idx(slice)` | 满足validInput/validThread前提下，指定slice的可达访问index小于长度 | 未指定pointer、FFI、对齐与真实buffer有效性 |
| `no_oob_idx(SHARED)` | 指定SharedArray的访问范围 | 未建模别名/硬件操作、实际lowering |
| `disjoint_writes(out)` | 同参数同位置且至少一方写的事件必须来自同线程，包含读写冲突 | 跨kernel/stream并发、外部C++访问 |
| `no_data_race(SHARED)` | 同CTA、同barrier phase、未由模型mbarrier handoff排序的冲突 | 完整NVIDIA弱内存模型、任意原子协议 |
| `writes_all_elems(out)` | grid覆盖等条件下，每个输出index有从入口0执行而来的写事件 | 写入值正确、完整GEMM等式、恰写一次 |
| `uniform_barriers` | CFG中的同步路径、初始化dominance、arrival counts和back-pressure等 | 任意调度公平性、系统级活性、所有内核终止性 |
| `tmem_lifecycle`及自动附加义务 | 已建模TMEM分配/释放、MMA/commit/wait/ld顺序、边界/warp切片/cluster rank | 4090并不具有这些Blackwell硬件能力 |
| `MirAssertRedundant` | 指定可达assert条件恒真，支持删除该检查 | 手工unchecked-indexing不是同一证明过程 |

定义可直接定位到[内存/输出合同][PF02]和[控制流合同][PF03]。整数位宽、wraparound及checked overflow已有建模；浮点和部分聚合值按opaque处理。**安全证明不证明FP16/BF16误差、NaN、reduction次序、量化scale、attention数学、模型logits或工具调用正确。**[PF07]

所有结论都有前提。若改了shape、dtype、stride、layout、block/grid、别名规则或launch contract，就必须重新确认义务及证明。数据决定routing/index/分支时，要审查opaque抽象是否足够，不能沿用“浮点值永不影响地址”的一般化说法。

Rust生成的PTX由Atomic C++启动后，Rust宿主borrow checker不会替C++证明存活、对齐、alias和异步完成。用Lean证明一个相似算法模型，也不能把证明授给独立生成的C++ kernel。两种情况均需明确记录证明对象与实际产物之间的边界。

## 7. 不能忽略的信任边界和绕过路径

### 7.1 0 sorryAx不等于零公理

runner拒绝Lean非零退出、`sorryAx`、使用sorry的警告以及不在白名单的axiom。实际允许的基础公理是 `propext`、`Quot.sound`、`Classical.choice`，生成器为主要定理输出axiom依赖。因此正确表述是“未使用sorry/admit补洞，并在规定公理白名单内检查”，不是“完全无公理”。[PF04]、[PF05]

本次静态源码扫描未检出显式axiom/sorry/admit声明；静态扫描仍不替代Lean运行。外部无缓存CI的证明证据另见第9节。

### 7.2 证明未覆盖最终PTX/CUBIN的语义等价

Rust→MIR、mem2reg、MIR→Lean转录、检查删除、后续优化、LLVM、ptxas以及host/CUDA运行环境均属于需要信任的链路。当前证明入口没有检查“最终PTX/CUBIN语义与Lean模型一致”的完整证书。给PTX/cubin增加哈希、target和ABI记录能绑定工程证据，但不能把追踪字段说成已完成translation validation。[PF04]、[PF05]

proof cache用SHA-256覆盖Lean toolchain文本、proof库 `.olean/.lean` 和生成Lean；命中 `.ok` marker便返回成功。它是提速缓存，不是签名证书，也不直接绑定driver、C++wrapper或最终cubin。正式准入采用无缓存验证，候选生成器不能同时修改proof库、验证器、cache marker、oracle、阈值和结果日志。[PF04]

### 7.3 `lean-export`成功不是证明成功

`cargo oxide lean-export`的inspection路径设置 `CUDA_OXIDE_LEAN_EXPORT_ONLY=1`；runner会在调用Lean及删除assert之前返回。命令还会恢复/移除inspection生成的PTX。它用于查看MIR与Lean文本，**不能记为proof PASS**。正式构建应清除并拒绝继承export-only开关，证明日志必须能确认所需定理实际执行。[PF04]、[PF13]

当前main已经拒绝verified kernel搭配 `--device-debug`，上游指引为使用 `--lineinfo`。不得为了调试方便再次绕过该拒绝。[PF06]

### 7.4 超时和无法证明都不授予资格

生成Lean设置 `maxHeartbeats=20000000`、`maxRecDepth=65536`；Rust runner未见wall-clock timeout。Python proof/exporter检查有各自超时。自动搜索controller还需限制进程时间、内存及候选预算。[PF04]、[PF05]

超时、unknown、unsupported、工具缺失和异常均不能升级为PASS。合法但暂时无法证明的候选，可以另走普通CUDA测试路径，前提是不沿用“已证明”标记、不删除依赖缺失证明的检查，也不保留依赖该证明的safe API承诺。详见 [29 自动优化流程](29_automated_kernel_optimization.md)。

## 8. 已合入hardening与B200示例的实际边界

### 8.1 #1857修复应作为回归要求，不当作当前未修漏洞

| 历史修复类别 | 影响层级 | 本包最小阻断范围 |
|---|---|---|
| 输出早退/常量槽、shared未初始化、barrier invalidation/arrival、leader/convergence、TMEM free偏移 | 证明规格与验证准入 | 对应负例未通过时，不授予该性质及依赖它的检查删除 |
| 2D laneId、checked overflow、pointer元素大小cast、unknown call | MIR→Lean转录 | 不能接受受影响操作的proof；不等于普通SIMT lowering全面失效 |
| device-debug绕过、宏unsafe吞用户表达式、SharedElement位模式 | 构建强制性与safe API | 拒绝不合格构建组合/API输入，不把wrapper当完整宿主安全证明 |

这些修复都在固定main中，主回归函数可定位到 `lean-exporter/tests/export.rs:2041–2258`。[CR02]、[PF08]、[PF09] 本次未本地实跑复现旧版本漏洞，也不把这些历史问题外推为整个仓库或Tile不可用。

### 8.2 最强GEMM不是整个kernel全IO零unsafe

`safe_vecadd`确有普通 `&mut [f32]` 版本，声明三个slice的边界、输出独占和覆盖；宿主也做输出检查。这能支持“简单SIMT kernel可用安全Rust表达并自动证明跨线程安全”的结论。[PF12]

`safe_gemm_sol_final`则应按实际verify列表理解：

- `kernels.rs:152–156`主要列SMEM、TMEM、metadata、barrier/race/lifecycle义务，没有给 `out` 声明bounds、disjoint或writes_all。
- `kernels.rs:700–703`仍通过显式unsafe的 `out.as_mut_ptr().add(...).cast::<U32x4>()` 写向量输出。
- host的TMA descriptor、模块加载及部分launch仍有unsafe责任。

因此，27个assert被证明并删除，不等于整个GEMM及所有IO已完全验证。本报告据源码限定证明范围，没有据此声称当前实现已经发生内存错误。[PF10]、[PF11]

### 8.3 不支持硬件时也可能exit0

`safe_gemm_sol_final/main.rs:509–523`在不支持tcgen05的GPU上，有PTX时可以只检查target/entry并打印PASS后返回；无该PTX时也可能打印Note后成功退出。**4090或5090上的exit0，不证明这个最终GEMM实际执行。** 验收须检查设备、实际launch、输出核对和RESULT；skip单独标 `SKIPPED_WITH_EVIDENCE`，不能合并为GPU PASS。[PF11]

## 9. CI和性能：实际证据分账

| 证据 | 已观察内容 | 可授予的结论 |
|---|---|---|
| [当前main CI](https://github.com/NVIDIA/cuda-rust/actions/runs/45208439132) | 53个job成功，CPU runner；包含unit、lint和Lean | 有实际工程CI，不是4090测试 |
| [当前main Lean job](https://github.com/NVIDIA/cuda-rust/actions/runs/45208439132/job/137811268879) | 31 passed、0 failed；37行明确negative mutation拒绝结果 | 固定版本proof/exporter外部CPU回归通过 |
| [当前safe_*编译job](https://github.com/NVIDIA/cuda-rust/actions/runs/45208438950/job/137810884011) | 9个crate无缓存构建/验证；最终GEMM删除27检查；GPU-less | 实际编译链存在；目标sm_90a/sm_100a，没有sm_89资格 |
| [当前main Tile workflow](https://github.com/NVIDIA/cuda-rust/actions/runs/45208438968) | workflow success，但只有changes成功，其余8项含GPU tests被跳过 | 不能写“当前main Tile GPU全通过” |
| [近期实际Tile GPU run](https://github.com/NVIDIA/cuda-rust/actions/runs/44581517212) | 2026-11-19、commit `8046b9e9...`；两个job在RTX PRO 6000 Blackwell执行，CUDA13.5/13.3 | 项目确有真实GPU CI，仍非4090与当前main完整资格 |
| 作者B200表 | 大方阵4096³/8192³/16384³；verified约1858.4/2082.3/2118.4 TFLOP/s，与unchecked相近 | 作者特定kernel微基准，不能换算Inkling/4090收益 |

safe_*工作流明确列出GPU-less runner、无缓存环境和sm_90a/sm_100a目标；这些属于编译资格。[CR28] 实际Tile GPU job为[135770641678](https://github.com/NVIDIA/cuda-rust/actions/runs/44581517212/job/135770641678)和[135770641930](https://github.com/NVIDIA/cuda-rust/actions/runs/44581517212/job/135770641930)。13.3 lane部分tile-library测试可因版本不足跳过却返回pass；13.5 lane设置 `CUTILE_REQUIRE_TILELIB=1` 阻止该类静默跳过。审计应区分workflow、job、step、test及实际device launch。[CR30]

另外三点直接影响复现口径：

1. 普通 `cargo test -p lean-exporter` 在Lean缺失时部分测试会return；上游proof CI设置 `CUDA_OXIDE_REQUIRE_LEAN=1` 和 `CUDA_OXIDE_NO_LEAN_CACHE=1`。只跑数学模型checker，不足以检查Rust/MIR提取和编译集成。[PF09]、[CR29]
2. 文章和源码注释说plain-slice vecadd删除3检查，当前CI两种vecadd均报该阶段删除2个；必须使用本次同pin编译日志和产物，不能机械复制文章计数。这个差异本身不证明代码错误。
3. 当前GEMM的RESULT明确是 **FP16输入、BF16输出、FP32计算**，采用median batch mean；4096³ Walsh数据做全输出检查。它不证明所有随机值、非方阵、尾块和量化模型正确。文章简称BF16 GEMM不能改写成BF16输入测试。[PF11]

## 10. 对Inkling的可迁移价值与拒绝条件

### 10.1 候选顺序由profiler决定

作为工程设计，优先从有热点证据、ABI简单、状态边界清晰的pointwise、norm/residual、copy/repack或规则索引开始。SIMT MMA/普通cp.async和Tile非TMA模板可以作为后续dense/prefill原型；数学、输出dtype、尾块和预算匹配后才比较收益。地址证明可以帮助量化unpack的索引检查，却不能替代量化值正确性。

上游Tile库的f16 MoE、FP32 atomic combine、fused QKV/FP8 scatter及NVFP4路径不能直接作为GGUF IQ2/IQ3/Q4_K或正式Inkling循环的drop-in。尤其不能为了复用kernel而把低比特权重展开成FP16、改变R3/DSpark语义或遗漏conv/KV状态。[CR26]

语言变化不会增加24GB显存或PCIe Gen3带宽。新编译器、JIT缓存、module、workspace、repack和graph的占用必须计入同一预算。是否采用，取决于真实模型和形状下的净收益及维护成本。

### 10.2 必须在launch前拒绝的组合

- target/指令/资源不适合SM89，或试图绕过CuTe/Tile的架构feature gate。
- 未提供准确ABI、shape/dtype/stride/alignment、alias或owner寿命合同。
- 产物、compiler、host wrapper、proof输入或模型身份与来源锁不一致。
- proof候选只跑lean-export、继承export-only、出现超时/unknown/unsupported，却要求删除检查或保留已证明标记。
- 未指定pointer、opaque或手写unsafe部分没有审查，却把整个kernel当作完全安全。
- Rust/C++桥接未落实event、allocation generation、graph与预算保活。

执行期发生内存、同步或sticky CUDA错误时，drain并退役相关context/worker；不能在同一失效context上换回C++继续服务。数值、状态或业务质量不符时隔离候选，保留证据与主线fallback。性能无收益按原停止规则记录 `NO_BENEFIT`，最多两轮有profiler证据的修正。

### 10.3 后续文档和任务入口

| 后续文档 | 使用本文什么结论 |
|---|---|
| [28 自定义后端架构](28_custom_backend_architecture.md) | PTX/CUBIN与窄FFI选择、ABI、单一所有权、fallback |
| [29 自动内核优化](29_automated_kernel_optimization.md) | 生成器/验证器隔离、proof对象绑定、预算与停止规则 |
| [30 SM89内核计划](30_sm89_kernel_program.md) | 原语/模板矩阵，Inkling算子语义与实测热点 |
| [31 内核任务](31_kernel_tasks.md) | 固定版本、待实施接口、依赖与各阶段资格 |
| [32 验证运行手册](32_kernel_validation_runbook.md) | 无缓存证明、负例、GPU实际执行、Sanitizer及端到端测量 |

普通C++/CUDA候选优化可独立推进，不以Lean路线成功作为所有优化的前置条件。启用某个可选实现后，它必须提供对应资格；未启用的研究路线不自动阻断T12。

## 11. 当前状态与最终采用门槛

| 项目 | 当前状态/结论 |
|---|---|
| 版本、目标表、公开源码与上游CI审计 | 已完成来源核查；只授予来源证据，不授予GPU资格 |
| 本机Rust/Lean/LLVM/Tile构建 | `NOT_RUN` |
| RTX4090实际load/launch/数值/Sanitizer | `NOT_RUN` |
| Atomic ABI、foreign lifetime、graph与budget整合 | `NOT_RUN`，属于待实现接口 |
| Inkling R3、KV/conv、DSpark continuation及Java/Pi质量 | `NOT_RUN` |
| 4090微基准、完整请求、长上下文与资源净收益 | `NOT_RUN` |
| CuTe Rust preview的SM89路线 | 当前源码明确不支持，任务 `DEFERRED` |
| Lean SM89证明资格实验 | 可规划；需要目标构建和运行证据，不因#1857“尚未合入”而阻塞 |

从“值得研究”进入“候选可启用”，至少需要：同pin可复现产物、明确ABI及资源所有权、真实4090执行证据、冻结阈值的算子/模型正确性、状态恢复资格、完整预算与端到端净收益。所有输出仍使用本包的证据分类和状态枚举；安全证明、CPU编译、作者跑分各自保留原始含义。

## 12. 固定来源入口

正文中的CR为CUDA Rust源码/官方兼容资料，PF为证明子系统/原文。除带明确历史run/commit的CI与官方发布文档外，源码链接均固定到本次main SHA；不以floating main作为复现输入。

[CR01]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/README.md#L8-L49
[CR02]: https://github.com/NVIDIA/cuda-rust/commit/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b
[CR03]: https://github.com/NVIDIA/cuda-rust/pull/1857
[CR04]: https://api.github.com/repos/NVIDIA/cuda-rust/releases?per_page=100
[CR05]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/rust-toolchain.toml
[CR06]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/rust-toolchain.toml
[CR07]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/rust-toolchain.toml
[CR08]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/README.md#L84-L137
[CR09]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/cuda-oxide-book/getting-started/installation.md
[CR10]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-bindings/build.rs#L21-L25
[CR11]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-bindings/src/dyn_load.rs#L134-L153
[CR12]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-ir/src/requirements.rs#L104-L163
[CR13]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-ir/src/capabilities.rs#L81-L118
[CR14]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-book/reference/compatibility.md#L7-L100
[CR15]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-oxide-mlir-export/src/profile.rs#L128-L143
[CR16]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-target-spec/src/lib.rs#L348-L352
[CR17]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-oxide-codegen/src/target/select.rs#L197-L235
[CR18]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-device/src/wmma.rs
[CR19]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-device/src/generated/async_copy.rs#L12-L51
[CR20]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/cuda-oxide-book/gpu-programming/launching-kernels.md#L470-L528
[CR21]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/allocation.rs
[CR22]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/runtime.rs
[CR23]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-artifact-finalizer/README.md#L3-L17
[CR24]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/rustc-codegen-cuda/examples/cpp_consumes_rust_device/README.md#L3-L89
[CR25]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-book/guide/interoperability.md#L225-L279
[CR26]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-kernels/README.md
[CR27]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-kernels/src/experimental/gemm_variants.rs#L6-L65
[CR28]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/examples-compile.yml#L352-L430
[CR29]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/unit-tests.yml#L301-L332
[CR30]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/cutile-rs.yml#L357-L409
[CR31]: https://docs.nvidia.com/deploy/cuda-compatibility/latest/minor-version-compatibility.html
[CR32]: https://docs.nvidia.com/cuda/archive/13.2.0/cuda-toolkit-release-notes/index.html
[CR33]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/README.md#L18-L27
[PF01]: https://nihalpasham.github.io/posts/provably-safe-gpu-kernels/?v=3
[PF02]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/oxide-proofs-preview/CudaOxide/Contracts/Program.lean#L19-L145
[PF03]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/oxide-proofs-preview/CudaOxide/Contracts/ControlFlow.lean#L95-L150
[PF04]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/lean-exporter/src/runner.rs
[PF05]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/lean-exporter/src/codegen.rs#L414-L545
[PF06]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-oxide-codegen/src/prep.rs#L101-L105
[PF07]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/lean-exporter/src/translate/program.rs
[PF08]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-macros/src/verify.rs#L418-L566
[PF09]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/lean-exporter/tests/export.rs
[PF10]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/examples/safe_gemm_sol_final/src/kernels.rs
[PF11]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/examples/safe_gemm_sol_final/src/main.rs
[PF12]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/examples/safe_vecadd/src/main.rs#L19-L107
[PF13]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cargo-oxide/src/commands/lean_export.rs
[PF14]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/oxide-proofs-preview/lean-toolchain

[CI01]: https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/examples-compile.yml#L118-L129
