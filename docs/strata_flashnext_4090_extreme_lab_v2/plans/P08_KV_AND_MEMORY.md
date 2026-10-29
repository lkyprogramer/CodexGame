# P08 — KV 格式、内存预算与权重格式 Implementation Plan

> **For agentic workers:** 执行时使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，分支完成数值与状态审阅后再做性能比较。本文所有新增设计均待实施；没有目标机新实测。

**Goal:** 先证明现有显存/RAM预算或数据流的浪费，再减少活跃 KV 与资源争用；需要改变精度/权重的候选单列数值或质量轨，不能与当前 int8、当前模型包的精确优化混算。

**Architecture:** 现有 ExpertCache VMM 与 elastic KV → 统一资源账本 → 有界 lease/admission → 现有 KV 编码/读取/快照合同 → 按格式资格启用候选。优先验证已有格式和流式路径，再决定是否添加新 codec。

**Tech Stack:** Strata C++/CUDA 12.3、`sm_89`，Xeon Silver 4216 16C/32T、64GB DDR4，固定 main `41cf05a06a25dd29103b7b27a2279a3f60c21876`。

**Spec:** 包内机器、质量、benchmark、统计协议；覆盖 O44、O46–O50、O52–O53。O45 冷快照无损压缩、O51 checkpoint、copy 仲裁归 P11；本计划定义 codec/version 和资源接口。P10 负责把低比特和稀疏等 Q 分支组织成独立研究资格，避免与默认配置混合。

## Freshness：审计锚与执行锁

