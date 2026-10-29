# P10 — 激进质量分支、硬件研究与 donor 资格 Implementation Plan

> **For agentic workers:** 执行时使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`。先完成可审阅的资格与实验定义，再决定是否实现。本文记录研究路线；不表示这些优化已经实现、验证或获准替换生产。

**Goal:** 保留可能跨越现有带宽/工作量上限的研究路线，同时准确披露其模型语义、硬件适用性、实现状态、质量代价和退出条件。产出速度—质量—资源 Pareto 与明确的 NO-GO/GO 依据。

**Architecture:** 资格卡 → 最小可证伪实验 → 独立 Q/N/X 分支 → 数值/状态/任务质量 → 单因素性能 → 有条件组合。研究路线与默认等价优化共享计量和manifest，不共享未经验证的默认开关。

**Tech Stack:** 4090/Ada `sm_89`、Xeon Silver 4216、64GB DDR4、Debian12/kernel6.1.0-17、驱动610.57.04/CUDA12.3；固定 Strata实现锚 `41cf05a06a25dd29103b7b27a2279a3f60c21876`。更晚执行锁见 freshness 声明。

**Spec:** O54–O57、O63–O64；O52/O53低位权重实现归P08，此处管理研究资格。另列target早退、recurrent state精度以及zapabob fork资格，不伪造新的已批准方向编号。E/N/Q是计算合同；R表示research状态，不能把“R分支”当成质量类别。

## Freshness：审计锚与执行锁

2026-10-25 最后刷新：实验执行锁为 [`4b9e05a2a806a3fe24f7b2560d98626c37dade35`](https://github.com/Niko1221/Strata/commit/4b9e05a2a806a3fe24f7b2560d98626c37dade35)，release v0.2.6；本文保留41cf的固定源码引用。项目已核对两锁之间`src/core`、`include/strata/core`、CPU/CUDA kernels与prefill的git对象相同；Qwen generate只有spec-split非bitexact说明增量，serve还有空消息400/one-token rate修正，CMake版本变化。执行时保留新锁的API修正，不用旧固定引用误称当前入口完全未变。相关新diff仍须随实验manifest记录。这个刷新不是本机性能验证。

## 1. Global Constraints 与统一资格卡

每个研究方向创建一份**拟新增** `research/<candidate>/qualification.json`，字段至少包括：

| 字段 | 必填内容 |
|---|---|
| `state` | `idea / source_reviewed / prototype / host_tested / target_gpu_tested / task_quality_passed / holdout_passed`，只能依已有证据向前推进 |
| `compute_track` | E/N/Q/X及理由；新kernel舍入、减expert、换模型不能混在一个标签 |
| `base_identity` | execution SHA、production baseline、EXACT6 patch、model/tensor/tokenizer/template/config hashes |
| `treatment` | 唯一变化、阈值/位宽/跳过层、训练/校准数据与成本 |
| `source` | 固定SHA/论文版本、文件+函数、代码/权重/数据许可分别记录 |
| `hardware` | 所需GPU指令、ISA、toolkit、driver、内存；当前机器逐项资格 |
| `hypothesis` | 要减少的关键路径工作或流量，以及可能增加的代价 |
| `pre_registered_gates` | 数值、状态、任务质量、性能、资源、停止规则与失败计入方式 |
| `rollback` | 旧binary/config/model/snapshot namespace；需要维护的X分支另有恢复方案 |

所有阈值、gate与新开关初始关闭。模型包和精度改变必须保留独立baseline，不能写进“当前IQ3_XXS/int8无损优化”的增益。已有P0、performance governor、C6off、EXACT6不是新贡献。没有实机数据就标“待测”，静态分析、host mock、编译成功或CI绿不能改成“4090已验证”。

授权边界：读取源码、构造计划、隔离代码/host测试可以继续；GPU性能测试按单GPU实验锁与既有维护授权执行。研究文档不授权停生产、改驱动/initramfs/bootloader、加载内核模块或更换线上权重。需要这些动作时，先把差异、资格、恢复和具体维护步骤准备完整，再依据已有授权决定是否执行；确实缺授权才提交具体审批，不用本文件制造泛泛确认流程。

## 2. Q 分支的共同评价合同

Q实验不能只做prompt短问答或perplexity。最低工作集应包含真实Java编译/单测/修复、工具调用schema与多轮状态、长context首/中/尾检索、跨文件依赖、持续会话、失败重试和实际sampled/thinking请求。输入/输出预算须符合131072总上下文。

教师强制层面记录hidden/logit误差、top-token margin与变更、router集合/权重、GDN状态漂移、KV误差；这些用于定位，不替代任务质量。自由生成层面记录功能oracle、长任务time-to-success、重试数和预算耗尽。

统计采用包内预注册协议：有效模型失败进入配对4格表，不能从性能/质量样本中删除；infra失效单列；OOM、state污染或hang是硬失败。质量非劣界若选成功率差-2个百分点，必须用适当配对置信界与足够样本，30任务筛选不能证明细小界。零discordance时不能用退化bootstrap产生的[0,0]宣布通过。

即使允许展示质量换速度，也分别报告Pareto和失败案例，绝不把非劣未通过写“质量保持”。研究结果需同时给有效提交token/s和任务时间，防止模型少说、早停、漏工具调用造成假提速。

## 3. P10-01：低位权重与敏感度分配（O52/O53，归P08实施）

**现状：** 当前包已是混合量化：偶数expert IQ2_XS GU/IQ4_NL down、奇数IQ2_XXS GU/Q2_0 down。不是所有矩阵IQ3_XXS，也不能假设还有统一从3bit降到2bit的空间。

- [ ] 先列整个model tensorinventory、actualbpw、尺寸、CPU/GPU访问比例和数值敏感度；文件更小、实际省内存与decoder更快分别证明。
- [ ] TQ3/TQ4、EXL3或其他格式做独立converter/loader/kernel资格，不把dense27B完整GPU驻留的结论套到CPU专家占主导的hybrid模型。[D1][D2]
- [ ] 在校准集选择per-layer/per-expert位宽，再冻结modelhash进holdout；校准器不得看holdout。
- [ ] 权重导出、模型许可和decoder许可分别核对。实际copy EXL3 MIT或tqLLM Apache-2.0代码时保留对应通知；研究机制不自动授权第三方权重再分发。

**拟新增开关：** 不用运行时含糊的“turbo”位；候选通过独立model manifest指向具体包。`STRATA_LAB_WEIGHT_PROFILE`仅可作为拟议显式资格入口，默认无。

**必测/Stop：** 真实GU/down格式都有内核，目标4216没有VBMI/AMX的fallback可执行；完整任务质量和128K轨迹。若格式更小但CPU解码慢、显存多出的expert不足、或量化误差失败，退出。详细实现与rollback见P08。

## 4. P10-02：减少expert/top-k/tail-skip（O54）

**现有锚：** `src/core/expert_source.cpp::tail_skip_rank/set_tail_skip_rank/expert_pool_dispatch_multi`。main已有相关入口，先记录其实际effective值；不能把已有近似隐去再拿它当原模型baseline。[S1]

**机制与轨道：** 跳过本来router选中的expert直接减少CPU/GPU工作量，同时改变MoE输出，明确Q。若丢弃tail后重归一化route weights，又是额外语义变化，应分开实验。

- [ ] 统计每层route weight分布、miss字节、tail贡献的输出范数与真实关键路径；weight小不保证最终影响小。
- [ ] 单因素比较固定top-k、weight阈值、tail rank。每组有完整原top-k控制；不要同时改defer或KV精度。
- [ ] 所有token记录选中/跳过expert数量、权重质量和实际省bytes。报告困难样本及route近tie稳定性。
- [ ] 质量通过前不更改默认值，也不让服务器自动根据负载降expert。

**拟新增实验配置：** `STRATA_LAB_EXPERT_PRUNE_POLICY=off|rank|weight`、明确阈值和renorm布尔值；均未实现，默认off，优先复用已有tail-skip可配置入口而非再造同义参数。

**必测：** 全部/无/一项跳过、阈值边界、负/非有限权重拒绝、router ties、longcontext、Java/tool任务、spec接受变化和restore后同配置。**Stop/rollback：** 质量失败或省时来自更早输出EOS而非同任务完成；恢复原top-k和combine semantics，丢弃带该近似identity的snapshot。性能再高也不能改标E。

## 5. P10-03：CPU轻expert跨层延后（O55）

**候选源码：** PR #2690 head `2e57231c067d50952a29e9b3dfc8ba221010608b`，标题声明 `STRATA_VERIFY_DEFER_CPU=1`，轻CPU rows在下一层FFN半段加入、默认阈值0.1。此参数是PR候选能力，不是当前main已合入结论。[P1]

**机制与轨道：** 弱贡献不再阻塞当前层，但下一层前部看到不同hidden state，改变网络依赖，明确Q。它与DALI/HybriMoE只提前搬运不同，不能因为expert最终算了就叫exact。

- [ ] 逐函数审阅当前Verifier的layer pre/post、residual、GDN/QSA位置，明确延后结果具体在哪个张量相加。
- [ ] 先一个层、一个轻expert的受控oracle，再完整轨迹；与原层及时join、减少expert、prefetch各自分开。
- [ ] 末层、EOS、拒绝、部分接受、cancel和请求切换必须drain或丢弃明确归属的pending结果，禁止跨token/会话注入旧贡献。
- [ ] pending队列有 `(request, token, layer, epoch)`和容量界；没有准时结果时的行为写进模型实验定义，不能随线程时序随机改变算法。

**拟新增/候选开关：** 仅使用该PR定义的opt-in及显式threshold；迁入前日志标PR commit，迁入后记录actual pending/late/drop counts。任何改名仍默认off。

**必测：** next-layer读state前后、最后一层、长GDN轨迹、top-k变化、CPU延迟注入、spec rollback、工具stop/取消。**Stop/rollback：** 无法证明pending归属、数值/质量失败、仅吞吐好而time-to-success差。恢复原层内join并等待自己的在途任务退出后释放，不能直接释放pending内存。

## 6. P10-04：激活稀疏、预测跳算与target早退（O56及研究扩展）

**依据：** PowerInfer将预测的神经元稀疏与CPU/GPU分工结合；其适用的激活稀疏性不能从Flash-Next已有MoE路由稀疏自动推得。[D3]

### A. 激活稀疏资格

- [ ] 先采真实GU/SwiGLU输出分布，统计严格零、近零阈值、空间聚类和稀疏模式稳定性；校准样本与holdout分开。
- [ ] 证明严格零跳过不会引入额外舍入/非有限差异后，才可考虑E/N；基于近零、预测漏召回或不同激活函数的跳算归Q。
- [ ] 测predictor本身CPU/GPU/RAM费用及gather/indirect访问；稀疏矩阵理论FLOPs不等于本机可省wall。
- [ ] 若必须改训到ReLU类结构才能获得稀疏，资格卡明确新checkpoint和训练预算。

**拟新增：** `STRATA_LAB_ACT_SKIP=off|exact_zero|approx`和threshold/predictorhash，均为设计，默认off。**Stop：** 真实稀疏率不足、predictor费用过大、需改训超范围或质量失败。

### B. Target层早退资格

这是一条尚未证明适配的Q研究假设，不能称现有Strata能力。**target早退**跳过目标模型后续层，改变模型；P04里的**draft提前停止**仅改变proposal长度，二者不能混称。

- [ ] 先离线采不同层hidden与final logits，测试有无可用早退head/置信信号；不存在匹配head则不实现线上路径。
- [ ] 设计跳层后GDN/conv状态如何继续。若该token没执行某recurrent层，下一token缺失真实state；不能只跳过logits计算却假装长期状态未变。
- [ ] 选择要么单独训练/定义新的recurrent模型，要么补齐必要state更新。若补齐后几乎无省时，就退出。
- [ ] 早退预算、层集合和confidence校准冻结，Java/tool/长序列重点评估；只看单tokenlogit一致不够。

**拟新增：** `STRATA_LAB_TARGET_EXIT=off`；任何非off值必须绑定完整head/state semantics manifest。**Stop：** 无可解释的recurrent state、状态补齐吃掉省时、质量失败或误把draft早停当target早退收益。默认部署不包含此分支。

## 7. P10-05：额外QSA/KV筛选、历史淘汰与recurrent精度（O57及研究扩展）

**现有锚：** `src/kernels/cuda/qsa_select.cu`、`qsa_decode_attn.cu`、`src/core/layer.cpp::qsa_kv_resolve`。当前模型已有QSA选择逻辑；再次缩budget属于新质量变化，不能认为训练好的稀疏结构还有免费的二次裁剪空间。[S2][S3]

- [ ] 先记录原selector的访问预算和页/cell分布，再对Quest类页筛选、近期窗口或历史淘汰做独立Q实验。[D4]
- [ ] `selector recall`只说明相对于一个oracle选择的覆盖，不等于attention output或任务质量；测漏掉高贡献位置以及首中尾、periodic、跨文件弱点。
- [ ] “只保留top块但原KV仍存着”仍是近似计算；“历史被压缩/删除”还改变后续恢复能力，两者分开。
- [ ] spec未提交区域与snapshot元数据必须和当前选择合同一致；prefix编辑后不能沿用旧selector状态。

**拟新增：** `STRATA_LAB_QSA_BUDGET`、`STRATA_LAB_KV_PRUNE_POLICY`，默认原budget/off；研究参数与model身份一同保存。

**Recurrent state精度资格：** 首先盘点main及候选PR现有精度选项；已有GDN chunk路径使用FP16暂存，不能把“暂存用FP16”推断成“持久recurrent state已量化”。同样不能未经查证宣称要首次引入低位state。P10只要求资格卡精确区分persistent state、临时matmul operand和activation precision。新persistent低位格式为N/Q实验，必须覆盖完整长轨迹、累积漂移、checkpoint/restore、reject/commit，不可用一次step parity代替。[S4]

**Stop：** 仅低难度检索通过、selector开销抵消attention节省、长工具/Java质量失败、state格式无法精确识别或恢复。回退原预算/原精度并隔离snapshot namespace。

## 8. P10-06：gpu-unlock-ada研究资格（O64，X）

**固定来源：** `JustAResearcher/gpu-unlock-ada` commit `4e7fefcc4923f9e083d5324dc75a7d2f906af77f`，2026-10-24 UTC。README/技术报告公开4090对FP16/BF16→FP32 Tensor issue-rate的约2倍微测，并明确INT8、dp4a、scalarFP32保持接近baseline；应用GEMM的收益依shape而变，不能推成2倍Strata。[X1][X2]

当前实际驱动610.57.04/kernel6.1与公开匹配4090测量中的615.78.08及其他kernel组合不同。项目构建使用固定610.43.03输入也不等于证明610.57.04已验证。RTX4090设备ID、板卡、boot流程、驱动交接和数值必须逐项资格，不能从“同Ada”外推其他型号。

### 阶段一：只读资格与性能上界

- [ ] 统计Strata真实关键路径上受影响FP16/BF16→FP32 Tensor指令/算子的份额，分prefill、verify、draft。CPU专家、IQ/dp4a、PCIe、INT8 attention不按2倍缩放。
- [ ] 以受益关键路径份额f给条件上界 `1 / (1-f+f/r)`；r来自对应算子/shape实测才有预测意义。微测r≈2只能作为假设边界，不能作为应用实测。
- [ ] 审阅固定SHA的源码、firmware来源hash、device admission、post-FLR/readback检查、数值测试和已知限制。host mock通过不是硬件unlock成功。
- [ ] 准备stock基线、完整版本清单、可恢复的原boot/driver配置、维护流程与原始记录模板。此阶段不加载模块、不解绑driver、不安装包。

### 阶段二：仅在具体维护动作已有授权后

- [ ] 在隔离可恢复维护环境按该固定版本的官方流程验证；不自动把实验boot状态持久化到生产。先确认实际device和操作对象。
- [ ] stock/unlocked同power cap、同温度/频率稳态、同任务/模型/配置，分别检查数值、CUDA错误、GPU健康与长运行稳定性；单次boot或短微测不足资格。
- [ ] 最后才跑真实Strata请求，保存任务质量、TTFT、wall、功耗/温度与关键路径占比。不用module加载成功当unlock成功。

**Stop：** FP16/BF16 Tensor关键路径份额很小、驱动/板卡资格缺失、没有可用恢复路径、任何验证读回或数值不符、GPU错误/不稳定，或收益只存在寄存器微测。无需为了完成64方向而实施X分支。

**Rollback：** 使用预先核对的stock启动/配置恢复并验证GPU健康；若官方报告firmware DMA未停止，遵循其明确的保留buffer/断电恢复约束，不能强制卸载仍在使用内存的模块。本文件不提供无人值守安装/boot变更脚本。

**代码与许可边界：** 项目Linux module/packaging/payload integration是GPL-2.0-only，NVIDIA firmware另有条款。[X1] 研究或独立维护实验不需要把其模块代码复制进Strata；若以后分发此组件，单独核对该具体分发物，不用MIT标签覆盖firmware/payload来源。

## 9. P10-07：zapabob/Strata与Spin8/TurboQuant资格审计

**固定fork快照：** `zapabob/Strata` head `9fcece0adb1c07ad25d844516d6c4546806dc16a`，2026-10-25 UTC。fork宣称的发布版本、Windows/CUDA13.3/其他GPU结果不是本机Debian12/CUDA12.3/Flash-Next 4090能力证明。[F1]

关键反证必须保留：fork `_docs/repair-20261025/claim-corrections.json` 主动撤回若干v0.3.0静态placeholder模型资格；`release-qualification-v2.json` 仍将DeepSeek真实执行、部分模型RAM资格列为BLOCKED/PENDING。[F2][F3] 因而不能把README吞吐表或CI绿当实际模型验证。这里不推断全部fork代码无效；每个可移植diff独立核验。

- [ ] 建立固定merge-base与main/fork差异清单，按文件分为前端/包装、配置、GPU kernel、model adapter、测试与声明。不要按“fork更大版本号”整体替换upstream。
- [ ] 对 `src/core/spin8_attention.cpp`、`include/strata/core/spin8_attention.hpp`、`spin8/src/query_v3_cuda.cu` 等实际候选，从公开入口追到目标generate/verify调用；存在文件或测试target不代表真实Flash-Next热路径使用。[F4][F5]
- [ ] 每个TurboQuant/Spin8相关声明说明所处理的模型架构、tensor形状/格式、数学变换、数值类别、sm89分支和编译条件。DeepSeek MLA或其他模型的优化不能直接搬到QSA/GDN。
- [ ] 先在main锁定的隔离worktree移植最小diff，使用已有reference和真实目标模型做数值/状态/质量测试；Windows发布binary不能代替Linux源码可构建性。
- [ ] 核对每个引用数字的模型完整shards、真正生成日志、硬件、hash、raw telemetry和对照。缺任一关键证据保持`source_reviewed`或`BLOCKED`。

**拟新增开关：** 不预先发明 `STRATA_SPIN8_FAST=1` 等未经源码确认的选项；资格后才由实际补丁定义，默认off。**Stop/rollback：** 无真实调用链、缺模型shards、只占位资源数字、claim已撤回、形状/架构不匹配、数值或task质量失败。成功部分只移植最小有效diff，不继承整fork的未验证宣传。

## 10. P10-08：功率、频率与热稳态（O63）

- [ ] 先只读记录stock power limit、实际频率、温度、throttle、持续请求能量/吞吐。生产已有performance+C6off固定保留，不重复计算旧收益。
- [ ] 功率上限/散热/频率实验仅在已有维护授权内，arm使用相同host设置；不与gpuunlock或新kernel同时变化。
- [ ] 以至少覆盖热稳态的持续任务比较（计划可预注册30分钟），记录task成功、wall、energy/task及尾延迟；时间长度是实验设计，不是声称已测。

**Stop：** 只短boost有利、长运行降频/错误、能耗收益靠任务未完成、主要瓶颈在CPU/DDR。**Rollback：** 恢复明确保存的原值与配置，再验证实际effective值。无必要不更改系统设置。

## 11. 组合、交付与研究停止的完成定义

先独立完成O54 prune、O55 defer、O57 sparse、P08 quant各自曲线，再最多组合少量互补候选。两个各自通过的Q变化不保证组合质量通过；样本选择/阈值不得在holdout反复调到刚好通过。

交付是以下任一：①有实机数值/状态/质量/性能证据的最小候选；②明确NO-GO及可复现反例；③因缺模型/硬件/许可/授权而标明具体条件的BLOCKED研究卡。没有实施激进分支也可以完成本计划的资格工作。

每张卡都要附原始数据位置、引用、实际执行命令/版本、未执行项和恢复验证。技术假设、公开作者实测、静态检查、host测试、本机GPU测试、真实任务结果分别标注；不填预计4090tokens/s，不把论文倍率写成收益承诺。

## 12. 一手来源

[S1]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_source.cpp
[S2]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cuda/qsa_select.cu
[S3]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/layer.cpp
[S4]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/gdn_chunk.cu
[P1]: https://github.com/Niko1221/Strata/commit/2e57231c067d50952a29e9b3dfc8ba221010608b
[D1]: https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/docs/reference/formats.md
[D2]: https://github.com/turboderp-org/exllamav3/blob/da68d57de61781e5b74ad68698ac4caf36408d7a/README.md
[D3]: https://arxiv.org/html/2312.12456v2
[D4]: https://arxiv.org/abs/2406.10774v2
[X1]: https://github.com/JustAResearcher/gpu-unlock-ada/blob/4e7fefcc4923f9e083d5324dc75a7d2f906af77f/README.md
[X2]: https://github.com/JustAResearcher/gpu-unlock-ada/blob/4e7fefcc4923f9e083d5324dc75a7d2f906af77f/docs/evidence/rtx4090-pr1-matched/README.md
[F1]: https://github.com/zapabob/Strata/commit/9fcece0adb1c07ad25d844516d6c4546806dc16a
[F2]: https://github.com/zapabob/Strata/blob/9fcece0adb1c07ad25d844516d6c4546806dc16a/_docs/repair-20261025/claim-corrections.json
[F3]: https://github.com/zapabob/Strata/blob/9fcece0adb1c07ad25d844516d6c4546806dc16a/release-qualification-v2.json
[F4]: https://github.com/zapabob/Strata/blob/9fcece0adb1c07ad25d844516d6c4546806dc16a/src/core/spin8_attention.cpp
[F5]: https://github.com/zapabob/Strata/blob/9fcece0adb1c07ad25d844516d6c4546806dc16a/spin8/src/query_v3_cuda.cu
