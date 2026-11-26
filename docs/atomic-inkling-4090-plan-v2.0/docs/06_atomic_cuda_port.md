# 06 · Atomic到CUDA的实际移植边界

## 1. 不能混淆两条入口

**普通CUDA路径**：GGUF权重按通用ggml/CUDA方式加载，不启用Atomic engine memory budget/streaming。Inkling和DSpark有通用建图代码，但4090上的实际算子覆盖、精度与峰值仍需T02/T06验证。

**离散预算路径**：同时限制host RAM与device VRAM，按需读取/缓存专家，受一组独立的准入限制。当前固定源码不支持“Inkling + 双预算 + DSpark +128K”。先全驻留不是绕过预算限制宣称已移植，而是建立单独的可用基线。[S01]

## 2. 已核查的代码触点

下面全部是固定提交的**现有路径**；行号会随未来补丁变动，按符号定位。

| 文件/符号 | 当前事实 | 所需动作 |
|---|---|---|
| `common/atomic-budget.cpp::common_atomic_discrete_validate` | 禁spec、MTP；ctx/batch≤4096、ubatch≤32；单slot/单CUDA | 新增经过测试的Inkling capability分支，保留未支持组合拒绝 |
| 同文件 `common_atomic_discrete_load` | 只接收lfm2moe/qwen4exp；Qwen microbatch≤8 | 添加经资格验证的Inkling分派 |
| `src/llama-model.cpp::load_tensors` | Inkling streaming要求预算、单MTL0、全GPU offload | 定义CUDA加载和参数alias的所有权，不伪装Metal设备 |
| `src/llama-expert-executor.cpp` | Inkling low-bit类型准入和加速依赖inkling_metal | 每种实际gate/up/down类型逐项CUDA资格 |
| `src/llama-inkling-core-banks.h::load` | Apple条件编译，Metal host base/grouped hook | 若T09需要，增加CUDA bank上传、两域计费与event寿命 |
| `src/llama-context-atomic.cpp::llama_atomic_inkling_dspark_enable` | 预算DSpark检查MTL0与模型geometry | 预算模式的target/draft共享账本及独立状态新实现 |
| `src/llama-context.cpp` | streaming microbatch及discrete ownership约束 | 保证target/draft context、rollback与预算协作 |
| `src/models/inkling2-loop.cpp` | 通用模型图；若干Metal专用短图/attention hook | CUDA能力分派 + 通用fallback |
| `src/llama-expert-store.cpp` | 非Metal direct路径存在host staging、tensor_set后同步 | pinned双缓冲/计算重叠属于新工作，先做同步正确版本 |
| `src/llama-memory-budget.*`、`llama-memory-contract.*` | 已有host/device账本、reserve/retire和离散准入 | 复用，不能再建一套漏记cudaMalloc池 |

源码固定链接集中在02与 `manifests/source-audit.json`。这张表是在已有能力上扩展，不意味着所有文件每次都必须改。

## 3. 三个资格阶段

### A：普通CUDA基线

正式Mini、固定R3、无spec、单sequence、text-only。4K先通过，继而16K与容量阶梯。验证所有op在CUDA或明确记录的CPU fallback上运行；非预期fallback视作待处理问题。基线本身若错误，先修loader/op支持，不开始性能“优化”。

交付：相同GGUF的参考logits/状态、visit映射、各allocation分类、完整命令与binary hash。FA、KV格式和microbatch列成独立能力行。不要只凭exit 0。

### B：离散预算基础（条件分支）

只有容量或质量要求触发T09。最初只开放4K、单sequence、无spec、已资格量化。先实现同步读取和正确lease；通过后再引入core优先驻留和有界pinned staging。

交付：physical权重alias不重复计费、预算下限正确、准入失败不发布半成品、短读/源文件变更检测、active lease不可evict、graph不引用过期bank。执行期sticky错误按05退役context，在同预算内新建/恢复或明确失败，不能去掉budget求启动。不引入Mac的固定8/20GiB profile魔数。

### C：预算 + 长上下文 + DSpark

分别扩大context和spec能力，最后才组合。每扩展一行，都要同时覆盖CLI、loader、context、executor、KV管理和server限制。单方面提高ctx guard没有资格意义。

交付：4/16/64/128K真实输入、所有拒绝位置回滚、取消/恢复、budget resize边界、峰值ledger与NVML对应，最终形成完整profile白名单。未通过的组合继续返回可读错误。

## 4. 物理驻留策略

起步策略：core优先，其次coda，最后prelude；理由是core重复访问。对照组至少有全驻留、全层均分和LRU。bank应按**实际复用的packed物理权重**驻留，不因48visit加载48份；dequant cache若存在也要计费。

只有miss分析表明必要时才分组按需缓存expert。whole-bank与per-expert-cache都是策略，不强行共存。shared physical layer在不同pass可能选择不同experts，重复层不等于重复路由。

## 5. CUDA传输状态机（T09拟新增）

`FREE → HOST_FILLING → HOST_READY → H2D_PENDING → DEVICE_READY → IN_USE → RETIRING → FREE`

每一步要有所有权、bytes、event和错误处理。只在H2D完成后publish给GPU；只有最后一个使用event完成才能复用。两个staging buffer是初始上限，不以无限pinned memory掩盖调度问题。取消只撤销未提交工作，对仍在执行的CUDA操作等待或延期释放。

现有同步路径作为reference保留到异步路径验证完毕。profiler中有copy和compute并发，不代表净wall time收益；比较相同预算、命中率和缓存冷热的A/B。

## 6. 数值与量化支持矩阵

每种实际expert tensor type × token batch（1/2/4/8与prefill）×resident/streaming都要有独立测试。IQ2/3、Q4_K、IQ4_NL、Q5_0不能靠总体GGUF文件名判断。目标KV和draft KV类型也分开。

先保留通用kernel，逐个引入专用kernel。某种量化不支持应在加载前失败；不可悄悄重新量化或大量展开成FP16后仍报告原预算。

## 7. 退出条件

如果普通CUDA已满足选定质量档和128K完整工作集，T09可对**该完整profile**标 `SKIPPED_WITH_EVIDENCE` 并记录容量表与headroom。指纹包括权重、KV、P/N/capacity、draft、k/B、ubatch、graph和workspace。新增T06/T08特性或更改任一字段必须重测容量，必要时重新打开T09。保留Atomic底座不要求把expert streaming放进所有请求。若host/device离散路径验证成本超过实际收益，主线继续全驻留，预算路径保留研究状态。
