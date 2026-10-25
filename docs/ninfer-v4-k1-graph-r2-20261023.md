# K1-T01 Graph修复与计时补测：通过正确性，未取得净收益信号

**Graph函数地址见证修复已通过实机验证，6张图与逐bit检查全部通过；Record＋Fold未达到可采用的净收益门槛，继续保留raw默认路径，不进入K1-T02产品接入。** 本轮只补Graph与计时，旧8个数值场景通过SHA复用，没有重跑。

| 提交列数 | raw中位耗时（μs） | correction中位耗时（μs） | 配对相对增益中位数 | 更快批次 |
|---|---:|---:|---:|---:|
| 1 | 692.224 | 699.992 | -1.054% | 0/5 |
| 2 | 700.540 | 701.044 | -0.071% | 0/5 |
| 4 | 707.456 | 706.176 | +0.181% | 3/5 |

每个配置有5个AB/BA交错配对批次，每批每路线8次replay。增益为每批`(raw-correction)/raw`的中位数，正数表示更快；它不是两列独立中位耗时之比。门槛保持≥10%且≥4/5批更快，三个配置均不满足，结论为`NO_SEGMENT_SIGNAL`。提交4列的+0.18%不能解释为稳定可采用的提升。

计时包含48个recurrent Record＋1个all-layer Fold及主机逐次投递间隙，包含新增correction记录的算子内写入/读取；状态D2D reset位于event外。它排除投影、conv生产者、Attention/MLP、proposal/sampling和host许可，不是完整Target Verify、模型整轮或Chat收益。只有五批短窗口，不提供p95或置信区间。仅凭这些数据不能确认算术节省为何未转成收益；额外记录流量是可能因素，当前未做独立kernel归因，不当作已证明根因。

## 修复、构建与冻结

通过`jssh 29`在新隔离分支`codex/k1-graph-witness-r2-20261023`实施，根为`/home/hhtele/ninfer-v4-k1-graph-r2-20261023`，基点`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`、候选树`41a913488b0138fe868a8321d2f6a86ce83e313f`。HEAD仍为O，未提交、推送或部署。[补丁](../output/ninfer-v4-k1-graph-r2-20261023/remote/evidence/K1-graph-r2.patch)和[源码身份](../output/ninfer-v4-k1-graph-r2-20261023/remote/evidence/source-identity.json)保存完整来源。

raw masked Record与48×48 Fold的地址由真实launch所在`recurrent.cu`导出，probe移除`recurrent.cuh`本地模板实例化取址。新增bench私有元数据validator，保持49节点、48 Record＋1 Fold、函数身份、grid、block及共享内存强校验。capture在校验前逐节点耐久保存actual/expected地址、index、type、grid/block、shared及GetParams状态；错误定位不再把所有未匹配节点都报成Fold。

变更10文件，其余1243个基点文件匹配。`recurrent.cuh`、`correction.cu`、FP64 oracle和typed correction布局逐字节保持；raw `.cu`除了两个host地址getter外，kernel与launch函数体字节一致。Engine/Program、默认分派、采样、Pi预算、codec和缓存格式未改。旧8数值的原始outcomes、8条完成预留、首次失败summary、身份及冻结回执共6附件纳入新冻结，并保留旧`RESERVED_UNKNOWN`。

