# Strata / 4090 / Flash-Next：可移植优化研究与退出条件

检索冻结日期：2026-10-25 UTC。本文是源码与论文研究，不包含本轮机器实测。Strata 基准源码为 `41cf05a06a25dd29103b7b27a2279a3f60c21876`，engine `0.1.50`；生产已迁移到 `v0.2.3`，P0 已完成。候选优化必须接在现有基线和已完成的消融之后，不能把重新打开已有开关写成新成果。

执行基线最终刷新到4b9e05a2（v0.2.6）；本文41cf固定引用处相关核心无变化。**已有/新增边界以[校正表](10_EXISTING_VS_NEW.md)和实施计划为准。**

## 1. 先固定决定移植价值的事实

- **目标模型不是 Qwen3.8-27B dense。** 是 Qwen3.8-Flash-Next，GSQ-RCO `IQ3_XXS` 包；混合注意力、MoE 专家和状态布局必须取自目标模型。包名不能代替 tensor inventory：附件 NP0 的 CPU 专家偶数层是 `IQ2_XS gate/up + IQ4_NL down`，约 1.87 MB/专家；奇数层是 `IQ2_XXS + Q2_0`，约 1.31 MB/专家。dense 27B 的 lm_head、GDN 状态尺寸、MTP drafter 和 attention 形状均不能直接移植。[LOCAL-NP0]
- **CPU 与 RAM 是强约束。** Xeon Silver 4216，16C/32T，2×32 GB DDR4，附件只读带宽约 36 GB/s；有 AVX512-VNNI，无 VBMI。当前 Strata `cpu_avx512_ok()`要求 VBMI，现有 `iq_avx512.cpp` 整个编译单元还启用 VBMI/VPOPCNTDQ；不能删掉 CPUID 条件强行执行。`iq_avx2.cpp` 的 AVX-VNNI 分支也不是 Cascade Lake 的 AVX512-VNNI。[ST-ISA][ST-CMAKE][ST-IQ256]
- **先修测量入口，再决定新内核。** NP0 偶数层 nt=1 达 35.3 GB/s，已接近所测带宽；nt=2/4 为 27.8/20.2 GB/s。NP0 奇数层 Q2_0 微基准原来走错 `native_down_rows`，实际 pool 走 `q2_rows_any`；已做的 NP-1a 只有微基准好看，整机无收益。PR3871 修正对应测量路径是后续无 VBMI 内核研究的前置，不得引用那两行旧 Q2_0 数字估算生产收益。[LOCAL-NP0]
- **配置语义保持精确。** 上限 131072、KV int8、`--spec 4 --spec-min-p 0.5`、conversation cache 6144 MiB 与 4 slots。`spec-min-p` 是 draft proposal 概率阈值；不等同请求采样参数 `min_p`。也不自行把 6144 MiB 与 slots 相乘推算 RAM。[LOCAL-ENV][ST-SAMPLER]
- **64 GB 不能当额外显存。** 同时存在冷专家权重、CPU 活跃 KV、会话快照、pinned staging、page cache、容器和 allocator 保留。prefix/continuation offload 是把已停用状态存 RAM、恢复后计算；active KV streaming 是生成每一步仍须访问 RAM；CPU expert execution 是 CPU 真正计算 miss。三者需分别建预算。[TQ-KV][N-CACHE][S-HICACHE][EX-CPUCACHE]
- **现有 P0 改变优先级。** 附件已显示 graph 后 GPU 真正空闲约 1.2%，不能再把“换 Rust”“少几个 launch”“整模型 megakernel”排在 CPU pool 临界路径之前。带 tracing 的约 20–23 ms/window 不能和无 tracing 的约 16.4 ms/window 混算。[LOCAL-NP0]

本文标记：`E0` 为要求位级一致的布局/调度变更；`E1` 为数学语义一致但可能改变浮点求和、量化边界或 verify 形状，须数值与任务门禁；`Q` 为明确改变目标模型计算/精度的实验。`P1` 是本机证据支持的下一轮；`P2` 是发现对应瓶颈后再做；`P3` 是研究方向。成本“小/中/大”描述改动和验证范围，不是工期承诺。

## 2. donor 快照与适配结论

所有 SHA 均于本轮通过 GitHub commit API 重核。`llama.cpp` 已从旧笔记 `1a0b56…` 前进，不能继续称其为当天最新。论文只有论文链接时，不虚构代码仓库或 SHA。

| donor | 本轮固定 SHA / 提交日期 UTC | 对这台机器的主要价值 | 不应照搬的部分 |
|---|---|---|---|
| tqLLM | `c2163c2da408603331a5814f62fd1f287f54370b` / 10-22 | Flash-Next CPU miss pool、分层专家缓存、layer-major prefill、active KV 管理 | 自有 TQ3/TQ4 格式不等于现有 GSQ-RCO，量化不可无损替换 |
| HyperQwen | `ce9615c4f2309be727407918a6c979bd67968069` / 10-21 | 小 query 多 token verify split-KV、int8 KV、草稿 head 缩减、内存预算 | pinned vLLM 0.31.0 patch 不是 Strata patch；主要是 dense 27B/3090 数据 |
| NInfer-4090 | `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923` / 09-30，`b0-scanner` | sm89 attention、ReplaySSM、完整 continuation 合约 | 27B tensor geometry、`.ninfer` 权重、E8 KV 不兼容现有 pack |
| FLARE | `bce032c014bae34502ba22d3304fa084d5b40afe` / 10-25 | checkpoint/state 合约、CPU 调度与已排队 graph 重叠 | 官方面向 SM120/121；NVFP4 recipe 不能在 SM89 原样跑 |
| Kern | `ff88b4f24e3a455491af02bedb1639bde6a56b88` / 10-20 | 明确 kernel ABI、buffer/state 生命周期、逐形状验证与打包 | `kern-qwen38-sm103` cubin 不能用于 4090；换 runtime 本身没有速度承诺 |
| EAGLE-4 | `60bab6b469e795d47bda82b16243b82bb7b6206f` / 10-24 | 按实测成本决定 draft 深度/verify 宽度、draft head 思路 | **source-available 非 OSI 开源**；核心源码不可作为普通 Apache donor 直接搬；训练好的 27B draft 非 Flash-Next draft |
| ExLlamaV3 | `da68d57de61781e5b74ad68698ac4caf36408d7a` / 10-20，1.6.4 | CPU/GPU handoff、host affinity、CPU page cache | EXL3/QTIP 权重编码、自己的 recurrent cache ABI |
| llama.cpp | `2280f0fd163b03d4331d49e08460f66502e35854` / 10-25 | GGUF 精确格式参考、x86 VNNI 分支、quantized attention | 不能假定上游 single-token vec_dot 等于 Strata multi-token pool 的实际路径 |
| Mirage MPK | `63af900000d8928a885f7af7889a3448621e18a9` / 10-22，`mpk` | 局部 persistent task graph、跨算子软件流水 | Blackwell task/TMA/tcgen05；整个 MPK 不自动解决 CPU experts、低 bit pack、128K 状态 |
| KTransformers | `a694e718e8b3ec2e221277d674e369f3be38d2a4` / 10-19 | CPU 异步队列、NUMA/pool、AVX 分支 | AMX 不适用于 4216；Expert Deferral 有质量变化 |
| Fiddler | `227715bfd6e8c731b29548eab01d9919c4fe9564` / 2024-04-28；另读 ICLR 2025 论文 | 小批量在 CPU 原位算专家、大批量搬专家到 GPU 的成本模型 | 公开原型围绕 Mixtral 8 专家，枚举 `2^E`，不能搬成 Flash-Next 通用调度器 |
| HybriMoE | `508a85b9a43dff37124370d8816e411e74827803` / 2025-12-15 | score-aware cache、混合调度、prefetch 接口 | 老 KTransformers/DeepSeek/Mixtral 的阈值和模型类 |
| PowerInfer | `8bd56d69906c9d2dba4d3bf6899763401e01a9a4` / 2026-05-11；现仓库 Tiiny-AI/PowerInfer | 热/冷工作集分配思想 | ReLU/预测神经元稀疏性非 Flash-Next 原生 MoE 稀疏性；漏算神经元不是无损调度 |
| FlashAttention | `98c1cee0ed59307833841cdbf567fe336ceec13a` / 10-24 | FA2 的 Ada tiling、online softmax、序列并行 | FA3 Hopper，FA4 Hopper/Blackwell；CUDA 版本达标不等于硬件支持 |
| FlashInfer | `847172573ad1d5a929a8e7fb67aa7c072f8f7dcb` / 10-25 | 可复用 plan、paged decode、cascade merge、Ada 适用路径 | README 支持 CUDA 12.9/13.0/13.4；若本机 nvcc 真是12.3，不能直接引最新整套 wheel |
| SGLang | `a99c7d050faee00b104a0b861df2d394ded74eb6` / 10-25 | HiCache transfer/layout、GDN exact fold | TMA I/O kernel、NVFP4、集群 L3/PD 拆分对单机未必有价值 |
| DALI | arXiv `2602.03495v1` / 2026-02-03 | greedy CPU/GPU assignment、残差预测 prefetch、workload-aware cache | 本轮未确认官方代码仓库；论文重实现，不能照抄实验加速比 |
| ScheInfer | arXiv `2411.15715v1` / 2024-11-24 | CC/CG/GG 三路张量分配、token assignment | 本轮未确认官方代码仓库；dense 切片方案和专家级分配不是同一粒度 |

