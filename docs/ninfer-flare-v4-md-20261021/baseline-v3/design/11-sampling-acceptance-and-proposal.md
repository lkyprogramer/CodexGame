# 确定性草稿 + Target sampling 验收合同（拟实施，默认OFF）

## 目标与当前状态

生产目标是保持Target输出temperature1、top_p.95、top_k20、presence_penalty0、preserve-thinking、medium；greedy描述proposal策略，不要求最终输出改成argmax。`research_greedy`只代表Target temperature0的独立数值诊断。当前B29 baseline不实施新引擎路径；未来Lookup/mixed/DFlash2/selective的sampling能力必须按本合同及H1-T07/各shape实际资格后才启用。未资格请求继续既有合格Target sampling路径，禁止偷偷改temperature或将fallback算新算法命中。

只复用NInfer已有Target/GDN/KV、processor、RNG、accept/residual/bonus、preview/resolve/commit/stop链；不另造sampler、第二套Target状态或发布者。真正随机draft/TokenTree/general-q分支本轮不实现；如果proposal不是可证明的确定性delta语义，不能套用下面的接口。

## 已有源码seam与证据限度

本地固定O的只读源码：

| 位置 | 已有能力 / 必须重定位 |
|---|---|
| [speculative_target_impl.h](../../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/targets/qwen3_8/impl/runtime/speculative_target_impl.h) | `target_verify_accept`调用`ops::speculative_accept_greedy_drafts`，名称里的greedy是草稿，不是Target必须greedy |
| [speculative_round.cuh](../../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/ops/kernel/speculative_round.cuh) 第59–72、136–199行 | 已有delta-q采样接受、拒绝残差和all-accept bonus |
| [sampling_device.cuh](../../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/ops/kernel/sampling_device.cuh) 第62、133行起 | seed/position/purpose/sub RNG；global count+前i个draft overlay，在top-k前施加processor |
| [public sampling.h](../../../../output/qwen38-27b-4090-ninfer/ninfer-4090/include/ninfer/ops/sampling.h) 第25–69行 | top_k<=0或>=20当前都规范成20；temperature0跳过penalty/filter/count更新，不能用greedy轨证明production processor正确 |
| [CPU sampling.py](../../../../output/qwen38-27b-4090-ninfer/ninfer-4090/tools/reference/qwen3_8/common/sampling.py) 第146行起 | 有delta-q参考，但min_p、top-k tie、随机数/CDF边界与CUDA不全等价，不能直接当全语义或bitwise oracle |

上述O源码不是B29运行镜像的完整构建认证，也不是尚未知B6的GPU资格。H0必须沿P6真实树重定位seam与hash；已观察两个旧采样test为top_k1，不能当作fractional acceptance/residual已经被覆盖。

## C22：实际proposal分布为delta

在已许可历史h、冻结policy/资源/shape及可用request-local信息下，先冻结最终候选链D=(d1…dK)。神经greedy、Lookup、head替换、tail或确定性selector都可产生这条链；每位置实际proposal为 `q_i(x | h,d_<i)=1[x=d_i]`。不是神经softmax、selector score、acceptance统计或词表频率。记录逐位置source和delta合同身份，不伪造full-q向量。

候选允许任意合法确定性token链；分布正确性不要求它是最终prefix下重新计算的神经argmax。原C14同头延长/partial-head截断保留为首版性能与状态简化策略，不是“异头旧tail数学上必然有偏”的定理。如果研究保留异头后旧神经tail，Target必须针对**最终mixed chain**每个实际前缀计算p，MTP/aux仍只按真实commit对齐，不能借旧神经prefix对应Target概率或hidden。

候选决策不得窥视本轮accept/correction/bonus随机数或根据这些随机数挑命中；不得把Target采样结果用于事后筛选并仍声称q=delta。相同历史/冻结policy下tie/source选择要可复现；host延迟feedback只能来自已完成且同epoch的历史轮。若提案用随机选择而没有相应q合同，关闭该新路径并回原合格sampling，不将分数softmax冒充实际q。

## C23：处理后的Target p、接受与残差

p_i是Target在h+d_<i上的实际分布：复用该版本支持的temperature/top-k/top-p/min_p、presence/frequency及其他真实支持processor的**既定顺序和参数归一化**。不存在的multiplicative repetition_penalty不要按别库假设加入。每列penalty历史是committed全局count加本列之前的候选prefix overlay，不能读未来draft/重复计anchor或在未commit时改全局count。Target full token domain不被draft shortlist裁剪。

对delta候选d_i：

```text
accept probability = min(1, p_i(d_i)/q_i(d_i)) = p_i(d_i)
reject residual r_i(x) = max(p_i(x)-1[x=d_i], 0) / (1-p_i(d_i))
                         = p_i(x)/(1-p_i(d_i)) for x!=d_i, r_i(d_i)=0
```

p_i(d_i)=0（含候选不在top-k/p/min_p支持）时必拒绝、残差即p_i；p_i(d_i)=1时必接受，拒绝分支概率0，不执行0分母归一化。发生首次拒绝只发布已许可前缀及一次correction，后续候选不发布；全部接受时从最终prefix的Target p_(K+1)采一次bonus。保持现有purpose分离和支持集处理，不另造随机序列。

