# 30 · SM89 kernel 候选与执行程序

> **v2来源更新：** 本篇141文件/工具链与CI详细审计基于历史`5e5c77…`；当前main为`f35d6ccc2e03a54e73e3796f415f11313e439d50`，新增#1866写覆盖修复与1D限制，详见[40](40_upstream_refresh.md)。未来K00冻结新pin并重做相关资格；原证据保持原SHA，不冒充新运行结果。

## 1. 目标与当前状态

**用真实 Inkling 请求的关键路径选择一个热点，在现有 ggml-cuda 内做有界候选搜索，再以完整模型状态、资源和 E2E 证据决定是否启用。** 不预先承诺 norm、GEMV、MoE 或 attention 哪一项最值钱；不以 Rust、Tensor Core、occupancy 或局部吞吐替代产品收益。

本篇是 NEW 工程程序。当前未编译候选、未安装依赖、未运行 GPU / sanitizer / profiler；本机前端 probe、每个 kernel、所有性能收益与新增运行测试均为 `NOT_RUN`。缺少前置条件时只将受影响任务标 `BLOCKED`；K07 独立 backend 初始 `DEFERRED`。文中候选域和成本上限是待 K02 冻结的计划，不是测量结果或自动执行授权。

沿用 Atomic `fb69fff02101b048a0a165a3b502712dd2ca978f`、正式 Mini、固定 R3、24 physical layer / 48 execution visit、真实 logical slot 映射、per-loop KV/conv、Vision Off、single active generation=1。普通 CUDA 与离散预算模式保留各自准入，不删除 [06](06_atomic_cuda_port.md) 的 guard。T02/T05 的原 CUDA baseline 必须先可用。

阅读关系：源码能力以 [27](27_cuda_rust_source_audit.md) 为准；所有权、ABI 和故障边界以 [28](28_custom_backend_architecture.md) 为准；生成、证明绑定、成本与统计流程见 [29](29_automated_kernel_optimization.md)；任务与依赖见 [31](31_kernel_tasks.md)，实际验证和 AX 编号见 [32](32_kernel_validation_runbook.md)。本篇不另造一套机器字段或状态枚举。

## 2. 硬件资源：架构上限与实测分开

### 2.1 SM89 资源表

下表是 NVIDIA Ada 指南中的架构资源，**不是用户机器的可用预算，也不是建议占满的配置**。T00 保存实际 device attributes；K00/K03 保存编译器资源报告；K05 再验证实际 launch / occupancy / 峰值。[N01]

| 项目 | SM89 / Ada 官方边界 | 候选必须做的检查 |
|---|---|---|
| 目标 | Compute Capability 8.9；显式编译 SM89 | 核对实际加载产物 target、函数与设备；有 PTX 时查 `.target`，Tile 查对应 IR/bytecode/assembler 产物；不只检查构建字符串 |
| resident warp | 每 SM 最多 48 warp | 与 block 几何、寄存器和 shared 共同计算；不是“warp 越多越快” |
| register file | 每 SM 64K 个 32-bit register | 保存每线程/每 block 用量、分配粒度、spill/stack/local memory；源代码估计不能代替编译结果 |
| resident block | 每 SM 最多 24 block | 同时受 warp、寄存器、shared 和实现限制；小 block 不自动达到上限 |
| shared memory | 每 SM 100 KiB，每 block 最多 99 KiB | 静态 + 动态 shared 按实际函数/设备上限检查；包括 staging、padding、barrier 与临时归约 |
| dynamic shared opt-in | 单 block 总 shared 超过 48 KiB 时，超额部分须采用动态分配并显式 opt-in | 由原 backend 在准入时设置并检查结果；不能仅把 launch bytes 写大 |
| L2、SM 数、可用显存、时钟、PCIe | 本机属性与运行状态 | T00 查询；不把完整 AD102 的规格当成 RTX 4090 的实测配置 |
| 全局工作集 | 原 24 GB 目标显存与 host 64 GB 目标机器 | 实际可用量、保留量、峰值由原账本和测量确认；kernel 资源表不扩大模型预算 |

寄存器/shared 约束用于剔除不可能启动的候选；能启动仍可能因 spill、bank conflict、低有效带宽或额外重排变慢。occupancy 只是诊断变量，最终对照完整请求耗时。shared memory 的硬件资源用量与 global arena 的账本是不同层次，两者都要记录。

### 2.2 指令与机制表

| 操作 / 机制 | SM89 硬件边界 | 本程序处置 |
|---|---|---|
| 常规 global/shared 访问、warp shuffle/同步、block barrier | 可用；具体操作仍有参与线程、mask 和可见性合同 | 使用已审查模板；验证非整 warp / 尾块的参与条件 |
| 普通 `cp.async` | SM80 起的 global→shared 异步复制；4/8/16-byte 形式有对齐、范围和同步要求 | 可试有界 1–2 stage；逐一验证尾块、wait、跨线程可见性和复用；不是 TMA |
| `ldmatrix`、FP16/BF16 `mma.sync` | 有 SM89 可用形式；dtype、shape、layout 与指令修饰符须对应 | 只启用实际工具链和模板能表达的精确形式；lane 映射与数值另测 |
| `dp4a` | 可用于匹配的整数点积 | 先证明输入解码、scale、累加范围与原格式；不是通用量化格式转换器 |
| FP8 `.e4m3/.e5m2` MMA | Ada SM89 有相应硬件形式 | 前端能力另查；新 FP8 算术/量化不进入默认同目标搜索 |
| CUDA stream/event/Graph | 宿主执行设施，可用于 SM89 | 复用原 stream、图和 ledger；不是新前端自动获得的完整状态正确性 |
| TMA / `cp.async.bulk`、thread-block cluster / DSMEM、PDL | 相关机制从 SM90 起，普通 `cp.async` 不在此列 | **SM89 候选硬拒绝**；不改架构标签绕过 |
| `wgmma`、`tcgen05`、原生 block-scaled FP4 | 其他架构及特定 target 的功能，不是 SM89 ISA | **本轮排除**；软件解码 + 普通算术不能称为原生 NVFP4 Tensor Core |

