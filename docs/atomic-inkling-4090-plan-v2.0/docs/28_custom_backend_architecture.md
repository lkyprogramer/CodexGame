# 28 · 自定义 kernel 与 backend 的接入架构

> **v2来源更新：** 本篇141文件/工具链与CI详细审计基于历史`5e5c77…`；当前main为`f35d6ccc2e03a54e73e3796f415f11313e439d50`，新增#1866写覆盖修复与1D限制，详见[40](40_upstream_refresh.md)。未来K00冻结新pin并重做相关资格；原证据保持原SHA，不冒充新运行结果。

## 1. 决策、状态与适用范围

**首选是保留 Atomic / ggml-cuda 的宿主所有权，离线生成少量针对 SM89 的设备 kernel，再沿现有算子分派局部接入。** CUDA C++ 参数搜索为起点；cuda-oxide SIMT 是可选设备前端；cutile-rs 是需要独立工具链与预热资格的另一分支。独立 ggml backend 为 K07，初始 `DEFERRED`，不是 K00–K06 或 T12 的默认依赖。

本篇是 **NEW 设计合同**，不是已有 adapter、C ABI、注册表或 GPU 成功报告。所有本机编译、4090 加载、运行、数值、状态、容量和收益验证均为 `NOT_RUN`。下文逻辑接口名只定义消费者边界；最终字段、类型、状态枚举和机器校验规则以本包合并后的 schema 为准，不能据此假定上游已经实现函数或命令。

固定审计基线：

| 对象 | 固定版本与解释 |
|---|---|
| Atomic Engine | `fb69fff02101b048a0a165a3b502712dd2ca978f`；现有 GGUF、模型、预算、状态、CUDA 与服务继续作为基础 |
| NVIDIA cuda-rust | 当前研究pin S45 `f35d6ccc2e03a54e73e3796f415f11313e439d50`；详细历史审计S22及新delta见40，不等同于生产资格 |
| 模型 / 运行合同 | 正式 Mini、固定 R3、24 physical layer / 48 visit 的真实映射、per-loop KV/conv、Vision Off、single active generation=1 |
| 目标机器 | 原 [04](04_hardware_memory.md) 的 RTX 4090 / host 配置；实际 OS、驱动、工具链、资源和独占条件由 T00 现场确认 |

项目成熟度、固定源码、工具链、CI 的实跑/跳过边界及形式验证范围见 [27 · cuda-rust 源码审计](27_cuda_rust_source_audit.md)。本篇消费该审计，不把 Rust 类型安全、证明通过、编译成功或第三方 GPU CI 任一项当作完整 Inkling 资格。[R01]

## 2. 三条路线分别准入

| 路线 | 构建与运行方式 | 本轮取舍 | 独立资格边界 |
|---|---|---|---|
| 现有 CUDA C++ / 局部模板 | 在 Atomic 原工具链中产生 kernel，保留原分派 | 首个同语义对照与参数搜索起点 | 原 T02/T05/T07，加本次被触及的 ABI、shape、资源与生命周期测试 |
| cuda-oxide 原生 SIMT | 隔离构建生成显式 `sm_89` PTX / cubin；C++ 用既有 context / stream 装载与 launch | **AOT cubin 优先**，先一个热点 / 一个受限 shape 集合 | 源、依赖、编译产物、参数 ABI、证明属性、动态检查与实际运行逐项绑定 |
| cutile-rs Tile | 单独锁定 Rust / Tile IR / tileiras；按实际工具链输出和加载路径接入 | 可选；必须 JIT 的路径先在隔离候选 worker 预热，再准入、加载并允许 capture | SM89 target、每个 op/dtype/属性、emitted Tile IR 版本、驱动入口及具体 kernel 模板分别检查 |
| cute-rs-preview | 当前 exporter 只允许若干 Blackwell target，明确拒绝 SM89 | **本轮排除**，不能改架构字符串绕过 | 上游未来改变支持时重审；不借用 CUDA C++ / CuTeDSL 的能力结论 |
| 独立 ggml backend | 新的 op/buffer/graph 执行集成 | K07 初始 `DEFERRED` | 仅按第 10 节 P0–P3 开启，不因引入 Rust 自动启动 |

