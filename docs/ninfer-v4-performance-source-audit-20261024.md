# 当前 NInfer decode 源码复核：先分清已有机制与新增收益来源

本次只读核查29上的 H3 隔离源码，并将15份关键源码按字节与SHA保存到本机。没有构建、GPU、模型或HTTP调用，没有改动远端源码、服务或缓存。连接使用 `ssh -J jump 29`。远端分支为 `codex/h3-w6-existing-route-20261024`，HEAD `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`；此前冻结源树为 `49bee647112ee171de35529028fc271494260751`。HEAD与内容树不是同一个身份；本次逐文件SHA记录不冒充新的构建或运行身份。

[逐文件来源与SHA](../output/ninfer-v4-performance-reflection-20261024/source-audit/source-identity.json)。下述行号均指本次实读源码见证。

## 1. 已存在的机制，不能再记作待开发的优化

| 核查项 | 读到的事实 | 结论 |
|---|---|---|
| Greedy proposal | `TextContext::proposal_argmax` 的两条路径都是 GPU `argmax`；优化head路径还做全局token ID重映射 | Greedy草稿已经实现；不是现在待增加的提速来源 |
| Target production sampling | Target接受kernel对temperature>0使用 `p(d)` 接受、排除d后的残差与全接受bonus；RNG有独立accept/correction/bonus purpose | Greedy proposal＋Target sampling已经存在；现有合同的delta-q不是新的实验 |
| 优化proposal head | `text/draft_head` 固定 Q4G64_F16S `[131072,5120]`，配131072项I32映射；选择Optimized后由GPU执行dense linear＋argmax＋remap | 不是未裁剪的248320词完整head；不能把首次“裁到131072”列作新收益 |
| Target full head | GroupwiseInt端点为 Q6G64_F16S，`text/output_head` 为 `[248320,5120]`；Target verify始终运行全head | Target不能随草稿词表一起裁剪，否则改变Target分布 |
| GPU采样 | full-vocab概率构造走GPU partial-topk/group-finalize两次launch，配置不用CPU回读判断 | 没有证据支持“把CPU top-k搬GPU”这个建议 |
| CUDA Graph | MTP body固定编排，已有Graph executable时直接launch；未准备Graph报错 | 不能把首次使用Graph当成新优化 |
| raw GDN提交 | 许可阶段已有跨层统一 `gdn_replay_fold`，之后同步并更新host账本 | 不能以“48层逐次launch合成一次”解释K1的新收益 |

对应源代码：[proposal head与argmax](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/text_context_impl.h:631)、[资产格式和形状](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8_27b/impl/load/bindings.cpp:336)、[Q6端点选择](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8_27b/impl/load/bindings.cpp:36)、[Target接受数学与GPU实现](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/ops/kernel/speculative_round.cuh:59)、[full-vocab多block分派](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/ops/launcher/speculative_round.cu:59)、[Graph执行](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/graph_impl.h:8)、[许可Fold与同步](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/program_impl.h:1055)。

## 2. 固定物理W4，仅缩逻辑extent不会减少主要计算

当前 `decode_mtp_batch` 由对象的 `draft_window` 决定 `width=K+1`、Graph profile以及传给调度器的K；每个lane的logical extent另外由现有draft数、remaining和context确定。

在固定K3/W4下，把extent从3改为1或0：

- `target_valid_columns` 会变化，许可和有效KV范围会变化。
- `target_verify_batch_impl` 仍按 `columns=width*batch` 分配及执行完整层、norm、全Target head与argmax；dense linear没有传入有效列参数。
- MTP alignment按固定物理窗口执行，随后无条件做第一次proposal head。
- 草稿循环条件是host `step+1<k`，而不是GPU `next_extent`；剩余AR层与proposal head仍被launch。
- `ar_valid_columns` 可阻止无效注意力/KV写入，但不自动消除上述dense投影和head。

因此，**仅写一个自适应extent策略，不能声称减少Target轮成本或草稿计算。** 若要确实少算，必须改变物理K/选择对应Graph，或显式把proposal子图做可跳过执行；还要同时维护MTP对齐、下一轮proposal与缓存状态。其范围大于“新增一个阈值”。

