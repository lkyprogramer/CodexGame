# K1-T01 最小实机：数值通过，Graph见证失败，净收益未测量

本轮通过`jssh 29`执行唯一一次冻结窗口。**8个数值场景通过：48层FP32 state、conv及BF16 readout逐bit一致；Graph首图见证失败，未执行replay或计时，Record＋Fold净收益为null。** 没有取得Graph、候选采用或生产发布资格。

原始失败、账本和清理证据已保存。没有追加GPU运行、重跑旧任务或修改候选代码。原服务保持停止，默认分派、采样及Pi medium/32768预算均未改。

## 身份与实际预算

隔离源码树为`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`，分支`codex/k1-correction-records-20261023`。冻结输入根为29的`/home/hhtele/ninfer-v4-k1-20261023/prepared-window-r1`。

冻结回执SHA为`4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105`，probe SHA为`5978092c268e1cf19481dfada20df66b0d45e143fffe8e0de83e41edf0dde726`。运行前7个冻结输入、15个源码SHA、空账本、原服务身份和GPU空闲检查通过；运行后7个冻结输入仍匹配，原始CPU回执及初始账本未改。[预检](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-hardware-20261023/preflight.json)。

| 项目 | 本轮结果 | 授权上限 |
|---|---:|---:|
| 数值场景 | 8完成、8通过 | 8 |
| direct Op | 784完成 | 784 |
| capture | 首个raw commit1尝试后见证失败；1次预留未完成 | 6 |
| 通过完整见证的Graph | 0 | 6 |
| replay，含warmup | 0 | 276 |
| 实际算法kernel执行 | 784 | 14308 |
| 模型 / HTTP | 0 / 0 | 0 / 0 |

八组数值预留均为`COMPLETED`。第九组`capture-1-raw`保留`RESERVED_UNKNOWN`，ledger原状态为`RUNNING`；这是失败现场，不能改成`COMPLETE`，也不表示候选还活着。capture只建立图，没有执行算法kernel；没有Graph replay或额外warmup。窗口已经终止，不重启、不清空或复用旧账本，未用额度不自动转为下一次执行授权。[账本](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-20261023/prepared-window-r1/budget-ledger.json)。

传输也在冻结上限内：H2D130次/977,281,104字节，D2D18次/2,771,002,368字节，D2H224次/7,744,856,192字节。初始化、guard、reset及检查导出均计账；这些不是性能样本。

## 数值结论

普通输入覆盖commit0/1/2/3/4、valid4/4/3/4/4；stress输入覆盖commit0/2/4、valid4/2/4。8条outcome均为`bitwise=PASS`、`fp64=PASS`、`guards_and_suffix=PASS`，与八条完成的预算记录一致。[原始outcomes](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-20261023/prepared-window-r1/native-outcomes.jsonl)。

48层使用不同初state/conv种子，检查raw/correction正式FP32 state、conv历史及BF16 recurrent readout逐bit；Record不修改权威state，检查无效输出零化、未写suffix和guard，再污染拒绝后缀验证Fold前缀。独立FP64仅layer0，复用原`gdn_ref.h`和原阈值，不能扩大为48层独立FP64证明。

这份证据只覆盖选定C1/W4/L48 direct Op组合。它没有验证真实Engine/Program的许可、epoch、取消、Target sampling路径、完整Verify或模型整轮。

## Graph失败与证据缺口

native原始错误只有：`K1 probe: unexpected Fold function/geometry`。[stderr](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-20261023/prepared-window-r1/runtime/native.stderr)。native stdout为空；summary为`FAILED_WITH_PRESERVED_RESERVATIONS`，候选退出1，非OOM。[summary](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-20261023/prepared-window-r1/native-summary.json)。controller退出0仅表示编排正常返回，不能当作测试通过。

从冻结代码控制流可确定：错误发生在首个raw commit1图的49节点计数检查之后、实例化与replay之前。**该报错不能证明Fold kernel或Fold几何错误。** 循环先比较Record函数地址，任何未匹配节点都转入Fold地址与grid.z的联合检查；Record地址不一致也会报同一错误。

静态核对发现，raw Record/Fold在probe翻译单元取模板函数地址，而真实launch位于`recurrent.cu`；correction则由实际实现单元导出地址。raw源码的预期Fold grid为`(48,1,384)`、block为`(32,4,1)`，与驱动期望相同。因此跨翻译单元地址见证是待查假设。**失败时没有落盘实际节点序号、actual/expected函数地址及grid/block，无法在本轮确认根因。** 不以此判定候选数学错误，也不降低断言、重发GPU来补造现场。

若继续，最小修复范围应限于实际launch所属单元提供地址见证，以及完整节点参数诊断。保留本轮8个已过数值场景，只为未完成的Graph和计时另冻工具、账本与预算；本轮没有实施该修复或补测。

## 净收益结论

**Record＋Fold净收益未测量，不能写0%、无收益或NO_SIGNAL。** 五批配对数据完全未产生，≥10%且≥4/5批更快的segment门槛尚未评估。即使后续得到信号，也仅覆盖48个recurrent Record＋1个all-layer Fold，不包括投影、conv生产者、Attention/MLP、proposal/sampling、host许可或整轮Chat收益。

## 清理与交付

controller约6.97秒返回；guardian在窗口开始后6.80秒完成归属清理，早于720秒准入截止和900秒硬限。[清理回执](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-20261023/prepared-window-r1/runtime/cleanup.json)及[最终资源检查](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-hardware-20261023/final-resource-check.json)确认：候选exited/PID0、GPU计算进程为空、GPU锁已释放。原服务ID、镜像、启动参数SHA及cache dev/inode与冻结值一致，仍exited/PID0，没有未结束GPU请求。[最终回读](../output/ninfer-v4-k1-hardware-20261023/remote/ninfer-v4-k1-hardware-20261023/postflight.json)。

[持久交付归档](../output/ninfer-v4-k1-hardware-20261023/ninfer-v4-k1-hardware-20261023-delivery.tar.gz)SHA为`52a0431ef205efe87bc7d2c2eb06a23525322c39a483cb15e93957a86cdffd59`，已在本机验证，包含原始日志、预算、outcomes、失败summary、冻结输入及清理回执。[离线核验](../output/ninfer-v4-k1-hardware-20261023/evidence-verification.json)确认无超预算；独立代理复核同意上述结论，未代跑测试或GPU。[结构化结论](../output/ninfer-v4-k1-hardware-20261023/final-summary.json)。

V4当前入口和注册表已同步；修改前14份文档已备份。Baseline、18处G1差异、C1附件缺口、K2 CPU19原stdout缺口及全部历史失败保留；新增Graph实际节点参数缺口明确登记。`p95=null`、`optimization_qualification=false`，任务资格仍PENDING。