独立小词表参考至少精确枚举p=(.6,.3,.1)、d=第二项：接受.3、拒绝.7后余两项比例.6/.7和.1/.7，最终回到原p。仅top_k1/deterministic target的绿色测试不够证明此性质。CPU参考需补齐本次测试所需processor/tie/CDF边界；明确CPU `searchsorted(left)`与CUDA `goal<cum`差异，禁止直接要求不同RNG库相同seed逐token一致。

## C24：RNG、state与输出许可

同一合格路径、相同完整state/seed/实际shape应按既定RNG与恢复合同可重复，eager/graph/state restore分别测。accept/correction/bonus purpose不能互用，lane/budget/stop/取消后恢复不得重复或错用位置。分布等价与pathwise一致分开：普通sampling和speculative可能消费不同purpose/数量，即使同seed也不能以token不同认定失真；也不能以几条同seed输出相同证明总体分布正确。

接受kernel的license(a+1)不是最终输出/状态发布权。EOS/stop/长度预算/cancel必须继续经过executor preview→resolve_pending_batch→commit_preview；按现有preview/resolve/commit处理Target/GDN/KV、aux/index/output。已查sampler会先按license更新token_counts，output preview之后可能terminal截断；不得假称kernel返回时counts已等于最终发布前缀，须保留request终止/新安装清零边界并以生命周期测试证明无跨请求污染。拒绝尾/stop后token不发布到SSE；cache/state按实际commit规则验证。bonus已输出不等于hidden已算，保留原anchor/frontier规则。取消/lateDMA/slot重用以后用独立合法请求验证状态未污染。

## 资格与具名证明

新增H1-T07在现有H1内承担共同sampling资格，不新增整个phase或另一套sampler。H1-T06性能对照前必须满足其硬合同；W8/W16、COPY、head profile、DFlash2、selective分别补其shape/资源/processor组合的实际证据，不能继承成“所有sampling都支持”。

必须保留：DeltaProposal、ConditionalMixedPrefix、ProcessedTargetPrefix、FractionalAcceptResidual、ZeroOneSupport、BonusCommitStopCancel、SeedDistributionVsPath、LegacyFallback八组断言。正常、首拒/中拒/全接受、support外token、真实非零presence/frequency（该版本支持时）、top-k/p/min_p边界、logicalV/physicalW、stop/budget1/2、graph/eager、跨轮restore与lane隔离都进对应参考。

L0布局/整数、L1数值/processor分布、L2同路径seed/state、L3 Target-greedy完整输出诊断分别通过；另做精确可枚举分布与冻结统计检验/样本功效的sampling验证。不得用旧top_k1测试、宽松tie容差、经验通过率或未到新route的fallback代替。GPU缺失/skip、oracle覆盖不全、随机分布不明都保持OFF/BLOCKED；功能数学通过也不是业务性能PASS。

固定源码行号、hash与数学来源详见 [独立源码证据](../../../../output/ninfer-baseline-29-20261020/slim-transition-20261021/sampling-contract.md)，不替代P6未来定位或GPU资格。

## 2026-10-21：根据完成的Baseline收敛首轮方案

278参考与8+2评分已经记账，完整分析见[瓶颈与失败归因](../research/04-completed-baseline-assessment.md)，拟验证顺序见[plans/07](../plans/07-baseline-informed-validation.md)。当前仍仅评估，不实施优化或重新测量。

- B29已测MTP3+生产sampling；O源码已有greedy delta接受器。新增合同不是新的性能收益，不能把旧MTP收益重复计算。首轮只增加有界Lookup/同宽fusion，C1、已资格W4/K≤3；不提前启用H4 proposal-skip，也不把DFlash2/full-q放进首轮。
- 先核查容量终止，再扩宽。97fc7be6的SSE为length，但服务端为context_capacity且KV增长截停计数+1；Core72条也在请求O前1/2 token容量终止。具体请求页ceiling/完整窗口余量/pool原因未证实。预算1/2和页边界须覆盖真实remaining与mandatory alignment，不能靠少发输出或扩大现网内存参数掩盖。
- lossless Target sampling不承诺纠正reasoning重复或功能实现错误。97的无工具reasoning行为、Gson完整8/10、RE003题意/隐藏trim合同不一致分别诊断；后者保留原FAIL但不作模型质量归因。两个Gson失败selector仍unknown，不以同seed换proposal偶然通过证明能力提升。
- 优先验证同宽净收益和非copy无命中开销；有命中/接受数上升仍须包括查找、传输、verify、alignment和commit全成本。之后再按实际条件接受率及整轮成本决定W8，W16后置。
- 生产Core的decode只占本批请求耗时总和13.86%，Pi39条为70.27%。若仅decode快10–30%，对应本批总加速情景约1.013–1.033×和1.068–1.194×，不是已测收益或生产流量承诺；冷长P首包需另解prefill/cache路径。
- 首轮64请求（48配对+4Pi+12自由Java/准备预留）包含在阶段≤240内；12条中至少4条用于自由Java对照，其余最多8条准备。首轮约1–2 GPU小时，正式1680参考请求仅纯请求外推已约20.77小时。任何正式采用仍按design/07与原release DAG，不因范围缩小而豁免分布/数值/质量/容量资格。