上述版本和架构定位的直接来源：[TQ-ARCH][H-OPT][N-README][F-README][K-REG][E4-ARCH][EX-README][LL-README][MPK-README][KT-README][FI-README][FA-README][DALI][SCHE]。

## 3. 建议首先进入实验卡的 8 项

1. **CPU pool 按真实 expert/nt/dtype 的任务粒度与等待策略**：以 NP0 已确认的小工作量、高分发/汇合频率为依据，优先于新增向量指令。
2. **修正奇数层 Q2_0 的微基准路径**：对应 PR3871，随后才允许评估 no-VBMI VNNI；这是测量基础，不计为生产速度优化。
3. **专家缓存按“节省的关键路径时间/字节”评分**：比单纯 hit rate 更适合偶奇层格式/大小不同的实际 pack。
4. **当前 spec=4 周围的低开销成本控制器**：保留生产最优已知阈值，先做离线 trace replay，观察长上下文/高 miss 时是否应缩短。
5. **小 query verify 的 split-KV/共享读取**：只针对 Strata 当前 trace 中确实存在的 attention 部分；不能把 dense 27B 的收益覆盖到所有 Flash-Next 层。
6. **CPU/GPU/H2D 三资源竞争的动态专家分配**：利用真实 PCIe 和 DDR4 成本，给已有 adaptive tier 增加成本约束，不能重复发明现有 CPU-miss 策略。
7. **会话状态 cache 的有界内存与恢复契约**：把现有 6144 MiB/4 slots、allocator 释放问题与新 cache 方案一起验证；不能为追求 cache hit 挤掉活跃状态。
8. **只有确认 rollback/state traffic 占比后，才做 exact ReplaySSM**：NInfer 与 SGLang 有可检查实现；空间压缩比不是速度提升比。

## 4. 具体移植清单：CPU、专家与数据搬运

### D01 — CPU pool 自适应任务粒度、保留 host 核心

**P1 / E0–E1 / 中；Flash-Next 直接相关，dense 27B 仅 CPU offload 时相关。** ExLlamaV3 `default_worker_threads`、`plan_host_cpus` 与 `exl3_moe_cpu_worker_run`，tqLLM `CpuMissPool::{start,work,run}`提供可读实现；KTransformers `CPUInfer::{submit_with_cuda_stream,sync_with_cuda_stream}`提供异步任务接口。[EX-AFF][EX-HANDOFF][TQ-CPU][KT-CPU]

移植重点是每层少量 miss 时避免把小矩阵拆成过多任务：比较 expert 级、行块级以及按估算工作量切换；为调度/I/O 留出核心。Strata 已有 pool/affinity，不重做整个框架。真实专家块和 nt=1/2/4/5 的形状必须来自 pool trace。

验证：4/8/12/15 workers、仅物理核与 SMT、固定 affinity 的配对实验；记录 wall ms/window、CPU active/wait、GPU wait flag、接受 token 数和内存读带宽。**退出：**只改善合成 CPU bench、不降低端到端 critical path；或减少线程后 miss 尾延迟抵消同步节省。不得从“16C/32T”推出32线程更快。

### D02 — 无 VBMI 的 AVX512-VNNI 小内核，按实际 dtype 做

**P2，先修 PR3871 / E1 / 中；dense/MoE 的对应 CPU 量化 GEMV 通用。** llama.cpp x86 `mul_sum_us8_pairs_float`明确把 `AVX512VNNI && AVX512VL` 与 `AVXVNNI`分开；可借用 nibble/codebook unpack + dot 的结构。参考 `ggml_vec_dot_iq2_xxs_q8_K`、`ggml_vec_dot_iq2_xs_q8_K`、`ggml_vec_dot_iq4_nl_q8_0`和 `ggml_vec_dot_q2_0_q8_0`，先覆盖真实偶奇层格式。[LL-X86]

单独编译 TU，特性白名单为实测 CPUID；不能让编译器在其它代码生成 VBMI/VPOPCNTDQ。保持当前 activation quantizer、整数溢出约束、scale、saturation 以及累加顺序的明确契约。256-bit EVEX VNNI 和512-bit方案都可测，不必强制更宽寄存器。

验证：反汇编、4216真机非法指令/数值门禁、冷/热 cache、多 nt、真实 pool callsite。**退出：**偶数层 nt1 已接近36GB/s而整机无提升；奇数层纠正后也饱和；AVX512频率降低抵消吞吐。现阶段不把它排在 D01 之前。[LOCAL-NP0]