机制来源为 NVIDIA PTX、Ada、advanced kernel 与 PDL 文档。[N01–N04] 工具链是否能表达、模板是否适用、4090 是否真实跑通仍是三件事。

## 3. 前端矩阵：不把 target 支持外推成算子支持

cuda-rust 固定为 `5e5c77b19a4b3204d6542bab2f0fde2a4eed824b`。下表中“源码支持”只描述审计事实，本地一律尚未资格。[R01–R06]

| 能力 | 现有 CUDA C++ | cuda-oxide 原生 SIMT | cutile-rs Tile | 本轮结论 |
|---|---|---|---|---|
| SM89 目标 | T00 核对原 Atomic 工具链，保留基线 | target 表接受 `sm_89`；可产 PTX/cubin | target registry 接受 SM89，baseline emitted Tile IR ≥13.2 | 三者分别 probe，不能互借成功结果 |
| warp/shared/普通 `cp.async` | 选原工具链支持的明确 primitive | 对应低层 API / 示例真实存在；unsafe 前提仍要满足 | 高层 tile lowering 的调度由编译器决定；不假定与 SIMT primitive 一一对应 | Tile 是否产生所需流水/同步与资源须看实际产物 |
| FP16/BF16 MMA | 检查具体 kernel 模板与编译形式 | `mma.sync.m16n8k16` 等有 SM80+ API 合同 | 可研究匹配的常规 tile 运算；每个 op/shape/属性独立检查 | 不把 dense 示例直接接到量化专家权重 |
| FP8 | SM89 的具体硬件形式可用，仍需工具链/格式资格 | 只按本候选实际 API、指令与编译结果判定；本程序不外推覆盖 | 当前 `f8E4M3FN/f8E5M2` registry 要求 SM90+ | 当前 Tile FP8 路线对 SM89 拒绝，即使硬件有 FP8 |
| NVFP4 / block-scaled MMA | SM89 不支持该原生硬件路线 | 不可凭 Rust 类型名获得指令 | 当前 FP4 / scaled MMA 要求 SM100+，相关 op 至少 Tile IR 13.3 | 排除；若软件解码则另建实现和数值合同 |
| non-TMA dense GEMM | 可从现有 ggml 路径定位 | 可用受审查的 SIMT/MMA/普通 copy 组合研究 | experimental GEMM 有关闭 TMA 的 MODE=2，不能默认其他 mode 合法 | MODE=2 只是源码候选，不是已资格 SM89 Inkling kernel |
| MoE / QKV 示例库 | 消费实际 ggml tensor / quant / route 合同 | 按实际热点实现受限候选 | 存在实验模板，但具体布局/类型/版本/资源均需适配 | 模板存在不等于正式 Mini、GGUF 或 per-loop 状态已覆盖 |
| CUDA Graph / foreign handles | 原 backend 是 owner | 宿主 wrapper 若用须借用原 context/stream | 可选 shim 同样遵守借用、预热、graph lease | 不创建第二套内存/stream/context 所有权 |
| cute-rs-preview | C++/CuTe 能力不转移给 Rust preview | 与原生 SIMT 是不同路径 | 与 Tile 是不同体系 | 当前 exporter 明确拒绝 SM89；整条 cute-rs 路线排除 |

Tile 的 requirements 是组合条件：SM89 baseline 为 13.2，不代表所有 op 都是 13.2。比如 `pack/unpack`、`gather_scatter_view`、`strided_view` 的版本门为 13.3；foreign tile-library call 为 13.5。FP8、FP4 与 cluster 还分别有设备门。候选 manifest 要逐项列出真实所需能力，不能写一个笼统的“支持 CUDA 13.2”。[R03]

### 3.1 构建、驱动与产物矩阵