cuda-oxide 已有设备产物层和 cubin materialization；`--materialize-cubin` 要求显式目标架构。这个事实支持研究局部模块加载，但未证明具体 Inkling kernel ABI 或 4090 运行结果。[R02] Tile registry 接受 SM89 的 baseline，最低 emitted Tile IR 为 13.2；当前 FP8、NVFP4 / block-scaled MMA、cluster 与 PDL 又有更高架构要求，不能从 target 接受外推模板可用。[R03] CuTe Rust 的排除是当前固定源码结论。[R04]

离线 cubin 消除的是**该份产物的运行时 PTX JIT**，仍须检查目标架构、驱动功能、module load、参数 ABI 和资源。SIMT 路径保留实际 PTX 作审计输入；Tile 路径保留实际 Tile IR / bytecode、tileiras 与最终加载产物，不强求存在 PTX。若实际走 driver PTX-only JIT，另建执行身份，记录 driver、JIT 选项、缓存与实际加载产物，不能继承另一份 cubin 的资格。Tile 的运行时编译也须记录真实编译链，不能直接称为 PTX JIT。

Tile 分支不得在正式请求上生成新代码、下载依赖、无限 shape 特化或临时扩大缓存。预热失败只阻断相应 Tile 候选和 shape；已经合格的 C++ / AOT 路线仍按自己的资格运行。跨语言 device LTOIR 示例虽然真实存在，其审计中的已验证设备并非 SM89；一个独立 kernel 无须先承担该链接复杂度。[R05]

## 3. 架构边界与唯一所有权

~~~mermaid
flowchart TD
  A["隔离 lab：候选与构建"] --> B["产物 / 合同 / 动态资格"]
  B --> C["只读候选 registry"]
  D["Atomic 模型图与原事务"] --> E["ggml-cuda 局部分派"]
  C --> E
  E --> F["借用原 context / stream 执行"]
  F --> G["event、错误与 lease 检查"]
  G --> D
  H["原账本与 generation 管理"] --> E
  H --> G
~~~

图中的 registry、bridge 和 generation 扩展均为 NEW 逻辑职责，不要求建立三套新服务。K01/K04 优先把必要逻辑放入现有能力验证与小型 adapter；新增代码位置由选中的热点确定。

| 对象 / 决策 | 唯一 owner | 候选可做的事 | 必须拒绝的越界 |
|---|---|---|---|
| GGUF、模型结构、权重身份、physical alias | Atomic 原 loader / model | 消费已确认格式与范围的只读 view | 重新解释量化、私自重载模型、把共享物理层复制为 48 份 |
| per-loop KV、conv、controller、DSpark、RNG、事务 | Atomic 原 context / 协调器 | 读写合同明确授予的槽位和临时输出 | 创建第二套目标状态、合并 loop、提交 token/tool、改变接受/回滚算法 |
| CUDA device / context | 原 ggml-cuda backend | 借用指定的 device/context；由 backend 管理调用线程的 current context | 私建 context、释放借用 context、随意 device reset |
| stream / event | 原 CUDA backend | 在指定 stream 提交，登记生产与消费依赖 | 假设默认 stream 能补齐同步；私自改变 stream 拓扑 |
| device arena / pinned staging | 原 ledger / allocator | 先 reserve，再取得带边界和 lease 的 slice | 独立漏账 pool；擅自 cudaMalloc；把 pinned host bytes 记为 device bytes |
| module / function | backend 的候选 generation 管理职责（NEW） | 共享已加载的不可变 module，按 ticket / graph 保活 | 在途覆盖 kernel；有未完成 event 或图引用时 unload |
| graph / graph exec | 原 CUDA backend | 增加已资格固定 shape 与资源依赖 | 图仍引用地址时 evict / resize；每请求无界新建图 |
| qualification / fallback | 原 capability 层与审查后的 registry | 精确命中已通过范围；干净的未命中回原实现 | 删除 guard、静默换量化/预算/目标、把执行故障当普通未命中 |