### D03 — 多 token 共享解包与 activation quantization

**P1–P2 / E1 / 中；MoE verify 尤其相关。** tqLLM `cpu_dot_iq4nl_q8_mc`将一块权重解码供多个 activation 使用，`CpuMissPool::Job`携带 token columns；Strata 现有 native multi-token 已采用类似思路，新增价值只能来自实际格式、分组/列宽和缓存复用不足处。[TQ-CPU][ST-NATIVE]

按 `(layer, expert, dtype)`聚合一轮 verify 的合法 token，复用解包和预量化 activation，避免重复从 DDR4读取同一专家。不得跨有因果依赖的未完成 token擅自合并；route weights 仍逐 token 保留。

验证：统计每个专家真实 nt 分布，而非只测nt4；比较packing成本、重复字节、微基准与窗口收益。**退出：**附件每miss平均约1.31 token意味着多数group很小，额外分组反而更贵；已有multi-token已覆盖；或新group改变舍入导致未过数值/任务门禁。[LOCAL-NP0]

### D04 — 按节省时间/字节而非 hit count 的专家 cache

**P1–P2 / E0–E1 / 中；MoE 专用。** HybriMoE `KScoreAwareCache::{get_expert_to_unload,get_experts_to_prefetch}`、`KExpertsCache::HSS`和tqLLM `MixedExpertCache::{set_layer_slots,set_layer_tiers,regrow,resident}`可作为缓存接口来源；DALI §4给出 workload-aware replacement 思路。[HYB-EXPERT][TQ-CACHE][DALI]

针对不同专家大小，评分近似为“近期预计复用次数 × 避免的CPU/PCIe关键路径时间 ÷ 驻留字节”，加入衰减、迁移成本和最短驻留期；CPU计算已可被GPU完全覆盖时，那个miss未必值得占GPU槽。预算需扣除128K KV、graphs、prefill scratch、MTP与会话恢复余量。

验证：同一routing trace做离线cache模拟，再选少量策略上线实验；同时报 bytes moved、CPU stall、GPU hit/miss、迁移抖动。**退出：**命中率上升但因大专家或频繁换入导致窗口更慢，或回收 expert 空间引入prewarm/recapture抖动。

### D05 — 每 expert 的 CPU 原位算 / 搬到 GPU 算 / 已驻留算三路成本模型

**P2 / E1 / 大；MoE 直接相关，dense需换为矩阵切片。** Fiddler论文、DALI greedy assignment、ScheInfer的CC/CG/GG分解共同支持这一方向，但不能把它们当同一实现。[FIDDLER-PAPER][DALI][SCHE]

从本机测得 `Tcpu(dtype, nt, workers)`、`Tcopy(bytes, outstanding)`和`Tgpu(shape, nt)`，优化实际临界路径；CPU、GPU、DMA重叠时不能把三个计时简单相加。沿用Strata现有adaptive tier，给当前CPU/GPU分配加入预算与滞回；decode低nt和prefill高nt应使用不同模型。

Fiddler公开 `mixtral_forward`是8专家原型，枚举`2^E`，源码cost求和和“max”注释也不一致；只能取成本建模思想。DALI用greedy近似减少求解开销；Flash-Next不能复制指数枚举。[FIDDLER-CODE]

验证：trace replay预测与真实延迟误差、prefill/decode分别比较、触发阈值两侧扫点。**退出：**决策开销高于可省时间；被DRAM/PCIe双向竞争压住；原有adaptive策略已覆盖收益。

### D06 — 已有下一层专家prefetch的预测与预算增量

**P3 / E0–E1 / 大；MoE 专用。** DALI残差信息预测高workload experts；HybriMoE `prefetch_expert`、tqLLM `MixedExpertCache::prefetch_released`提供接口形态。[DALI][HYB-EXPERT][TQ-CACHE]

预测只决定提前拷贝哪些专家。真实router结果仍决定全部要计算的专家；预测错时回退CPU或按需搬运。因此错误prefetch是带宽/槽位损失，不是默认质量损失。不能把“预测不激活”当作跳过真实selected expert的依据。

验证：prefetch precision、recall、useful bytes/total bytes、真实H2D排队、被挤出的热专家；与现有adaptive swap、host KV streaming共用PCIe预算。**退出：**附件已有约18个adaptive迁移/window，新增预取争用使总窗口更慢；低命中或污染热cache；需要修改router/少算专家才能出收益，则移到Q类。

### D07 — layer-major prefill、expert union 与有界 bank 借用

**P2 / E1 / 中–大；Flash-Next donor最直接。** tqLLM `prefill_plan.hpp::{prefill_chunk_bytes,prefill_plan,banks_to_borrow,BankLedger}`显式计算激活、expert IO、双staging、context和workspace，确保scratch释放后才refill expert banks。[TQ-PLAN]

只补Strata现有layer-major/prefill路径尚未覆盖的峰值预算、跨subchunk复用和按需bank释放。将一个chunk内相同专家聚合后GEMM，减少重复搬权重；全prompt layer-major与chunk-major的激活内存差异必须算清。不能照抄donor的“每token多少MB”经验常数。

验证：cold 4K/32K/64K/接近满窗prefill、实际copy bytes、峰值VRAM、prefill后恢复decode热集的成本。**退出：**TTFT收益被bank重热抵消；scratch挤压KV导致有效context下降；已有路径相同。

### D08 — CPU/GPU handoff 用 stream-ordered 信号，减少同步往返

**P2 / E0 / 中。** ExLlamaV3 `exl3_moe_split_issue_fused`、`exl3_moe_split_collect_fused`、`exl3_moe_flag_write/wait`展示了CPU-worker与CUDA stream的交接；KTransformers提供相应异步队列。[EX-HANDOFF][KT-CPU]

Strata已使用wait flags，目标不是再次引入自旋，而是压缩已有handoff次数、合并可合并的metadata、消除不必要device→host→device同步。必须定义release/acquire可见性、epoch/abort、地址生命周期和graph复用规则。

验证：Nsight上的CPU唤醒到GPU恢复时间，真实deadline/取消/错误恢复和长循环。**退出：**profile显示GPU wait主要是CPU实际算专家，此时换信号协议不会消灭等待；轮询还抢占DDR4/CPU资源。系统C-state变更另走用户已规定的权限流程，不混进源码实验。

### D09 — 统一 DRAM/PCIe admission，避免三种 offload互相挤占

**P2 / E0 / 中。** 可借tqLLM memory fit与SGLang cache controller的分层思想，分别计权重、活跃KV和会话快照。单机不需要复制分布式PD/L3部署。[TQ-PLAN][TQ-KV][S-HICACHE]

在copy队列中标明critical active-KV、必要expert miss、低优先级prefetch、后台checkpoint；给后台工作限速并允许取消。CPU experts与pinned copy都读取同一DDR4，不能把PCIe实测带宽与36GB/s当作互不干扰的两个上限。

