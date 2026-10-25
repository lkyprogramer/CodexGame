# H1-T01最小实机：状态一致通过，未获得Lookup采用信号

**已完整执行冻结r3，Lookup实际命中，2个native状态场景逐bit通过；本轮没有完整decode净收益，保留默认MTP。** 新Chat的三对样本按生成token归一化，候选耗时分别增加6.98%、4.28%、8.11%。两个重复正例同时触发既有`repetition_cycle`保护，形成夹具有效性缺口；不能把这4条当作模型答错或Lookup导致质量回退的证明，也不能改为PASS。

## 执行与预算

通过`jssh 29`（`ssh -J jump 29`）执行。先逐文件核对冻结SHA、PRISTINE账本、模型stat、原镜像/argv/cache身份、GPU空闲和lease，再唯一启动controller191347与guardian191359。冻结SHA为`716ccfc4e8308f7db34497d8edc6d6705aa1a843370b4efef1f073df42d22eb0`，源树`9e7c0a1f19721d0ba63db362da6d10b5cda7c8e0`，根`/home/hhtele/ninfer-v4-h1-t01-20261024/prepared-window-r3`。r1/r2未恢复，未修改冻结脚本或分派，没有编译新优化代码。

| 计账 | 实际 / 上限 |
|---|---:|
| native场景 | 2 / 2 |
| native请求 | 4 / 4 |
| native Program decode/verify调用 | 6 / 16 |
| 新Chat | 6 / 6 |
| 显式HTTP warmup | 2 / 2 |
| wire（含2次health） | 10 / 10 |
| 模型工作提交（含native） | 12 / 12 |
| capture | 36 / 256 |
| replay（含startup/warmup） | 339 / 73728 |
| 算法kernel | 303561 / 35651584 |
| 从窗口开始到清理核查完成 | 250.301秒 / 硬1200秒，第1020秒清理线未触及 |

完整14项资源及分方向copy/memset上限均满足，四个CUDA审计status为COMPLETE，实际计数合计与账本一致。没有额外探测、重试、旧Baseline或已通过任务重跑。controller退出0，guardian正常关闭准入并精确清理本轮4个候选；最后三个监督进程均ABSENT，GPU idle、lease free。原服务保持STOPPED/PID0，原镜像/参数/cache目录身份不变。账本COMPLETE、所有reservation已结束，无未结束请求或未知终态。

[最终readback](../output/ninfer-v4-h1-t01-hardware-20261024/hardware-r3-final-readback.json) · [完整账本](../output/ninfer-v4-h1-t01-hardware-20261024/remote/budget-ledger.json) · [原冻结与CPU交付](ninfer-v4-h1-t01-20261024.md)。

## Lookup与状态一致性

候选native3轮均命中。场景1整包与MTP相同：完整W4 verify bytes、canonical state/conv、首轮下一轮MTP一致，第二轮终态截断的许可state一致。场景2选择不同整包且实际拒绝：相同正式提交前缀的state和verify首列一致；本场景没有触发部分终态截断，不能伪记为已覆盖，该边界由场景1覆盖。

每个case/variant导出72个真实state段，共174080593 bytes；两个case对照各72段全相同。真实verify为BF16 `[248320,4,1,1]`、1986560 bytes。场景1比较全部列，场景2仅比较相同因果前缀对应首列496640 bytes；后续列因proposal不同，整块hash不同属于预期，未要求伪造全列等价。

[原生比较原件](../output/ninfer-v4-h1-t01-hardware-20261024/remote/runtime/native-comparison.json)绑定实际raw文件与state元数据。结论只覆盖这2个新场景；不同packet非终态下一轮、完整取消/restore矩阵、随机分布、长时稳定性与发布资格均未额外验证。原有18处G1差异、C1附件缺口及历史失败继续保留。

6个正式Chat中，候选128轮均eligible、47轮选中Lookup（36.72%），选中141个draft中122个被Target接受（86.52%），命中轮正式committed169个token。这些数直接来自实际事件字段，没有用`accepted+1`代替正式提交数；warmup单列，不加进47/128。

## 完整decode净收益

主口径沿用冻结合同：server累计完整decode秒数 / Engine报告的completion token；包含本轮的建索引/查询/append/reset、Target verify、必需MTP对齐和下一轮、许可提交。另重算trace完整round wall / 实际committed，两种口径方向相同。

| 样本 | 候选Lookup命中 | raw → 候选（ms/报告token） | 耗时增幅 | 每轮正式提交raw → 候选 | 输出合同 |
|---|---:|---:|---:|---:|---|
| 复制 | 23/69 | 5.9701 → 6.3870 | +6.98% | 3.880 → 3.623 | 两组均被repetition guard截断 |
| 工具 | 17/37 | 5.8433 → 6.0937 | +4.28% | 3.944 → 3.784 | 两组均被repetition guard截断 |
| 低重复控制 | 7/22 | 7.1555 → 7.7358 | +8.11% | 3.188 → 2.955 | 两组PASS，但控制组也命中Lookup |