2026-10-25 最后刷新：实验执行锁为 [`4b9e05a2a806a3fe24f7b2560d98626c37dade35`](https://github.com/Niko1221/Strata/commit/4b9e05a2a806a3fe24f7b2560d98626c37dade35)，release v0.2.6；本文保留41cf的固定源码引用。项目已核对两锁之间`src/core`、`include/strata/core`、CPU/CUDA kernels与prefill的git对象相同；Qwen generate只有spec-split非bitexact说明增量，serve还有空消息400/one-token rate修正，CMake版本变化。执行时保留新锁的API修正，不用旧固定引用误称当前入口完全未变。相关新diff仍须随实验manifest记录。这个刷新不是本机性能验证。

## 1. Global Constraints：已有能力与真实模型

1. 当前生产 KV 为 int8；`--kv q4_0`、`--kv k8v4`、旋转 KV、`--kv-resident`、`--kv-grow` 已在 main 存在。`QsaState` 已含 elastic VMM、host/resident 和多精度字段。候选新增点是本机资格、统一预算、PR 的窗口扩展或真正缺失格式，不能把 4bit/旋转/弹性 KV 重新宣称为新实现。[S1][S2]
2. `ExpertCache::open_segmented/shrink/grow` 已有分段 VMM。O44 应先扩充跨 KV/GDN/conv/MTP/graph/scratch 的资源账本与安全点，不另建与之竞争的 allocator。[S3]
3. 当前模型是 hybrid Flash-Next：QSA KV 只在相关层存在，另有 recurrent GDN/conv 等状态。不能拿 dense 27B 全 attention 层公式直接估128K KV，也不能认为 KV 之外没有长度/窗口相关开销。
4. IQ3_XXS 是包名，真实 expert GU/down 是逐层混合类型。替代权重格式要重新 inventory、hash、converter、实际 bpw 和 CPU/GPU kernel；不把文件扩展名当量化格式。
5. 4090 是 Ada，不支持 Hopper TMA/WGMMA 或 Blackwell `tcgen05`/原生 NVFP4 路径；本机 CPU 有 AVX512-VNNI 不代表 VBMI/AVX-VNNI/AMX。新格式必须有实际可用的本机 decoder/kernel。
6. 6144MiB conversation cache 与4 slots 的实际预算合同按代码和进程日志读取，不能直接乘4；slots 不表示4条并行 decode。全局峰值要同时计旧/新 snapshot 的暂存、pinned buffer、active state 与文件缓存压力。
7. 默认不改模型/KV，所有新格式或新 lease 策略关闭。数值路径为 N；不同权重包与近似淘汰/稀疏是 Q。质量改变后不能用“近期 exact window”称整体无损。

## 2. 当前源码锚

| 文件/符号 | 需保留的合同 |
|---|---|
| `include/strata/core/layer.hpp::QsaState` | KV format、scale、rotation、host/VRAM、elastic、索引和当前位置的完整状态 |
| `src/core/layer.cpp::qsa_set_kv_int8/qsa_set_kv_q4/qsa_set_kv_hybrid/qsa_set_kv_elastic/qsa_kv_resolve` | 实际选格式、分配/增长、host KV 解析；不靠入口 flag 推测实际 residency |
| `src/core/session.cpp` 的 session 分配/清零流程 | GDN/conv/QSA 全部层的空间与生命周期 |
| `src/core/expert_cache.cpp::open_segmented/shrink/grow` | 稳定虚拟地址、分段映射、可回收 expert 容量 |
| `src/kernels/cuda/kv_q8.cu`、`kv_q4.cu`、`kv_stream.cu` | 编码/解码、旋转与流式 copy 的实际 kernel |
| `src/kernels/cuda/qsa_decode_attn.cu::attn_kv_mode` 与 decode 入口 | int8/q4/k8v4 路径、分段 softmax、query/row scratch |
| `src/core/conversation_snapshot.cpp::conversation_kv_save/validate/restore/restore_prefix/part_sizes` | 格式、范围、索引、scale、resident rebuild 的事务一致性 |
| `src/core/conversation_memory.cpp::sample_host_memory` | host available/cgroup 限制；RAM预算不能只看物理64GB |
| `src/core/mtp.cpp::MtpDrafter::load` | target KV 与 draft KV 可能不同；例如 hybrid target 的 drafter 仍走 plain int8 的现有处理 |

来源固定 [S1]–[S7]。修改新 codec 必须检查所有这些 consumer，不只改 decode kernel。

## 3. 先测资源账本与下界

**拟新增** `MemoryBudgetLedger` 按 owner 记录 `requested/reserved/mapped/live/peak/reclaimable bytes`、分配设备、generation、允许释放的安全点与 graph 引用数。至少覆盖：dense/专家权重、GPU热专家、active target KV、draft KV、GDN/conv、verify/草稿 checkpoint、图私有内存、prefill scratch、attention scratch、resident staging、会话 snapshot 和恢复临时副本。

VRAM 账本与 CUDA/NVML high-water 差额单列 driver/library/allocator 未归因值，不强行令二者相等。RAM 同时测 RSS、PSS（可得时）、locked/pinned、匿名/file-backed、cgroup limit/available、major faults、swap 与 page cache；连续峰值比单个 `nvidia-smi` 截图有意义。

场景包括 startup→短请求→32K→64K→合法近128K；长 prefill；spec 最大合法窗口；会话 A→B→A恢复；取消后再请求；restore 与必要 expert copy 重叠。每个长度包括固定输出预算与模板余量，不以131072 token prompt 加输出冒充128K配置。

实际 KV bytes 用 tensor shape、scale、metadata、padding、recent high-precision tier 和选中层数计算，并与分配器实测对齐。若 host-KV 对本轮要搬 B 字节，理想下界至少 `B / measured_effective_PCIe_bandwidth`，且 DDR copy 与 CPU expert 竞争；不能用厂商 PCIe理论值估“可隐藏全部”。

## 4. 拟新增接口与开关

| 拟新增项 | 默认与合同 |
|---|---|
| `MemoryLease {owner, generation, bytes, readers, release_event}` | 不拥有活跃地址的对象不能回收该地址；graph 引用是 live reader |
| `BudgetDecision {admit, reclaim_plan, fallback, reason}` | all-or-none admission；先算完整峰值，失败不留下半迁移状态 |
| `STRATA_LAB_MEMORY_LEDGER` | 默认0，采样和高水位日志，不在每次kernel分配/计时 |
| `STRATA_LAB_MEMORY_POLICY=baseline|shadow|lease` | 默认baseline；shadow只给建议，不实际缩缓存 |
| `STRATA_LAB_KV_CODEC` | 默认baseline；实验值只在完成格式注册、snapshot和kernel资格后暴露 |
| `STRATA_LAB_KV_HISTORY_BITS / RECENT_CELLS` | 拟议研究参数，不是main现成CLI；显式绑定codec版本 |

已有 `--kv`、`--kv-resident`、`--kv-grow` 原样记录，不重复增设同义 CLI。PR #4068 的选项只在候选 PR 所定义的 head 中有效，移植前不能进入可运行配置模板。

## 5. 任务清单

### P08-01 — 资源账本与当前路径资格

- [ ] 在现有分配和 grow/shrink 路径收集 ledger，标明 CPU/GPU ownership 与 transient double allocation。
- [ ] 核对当前 `kv_mode/kv_format/resident_cells/max_cells/elastic`、实际 graph 集和 draft 格式；记录源码路径命中，而不是猜测128K会自动host offload。
- [ ] 对现有 int8 做 snapshot save→restore→next-token reference，验证 ledger 观测不改变输出。

**验收：** 解释主要内存峰值与可回收区；区分 reserves 与 live bytes。**Stop：** 当前未发生预算浪费或压力，O44只保留观测，不自动实施大allocator重构。

### P08-02 — O44：已有 elastic KV/cache 之上的统一 lease

- [ ] 先列现有 `--kv-grow` 已处理的交还/增长流程；只给尚未统一的 graph、MTP、prefill scratch 和 snapshot transient 增加账本。
- [ ] `admit()` 先验证最坏所需容量和可释放对象，形成 all-or-none plan；已在 capture 或 kernel 使用的地址不能被 remap/recycle。
- [ ] 在 request/window 安全点执行 lease 变化，copy完成/event/reader退出后释放；capture 后固定地址，失败回滚旧映射和 metadata。
- [ ] 对扩大 lookup 图或新KV精度，报告新增/释放bytes造成的实际expert槽位改变，接P03成本，而不是把省显存单独当吞吐提升。

**测试：** 恰好可容纳/差一页；分配中途失败；grow与restore同轮；图引用保留；返回旧budget；整数溢出；resident blob比slot大；取消后读者退出。**Stop：** 稳定地址合同无法证明、VMM/管理费用超过收益、没有真实浪费。不得回收live映射来追求高利用率。

### P08-03 — O46/O48：现有4bit与 PR4068 exact-cell窗口

- [ ] 首先对已有 q4_0/k8v4 与当前int8做单独资格；它们改变有效数值，不能复用int8质量结论。[S1][S4]
- [ ] 审阅 PR #4068 固定 head `6c3bd96972c435476d0614035d060deb8c46768c` 的 q4lm8v exact-cell window；逐文件重接当前main。作者/CI若只覆盖HIP，CUDA12.3/sm89仍为待测。[P1]
- [ ] 完整注册 format identity：K/V码流、scale、旋转、recent tier、head_dim/page/block、版本与校准hash。snapshot/恢复/前缀恢复不能靠旧format编号误读新布局。
- [ ] 最近窗口跨界时按明确时点把cell转入历史编码；spec拒绝的未提交cell不可永久污染recent/history；window/ring位置与接受前缀原子更新。
- [ ] 对每种格式报告actual bytes、codec时间、attention时间、expert cache增加、整体wall与质量，分别归因。

**数值测试：** 零/常量/outlier/非对齐维度/scale极值、NaN策略；编码/解码reference；长轨迹logits、GDN漂移和router变化。**状态测试：** window-1/window/window+1、page/ring wrap、accept0/partial/all、restore后跨界、prefix截断后续写。**质量：** Java编译/测试、工具schema、首中尾检索、跨文件/长期记忆；不能只用perplexity。

**Stop：** 解码更慢、window/meta/copy吞掉节省；128K质量门失败；源码仅HIP通而CUDA无对应实现。近期cell局部精确不等于全历史或整模型精确。

### P08-04 — O47：K/V非对称与旋转的真实增量

- [ ] 先标记main已有 rotated Q4_0、k8v4 和int8 rotation，不把它们算新算法。
- [ ] 新假设可为K按channel/V按token、不同bit数或不同group；从Flash-Next实际QSA激活统计校准。KIVI提出的结构是研究依据，dense模型结果不能证明这里的质量。[D1]
- [ ] 验证Q/K旋转一致性、V与输出逆变换、RoPE相对次序和scale生命周期。K相对int8保持同编码只能说明局部score路径，早层V误差仍会改变后续Q/K与整模型输出。
- [ ] 如参考HyperQwen KVarN，先隔离draft/verify读取的表示和生命周期，不能忽视其公开文档对shared verify配置的禁用与异常观察。[D2]
- [ ] 只有本机支持的sm89/CUDA12.3实现才进性能轮；不用Hopper/Blackwell专用内核占位。

**测试：** rotation往返、不同query、所有attention入口、draft与target共存、长context误差累积、校准集与holdout隔离。**Stop：** transform开销/误差放大、低位宽需要不可用ISA、只在校准数据上有利。

### P08-05 — O49：已有host-KV streaming的块化和双缓冲

- [ ] 先确认生产是否实际启用`--kv-resident`且context超过resident范围；全GPU场景没有此方向的直接收益。[S1]
- [ ] 审阅`qsa_kv_resolve`、`kv_stream.cu`已有映射/搬运，测每轮必要访问块与真实copybytes，优化缺失部分，避免重造streaming。
- [ ] 若存在重复或过大的copy，候选将所需页合并为有界span，复用pinned/staging buffer与event，在已知合法索引后提交。
- [ ] 双缓冲必须阻止consumer读未完成页，cancel不能释放DMA中的内存；与P11共享copy配额，active KV/必要expert优先于预测和checkpoint。

**测试：** 非连续页、重复页、空选择、最后残页、长context、source/destination alias、延迟copy、取消、restore；E路径要求解码后字节/相同算术输出一致。改变分段求和则N。

**Stop：** 全GPU驻留、PCIe实际字节下界已接近、DDR竞争抵消overlap或多搬无用块。冷snapshot从SSD恢复不属于本任务的active KV优化。

### P08-06 — O50：分页计划复用与正确的softmax合并

- [ ] 先测现有layout/plan构造占比和同prefix多query的真实重复读机会。单请求没有重复机会就不引入multi-level cache。
- [ ] 缓存只依赖稳定shape、page table/version、设备/format和workspace的plan；page mapping或dtype改变后必须失效。
- [ ] 分段attention对同一query保存 `(m,l,o)` 或LSE和归一化输出，按log-sum-exp权重合并。不同query有不同score，不能共享前一query的最终prefix输出/LSE；可共享的是KV/layout或联合kernel读。[D3]
- [ ] 空段/allmask给明确定义，不能形成`-inf - -inf` NaN；非连续选择保留合法mask和position。

**测试：** 单段vs多段reference、段顺序/大小、空段、allmask、不同query、重复/无效page、prefix编辑、snapshot恢复、长context。**Stop：** 当前tile已实现重复读消除、merge开销大于节省、需要近似筛KV才有效（转P10 Q轨）。FlashInfer当前工具链要求与本机不一，先移植算法/小kernel，不能直接声称最新wheel在CUDA12.3可用。[D4]

### P08-07 — O52/O53：替代权重包与敏感度混合精度

- [ ] 每个候选建立独立model identity：原始checkpoint、convertercommit、每tensordtype/shape/scale、真实bpw、文件hash、许可和完整tensorinventory。
- [ ] 先验证loader/kernel覆盖实际GU/down/embedding/head/GDN/QSA类型。TQ3/TQ4或EXL3是独立格式，不可把当前GGUF改label即用。[D5][D6]
- [ ] 测CPU/GPUdecode每种格式和nt；先修正确Q2_0 pool调用路径。没有VBMI/AMX的4216不能套用另一机器的吞吐。
- [ ] 混合精度先用校准集测layer/expert敏感度，固定预算与选择，再完全冻结后进holdout。高路由频率与高数值敏感度不是同一指标，两者分别记录。
- [ ] 比较文件更小、host resident更多、GPU slots更多、decoder变慢和质量的净效应；所有权重变化列Q，单独model baseline，禁止并入“当前模型无损优化”数字。

**测试：** 每tensor读取和conversionreference、zero/outlier、fulltrajectory、实际Java/tool任务、长context与多轮、restore身份不匹配拒绝。**Stop：** 小文件但慢kernel、缺某类量化实现、校准过拟合、质量门失败或模型许可不允许拟议转换/分发。P10管理这些研究的资格与Pareto呈现。

### P08-08 — 端到端判定与rollback

- [ ] E/N/Q分轨报告；新codec的内核快不代表模型wall快，省KV产生的expert容量收益按组合实测。
- [ ] 采用预注册配对macroblock和任务失败处理；性能正式轮关闭重日志。固定arm除声明的codec/budget变量之外所有参数。
- [ ] 回退同时恢复binary、格式、weights、配置与snapshot命名空间。旧快照只在identity完全匹配时恢复，不能把新格式内容交旧decoder。
- [ ] 任何OOM、UAF、地址悬空、错误恢复、nonfinite或质量门失败立刻停止扩测；当预算策略无收益时退回已有grow/cache行为。

## 6. 验证目标与交付

main已有相关CMake targets：`kv_q8_parity`、`kv_q4_parity`、`kv_hybrid_parity`、`kv_stream_parity`、`kv_window_parity`、`kv_steps_parity`、`qsa_parity`、`qsa_slots_parity`、`conversation_snapshot_test`、`conversation_validation_test`、`expert_cache_segmented_test`。先核对当前配置`ctest -N`和模型/GPU要求；HIP-only target不能作为CUDA验证证据。[S8]

拟新增：`tests/core/memory_lease_test.cpp`（all-or-none、失败回滚、live readers）；`tests/core/kv_codec_snapshot_test.cpp`（format/version/tier）；`tests/core/kv_recent_window_test.cpp`（window/wrap/spec拒绝）；`tests/core/weight_format_inventory_test.cpp`（只有引入新格式才需要）。新增名字不是可直接调用的现成target。

交付至少包含资源账本与峰值、现有能力核对表、codec规格/布局图、snapshot版本、raw测试结果、预注册holdout、性能质量Pareto、回退数据兼容规则。局部精度结果、上游测试、估算与本机实测分别标记；无本机GPU数据时保留“待测”。

## 7. 固定来源

[S1]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/program/generate.cpp
[S2]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/layer.hpp
[S3]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_cache.cpp
[S4]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/qsa_decode_attn.cu
[S5]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_snapshot.cpp
[S6]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/layer.cpp
[S7]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/mtp.cpp
[S8]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt
[P1]: https://github.com/Niko1221/Strata/commit/6c3bd96972c435476d0614035d060deb8c46768c
[D1]: https://proceedings.mlr.press/v235/liu24bz.html
[D2]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/kvarn/README.md
[D3]: https://github.com/flashinfer-ai/flashinfer/blob/847172573ad1d5a929a8e7fb67aa7c072f8f7dcb/flashinfer/cascade.py
[D4]: https://github.com/flashinfer-ai/flashinfer/blob/847172573ad1d5a929a8e7fb67aa7c072f8f7dcb/README.md
[D5]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/docs/reference/formats.md
[D6]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/README.md

FlashInfer/HyperQwen/tqLLM实质copy按固定SHA的Apache-2.0 LICENSE/NOTICE处理，ExLlamaV3按MIT保留版权；仅用机制独立实现无需将无关整个框架引入。SGLang HiCache 的[分层存储设计](https://github.com/sgl-project/sglang/blob/a99c7d050faee00b104a0b861df2d394ded74eb6/docs/docs/advanced_features/hicache_design.mdx)可参考layout/批量搬运，但host prefix cache与active host-KV是不同路径，TMA实现不直接用于Ada。

### Kern pool的准确借鉴边界

Kern固定ff88b4f的`kern-pool`已把paged state与per-sequence state纳入同一physical-chunk预算，以Lease持有，并可将空闲page/slot的backing经VMM remap互转。draft/MTP只有在manifest声明为这些state时才参与；活跃lease不会被抢占。pool在host产出Copies/Remap，runtime执行CUDA动作。它**不是**覆盖expert weight/cache、CUDA graph、通用scratch的全局动态预算器。本计划借鉴显式状态所有权和映射合同，跨上述资源的统一lease是Strata上需另行设计的工作。

来源：[Kern pages.rs](https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/crates/kern-pool/src/pages.rs#L1-L70)、[chunks.rs](https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/crates/kern-pool/src/chunks.rs#L1-L23)。