Atomic 的普通 CUDA 路径与离散 budget 路径继续独立。一个新 kernel 不能使当前拒绝的 Inkling budget / DSpark / 长上下文组合自动合法；扩展仍由 T09 等原任务资格化。[06](06_atomic_cuda_port.md) 所列 CLI、loader、context、executor 和类型 guard 全部保留。局部替换先使用原目标 profile 的合法路径。[A03]

## 4. 构建身份与 ABI：必须查产物，不能猜签名

### 4.1 固定的是完整执行链

每个候选绑定 source / template / 参数、完整依赖、compiler/macro/LLVM 或 Tile lowering revision、精确 flags、CUDA 工具、目标 SM、实际中间表示与加载产物、entry symbol、资源报告、合同与资格证据。SIMT 绑定实际 PTX ISA、PTX/cubin；Tile 绑定实际 Tile IR / bytecode 版本、tileiras 与 cubin 等对应产物，不编造缺失的 PTX 或 hash。记录实际 argv、退出码和原始输出；命令模板本身不构成执行事实。

cuda-oxide、Tile 与现有 Atomic C++ 可以使用不同的隔离构建环境。引入新前端不授权升级生产驱动、改全仓 Toolkit 或替换 Atomic 的宿主运行库。新产物必须与 T00 冻结的实际运行环境做 load / launch probe。工具链与驱动矩阵见 [30](30_sm89_kernel_program.md)；已知 CUDA 通用兼容规则不能填补尚未实跑的具体组合。

若候选声明 verified 模式，`check_proof_binding` 必须核对实际被验证 IR、被发射 IR、产物与 launch 前提。证明属性、假设、未证明链路及可信组件分别保存；0 个义务、unknown、超时或不支持不能伪装为所需属性已证。普通 C++ 动态资格与 scoped proof 路线身份分开；证明失败后不能保留 verified 标签悄悄降级。详细规则以 [27](27_cuda_rust_source_audit.md)、[29](29_automated_kernel_optimization.md) 为准。

### 4.2 设备 entry ABI 与宿主 C ABI 是两张合同

源码中的 Rust 参数不能直接抄成 C++ launch 参数。当前宏会按 scalar、slice pointer + length、row width、by-value aggregate / closure 等不同规则编组；泛型 entry 的命名还可能由实例化产生。必须检查实际生成 entry 与参数布局，不能猜一个稳定符号或把 `repr(C)` 当作全部证据。[R06]

K01/K04 至少冻结：

1. **设备入口**：实际 symbol、参数顺序、宽度、对齐、by-value 块 size / offset、pointer width、显式 length / stride 单位、目标架构与 module hash；有 PTX 时核对 `.target` / `.version`，Tile 则绑定实际 bytecode / tileiras / 加载产物合同。
2. **宿主 descriptor**：版本、总大小、固定宽度 scalar、opaque device address、allocation bounds / offset、shape / stride / dtype / layout 身份；宿主 struct 与设备参数分别描述。
3. **launch**：grid、block、动态 shared、必要 opt-in、feature 集、shape 范围与前提；必须来自同一已审查模板和资源报告。
4. **错误通道**：参数错误、准入未命中、提交状态、异步错误、取消与资源回收结果分开。禁止异常或 panic 穿过 C 边界。
5. **边界校验**：每个长度与偏移的单位、乘加溢出、最大可达地址、空 tensor 语义、设备归属、alias 许可。不能从裸 pointer 推断真实 allocation 长度。