验证：长上下文同时park/restore的最坏条件，报peak RSS、MemAvailable、PCIe队列、window p95。**退出：**实际业务没有并发后台copy；限速让restore更慢却没有改善decode；复用现有控制就已满足目标。

## 5. 具体移植清单：注意力、KV与长上下文

### D10 — 针对 q=2–5 verify 的 split-KV 与 query tile autotune

**P2 / E1 / 中；dense27B和Flash-Next中实际full-attention路径可用，不能替代GDN/QSA本身。** HyperQwen `SpecDecodeAttention::{_plan,run}`、`_spec_attn_partial`和`_spec_attn_combine`通过KV分段和query-row tile增加SM并行度；donor明确extra query tile会重复读KV。[H-SPLIT]

Strata已含CHUNK=64分段及可选int8 TensorCore split；在sm89上针对模型实际heads/head_dim、KV格式、q长度、有效context选择segment和BLOCK_M；不用3090默认表覆盖4090。现有mask/causal/position/选中KV语义不能丢。scratch一次分配，不能在capture后扩容使graph持有悬空地址。

验证：q=1/2/3/4/5、实际32K/64K/96K/接近128K深度；记录kernel与窗口收益、寄存器spill、重复KV字节。**退出：**目标Flash-Next已不读那段dense KV；reduce/combine成本抵消并行；改块只改善短窗或破坏长窗。

### D11 — 已有int8 KV融合路径的访存增量

**P2 / E1 / 中。** NInfer `gqa_attention_decode_i8_tiled_kernel`、HyperQwen `spec-decode-int8-kv.patch`和llama.cpp `flash_attn_ext_vec`可参考。Strata主线load8_q8已在QK/PV时即时解码，不存在这条“先展开整段”缺口；donor只用于对照packed读取、scale复用与实际访存增量。[N-I8][H-I8][LL-ATTN]

必须适配Strata自己的int8 scale/zero point/page layout，保留现有存储精度；“都叫int8”不代表能直接读同一字节。目标IQ权重量化与KV int8也不是一套codec。

验证：以当前KV字节为固定输入比对attention输出/最终logits；测H2D/显存读流量、临时buffer、full窗口。**退出：**已有内核已经融合；register pressure/spill抵消流量节省；改scale或改FP32 accumulation则需重新分类并过质量门禁。

### D12 — active host-KV 分块stage、双缓冲与下一层预取

**P2 / E0–E1 / 中。** tqLLM `CudaKvMemory::{host_alloc,copy,map,map_phys}`以pinned内存、VMM和异步copy提供分层KV；SGLang文档描述layer N计算时加载N+1的transfer overlap。[TQ-KV][S-HICACHE]

优先移植chunk staging/稳定地址生命周期，不直接依赖新版host-NUMA VMM API。本机CUDA12.3若不支持某API，应保留`cudaHostAlloc`+显式copy退路。对128K已启用的host KV路径，比较tile大小、固定buffer及copy stream优先级；不能宣称把64GB RAM变为零成本显存。

验证：实际accessed KV bytes、有效PCIe带宽、copy/compute overlap、GPU等待、page fault和RSS。**退出：**已经被PCIe真实bytes下界限制且无需更多context；增大pinned预算挤出专家/会话；prefetch抢占必要expert copy。

### D13 — 共享前缀 attention state 的 cascade/online-softmax合并

**P2–P3 / E1 / 中–大。** FlashInfer `merge_state`、`merge_states`、`MultiLevelCascadeAttentionWrapper::{plan,run}`和shared-prefix wrappers把分段softmax状态正确合并。[FI-CASCADE]

移植对象是多个verify query、树节点或真实共享prefix请求对同一KV的重复读取。必须携带每段log-sum-exp及相应加权输出，不能对独立softmax结果简单相加。不同query仍有不同Q和分数；“共享prefix”并不代表可以重用一个query的attention结果。

验证：不等长prefix、全mask/空段、极端logits、多个spec深度和分页边界；衡量减少的全局KV读取与额外merge开销。**退出：**parallel=1且现有kernel已经同tile复用；prefix共享只停留在cache residency而没有实际算子复用机会。

### D14 — FA2式sm89 prefill tiling、online softmax与非GEMM开销削减

**P2 / E1 / 中。** FA2论文与当前README明确支持Ada、CUDA>=12.0；采用序列维并行、合理warp工作分区与减少非matmul操作。[FA2][FA-README]

仅用于目标模型的实际attention算子，保留原生稀疏/混合结构。Ada可用其自己的`mma.sync`、`cp.async`路线；FA3的TMA/WGMMA和FA4/Blackwell专核不是可用指令。长prompt prefill与tiny-q verify分别调参。

验证：TTFT、peak scratch、128K边界、同精度参考输出；单独核对PTX/SASS架构。**退出：**现有kernel已同类融合；总体prefill仅占业务少部分而新增编译/维护成本过高；donor需要更高precision临时KV导致装不下。

### D15 — plan元数据和分页layout复用，避免每步重复构建

**P2 / E0 / 中。** FlashInfer `BatchDecodeWithPagedKVCacheDevice/Dispatched`与cascade `plan/run`分离，为固定容量graph保留可复用metadata；HyperQwen patch显式避免scratch在capture后realloc。[FI-DECODE][FI-CASCADE][H-SPLIT]

缓存按batch/query/context bucket、KV layout和mask能力建立；更新页表内容而不是重建全部对象。Graph键必须包括会改变kernel/stride/容量的参数；context bucket不足时有明确fallback。

验证：decode host CPU time、allocation计数、capture次数，以及cache restore、请求取消后页表有效性。**退出：**Strata C++静态路径已经无这类开销；过多bucket挤占显存或增加冷启动。

## 6. 具体移植清单：投机、草稿与递推状态

### D16 — 已有DraftPolicy的本机成本校准与细化

**P1–P2 / E1 / 中。** EAGLE-4 `CostModel::{verify_cost,tree_width,chain_stop,verify_num_paged}`与calibration文档提供成本感知设计参照；FLARE `round_ceilings`、`proposal_forecast_tokens`、`fixed_round_candidate`也是可复制代码的替代参照。[E4-COST][E4-CAL][F-ROUNDS]

主线DraftPolicy已有context桶、EMA、stale探测和概率校准，先验证现有STRATA_SPEC_COST；不先引入外部drafter。对现有MTP候选深度如0/1/2/4建立context、CPU miss量和内存压力分桶；最大化`committed_target_tokens_including_bonus_and_correction/round_wall_time`，以真实重叠后的wall time作分母。加入滞回/探索预算，避免一两个低接受率窗口导致来回抖动。`spec-min-p=.5`是起点，不是sampling-min_p。

验证：离线trace replay估算机会，再真实对照固定spec4；记录accepted tokens、draft/verify/state关键路径、不同输入类别。**退出：**阈值选择过拟合、trace控制器成本超过收益、上下文分桶后仍无稳定提升。EAGLE核心代码受特别许可，方案需独立实现或选择许可明确的替代实现。[E4-LICENSE]

