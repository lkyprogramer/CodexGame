# 07 · 原生DSpark、精确验证与动态长度

## 1. 先把目标固定

T06目标是正式Mini固定R3、per-loop KV、固定GGUF量化与sampler。原生DSpark作为proposal，不改变最终目标。`src/models/inkling2-dspark.cpp`来自已有上游工作；Atomic的增益属于整合与执行优化，不能把DSpark本身标为本项目发明。[S01/S12]

当前Metal预算profile不证明普通CUDA或双预算CUDA已支持原生DSpark。每条路径单独记录。正式官方原生MTP的feature visits绑定默认loop数，不能在少轮或更多轮后直接复用。[S02/S14]

## 2. 先固定宽度，再做自适应

实验中统一用：`k=提出的候选数量`，`B=target实际验证的token/位置数`。block8通常含anchor/bonus语义，不能把8都记为accepted候选。引擎日志必须公开k、B、已接受候选数、最终emit数。

顺序：AR → k=1 → k=3 → k=7（仅模型/实现允许）→最佳固定k →自适应k。每种宽度先greedy，再sampling。图和低层kernel的不同B路径都要过同样的正确性门。

## 3. Greedy验证

候选x_i由同分支有效prefix x_<i 的最终目标next-token logits验证，使用同样的tie-break、EOS、grammar和logits processors。仅最终确认的连续前缀可以对外stream。首个拒绝后丢弃该位置之后的所有未确认状态，由目标模型产生corrective token并继续。

强制比较：拒绝位置0..k-1、全接受、EOS在候选中、stop字符串跨token边界、空/短输入、跨SWA覆盖、接近capacity。后续至少再串行生成64tokens，以检测“当前输出一样但状态已经错”的问题。

## 4. Sampling分布合同

对同一prefix，p为**最终实际目标采样分布**，q为**真正生成候选的提案分布**，都已经按各自实际温度、top-k/top-p、mask、grammar和penalties处理。

候选y的接受概率：

`a(y) = min(1, p(y) / q(y))`

拒绝后的恢复分布：

`r(x) = max(p(x)-q(x),0) / sum_v max(p(v)-q(v),0)`

手算负例：p=(0.8,0.2)、q=(0.4,0.6)，接受质量为(0.4,0.2)，拒绝总质量0.4；正确残差只选第一个token。若拒绝后直接从p再采一次，最终得到(0.72,0.28)，已经不是p。

必须实现small-vocab枚举检验、错误residual负例、q为one-hot时的检验，以及多步条件分布测试。q(y)=0却产生y、理论不该出现的空residual、NaN等均为实现错误，不能静默重新归一化为另一个目标。

完整spec算法的精确性包括tree/多branch的条件分布，不能只贴上上述一维公式。2DSD的额外约束在11。

## 5. 完整状态事务

依赖05的checkpoint协议。每轮以committed prefix为边界，候选使用分支私有的可写状态。卷积滑窗与环形KV被原位覆盖时，单改length不能回滚；要记录delta、COW或可重算的完整checkpoint。

外部cancel与投机reject不同：cancel可能结束整个请求并释放会话slot；reject只撤销候选后缀并继续同一请求。两者都要等异步lease安全退役。接受/恢复RNG事件不能因reject无条件回拨。

## 6. 如何判断真的加速

每轮记录：draft、target verify、调度、copy、rollback、等待时间，以及最终emit tokens。端到端有效TPOT用总wall time除总emit，不能除proposed tokens。存在重叠时不能把CUDA event时长简单相加当wall time。

粗略决策：

`spec有效TPOT ≈ E[T_round] / E[最终emit数]`

与同配置AR的真实TPOT比较。接受率高仍可能慢：draft大、head贵、verify形状差、rollback贵、额外草稿器把target挤出显存，都会抵消收益。

## 7. 自适应策略（T08设计）

第一版只在已资格k集合中选择，保留k=0串行。输入来自最近若干轮的接受前缀长度、verify成本、上下文长度和内存余量。用预注册策略比较最优固定k，不从测试集事后挑赢家。

初始可用host选固定CUDA图；随后测device-side条件图。conditional SWITCH是工具链/API能力单独探测，不写成SM89必有或必无。不可用时仍能运行固定图。

切换k不得改变目标、状态布局或采样事件语义。对每个切换序列做确定性重放，特别是k7→k0、长上下文触发缩短、cancel后下一请求。

## 8. Prompt lookup（独立ablation）

借鉴squid的精确前缀匹配proposal，适用于复制/重构场景。hash只找候选位置，必须逐token比较确认；跨请求复用需模型/tokenizer/数据权限相同。lookup提出的token仍全部由最终目标验证，不可直接stream。

greedy优先实现；若sampling中使用确定性lookup，q是one-hot，不能拿不存在的softmax当q。lookup与DSpark是否仲裁、是否同时提出，要明确协议。复制fixture改善而真实Java任务无益则不默认启用。

## 9. 默认回退

草稿器加载不匹配、资格缺失、内存不足或连续低收益时，回到**同一目标契约**的AR；如果已经更改目标（如LoopCD/last-loop），回退仍必须保留该目标契约或明确开启新会话。日志记录实际路径，不继续贴DSpark标签。

## v2.0 · 成本按运行条件失效

借鉴Magnitude的draft controller，但保留原目标与门槛。成本记录绑定model/representation、context class、active sequences、graph/kernel、驻留比例、KV Tier/Pool、预算和draft/verify资格。任何字段改变生成新CostEpoch，unknown不可填0；plain对照过期时在冻结预算内重测。先离线比较合法固定宽度，再决定是否立项在线控制；不复制上游acceptance prior。成本包含draft、verify、feature catch-up、接受/拒绝回滚、切换、prefill及后台争用，收益看已提交token与完整请求。MGX09/10与M02见[42](42_magnitude_integration.md)。

## v2.1 · 社区DSpark数据与DFlash2候选

mainline DSpark（#32218）社区报告：固定n_max 2–4最好，prose常持平或变慢；默认f16 draft KV可挤爆显存；verify batch大小变化导致graph重建（Vulkan约25 ms/次）。因此§2的宽度顺序改为 AR→k=1→2→3→4，k=7只作诊断；draft KV类型显式等于target并计入容量；记录graph复用；按code/Java/工具JSON/prose分层。

DFlash2（incoai草稿器，S54/S55）作为T06扩展T06-DF2：在DSpark G2后、以最佳固定k DSpark为对照配对比较；#33073转换器与#33049语义交叉核对，不一致即BLOCKED。完整说明见[43 §7](43_upstream_llamacpp_4090_site.md)。
