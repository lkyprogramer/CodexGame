# P07：4090 的 FlashNext CUDA kernel 与局部执行区域计划

本计划覆盖 O21–O32。O23 / O26 的接受算法由 P04 负责，O30 的内存与拷贝策略由 P11 负责，这里给出它们与 CUDA kernel 的接口、测试和停止条件。Prefill scratch / grouped MMQ / `GDN_CHUNKED` 由 P05 单独执行。本文件是实施与验收设计，**没有实施或运行新的 GPU kernel**，也没有把其他卡的 micro 收益换算为 4090 收益。

已审源码固定为 `41cf05a06a25dd29103b7b27a2279a3f60c21876`；最终 freshness 检查的新执行 base 为 `4b9e05a2a806a3fe24f7b2560d98626c37dade35`。核心 CUDA、CPU、verify/MTP、prefill 文件在这两个 tree 间相同，证据见 [最终版本增量复核](../sources/FRESHNESS_DELTA.md)；所以本计划保留固定的已审源码链接。生产 oracle 仍是 v0.2.3 + EXACT6，不能把升级和新 kernel 混成一个变量。

目标固定：RTX 4090 24 GB / sm89、Xeon Silver 4216、64 GB DDR4，GSQ-RCO **IQ3_XXS**，KV int8、总 context 上限 131072、spec4 / `--spec-min-p 0.5`（草稿阈值，非采样 `min_p`）。以 manifest 中每个矩阵的真实 dtype 为准。不能用 DeepSeek、Qwen3.5、NVFP4、TQ、IQ3_S 的专用形状来代表本模型。

## 1. 必须保留的现状与优先级

**先验证当前已有路径的命中和收益，再做增量改造。**下面几项不是待发明的新功能。

| 能力 | 固定 main 的状态 | 本计划如何处理 |
|---|---|---|
| native expert GU / SwiGLU / q8_1 融合 | 已有 `STRATA_GU_SWIGLU=1`，默认资格主要在特定 sm120；实际格式与布局另有 gate | 先确认 IQ3_XXS 真命中、hq 字节和真实窗口结果 |
| expert multi column 解包共享 | 已有 native multi kernel | 不把重写一份同功能代码计为成果 |
| QSA int8 原位读取和反量化 | `load8_q8` 直接读取 int8 与 scale 到寄存器 | 只做向量读取、scale 复用、访存改善等增量 |
| QSA split-KV | baseline 已有 CHUNK=64 + merge | 不再提“首次实现 split-KV” |
| QSA int8 Tensor Core 分段 | 已有 `STRATA_QSA_SPLIT_ATTN=1`，sm80+；header 明示非 bitwise | 优先单独验收已有 opt-in，再考虑 tiny-query 新调度 |
| verify CUDA graph | 已有 whole-window capture / replay、commit graph 与 host/CPU 协同 | 优化真实 host gap 或 metadata，不改写整个运行时 |
| greedy 大词表多 block argmax | sm80–89 已有 `argmax_rows`，MTP top-prob 也有 split 路径 | 新 head 计划只能减少剩余流量或规约成本 |
| GDN decode recurrence / commit | 已有 multi、split、QFUSE 和 state-only commit 路径 | 首先定位真正被调用的组合 |
| HC persistent read | 源码已有，但实现是 HIP-only；CUDA stub 返回 false | 4090 需要新实现，不能只设置现有开关声称命中 |

旧 Ada 表、IL0 / IL89 已测无收益；O22 保持搁置。旧 host window gap 约 1.2% 的附件结果是 O25 的低收益先验，不是本轮应重跑全部 graph 方案的理由。MTP Q4 head 已是边缘收益，O23 必须以新的接受率 / head 成本证据才能重开。

## 2. 固定源码地图

