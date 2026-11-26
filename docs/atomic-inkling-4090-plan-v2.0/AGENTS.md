# AI 工程代理执行合同

## 使命与范围

基于 Atomic Engine 的固定版本，构建并验证面向单 RTX 4090 的 Inkling 服务候选。默认业务为 Pi / Java 8 Coding Agent，生产单请求执行、Vision Off。先达到正式模型固定三轮、正确工具调用和可恢复会话，再优化速度。此文件与 docs/01_product_contract.md、docs/05_architecture.md、docs/13_correctness_quality.md 共同约束所有任务。

本包是实施输入，不是 GPU 成功报告。本轮用户授权的是文档包；后续工程执行仍以当时会话的授权范围为准。不要因读到上线手册就自行停生产、改流量、升级驱动、购买 GPU 或上传私有代码。

## 必须保持的事实

- 底座：`AtomicBot-ai/atomic-engine@fb69fff02101b048a0a165a3b502712dd2ca978f`。
- 目标：RTX 4090 24 GB、Xeon Silver 4216、64 GB DDR4、PCIe Gen3。SSD 历史约 600 GB；OS、驱动、Toolkit、SSD余量和实效带宽需 T00 现场确认。
- 正式 Inkling Mini 的权重、循环策略和原生草稿器，与 varloop / 2DSD 资产分开。
- 当前 Atomic 的 Metal Inkling budget 能力不能冒充 CUDA 能力。
- 不把旧 Strata / NInfer 的参数名、缓存实现、速度、质量结论直接套到 Atomic。

## 执行规则

1. 顺序读 README、目标合同、证据登记、架构、任务图。以 `manifests/task-graph.json` 的依赖为准；不得跳过依赖后标 PASS。
2. 先读目标仓库的 AGENTS.md / CONTRIBUTING 和被修改代码。现有源码路径可以直接定位；标为 NEW / PLANNED 的路径要由对应任务创建，不能假称上游已提供。
3. 每次只改变一个可归因变量。新算法、量化变化、内核算术变化和调度变化分别建实验。
4. 所有代码和实验使用隔离分支、独立构建目录、独立端口、固定模型资产。禁止自动更新到 main、下载未锁定模型或复用不匹配的 session cache。
5. 正确性先于速度。新状态/调度/数值实现先建立能失败的测试，再实现。按精确性级别使用 token、logit、状态与质量测试，不要求浮点实现跨内核无条件 bitwise 相同。
6. 有依赖接口的工作先锁定字段/类型，再并行实施。不要并行跑占用同一张 GPU 的性能实验；会污染结果。
7. 每个任务保存：输入版本、变更 commit、配置、实际命令、原始输出、失败案例、测试结果、资源轨迹和结论。使用 templates/，不得只留下摘要。
8. 状态只用 `NOT_RUN / RUNNING / PASS / FAIL / BLOCKED / NO_BENEFIT / DEFERRED / SKIPPED_WITH_EVIDENCE`。没有硬件或数据是 BLOCKED，不是 PASS；程序能启动不等于性能或质量通过。
9. 不为了过测删上游 guard、不降低阈值、不换更简单样本、不改变输出长度、不在看过结果后改基准权重。
10. 性能退化或无收益按停止规则结案；最多两轮有明确 profiler 证据的修正，然后重新立项才继续。研究路线的失败也是有效交付。
11. 合成计时、mock、文档自检与真实 GPU 数据使用不同 `evidence_kind`，禁止混算。记录所有不支持的组合和拒绝原因。
12. 每阶段结束交付可审查结果并继续已授权的下一任务。只有权限/访问、费用、不可逆操作或改变产品目标才需要用户介入。

## 永远不能省略的状态

physical-layer 与 logical-visit 映射；各 loop 的 KV 与 convolution；position/有效长度/滑窗；loop 消息与必要控制状态；DSpark feature 顺序与 Markov 状态；已接受前缀；采样器状态；RNG 消费账本；缓存版本；异步专家 lease 与 CUDA event。

推测拒绝时丢弃无效候选状态，但不能盲目回拨已经消费的接受/恢复随机数。跨请求恢复必须完整校验状态指纹。

## 硬停止条件