首选 AOT 路线中，C++ 直接加载设备模块，**无需 Rust 宿主 FFI**。只有 Tile 的实际加载路径或其他已证明必要的功能要求 Rust shim 时，才设计小型、版本化 C ABI。不得跨边界传 Rust `Vec` / `String` / reference / slice / trait object / closure，或把 Rust allocator 的销毁责任交给 C++ 猜测。此处不提供假定可用的函数签名。

### 4.3 若使用 Rust 宿主 shim，借用不能变接管

固定源码有 `Context::borrow_raw / borrow_with_owner`、`Stream::borrow_raw / borrow_with_owner`，以及 `RawDeviceBuffer::borrowed_from_raw_parts`。这些为外部资源接入提供工具；创建时的有效性、context 与异步寿命、外部并发访问仍由 unsafe 调用者保证。[R07]

`DeviceBuffer::from_raw_parts` 的接管 / 释放语义不能代替借用 Atomic 地址。`DeviceAllocation` 的 unsafe 合同也不会替 C++ 证明 alias 互斥。`AllocationLease::retain_until_complete` 能保活到 event 完成，但不是 Atomic 预算账本；bridge 必须把它与原 reservation / epoch / allocation generation 连起来。[R08]

## 5. 精确 consumer 边界（NEW）

以下与 [29](29_automated_kernel_optimization.md) 共用逻辑合同。机器字段规范由统一 schema 固定；这里只定义输入、消费方和副作用，不能据表创建未经审查的生产 API。

| 接口 / 调用者→消费者 | 输入 | 返回 / 副作用边界 |
|---|---|---|
| `propose_candidates` / AI→lab policy validator | 冻结 SearchPlan、去敏 trace summary、已审查模板、停止记录 | CandidateSpec；提出假设与参数，无执行权限，不修改 oracle / 阈值 / holdout |
| `compile_candidate` / lab→隔离 builder | 一个规范化 CandidateSpec、ToolchainLock、依赖 closure | BuildRecord：actual argv、exit、产物、ABI、资源报告 hash；不接触生产 GPU context |
| `check_proof_binding` / lab→verifier/checker | BuildRecord、实际 verified/emitted IR、KernelContract、ProofPolicy | ProofBinding：逐属性结果、义务计数、假设、TCB、未证明链路；缺项显式保留 |
| `resolve_kernel` / ggml-cuda 分派→只读 registry | 完整 CapabilityKey、op / tensor descriptor、artifact / contract revision | SelectedKernel 或带原因 NoMatch；只读、未提交；合法 NoMatch 才回原分派 |
| `prepare_invocation` / ggml-cuda→bridge | SelectedKernel、BorrowedExecution、views；MoE 另加 RouteIndexContract | PreparedInvocation：精确 ABI/launch、module/arena/input/output lease 与依赖 event；失败给出零提交事实及预留回收状态 |
| `enqueue_invocation` / bridge→原 stream | PreparedInvocation、预期 epoch / address generation | SubmissionTicket：request/epoch/sequence、stream/event、全部 lease，状态为 SUBMITTED；单次提交，重复拒绝 |
| `resolve_ticket` / 原 backend→bridge | ticket 与当前 epoch | NOT_READY / READY / FAULT；READY 需 event 完成及错误检查；FAULT 保留错误并 poison，不提交 token |
| `consume_ready_output` / 原 Atomic 协调器 | READY ticket、有效事务、模型/数值/stop 条件 | 在原模型流程消费输出；token/tool 仍由原 commit 边界处理 |
| `retire_resources` / 原 backend 回收器 | ticket/graph/module lease、末次使用 event | 待回收或已回收；未知完成不释放，Drop / timeout 不等于完成 |
| `qualify_candidate` / 确定性审查器→gate/registry writer | 冻结候选、raw run、proof/动态证据、原 G2–G6、comparison contract | 审查资格与可用范围；AI 生成器不能写 PASS；不自动执行 G7 |

三类关键记录至少表达下列语义，不在这里另建与 schema 竞争的字段清单：