### D17 — draft-only紧凑词表或低秩候选head

**P2–P3 / E1 / 大。** HyperQwen `qwen3_5-mtp-draft-vocab.patch`保留draft-to-target词表映射；EAGLE-4 `LowRankFactors`、`low_rank_factors`是低秩候选筛选再精确重排的参照。[H-DRAFTVOCAB][E4-HEAD]

只压缩draft head，目标模型head保持现状。Flash-Next tokenizer、MTP输入/hidden state与dense27B不同，不能直接下载27B draft当替换件。缺失草稿词会降低acceptance；在正确目标验证/拒绝采样下不应改变目标分布，但实际有限精度与采样实现仍要验证。

验证：中文/英文/代码/罕见标识符分组的acceptance，draft head时间、净tok/s和草稿显存。**退出：**词表缩减导致acceptance下降超过head节省；需训练新draft而投入超出收益；或词表映射/采样契约无法证实正确。EAGLE实现不直接copy。

### D18 — exact ReplaySSM：checkpoint + raw transition log

**P2 / E0目标，实施需严格数值门禁 / 大。** NInfer `gated_delta_net_replay_record`、`gdn_replay_fold`；SGLang Apache-2.0 `gdn_replayssm_exact_fold_kernel`、`commit_gdn_replayssm_fold_all_layers`提供直接实现参照。[N-REPLAY][N-REPLAY-CODE][S-REPLAY]

verify保留一个committed state与短raw log，接受后只重放accepted prefix，避免每候选token写一份大状态。应存raw pre-normalization k/v及verify所用gate bits，fold沿相同有限精度递推、归一化/运算顺序/写回边界重建；拒绝suffix不可读取。不能只存数学上可重构、但舍入不同的中间结果。

验证：每一轮state与sequential recurrent oracle比较；0接受、全接受、混合拒绝、长循环、prefill接decode、park/restore都测。**退出：**本机state写流量很小；replay算力成本更高；省容量不改变可运行工作负载。NInfer 27B的状态尺寸压缩比不能当Flash-Next或4090速度预测。

### D19 — tree/多token GDN与conv的明确父状态语义

**P3 / E1 / 大。** EAGLE-4架构与 `gdn_tree_recurrent_update`说明每个节点从父节点state继续，conv history也沿祖先更新；可以回到SGLang/Flash-Linear-Attention的许可明确基础实现开发。[E4-ARCH][E4-GDN][S-REPLAY]

先确认目标真的需要tree而非现有chain。并行verify时不能拿线性causal conv或串行state当tree用；commit必须同时选择KV、recurrent state、conv与draft position。128K和24GB下tree节点会额外消耗state/scratch。

验证：每条树路径与逐tokenoracle相同输入对照；siblings不同、重复token、不同接受叶节点、取消。**退出：**额外tree容量挤走热专家、accepted tokens收益小于验证成本；没有兼容的Flash-Next drafter。不要把EAGLE头条“same answers”当无条件位级保证，其架构/FAQ明确记录shape引起的数值分歧。[E4-FAQ]

### D20 — prompt lookup与MTP混合的成本门控

**P2 / E1 / 中。** HyperQwen `dflash2-lookup-drafting.patch`与优化文档解释lookup proposal送入真实目标验证；tqLLM spec文档可用于比较调度形态。[H-LOOKUP][H-OPT][TQ-SPEC]

Strata已经有prompt lookup，不把“支持n-gram”当新优化。新实验只研究命中置信度、候选长度、CPU lookup耗时与MTP选择顺序；对于代码复述/patch应用可能更有价值，自由生成不应强行长proposal。不能为了lookup改目标sampling。

验证：真实Java/agent工作负载与独立自由问答，对照候选长度分布、命中后实际接受率、CPU lookup和verify成本。**退出：**只是重复benchmark占比变大，真实业务无收益；lookup挤占CPU expert线程。

### D21 — 融合accept/commit的小型设备端bookkeeping

**P3，本机已降级 / E0 / 中。** EAGLE-4 `accept_tail.py`、NInfer `speculative_round.cuh`说明可以合并路径接受、索引准备和状态提交的少量launch；FLARE也将round状态更新纳入graph。[E4-ACCEPT][N-ROUND]

只在trace证实CPU/GPU往返或小kernel占关键路径时做；保持停止词、长度上限、bonus token、取消和随机数推进语义。不要把sampler从完整目标分布改成无充分证明的bounded-top-k捷径。

验证：先统计现有launch和host同步开销，再测各种接受长度与EOS。**退出：**NP0显示graph后空闲约1.2%，可省时间小；fusion增加register压力或破坏graph复用。[LOCAL-NP0]

### D22 — 仅量化drafter，保持目标计算不变

**P2–P3 / E1 / 中–大。** HyperQwen的MTP/DFlash2量化工具及其head/int4实验说明draft容量和速度可独立优化。[H-OPT][H-DRAFTQUANT]

将drafter参数与目标参数分开，验证是否共享embedding/head；共享对象不能被“draft-only”转换偷偷改成target量化。重新测acceptance与草稿加载后可供expert/KV的显存，不拿dense27B量化draft直接适配Flash-Next。

验证：同一目标token logits、相同verify语义；量化前后draft质量、接受率、显存与净吞吐。**退出：**接受率下降吞掉计算收益；释放显存没有改善expert/KV容量；需要改target权重则转Q类。

## 7. 具体移植清单：会话状态、执行框架

### D23 — 完整continuation的事务式checkpoint/restore

**P1–P2 / E0 / 中。** FLARE `PreparedStateTransfer::{prepare,validate,apply}`检查source/destination、epoch、范围及alias；NInfer continuation cache文档定义完整state；ExLlamaV3 `CPUPageCache::{store,begin_promote,fetch}`保留异步copy有效期。[F-STATE][N-CACHE][EX-CPUCACHE]

对Strata快照建立同一committed token边界上的状态集合：attention KV、GDN/conv、draft state、位置、tokenizer/template/model/quant标识、必要sampler状态。source在copy完成前保持不可变，恢复失败应回到明确可重算状态；cache key不能只有文本hash。

验证：A→B→A、部分命中、cache eviction、取消中checkpoint、被拒绝spec suffix、128K状态恢复后的后续token/state一致性。**退出：**目标只是降低ms/window而业务几乎不恢复；现有PR已完整解决，不重复移植。

### D24 — 有界CPU prefix cache与page-first-direct搬运

**P2 / E0–E1 / 中。** SGLang HiCache将GPU L1、instance CPU L2和可选L3分开；page-first-direct把同page同layer的tokens聚合传输。ExLlamaV3 CPUPageCache提供pinned slab与busy/eviction状态机。[S-HICACHE][EX-CPUCACHE]

本机优先固定RAM上限、批量copy和明确释放；不复制跨机器L3。与现有会话cache/host KV合并预算，避免重复保存同一段；停用active context的page才可作为prefix tier处理。不要把HiCache解释为CPU直接执行每token attention。