复用BO镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`及原构建/依赖。Release、CUDA13.2、SM89、仅27B、最多4 worker，`runc`无网络、无NVIDIA设备。实际命令为：

```sh
cmake --build /build -j 4 --target ninfer_k1_graph_contract_test ninfer_k1_gdn_correction_probe ninfer-serve
/build/tests/ninfer_k1_graph_contract_test
cd /src/tests/k1
NINFER_K1_PROBE=/build/bench/ninfer_k1_gdn_correction_probe python3 -B -m unittest -v test_graph_r2
```

BO增量构建通过，耗时20.633秒。8个新Graph元数据CPU合同和8个Graph-only工具CPU合同通过，覆盖地址/几何/节点数量负例、复用证据篡改、无完成预留的假PASS、旧预算拒绝和一次性runtime保护；没有执行旧suite或旧Baseline。独立评审闭合，评审代理没有代跑测试或GPU。[原始构建与CPU日志](../output/ninfer-v4-k1-graph-r2-20261023/remote/evidence/)，[评审记录](../output/ninfer-v4-k1-graph-r2-20261023/review.json)。

profile为`SM89_GDN_CORRECTION_C1_W4_L48_GRAPH_ONLY_R2`。新冻结SHA `29c89db3f440cea8b8620e0728dd9220c7c3366782fbc408b283e5aedd9e0969`，probe SHA `f56448d676af7893df3b74bb7788c04bb5fbf7fad01e1332b2c05af1a102430e`；13个冻结输入、空账本及复用证据校验通过才启动。[冻结回执](../output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/freeze-receipt.json)，[准备回执](../output/ninfer-v4-k1-graph-r2-20261023/remote/evidence/preparation-receipt.json)。

## 实机结果与预算

| 项目 | 实际 / 上限 |
|---|---:|
| capture | 6 / 6，每图49节点 |
| correctness replay | 12 |
| warmup replay | 24 |
| timing replay | 240 |
| 全部replay | 276 / 276 |
| 算法kernel执行 | 13524 / 13524 |
| direct Op / 新数值场景 | 0 / 0 |
| 模型 / HTTP | 0 / 0 |

30个预留全部`COMPLETED`，当前ledger为`COMPLETE`，无未知预留。6份Graph诊断的294个节点均匹配真实函数地址及几何。[账本](../output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/budget-ledger.json)，[原始outcomes](../output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/native-outcomes.jsonl)，[原始summary](../output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/native-summary.json)。

Graph correctness、warmup和15个计时配对后的48层FP32 state、conv及BF16 readout逐bit对照全部通过；Graph correctness继续沿用layer0原FP64参考与原阈值。旧8场景未重跑；Graph replay里的正确性检查属于本次授权的12次correctness replay。

实际传输H2D312次/1,237,932,256字节，D2D54次/8,313,007,104字节，D2H336次/11,617,284,288字节，均低于冻结的独立上限。没有未计账warmup、helper compute或memset。

新run已解决当前六图的地址见证并保存完整参数。**旧首次失败的实际节点参数仍缺失，不能由新结果反填或确诊旧现场是哪一个指针。** 首次失败原因、旧账本UNKNOWN、C1附件缺口、K2 CPU19原stdout缺口和全部历史失败原样保留。

## 清理与采用结论

controller约10.701秒返回，guardian在窗口开始后10.580秒完成清理，早于第12分钟清理阈值和15分钟硬限。候选exit0/PID0、GPU计算进程为空、共享锁释放；原服务身份/镜像/参数SHA/cache dev/inode及原serve SHA不变，仍停止，没有恢复原服务。[清理回执](../output/ninfer-v4-k1-graph-r2-20261023/remote/prepared-window-r1/runtime/cleanup.json)，[最终资源检查](../output/ninfer-v4-k1-graph-r2-20261023/remote/hardware-r1/final-resource-check.json)。

correction方案在本C1/W4/L48算子段的正确性成立，但性能门槛未通过。它还新增完整10,260,480字节（约9.785MiB）correction payload；未证明可与raw池互斥alias，不能宣称显存节约。**保留raw，不默认启用correction，不推进本候选的产品接入，也不追加配置或GPU补测。** 这不等于证明所有形状或所有correction设计都无收益。

[持久交付归档](../output/ninfer-v4-k1-graph-r2-20261023/graph-r2-delivery.tar.gz)SHA `87fce9ac4e9b482d3e21ef7822e0d9b902b434c3200d894e14c8d70bb3149400`已本机核验，包含补丁源码、BO/CPU日志、新冻结输入、复用附件、6份节点诊断、所有计时数据及清理证据。独立代理重算全部配对增益、胜批数、预算和冻结SHA，与本结论一致。[离线核验](../output/ninfer-v4-k1-graph-r2-20261023/evidence-verification.json)，[结构化结论](../output/ninfer-v4-k1-graph-r2-20261023/final-summary.json)。

V4入口、注册表和预算已同步，修改前14份文档另有备份。原Baseline、18处G1差异和旧资料未改。`p95=null`、`optimization_qualification=false`，候选资格与生产发布资格均未授予。
