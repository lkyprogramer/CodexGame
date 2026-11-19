# 03 — Donor 底层架构：可借机制与不可混用的性能合同

审计日期：2026-11-15，北京时间。本文解释“为什么快”及其实现代价，不替代当前部署绑定与统一验收门。
本轮只读固定源码与作者一手材料，没有构建、运行模型、下载权重或执行GPU实验。
机制存在、硬件可执行、质量通过、端到端收益成立，是四种不同结论。

## 1. 固定版本与项目定位

| 对象 | 本轮固定版本 | 定位与证据范围 |
|---|---|---|
| YASAKANI | [v0.1.3 / 274d70967f013dc197888dfec233681ddd386012][y-commit] | Qwen3.8-27B特化的权重、activation、块式draft、verify与runtime联合设计；作者5090，非4090实测 |
| yasakani-Unlocked | [rtx3090 / 3131d9a285f476bbbdbd55730bb4b3a16706a285][u-commit] | 基于91a5178的老兼容fork；ahead 5，无tag/release；调优值原样 |
| OSAKANA | [main / 40c8a0554f1863e612eb5e045532ddf23b4ac8ae][o-commit] | 单个initial commit，无release；llama.cpp框架承接YASAKANI trellis，并加QSA、tree、copy-edit |
| TensorFold | [v1.2.9 / 6b9de695104b6b8b30c20458da87ac06c9480289][t-commit] | Native Zig多family runtime；本轮深入的是27B CUDA DFlash2/verify路径，不是整个多硬件矩阵重新验收 |

YASAKANI tag是直接指向commit的轻量tag。
TensorFold v1.2.9于北京时间09:22:59发布；annotated tag对象539dc9d6044cad545cae3abeb019bb8fe202d35a解引用到上述commit。
其release字段target_commitish=2ba55ec7…是parent，不应拿来代替真实tag目标。
TensorFold main=643db947…已在tag之后；本文源码链接均固定真实tag commit。

## 2. 权重、activation与乘法：四者不是同一种数值合同

| 维度 | YASAKANI / 老Unlocked | OSAKANA | TensorFold 27B CUDA |
|---|---|---|---|
| 权重来源 | 专用.yskn trellis；quality主体混3/4bit，fastest主体3bit | 同一YASAKANI speed码流以GGUF新类型YTR3/YTR4承载，另加QSA indexer | MLX affine group64、ModelOpt NVFP4/FP8、EXL3 mul1等不同格式 |
| 运行读取 | LNORD repack，查LUT8，临时生成INT8 operand；非整模INT8常驻 | 原生trellis查表，INT8 operand与INT8 activation做MMA | 专属tiled layout；按格式选择BF16 row kernel/量化读取路径 |
| activation | signed H512、FP16 rounding、每512值amax量化到INT8 | 对应trellis/activation int8协议及融合prologue | 默认prompt BF16；可选FP8/INT8 prompt不是同一数值路径；verify固定row算术 |
| 局部乘加 | m16n8k32 s8×s8→S32，配套fixed-point scale/S64聚合 | s8 MMA与该实现的scale/融合finish | BF16 TensorCore/FP32局部归约或对应格式kernel，不能统称W4A8 |
| 与现有GGUF兼容 | 不能直接使用UD v3.1 GGUF | 文件扩展名GGUF不代表现有GGUF reader/kernel支持YTR | 不能把MLX affine/EXL3 kernel直接套到现NInfer codec |

[YASAKANI FORMAT][y-format]、[loader::build_lut8_tau][y-loader]与[lnord.cu][y-lnord]给出完整链条：
FP16字典先按gamma=maxabs/127转LUT8，row scale吸收gamma；实际推理误差包含这一步，并非无损恢复BF16。
输入Hadamard/round/amax量化与码流布局相互配套，不能只拿一个MMA替换现有浮点GEMV。
LNORD的S64聚合保证自身fixed-point协议对归约次序稳定，不保证原BF16或NInfer现有浮点结果bitwise不变。

[Trellis转换说明][y-convert]还包含Hessian/输出侧统计、Viterbi选路径、误差反馈与校准分布。
draft针对已量化target适配，因此作者最终tok/s同时受权重、activation、drafter和kernel影响。
OSAKANA的[YTR实现][o-ytr]重用这类思想并融合residual、norm、下一product输入quant；这不是保持现codec的“小补丁”。

## 3. Verify geometry：行数、树节点数、输出token数不同

对一个验证回合，应按依赖图的完成路径组织归因，而不能只看接受率：

\[
T_{round}=\operatorname{CompletionPathTime}(DAG_{proposal,target,accept,commit,host}).
\]

\[
R_{effective}=\frac{\text{最终可见且提交的token数}}{T_{round}}.
\]

proposal、target、accept、commit、host可能异步重叠；该记号表示包含已证依赖与等待的完成路径，不是某个已实现计算器。依赖缺失就保留UNKNOWN，不能把重叠段时长直接相加。

### 3.1 YASAKANI：8/16行是同一链的批宽

