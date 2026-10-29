# NP-3 · CPU pool 执行计划（收编自 v2 包 P01，2026-10-26）

> 正文来自 GPT Pro v2 包 `strata_flashnext_4090_extreme_lab_v2/plans/P01_CPU_POOL.md`（2026-10-25，未连目标机）。**在本包执行时，下面的调整优先于正文。**
>
> 1. **基线**：本包公共基线 A0 `5c8dd322` + EXACT6，不先换到 v0.2.6。已核对 A0 → v0.2.6（`4b9e05a2`）的 Flash-Next 相关改动：CPU 侧只有 AVX-512 一 token 行（`x512_one_ok`，依赖 4216 不具备的 VBMI 等）和 `STRATA_ACT_DUMP` 研究开关，`pool.cpp` 未变；async tier 自评估在 `STRATA_ADAPT_OVERLAP=1` 下被排除；`serve/server.py` 有改动，会与 #1536 / CFG-PT 补丁冲突。
> 2. **已有证据**（[DIAG](../reports/P0-T5-DIAG-20261025.md)、[NP-0](../reports/P0-T7-NP0-20261025.md)）：EXACT6 下 CPU 专家约 4.5～4.6 ms/窗口，约 77 µs/miss，折算带宽约为 36 GB/s 上限的 55%；POOL8 让 CPU 阶段慢约 21%；NP-1a 的 Q2_0 微基准测的是引擎不走的分支。所以 P01-02 之前先做 #3871（`kq_cpu_bench` 走 pool 实际路径，见 `prs/13_PR3871.md`）。**#3871 已完成**（[P2-PR3871](../reports/P2-PR3871-20261026.md)）：
>    - Pi 采样负载下引擎约 75 µs/miss，每个 miss 平均 1.23 个 token。
>    - 本机 CPU 专家有 10 种 GU/down 格式组合（不是此前写的奇偶两种），按层加权的 16 线程吞吐下限约 57 µs/miss（nt≈1.2）。
>    - 差额 17～25 µs/miss 是本计划能回收的上限，约 0.8～2.5 ms/窗口（窗口时间的 6～11%）。
>    - **P01-02 第一步（perf + 非 serve 分阶段汇总）已完成**（[P2-NP3-PERF](../reports/P2-NP3-PERF-20261026.md)）：串行中间量化只占 pool 时间约 1%，**P01-04 按停止条件不做**；两个 rows 阶段只达到 bench 吞吐的 72～74%，每阶段约 17 µs 非计算开销；perf 只能看到自旋，分不清来源，所以第二步写分阶段 trace（`STRATA_LAB_NP3_TRACE`）。
>    - **第二步已完成，NP-3 关闭**（[P2-NP3-TRACE](../reports/P2-NP3-TRACE-20261026.md)）：每个 CPU miss 约 76 µs，同步（publish / 唤醒 / claim / re-park / 量化）约 2.5 µs，尾部约 5 µs，其余在任务内；第一步“每阶段约 17 µs 固定开销”的推断是错的。任务内偏慢来自 gate/up 受计算限制，以及 PCIe 同时读内存的争用。P01-03 / 05 / 06 / 07 判 NO_BENEFIT，不实施；`--pool-tasks` 扫描在 ±1.5% 内。下一步转 NP-RES 的 CFG-PCIEFRAC。
> 3. **perf 已可用**（linux-perf 6.1.190，`perf_event_paranoid=1`）：P01-02 第一步用 `perf record -g` / `perf stat` 对 pool worker 采样，区分计算、自旋 / park、内存停顿；只有 perf 拆不清时才写 phase trace。
> 4. **评估负载必须含 Pi 采样 + thinking**：单会话实测每窗口只提交 2.05～2.44 token（greedy 2.78），T 分布不同，CPU 每 expert 的 nt 分布也不同。除 decode 组外，用 `tools/session/session_bench.py` 的固定前 3 轮（同 seed 的文件与问题）做配对；主指标是引擎 decode ms/窗口和“总生成 token / 总 decode 时间”，不比较每轮墙钟（采样输出长度不同）。见 [单会话](../docs/11_SINGLE_SESSION.md)。
> 5. **顺序**：P01-02（perf / trace）→ P01-03（所有权与调度测试）→ ~~P01-04（并行中间量化）~~（已排除）→ P01-05（成本加权分行）；P01-06 / 07 只在 trace 证明 park 周转或跨 expert 尾部仍是实质瓶颈时启动。
> 6. **采用门**按本包 [统计](../docs/05_STATISTICS.md) 的正式门；开关命名用 `STRATA_LAB_NP3_*`，默认关闭，启动回执 `LAB_NP3 enabled=`。