| 模块 / 符号 | 固定源码锚点 | 关键事实 |
|---|---|---|
| `native_expert_grouped` | [iq_kernels.cu L5071](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/iq_kernels.cu#L5071) | V2 专门 gate 包含 IQ3_S / IQ4_NL，不等于 IQ3_XXS 通用支持 |
| `native_gu_swiglu_kernel`、`gu_swiglu_on`、`launch_gu_swiglu` | [L2758](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/iq_kernels.cu#L2758)、[L4106](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/iq_kernels.cu#L4106)、[L5170](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/iq_kernels.cu#L5170) | 限 split 格式、shape、每 row dot 数和其他分派状态；env=1 不等于已执行 |
| `native_mmvq` / IL table | [native_mmvq.cu L2921](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/native_mmvq.cu#L2921)、[L2980](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/native_mmvq.cu#L2980)、[L3143](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/native_mmvq.cu#L3143) | 默认共享表与按架构形状选择；用户旧 Ada 失败结果仍有效 |
| verify 的实际 target head | [verify.cpp L2250–2343](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L2250) | T-column quant→MMVQ/IL→argmax；不能只改 `NativeHead::run` 以为改到了主 verify |
| `NativeHead::run` | [native_head.cpp L86](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/native_head.cpp#L86) | 单次 head API，和 verify 内直接调用的分支不同 |
| `MtpDrafter::make_q4_head / bind`、head | [mtp.cpp L226](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/mtp.cpp#L226)、[L661](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/mtp.cpp#L661)、[L1193](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/mtp.cpp#L1193) | 已有 subset / Q4 draft head、共享 owner、map_ids、prob/coupled 分支 |
| `sample_tokens` 与概率验证 | [sampler.cu L1239](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/sampler.cu#L1239)、[L1347](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/sampler.cu#L1347) | 采样链、Philox counter、q / residual 语义必须保持 |
| QSA inline int8 / chunk / merge | [qsa_decode_attn.cu L54](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/qsa_decode_attn.cu#L54)、[L948](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/qsa_decode_attn.cu#L948)、[L1042](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/qsa_decode_attn.cu#L1042) | 已有 vector load、selected IDs、每 query partials 和 log-sum-exp merge |
| `qsa_decode_attn_split` | [qsa_prompt_attn.cu L2275](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/qsa_prompt_attn.cu#L2275)、[header L37](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/kernels/qsa_prompt_attn.hpp#L37) | int8、sm80+、最多20 splits；数值路径有变化；verify L1891 / MTP L1033 调用 |
| GDN 真正 verify 入口 | [verify.cpp L1538](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L1538)、[verify_kernels.cu L1134](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/verify_kernels.cu#L1134) | `float* state`；multi 与 commit / split / QFUSE 在这里选择 |
| GDN 层合并 commit | [verify_kernels.cu L1067](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/verify_kernels.cu#L1067)、[session.hpp L35](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/session.hpp#L35) | 状态为 FP32；conv history、递推状态和接受前缀均要恢复 |
| graph / host / CPU plan | [verify.cpp L2454](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L2454)、[L2865](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L2865)、[L3303](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L3303)、[L3382](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L3382) | capture、run、publish_plan、commit；doorbell / fence 不可删除 |
| mapped copy / DMA | [verify_kernels.cu L614](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/verify_kernels.cu#L614)、[verify.cpp L3275](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L3275) | `fetch_blobs_kernel` 与 `Verifier::fetch_dma` 是比较入口 |
| 现有 HIP HC persistent | [fused_gr.cu L2601](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/fused_gr.cu#L2601)、[L3040](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/fused_gr.cu#L3040) | HIP 内80 blocks全驻留、两次grid barrier、非bitwise；CUDA为stub |

## 3. 全部 kernel 的固定输入 / 输出 / 命中合同

每个微测保存实际 dtype、shape、strides、nt、expert group maps、quant 字节、KV page table / selected IDs、device attributes、编译器与 cubin 身份。完整上下文长度和本次 attention 读取的 selected-KV 数分开记录：FlashNext 的选择式 attention 不是每个 query 直接扫描全 128K K/V。

**所有新选择器 / wrapper 都必须有 actual-path 计数或 test-only 返回值。**assert requested path executed；fallback 记录原因；零调用、skip、未知 architecture 不得作为“通过而且很快”。生产指标使用关闭高扰动观测的 binary，诊断 profile 另跑。当前 `STRATA_VERIFY_PROFILE` 会禁用部分 branch / shared-stream / fused 路径，因此不能在 profile-on 的图上决定 profile-off 的最终收益。[verify.cpp L1162 / L1929](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp#L1162)

数值等级预先声明：E 为与旧路径逐 bit 相同；N 为运算顺序或精度有变化，需要预冻结误差与质量门；Q 为有意改变 target 分布或模型近似。不能用 sampled 输出在相同 seed 下恰好相同来证明完整分布相同；也不能用一次 greedy 文本无差异证明长序列状态相同。

除对应实现任务明确新增外，本文件出现的候选结构、接口、开关、测试都标为**拟新增 / 未实现**。已有 env 由进程内 static 缓存读取的路径，A/B 要使用独立进程，不能在同一个进程里改 env 后假定重分派。

## 4. 逐任务实施

### P07-01：真实热点、资源与命中清单

**覆盖**：O21–O32 的先决步骤。**输入**：P0生产基线、最新隔离基线、真实模型 manifest、固定请求集。**源**：上节各分派入口，尤其 `native_expert_grouped`、`Verifier::record_window`、`MtpDrafter::record_rest`。

**拟新增输出**：`cuda_path_manifest.json`、按 `(dtype, shape, nt, path)` 汇总的调用表、每阶段 critical-path 贡献、GPU/CPU 重叠图。尽量用 launch site 的采样计数和 NVTX scope，不在每个 kernel 末尾同步。记录寄存器、local-memory spill、静态 / 动态 shared memory、launch grid、实际 occupancy 与 memory / compute 受限证据。

**验收 / 停止**：所有重要调用有实际符号而非仅 env 名；时间能解释完整 window 而非把重叠阶段相加。若目标阶段的理论上限也不足以覆盖工程成本，就停止对应任务。Amdahl 只用于上界筛选，不能把彼此重叠的时间份额当可加收益。

### P07-02：GU / SwiGLU / quant 的局部融合

**覆盖 O21。源**：`iq_kernels.cu::native_expert_grouped`、`native_gu_swiglu_kernel`、`launch_gu_swiglu`。**先做现有能力**：单独启用已有 `STRATA_GU_SWIGLU=1`，对实际 IQ3_XXS GU / 实际 down、nt1 / 2 / 4及实际nt分布检查 `gs_done`，同时记录 V1 / V2 / EXPDEC / layout gate 是否覆盖它。不能把 IQ3_S + IQ4_NL 的 V2 gate 改名字后当通用优化。

**拟新增增量**：只有现有路径不覆盖且关键路径充分时，新增当前 dtype 的 GU→SwiGLU→q8_1 tile 或改其访存；尽量保持相同 dot 和量化顺序。GU+down 完全融合不是默认下一步：down 需要整个中间向量，不可把“局部 GU row 已好”当成完整 hq 已就绪。跨 CTA 保留全局中间量通常更安全；若探索 CTA 内完整 expert，先证明 register / SMEM 可容纳且不会严重降低并发。

**拟新增 gate**：`STRATA_EXPERT_FUSE_SM89=0|1`，仅补丁实现后有效、默认0，支持形状白名单。**测试**：基于已有 `native_grouped_parity` / `iq_multi_parity`，增加 IQ3_XXS 真 blob、GU/down mixed types、0/1/多 groups、重复 experts、nt1…8、空 entries、tail / Hadamard 不支持时 fallback、毒化 scratch 与 graph replay。要求 hq 字节与 E oracle 相同，最终 down 与 combine 同样通过。

**性能 / 停止**：micro 是完整 GU+quant+down，并保留48层相似 graph replay；最终测 verify window。若 spill、occupancy 或指令数抵消省下的读写 / launch，关闭。复杂度中高；收益不从 sm120 注释外推。

### P07-03：dense MMVQ / Ada 表的重开门

**覆盖 O22。状态：已测搁置。源**：`native_mmvq_il_rows_for`、`native_mmvq_il_supported` 与 `mmvq_il_parity`。本任务首先比较 P07-01 shape 直方图与旧 IL0 / IL89 记录。

只有新增模型类型、新 T 分布、新编译器导致的明确回归，或此前未覆盖但如今显著的具体 shape，才允许单个 shape 的小范围研究。先算其 critical-path 上界，再在该 shape 选择 rows / warps / interleave，验证完整 quant+interleave+MMVQ 成本。

**新增物**：仅需要时新增一个有证据的白名单项，不引入全局盲扫开关。**验收**：bitwise、nt1…8、留出相邻 shapes；micro 及窗口都命中。**停止**：分布未变，或 paired 差异落 A/A 噪声，记录“旧败延续”并结束，不重跑历史整套表。复杂度低，但优先级低。

### P07-04：draft-only head 的有界实验

**覆盖 O23，与 P04 共用接受率门。源**：`MtpDrafter::make_q4_head / bind`、`mtp.hpp::owns_draft_head_ / dhead_ / dhead_type_`、`record_rest` 的 head 与 `spec_draft_sample / coupled_draft_sample`。

当前已有 vocab subset 和 Q4 draft head；历史 MTPQ4 head 仅边缘收益，不能改个命令重跑便算新路线。新候选可为实际高开销 row 的 draft-only quant、候选集合生成后对小 head 计算、按请求稳定词表的 cache，但先给出新机制相对旧方案减少的真实字节 / dot 份额。

**所有权合同**：target `head_->weights()` 保持完整且只读；多个 drafter 共享 `dhead_` 时只有 owner 分配 / 释放；新 candidate map / inverse map、penalty token IDs 与共享 lifetime 一并管理。模型 hash、vocab 与 layout 变化必须失效。禁止原地量化共享 target head。

**拟新增接口**：`DraftHeadPlan`、`DraftVocabMap`、`STRATA_DRAFT_HEAD_PLAN=baseline|candidate`，均未实现。greedy 下仍用完整 target 决定接受；概率 spec 下明确 q 的 support、归一化、完整 q 或算法实际需要的 q 值与 residual correction，不将“greedy 正确”自动推广为 sampled 正确。拟新增 `draft_head_plan_parity` / `draft_head_accept_bench`。

**测试**：subset 不含 target 最优 token、候选并列、EOS / tool token、thinking token、所有 penalty、候选 refresh、shared drafter 释放、accept0 / partial / full、固定 seed 的 q 与 correction。**指标**：draft ms、平均接受个数、accepted tokens/window、完整请求 wall、峰值显存；只省 draft ms 而总 wall 变慢必须停止。复杂度中高；由 P04 负责最终算法证明。

### P07-05：target head 与 sampler 的精确优化

**覆盖 O24。源**：`verify.cpp` L2250之后的实际 T-column head，`argmax_rows`、`row_top_prob_split`、`sampler.cu::sample_tokens`。`NativeHead::run` 是相关单次 API，但修改它不代表主 verify 使用了新 kernel。

已有 sm80–89 多 block argmax，不能把增加 split argmax 当新增成果。候选为 head tile 内局部极值 / 规约与现有 launch 合并、减少仅 greedy 请求不需要的 logits 往返，或 sampler 内已证明冗余的 pass。greedy 可流式保留每 tile 极值，但必须维持同样 logits 算术、NaN/Inf 合同和 tie-break；需要 logits、logprobs、penalties、coupled/prob verifier 或 sampled 时必须保留对应完整数据与语义。

**拟新增接口**：`HeadOutputContract { FullLogits, GreedyIds }`；不是主线已有枚举。选择依据请求合同，不以一次调用的“看起来 greedy”偷删后续 verifier 需要的 logits。任何 target vocab 裁剪都不是此 E 路线，必须另列 Q 并重新获准。

**测试**：实际大词表、nt1…8、奇数 tail、全相等 logits、跨 tile ties、负零、NaN / Inf、top-k / top-p / min-p、temperature、penalty 顺序、history ring、Philox seed/counter、logprobs。已有 `sampler_parity` / `verify_parity` / `spec_verify_parity` 作基础，拟新增 `head_output_contract_test` / `head_trace_bench`。

**性能 / 停止**：计算整个 head+pick+prob 而非单独 argmax。head 不在关键路径或新规约数值改变时，停止 E 路线或明确改列 N。sm90 cluster greedy 实现不适用于4090；无需把其 target 跳过当成已验证 Ada。复杂度中高。

### P07-06：graph metadata、host 前移和设备 bookkeeping

**覆盖 O25 / O26。源**：`Verifier::capture / stage_inputs / prelaunch / run / publish_plan / commit / wait_commit / prestage / pl_launch`。当前已有多种提前 stage / pipeline，先核对实际使用情况。

**可前移的内容**：稳定形状与 buffer metadata、已知输入 token 的拷贝准备、不会依赖上一轮接受结果的描述符初始化。**不可前移的内容**：未确定接受长度的下一 token / pos、待确认的 GDN / KV commit、依赖本轮 router 的 expert plan、未消费的 RNG counter。graph key 至少要覆盖会影响捕获的 shape / slot mapping / addresses / mode；新 scratch 指针变化须重捕获或使用已有安全参数更新合同。

**拟新增**：`PreparedWindowMetadata` 和 generation-tagged 的预备槽，默认关闭 `STRATA_PREPARE_META=1`；O26 可提出一个 `CommitSummary` device buffer，但不是现有接口。只合并真实冗余的 D2H / 小 kernel；host 仍须在返回 token、响应取消与释放 owner 前看到正确完成状态。不能删除 GPU flag 的 system fence 或 CPU complete 发布协议。

**测试**：graph key 改变、指针复用、batch / 单slot切换、accept0 / 1 / all、EOS、cancel 在计划准备 / kernel / commit 各安全边界、cache restore、后续 prompt、关闭 async。对 device bookkeeping 比较提交后的 KV、GDN、conv、PLE、RNG与旧路径。

**停止**：重新测得 host gap 仍近旧记录且上界过小；busy polling 抢 CPU；或取消响应退化。`verify.cpp` L3130已有 query polling 负收益注释，不能默认用它代替 blocking sync。复杂度中高；P04 负责接受算法完整性。

### P07-07：已有 int8 QSA 路径的向量化和复用

**覆盖 O27。源**：`qsa_decode_attn.cu::load8_q8 / load8 / launch_chunks_batch / launch_merge_batch`。现有 `load8_q8` 已经以 `uint2` 读8个 int8，再乘同一 FP16 scale；不存在需要本任务首次消除的整块 FP16 KV 解压 buffer。

**拟新增增量**：仅在具体 memory stall 证据下，调整连续 dims 的 load 合并、scale 共享、页内 coalescing、预取距离；维持现有 byte layout 和 `row / kvh / d0` 地址计算。query-head 组共享同一 KV 时验证是否已有共享，新增复用必须计算节省的 DRAM 流量与增加的 shared / register 用量。

**拟新增 gate**：`STRATA_QSA_I8_LOAD_SM89=0|1`，未实现。**测试**：固定 KV codes / scales 的逐步 QK 与 PV oracle、页边界、最后不完整页、selected IDs 不规则、非连续 physical pages、int8极值 / 零scale、q1…8，其他KV格式必须走原路径。已有 `kv_q8_parity` / `qsa_parity` 为基础，但要显式增加新 loader 的路径命中断言。

**停止**：新核只是复刻已有 load8_q8，或 spill / 低 occupancy / 冗余读取抵消收益；不改变 KV 量化格式或 scale 以掩盖 performance 问题。复杂度中高；与 O29 先分别验收。

### P07-08：tiny-query split / selected-KV 交集复用

**覆盖 O29。先验收已有** `STRATA_QSA_SPLIT_ATTN=1`。它位于 `qsa_prompt_attn.cu::qsa_decode_attn_split`，由 verify 和 MTP 调用；要求 int8 K/V、合法 page table / scales、HD256、Q/KV 头比例12、sm80+，Q4 / hybrid 等不符合则返回 false。splits 按设备 SM 数、n_q、KV heads 与 capacity 估算，最多20，并检查 scratch 容量。header 明示不是 baseline decode kernel 的逐 bit 输出，必须按 N 档验收。

**第一步输出**：baseline CHUNK=64 和既有 Tensor Core split 两路，在 q1…8、短到长 selected list、实际 32K / 64K / 96K / 约122K prompt 上的分段 / merge / 总 attention 时间。不要把 context 当 selected-KV 数；实际 topk 与尾 cells、causal mask 都要保留。已有 `qsa_prompt_attn_parity` 的名称不保证测试到 split wrapper；当前测试未直接调用该 wrapper，必须新增覆盖。

**拟新增 target**：`qsa_decode_split_parity` / `qsa_tiny_query_bench`。针对新研究，候选接口 `QsaTinyPlan { query_tile, segments, scratch_bytes }` 与 `STRATA_QSA_TINY_PLAN=baseline|auto` 均未实现。先做 segment 的有界白名单，再研究 q2…5 选中页交集：同一页为多个 query 复用 K/V，但各 query 的 selected ID 序列、head、mask、position、softmax 归一化独立。交集为空、只有尾页相同、selected顺序不同、跨slot必须退回或正确处理。

**数值验收**：N 档记录 QK/PV、attention output、logits 与长 teacher-forced误差；按实际采样和任务质量验收。不能只用 FP64参考给出小误差就承诺最终 token相同。变更 segment会改变 FP32 log-sum-exp merge 顺序，初期不要标 E。scratch 的最大写域、alignment、graph 指针 lifetime、zero-length处理全部测试。

**性能 / 停止**：报告 split 和 merge 两阶段及真实窗口；GPU 选中 KV 较短时增加 splits 常可能更慢。若分段 / 交集元数据、重复读或 merge 超过节省成本，保持已有实现。`native_flash_attn_short_step` 的 ctx≤256路径不替代本模型长context QSA。复杂度中高。

### P07-09：GDN decode 的 FP32 状态与局部融合

**覆盖 O28。源**：真实 verifier 的 `gdn_step_norm_multi`（`verify_kernels.cu` L1134），以及 `gdn_step_norm_groups`、`gdn_commit_layers`。`fused_gdn.cu` 是相关实现 / oracle，但不能只优化那里的单 token 入口而漏掉当前 verify 主路径。

**状态合同**：GDN长期 state 为 **FP32**；保留真实 projection 的存储格式、所有原有量化 / BF16转换点、FP32递推与 norm 顺序。36层GDN、S128、16 K heads / 48 V heads的真实shape以模型 geometry复核；不能把整块状态改成BF16并声称只是搬运优化。

**先验收已有路径**：`STRATA_GDN_SPLIT`、默认 state-only commit split、QFUSE、batch groups / per-slot分支。若现有split在4090有收益且通过对应parity，它是现有功能实验，不是新kernel。

**拟新增增量**：state tile寄存器驻留、只在同一个合法窗口内复用、sm89支持的cp.async双缓冲（仅在确有可重叠的global→shared搬运时）、norm/quant epilogue局部合并。不能并行重排有时间依赖的递推，不能把被拒绝token状态提交。候选 `STRATA_GDN_TILE_SM89=baseline|tile` 与 `gdn_state_tile_parity` 均未实现。

**测试**：已有 `gdn_parity` 已覆盖multi T1…8及layer commit基础，新增真实长teacher-forced、不同state幅度、非对称conv history、modulo head pairing、T1…8、keep0…T、commit-only、all-output、QFUSE hq字节、reject后重算、park/restore/cancel。N档的长序列漂移必须额外验证，不能拿单step容差直接通过。

**性能 / 停止**：测state实际读写bytes、SMEM、register、occupancy、recurrence与commit总时间；若小tile重复读取state、融合导致spill或GDN不在criticalpath则关闭。不要搬入Hopper TMA/PDL/WGMMA路径；prefill chunk算法属于P05。复杂度高。

### P07-10：mapped fetch / DMA 的 kernel 接口

**覆盖 O30，主计划 P11。源**：`fetch_blobs_kernel / fetch_blobs`、`Verifier::fetch_dma`、`publish_plan`。当前mapped SM copy与显式DMA已有不同调用基础，选择必须计入真实PCIe链路和DDR竞争。

**拟新增接口**：`FetchCostSample` / `FetchMethodDecision`，如果P11已定义同类结构就复用；不重复加入另一份策略。输入至少为bytes、expert数、contiguity、pinned状态、staging是否命中、当前CPU miss量和copy队列。测量GPU SM copy与DMA同时对CPU的带宽影响，不能在空闲CPU下定一个放进生产便永久使用的常数。

**测试**：0/1/多expert、不同blob大小、非连续页、cold page、源owner保活、copy完成event、plan epoch、cancel/restore；慢DMA与CPU完成不同顺序不破坏GPU barrier。必要pin/memcpy成本计入。

**停止**：当前方法处于本机甜点区、新staging导致RAM压力，或只是将等待从GPU计时移到host；不把NVLink或新PCIe代际donor收益搬给本机。复杂度中；与P01/驻留策略的组合最后验收。

### P07-11：MPK思想的局部persistent区域

**覆盖 O31，研究后置。Donor**：Mirage固定SHA `63af900000d8928a885f7af7889a3448621e18a9` 的 [persistent_kernel.cuh](https://github.com/mirage-project/mirage/blob/63af900000d8928a885f7af7889a3448621e18a9/include/mirage/persistent_kernel/persistent_kernel.cuh)、[runtime_header.h](https://github.com/mirage-project/mirage/blob/63af900000d8928a885f7af7889a3448621e18a9/include/mirage/persistent_kernel/runtime_header.h)、[Ampere任务目录](https://github.com/mirage-project/mirage/tree/63af900000d8928a885f7af7889a3448621e18a9/include/mirage/persistent_kernel/tasks/ampere)。这里只借鉴任务表、依赖计数与局部软件流水；不是已经可用的FlashNext sm89整模型引擎。

**先决门**：P07-01证明一个没有CPU / DMA外部未完成依赖的短GPU连续区域，其launch或中间写回有可回收成本。先选CTA-local fusion；只有跨kernel成本仍显著才考虑bounded persistent region，例如同一HC read中的数个阶段。不要把整个verify常驻kernel化，也不要让常驻CTA轮询CPU专家完成而占满SM。

**现有Strata限制**：`STRATA_HC_PERSIST=1` 对应HIP实现；它要求80blocks全驻留，两次grid barrier，启动检查还验证驻留与数值，规约顺序不同。CUDA stub返回false。4090上该env的“test进程通过”不代表执行了persistent路径。

**拟新增接口 / gate**：`GpuRegionTask`、`GpuRegionEpoch`、`GpuRegionPlan`、`STRATA_GPU_LOCAL_REGION=off|hc`，均未实现。第一版任务表固定且有限，generation防止旧通知进入新任务，release/acquire及device fence根据数据owner严格设计。任何软件grid barrier先证明所有参与CTA能同时驻留，或改为不依赖全驻留的调度；资源变化、不同T、并发graph会打破静态假设。测试时设置可诊断的超时与外层进程 watchdog；不能在不受控死锁的GPU上靠hostflag保证可终止。

**测试**：T1…8、最高register / SMEM配置、并发expert / attention / copy、graph replay多generation、错误task ID、poisonedscratch、故障退出、取消安全点。新的 `gpu_local_region_parity` / `gpu_local_region_stress` 均需新增。N档规约必须按N处理，不从donor性能推断数值相同。

**停止 / 回滚**：实际等待来自CPU算力、persistent抢占expert资源、吞吐/尾延迟退化、不能证明无死锁，立即退回原CUDAgraph。保持区域边界输入/输出与旧核相同，关闭开关即可回滚，不需要整引擎迁移。复杂度很高、资格最严格、优先级低。

### P07-12：sm89 编译与资源有界调参

**覆盖 O32。源**：[CMakeLists.txt L182](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L182)，以及各kernel的launch site。固定main没有指定时默认arch120；4090隔离实验须明确 `CMAKE_CUDA_ARCHITECTURES=89`，不能盲从默认构建出不匹配binary。实际toolkit与hostcompiler先做兼容性检查，driver报告的CUDA能力与nvcc版本分开记。

**实施**：仅对P07-01已识别热点选择少量block / warp / register / shared-memory候选；保留实际shape白名单。记录ptxas资源、cubin的sm89代码、SASS和spill；maxrregcount降低寄存器却增加localmemory是回归而非优化。query deviceattrs验证shared/block、shared/SM与opt-in上限，不按其他GPU常数设置。

4090路线不包含sm90thread-block cluster、PDL、TMA/WGMMA，也不包含sm120原生FP4 MMA。允许实际源码支持的普通CUDA、cp.async与适用的矩阵路径；是否更快由目标shape决定。编译器全局`--use_fast_math`、更改FMA contraction、TF32或FP16累加都会改变数值合同，不能混进E档“编译优化”。

**拟新增**：离线`sm89_kernel_tune` harness和版本化shape配置，不在生产每个request在线搜索；所有候选计入编译/测试成本。已有IL0/IL89失败仍按P07-03处理，不因为设置sm89就重开全套。

**测试 / 停止**：正确性、资源上限与actualpath命中先过，再测micro和留出shape混合；最佳候选在完整window无净改善或p95退化即不采纳。复杂度中，避免大量组合消耗预算却没有新证据。

### P07-13：全链验收与组合最小化

每个候选先单独对原binary做A/A与ABBA，再只组合独立通过的patch。验收包含greedy、真实sampled参数、thinking/tool请求、短中长context、cold/warm权重与KV、prefix reuse、cancel/resume、会话park/restore。spec4的实际query数与API最大nt分别覆盖；slots4是停车缓存数量，不是默认并发batch4。

E档要求相关activation / hq / logits / acceptedstate逐bit相同；N档按预冻结数值与任务质量门。draft改变但target保持精确的方案仍要做真实接受算法测试，特别是概率spec与candidate map。总context131072包括prompt与输出，长prompt测试留出固定generation预算。

**性能准入建议**：小改须有重复的正净收益且配对置信区间不跨零；维护成本高的newkernel或persistentregion，可预先设3%完整场景净收益作为工程门槛，并为p95、TTFT、峰值VRAM / RAM写入允许回退界限。此阈值是项目选择，不是已测得/预测收益。先冻结门，再跑数据，不根据结果调门。

最后只保留有实际命中且提升最终目标的最小集合，记录没收益的组合。微测极值、作者异机结果、没有运行的测试、CUDA stub skip 均不进入“已验证加速”栏。

## 5. 当前已有构建目标与必须新增的覆盖

| 当前已有 target | 准确用途 / 不能据此宣称的事 |
|---|---|
| `native_grouped_parity`、`iq_multi_parity` | grouped / multi与已有融合基础；需要加入新dtype与gate的explicit hit |
| `native_expert_parity` | 实际/native expert基础，按构建与fixture条件执行 |
| `expdec_bench` | 已有但 `EXCLUDE_FROM_ALL`，显式构建；不是所有quant布局通用oracle |
| `mmvq_il_parity`、`b6_mmvq_bench` | 已有MMVQ / shape实验；旧Ada结果继续归档 |
| `sampler_parity`、`spec_verify_parity`、`verify_parity` | sampler、概率接受、argmax/prob等基础；新的head-output合同需另补 |
| `coupled_draft_test` | 已有host接受/采样相关测试；不替代GPU新head fixture |
| `kv_q8_parity`、`qsa_parity`、`qsa_slots_parity`、`qsa_merge_daily_parity` | 已有KV/QSA基础；不能只看名称推断覆盖新的splitwrapper |
| `qsa_prompt_attn_parity` | CUDA、tests或`STRATA_PARITY_PROMPT_ATTN`构建；该target有可执行文件，但此处CMake未给它注册同名CTest；需显式运行 |
| `qsa_rows_bench` | `EXCLUDE_FROM_ALL`；QSA相关micro，不是拟新增tinyquerybench |
| `gdn_parity` | 已有multi T1…8与layercommit基础；需扩展新tile、QFUSE及长序列 |
| `verify_batch_parity` | 已有batch窗口相关回归；不能把parking slots误作batch |
| `hc_persist_parity` | 对CUDA的skip / false不表示Ada路径已实现或通过 |

来源：[QSA targets L447–505](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L447)、[GPU parity L1099–1275](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L1099)、[HC/QSA/KV/batch L1334–1439](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L1334)、[native/EXPDEC L2152–2166](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L2152)。

**本计划拟新增，尚不存在**：`cuda_path_manifest`导出、`draft_head_plan_parity`、`draft_head_accept_bench`、`head_output_contract_test`、`head_trace_bench`、`qsa_decode_split_parity`、`qsa_tiny_query_bench`、`gdn_state_tile_parity`、`gpu_local_region_parity`、`gpu_local_region_stress`、`sm89_kernel_tune`。在实施PR里新增source与CMake注册后才可生成调用命令；不要把这些名字交给自动执行器当当前可运行目标。

## 6. 冲突组合与回滚矩阵

| 组合 | 具体风险 | 组合次序 / 回退 |
|---|---|---|
| GU融合 + V2/V2K/EXPDEC/layout | 一个gate覆盖另一个，env启用但未命中 | 单独命中记录；白名单最小组合 |
| QSA int8向量化 + Tensor Core split + tinyquery | 规约与访存同时变化，难定位数值差异 | loader先独立；split按N档；随后2×2 |
| GDNtile + QFUSE + commitmerge | hq/输出/状态最后读者不同；拒绝前缀错误 | 分别验证all-output与state-only、keep0…T |
| targethead省logits + sampled/prob/logprobs | downstream需要完整logits或概率 | `HeadOutputContract`拒绝不满足的请求 |
| draft候选 + shared drafter | ownership、tokenmap或q支持错误 | P04算法门；共享生命周期测试 |
| persistent + expert/attention/copy | 常驻CTA造成SM饥饿，破坏假设的全驻留 | boundedregion；并发压力不通过立即关闭 |
| graphmetadata前移 + cancel/restore | 旧generation覆盖新session，指针失效 | generation/owner检查；保留旧stage路径 |
| 新scratch + P05借用/relayout | capture持有旧地址，内存区域提前复用 | memoryledger共同审查；不得仅重测速度 |
| 新copy选择 + P01/CPU ISA | DDR竞争与CPU/GPU分流同时变化 | 单因素后组合；重新测成本而非硬套旧表 |
| sm89调参 + globalfastmath | 把数值改变伪装为资源优化 | 工具链/算术独立；E失败重新分类 |

回滚至少包括：保留原binary与config；新kernel只在独立gate后调用；unsupported/失败初始化回旧路径；恢复旧graph与scratch容量；停止实验服务后再释放其ownedbuffers。遇到正确性、hang、显存越界时先撤回相应候选，不继续扩大性能测试。

交付evidence包括fixedSHA、compile/cubin身份、sourcepatch、path-hit与fallbackcounts、test/skip/fail列表、数值/状态hash、nsys/ncu或等价诊断、profile-off完整请求原始数据、资源峰值和最终保留组合。未实际运行的项目明确标为未运行，不能用本计划的完整度替代运行证据。