[SpecxT::generate][y-spec]按frontier token加候选运行verify，逐前缀比较，首失配用target token，再提交实际接受前缀。
8/16并非8/16个独立会话；gamma最多15，main pass行数最多16。
[lnord_dispatch / lnord_kernel][y-lnord]对M≤8、M≤16选择不同tile与占用率配置，16行共享权重读取也增加寄存器/工作量。
YSKN_BLK16默认自适应，结合B8 full-accept EMA、B16额外收益与周期probe，不是固定16总赢。
这些只为已有宽窗路线提供外部实现例证，不能以项目名变化重开H3 W6、W8/W16。

### 3.2 OSAKANA：树与wide copy是两条验证路径

[common_speculative_impl_draft_dflash::draft_tree][o-spec]从一次block的top-K/selector lattice作best-first展开。
online conditional landing估计path survival，生成parent-closed树，再转DFS顺序供混合state kernel处理。
默认launcher设置15个draft节点；源码可选7,15等budget，但默认不是多budget动态切换。
旧lattice复用由LLAMA_DFLASH_TREE_REUSE控制，默认0；不能把默认运行描述成“每轮都复用branch免draft”。

copy路径可提议最多63 token；[server-context][o-server]通过稀疏snapshot stride及必要尾部replay支撑宽窗回滚。
tree要求stride=1；63-token copy不等于63-node树。
LLAMA_COPY_EXTEND默认off，源码明确其在code/structured output可能扩大verify成本多于落地收益。

### 3.3 TensorFold：真wide共享权重pass有硬件门

[Affine4Kernels::verifyRows][t-affine]：GB10 PDL路径可128行，经过筛选的sm120可32行，其它路径通常16行。
所以API窗口含64行，不等于4090一次matmul读权重服务64行。
[cuda_projection::project][t-project]把prompt GEMM与native row-invariant verify分开；verify可由多个16行tile完成。
[分段split-K实现][t-gemv]让不同projection保留各自slice与固定归约顺序，避免合launch时改变算术。
不能把GB10宽窗/cluster结果直接外推到sm89。

## 4. GDN、conv、KV、indexer：接受路径的提交必须一致

| 引擎 | 临时验证状态 | 实际提交/回滚 |
|---|---|---|
| YASAKANI | verify保存所需中间量，不永久推进GDN S/hist | replay实际接受行；KV候选尾部按pos截断后覆盖；分支命中另需promotion |
| OSAKANA | DFS depth栈保parent；GDN记录key/decay/delta；conv按祖先taps | accepted path replay；attention与QSA indexer共同compact；repool改写尾块 |
| TensorFold | parent-live slot调度；log保每节点更新；单行可有before快照 | replay accepted path、conv取最后accepted row、KV按path compact；空路径恢复before |

[YASAKANI replay_commit / replay_fence][y-engine]用普通stream/event把accepted-state replay与不读已提交state的next-draft重叠。
这不是两轮main model并行，也不是发明新的GDN代数；与已有K1/K3邻接设计须判重。
[OSAKANA spec_tree_keep / spec_tree_compact][o-context]处理KV与indexer一致性；CUDA不支持的row move有host fallback与同步，不是无条件GPU-only。
[TensorFold tree_slots::Builder.visit][t-slots]最大子树后访问、复用parent slot，原row id不变；[q35_slots][t-qslots]消费该schedule。
[TensorFold Cache.keep][t-cache]与[keep kernels][t-keep]分别处理GDN、conv、KV，不可只看logits相同。

TensorFold TF_QWEN_KEEP_LATE是默认关闭的opt-in，源码还记录其copy曾失败served chats；不能当成熟默认优化。
这些机制说明“回滚正确”包含多个owner，而非KV len减一；不为已关闭K1追加新的实验资格。

## 5. Draft head：降低proposal成本不等于剪target词表

YASAKANI [load_shead / bdr_block_impl][y-engine]与[launch_bdr_shead][y-bdraft]采用：
rank512近似扫完整词表 → 约512候选（可配置）→ 全维INT8 head重打分 → top16候选。
OSAKANA [ytr_shead_try][o-ytr]是rank512 sketch → 960候选（1024含tie slots）→ INT8全维重打分。
“exact rescore”仅针对其已存的INT8 head，不是原BF16无误差。

两者均应只影响draft proposal，main target仍完整verify；漏召回会降低接受率，不能保证最终更快。
**YASAKANI的0.17GB是作者估算bytes/pass，不是sidecar总VRAM。**
sidecar还保留V×H的完整INT8 head与V×512 sketch等；不可以0.17GB申请显存预算。
NInfer现有静态131072行optimized proposal head已存在，H2进一步裁剪/稀疏投影也已有规划。
因此本包只把该设计作为H2旧计划细化，不称新路线，也不直接搬.shead。

TensorFold [draft_frame::scan / logitsOf][t-frame]按token范围选择较窄draft head；遇范围外token后退full head。
这不是把中文/日语target词表永久砍掉。
top-K与selector projection仍下载到host，forward含stream.synchronize，不能说整套draft已无host同步。