# P01 / NP-3：FlashNext CPU pool 主线实施与验收计划

执行基线最终刷新为`4b9e05a2a806a3fe24f7b2560d98626c37dade35`（v0.2.6）；本文41cf固定实现锚在相关文件中未变，见 v2 包 `sources/FRESHNESS_DELTA.md`。
本计划不修改引擎。执行基线固定为用户生产 v0.2.3 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + EXACT6，并保留最新 main `41cf05a06a25dd29103b7b27a2279a3f60c21876` 的隔离对照。目标机器是 Xeon Silver 4216 16C/32T、64 GB 双 DIMM DDR4（附件约 36 GB/s）、RTX 4090 24 GB。目标模型是 GSQ-RCO IQ3_XXS，所有实际 GU / down 类型以模型 manifest 为准。

**主目标：缩短真实 CPU miss 工作在 verify 窗口中的关键路径，同时保持相同 expert 分组、相同算术与相同输出。**既有 POOL8 / PROFILE 无收益结果已经归档；本计划不是重新把 worker 数改成 8。已有 EXACT6 也不是本计划的新成果。

## 1. 固定源码事实与修改边界

| 项目 | 现有入口 | 事实与不可破坏的合同 |
|---|---|---|
| GPU / CPU 分流 | `src/core/expert_source.cpp::expert_pool_dispatch_multi`，约 L4779 | 同一 expert 的多 token 已合并；先发 GPU/PCIe plan，再做 CPU 工作 |
| job 输入 | `include/strata/kernels/cpu/pool.hpp::ExpertJobMulti`，L59 | `blob`、`nt`、`act[MAXT]`、`nact[MAXT]`、`out[MAXT]`、可选 `fmt` |
| pool 入口 | `ExpertPool::run_split_multi_native`，`pool.cpp` L1359 | `n<=0` 直接返回；每批最多 `kMaxSplitMulti=96`；GU→quant→down |
| 当前分行 | `phase_tasks` / `drain`，L1316 / L1176 | 大致每参加线程 3 个任务；phase 5 是 GU、phase 6 是 down；按总行数分配 |
| 同步协议 | `publish` / `worker` / `run_phase`，L960 / L974 / L1280 | epoch-tagged claim；seq_cst sleepers 协议防丢唤醒；阶段结束不仅等待 done，还等待 re-park |
| 中间状态 | `SplitBufMulti`，pool.hpp L363 | 每 expert 的 `ff[MAXT][FF]`、`a2[MAXT]`、`hq[MAXT][kNativeHBytes]` |
| 算术 | `native_gu_rows` / `native_quant_h` / `native_down_rows` | 不同 nt 路径可能有不同舍入；必须保持原 group / nt，不能把 nt=4 拆成 4 个 nt=1 当精确优化 |
| 统计 | `ms_multi_gu/q/down` 与 `phase_ms` | 前者含 phase wall time；旧 `phase_ms` 不能直接解释 native multi 内每个 barrier |

