> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 显存预算、性能模型与实验矩阵

## 精确单位与状态账本

NInfer27B的16个FA层、4KVheads、head_dim256给出BF16 KV每token64KiB；262144token为16GiB。新rk4v4每KVhead每token272B时，16×4×272×262144=4.25GiB，而不是只算4bit元素得出的4GiB。这里尚未包括MTP/GDN、metadata、workspace、graphs与模型权重；最终以P7采集的真实allocator峰值为准。[N01及原包P4 codec设计]

| 状态 | 算例几何 | 262144token成本 | 是否可用旧Target L2代替 |
|---|---|---:|---|
| Draft全层BF16 KV | 5layers×8heads×128×K/V×2B | 5GiB | 否 |
| Projected G archive | hidden5120×2B | 2.5GiB，host | 否，需要主动捕获 |
| 原始5层features | 5×5120×2B | 12.5GiB，host | 否 |
| 固定2176-row ring | 2176×20KiB | 42.5MiB/驻留lane | 否 |
| 页代表K | 1024pages×2reps×5layers×8heads×128×2B | 20MiB，GPU | 否 |

**五层等Draft参数是预算算例，最终必须由冻结资产manifest替代。** 0.79GB是tqLLM低比特文件的公布下载体积，不是新NInfer drafter的device bytes；selector表、embedding/head副本、repack与temporary buffers不能漏记。[T01/T03]

候选峰值=`P6实测峰值 - 已证明删除的互斥slab + draftweights + rings + stagingA/B + index + scratch + graphs + extrahead + checkpoint`。同一份矩阵共享时只计一次，声称可回收MTP时须证明此profile已不加载/使用它；“运行时不选MTP”不等于分配自动释放。预算工具要求reclaim证据，否则拒绝。

首轮采用GPU空余下限512MiB、host系统/其他任务预留下限8GiB作为新增资格门槛；若P6实际运维预留更大则取更大者。4lane的rings/featureframes/graphs须按实际同时存活数量计算，archive按所有session总token。Pinned host工作集必须单列，禁止不受限pin全历史。独立图缓存上限由测量确定，不照抄tqLLM256graphs默认。[T08]

## 测量口径

`effective_tps = sum(committed_tokens) / sum(nonoverlapping_round_wall_seconds)`。committed含修正/bonus；accepted_drafts只用于接受率。端到端wall time另计排队、prefill、draft历史建立、host传输、HTTP与工具交互。CUDA事件按依赖关键路径对齐，异步retrieval不能与verify重叠后又相加计时。Python `tqllm_tools.summarize_rounds`只处理串行chain执行轮，不能当成多请求服务器吞吐。

Amdahl式判断：若Target full attention占round时间比例a、其余不变，单独把draft提速无限倍也消不掉Target成本。先按profile选瓶颈，避免再提出“加FlashAttention”“增加K”这样的无定位方案。[N07]

## 受控矩阵

| 维度 | 必须覆盖 |
|---|---|
| 实际prompt tokens | 2048、32768、65536、131072、196608、253952（248Ki tokens）；tokenizer精确计数 |
| configured context/pool | 沿用P6，最大262144；prompt+有效输出+事务reservation不得超界 |
| output预算 | 128、512、2048；高上下文至少保留完整输出空间 |
| speculative profile | P6固定MTP3；None；MTP3/4/5；Lookup；P10 ringDFlash2；P11 global retrieval |
| runtime | eager/graph；1lane与P6并发配置；newcold/L1/L2/L3/missingDraftArchive/rewrittenhistory |
| workload | Java代码生成、工具结果复制、跨文件远端引用、中文约束、非重复文字、对抗低接受率 |
| defaults isolation | Target artifact、tokenizer/template、rk4v4、sampling、stop、功率/时钟/thermal、请求顺序/seed冻结 |

每个采用结论每配置至少30个配对请求（长序列可跨不同固定case），A/B/A顺序，报告中位数/分位数、配对bootstrap95%区间和离群原因；不以最大tok/s替代结果。真实Java评测至少30个冻结任务，编译、测试、工具调用和walltime可重复，测试集与调参集分离。精确模式任何token差异先阻断资格，不能靠总体成功率抵消。

## 发布门槛

原包`profiles/benchmark-rules.json`不变：decode中位数退化3%/p10退化5%、TTFT中位数5%/p90 10%等仍适用。本扩展采用更明确的增益要求：

- P8/P9至少一个目标工作负载有效walltime提高5%且配对区间不跨0；无收益的kernel变体不得成为默认，可以记录NO_CHANGE退出该实验任务。
- P10/P11高复杂度功能要默认采用，128K decode中位数至少提高15%，相对于**同一阶段前已合格NInfer基线**；相对于最初P6也另报。248K满足原回退门槛，且总Agent walltime改善，才有默认采用资格。
- 新功能GPU/host预算和实际压力峰值均满足预留；不能通过缩context、自动Target量化或host TargetKV换取表面fit。
- 所有已启用功能每次最终集成commit重新通过精确性/状态/streaming门禁；新精确路径关掉时原P6行为不退化。

无资格资产/机器时保持BLOCKED；预算工具输出BUDGET_GO仅代表数字相加成立，绝不是GPU测试通过。