| 路线 | 固定源码中的要求 / 行为 | 尚需确认的运行条件 |
|---|---|---|
| Atomic C++ baseline | 沿用原固定源及实际构建配置 | T00 冻结本机 compiler、Toolkit、driver、flags；不因新前端自动升级 |
| cuda-oxide SIMT | checkout pin Rust 1.99.1；CUDA 构建下限 13.0；LLVM 需 NVPTX，按实际 PTX / intrinsics 选择足够版本；相关组件/Clang 按源码要求 | README 列 LLVM21 等发现路径，但完整例集 CI 要 LLVM23；旧 ldmatrix/stmatrix gate 曾要求22。不能把“21+”当全部 kernel 保证；本机编译/运行 `NOT_RUN` |
| Tile / shared host workspace | checkout pin Rust 1.98.0；SM89 baseline emitted Tile IR 13.2；选中的 tileiras 必须接受实际输出版本 | assembler、各 op 版本、具体模板、加载路径与目标 driver 逐项 probe |
| shared driver loader | 查询成功时主要检查 runtime major 不低于 build major | 这个检查不证明全部 API、PTX、Tile 功能或具体设备组合可用 |
| CUDA 13.x 通用兼容 | NVIDIA minor compatibility 表给出 R580 分支下限 | 这是通用下限；新 PTX JIT / feature 可额外要求更新驱动，不能直接据此授 Tile SM89 资格 |
| CUDA 13.2 GA 完整对应 | 官方发布表列 Linux driver 595.45.04+ | 不等于要求所有 minor-compatible 应用必须升级；本机 OS/driver 未测，Tile13.2+SM89 的精确最低驱动组合仍 `UNKNOWN` |
| SIMT PTX / AOT cubin | SM89 表中 PTX floor 为 7.8，具体指令/lowering 会抬高；AOT cubin 避免该产物 runtime PTX JIT | 保存实际 `.version` / `.target`；PTX-only JIT 另锁 driver/选项/缓存，不能继承旧 cubin 的资格 |

上表来自固定 toolchain / build / target 源码与 NVIDIA 兼容说明。[R07–R10,N05,N06] 其中 `UNKNOWN` 描述证据缺失，不是新增任务状态。没有查到“RTX4090 + Tile13.2 + R580”专项实跑，不能自行补成支持矩阵的 PASS。Tile 的 artifact 合同按实际 Tile IR / bytecode、tileiras、最终 cubin / 加载产物保存，不强求 PTX；Tile JIT 与 driver PTX JIT 分别记录。

审计 HEAD 的常规 CI 是 CPU 检查/编译；HEAD 的 Tile GPU lane 被跳过。最近找到的实际 Tile GPU main run 使用 RTX PRO 6000 Blackwell，不能替代 RTX 4090 的本机资格。safe_* 编译与证明 lane 也不是完整 SM89 GPU 测试。精确 run/job/commit 与跳过情况见 [27](27_cuda_rust_source_audit.md)。

## 4. 先取得什么 trace，才允许生成候选

K02 只在已正确运行的完整 profile 中选择热点。每次最多一个 family，先写可证伪假设，再生成候选。trace 至少能够关联下列信息；这是 NEW 采集需求，实际 hook/字段由 K01 和机器 schema 固定：

| 观察维度 | 必须回答的问题 | 对候选的影响 |
|---|---|---|
| 完整请求时间线 | TTFT / decode / verify / 工具阶段的等待在哪里；CPU、H2D、kernel、sync 是否重叠 | 只以关键路径成本立项，不累加已重叠的 kernel 时间 |
| 实际 dispatch | ggml op、真实 symbol、调用次数、grid/block/shared、前端/产物身份 | 防止优化未被调用的模板；确认 CPU fallback 和未命中比例 |
| 模型索引 | physical layer、execution visit、logical cache slot、loop/pass、token/position | 判断权重复用、状态边界和能否融合；不能只凭层名聚合 |
| tensor / quant | 每个输入输出的真实 dtype/quant、shape、stride、alignment、alias、head/专家几何 | 推导合法向量、tile、尾块和 ABI；GGUF 文件名不能代替 tensor 类型 |
| MoE 分布 | 每个有效 token 的 route 数、每 expert token 数、空/热 expert、gather/scatter 与 padding 成本 | 判断 B1 GEMV、small-B 或 grouped prefill 哪条真实可用 |
| 内存与状态 | resident/streaming、bank 命中、live lease、workspace、module/graph/staging 与 host/device 峰值 | 防止用漏账驻留或展开权重换速度 |
| cache / graph / 冷热 | 首次 load/JIT/repack/capture、图命中/重建、稳态与恢复 | 明确哪种请求实际支付初始化成本 |
| 热点资源 | register/spill、访存/带宽、bank conflict、eligible warp/stall、实际 occupancy | 只指导少数候选参数；不能以单指标选胜者 |

先用 Nsight Systems 定位完整路径，再用 Nsight Compute 对少数选中 kernel 取必要 sections；正式性能计时不挂 profiler 或 sanitizer。保留 replay/cache/clock 设置，默认不改生产 power limit 或锁频；具体可用选项由 T00 确认。[N07,N08]

若热点关键路径占比为 `f`、局部加速为 `s`，理想请求耗时降幅上界是 `f × (1 − 1/s)`。`f` 需要去掉重叠，不是 kernel duration 的简单和。`f < 5%` 时，单独消除此热点也无法达到原单项 5% 中位数门槛；可记录容量或维护价值，但不能据此启动大范围后端工程。

## 5. Trace 驱动的候选清单

此表不是默认执行顺序。所有行初始 `NOT_RUN`，真实 trace 选中后才进入 K02；不存在热点或收益上界不足则不生成对应实现。E/N/Q 定义继承 [13](13_correctness_quality.md)：精确索引/存储可能属于 E，算术顺序、融合或 dtype 改变按 N 审查；模型/量化目标改变需单独合同，默认不进本搜索。

