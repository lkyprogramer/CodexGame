# NInfer性能复盘与下一项准备：先争取完整decode收益

**计划的优先级和我的执行都有问题。到目前为止，已经得到若干局部加速和功能/可靠性改善，但还没有交付可归因、可复现的整体Chat推理提速。不能用“还有很多方向没做”“通过很多测试”解释这个落差。**

这次结合原始结果、29源码和公开一手资料重新评估。下一项**优先准备固定C1/W4/K3的 sampled MTP＋真实稀疏q接受修正**：它直接尝试提高每轮正式产出，有同型号GPU的外部实现线索，且不需要新模型、扩宽或改变Target参数。它是值得验证的中等范围算法候选，**不是已证实收益最大/改动最小，也不是几行开关**。最少新增代码仍是修完已有W6驱动；潜在更大规模的并行draft是DFlash2，但适配范围更大。三者不能混成一个“小改大收益”的承诺。

本轮完成只读搜索、源码差异、候选合同和离线概率参考准备；没有引擎补丁、BO构建、GPU或模型请求。原GPU服务实时读回为STOPPED/PID0、GPU空闲。原始Baseline、18处G1差异、C1附件缺口与全部失败保持原样。

## 1. 为什么做了几天仍没有可交付的整体提速

### 计划问题：一直没有把“优化哪段”换算成“整轮最多能省多少”

K0已经明确GPU算子占比、关键路径和逐轮时间线为null，之后却连续选择norm、correction、卷积等局部候选。改动可隔离不代表它值得优先。K2-T05是最清楚的例子：卷积＋提取段减少36.48%，完整Prefill中位只减少0.314%。如果某段只占整体1%，该段减少36%也只贡献约0.36%；这类上界应在大规模接入前审查。[K0原记录](ninfer-v4-k0-20261023.md) · [完整Prefill结果](ninfer-v4-k2-t05-chat-remaining-20261024.md)。

C0的SHA约2.15倍速度是真实局部成果，但后台publication未必阻塞下一请求，不能把省下的CPU时间直接加到TTFT。H1的复制正例又已接近W4每轮4个token上限，单靠接受率的条件节时空间约3.01%和1.39%，低于原5%目标；它仍照常生成MTP下轮草稿，Lookup命中并不省当前轮计算。这是选题和实验设计的问题，不是用户限制预算造成的。[完整复盘](ninfer-v4-performance-retrospective-20261024.md)。

P1—P4包括真正的性能代码，也包括正确性、接口和观测工作；没有做旧版到候选的同口径性能AB，所以既不能把它们算成已实现的整体加速，也不能断言它们全部无效。早期把完整上游功能集成当性能主线前置，范围确实过宽。

### 执行问题：我增加了太多验证代码，却漏掉真实调用边界

请求ID关联、PID登记、消费模型TU的宏、Graph函数地址、具名tool_choice、重复保护夹具、H3零工作区和异常audit，都是已出现的具体工具/驱动缺陷。CPU合同数和review通过没有覆盖真正失败的位置。保全失败是必要善后，不是性能成果；这些错误应该由执行方承担，不能归咎于“不可重跑”或“预算太严格”。

反复为小候选增加controller、账本、probe、快照与长文档也提高了出错面。以后沿用已有owner/响应ID/deadline/终态实现，只增加必要的候选参数和证据字段；不再把一项局部实验升级成一套新验证平台。没有统一实际工时账本，因此本报告不编造“多少小时/多少百分比浪费”的统计。

还需更正状态：**W6已实测6个数值/Graph场景，第7个驱动初始化失败；native/Chat没有执行。** 不是完全没跑GPU，也不是W6已经证明无效。[最新实机结果](ninfer-v4-h3-w6-hardware-20261024.md)。

## 2. 搜索和源码核对改变了什么判断