- **KernelContract**：spec、op、dtype/quant/layout、shape/stride/alignment 范围、读写区域与 alias、E/N 分类、资源/feature 要求、参数 ABI、module hash。
- **BorrowedExecution**：backend/context/device 身份、指定 stream、request/epoch、allocation generation、graph mode、arena bounds / lease、输入 event。
- **SubmissionTicket**：唯一提交身份、实际资源集合、提交与完成事实、错误和回收状态。不是“结果已正确”或“token 已可提交”的代称。

`resolve_kernel` 的未命中、任务状态和错误 reason code 是不同层次，不混入同一枚举。任何适配器必须让调用者判断“是否提交过”“是否可能污染状态”“哪些资源仍在途”，不能只返回一个布尔值。

## 6. 异步寿命、alias 与 graph

### 6.1 地址有效期覆盖最后一次设备使用

宿主 borrow 结束、函数返回或取消请求都不代表 GPU 已完成。每个输入、输出、workspace、pinned buffer、module 与 graph 依赖从 prepare 起有可追踪 lease；提交后由 ticket 持有，直到**末次使用** event 完成且所有 graph 引用退役才归还。

只读 physical weight view 可共享；写入 KV / conv / controller / output / scratch 必须有独占写 lease，或证明写入范围不相交。多 view 指向同一 allocation 时按真实 byte 区间检查，不以不同宿主对象名视为不 alias。in-place 只有在 KernelContract 明确支持且同步/读写次序已验证时才允许。

参数打包区的寿命遵守具体 launch API；被 device 访问的 descriptor、间接参数、pinned DMA source 与普通按值参数不可混为一谈。需要跨 capture/replay 存活的对象由 graph lease 保活，不能仅保活一次宿主 launch 调用。[N01,N02]

### 6.2 先保持原 stream

首版在 Atomic 原 stream 执行。输入 event 和前序 kernel 建立明确依赖；若以后增加 copy stream，必须有 producer event → consumer wait，以及消费者末次使用 event。不能依赖默认 stream 的偶然同步。

普通 `cp.async` 的 group wait 与 block/warp 可见性按该指令合同处理；它不是所有跨线程读写的通用 fence。由别的线程消费 shared staging 时，仍须相应同步。共享内存双缓冲只能在消费者结束后复用，不能让宿主 event 补救一个 kernel 内部 race。[R09]

单请求可有受控的内部并行，但仍维持 single active generation=1。bridge 不因 Rust wrapper 可构造就默认允许跨线程无约束调用；调用线程 current context 的进入/恢复仍由原 backend 管理。Runtime / Driver 的句柄互操作不自动传递所有权。[N02]

### 6.3 图与模块形成同一失效域

capture 前完成 module load、函数解析、首次 JIT/预热和资源 reserve。graph key 保留 [08](08_sm89_kernels.md) 的 model epoch、B、序列数、capacity、KV/loop/mask/graph/budget 身份，再绑定 kernel artifact/module hash、contract revision、ABI、shape bucket、workspace layout 与 allocation/address generation。

以下变化必须失效或重建受影响图：kernel/flags/工具链产物变化，模型或 packed layout reload，arena resize / budget shrink，KV codec / loop / verify width 变化，地址 generation 改变。若仍有在途 ticket 或 graph replay，旧 module 和地址继续持 lease；不得原地覆盖代码或回收 bank。

图缓存数量和 module 常驻量纳入 device/host 账本。先支持 B1 与 T06 已资格的少量固定 B；动态 position / length 只有在已经审查的设备参数路径中更新。首次 capture、graph update、预热、热图执行分开记录；冷启动或新 shape 请求实际承担的成本要计入相应 E2E。[N03]

### 6.4 取消与 epoch

取消停止未提交工作和对外 commit；已提交工作保持 lease，等待 drain 或延期回收。旧 epoch 的迟到完成只可用于完成退役，不可复活请求、写入新 arena 或提交 token/tool。超时是等待结果未知，不是 GPU 已停止；不得因超时把地址分配给下一请求。