| 候选 family | 触发证据 / 首个受限变化 | 必须保持 | 主要退出条件 |
|---|---|---|---|
| **逐 token 分配、host 同步与 graph** | CPU timeline 出现关键空隙；先复用既有 workspace、固定地址、少量原 graph shape | 原 stream/event、地址 generation、预算、取消和原提交边界 | 空隙不在关键路径；capture/JIT/缓存峰值抵消收益；引入无界图或新 relay |
| **norm / residual / loop control** | 多个小 kernel 重复读写同一合法边界；先融合一段已审查表达式 | norm 位置、epsilon、累加 dtype、gain/forget/query/down 关系、prelude 与上一 pass bank 依赖 | 数值/路由改变超合同；register spill 或输出 scratch 抵消收益；跨越 loop 状态边界 |
| **convolution / state update** | 小 conv 或多次 state 搬运占关键路径；调 block/vector 或一个合法局部融合 | 每 loop 的卷积窗口、padding、token 顺序、in-place/rollback 语义 | 跨 loop 混 state；尾块覆盖旧窗口；拒绝/取消后无法完整恢复 |
| **无损 repack / gather / scatter** | 实际量化/布局导致重复解码、错位或低带宽；先改一个真实 tensor layout | 原 code/scale/符号/块映射与值，token/expert/slot 顺序；E 与后续算术 N 分开 | 格式并非实际热点；初始化/额外 RAM/VRAM 超预算；任何映射丢失/重复 |
| **B1 quant GEMV** | 正式 decode 的某种实际 gate/up/down 或 dense tensor 为带宽/解码热点 | 原量化解码、scale、累加范围和输出 dtype；一套类型一套资格 | 依赖整权重 FP16 展开；单 op 快但请求无净益；低比特误解释 |
| **B2/4/8 verify** | T06 已资格相应宽度，实际 verify 效率低 | candidate token 顺序、各位置目标状态、每个拒绝位置、bonus/correction 与 max_new 规则 | 没有 T06 前提；gather/padding 成本超过计算收益；状态只对全接受有效 |
| **grouped MoE prefill / small-B MoE** | route 分布和时间线表明可按 expert 聚合；先一个类型/几何 | RouteIndexContract、top-k/tie、weight 对槽位、聚合顺序、per-loop 真实 route | 动态索引假设未兑现；重排/校验/临时空间抵消收益；共享权重被误当共享路由 |
| **relative attention / FA** | 上下文增长后 mask/relative bias/attention 成为热点；先一个合法 KV dtype/shape | global/SWA 区分、position、mask、相对位置公式、实际 head 几何、全部 loop KV | 改窗口/codec/精度目标；长尾或全 mask 行错误；workspace/容量倒退 |
| **普通 cp.async 搬运流水** | 已选 GEMM/GEMV/局部搬运模板确有可重叠 global→shared 成本 | 1–2 stage、精确对齐/范围、completion wait、跨线程同步与 staging 复用 | 拷贝太小或无重叠；尾块/race；资源增加使驻留下降且 E2E 无益 |

### 5.1 Repack 的“精确”只限存储转换

若采用 [24](24_ghost_transfer_design.md) 的 IQ3_S 等候选，必须确认正式资产确含该 tensor 类型。保持解码值与索引的无损 repack 可按 E 测；后续 GEMV/MMA 的分组、乘加或累加顺序改变仍按 N 资格。host 原数据、packed 数据、临时 staging、device 地址、module/graph 引用的峰值同时计费；初始化和缓存未命中的成本不能只写在文档里、不进入请求模型。

不能把不同项目的 Q4 KV、NVFP4、IQ3 或 grouped weight 视为同一格式；也不能因为软件解码后使用 `dp4a` 就宣称 SM89 原生执行 FP4 MMA。实际 dispatch 与字节布局先于模板选择。

### 5.2 Norm / conv / control 的融合边界

先在原图中标出精确输入、输出、必要中间量和状态写入，再判断一个融合是否闭合。被 DSpark、下一 pass bank 或回滚逻辑引用的中间量不能因融合而消失。融合默认按 N；若声称 E，需证明实现保留原定义的算术/存储行为，并用对应 oracle 验证，不能仅以少数 greedy token 相同下结论。

conv 必须覆盖长度小于窗口、恰等于窗口、跨窗口/块边界、多 token verify 和滑窗覆盖。若 in-place 更新会覆盖撤销所需历史，先写已预留 scratch 或沿原 copy-on-write 合同处理；不能只回退 position。

### 5.3 MoE 动态索引必须有自己的合同

`RouteIndexContract` 为 NEW 逻辑记录，至少表达实际 expert 数 `E`、top-k、有效 token mask、每个 `(token, topk_slot)` 的 expert ID 范围、重复 expert 的语义、route weight 对槽位、group offsets 单调且末值等于真实 route 数、gather/scatter 无丢失/重复、padding 不参与输出。权重归一化与 top-k 次序按原公式，不能自行假定 route weights 和为 1。

宿主 shape 合法不能证明 device 动态索引合法。首版 producer 与 consumer 在同 stream，以已审计 producer range contract 或受保护的索引读取兑现前提；必要校验成本全计入 E2E。非法 ID、offset 或 scatter slot 必须阻止越界、设置 sticky fault，并禁止后续 logits/token/tool commit；不能静默 clamp 到合法范围。

