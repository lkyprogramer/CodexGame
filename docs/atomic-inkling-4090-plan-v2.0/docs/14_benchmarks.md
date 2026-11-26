# 14 · 配对基准、统计与真实任务时间

本篇执行G3/G4。门槛来自[01产品合同](01_product_contract.md)，属于工程策略；未实测为`NOT_RUN`。其他GPU/论文数据与统计工具自检不能代替本机验收。

## 1. 冻结对照，分开三类问题

A/B锁定权重、R3、KV、模板/tokenizer、sampler、Pi工具schema、P/N预算、backend/驻留、线程/NUMA、driver/runtime、graph/spec；仅改变预登记因素。系统优化、质量变化、新旧主力替换分别报告；不同tokenizer以同任务内容/E2E比较，不以tok/s排名。

起步generic CUDA串行target-only；离散budget、Inkling新路径、spec分别资格。旧StrataDFlash2未胜MTP spec4及CPU pool/launch overlap无收益，不当作Inkling数据；无新trace不重开。

试验前锁plan：假设、A/B、终点、分层/权重、样本、seed/次序、预热/cache、资源余量、timeout、排除规则、样本数/预算、停止条件。探索用于筛选，确认用独立保留case。

comparison contract保存A/B各自完整能力key、固定因素清单、允许差异清单和配对schedule的路径/hash。完整key不要求相等：AR对DSpark必然改变spec相关维度。`same_target_optimization`必须保持03规定的目标契约；`controlled_numerical_change`仅允许预登记的N类数值变化，必须引用冻结容差表及相应质量证据，不能宣称采样分布精确等价。缓存/guidance等Q类改变该契约时，按独立目标与质量门处理。`cross_target_product`比较旧主力与Inkling等不同目标，固定任务和预算，不能把业务结果包装成同目标无损加速。

## 2. 计时与计数合同

duration来自同进程monotonic clock；UTC只关联事件。跨进程没有已测时钟误差时，不直接相减微秒级timestamp。重叠阶段不得简单相加冒充wall time。

| 指标 | 起止/分母 |
|---|---|
| client TTFT | 发出请求首字节至首个实际模型输出delta；空SSE/role头不算 |
| first visible/tool | 首个用户可见内容、首个完整可执行tool call分别计时 |
| tokenizer/template | messages开始处理至input IDs就绪，client/server分列 |
| queue | 完整请求可调度至获得generation slot；入队前处理另记 |
| prefill | 开始实际计算至首个目标next-token logits；computed/reused分列 |
| engine TTFT | 获取推理资源至首个commit token，含必要prefill/首步decode |
| TPOT | `(最后commit时间−首commit时间)/(commit数−1)`；≤1token时null |
| server E2E | 完整请求到达至最终响应/终态；含queue与序列化 |
| agent E2E | Pi接受任务至产物验收结束；含所有轮次、工具、编译、重试和排队 |
| makespan | 主任务及2–3子任务依赖图整体结束，不把并行工具耗时相加 |

token单列prompt、prefix reused、prefill computed、reasoning、visible answer、tool call、proposed draft、accepted draft、target committed、discarded。吞吐仅以已commit目标token为分子；reasoning、可见文本、工具序列混成一个output数会误导比较。spec成批返回记录burst大小，不伪造逐token独立时间。agent E2E为首要业务结果，接受率只是解释变量。

固定256/1024输出只作synthetic微基准；真实任务自然结束，不忽略EOS。max输出相同不保证实际等长，保存tokens/bytes/finish_reason。

## 3. 缓存、交错与运行纪律

缓存至少三个维度：process cold/warm、OS page cache unknown/cold/warm、prefix cold/warm。核心steady-state比较固定process warm，将prefix cold/warm分开。cold要验证reused=0；warm先priming再计分并验证命中长度。只改request ID不证明prefix miss。模型加载/冷盘恢复另测；不能为了试验擅自drop全机page cache或停生产。

同case/seed配对，按预生成均衡AB/BA、context/cache/task分层。同卡切换构建采用相同预热，加载另计。每5对用anchor监测漂移；温度、功耗、GPU/CPU/IO占用入raw日志。

异常按预登记规则排除/重跑整对并保留raw，不事后挑outlier。多seed/多轮/重复共享case ID，不能充独立样本。单GPU一次只跑一个性能实验。

## 4. PF测试矩阵与规模

| ID | 配对工作负载 | 最低要求 |
|---|---|---|
| PF01 | generic CUDA串行4K/16K，spec off | 3prompt×3次smoke；只判断能否继续 |
| PF02 | 同模型系统/kernel候选 | 每primary cell探索12pairs；确认≥30独立case |
| PF03 | AR、已资格固定k、最佳固定k与自适应k | 全部计入draft/verify/rollback/搬运；目标一致 |
| PF04 | 64K、C128K、P128K cold/warm | 每档12pairs可行性；发布速度结论须补确认样本 |
| PF05 | 真实Pi/Java8任务 | 质量集按冻结任务计E2E；失败/timeout不丢弃 |
| PF06 | 1主+2/3子agent排队，GPU active=1 | queue、session切换、makespan；真并发另测 |
| PF07 | 装载、保存/恢复、容量与offload | GPU/host/SSD峰值、实际H2D/D2H及恢复净收益 |
| PF08 | p95保护与资源soak | 每承诺tail的cell≥200requests；soak≥8h且≥200请求 |

