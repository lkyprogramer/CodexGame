# 41 · Magnitude 源码、分支与借鉴边界

**审计对象：** https://github.com/magnitudedev/magnitude  
**固定主线：** `3aba40fda19fdaacc345c91c5e711a3bca2f9ee3`，committer 时间 2026-11-25 16:41:39 UTC。  
**证据快照：** 2026-11-25 UTC。以下结论来自公开仓库、固定源码和上游设计文档的静态检查；没有安装、构建、运行 GPU、运行上游测试、启动服务或修改生产。全部本机正确性与性能资格为 **NOT_RUN**。

## 1. 决策

Magnitude 值得加入 v2 工程包，最有价值的部分在 **资源账目、异步传输寿命、专家路由回放、驻留变化下的投机成本、证据管理与 Pi 请求观测**。维持 Atomic 为唯一主底座；正式 Inkling-2-Mini 固定 R=3、RTX 4090 24 GB、64 GB RAM、一次一个活跃 GPU 生成，以及原支持范围内的 Q8 KV 不变。

当前 Magnitude 是 Rust / Seismic 推理引擎。它不是 `magnitudedev/browser-agent`，不能用同组织旧项目的浏览器、视觉代理或 action protocol 介绍解释这个仓库。它有自己的模型解释、调度、状态、数值编译、后端和 HTTP 服务；对本方案适合按机制取用，不适合作为现成 Inkling 替代运行时。来源：[职责划分](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/README.md#L1-L7)。

已有明确阻断：当前唯一 target family 注册表没有 Inkling 家族，完整递归树 7094 项也没有 Inkling 命名路径；`recognize` 对未注册 architecture 返回错误。这个发现支持“尚无已验证 Inkling 适配”，不是对未来版本的永久否定。GGUF 是容器格式，递归状态基础设施与 DSpark 方法分类均不足以证明正式 Mini 的 R3 计算、SWA、conv、逐循环状态和 drafter 绑定已实现。来源：[注册表](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/families/registry/src/lib.rs#L20-L32)、[识别与拒绝](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/src/families.rs#L52-L84)。

## 2. 版本、分支与许可证

根许可证为 Apache-2.0，Rust 工具链固定 1.91.1。Pi 扩展的 package.json 另写 MIT、`private: true`、版本 0.0.2；这是组件元数据差异，移植源码前应核对所选文件和依赖的适用许可，并保留所需声明。这里只借鉴设计，不打包第三方代码。来源：[根许可证](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/LICENSE#L175-L191)、[工具链](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/rust-toolchain.toml)、[Pi 组件元数据](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/integrations/pi/package.json#L1-L11)。

本次取得 **49 个公共分支**，完整名称、SHA、author/committer 时间、提交标题和 tree SHA 见 [magnitude-source-pins.json](../manifests/magnitude-source-pins.json)。下表中的 ahead/behind 均表示“固定 main 相对该分支”。它们来自 GitHub ancestry compare，不能由分支名或时间推断。比较接口的文件列表至多返回 300 项，因此未拿该列表证明完整代码差异。

| 分支 | 头 SHA | 头 committer UTC | main ahead / behind | 解释 |
|---|---|---|---|---|
| main | `3aba40fda19fdaacc345c91c5e711a3bca2f9ee3` | 2026-11-25T16:41:39Z | 基准 | 当前审计 pin，最新提交是发布 CI |
| qa/alpha2-fixes | `157a8569a7b0e0d3c229793ef27a382da53085e9` | 2026-11-24T02:48:58Z | 82 / 0 | 已是 main 祖先，不必切回 |
| ship-floor-wave-1 | `afeee41ec2392125f235d25d94b3a75deb2fe89b` | 2026-11-23T06:24:25Z | 148 / 0 | 已是 main 祖先，不必切回 |
| expert-streaming | `1941f0e85d1a4f517ce92d5102882c538dc26cb7` | 2026-11-09T22:56:43Z | 1089 / 13 | 历史分叉；未审计 cherry-pick 等价性，不直接换分支 |
| q8-nonfinite | `64404f48d4c218d043f3e25fe0b546db700e08e0` | 2026-11-15T00:10:15Z | 898 / 1 | 历史分叉；未审计 cherry-pick 等价性，不直接换分支 |
| program-store | `10c4075c458e6bb29b1a2074ab11ae457efde482` | 2026-11-14T10:52:25Z | 905 / 2 | 历史分叉；未审计 cherry-pick 等价性，不直接换分支 |
| custom-models | `726c6affc3d95ae669bec930e137c39877f252a5` | 2026-10-20T20:07:57Z | 1810 / 0 | 已是 main 祖先，不必切回 |
| tilelang | `e01eab35952e102379a97743c2ea0b1259283f31` | 2026-09-16T22:29:51Z | 2719 / 63 | 历史分叉；未审计 cherry-pick 等价性，不直接换分支 |
| engine-rewrite | `34ef779940e07052a493160d1c30ff3fa5a76f27` | 2026-09-28T03:21:02Z | 2338 / 0 | 已是 main 祖先，不必切回 |

最近主线提交 `3aba40f…` 是安装脚本发布同步，不能称为最新内核改进。最近 20 条提交中最靠前的实质运行时修改是 `78c92e4f21e38f9528f21e09c5e43936a04b6b0d`（2026-11-25 05:32:33 UTC，统一 segmented projection GEMV 与 packet dispatch）。同日还包括 recurrent slab 容量、split-DMA eviction / pricing、drafter head 预留、lineage 拒绝、device-lost 等待、CUDA attention vacant tile 初始化等修复。此处引用的是提交历史，不声称这些修复已在本机复现或验证。

尤其不要按 `expert-streaming`、`program-store` 的名字选分支。当前主线已经有相关大模块；这些老分支仍有独立提交，也缺少大量主线后续提交，选择它们会同时改变模型、资源与编译行为。默认研究 pin 仍为上面的完整 main SHA。

## 3. 硬件、数据格式与模型边界

[CUDA 支持合同](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/docs/compatibility.md#L43-L85) 声明 CUDA floor 为 SM80 / R525，列有 CC8.9 RTX40；模型原生 kernel 由 NVRTC12.9 针对设备编为 CUBIN，编译器生成 kernel 则有 PTX 路径。这使 SM89 成为合理的源码研究目标，但文档末尾又明确 **R525–R575 尚未端到端实测**。本次没有独立编译或运行，因此只能写“声明支持范围内”，不能写“4090 已验证”。来源：[未验证范围](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/docs/compatibility.md#L378-L388)。

Magnitude 当前 KV 选项是 `Dense`、`AffineK8V4`、`RotatedK4V4`。Affine 的 codes 与 (scale, zero) 系数分面存储；K4 路线还有旋转 / Lloyd-Max / norm 语义。其注释提到 llama.cpp 的 32 值块宽，不等于复用 Q8_0 的 34-byte block 格式或相同舍入。它们不是 GAAC / SplitZip 式无损包装，不能把 `K8` 当“现有 K/V 双 Q8”或把量化后效果视为 bitwise 等价。来源：[KV 规格](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/state/src/codec.rs#L80-L225)。

本包保留已有 representation 指纹和资格链：Q8_0 原 codes/scales 的精确存储、BF16 lossless、FP8、Magnitude 自有 affine 或 rotated KV 分属不同表示；新增量化必须单独进入 N 类数值和模型质量验证。无损缓存优先保存 Atomic 已有表示，不为套用某压缩率而转成 BF16。

Magnitude 的 SSD 路径主要是**模型专家权重读取与分层驻留**；本包 L03 的 SSD 路径是**完整会话状态 checkpoint**。二者可共享预算与事件合同，但对象身份、持久性、访问模式和发布条件不同，不能共用一个“SSD cache 已支持”的结论。

## 4. 可采用 / 需适配 / 延后矩阵

| 机制 | 对本方案的价值 | 拟落点 | 级别与边界 |
|---|---|---|---|
| 一个物理 store 一份 ledger；claim / allocated / retiring 区分 | 防止重复计算节省、尚未释放即重新分配 | docs34/37，L00/L01 | 优先适配；不替换 Atomic allocator |
| 同快照的预算决定与自身变更日志 | 避免 OS 读数滞后引起容量振荡 | T00、L00/L06 | 先实现可解释快照；统一内存特有 grant 不照搬 |
| DMA + 最后 reader + generation 退休 | 专家预取、Tier staging、Pool 迁移共享寿命合同 | docs34/35，L01/G01 | 优先纳入故障测试 |
| 需求保留的 staging、未发出 hint 可取消 | 防止预测工作占满当前请求需要的空间 | G01/L03 | 绝对 byte / record / in-flight 上限必须独立存在 |
| 路由 trace replay + Bélády 上界 | 判断是否真的值得开发驻留策略 | T09/G01 | 先离线；真实 wall time 另测 |
| 按 deadline / reuse / link cost 的预取 | 减少真实专家 miss stall | G01/L06 | 只有实际 streaming 瓶颈才开；all-resident 可 NO_BENEFIT |
| 按 residency regime 的投机成本失效 | 防止 Pool/Tier/专家变化后套用旧 DSpark 决策 | T06–T08、L06 | 先离线冻结；在线控制另设有界实验 |
| 编译缓存与资格记录分开 | K00–K06 产物可复查、可撤销 | KernelLab 证据清单 | 参考合同，不移植整个 Seismic |
| Pi 被动进度和完整请求统计 | 区分 queue/load/prefill/decode/tool 时间 | T11/L07 | 可选；不改变标准 token/tool 消费权 |
| 完整 Magnitude 引擎作为正式 Mini 后端 | 当前无已验证模型 adapter | K07 或独立未来任务 | BLOCKED/DEFERRED；本轮不新增替代后端工程 |
| K8V4/K4V4、自调数值 α、vision tower | 改变数值 / 模型 / 服务范围 | 独立研究 | 不启用；保留 Q8、VisionOff 和既有质量门 |

## 5. 资源与状态合同：具体借鉴

`ledger.rs` 将一个物理块的分配只记一次，claim 是容量权利、allocation 是实际存在的内存；pool 内 granule 换 owner 不等于物理内存释放。释放请求已经发出但 GPU 仍持有的字节继续占账。OS 快照与自身 allocation journal 配对，预算决定只用同一份 Estimate。这与本包 ResourceLedger 的方向一致，值得补成测试，而非只写“统一预算”。来源：[账目合同](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/memory/ledger.rs#L1-L75)。

`Ledger::reserve/extend` 在下一步状态行数写入前预留，容量不足不推进 reservation；`Reservation::grow` 检查实际写入不得超预留。对 Inkling 必须把逻辑 loop/visit、SWA、conv、target/draft/verify 分别纳入 state_bytes，而不是沿用只按 KV token 数计费。来源：[reserve / extend / grow](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/memory/ledger/reservation.rs#L24-L98)。

Magnitude 的 state 合同要求 completion 后才能 accept，未决 advance 不可 checkpoint；快照除数值状态还含输入布局、接受输出、pending token、grammar、publication cursor、recovery obligation、sampling 和终止结果。它还明确“保留 allocation”不等于“独占某个范围”。本包应延续此区分，增加 tail / SWA 环写保护和 snapshot generation 检查。来源：[状态合同](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/docs/engine/state.md#L6-L87)。

### 拟新增的 hook；均不是既有实现

| NEW hook / 数据 | 触发边界 | 最小输出 / 不变量 |
|---|---|---|
| `BudgetSnapshot` | 请求准入、safe-boundary 重分配 | physical_store_id、sample_id、ledger_epoch、free/grant/held/allocated/retiring；不能混合多个时刻 |
| `AdvanceReservation` | target / verify / recurrent successor launch 前 | state fingerprint、rows、loop planes、reserved bytes；失败时无部分提交 |
| `TransferTicket` | H2D/D2H/SSD landing 提交 | source/destination allocation+generation、issued event、done event、reader set、quarantine reason |
| `RouteTraceRecord` | 已知路由结果发布后 | request、token、loop、visit、physical expert、target/draft、predicted/actual、tier、bytes、wait |
| `CostEpoch` | KV/graph/dtype/residency/budget/context class 改变 | 使旧 profile 的 timing 与 acceptance 估计失效；unknown 不能作为零成本 |
| `InferenceObservation` | 服务端可选进度事件 | request_id、phase、timestamps、cached/processed tokens、generated counts；不可提交 token、工具或状态 |

这些 hook 首版可以是 Atomic 内的结构、事件与 JSONL，不需要新增常驻进程或 RPC 服务。Java8/Pi 只消费服务合同，不获得 CUDA 或 allocator 所有权。

## 6. 异步预取：先寿命正确，再优化策略

当前 main 的 `Copies::watch` 在硬件 transfer 完成后先标记 transport Landed，再弹出 running 队列，避免“队列已完成”先于“slot 可安全退休”被观察。真正回收还要求 hint owner 离开、consumer 集合为空且没有 quarantine。已有源码测试覆盖 delayed fill、两个读者、取消和 slot reuse；本次只读取测试，没有执行。来源：[完成顺序](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/copies.rs#L603-L655)、[退休条件](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/transport.rs#L1562-L1599)、[slot 释放](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/transport.rs#L2485-L2524)。

有界 staging 通过 `keep` 保留需求记录，并以 `limit` 防止不同 pool 大小导致索引越界。`cancel_unbegun_hint` 只撤销尚未发出的 Queued 状态且没有消费者的 hint。对已提交 DMA，应停止新消费、等待 completion、按事务退役；不能将取消标志当成释放许可证。来源：[staging 保留](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/staging.rs#L48-L104)、[取消条件](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/transport.rs#L2309-L2319)。

预取预算不是把“空闲时间”换算成无限免费工作。上游 `Prefetch` 记录每步 bytes 和未使用淘汰，但其 `derive` 中 byte-budget 限制依赖 `in_draft`、`binds` 等条件。本方案不能把它当通用硬限额直接移植：先在 ResourceLedger 设绝对 pinned/device/inflight envelope，再在内部试验 deadline / reuse 排序。缓存 restore、expert fetch、codec 与草稿 feature copy 同计 PCIe/SM 干扰。来源：[预取状态](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/watcher/prefetch.rs#L550-L584)、[条件预算](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/watcher/prefetch.rs#L1434-L1472)。

**静态文档不一致：** `copies.rs` 顶部注释称 Promote 优于 Stage，实际 `cmp_dispatch` 和测试是 Stage 优于 Promote。这是可直接复核的注释/代码差异，未报告运行时错误。Atomic 必须自己冻结优先级表，并覆盖持续 hint、关键 demand、写回释放和低优先级饥饿情形。来源：[注释与比较器](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/copies.rs#L82-L114)、[实际测试顺序](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/copies.rs#L673-L704)。

## 7. 路由回放与投机控制如何进入现有路线

先收真实 R3 route trace，再回放固定预算下的 LRU / frequency / reuse。Magnitude 的 `directory::replay` 同时提供因果 Reuse 与利用未来下一次访问的 NextRead / Bélády；后者能给出“还有多少 miss 可避免”的离线上界，不能作为在线算法成绩。复用物理专家与逻辑 loop/visit 不同，trace 要同时保留两种身份。未发生真实权重传输的全驻留场景，无需据此开发复杂预测器。来源：[回放 API](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/directory/replay.rs#L8-L42)、[未来 oracle](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/executor/src/experts/directory/replay.rs#L99-L124)。

Magnitude 的 draft controller 优化 expected committed tokens / round time，包含 draft、verify、feature catch-up 和切换开销。它会刷新长期未测的 plain reference，并将 target timing 按驻留 regime / context class / sequences 隔离；改变专家缓存容量后继续使用旧 verify 时延，会使决策错误。这是本包 L06 协同实验值得直接采用的观察原则。来源：[控制目标](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/generation/src/draft_control.rs#L1-L30)、[有界观测常数](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/generation/src/draft_control.rs#L44-L80)、[regime 失效](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/generation/src/draft_control.rs#L1116-L1139)。

不能照搬其 0.72/0.78 等 structural acceptance prior，或把 Block 注释列出的 DSpark 视作正式 Mini drafter 资格。也不把“verification 应接近一次 decode”的设计目标当本机事实。首轮只比较预注册、已经正确的宽度与 plain，完整计入 prefill、切换、拒绝回滚、后台干扰，再决定是否需要有上限的在线调节。来源：[先验与方法分类](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/cost-model/src/speculative.rs#L29-L125)。

## 8. KernelLab：证据管理可借鉴，数值门槛不替换

编译缓存存“可加载产物”，资格记录存“在哪个数据、表示、shape、设备、工具链和预算上正确且有收益”。两者独立。Magnitude 文档要求保留全部已测候选、失败、coverage、停止原因和资源；未知项不得写零，产物缓存不得授予新搜索预算。可纳入 K00–K06 manifest 与证据读取，不需引入整个 Seismic DSL / solver / compiler。来源：[证据与资格](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/docs/tuning.md#L337-L370)。

上游 `precision.md` 明确列出 per-row storage-resolution acceptance bar 的开放问题：自身 noise draw 也可能因少量行超阈而被拒绝，并指出尚需特定模型实际测量。另明确“压缩 canonical kernel 相符”不能证明 KV 压缩适合模型，默认路径共享错误也无法靠互相比较发现。这是**上游报告的限制**，不是本次独立复现。它进一步支持保留本包原 G0–G7、Java/tool 非劣、单项请求 ≥5%、真实任务迁移 ≥10%、配对 95% CI 与关键分层 p95 退化 ≤5% 的合同。来源：[开放问题与边界](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/docs/precision.md#L368-L405)。

## 9. Pi / Java8 服务观测与副作用边界

Pi 扩展通过 `openai-completions` 兼容入口工作，`Magnitude-Include-Progress` 为可选进度头。正常产品连接不要求安装该扩展；它是 private 开发组件，peer floor Pi0.83，开发 pin0.84.4。不能拿这一版本约束替代用户现场 Pi 的兼容性检查。来源：[安装地位](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/integrations/pi/README.md#L8-L19)、[provider 接口](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/integrations/pi/extensions/magnitude.ts#L23-L48)。

可借鉴的是 **观测支路没有生成提交权**：clone 只解析额外 progress/timings，原 response 给权威 provider；坏观测不污染 token/tool 流；EOF 不等于生成成功；summary 必须等待正式 response 成功；重试请求只有被接受的一次计入。abort、session shutdown、慢消费者都要显式清理。源码有 CRLF 分片、多 data 行、坏 JSON、clone取消和abort测试，均尚未由本次执行。来源：[观测实现](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/integrations/pi/extensions/observing-fetch.ts#L39-L105)、[EOF 合同](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/integrations/pi/extensions/progress.ts#L48-L63)、[成功统计](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/integrations/pi/extensions/progress.ts#L104-L122)。

Java8 客户端可独立实现 UTF-8 / SSE 解析、请求身份、进度状态和取消，不必引入 Bun / TypeScript / Effect。为了控制复杂度，首版只新增可选 telemetry 字段和 JSONL，保留既有 tool-call 解析器；工具真正执行、重试及外部副作用仍由 Agent 层负责。收到 observation、timings 或连接关闭，均不能授权重复执行工具。Magnitude 服务的有界输出队列和 disconnect handling 可作接口测试参考，而 GPU 已提交工作仍须由 engine 持有到完成。来源：[有界 progress channel](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/serving/src/chat.rs#L1585-L1611)、[disconnect](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/engine/serving/src/chat.rs#L1676-L1693)、[失败完成](https://github.com/magnitudedev/magnitude/blob/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3/inference/docs/engine/scheduling.md#L281-L290)。

没有理由为这个仓库新增 browser/vision agent 集成。VisionOff 继续作为生产默认；多模态支持、视觉塔或图片输入属于另行资格，不能由 README 的通用平台描述推出。

## 10. 有界工程顺序与停止条件

1. **先纳入文档和 CPU 合同：** 在 L00/L01 补 BudgetSnapshot、reservation、DMA/reader退休；MGX01–MGX06。完成条件是合同可执行且错误路径有证据，不要求立刻开发预测器。
2. **收单请求 trace 后做离线回放：** T09/G01 只在真实专家传输占关键路径时进入；MGX07。若未来oracle表明可避免的驱逐miss空间很小，可对进一步替换/驻留命中策略记录NO_BENEFIT。该回放只输出miss与held，没有时延/提前量/重叠模型；预取仍可能隐藏compulsory miss，是否停止需另看真实stall、因果提前量、DMA/compute重叠、带宽竞争与E2E证据。
3. **只选一个可证伪预取候选：** 绝对内存/队列上限、same-format weights、相同R3 / Q8 / context / output；MGX08。SSD 冷读取与 OS page-cache 热读取分别记录；容量收益和速度收益分开。
4. **为现有 DSpark 加 cost epoch 与离线选择：** MGX09–MGX10；先解决失效和完整成本，再讨论在线探测预算。不能为追求接受率降低 R3 或变更目标。
5. **观测协议作为独立小功能：** MGX12–MGX13，在不改模型输出的前提下报告端到端请求、TTFT、prefill/decode与tool时间；现有150 Java任务/300工具案例和soak仍有效。
6. **完整 Magnitude 参照引擎实验默认延后：** 无正式 Mini adapter 先记 BLOCKED；若未来仅用于其他已支持模型的机制 oracle，也必须单独标明目标不同、抢占同一全局 GPU lease，并与 Atomic 的生成/调优串行。MGX14–MGX16。

README 的“2x Ollama”、其他 GPU 的速度图、稀疏 MoE 约5%活跃的产品解释，都不纳入本机预期收益。短任务是否值得首载调优、SSD 流式是否有净收益、64GB RAM中多少空间能分配给专家 tier，必须由 T00/T04 和配对实验决定。未支持设备/模型、测试跳过、装不下、无收益应各有状态，不用 PASS 合并。

## 11. 可交给工程代理的测试目录

这些是 **新测试设计**，不是已存在并执行的命令。具体实现由对应T/G/K/L/M任务产生后才能运行；最终适用范围以42的M任务表为准。不得复制下面的名字生成假 PASS。

| ID | 方式 | 刺激情形 | 验收 | 关联 |
|---|---|---|---|---|
| MGX01 | CPU_MODEL_TEST | 同一allocation多个view、pool转移、claim未分配、释放未完成 | 每块仅计一次；reserved/retiring占准入直到真实完成 | L00/L01 |
| MGX02 | CPU_MODEL_TEST | OS sample与allocate/free交错、stale generation、split VRAM/RAM | 决定使用同snapshot+ledger epoch，自身变化不成others | L00/L06 |
| MGX03 | CPU_MODEL_TEST | state/verify扩展刚好够或差1byte、整数溢出 | 失败不launch/commit，accepted状态不变，checked算术 | T05/L01 |
| MGX04 | FAULT_INJECTION_GPU_TEST | DMA延迟、两读者、取消、晚event、device fault | DMA或任一读者未结束不可复用；fault隔离；无假完成 | L01/G01 |
| MGX05 | CPU_MODEL_AND_GPU_TEST | pool空、跨pool索引上限、hint占满、demand新到 | 需求保留不被hint占用，无越界/无界扩容，有背压 | G01/L03 |
| MGX06 | CPU_MODEL_TEST | 队列排序、reprice、queued/issuing/inflight取消 | 显式policy一致；只撤销queued；连续hint不饿死demand | G01/L03 |
| MGX07 | OFFLINE_REPLAY | R3逐loop/visit真实route；LRU/frequency/reuse/未来oracle | 因果策略不看未来；Bélády只作上界；物理共享和逻辑visit分开 | G01/T09 |
| MGX08 | PAIRED_GPU_EXPERIMENT | all-resident/可预测stream/随机route/SSD冷和page-cache热 | 记录miss/传输/unused/峰值/stall/E2E；可结案NO_BENEFIT | G01/L06 |
| MGX09 | CPU_MODEL_TEST | tier/pool/residency/context/graph/verify资格改变 | 旧成本失效；unknown非0；plain受预算刷新；safe boundary切换 | T06-T08/L06 |
| MGX10 | PAIRED_GPU_EXPERIMENT | plain vs合法draft宽度，含catch-up/switch/prefill | 既有≥5%/≥10%收益、CI、p95≤5%退化和质量门不变 | T06-T08/L06 |
| MGX11 | CPU_MODEL_TEST | 改变dtype/driver/NVRTC/layout/model/预算/shape域 | 旧产物不冒充旧资格；不完整coverage不能生产采用 | K00-K06 |
| MGX12 | CPU_PROTOCOL_TEST | CRLF/UTF8拆包、多data、无DONE、坏JSON、非2xx | 不改token/tool流，EOF不当成功，unknown字段兼容 | T11/L07 |
| MGX13 | CPU_PROTOCOL_AND_GPU_TEST | Pi/Java8 abort、慢消费者、observer卡住、晚DMA | bounded队列、无提前回收、取消不发布新tool；不自动重试有外部副作用的工具 | T11/L07 |
| MGX14 | SERVICE_EXPERIMENT | Atomic生成时启动Magnitude参考或调优 | 全局GPU lease拒绝第二活跃生成，实验串行，VisionOff | T00/L07 |
| MGX15 | STATIC_SOURCE_CHECK | 正式Mini metadata/未知architecture/drafter lineage | 无adapter为UNSUPPORTED/BLOCKED，不以shape替代绑定，不改R3 | T01/T03 |
| MGX16 | CPU_REPRESENTATION_CONTRACT_TEST | 相同shape的Q8_0与affine/rotated | 格式不同先拒绝，无损保持原bytes，新quant另过N/质量门 | L02/L04 |

## 12. 证据分级与交付

[magnitude-source-audit.json](../manifests/magnitude-source-audit.json) 含 20 条带固定 commit、blob SHA、函数/行范围、证据定位和置信级别的发现；每项均为 runtime_status=NOT_RUN、runtime_reproduced=false。分类区分：

- PRIMARY_REPOSITORY：公开仓库身份、根文件、元数据。
- STATIC_SOURCE_FINDING / STATIC_SOURCE_AND_CONTRACT：从具体实现与合同可直接读出的行为，未执行。
- UPSTREAM_DOCUMENTED_NOT_RUN / UPSTREAM_CONTRACT：上游声明的目标或设计，不能提升成本机实测。
- UPSTREAM_REPORTED_LIMITATION：上游主动记录的开放问题。
- STATIC_DOCUMENTATION_MISMATCH：注释/实现/测试之间可复查的差异。

[magnitude-source-pins.json](../manifests/magnitude-source-pins.json) 含完整49分支清单、8个相关分支的祖先关系、最近20条主线提交、58个读取源码的blob pin、树完整性和工具访问边界。仓库主页和固定源码 URL 可直接追溯；部分网页入口无法抓取时，已通过仓库接口读取相应固定文件。访问失败不代表源码不存在。

本审计没有改动已有 codec 文件或 v1.2 工程文档；只为父任务提供可整合的研究结果。后续修改任何 source pin、dtype、model、loop、graph、kernel、driver、budget 或策略时，都需使对应能力证据失效并重新资格。


实施任务、共享接口与停止条件见 [42 Magnitude 融合执行](42_magnitude_integration.md)。这些机制已进入总架构、预算、投机和服务合同，不能只阅读本审计后直接启用上游参数。