验证：真实多轮复用率、TTFT、park/restore总bytes、冷热page错误复用、驱逐后RSS/MemAvailable回落。**退出：**缓存增加RSS导致parking被拒或影响专家/active KV；源已在当前Strata PR中实现。TMA版本I/O kernel不适用于Ada，优先显式copy/普通CUDA kernel。

### D25 — CPU调度ahead-of-time，与已排队graph重叠

**P3 / E0–E1 / 中–大。** FLARE当前HEAD提交就是CPU scheduling与queued generation graphs重叠，其`helios/src/scheduler/rounds.rs`可供策略/状态边界参考。[F-ROUNDS]

前提是下一轮可准备的数据已经稳定；依赖本轮accepted length的决策不能未经同步就使用错误值。可以先准备独立metadata、资源预约和候选shape，用epoch防止过期结果写回。单用户C++路径原本host开销很低时收益有限。

验证：host scheduler占用与GPU critical path的实际overlap、请求取消、空队列、动态context。**退出：**空闲占比低、CPU expert才是关键路径；新增lookahead多占buffers/图导致得不偿失。

### D26 — Kern式ABI/状态manifest用于内核移植门禁

**P2作为开发基础，非生产加速承诺 / E0 / 中。** Kern `crates/kern-runtime/src/compile.rs::CompiledProgram`、`exec.rs`的capture/执行边界以及registry按内容hash记录cubin和license，是可借鉴的可审计单元。[K-COMPILE][K-EXEC][K-REG]

给每个sm89移植核写清参数ABI、dtype/pack、stride、alignment、scratch、stream、读写state、shape上限及fallback；建立oracle输入输出和kernel/端到端两层bench。可以在Strata现有C++里做同等轻量manifest，不必迁移Rust运行时。

验证：任何换kernel必须通过该shape集合；旧cubin/新layout组合应明确拒绝。**退出：**为了manifest重写整个server；只有框架形式变化没有可度量开发/验证收益。`sm103`artifact不是4090可执行物。

### D27 — MPK局部persistent region，而非整模型替换

**P3 / E1 / 大；当前不排近期。** Mirage `persistent_kernel.cuh`、`runtime_header.h`和`tasks/ampere`说明persistent task调度与Ampere任务族存在；不能据此宣布Flash-Next完整sm89包已验证。[MPK-KERNEL][MPK-RUNTIME][MPK-AMPERE][MPK-PAPER]

若未来trace显示同GPU连续小算子有足够launch/中间流量，再把一个稳定region做persistent kernel。CPU expert handoff、host KV streaming和动态page状态会打断完整GPU驻留假设。优先试norm/router/固定shape局部，不先做整token megakernel。

验证：相同算术/布局oracle、SM占用/寄存器和与copy engine/其它kernel共存；比较CUDA Graph基线。**退出：**现有graph已消除launch间隙；persistent worker占SM使实际GEMM/attention更慢。TMA/WGMMA/tcgen05/Blackwell cluster实现不可用于sm89。

## 8. 必须独立列出的质量变更实验

以下方案不能进入“同等模型、同等质量的纯系统优化”排行榜。通过少量needle或一份perplexity数据不等于Flash-Next/GSQ-RCO/128K全部任务保真。

### Q01 — TQ/EXL3或其它权重重新量化

**P3 / Q / 大。** tqLLM TQ3/TQ4是自有旋转和打包，GGUF type301/300，不等于Strata当前pack。ExLlamaV3 EXL3/QTIP也有自己的量化、混合精度和算子。[TQ-FMT][EX-README]

收益来自权重容量/带宽与新codec融合核，代价是重新量化和质量分布变化。优先从原始高精度权重生成，不把对已有低bit pack再量化称“无损”。需要实际tensor清单、CPU/GPU双端codec和热专家驻留收益评估。**退出：**同质量点权重/CPU解码成本没有优势，或CPU miss开销变大；实验不修改生产pack。

### Q02 — E8/旋转4-bit KV

**P3 / Q / 大。** NInfer的`gqa_attention_decode_i8_tiled_kernel`包含packed/rotate/E8分支，KV helper负责旋转、pack和scale。sm89实现可参考，但格式与Strata int8完全不同。[N-I8][N-KVQUANT]

收益可能是将更多active KV保留GPU、减少PCIe；需要quant-store、prefill/decode、spec、restore全链路同codec。**验证：**多针/多跳/代码细节/长摘要、不同context位置与长生成、量化误差和decode税。**退出：**容量虽增但实际128K任务不需要，或decode/quality退化抵消收益；不得套用NInfer dense27B官方最大context。

### Q03 — KVarN K4V2或KIVI式非对称KV

**P3 / Q / 大。** HyperQwen KVarN port使用Hadamard、variance normalization、128-token tiles、4bit K/2bit V；KIVI提出K按channel、V按token的非对称量化。[H-KVARN][KIVI]

在Strata现有int8上做容量/质量pareto，必须记真实tile、scale、scratch和residual buffer，不只算名义bit数。HyperQwen当前文档明确`KVARN_SHARED_VERIFY=1`默认关闭，存在未隔离的MTP proposal破坏；该variant不作为可部署donor。其3090约100K时decode较FP8更慢的报告说明压缩并非自动提速。[H-KVARN]

**退出：**只让名义context更长但TTFT/decode恶化、任务质量下降、page recycling/spec/restore correctness尚未通过。KIVI原论文模型不是Flash-Next，效果须本机重新验证。

### Q04 — GDN recurrent state fp32→fp16

**P3 / Q / 中–大。** HyperQwen用fp16 state缓解dense27B并发容量；不能假定Flash-Next长递推稳定性相同。[H-OPT]

收益是state容量和读写流量；误差可能跨长生成积累，replay/rollback需保持同dtype。先确认当前Strata state dtype，若已是同格式不再提出重复优化。**退出：**没有容量问题；长状态、低概率token或工具schema退化；仅短prompt perplexity正常不足以通过。

### Q05 — prefill W4A8 / int8 activation与目标embedding/head重定量化

**P3 / Q / 大。** HyperQwen Marlin activation/int8 embedding-head方案主要适用其dense27B量化配置。[H-OPT]

Ada有整数Tensor Core不意味着现有IQ2混合pack可直接变成MarlinW4A8；改activation或目标head精度就是新数值路径。Flash-Next小专家、高路由分散度、CPU分支还需不同处理。**验证：**按prefill/dense/expert分别微bench与任务质量；记录state与expert cache释放的字节。**退出：**转换/解包成本高于GEMM收益；对整机prefill小占比没有价值；负scale/zero-point/量化格式不兼容。

### Q06 — Quest/SnapKV类额外KV筛选或淘汰

**P3 / Q / 大。** Quest按query与KV page min/max估计关键page，仅读top-K；它保留全部KV并不代表attention计算精确。[QUEST]