仅证明“索引在给定范围时不越界”，不能证明 router 浮点算对、near-tie 选对 expert、tie-break 正确或聚合数学等价。每个 loop 的实际 route、weights、专家输出和最终聚合仍需冻结数值 oracle。改变 route 内容不能因地址安全而升级为 E。

### 5.4 Attention 先保语义，再选 tile

从固定模型资产和原图取得 head_dim、head 数/GQA、KV dtype/codec、global/SWA slot、有效长度、position 与 relative bias 的真实约束。不得套用另一模型的 256-dim head 或另一后端的自定义 KV codec。尾块、padding 和完全 masked 行必须按原实现定义处理；不能用随意填零使 softmax 产生可读但错误的输出。

K/V 所属 loop、页/窗口映射和最后已提交位置进入合同。只针对已资格 context 档位做优化；研究 128K 不能把当前未支持 budget/context 组合自动放行。任何扩大支持范围都沿原 T08/T09 的容量与状态门执行。

## 6. 合法 shape、尾部与 launch 准入

### 6.1 候选集合从实际能力行生成

初始 shape 集为空；K02 从 trace 与已资格 capability 填入具体值。decode 先 B1；B2/4/8 仅在 T06 对应行已资格时加入。prefill 使用当前 profile 的代表 ubatch 和真实尾块，不为了凑 Tensor Core tile 扩大原 batch/ubatch/context/verify 上限。

每个候选至少锁定这些轴：

| 轴 | 合法域来源 | 必须拒绝 / 显式 fallback 的情况 |
|---|---|---|
| dtype / quant / layout | 实际输入 tensor 与审计过的 decoder / packed revision | 未知量化、scale 块不匹配、误把文件总标签当 tensor 类型 |
| rank / dimension / stride | 原 ggml descriptor、已验证几何 | 不支持的非连续 stride、负/异常 stride 或未定义空 tensor；不能 reinterpret |
| B / sequence / context / position | 完整 capability 与原硬 guard | 未资格 B、序列数或位置范围；不能靠 kernel 可编译扩大模型能力 |
| alignment / vector width | 实际基地址、view offset、每行 stride 和尾部 | 仅首地址对齐但后续行不对齐；vector 跨出 view；按原路径或已资格 scalar variant 处理 |
| alias / in-place | allocation 身份与可达 byte 范围 | 写写/读写冲突、跨 loop state 共用、未知 overlap |
| index / offset arithmetic | 显式宽度、单位、overflow 语义 | 乘加溢出、地址超真实 allocation、signed/unsigned 隐式转换、错误 element/byte 单位 |
| launch / feature / resource | 实际 kernel ABI、SM89 device/function limits、编译资源报告 | 非法 block/grid/shared、opt-in 失败、需要 TMA/PDL/cluster 或其他禁用指令 |

准入检查必须在提交候选工作前完成。`prepare_invocation` 返回零提交及预留回收事实，才能允许同目标、同预算的原实现 fallback。已经提交后发现错误走 [28](28_custom_backend_architecture.md) 的 sticky 退役流程，不能伪装为不支持 shape。

### 6.2 尾块规则进入模板本身

- 对每个归约/矩阵维度保存：整 tile、最后一个有效元素、只剩一个元素、恰跨 tile、空/全 mask（若原 op 支持）的行为。fixture 必须使用真实格式约束，不能构造模型不接受的 tensor 后称覆盖。
- load、解码、MMA 输入、shared staging 和 store 的 mask 各自检查；masked output 不代表前面的 invalid load 安全。量化块需要完整读取时，必须证明读的是已分配/允许的块，不可越过 view 借用邻接内存。
- neutral padding 按具体算子定义。sum 可用的零，不自动适用于 max、softmax、norm 计数或 route aggregation；有效长度不能被 tile padding 放大。
- vector width 只有在所有被访问 lane 对齐且在界内时合法。尾部可由已审查 scalar/masked 路径处理，但该路径和分派成本同样测试、计时；不得假设编译器会自动生成安全尾部。
- 普通 `cp.async` 的 zero-fill / predication 只使用前端和指令明确支持的形式；source pointer、copy bytes、group completion 与 shared consumer 的合同分别验证。
- warp/block barrier 的参与集合不得因尾部提前 return 而不一致。最后 stage 使用结束后才能复用 shared；不能以“下一轮覆盖”代替可见性与竞争证明。

### 6.3 资源过滤先于 GPU 计时

由具体模板计算 staging、padding、归约、barrier 和输出临时区需求，再与静态/动态 shared、register/spill、stack/local memory、grid/block 上限核对。不能把 `stages × tile_bytes` 当成完整 shared 用量；实际编译结果是最终依据。

对每个 shape 计算当前 live state、scratch、packed weight、graph/module、pinned staging 与加载/恢复临时峰值，并向原 ledger 预留。双预算不因新前端分成两套；borrowed memory 不代表免费。shared-memory opt-in 只改变 kernel 的可用上限，不释放全局显存保留量。

资源不合法的候选不进入 GPU；合法但明显 spill 或低驻留的候选先记录原因，再决定是否值得占用有限测量名额。禁止为了让候选通过而缩小上下文、删除 draft/loop 状态、改量化、关闭保留量或扩展未授权池。

## 7. 有界搜索空间与预算

### 7.1 先参数，再扩大表达式