确认至少3个时间块，覆盖短请求、64K及承诺的C128K/P128K、prefix cold/warm。p95即使200请求也须给CI；不足只报观测分位数，tail门BLOCKED。soak含承诺的64K/128K各≥10次及取消/恢复。

## 5. 中位数与几何平均分别报告

### 5.1 产品决策用中位数

先对每个独立case的重复运行取A/B各自中位数。用预登记业务分层权重，给每case权重`w_i=该层业务权重/该层独立case数`；计算A/B加权中位数及`median_reduction=1−median_B/median_A`。按case配对、层内cluster bootstrap至少10000次，重算整个统计量，报告95%CI；不能对独立A/B样本分别抽样。

对应01：单项主要请求耗时中位数至少降低5%，CI支持正收益；主力迁移真实任务中位数至少降低10%，CI支持正收益；关键层p95退化不超过5%且满足绝对SLO。低维护成本的小改动可单独记录，但未达到门槛不独立构成升级理由。容量功能报告新能力和时延代价，不冒称加速。

### 5.2 包内辅助统计工具的范围

`paired_stats.py`预设**单stratum** CSV字段：`pair_id,case_id,stratum,baseline_ms,candidate_ms`。每行是一次合法配对；同case可以多行，但先计算该case的平均`log(baseline/candidate)`，再对case等权取平均并指数化，得到gmean speedup。置信区间按case cluster重采样；独立case少于30时不给CI。输入须为有限正耗时、完整配对、唯一pair_id且只有一个stratum。

该gmean不是中位数提升，工具不计算产品全部门槛，也**不能输出PASS**。若多个分层，应分别运行/报告，再由冻结权重的独立聚合分析形成产品指标；禁止把不同stratum混成单组掩盖长context退化。不要为了得到CI把case重复编号为新case。

### 5.3 失败与置信度

同时报告完成率、成功任务E2E、全部任务的惩罚耗时：失败按预登记wall budget计惩罚，同时保存实际耗时。timeout不能剔除后只报成功子集。质量非劣见[13](13_correctness_quality.md)，速度不能抵消错误工具动作。样本量已到但CI仍跨门槛时记BLOCKED/`INSUFFICIENT_EVIDENCE`；预算结束而未达到工程收益门可结案NO_BENEFIT，并明确不是证明真实效应为零。

多候选用独立确认集或预登记多重比较校正，不能测到显著才停。p95按case/会话聚类，不把200个token间隔当200个请求。

## 6. P128K必须测真实输入

沿用[09](09_long_context.md)：C128K总容量为131072，含输入、预留生成与必要特殊token；P128K是模板后实际输入131072，再生成实际配置的N，capacity至少P+N及实现需要的额外reserve。N必须写入实验计划，不在本篇固定为某个默认值。

保存templated IDs/hash、client token数、server `prompt_n`、实际capacity/reserve、reused/computed、截断标记和finish_reason。硬断言：实际输入达到计划P且零截断。输入包括真实代码/工具历史、中英文需求、分布于5/25/50/75/95%位置的约束及干扰；重复文本只作容量压力。200000/262144为独立扩展行，不能从P128K外推。

warm prefill以computed tokens算吞吐；跨模型保持任务内容，不裁成相同token数。

## 7. 记录与停止

每run保存plan、case/pair/stratum、锁、实际路径/配置、硬件、计时/token、资源、oracle及raw artifacts；缺数据为null+reason。预算沿[04](04_hardware_memory.md)。

状态损坏、重大工具错误、NaN、截断、OOM/swap/headroom违规立即停止；降精度/context须新run。最多两轮有profiler依据的修正，之后结案。未来`tools/inkling-lab/lab.py`调用标 **PLANNED_AFTER_T01**，不假造现成CLI/flag。

## v1.2：自动搜索的确认纪律

[29](29_automated_kernel_optimization.md)把正确性开发、性能探索、独立性能确认和质量holdout分开。最多24候选/4micro/2E2E探索/1独立确认赢家是初始计划额度，必须事先冻结；最终资格仍采用本章与validation-policy原门槛。后看结果改变赢家、shape dispatch或阈值，需要新的独立确认或事前登记的多重/序贯方案。

Nsight用于定位，正式G3不挂profiler/sanitizer。核对实际GPU、非零launch、kernel/case覆盖与输出；编译、PTX检查、arch skip、作者数字、外部CI全部独立分类。报告冷编译/JIT/module load/capture/repack及请求真实承担的成本，包含所有未命中、fallback和失败。Amdahl关键路径估计用于筛选，不能替代端到端测量。

## v2缓存与系统耦合实验

按37的四格矩阵分别比较raw Tier/压缩Tier、raw Pool/压缩Pool、residency和DSpark；不同时改变精度。增加无复用、RAM hit、真实SSD hit、临界/充足容量、后台PCIe/SM/host干扰；完整restore/flush/重算纳入请求和Agent计时。保留原随机化、独立cases、时间分块、bootstrap、失败样本、holdout和停止规则。所有量化/last-loop/guidance变化另立目标，不乘论文倍率。