首版 generation 发布采用排空后切换。若将来需要热切换，必须另证旧请求持旧 generation、新请求持新 generation，且两代峰值都计费；本篇不以“双版本理论可行”自动允许同时驻留。

## 7. 错误必须在 fallback 之前分类

CUDA API 可能报告此前异步错误；一个 launch / module API 返回错误不充分证明“这次未执行、上下文仍干净”。[N01,N02] 处理遵循 Atomic 已有 sticky 故障与同预算恢复原则。[05](05_architecture.md)、[06](06_atomic_cuda_port.md)、[A04]

| 场景 | 必须保留的事实 | 恢复 / 拒绝 |
|---|---|---|
| 未命中 shape、dtype、layout、alignment 或 alias | 无候选提交；明确不支持的前提 | 请求本身合法时用原已资格实现；不能 reinterpret 或改目标 |
| registry / contract / artifact / epoch 不一致 | 不加载候选；缺失或失配证据 | 保留旧合格 generation，或显式 UNQUALIFIED；不下载新产物救场 |
| prepare 预算不足或 module 不可用 | 是否零提交、reservation 回收结果、context 健康状态 | 只有证明无副作用、无早前 fault、同预算合法时才 fallback |
| 编译、必要证明、sanitizer 或数值失败 | 原始日志、失败案例、候选身份 | 隔离候选；不进入 registry；修复后重新资格 |
| enqueue 返回错误 / event 报错 | 原始 CUDA error、最后可靠提交边界、所有在途 lease | 状态不确定则 sticky poison，不能当普通 NoMatch |
| 提交后非法访问、执行超时、状态或数值异常 | completion 未验证；停止 logits/token/tool commit | drain 并退役旧 context；device context 失效则重建隔离 worker |
| 取消 / 旧 epoch 完成 | 唯一终态、最后提交点、待回收资源 | 完成退役；不执行已完成的工具副作用，不复活旧 ticket |

恢复只能在**同一有效预算与已资格 profile**内，从 committed prefix 重建所需状态。不可在可能已部分写坏 KV/conv 的旧 context 上立刻跑原 kernel 掩盖故障；不可移除 budget 后重载普通 CUDA 来报告恢复成功。

首个候选尽可能把结果写入受控 scratch，经过完成/错误检查后由原流程消费，以缩小污染范围。但 scratch 仍占预算，且后续操作可能已经消费数据；它不能豁免状态一致性、event 和 fault 传播测试。未知完成时不自行释放地址，不在共享服务上调用 device reset。

## 8. 现有真实触点与 NEW 代码边界

下表路径均来自固定 Atomic 提交。它说明应在哪里阅读和连接，不要求一次改完这些文件。新建 runtime 文件只有 K02 选中热点、K01 合同冻结后才确定；没有实现的路径一律标 NEW。

| 固定现有路径 | 接入职责 | 本轮不得夹带的变化 |
|---|---|---|
| [ggml/src/ggml-cuda/ggml-cuda.cu](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/ggml/src/ggml-cuda/ggml-cuda.cu) | 观察真实 op dispatch；最小候选选择与原分派边界 | 重写整套 CUDA 调度、隐式跨 backend copy |
| [ggml/src/ggml-cuda/CMakeLists.txt](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/ggml/src/ggml-cuda/CMakeLists.txt) | 固定 artifact / adapter 的显式构建依赖 | 自动更新 Rust main 或改变全仓工具链 |
| [src/models/inkling2-loop.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2-loop.cpp) | 对齐真实 visit/slot、controller 与算子边界 | 将三轮简化为同一 core 重复、共享 loop KV |
| [src/models/inkling2-dspark.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2-dspark.cpp) | 仅在 T06 涉及的 verify / feature 边界核对 | 以 kernel 优化修改接受算法、feature 列表或 Markov 状态 |
| [src/llama-context.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-context.cpp)、[src/llama-context-atomic.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-context-atomic.cpp) | context / 原事务 / 能力边界 | 把 wrapper 的 READY 当成对外 commit |
| [src/llama-memory-budget.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-memory-budget.cpp)、[src/llama-memory-contract.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-memory-contract.cpp) | 既有 host/device 预算与 reserve/retire；新增资源并账 | 第二套漏账 allocator、降低保留量 |
| [src/llama-expert-executor.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-expert-executor.cpp)、[src/llama-expert-store.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-expert-store.cpp) | 专家状态、错误和权重 lease；实际类型与驻留 | 用局部 kernel 越过类型 / streaming 准入 |
| [common/atomic-budget.cpp](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/common/atomic-budget.cpp) | 核对当前 CLI / 模型 / ctx / batch 限制 | 为性能测试全局放宽 guard |