第一阶段使用 CUDA C++ 的既有实现或受审查模板，只改一个可归因参数；有证据后再增加同语义 cuda-oxide / Tile 实现。比较前端时分别锁定源、产物和完整 comparison contract，不要求不同前端生成相同 SASS，也不把不同算术模式当纯语言对照。

| 搜索维度 | 初始小域（提案） | 过滤条件 |
|---|---|---|
| block size | 64 / 128 / 256 threads | 真实 work 划分、warp 参与、barrier 与资源合法；不强制每个 op 都试三个 |
| vector width | 1 / 2 / 4 **elements** | dtype bytes、各行 alignment、decoder 块和尾部；与 cp.async 的 byte 形式分开 |
| tile shape | 已审查 catalog 中与真实 M/N/K 匹配的少量形状 | MMA/lane/layout、量化 group、padding 和 shared 计算通过；不凭模型名生成任意 tile |
| pipeline stage | 1 / 2 | 只用于真实可重叠搬运；普通 cp.async 合同、等待/复用和资源通过 |
| fusion boundary | 一个冻结的相邻子表达式 | 必要中间量、状态写入、N 容差与消费者边界完整 |
| graph shape | B1，加已资格的少量 B | 原 graph 生命周期、固定地址/arena generation 与缓存上限；不无限按长度特化 |

这些不是暴力笛卡尔积。候选必须规范化、去重、检查历史停止记录，再提交给确定性 builder。AI 只提假设与参数，不自行生成任意 unsafe/inline PTX、删除同步或修改测试 oracle；已审查模板中的 unsafe 前提必须明确进入 contract。

### 7.2 初轮成本上限

以下沿用 [29](29_automated_kernel_optimization.md) 的初轮提案，K02 在看结果前冻结实际数值与停止策略；最终机器 SearchPlan 是唯一计数依据。

| 预算项 | 初轮提案上限 | 解释 |
|---|---|---|
| family / 修正 | 1 个 family；初始设计后最多 2 轮有 profiler 依据的修正 | 无新证据不重启历史 NO_BENEFIT |
| unique candidate | 合计不超过 24 | 参数/源/flags/shape 分派变化都产生新的规范化身份，不能改名逃计数 |
| microbenchmark | 最多 4 个入围配置 | 前面静态/证明/动态门已通过；单 kernel 快不能直接启用 |
| E2E 探索 | 最多 2 个候选 | 计完整请求、fallback 和资源；不只统计命中最快请求 |
| 独立确认 | 冻结 1 个赢家 | 源/产物/阈值/shape 分派冻结后才使用确认集 |
| CPU 编译 / proof | 总计建议 2 小时；单次建议 5 分钟上限 | 超时记实际结果与未完成属性，不能写“证明通过” |
| GPU 探索 | 总计建议 4 小时 | 包括失败与重试的真实成本；一个时段只运行一个 GPU 性能实验 |

最终资格所需质量、尾延迟与 soak 有独立预算，不在“4 小时探索”中删掉。原 [14](14_benchmarks.md) 的独立样本、AB/BA、anchor、漂移、bootstrap 与停止规则保留；看到结果后不得扩候选或阈值到出现赢家为止。

### 7.3 自动搜索排除项

R 变化、last-loop/共享 KV、LoopCD、2DSD、sampler/RNG、top-k/tie-break/route 内容改变、新 activation/weight/KV 量化、训练、CPU pool 重写、历史无收益 overlap 重启、TMA/PDL/cluster、`wgmma/tcgen05`、cute-rs、无限 persistent / megakernel、新 mapped spin/relay、运行时下载/编译均不进入此搜索。需要这些方向必须沿原独立任务另立合同。

固定版本 Tile 的 FP8 / FP4 架构限制也不能由自动生成器绕开。若第三方模板需要被排除的功能，输出明确不支持原因，不能通过改 `.target` 或忽略 verifier 获得候选资格。

## 8. R3 与每个 loop 的状态不变量

这里的 kernel 可以改变执行实现，不能改变目标模型。检查点位置由真实图和状态消费者确定；不得把物理权重复用误解为可重用运行状态。固定源码触点为 `src/models/inkling2-loop.cpp`、`src/models/inkling2-dspark.cpp`、原 context 与 memory 实现。[A01–A04]