证据：[fixed width、Graph与extent](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/program_impl.h:3312)、[固定K的proposal和AR循环](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/mtp_impl.h:158)、[全物理列Target verify](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/text_context_impl.h:759)、[next extent与AR valid的原语义](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/ops/kernel/mtp_round.cuh:10)。

## 3. 每轮同步和拷贝确实存在，但还没有耗时证据证明它们主导decode

一轮MTP首先复制小型host ingress到GPU，Graph内完成Target verify、接受、MTP alignment和下轮proposal，再复制小型egress到host；`decode_mtp_batch` 随后同步。host决定正式许可后，GDN Fold再执行并同步，然后更新正式frontier、ledger与下一轮draft IDs。这些是实际代码边界，不是“每个token把完整logits搬回CPU采样”。

不能据此直接删除同步：host需要许可候选token、检查终止/取消，并在Fold后安全重用工作区和状态。是否能合并/异步化要看真实时间线及所有者生命周期。已有整体round约几十毫秒的描述并未给出这些同步所占份额。缺这项测量时，将它排成最高收益优化没有依据。

可确认的一项小冗余是：Target verify总会运行 `ops::argmax`，即使后续Target走temperature>0的随机接受路线。不过它扫描的是verify logits，不是重新读取所有模型权重；在未计时前只能认定存在可研究的冗余，不能承诺显著整链收益。

## 4. 更值得准备的新候选：sampled proposal＋稀疏q接受

这是与当前delta-q不同的算法候选，**当前分支并没有实现，也不属于原有greedy合同自动授权范围。** 在完整 `src/include/tests` 中精确搜索 `speculative_accept_sparse_drafts`、`sample_logits_sparse_draft`、`sparse_draft`、`draft_prob`、`draft_q` 没有对应采样实现；命中的sparse只涉及无关MoE。不能认为当前DFlash已有可直接开关的随机q verifier。

现有确定草稿的单位置接受率为Target的 `p(d)`。若实际从草稿分布q采样，正确接受率为 `Σ min(p,q)=1-TV(p,q)`；q接近p时可能提高每轮正式产出。这个数学潜力与“把greedy再实现一次”不同，也与重新裁词表不同。目标是减少生成相同token数量所需的完整Target轮数，并不声称节省单轮原有head、AR或Target数学。

[既有Baseline评估](ninfer-hyperqwen-v3-md-20261019/research/04-completed-baseline-assessment.md:44)记录97的三个位置条件接受率约69.42%/71.44%/74.08%；[K0](ninfer-v4-k0-20261023.md)记录Pi总体每轮接受草稿约1.566，平均总产出约2.566 token/轮。这说明随机Target下的接受率有优化空间，不是q候选必然有效的证明。即便K3达到理想4 token/轮并且单轮成本完全不变，2.566→4的条件耗时降低上限也只有35.85%；任何采样/概率保存新增成本都会压低该上限。对H1里接近4 token/轮的简单复制样本，余量本来就小，不能只用这种夹具验证新候选。

### 4.1 最小可隔离实现边界

保持C1/K3/W4、现有Q4 draft head资产、完整Target Q6 head与所有Target参数。新路线只在proposal分布和正确接受/残差上变化；不是W8、DFlash2、全局检索、词表重训或kernel重写。候选范围仍是中等修改，不能描述成替换一行argmax。

| 位置 | 必要改变 | 应复用的原路径 |
|---|---|---|
| `text_context_impl.h::proposal_argmax/mtp_propose_batch` | 在已得到的proposal logits上构造实际小支持集q、独立随机采样，导出支持ID和归一化概率；如首选top12，必须先固定其数学定义 | 原Q4 linear、token-ID remap与MTP autoregressive前缀 |
| `round_state.h`／`program.h`／相应layout及copy glue | 将每个位置的实际条件q从本轮proposal完整带到下一轮verify；token IDs和q必须同属同一个包、同一请求与prefix | 原lane、epoch、frontier、cancel、permit所有权 |
| `speculative_round` wrapper／launcher／kernel | 新稀疏q分支：`min(1,p(d)/q(d))`；拒绝后从完整 `(p-q)+` 归一化分布采样 | 原Target processor、概率构造、许可输出与GDN Fold |
| `sampling.h`与proposal采样辅助实现 | 独立proposal RNG purpose；不能与accept/correction/bonus使用相关随机数 | 原Target seed、各Target RNG purpose及逻辑位置定义 |
| native/状态/数值验证 | 证明新q包的生命周期与Target分布、状态；不要要求随机路线与greedy输出逐token相同 | 既有FP64/FP32状态参考、原numerical/Graph与已通过算子证据 |