- 出现不可解释的正式模型输出差异、越界、NaN、错误工具执行或会话串扰。
- 模型/草稿器/特征层/模板/量化指纹不匹配。
- 实际128K输入无法证明、发生静默截断或 synthetic 被混成真实业务。
- 无法满足资源保留量；存在持续 swap、OOM、lease泄露、图引用已释放地址。
- 无法取得所选2DSD目标匹配的资产、Atomic适配或SM89资格。公开实验runner已在S44中审计，不再作为统一缺码理由。

满足停止条件时：隔离候选、保存证据、标明阻塞及受影响任务；保留已经通过的主线。

## Ghost增补执行边界（v1.1）

先读docs/23–26及manifests/ghost-source-audit.json。G00–G05是可选任务，G0–G7是能力gate；未启用特性不阻断T12，已启用特性必须附对应资格证据。禁止把外部CPU CI、作者短序列跑分或本包工具测试当4090资格。

- Ghost仅作固定源码参考；专用Inkling与通用GpuSession的功能分别审计。未知R/head/conv/pool几何在launch前拒绝，不靠metadata中的loop_count推导varloop支持。
- 精确存储重排与实际算术分别定性；repack增加的RAM、staging、GPU地址和图生命周期纳入同一账本。改变算术必须重新绑定target身份与质量合同。
- relay错误在提交token/tool前必须可检测；sticky失败后drain并退役context/worker，不在旧epoch续跑。迟到ack不复活失效ticket。
- EOS/取消/接受前缀提前终止后恢复全部状态，不能只缩短pos；max_new边界也保留回归测试。
- 闲置会话快照先预留/驱逐再复制，原子发布；weights/layout/staging/opening/live snapshot/恢复峰值统一计费，single active generation仍为1。

## CUDA Rust与自动优化边界（v1.2）

先读docs/27–32及相应机器清单。K00–K07是可选任务，不替换T00–T12；只对实际选用的kernel/profile要求新增资格。K07独立backend初始DEFERRED。既有门槛、G04后置与历史停止条件保持；R03因S44公开实验分支改NOT_RUN，实际能力仍未资格。

- AI生成器仅提出冻结模板/参数和假设，不可写oracle、holdout、阈值、资源余量、stop registry或资格registry。先冻结SearchPlan再看结果，单GPU性能worker为1。
- 原ggml-cuda持有context、stream、arena、weights、state、events与graph。候选首选固定SM89 cubin；不自动引入第二context/allocator或重写server/model。
- 硬件支持、前端支持、具体op/模板支持、编译、scoped proof、actual GPU与模型资格分别记录。cutile与cute-rs不同；SM89不能启用SM90/Blackwell专属路径。
- proof的PROVED_SCOPED不等于task/gate PASS。禁止export-only、未知、超时、空义务、unchecked或旧hash获得verified资格；基础公理/TCB/未证明编译链必须列明。普通C++可独立走原动态资格，不强制所有候选先有形式证明。
- 实际SM/UUID、非零launch、输出oracle与完成证据不可省略；exit0/外部CI/静态PTX检查不能冒充4090执行。动态检查必须显式处理sanitizer错误退出码和覆盖。
- 提交后lease持续到最后event；CUDA错误sticky，禁止token/tool commit。未确认完成的内存不释放、不复用；状态污染后不在旧context中静默fallback。预提交NoMatch才可选择原合法实现。
- 新candidate/ABI/registry/layout/toolchain/driver身份必须进入完整能力绑定。改编译或runtime条件重新验证受影响资格；哈希绑定不代表编译器语义证明。
- 生成、构建、证明、隔离执行、性能、确认、registry分阶段保留全部失败。没有真实E2E收益就按原停止条件结案，不自动扩大为完整后端重写。

## v2.0 统一执行要求

先读docs/00、34–40，以及Magnitude的41/42。L00–L07和M任务只为选中功能生成证据，不成为全部主线的强制前置。Tier不释放GPU KV，Pool另做N类Attention资格；Q8_0不按BF16比例估算。完整StateInventory、next-logits/cursor、typed subrecord目录、raw pending峰值、reader/update/replay事件与有限overflow回退必须闭合。Schema只验证结构；缺L01语义验证不能授缓存能力。Magnitude是inference engine，browser-agent是另一个仓库；不因Magnitudes源码存在就切换Atomic底座或重开旧no-benefit路线。