来源固定为 [pool.hpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/kernels/cpu/pool.hpp#L1)、[pool.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/pool.cpp#L1176)、[expert dispatch](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_source.cpp#L4779)、[native expert](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/native_expert.cpp#L296)。

不在本主线修改：CPU ISA dispatch、IQ dot 求和顺序、GPU kernel、router / tail skip、spec 接受算法、cache replacement、worker 数默认值。独立的 Cascade Lake VNNI 实现应另立项目，不能通过放宽 `cpu_avx512_ok()` 让缺 VBMI / VPOPCNTDQ 的 CPU 进入已有 IQ512 编译单元。

## 2. 固定输入、输出与状态合同

### 2.1 输入

每次调用固定 `NativeFmt f`、`ExpertJobMulti jobs[0..n)`，保持 `jobs[e].nt` 和指针顺序，blob 与 activation 在调用结束前只读。`fmt != nullptr` 的 job 使用自己的布局；当前实现中 phase rows 仍以层形状规划，因此测试应区分“同形状不同合法布局”与不应被接受的形状不匹配。未知 / 非法参数应在边界验证，不允许进工作线程后悬挂。

真实服务时路由最多 T×10 个条目、T≤8，所以一个合法 FlashNext 窗口通常不会超过 80 个独特 expert；仍需直接测试 API 的 96 / 97 边界，因为实现公开支持分批，未来调用者可能使用它。零 expert 对应全 resident 或全 GPU miss 的合法层，不是异常。

### 2.2 输出

每个 `jobs[e].out[t][0..n_embd)` 与旧 pool 在相同 binary / ISA / group / nt 下逐 bit 相同。调用返回后不得仍有 worker 读 jobs / blob / activation / 临时 `ff` 或写 output。每个 output row 只有一个 writer；路由 weight 仍由原 combine 处理，pool 不改它。

### 2.3 稳定性合同

1. `n=0` 不发布无意义 epoch、不改变输出、不等待已不存在的工作。
2. 旧 epoch 的迟到 worker 不能领取新 descriptor，不能给新批次 done 累加。
3. job 完成与 descriptor 可回收是不同事件；新协议必须明确证明读者已经退出。
4. GU 全部必要输入生成后，才可量化完整中间向量；down 读取整个 hq，不能根据“对应 GU row 已好”提前执行。
5. 每次线程 sleep 前、publish 后、destructor stop 都不丢通知；取消遵守原引擎安全边界，不能新增“释放正在执行数据”捷径。
6. GPU plan 发布、CPU complete doorbell 与 `Verifier::commit` 顺序保持。没有 CPU miss 的层不得意外拖延 GPU。

## 3. 拟新增接口：先内部结构，后是否暴露选项

下面是**拟新增设计示意**，不在当前 main，名称可由实现者按项目风格调整。第一版不新增公开 CLI，不改变默认策略；选择通过测试 harness 或临时 compile-time gate 完成，最终 gate 是否保留取决于实测。

```cpp
// Proposed internal API; not present in upstream.
enum class NativePhaseKind { GateUp, Quantize, Down };

struct NativeRowTask {
    uint32_t expert;
    uint32_t row_begin;
    uint32_t row_end;
};

struct NativeQuantTask {
    uint32_t expert;
    uint32_t token;
};

struct NativePhaseSample {
    uint64_t generation;
    NativePhaseKind phase;
    uint64_t published_ns;
    uint64_t first_claim_ns;
    uint64_t last_done_ns;
    uint64_t last_reader_exit_ns;
    uint32_t task_count;
    uint32_t expert_count;
};

struct NativeScheduleDecision {
    bool parallel_quantize;
    uint32_t gate_up_tasks;
    uint32_t down_tasks;
};
```

P01-04 只需要 quant tasks；P01-05 才需要 row task 表。P01-06 的 descriptor 双缓冲与 reader-exit 仅在证据要求时新增，不应为了架构漂亮先把全部结构一次引入。所有任务数组和 trace buffer 在 pool 创建 / 容量变化的安全阶段预分配，token 热路径不反复 heap allocate。

如果实施阶段需要临时环境变量，例如 `STRATA_POOL_NATIVE_SCHED`、`STRATA_POOL_PHASE_TRACE`，必须在文档、日志中标为**拟新增 / 本补丁专有**，给出默认关闭与非法值拒绝；不得用它们生成“上游现成可运行命令”。

## 4. P01 任务拆分

### P01-01：冻结可比输入与源码合同

**输入**：生产 binary / EXACT6 diff、主线 SHA、实际模型与 runtime 配置。**输出**：`baseline_manifest.json`、实际 GU/down/shape清单、CPU placement、固定 decode 请求集、旧 pool replay oracle。

读取上述真实源文件；比对 EXACT6 所改函数，保留实际编译 ggml ISA。显式固定 adaptive async、tail skip、spec 与 lookup 的配置，关闭 VERIFY_PROFILE / ACT_DUMP 等重观测。0/1/2/多 expert 与 nt1…8 的 replay 输入从真实 trace 和可复现 synthetic fixture 两类构建。

**验收**：同一旧 binary 重放产生一致 hash；所有 fixture 记录量化类型、nt、形状和 seed；有无 Hadamard 分开。**停止**：实际模型 / binary / config 对不齐时只补齐输入，不能继续声称优化。**已有 target**：`native_expert_parity`、`q8k_quant_parity`（运行方式见第 6 节）。

### P01-02：低扰动 phase trace

**源**：`pool.cpp::publish / begin_batch / run_phase / drain / worker`；dispatch 的 round/layer ID。**拟新增**：抽样 `NativePhaseSample` 与每 worker 局部完成时间，最后在非热路径汇总。

第一轮区分：等待上一phase读者退出、publish→首次claim、GPU overlap中的hostdrain、最后任务到最后读者退出、serialquant。每 expert 记录 nt / bytes；不在 `_mm_pause` 内增加原子 fetch_add，现有头文件明确解释该做法曾引入缓存行争用。

**验收**：trace开关不改变输出；记录缺失和时钟倒序可检测；instrumented与uninstrumented差异在预先选择的测量噪声范围内。**停止**：trace本身使性能差异不可分辨，先降采样；若phase/barrier成本没有足够关键路径份额，停止P01-06/07。

### P01-03：建立调度回放与所有权测试

**源**：现有 `pool_tasks_test.cpp`、`pool_stress.cpp` 与 `native_expert_parity.cpp`。**拟新增 source / target**：`tests/core/native_pool_schedule_test.cpp` / `native_pool_schedule_test`；`tests/core/native_pool_replay_bench.cpp` / `native_pool_replay_bench`。这些不是已有构建目标。

用真实 job 格式构造只读activation、带 canary 的 output、可延迟的 task completion。旧 pool 是调度改动的同算术 oracle，不用浮点 double reference替代bitwise对照。增加每row exactly-once instrumentation作为测试模式，输出buffer前后 redzone检查。

**验收**：第 5 节的边界矩阵全部通过；unsupported fixture显式skip/拒绝而非空跑成功。**停止**：出现非确定性hash、重复writer或guard损坏时先定位race，不扩性能测试。

### P01-04：独立并行中间量化

**源**：`run_split_multi_native` 中 GU结束后的双循环；`native_quant_h` 与 `act_quant_any`。**改动**：量化单位为 `(expert, token)`，不切 quant block；使用原函数和每worker私有scratch；GU与down边界先完全保留。

小任务可以走旧serial量化，门槛先由fixture和实际分布决定，不硬编码“多于8就快”。拟增加quantphase模式，若新publish开销抵消，就采用host+部分worker协作或保留serial，而不必强留新模式。

**正确性**：bitwise `ff→hq/a2`，每down格式与Hadamard；nt1…8；小/大n。**指标**：quant段walltime、额外同步、整个CPUphase与有效token/ms。**停止**：仅quant微基准改善而完整verify无可重复收益，或0/1 expert明显退化，回退该策略。

### P01-05：成本加权分行，保持原 expert grouping

**源**：`phase_tasks / drain` mode5/6、`NativeFmt::gu_row / d_row / n_ff / n_embd`。**拟新增**：bounded `NativeRowTask` 表与确定性cost估计。

估计权重格式解码成本与nt点积成本，优先调度重任务，按较大有界行块避免过细claim；每task可跨expert或不跨expert均须保存单rowowner。不能将多token组拆成独立dot，也不改变Hadamard与SwiGLU。

**正确性**：同旧pool输出逐bit；nt极偏斜（一个nt8，其他nt1）、不同合法rowbytes、0/1/2 expert与96/97分批。**指标**：last-worker tail、总claims、LLC/DDR、GU/down/verify。**停止**：权重模型只在synthetic均匀组快而真实trace不快，保留原简单切分；不得无限增加heuristic。

### P01-06：可选 epoch / reader-exit 周转优化

**启动条件**：P01-02仍显示park等待是实质瓶颈；P01-04/05已通过。**源**：`claim / publish / worker / wait_parked / run_phase`、pool.hpp开头同步合同。

拟设计双缓冲不可变descriptor、generation与reader-exit确认，使worker短阶段之间等待新descriptor而非完整re-park。书面列出happens-before：descriptor写→releasepublish→successfulclaim acquire→任务读写→done release→readerexit release→host acquire→复用。保留旧协议作为回退。

**新增测试**：epoch-wrap附近测试hook、迟到worker、sleepers通知竞争、descriptor重用、constructor第一批、destructor空闲/忙转空闲、host_works on/off、过短spin压力。**指标**：phase周转与CPU总功耗/占用、request响应。**停止**：协议不能简单证明、增益不足覆盖维护风险或任何一次deadlock/错误writer；不能通过加超长timeout掩盖。

### P01-07：可选 expert-local pipeline

**启动条件**：P01-06后仍有较大跨experttail且有可用带宽。**源**：`SplitBufMulti` 与 GU/quant/down ownership。**拟新增**：每expert GU剩余任务计数、quant完成、down就绪状态；所有局部任务完成后才CPUcomplete。

这是后续高风险分支，不是本轮成功必须包含的项目。down必须等待完整hq；未量化或尚有写者的输入禁止消费。固定权重/activation读顺序与运算核心，避免流水变成数值优化。

**验收**：不同expert人为延迟、最大nt、取消/清理、buffer复用、压力矩阵；比旧方案逐bit。**停止**：额外counter/queue/cacheline争用抵消tail消除，或DDR已经饱和，退回P01-04/05/06已证明有效子集。

### P01-08：集成到 hybrid verify，不动门铃合同

**源**：`expert_pool_dispatch_multi`、`Verifier::run / publish_plan / raise_flag / commit`。保留先发GPU计划、CPU输入一次quant、VRAM/PCIe/CPU并行。拟新增日志只报告当前policy/命中计数，不引入用户必须理解的内部任务参数。

**回归**：全GPU（0CPUexpert）、1miss、2miss、多miss；PCIe share不同但固定的合法配置；specT1…8；accept0/partial/full；CPU慢/PCIe慢注入；取消在draft/verify/commit安全边界；A→B→A恢复与下一请求继续工作。

**验收**：所有完成标志只在真实工作完成后发布；固定placement的logits/state按位等价；输出不遗漏不重复。**停止**：pool快而GPU等待/host门铃变慢导致无总收益，先恢复交叠，不直接叠新GPU优化补洞。

### P01-09：最小必要并发与长期回归

运行已有pool tests与新增owner/stress，不把纯CPU测试无关地扩到全部平台。压力重点是大量0/1/2expert、worker在睡眠边界返回、1…8 nt轮换、96/97批次和host参与。测试进程必须有限timeout，超时保存 `ExpertPool::diag`。

另跑生产长请求、连续短请求、空闲后重新开始、用户取消后重入，分别固定adaptiveblocking与生产采用的overlap模式。`pool_stress`本身是现有针对tinybatch/sleepers的测试，不能当全部native multi覆盖。

**停止**：任何race、hang、UAF、canary损坏或非有限输出零容忍；出现问题立即停性能评测，缩成最小fixture。

### P01-10：关掉观测后的性能决策

输出三层结果：`native_pool_replay_bench`（拟新增）固定jobs；同T/placement的verify；生产spec策略的完整请求。用配对ABBA或随机顺序、固定热身、相同输入和cache初态；hash不同则先确认是否配置/算法变化。

**建议决策门槛，属项目选择而非测得结论**：小改要有可重复正收益且置信区间不跨零；协议大改宜有更明显净收益（可预先选3%为工程门槛），常见0/1expert和p95不允许物质退化。若团队另设阈值，必须测试前写入manifest，不能看完结果后改口。

报告有效outputtoken/ms、p50/p95、GU/q/down、miss/nt分布、频率、DDR流量与CPU占用；禁止把互相重叠的phase毫秒相加计算“总省时”。P01只保留经验证有效的最小patch集合。

### P01-11：交付与回退

交付：diff/commit、ownership设计、真实target运行记录、fixturehash、AB原始日志、统计脚本、环境manifest、旧路径回退方式、为什么未采用其余候选。默认是否启用由证据决定；若无收益，交付“NP-3在该瓶颈分布下已排除”的报告并保留有用诊断，不强行合并零收益代码。

## 5. 必测边界矩阵

| 维度 | 样例 | 核心断言 |
|---|---|---|
| expert数 | 0、1、2、3、10、31、80、96、97 | 0不触碰output；exactly-once；97合法分批 |
| nt | 每组1…8；组间极偏斜 | 保持组内原顺序和同算术结果 |
| phase分块 | rows<workers、1row、最后不整除、默认/显式tasks | 每row恰覆盖一次，量化block无重叠 |
| 格式 | actualmanifest中所有GU/down、tail_off、Hadamard | 不以IQ3_XXS包名代替逐层类型 |
| 参与者 | host_works true/false；实际worker配置；单worker测试 | host与worker不会共用scratch |
| 等待 | 长空闲后首批、极短spin、迟到worker、快速0→1→0 | 不丢唤醒，不跨epoch写done |
| ownership | 输入只读；outputredzone；descriptorpoison | 返回后无读者/写者 |
| overlap | VRAM/PCIe/CPU混合，先plan后CPU | 保留原GPU提前启动与join |
| speculation | T1…8；0/部分/全接受，page边界 | GDN/QSA只提交接受前缀 |
| 生命周期 | cancel、error、恢复、析构、下一请求 | 无死锁，无脏状态传播 |

取消测试针对引擎现有安全边界，不能假定CPU pool已经提供任意task中断API。需要新增task级cancel时必须另列设计与强制析构禁止条件。

## 6. 已有 build targets 与可执行命令模板

已从固定SHA [CMakeLists](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L1765) 核对：

| build target | CTest名 / 调用 | 条件/注意 |
|---|---|---|
| `pool_tasks_test` | 同名 | `STRATA_BUILD_TESTS`；native CPU支持 |
| `pool_plan_test` | 同名 | mock topology，不用GPU |
| `pool_cores_test` | 同名 | 真实pool/thread placement |
| `pool_affinity_test` | 同名 | Linux构建取Linux源码，不叫 `pool_affinity_linux_test` target |
| `numa_pool_test` | 同名 | mockNUMA策略 |
| `pool_stress` | `pool_stress 20` | tinybatch/sleep测试 |
| `q8k_quant_parity` | 同名及AVX变体 | 原quant函数参考 |
| `native_expert_parity` | 支持 `<shard.gguf> [layer ...]`、`--synthetic GU/DOWN` | 目标需CUDA或HIP相关构建；真实pack路径必填 |
| `pool_test` | `pool_test --selftest` | 项目真实expertpack输入可能必需；缺数据不能报告通过 |

以下复用**已经配置的**测试build，保留生产相同编译设置；不凭空指定新工具链或覆盖生产build。执行者先把 `STRATA_TEST_BUILD` 设为自己的隔离测试目录：

```bash
cmake --build "$STRATA_TEST_BUILD" --target pool_tasks_test pool_plan_test pool_cores_test pool_affinity_test numa_pool_test pool_stress q8k_quant_parity
ctest --test-dir "$STRATA_TEST_BUILD" -N
ctest --test-dir "$STRATA_TEST_BUILD" --output-on-failure -R '^(pool_tasks_test|pool_plan_test|pool_cores_test|pool_affinity_test|numa_pool_test|pool_stress|q8k_quant_parity)$'
```

新增 `native_pool_schedule_test` / `native_pool_replay_bench` 只有实现并加入CMake后才可以调用。不要将文档中的拟新增接口或target误记成已存在、已执行。

## 7. 放弃条件与有限后续

如果数据表明实际CPU专家已接近本机可达DDR上限，且park/量化/tail都很小，NP-3的大型任务图不会创造带宽。此时保存证据，转向减少CPU miss字节、分流与缓存；如果CPU份额被GPU完全遮住，也不把微基准改善算生产收益。只有后续GPU/PCIe改动重新暴露CPU关键路径时，才按新分布复测。

本计划完成的定义是：得到一组正确且在真实目标上有效的最小改动，或严谨排除这组假设；不是一定交付一个复杂的新线程池。