Target的full-vocab实际走partial/group路线，不能只修改small-vocab单block kernel。否则CPU/小词表测试会通过，而真实27B仍走旧公式或出错。

### 4.2 真正影响范围与资格的风险

1. **只保存被选token的q(d)不够。** 拒绝时需要对p支持集每个token减去对应q；必须保存完整非零q支持和概率，并经proposal ID remap映射到全词表ID。
2. **每位置q必须来自该位置实际前缀。** 不能先生成greedy包，再把最后一列top12概率挂到所有位置上。每次AR输入应是实际sampled token。
3. **Target不变。** 不裁Target词表、不改变temperature/top-k/top-p/processor顺序；q支持之外q=0，Target p支持内未被q覆盖的概率仍必须可被纠正采样选中。
4. **新旧proposal缓存不可混用。** 当前 `SequenceState` 与frontier序列化只保存draft IDs，没有q。直接启用新算法会在恢复后丢掉接受所需分布。首个隔离pilot可明确cache off、fresh请求，从而不扩张缓存格式；生产发布前仍需确定恢复时携带q或清空并重建proposal的合同，不能借pilot的cache off冒充解决。
5. **概率和随机数是正确性边界。** q归一化、BF16 logits tie、FP32舍入、极小残差、q(d)=0非法包和RNG独立性都需要定向合同。不能沿用delta-only接受测试就宣布分布通过。
6. **收益取决于q接近p。** 现有131072 shortlisted head对不同语言/代码类型的覆盖和校准并未测出；top12可能漏掉Target高概率token。q偏离p时，可比greedy更慢。别的模型/量化/K7上的作者数字不能转成29上本模型的预期测量值。

[只有draft IDs的正式状态](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/program.h:281)、[frontier编解码](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/src/targets/qwen3_8/impl/runtime/continuation_image.h:476)、[现有delta-only公开Op合同](../output/ninfer-v4-performance-reflection-20261024/source-audit/source/include/ninfer/ops/speculative_round.h:54)。

## 5. 根据本次源码证据的排序

| 候选 | 作用于什么主要量 | 范围判断 | 本次建议 |
|---|---|---|---|
| 固定W4 sampled proposal＋稀疏q正确接受 | 提高每轮正式提交量，减少完整Target轮数 | 中等，涉及算法/状态/分布合同；小于新W8执行链或DFlash2模型适配 | 优先做新合同、donor差异和离线数学准备；通过最窄算法证明后才考虑实机 |
| 物理K/Graph的自适应选择 | 缩少算时的真实AR/head与Target列 | 中等到较大；当前对象draft_window、frame strides、Graph及缓存状态绑定固定K | 有理论价值，但不要用仅改逻辑extent伪造已省计算 |
| 再裁draft词表/专调Q4 head | 减少单轮proposal投影字节/成本 | 支持集与接受率变动；仍缺head在整轮中的份额 | 在真实head耗时与语言覆盖证据出现后选择 |
| 去掉随机Target下多余argmax或再调norm/Fold | 减少局部扫描/launch/小算子 | 很小，但收益上限易受整体份额限制 | 不再因改动小就排为主线；需要归因支持 |
| 工作区回收、双流调度 | 容量或重叠 | 依赖真实生命周期与竞争，未证明当前主要瓶颈 | 保留研究，不在缺时序证据下承诺decode大幅提速 |

本次没有实际GPU时间分解，因此不能把某一个kernel宣称为已测得的最大热点。能确认的是：已有greedy/Graph/优化head不是新机会，固定extent缩小不是实际少算；若保持现有W4与模型，改变proposal分布以增加每轮正式产出是更直接的候选假设。它尚未取得本机分布、状态、性能或发布资格。原服务继续保持停止，所有历史失败、G1差异与C1缺口保持原状。