- 当前已有greedy proposal＋Target sampling、Q4的131072行optimized proposal head、GPU sampler、CUDA Graph和统一GDN Fold。这些不能重新命名成新优化。完整Target head为Q6、248320行。[29源码核对](ninfer-v4-performance-source-audit-20261024.md)。
- 固定W4只缩logical extent，不会少执行主要dense verify、固定K的MTP AR和head。真正的动态宽度/skip需要物理Graph或子图执行改变，不能声称加一个阈值就提速。
- 找到固定版本`jram4/ninfer-4090@70ebb129…`的随机MTP草稿实现。它记录真实top12 q并做完整拒绝修正。作者的32条temperature1工具请求聚合decode速率约提高11.1%，但模型是abliterated变体、K7/K8V4、188416 context，请求体私有，输出长度和工具数不同。这是选题依据，不是29的预期收益或质量证明。[固定聚合数据](https://github.com/jram4/ninfer-4090/blob/70ebb1290dc7abe246c20696a24d21f77faee8d4/results/rtx4090-20260924-sampled/temperature1-replay-summary.json)。
- **DFlash2匹配Qwen3.8-27B检查点现已存在**，不能继续以“没有资产”排除。但新5层draft、特征抽取、selector、显存和状态适配不属于小改。所查BF16参数的紧密容量约3.85GB，不含workspace；不能为装入24GB改动当前context或codec。[官方支持列表](https://github.com/z-lab/dflash#supported-models) · [固定配置和差异核查](ninfer-v4-performance-primary-research-20261024.md)。

## 3. 下一方向如何选择

| 方向 | 新增范围 | 为什么可能有收益 | 本次取舍 |
|---|---|---|---|
| 现有W6补齐 | 最小边际代码量，主要修驱动；沿用已有执行链 | 更高每轮产出可能覆盖额外两列成本 | 保留未完成结果，不自动追加；若唯一目标是最少新增代码，它最便宜，但没有收益证据 |
| **固定W4 sampled MTP＋精确q** | 中等；proposal选择、general-q接受、跨轮包、RNG/Graph | 同样Target轮成本下争取多提交token，直接作用于完整decode | **唯一优先准备的新算法候选**；先做窄可行性，不承诺最大收益 |
| H2进一步裁draft head | 模块集中，但需要新shortlist/资产映射/覆盖率 | 降低每轮多次head成本 | 先有head占比才做；当前已是131072，不能按词表比例推整机收益 |
| DFlash2 | 大；额外权重、特征、状态和后端适配 | 并行draft可能减少串行AR | 长期有较大潜力，当前不符合小范围要求，不移植完整运行时 |
| norm/Fold/conv/冗余argmax、workspace、utility | 前几项小、后几项中大 | 依赖实测份额或混合流量约束 | 没有关键路径证据，不再轮流排为“最值得做” |

这不是把所有希望换到另一份README。真实收益仍需本机测量；如果要求“已经确定大幅收益、改动又小”，现有证据做不到。应明确这一点，而不是再给一串百分比。

## 4. 已准备的候选合同

候选名：`C1_W4_K3_SAMPLED_MTP_EXACT_SPARSE_Q`，状态`RESEARCH_AND_CONTRACT_PREPARED_NOT_IMPLEMENTED`。沿用raw基点`a5ba33de…`，参考已核对的H3源树；未来隔离候选不叠加未采用的Lookup、correction或T1024分派。

保持现有C1/K3/W4、Q4 proposal head、完整Q6 Target、模型/codec/context262144及Target temperature1/top_p.95/top_k20。Pi medium/32768不改，默认仍走原greedy路线，新路线仅显式候选开关。初次实验fresh请求、cache off；这只隔离缓存变量，**不代表生产恢复已解决**。

数学合同：先从真实条件q抽出草稿d，接受概率为`min(1,p(d)/q(d))`；拒绝后从完整Target有效支持集上的`normalize(max(p-q,0))`抽样；全接受bonus按Target合同。q可以是稀疏top12，但不能只保存被选token的q(d)，不能把Target支持裁成12项，也不能让随机草稿继续走原delta-q公式。理论依据为[原始Speculative Decoding论文](https://proceedings.mlr.press/v202/leviathan23a.html)。

准备已核对的实际边界：

1. `proposal_argmax`目前是独立linear→argmax→remap，不是必须拆掉的融合head；可以复用其真实logits。但top12选择/归一化会增加成本，不能视为免费。
2. 本机没有general-q API。small-vocab和真实248320词的multiblock接受路径都需正确实现，不能只让小词表测试通过。
3. 每位置完整q的global IDs与概率必须和实际sampled prefix、请求/epoch/frontier绑定，经current/next双缓冲传给下一轮。proposal RNG需独立purpose，不能与accept/residual/bonus共享相关随机数。
4. 当前缓存只保存draft IDs，不保存q。首筛不改变缓存格式；未来发布必须解决恢复时q携带或proposal重建，未解决不能启用缓存候选。
5. 相同输入状态/相同proposal包下应继续检查state/conv/KV与Graph的一致性；**不能要求sampled与greedy在相同seed下输出逐token一致**。输出分布不变与浮点/状态逐bit正确是不同合同。

固定donor功能提交`cbf7b7e…`涉及23文件、1996新增/67删除，含约900行测试；本机缺少donor已具备的general-q verifier，因此不能直接cherry-pick或承诺几行完成。详细责任边界见[机器准备包](../output/ninfer-v4-performance-reset-20261024/preparation.json)及[源码审计](ninfer-v4-performance-source-audit-20261024.md)。

本轮新增一个纯离线有理数参考，8个小词表例子验证delta退化、p=q、部分/完全不交、Target过滤、映射和不完整q拒绝。它不调用模型，也不执行旧测试；**仅检查数学参考，不证明本机CUDA sampler、RNG、条件前缀或真实速度。** [脚本](../output/ninfer-v4-performance-reset-20261024/check_sparse_q_math.py) · [结果](../output/ninfer-v4-performance-reset-20261024/sparse-q-math.json)。

## 5. 预期收益应该如何表达

历史Baseline的39条Pi HTTP200中，decode占请求elapsed之和约70.27%，平均接受草稿1.566；粗略每轮总产出约2.566（忽略尾轮等细节）。这是历史合计，不是当前流量分布或新路线profile。

令G为每轮正式提交token、R为包含proposal/verify/commit/host间隙的完整轮耗时，吞吐比为`(G新/G旧)/(R新/R旧)`。以下只是假设情景，不是预测：

| 假设 | decode吞吐变化 | 同样输出工作量的decode耗时变化 |
|---|---:|---:|
| G不变，R增加3% | −2.9% | 增加3.0% |
| G增加10%，R增加3% | +6.8% | 减少6.4% |
| G增加20%，R增加3% | +16.5% | 减少14.2% |
| G增加30%，R增加5% | +23.8% | 减少19.2% |

在“其余耗时不变、相同输出工作量”的额外假设下，第二、三行换算到历史Pi整请求约为4.5%、10.0%节时。不能把输出变短当算法提速，也不能把token/s提高11%写成整请求节时11%。实际可达区间目前仍为null。[公式与输入](../output/ninfer-v4-performance-reset-20261024/conditional-upside.json)。

## 6. 后续验证和耗时收敛到一项实验

- **准备完成后，首次实现最多投入4–6小时做可行性检查点。** 只实现/审查实际q producer→packet→verifier的窄链路和CPU合同。如果需要改Target支持、模型资产、缓存ABI或全面重做sampler才能完成首筛，就停止并重估，不顺带扩W8/DFlash2。
- **可构建候选粗估1–2工程日**，包括BO、必要CPU/算法检查和独立评审，不是已完成工作或保证工期。GPU前应覆盖真实zero-workspace、owner/ID、异常audit出口，而不是累积合同数量；默认构建和实际消费TU证据复用方法，未改算子矩阵不重跑。
- **只提出一个未来最小窗口：**≤4 native请求/≤12decode；4种新非重复任务各W4-greedy与W4-sampled一对，共8 Chat＋2warmup/12wire，总≤14模型提交；硬20分钟，第17分钟清理。它不复用已消费的H3预算。完整Op/capture/replay/kernel/copy上限要在具体候选构建后冻结，本准备包不具备GPU执行授权。
- **同窗回答净收益。** 用native诊断区分Target/MTP/head/selector/commit成本；正式Chat性能不开profiler，记录完整decode/token、服务wall、质量与实际q路线。Nsight节点追踪会引入开销，不能将其时间当正式吞吐。29现有nsys为2023.3.3，已核对help但未验证与当前CUDA13的采集兼容，不把工具升级另设前置工程。[NVIDIA指南](https://docs.nvidia.com/nsight-systems/UserGuide/#preparing-your-application-for-profiling)。
- **只作筛选。** 新Java、中文推理、非重复工具、低接受控制任务事先固定；不再以高接受复制任务代表真实Pi。单对样本只能给方向，不能给p95或质量等价保证；接受率增加而完整decode无净收益就停止该配置，不自动扩宽/调参数/加样本。结果整理预计0.5–1小时。

完整候选资格、缓存恢复与生产发布仍独立；本轮不部署，原服务持续停止。当前H3失败不抹去，也不让其追加补测自动成为新候选的前置。

[计划与执行复盘](ninfer-v4-performance-retrospective-20261024.md) · [一手搜索报告](ninfer-v4-performance-primary-research-20261024.md) · [29实际源码](ninfer-v4-performance-source-audit-20261024.md) · [准备回执](../output/ninfer-v4-performance-reset-20261024/preparation.json)。