| 不变量 | kernel / 分派必须保持 | 必测反例 |
|---|---|---|
| **physical / visit / slot 分离** | 6 + 12×3 + 6 产生 48 visit，映射到 24 physical layer；logical slot 沿 Atomic 的真实重排 | 用 visit 直接当 slot、按 48 份加载权重、不同 pass 写同一私有 state |
| **R3 输入与控制消息** | prelude 保留；后续 pass 从规定输入重建，再用上一 pass bank 与 query/down/gain/forget 等产生消息；norm 与 Q/K/V/FFN 边界不变 | 简化成 `h = core(h)` 三次；融合删除必要 bank、norm 或控制中间量 |
| **每 loop KV** | global / SWA 的 slot、有效长度、页/窗口、position 和 codec 按原模型独立 | 只保最后 loop、共享不同 loop KV、更新长度却未恢复已覆盖页 |
| **每 loop conv / controller** | 历史窗口、有效范围及跨步存活状态可提交/撤销/恢复 | verify 后拒绝仅减 pos；取消后滑窗内容来自无效候选 |
| **物理权重共享但路由独立** | 不同 pass 对共享物理 expert 可以选不同 route；route weight 与 slot 对齐 | 缓存上一 pass 的 expert IDs；把复用权重误写成复用路由 |
| **DSpark / draft feature** | 使用资产指纹指定的真实 feature visit 与顺序，保持 Markov / draft 状态 | 抽融合后的错误中间量；以 physical layer 号代替 feature visit |
| **committed prefix 一致** | 所有必要 loop/KV/conv/controller 状态对应相同已提交前缀；bonus/correction 按协调器规则推进 | 最终 logits 看似相同但续接不同；接受数和最后 emit token 的 KV 约定错位 |
| **拒绝 / EOS / max_new / 取消** | 原事务定义的未接受后缀全部撤销，已完成副作用不重做 | 只测全接受；在第一个/中间/最后一个候选拒绝时漏 state；越过 max_new |
| **RNG 与采样事件** | kernel 不新增/重排采样算法；原 proposal/acceptance/residual/target 消费账本有效 | 把丢弃模型状态等同于回拨所有随机数；迟到 ticket 触发第二次采样 |
| **epoch / 资源生命期** | request/model/地址 generation 一致；所有设备/graph 引用保活到末次使用 | 热切换混用新旧 module；旧 epoch 完成写入新 arena；超时释放仍在用的地址 |

检查不能只看最后一个 token 或最终 logits。按冻结 reference 观察关键 visit 的 activation、route、各 loop 的 KV/conv/controller、有效长度/position、draft feature 与 committed state；再从相同 committed prefix 独立重算，验证续接。哪些中间值允许数值容差、哪些索引/状态必须精确，在实验前冻结，不能出错后扩大容差。

涉及融合或不同归约顺序时报告 max-abs、relative-L2、cosine、非有限值、logit 分布与 top-1/top-k、route 差异及原业务质量门。合法 mask 的 `-inf` 与非预期 NaN/Inf 分开处理；禁止把非法数值通过 clamp 变成正常 token。greedy 与随机采样、AR 与 DSpark 分开资格。[13](13_correctness_quality.md)

## 9. 验证矩阵与实际交付

AX 测试编号由 [32](32_kernel_validation_runbook.md) 定义，本表只给消费关系，不重定义 fixture 或 PASS 规则。原 48 项和 GX01–GX20 继续保留；新增 AX 不取代原模型、质量、容量或服务测试。

| 检查层 | 重点 | 消费的 AX / 原门 | 必须保留的输出 |
|---|---|---|---|
| 静态 / 编译 / proof | 实际 SM89、必要属性、整数溢出、ABI、资源与 forbidden feature | K00/K03；AX 中相应构建/证明项，AX03/04/11/19 | 实际命令、退出、按前端对应的 IR/bytecode/device 产物、ABI/resource hash、义务与假设，不编造缺失 PTX |
| 设备访问 / 同步 | 尾块、stride/alias、dynamic route、shared staging、cp.async、未初始化读取 | AX03/04/19/20/21；先 memcheck 后其余适用 sanitizer | 原始 sanitizer 与负例结果、工具版本、错误退出设置；不可用明确未覆盖 |
| 宿主 bridge | context/device、event/lease、跨 stream、graph/module/address generation | AX11–AX17、AX27 | owner/lease/event 轨迹；零提交或 sticky 事实；迟到 epoch 与错误注入结果 |
| 模型状态 / 数值 | 真实 visit/slot、所有 loop 状态、route、拒绝/取消/EOS/max_new/续接 | AX21–AX23，T05/T06/T07 与适用 GX | 中间状态差分、数值指标、独立 prefix 重算与失败样本 |
| 资源 / 冷热 | host/device 两域峰值、module/graph/repack/staging、预算不足和恢复 | AX19/24/25，原 PF07 与适用 G4/T09 | ledger 与设备测量、预留/回收、首次/热态/恢复成本 |
| 性能 / 产品 / 服务 | 完整请求、真实命中与 fallback、原质量、p95、soak | K06，原 G3/G4/G5/G6，AX28 | 冻结比较合同、raw pairs、独立确认、质量/尾部/8h soak 与全部失败 |

Compute Sanitizer 的 memcheck、racecheck、initcheck、synccheck 各有覆盖边界；racecheck 不能被当成所有 global/跨 kernel race 的证明。arena suballocation 的逻辑边界、跨语言 alias、event/epoch 和模型状态仍需自己的合同/测试。固定 error-exit 行为，不能把工具退出 0 与“所有拟检查内容均覆盖”混同。[N09]

### 9.1 收益判定

保持原 [14](14_benchmarks.md) 规则：每 primary cell 探索 12 pairs；冻结唯一赢家后确认至少 30 个独立 case、至少 3 个时间块及原配对统计。最终产品判断用原预登记指标；单项请求中位数至少降低 5% 且 CI 支持正收益，主力迁移至少 10%；关键 p95 不超过 1.05× baseline 并满足绝对 SLO。质量仍是原 150 Java / 300 工具及非劣合同；尾部 200 请求、soak 8 小时且至少 200 请求等原要求不因 kernel 搜索缩减。

重复同一 case、重复 seed 或测许多 kernel 不增加独立确认样本数。失败、timeout、unsupported shape、fallback 和冷启动成本全部报告；不能只统计“新 kernel 命中的快请求”。多 finalist 使用同一确认集时沿 [29](29_automated_kernel_optimization.md) 的预登记多重比较规则，不能边看保留集边换参数。