使用实际decode committed为分母的整轮wall增幅分别为7.20%、4.29%、7.66%。没有一项达到冻结正例≥5%改善信号。低重复控制也命中7/22轮，不能据此声称no-hit开销≤1%；warmup不替代该控制。

当前单轮decode约23.2ms，raw与候选接近；本次候选每轮正式产出反而更少。两个重复正例raw已达到3.880/3.944 token每轮。**条件上界推导**：若同token轨迹、同单轮成本且K3每轮最多提交4个，单靠接受改善可节约的时间最多约3.01%/1.39%，低于本次5%信号门槛。这说明本次正例对“通过proposal质量节省整轮”的空间很小；不是对所有Lookup使用场景的否定，也不是实测收益预测。

复制样本总decode 3.0865→1.6031秒同时对应O 517→251；不同reasoning轨迹使输出长度差异很大，不能把绝对总时长下降算成提速。两组各自使用原生产sampling自动seed，未强制相同随机轨迹；每个输入仅一对、有序cohort，且正例被保护截断，三项百分比只能作为本轮观察，不能独立归因为Lookup的普遍性能回退。

50条5秒周期GPU遥测已保留，含idle/装载：SM210–2775MHz、43–61°C、功率11.29–387.96W。部分短请求没有落入期间的采样，未证明逐请求频率严格相等；未跑额外profiling或追加样本。`p95=null`，不声称稳定收益或优化PASS。

## 四个失败的真实原因

原始输出判定保留`FAIL_MODEL_BEHAVIOR`；**派生分类**为`EXISTING_REPETITION_GUARD_TRUNCATED_POSITIVE_FIXTURE`，不改原raw、判定或分母。

四个Engine durable终态均为`repetition_cycle`；Chat协议按既有合同映射为`length`，当时实际O为517、143、251、141，均小于请求2048。复制两组均仅发出289 bytes的部分文本；工具两组均有`tool_calls_incomplete=1`，参数在闭合前中断。该原因不是2048 token耗尽的证据。

冻结基点的RepetitionGuard默认enabled，window512、ngram24、cycles3、min_tokens64；只观察正式提交的token，周期确认后截断。新fixture要求复制24个完全相同行或输出8个相同对象，会与保护合同冲突。协议输出不区分该guard和其他length原因，所以必须读取Engine终态才能正确解释失败。

[源树见证](../output/ninfer-v4-h1-t01-hardware-20261024/guard-source/receipt.json) · [Guard](../output/ninfer-v4-h1-t01-hardware-20261024/guard-source/src/runtime/generation/repetition_guard.h:104) · [正式提交与终态](../output/ninfer-v4-h1-t01-hardware-20261024/guard-source/src/runtime/engine/concurrent_executor.h:4016) · [wire映射](../output/ninfer-v4-h1-t01-hardware-20261024/guard-source/src/serve/translate.cpp:262)。

因此新Chat为2条完整PASS、4条保护截断未满足合同；2次warmup另为PASS。数据不足以把这4条当作原始模型质量失败或Lookup破坏质量的证据。未关重复保护、未放宽断言、未修改2048/32768或采样，也没有为了PASS重跑。

## 结论与证据保全

本轮完成：**真实命中可核对，限定场景状态一致；完整decode没有采用信号，质量正例与no-hit控制仍有缺口。保持原MTP、结束本轮profile，追加预算0。** 完整候选与发布资格继续独立，`optimization_qualification=false`；不推导未来sampling资格已通过。若以后继续，应先修复正例夹具与既有保护的冲突，当前不授权或自动追加任何测量。

完整state/runtime归档持久保留在`/home/hhtele/ninfer-v4-h1-t01-20261024/H1-T01-hardware-r3-runtime-complete.tar.gz`，635290233 bytes，SHA `3a824214d966f9e034c3f54d1b14b6eaf3f463a84dec6098c7f0ea5af034c952`。本机已完整SHA校验并镜像5871680 bytes的[wire/logits/元数据归档回执](../output/ninfer-v4-h1-t01-hardware-20261024/hardware-r3-archive-receipt.json)，含所有请求body、SSE raw/headers/arrival、durable Engine终态、真实verify bytes、state SHA、CUDA审计和监控/进程回执。大state原件不声称已复制本机，均在远端原目录和完整不可变归档中。

[可复算分析](../output/ninfer-v4-h1-t01-hardware-20261024/analysis.json) · [分析脚本（离线、0请求）](../output/ninfer-v4-h1-t01-hardware-20261024/analyze.py)。旧Baseline缺失附件/损坏raw、18处G1差异及C1缺口没有补造、覆盖或默认为已恢复。