## 6. Runtime与资源生命周期

YASAKANI的[continuation/snapshot][y-spec]是严格prefix extension与单份snapshot，不是任意多prefix paged LRU。
[snap_save / snap_load][y-engine]主要保存GDN、conv、draft ring等；不是可跨engine搬运的整份attention KV checkpoint。
host RAM充足不等于GPU能无代价容纳更多会话。

OSAKANA默认launcher单slot、Q8 KV、262144容量，开启shape graph cache与draft GPU argmax/top-K。
[README][o-readme]自报峰值26.8GiB，**默认配置不fit RTX4090 24GB**。
TensorFold [cuda_recurrent][t-recurrent]按ordered stream lease管理scratch，[Cache.overlay][t-cache]把互斥before/log区间重叠。
节省workspace不等于自动把prefill峰值余量变成热门MoE expert cache。

最新TensorFold [v1.2.9 tagged commit][t-commit]提供反例：
group draw多一个top-K launch并同步下载整个batch buffer，使GB10单流sampled chat相对前版回归约10%。
修复是单流回per-stream draw、两流以上保留group，不是“一律再融合”。
单流与并发摊销条件不同；这个反例比照抄其速度表更有迁移价值。

## 7. QSA语义与性能表的读取方式

OSAKANA QSA shared frontend实际在[qwen4exp.cpp][o-qsa]。
树节点祖先所在块总可见，普通sequential QSA则可能让这些块竞争top-K；两者不是严格相同的稀疏算子。
accepted-path compact后会repool最近受影响块，restore则rebuild，raw indexer ring8192不等于target KV只留8192。
README的192K检索177/240=73.75%；dense早前222/240=92.5%还使用不同权重，既有质量风险也不是严格ablation。
LLAMA_QSA_DENSE=1提供dense路由，不保证同容量、同速度。

| 测量来源 | 可以说明 | 不能说明 |
|---|---|---|
| YASAKANI官方5090表 | 其自选权重/KV/draft整栈吞吐；TG排TTFT | 当前NInfer同codec增益；所有任务端到端加速 |
| Unlocked 3090自报 | 老fork可运行及有限prompt结果 | 独立复现、4090调优、262K真实prompt服务验收 |
| OSAKANA七任务表 | 5090 greedy单次、copy-edit上限 | 普通Java普遍提速；224K结构输出形状一致 |
| TensorFold GB10 recipe | 同engine不同格式round成本与接受率权衡 | 4090宽窗收益或24GB容量保证 |

YASAKANI thinking-on每任务最快次且试次数不同；thinking-off过滤重复/非请求tool call，规则修订后结果显著变动。
OSAKANA TG=(tokens−1)/(last−first)，不含prefill；其warm prefix TTFT与对方cold prefill不是kernel同条件比较。
仓库旧bench.py/copybench.py不完整对应新七任务曲线；SequenceMatcher相似度也不是编译/测试正确性。
TensorFold EXL3 3bpw在GB10读更少权重、verify更快，但chat接受率降低可让chat反慢；64K峰28GiB也不能照抄4090。
最终适配只使用本包状态：D1条件差量、H2旧计划细化、K-PAIR源码门、M0维护；门统一见[测试协议](10_TEST_PROTOCOL_AND_GATES.md)。

## 固定源码索引

[y-commit]: https://github.com/yasakani-dev/yasakani/commit/274d70967f013dc197888dfec233681ddd386012
[u-commit]: https://github.com/watayuki288/yasakani-Unlocked/commit/3131d9a285f476bbbdbd55730bb4b3a16706a285
[o-commit]: https://github.com/pentaCoxian/OSAKANA/commit/40c8a0554f1863e612eb5e045532ddf23b4ac8ae
[t-commit]: https://github.com/ashhart/TensorFold/commit/6b9de695104b6b8b30c20458da87ac06c9480289
[y-format]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/docs/FORMAT.md
[y-loader]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/loader.cpp
[y-lnord]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/lnord.cu
[y-convert]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/tools/convert/README.md
[y-spec]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/specx.cpp
[y-engine]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/engine35.cpp
[y-bdraft]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/q35_bdraft.cu
[o-ytr]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/ggml/src/ggml-cuda/ytr.cu
[o-spec]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/common/speculative.cpp
[o-server]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/tools/server/server-context.cpp
[o-context]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/src/llama-context.cpp
[o-qsa]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/src/models/qwen4exp.cpp
[o-readme]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/README.md
[t-affine]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/cuda/affine4_kernels.zig
[t-project]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_projection.zig
[t-gemv]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/kernels/cuda/lane_gemv.cu
[t-slots]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/core/tree_slots.zig
[t-qslots]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/kernels/cuda/qwen35_slots.cuh
[t-cache]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_cache.zig
[t-keep]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/kernels/cuda/qwen35_keep.cu
[t-recurrent]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_recurrent.zig
[t-frame]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_draft_frame.zig
