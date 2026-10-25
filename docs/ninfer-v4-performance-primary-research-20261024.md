# NInfer后续性能方向：一手资料与源码核查（2026-10-24）

**最值得先准备的新假设是“现有MTP/现有W4内改用有精确q记录的随机proposal”，同时保持Target production sampling。** 它直接改善每轮产出，已有同型号4090的源码和作者配对结果作为研究依据；本机尚无general-q入口，不能称为一个小开关。DFlash2有更大幅度并行draft的潜力，但本机收益未测，适配范围大；最小改动仍是已有W6路径的失败修复，但该路径尚无实机收益结果。上述排序是研发投入判断，不是当前机的性能结论。

本轮仅公开资料/源码读取和文档，0 GPU、0模型、0HTTP模型请求、0新构建/测试；未读取远端服务或修改产品。源码与元数据固定版本、下载字节SHA见[来源回执](../output/ninfer-v4-primary-research-20261024/source-receipt.json)。

## 1. 搜索纠正了哪些旧前提

1. **“greedy proposal＋Target sampling”已经存在，不能重新命名为优化。** 当前本地合同明确q=delta；真正不同的新方向是随机q与精确残差校正。这需要更新proposal合同，不能把随机proposal传给旧delta接受器。[现合同](ninfer-flare-v4-md-20261021/design/08-target-sampling-and-baseline.md)。
2. **Qwen3.8-27B的DFlash2公开检查点已经存在。** 官方z-lab项目列出匹配模型；`z-lab/Qwen3.8-27B-DFlash2`镜像`incoai/...`，本次元数据revision固定`50307d4c4cde6860d4eee73e2547cd786fe8e8a4`。不能继续以“无匹配27B资产”为排除理由。存在检查点不代表已有NInfer/SM89/当前codec资格。[固定项目README](https://github.com/z-lab/dflash/blob/07ebd93db9f472af339b644bb70221ad8428328a/README.md)、[模型卡](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/tree/50307d4c4cde6860d4eee73e2547cd786fe8e8a4)。
3. **Flare本身已有按成本与接受历史选择宽度的机制。** 它支持的SM120/121/模型/Graph目录不等于本机SM89资格；应借鉴决策合同而非直接移植完整调度器。[固定MTP设计](https://github.com/NVIDIA/flare-local-inference/blob/d5fd9824593c2a70f6bdc001b39f16b4c5b3b0b4/docs/mtp-design.md)、[前缀存活统计源码](https://github.com/NVIDIA/flare-local-inference/blob/d5fd9824593c2a70f6bdc001b39f16b4c5b3b0b4/helios/src/scheduler/speculation.rs)。

## 2. 首位候选：MTP随机proposal＋精确稀疏q

### 已核查的donor、机制和证据

公开donor为`jram4/ninfer-4090`，本次固定HEAD `70ebb1290dc7abe246c20696a24d21f77faee8d4`（2026-09-24）；核心功能commit `cbf7b7e1c9e736bf8bc4ff95354fd0658447b743`。后者变更23文件、1996新增/67删除，包含约900行测试；不能包装成几行分派修改。它的model目录仍叫qwen3_5，不能凭目录名排除它实际描述的Qwen3.8-27B路线。[功能commit与完整文件列表](https://github.com/jram4/ninfer-4090/commit/cbf7b7e1c9e736bf8bc4ff95354fd0658447b743)。

核心数学是对真实条件proposal分布q，接受概率`min(1,p(d)/q(d))`，首次拒绝后在整个Target有效支持集上用`max(p(x)-q(x),0)`重归一化；全部接受时按Target bonus规则。q可以只含12个token，但Target支持集不能裁成这12个。原始理论允许不同proposal分布；正确性来自接受/残差，而不是草稿必须argmax。[Leviathan et al. ICML2023，v2](https://arxiv.org/abs/2211.17192v2)、[Chen et al. 2023](https://arxiv.org/abs/2302.01318v1)。

| 部位 | 固定源码观察 | 必须保持的本机合同 |
|---|---|---|
| q定义 | `kMtpProposalSupportCapacity=12`；实际top-k为规范top-k与12的较小值，保留温度/top-p/min-p后的真实归一化q | Target的temperature1/top-p.95/top-k20保持原值，q截断不是Target截断 |
| shortlist映射 | selector先通过id_map映射全局token ID，再进行processor、tie与q输出 | q和draft IDs都必须使用同一全局ID域，不能用shortlist行号查Target概率 |
| prefix processor | token_counts叠加本轮licensed token与已产生的prior proposals；不修改全局count | 必须与本地最终许可/前缀定义核对，特别是partial permit、终态和next-round |
| proposal RNG | 新独立`kSamplePurposeMtpProposal=6`，key包含seed和逻辑位置；不是GPU lane序号 | 新purpose在本机无碰撞；不复用accept/correction/bonus随机数 |
| 稀疏接受 | 查真实q(d)，`pd>=qd || u*qd<pd`；拒绝校正遍历Target支持中的每个token减q并clamp0 | q=0的Target token仍可能从残差输出；q/支持必须与实际抽样完全一致 |
| 开销 | 131072行proposal logits的多块partial top-k/group finalize；保留current/next q与IDs | 全量draft forward、selector、verify、mandatory alignment及commit均计入完整轮 |

直接源码：[API和RNG合同](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/include/ninfer/ops/sampling.h#L14)、[proposal kernel](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/src/ops/kernel/sampling.cuh#L106)、[多块分派](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/src/ops/launcher/sampling.cu#L53)、[general-q接受/残差](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/src/ops/kernel/speculative_round.cuh#L146)、[Target接线](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/src/models/qwen3_5/program/speculative/target_verification.cpp)、[下一轮MTP接线](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/src/models/qwen3_5/program/speculative/mtp.cpp#L159)。

这与DFlash2的`candidate_selector_path`不同：后者是top16候选＋rank256边打分，不是本项MTP top12生产器，不能错移其接口或成本。

### 为什么它比继续调小kernel更有潜力

对固定p，delta proposal d的接受率是`p(d)`，随机q的接受率是`sum_x min(p(x),q(x))`。例如`p=(.6,.3,.1)`、`q=(.5,.4,.1)`，若greedy draft为第一项，前者为.6，后者为.9；这是精确算术示例，不是本机提升预测。真实q质量与更贵selector可能抵消收益。

作者公开聚合JSON记录32条温度1的私有工具请求：同一4090上decode rate从127.433到141.556 tokens/s，27/32请求更快；但模型为abliterated variant、K7、K8V4、context188416，输出总token与tool调用数不同，且请求体明确不公开。它只提供可复核聚合结果和代码，不提供第三方可独立重放的32条原始任务，不能当本机+11.1%的承诺或质量证据。[原始聚合JSON](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/results/rtx4090-20260924-sampled/temperature1-replay-summary.json)。

本机与donor一致处是4090、同类Qwen27B、production temperature1与优化proposal head；差异是stock模型、K3/W4、rk4v4、context262144，以及当前q=delta合同。不能跟着移植K7/K8V4/缩context、abliteration或产出倍率。

### 本机适配边界和第一项可证伪准备

独立源码核查反馈：当前H3树`49bee647...`没有`speculative_accept_sparse_drafts`或随机MTP q API，只有greedy delta接受；已有Q4 `[131072,5120]` proposal head＋argmax/remap。因此“已有greedy＋Target sampling”可复用，**general-q verifier必须新增或小范围移植**，不能声称仅补producer接线。

建议第一候选限制C1/W4/K3、既有头和模型/codec/context，默认OFF。影响范围为proposal sampler API/launcher/kernel、general-q verifier、current/next IDs+q双缓冲、prefill与每轮MTP接线、Graph scratch规划；产品默认Target sampler和许可/state authority继续复用。若采用donor兼容`[20,K,B]`存储，C1K3两套I32 IDs＋FP32 q的紧密payload仅960字节，**不含多块selector scratch、Graph和对齐**。源码适配不是直接cherry-pick，donor目录/类型/状态版本与本地不同。 当前缓存snapshot只保存待验证draft IDs，没有与其对应的随机proposal q；跨恢复后只恢复IDs会丢失真实q，不能继续用旧delta合同验证。首筛cache off仅用于隔离这一缺口，生产仍须另立q的保存/恢复/失效生命周期及缓存资格，不能把关闭缓存当作发布问题已解决。

先做CPU可枚举分布及实际q生产合同，覆盖：部分重叠、完全不交、p=q、delta退化、q支持不足Target20、全局ID映射、并列top-k/p边界、RNG purpose和前缀processor、partial permit/终态/remaining1/2。donor的[CPU分布测试](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/tests/ops/test_speculative_sampling_distribution.cpp)只证明其枚举输入的代数恒等，不能替代实际GPU producer/verifier或本机状态资格。本轮没有运行该测试。

性能判断应比较`R/G`：R为完整轮wall，G为正式committed token数。若实际G增长10%、R增长2%，条件性速度比是1.10/1.02≈1.078；若selector使R增长12%，则退化。这个算式仅定义盈亏，不给收益区间。优先试验依据是“改变每轮正式产出、无需新模型或扩宽”，不是宣称一定比W6强。

## 3. 其余可证伪方向排序

| 方向 | 可证伪假设 | 潜在收益与范围判断 | 先停在哪里 |
|---|---|---|---|
| 现有W6/K5 | 增加后两列的实际提交量，足以抵消额外MTP AR和verify成本 | 实现范围最小，准备已做；收益未知。若R6贵20%、G4≈3.9，则G6需>4.68才盈亏平衡，节时10%需≥5.2 | 先修已知新驱动分配/审计缺陷并复用6个PASS；不把失败归为W6无效，不立即开发W8 |
| 请求内成本感知K选择/skip | 低接受片段减少无效draft，节省的draft时间大于多出的Target轮 | 中小范围，须已有宽度Graph和MTP历史吸收；减少逻辑extent却仍执行完整AR不会提速 | 先定量拆分当前Target/draft/head/commit成本；不能从HF oracle/Flare机制直接推本机收益 |
| proposal head缩小或按局部语料选域 | 少读头权重省时，接受率损失低于省下的draft成本 | 已有131072 shortlist，不能重新提“加优化头”。再减域需要资产制作/映射与领域覆盖，不是纯kernel改动 | 必须看到该头在本机整轮占比；Target full head不可裁，中文/Java覆盖不能由词频猜 |
| DFlash2替换串行MTP drafting | 并行块draft减少串行AR成本，并保留合格Target验证 | 长期潜力较大；匹配资产存在，但新5层draft、特征提取、selector、状态与显存适配边界明显大于本项 | 先只读资产/特征/显存差额审计，不加载权重、不借H200倍率、不改context/codec |
| small-T weight-bandwidth优化 | 真实大占比线性层在SM89仍有可避免的重复读/低效分派 | 先前P3已有读一次的small-T；不能从“还有kernel方向”推有大收益 | 若已接近带宽上界或该Op份额小，就停止该方向；先读实测完整profile |

HF 2024官方资料表明动态lookahead以draft置信度提前停止，实验中不同任务每轮最佳长度变化很大；其oracle采用temperature0，不能原封不动当生产temperature1的最优策略。[HF官方，2024-10-08](https://huggingface.co/blog/dynamic_speculation_lookahead)。Flare固定源码的`AcceptanceProfile`使用请求内prefix survival而非单一平均接受率，并将终态后缀视为删失而不是拒绝；这些约束值得吸收，整个运行时不必移植。[Flare统计源码](https://github.com/NVIDIA/flare-local-inference/blob/d5fd9824593c2a70f6bdc001b39f16b4c5b3b0b4/helios/src/scheduler/speculation.rs#L98)。

DFlash2资产配置为5层、hidden5120、block8、selector rank256/top16、Target taps `[5,19,33,47,61]`；元数据列BF16参数1,924,404,480，紧密参数字节约3.85GB。这是参数容量推导，不是加载峰值；新资产量化/后端/工作区另算。模型卡的性能测量为H200、xhigh/4096输出、block8，不能直接归给本机4090、medium/32768。[固定配置](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/blob/50307d4c4cde6860d4eee73e2547cd786fe8e8a4/config.json)、[模型卡条件](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/blob/50307d4c4cde6860d4eee73e2547cd786fe8e8a4/README.md)。原DFlash论文只是并行draft机制的理论/实验依据，不证明DFlash2在该机的净收益。[DFlash论文2026-02-05](https://arxiv.org/abs/2602.06036)。

## 4. 本轮搜索支持的工作方式调整

NVIDIA官方指南明确先找真实应用bulk time、计算可达收益，再作局部优化；不代表必须先新建一套大测量框架。对NInfer，应该先复用当前完整round观测与现有Nsight工具，直接回答Target backbone、MTP AR/head、sampler、commit、host空洞的份额，再选择唯一变化。单个Op快36%而整段只快0.3%的结果不能由“更多局部实验”自动解决。[CUDA Best Practices：Assess/Profile/Amdahl](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#application-profiling)。当前网页为13.4；这里只采用通用归因原则，不将其版本特性当BO13.2运行合同。

原Baseline、已完成任务、评分、18处G1差异和C1缺口保持原样。候选排序允许根据首次实际profile改变。本文不授权任何新实机窗口，不改现网、默认分派、Target采样或Pi输出预算；`p95=null`，无候选/发布资格结论。