NEW 的 adapter、contract、registry、artifact staging 和证据文件由 [31 · kernel 任务](31_kernel_tasks.md) 指定任务创建；本篇不提前承诺目录或 C++ 类型。原 [08](08_sm89_kernels.md) 中拟议的 `inkling-control.cu/.cuh`、`inkling-conv.cu/.cuh`、`inkling-relative-attn.cu/.cuh` 仍为 NEW 候选名，只在对应热点成立时创建。

## 9. 局部候选何时允许登记

K00–K06 的依赖和任务状态以 [31](31_kernel_tasks.md) 及机器任务图为准。运行步骤、故障注入与 AX 测试见 [32 · kernel 验证手册](32_kernel_validation_runbook.md)。至少具备以下事实后才能请求审查登记：

1. 已有正式 Mini 固定 R3 的合法原 CUDA baseline；候选只改变冻结 comparison contract 允许的因素。
2. 实际 SM89 产物、ABI、合法 shape / alias / resource 范围可追溯，载入原 context/stream，不新增不可见所有权。
3. 必要 scoped proof 与动态检查各自有真实结果；完整 per-loop 状态、数值、取消/拒绝/续接、预算和 graph 生命周期通过对应门。
4. 原 G3/G4/G5/G6 的适用证据齐全；冷/热、fallback 命中率、全部真实请求、资源峰值均进入结论，不能只报 microbenchmark。
5. registry 只发布已确认的窄范围；未确认 shape 明确回退或拒绝；候选 generation 可排空退役。生产切换仍需原 G7。

自动搜索和编译工具没有修改 oracle、停止记录、资格 registry 或生产流量的权限。没有执行条件只阻断受影响任务，不连带否定另一条已资格路线；本包的文档静态检查也不能代替以上 GPU 门。

## 10. 独立 backend：K07 的 P0–P3 门槛

### 10.1 重新立项所需证据

K07 初始 `DEFERRED`。只有以下条件同时成立才记录新 DECISION 并解除延期：局部候选链路已可维护；真实请求中相邻 op 的分派/同步/布局成本仍足以跨越原 G3；已尝试或明确设计现有 backend 内的最小 fusion / partition，并指出其真实接口限制；独立 backend 的维护范围、未支持 op 回退和跨 backend copy 成本已可审查。换一种语言或 microbenchmark 更快不能替代这些证据。

范围必须覆盖 op support、buffer type、view / alias、tensor get/set/copy、同步与 event、graph compute、scheduler partition/fallback、allocator/双预算、module/graph 生命周期、sticky fault 与 context 退役、正式 Mini 全 op 矩阵。它仍然是 Atomic 的执行后端，不重写 GGUF、tokenizer、循环目标、server、投机事务或工具协议。

### 10.2 四个有界阶段