必须先区分Flash-Next模型原生QSA选择与额外近似筛选。不得在原生稀疏结构上再加裁剪并称same-model系统优化。收益是active-KV流量减少；漏掉远端低显著但重要token可能破坏代码依赖、多跳和后来才出现的查询。**退出：**全量已有原生稀疏，额外选择开销大于收益；长上下文任务退化；只通过single needle不能推到生产。

### Q07 — PowerInfer预测跳算、Expert Deferral、减少selected experts

**P3 / Q / 大。** PowerInfer依赖神经元稀疏和预测；KTransformers论文Expert Deferral明确报告平均accuracy变化。这些与D06“预测错仍计算全部专家”的prefetch不同。[POWER][KT-PAPER]

Flash-Next的router选择是模型语义，selected expert不可因冷、慢或cache miss被省略。若做“少专家”“近零神经元省略”“延迟专家贡献”，必须显式标注模型/计算变更，独立质量阈值和独立配置。**退出：**要牺牲任务成功率才有速度；不能获得可接受的长context/工具调用保真；不作为默认生产路径。

## 9. 实验组织和统一退出规则

完整benchmark门禁以主文档和现有实验包为准。donor研究补充下面六条，防止迁移后只得到一个更快的微基准。

1. **每卡只改一条路径。** 写清目标文件/函数、现有路径、donor参考点、开启条件、关闭条件和fallback。若当前main已有同类实现，先做差异审计。
2. **测生产实际dtype/shape/调用点。** 偶奇专家分开；nt=1/2/4/5按真实频率加权；全ctx容量和实际已填充ctx长度分开。微基准不能绕开真实pool special-case。
3. **先对齐质量契约。** E0检验字节/state；E1用teacher-forced logits/state误差加任务结果，检查near-tie之外分歧；Q用独立质量实验报告。相同随机种子不自动证明相同分布，spec形状改变也可改变浮点舍入。
4. **看critical path而非相加计时。** CPU计算、copy、GPU重叠，三者各减少1ms不等于总省3ms。主指标是每接受token的wall time、TTFT、请求完成时间及p95；accepted tokens变化必须一起报告。
5. **128K预算包括全部状态。** 权重/热专家、KV、GDN/conv、draft KV/state、verify临时区、graphs、prefill scratch、恢复暂存；RAM同样包括pinned副本与allocator保留。任何“fit”不得默默缩ctx、换KV精度或降低并发。
6. **无收益就停止。** 若配对实验区间覆盖无提升、收益只来自改变输出长度/接受token/质量、内存容量改善不对应目标需求、或microbench改善不进入真实路径，标`NO_BENEFIT`。若模型/ISA/layout不满足前提，标`NOT_APPLICABLE`。不要为凑优化数量继续扩大测试。

推荐实验卡字段：`source_sha / source_file / target_file / tensor_inventory / correctness_class / context_filled / spec_depth / workers / cache_budget / kernel_ms / round_wall_ms / accepted_tokens / H2D_bytes / DRAM_bytes或明确估算 / peak_VRAM / peak_RSS / quality / confidence_interval / decision`。

## 10. 实质代码移植时的许可边界

本轮核对根LICENSE：[tqLLM][TQ-LICENSE]、[HyperQwen][H-LICENSE]、[NInfer-4090][N-LICENSE]、[FLARE][F-LICENSE]、[Kern][K-LICENSE]、[Mirage][MPK-LICENSE]、[KTransformers][KT-LICENSE]、[Fiddler][FIDDLER-LICENSE]、[HybriMoE][HYB-LICENSE]、[FlashInfer][FI-LICENSE]为Apache-2.0；[ExLlamaV3][EX-LICENSE]与[llama.cpp][LL-LICENSE]为MIT；[FlashAttention][FA-LICENSE]为BSD-3-Clause。实际copy时仍记录所复制文件头、第三方来源、notice和修改标记，不把仓库根license覆盖到vendored代码或模型权重。

**EAGLE-4是实质例外。** 当前根LICENSE明确称source-available、非OSI开源，`cost_model.py`与`low_rank_head.py`的SPDX为`LicenseRef-Eagle-4-Source-Available`，有竞争性offering和商业使用限制。本计划不将这些文件直接copy进Strata。可以研究公开算法/成本建模原则，独立设计本机控制器；若需要实质移植，先解决该具体文件许可。它的GDN文件声明派生自SGLang/vLLM/causal-conv1d/FLA，不能仅凭头部第三方版权就认定Eagle修改全部Apache；优先从许可明确的原始上游拿基础代码。这里是对已读文件条款的移植边界记录，不对项目整体给法律结论。[E4-LICENSE][E4-COST][E4-HEAD][E4-GDN][S-REPLAY]

## 11. 固定一手来源索引

下列Markdown引用均为固定SHA或固定论文版本；不以搜索摘要/二手DeepWiki作为实现证据。DALI/ScheInfer本轮未找到可确认官方代码，不编造路径。本文Exa本轮共9次搜索、每次5条，共45个搜索结果槽位（含重复）；另有直接fetch/GitHub源码核对，不把45当作45篇唯一资料。