### 9.2 明确停止，而不是扩大范围

- baseline 不正确或原 capability 不合法：先回原任务修复/资格；不进入性能搜索。
- ABI、越界、race、错误 route、per-loop 状态、数值或 token/tool 提交异常：候选隔离，禁止进入计时排名；提交后错误按 sticky 退役。
- 工作集/保留量不满足：拒绝当前候选，不以缩上下文、删状态、去 budget 或新量化继续原比较。
- microbenchmark 提升而完整请求没有净益：记录全部成本与 NO_BENEFIT；最多两轮有 profiler 证据的修正。
- 前端特有问题：只阻断该固定前端/版本/shape，不把 Tile、SIMT、C++ 或独立 backend 一并判定失败。
- K07 的升级条件不成立：继续局部路线或结案；不因投入工具链成本而启动完整后端重写。

当前没有任何候选被上述门放行。源代码支持、硬件能力与本机收益分别记录；性能和质量结论保持 `NOT_RUN`，直到 [31](31_kernel_tasks.md) 的任务真正执行并产生 [32](32_kernel_validation_runbook.md) 所需原始证据。

## 10. 固定源码与官方文档

审计日期 2026-11-25。cuda-rust 均固定到同一 commit；Atomic 真实路径均固定到原底座。以下来源用于机制和源码事实，不代表当前机器测试。

- **N01**：[NVIDIA Ada Tuning Guide](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)，§1.4 的架构、occupancy、shared 与显式 SM89 建议。
- **N02**：[PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html)，`cp.async`、`ldmatrix`、`mma`、`dp4a`、FP8 与目标要求；实际使用必须同时保存构建工具链版本。
- **N03**：[Advanced Kernel Programming](https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/advanced-kernel-programming.html)，TMA / cluster 等硬件前提。
- **N04**：[Programmatic Dependent Launch](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html)，CC9.0 起的条件。
- **N05**：[CUDA minor-version compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/latest/minor-version-compatibility.html)，CUDA13.x 通用驱动下限与新 feature / PTX 限制。
- **N06**：[CUDA13.2 Release Notes](https://docs.nvidia.com/cuda/archive/13.2.0/cuda-toolkit-release-notes/index.html)，Table 2/3 的版本对应；不是本机专项资格。
- **N07**：[Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html)，timeline 与 trace 使用边界。
- **N08**：[Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)，replay、cache、clock 与采样开销。
- **N09**：[Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/)，工具覆盖、memcheck/racecheck/initcheck/synccheck 与错误退出。
- **R01**：[SM89 target/PTX floor](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-target-spec/src/lib.rs#L348-L352)、[target feature checks](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-oxide-codegen/src/target/select.rs#L197-L235)。
- **R02**：[MMA / ldmatrix](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-device/src/wmma.rs#L236-L317)、[async copy unsafe 合同](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-device/src/generated/async_copy.rs#L12-L51)、[SM80+ cp.async 示例](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/rustc-codegen-cuda/examples/cp_async_small/src/main.rs#L6-L65)。
- **R03**：[Tile requirements registry](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-ir/src/requirements.rs#L104-L163)、[compatibility](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-book/reference/compatibility.md#L7-L100)。
- **R04**：[non-TMA GEMM MODE=2](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-kernels/src/experimental/gemm_variants.rs#L6-L65)。
- **R05**：[Tile kernel catalog / 实验模板](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/cutile-kernels/README.md#L13-L179)。
- **R06**：[cute-rs target whitelist](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cuda-oxide-mlir-export/src/profile.rs#L128-L143)、[SM89 rejection](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/cuda-oxide-book/cute/support-matrix.md#L23-L37)。
- **R07**：[oxide Rust pin](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/rust-toolchain.toml#L1-L10)、[shared pin](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/rust-toolchain.toml#L1-L8)、[Tile pin](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cutile-rs/rust-toolchain.toml#L1-L7)。
- **R08**：[CUDA build floor](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-bindings/build.rs#L21-L25)、[shared driver loader](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-bindings/src/dyn_load.rs#L134-L153)。
- **R09**：[cuda-oxide build / feature status](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/rustc-codegen-cuda/STATUS.md#L3-L60)、[README 的 LLVM 发现与版本说明](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/README.md#L204-L228)、[完整例集 LLVM23 gate](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/examples-compile.yml#L118-L133)。完整 toolchain 证据见 [27](27_cuda_rust_source_audit.md)。
- **R10**：[artifact materialization](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/crates/cargo-oxide/src/commands/materialize.rs#L182-L216)。
- **A01**：[Atomic Inkling loop](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2-loop.cpp)、[Inkling base](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2.cpp)。
- **A02**：[DSpark](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2-dspark.cpp)、[context](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-context.cpp)。
- **A03**：[hybrid ISWA memory](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-memory-hybrid-iswa.cpp)、[ISWA KV](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-kv-cache-iswa.cpp)。
- **A04**：[ggml CUDA dispatch](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/ggml/src/ggml-cuda/ggml-cuda.cu)、[CUDA attention](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/ggml/src/ggml-cuda/fattn.cu)、[expert executor](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-expert-executor.cpp)。