| 阶段 | 进入条件 | 交付与检查 | 放行 / 失败出口 |
|---|---|---|---|
| **P0：合同与支持矩阵** | K07 立项证据和维护预算已审查 | 每个 op×dtype×shape 的支持/拒绝、buffer/view/alias、copy/event、原 context 归属；完整 fallback 与跨边界复制图 | 不支持组合能加载前或派发前明确拒绝；所有权或接口仍未知则不进入 P1 |
| **P1：一个固定子图** | P0 合同冻结 | 一个有界子图、一个固定 shape；同 context、原账本、完整 ABI/lease、错误注入和回原分派成本 | 动态正确性、资源寿命和可恢复边界通过；没有“单子图通过即全模型支持” |
| **P2：正式 Mini 串行 forward** | P1 通过，所需 op 覆盖可交付 | 固定 R3、真实 48 visit、per-loop KV/conv/controller；取消、续接、长短边界；先无新 spec / quant | 完整状态与数值资格；任一语义失败先停，不能靠新算法绕过 |
| **P3：完整产品比较** | P2 通过，完整 profile / 资源已冻结 | 对照**最佳已资格局部 backend 候选**，测 E2E、容量、质量、p95、冷/热与 soak；所有跨 backend copy 计时计费 | 通过原门才申请集成；无净益则 NO_BENEFIT 并保留局部路线 |

每阶段正确性故障先停止。性能问题最多两轮有 profiler 证据的修正；达到停止规则即结案，不因已投入重构扩大范围或放宽阈值。K07 未启用或未成功，不阻止不依赖它的 K00–K06 / T12 主线。

## 11. 固定源码与官方合同引用

以下源在 2026-11-25 审计。Atomic 路径还可通过 `manifests/source-audit.json` 复核 blob；cuda-rust 全量审计与 CI 限定见 [27](27_cuda_rust_source_audit.md)。网页说明为机制来源，不是本机结果。

- **R01**：[cuda-rust README](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/README.md#L8-L49)，项目/前端范围与 preview 语境。
- **R02**：[materialize](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cargo-oxide/src/commands/materialize.rs#L182-L216)、[artifact finalizer](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-artifact-finalizer/README.md#L3-L17)，显式目标和设备产物。
- **R03**：[Tile requirements registry](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-ir/src/requirements.rs#L104-L163)，按操作/类型/版本/架构分别约束。
- **R04**：[CuTe exporter profile](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-oxide-mlir-export/src/profile.rs#L128-L143)、[support matrix](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/cuda-oxide-book/cute/support-matrix.md#L23-L37)。
- **R05**：[C++ 消费 Rust device 示例](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/rustc-codegen-cuda/examples/cpp_consumes_rust_device/README.md#L3-L89)、[device FFI 示例](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/rustc-codegen-cuda/examples/device_ffi_test/README.md#L1-L29)。
- **R06**：[generated launcher 编组](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-macros/src/cuda_module/launchers.rs#L1096-L1147)、[closure launch](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-macros/src/launch.rs#L23-L29)、[launch ABI 文档](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/cuda-oxide-book/gpu-programming/launching-kernels.md#L470-L528)。
- **R07**：[context 借用](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/runtime.rs#L193-L251)、[stream 借用](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/runtime.rs#L783-L837)。
- **R08**：[allocation 合同](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/allocation.rs#L14-L25)、[borrowed memory](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/allocation.rs#L199-L224)、[completion lease](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-core/src/allocation.rs#L332-L360)。
- **R09**：[普通 async copy 合同](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-device/src/generated/async_copy.rs#L12-L51)。
- **A03**：[Atomic budget 验证/加载](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/common/atomic-budget.cpp)、[loader](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-model.cpp)。
- **A04**：[Atomic expert executor](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-expert-executor.cpp)。
- **N01**：[CUDA Driver API — Module Management](https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__MODULE.html)，module 与此前异步错误；参数/launch 需同时核对所用版本的 Driver API。
- **N02**：[CUDA Runtime / Driver API interoperability](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__DRIVER.html)，current context 与句柄互操作。
- **N03**：[CUDA Graphs](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html)，capture、更新与资源管理。