[LOCAL-NP0]: ../history/reports/P0-T7-NP0-20261025.md
[LOCAL-ENV]: ../history/02_ENVIRONMENT.md
[ST-ISA]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert_layout.cpp
[ST-CMAKE]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt
[ST-IQ256]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/iq_avx2.cpp
[ST-NATIVE]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/native_expert.cpp
[ST-SAMPLER]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/sampler.cu
[TQ-ARCH]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/docs/ARCHITECTURE.md
[TQ-CPU]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/src/models/qwen/qwen4exp/fn_cpu_experts.hpp
[TQ-CACHE]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/src/experts/tq3_expert_cache.hpp
[TQ-PLAN]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/src/models/qwen/qwen4exp/prefill_plan.hpp
[TQ-KV]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/src/kv/kv_store_cuda.cpp
[TQ-FMT]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/docs/reference/formats.md
[TQ-SPEC]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/docs/guides/speculative-decoding.md
[H-OPT]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/docs/optimizations.md
[H-SPLIT]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/patches/spec-decode-attn.patch
[H-I8]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/patches/spec-decode-int8-kv.patch
[H-DRAFTVOCAB]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/patches/qwen3_5-mtp-draft-vocab.patch
[H-DRAFTQUANT]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/drafter/quant_dflash2.py
[H-LOOKUP]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/patches/dflash2-lookup-drafting.patch
[H-KVARN]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/kvarn/README.md
[N-README]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/README.md
[N-I8]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/kernel/gqa_attention_decode_i8.cuh
[N-KVQUANT]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/kernel/gqa_attention_kv_quant.cuh
[N-REPLAY]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/docs/maintainer/replayssm-gdn.md
[N-REPLAY-CODE]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/linear_attention/gated_delta_net/replay.cpp
[N-CACHE]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/docs/continuation-cache.md
[N-ROUND]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/kernel/speculative_round.cuh
[F-README]: https://github.com/NVIDIA/flare-local-inference/blob/bce032c014bae34502ba22d3304fa084d5b40afe/README.md
[F-STATE]: https://github.com/NVIDIA/flare-local-inference/blob/bce032c014bae34502ba22d3304fa084d5b40afe/ignition/components/state_transfer.py
[F-ROUNDS]: https://github.com/NVIDIA/flare-local-inference/blob/bce032c014bae34502ba22d3304fa084d5b40afe/helios/src/scheduler/rounds.rs
[K-REG]: https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/docs/registry.md
[K-COMPILE]: https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/crates/kern-runtime/src/compile.rs
[K-EXEC]: https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/crates/kern-runtime/src/exec.rs
[E4-ARCH]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/docs/architecture.md
[E4-FAQ]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/docs/faq.md
[E4-CAL]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/docs/calibration.md
[E4-COST]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/eagle_harness/core/cost_model.py
[E4-HEAD]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/eagle_harness/models/low_rank_head.py
[E4-GDN]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/eagle_harness/kernels/gdn_tree_recurrence.py
[E4-ACCEPT]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/eagle_harness/kernels/accept_tail.py
[E4-LICENSE]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/LICENSE
[EX-README]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/README.md
[EX-AFF]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/exllamav3/model/moe_cpu_affinity.py
[EX-HANDOFF]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/exllamav3/exllamav3_ext/cpu/moe_handoff.cu
[EX-CPUCACHE]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/exllamav3/generator/cpu_cache.py
[LL-README]: https://github.com/ggml-org/llama.cpp/blob/2280f0fd163b03d4331d49e08460f66502e35854/README.md
[LL-X86]: https://github.com/ggml-org/llama.cpp/blob/2280f0fd163b03d4331d49e08460f66502e35854/ggml/src/ggml-cpu/arch/x86/quants.c
[LL-ATTN]: https://github.com/ggml-org/llama.cpp/blob/2280f0fd163b03d4331d49e08460f66502e35854/ggml/src/ggml-cuda/fattn-vec.cuh
[MPK-README]: https://github.com/mirage-project/mirage/blob/63af900000d8928a885f7af7889a3448621e18a9/README.md
[MPK-KERNEL]: https://github.com/mirage-project/mirage/blob/63af900000d8928a885f7af7889a3448621e18a9/include/mirage/persistent_kernel/persistent_kernel.cuh
[MPK-RUNTIME]: https://github.com/mirage-project/mirage/blob/63af900000d8928a885f7af7889a3448621e18a9/include/mirage/persistent_kernel/runtime_header.h
[MPK-AMPERE]: https://github.com/mirage-project/mirage/tree/63af900000d8928a885f7af7889a3448621e18a9/include/mirage/persistent_kernel/tasks/ampere
[MPK-PAPER]: https://arxiv.org/abs/2512.22219v1
[KT-README]: https://github.com/kvcache-ai/ktransformers/blob/a694e718e8b3ec2e221277d674e369f3be38d2a4/README.md
[KT-CPU]: https://github.com/kvcache-ai/ktransformers/blob/a694e718e8b3ec2e221277d674e369f3be38d2a4/kt-kernel/cpu_backend/cpuinfer.h
[KT-PAPER]: https://dl.acm.org/doi/10.1145/3731569.3764843
[FIDDLER-CODE]: https://github.com/efeslab/fiddler/blob/227715bfd6e8c731b29548eab01d9919c4fe9564/src/fiddler/mixtral.py
[FIDDLER-PAPER]: https://proceedings.iclr.cc/paper_files/paper/2025/file/8cd1ce03ea58b3d7dfd809e4d42f08ea-Paper-Conference.pdf
[HYB-EXPERT]: https://github.com/PKU-SEC-Lab/HybriMoE/blob/508a85b9a43dff37124370d8816e411e74827803/ktransformers/operators/experts.py
[DALI]: https://arxiv.org/html/2602.03495v1
[SCHE]: https://arxiv.org/html/2411.15715v1
[POWER]: https://github.com/Tiiny-AI/PowerInfer/blob/8bd56d69906c9d2dba4d3bf6899763401e01a9a4/README.md
[FA-README]: https://github.com/Dao-AILab/flash-attention/blob/98c1cee0ed59307833841cdbf567fe336ceec13a/README.md
[FA2]: https://arxiv.org/abs/2307.08691
[FI-README]: https://github.com/flashinfer-ai/flashinfer/blob/847172573ad1d5a929a8e7fb67aa7c072f8f7dcb/README.md
[FI-CASCADE]: https://github.com/flashinfer-ai/flashinfer/blob/847172573ad1d5a929a8e7fb67aa7c072f8f7dcb/flashinfer/cascade.py
[FI-DECODE]: https://github.com/flashinfer-ai/flashinfer/blob/847172573ad1d5a929a8e7fb67aa7c072f8f7dcb/include/flashinfer/attention/decode.cuh
[S-HICACHE]: https://github.com/sgl-project/sglang/blob/a99c7d050faee00b104a0b861df2d394ded74eb6/docs/docs/advanced_features/hicache_design.mdx
[S-REPLAY]: https://github.com/sgl-project/sglang/blob/a99c7d050faee00b104a0b861df2d394ded74eb6/python/sglang/kernels/ops/attention/linear/gdn_replayssm_spec_fold.py
[KIVI]: https://proceedings.mlr.press/v235/liu24bz.html
[QUEST]: https://arxiv.org/abs/2406.10774v2
[TQ-LICENSE]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/LICENSE
[H-LICENSE]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/LICENSE
[N-LICENSE]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/LICENSE
[F-LICENSE]: https://github.com/NVIDIA/flare-local-inference/blob/bce032c014bae34502ba22d3304fa084d5b40afe/LICENSE
[K-LICENSE]: https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/LICENSE
[MPK-LICENSE]: https://github.com/mirage-project/mirage/blob/63af900000d8928a885f7af7889a3448621e18a9/LICENSE
[KT-LICENSE]: https://github.com/kvcache-ai/ktransformers/blob/a694e718e8b3ec2e221277d674e369f3be38d2a4/LICENSE
[FIDDLER-LICENSE]: https://github.com/efeslab/fiddler/blob/227715bfd6e8c731b29548eab01d9919c4fe9564/LICENSE
[HYB-LICENSE]: https://github.com/PKU-SEC-Lab/HybriMoE/blob/508a85b9a43dff37124370d8816e411e74827803/LICENSE
[FI-LICENSE]: https://github.com/flashinfer-ai/flashinfer/blob/847172573ad1d5a929a8e7fb67aa7c072f8f7dcb/LICENSE
[EX-LICENSE]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/LICENSE
[LL-LICENSE]: https://github.com/ggml-org/llama.cpp/blob/2280f0fd163b03d4331d49e08460f66502e35854/LICENSE
[FA-LICENSE]: https://github.com/Dao-AILab/flash-attention/blob/98c1cee0ed59307833841cdbf567fe336ceec13a/LICENSE
