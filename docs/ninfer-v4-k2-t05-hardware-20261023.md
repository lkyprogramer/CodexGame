# K2-T05最小实机筛选：T1024有整段信号，T512计时不合格

**4个场景的逐bit、原FP64参考及guard检查全部通过，4张实际Graph全部通过。T1024卷积＋state更新＋提取整段配对中位耗时下降36.4834%，5/5批更快，达到冻结的段级信号门槛。T512虽观察到下降，但host提交占比未达预定要求，收益结论为INCONCLUSIVE。**

本窗口已经结束，未追加请求或迭代。原服务保持停止，默认分派、采样/context及Pi medium/32768未变。这里的收益仅针对该算子段，`optimization_qualification=false`，尚无完整prefill或Chat提速结论。

## 数值与实际Graph

| 范围 | 结果 |
|---|---|
| T65、T128、T512、T1024 | 完整Q/K/V BF16输出与conv state逐bit等于raw，PASS |
| 唯一原FP64卷积参考与原A16准则 | PASS，未修改阈值 |
| 非零history、分界/末通道压力输入、guard及不可变输入 | PASS |
| state输入输出 | T65/T512精确同址，T128/T1024分离，均PASS |
| Graph T512/T1024各raw/split | 4次capture全部`WITNESS_PASS` |
| 实际节点 | raw为2 kernel＋3 D2D copy；split为2 kernel |
| 函数、grid/block、shared、kernel参数、copy地址/pitch/extent/方向及依赖 | PASS |
| Graph correctness、warmup及全部计时后的逐bit | PASS |

函数地址来自实际launch TU。4份Graph诊断保存了实际节点参数，未从探针重新实例化kernel来替代见证。独立FP64检查覆盖4个直接数值场景及Graph correctness；warmup/timing使用逐bit、guard和输入完整性检查，没有另造参考。

## 卷积＋提取整段净收益

计时范围为输出卷积、原state更新及raw三次二维D2D提取，对照直接写连续Q/K/V的候选两kernel。输入投影、GDN递推、整层或模型prefill均不在该段内。

| T | raw event中位数 | split event中位数 | 同批配对改善中位数 | 更快批次 | 冻结判定 |
|---|---:|---:|---:|---:|---|
| 512 | 36.180 μs | 22.784 μs | 38.4411%（仅观测） | 5/5 | INCONCLUSIVE：host提交门槛未过 |
| 1024 | 64.084 μs | 40.704 μs | **36.4834%** | **5/5** | **SEGMENT_SIGNAL_NOT_K4** |

两列耗时各自取中位数；改善采用五批同批配对改善的中位数，因此不必等于两列中位数之比。每图5批×8次timing replay，AB/BA交错；reset、检查及导出均位于event区间外，host投递和完成wall单独保留。

冻结采用门槛是配对中位改善至少10%、至少4/5批更快，并满足每批raw/split的host提交时间不超过对应event段的25%。T512候选在第2/3/4批的占比分别为34.81%、26.90%、31.97%，所以不能因5/5更快而跳过门槛，也不删除这些批次重算资格。T1024全部满足，raw占比最高13.58%、split最高7.77%。这些占比是冻结的计时质量筛选指标，不是直接测得的GPU空闲比例；event结果也不称为纯kernel latency。

冻结native给出`SEGMENT_SIGNAL_ONE_SHAPE_NOT_K4`。[离线审计](../output/ninfer-v4-k2-t05-hardware-20261023/offline-audit.json)从10条原始配对记录重新计算中位数、胜出批次和host条件，与native一致，没有再次运行GPU或测试。

只有T1024获得本段信号。T65/T128只有数值证据，T512收益尚不合格，不能将四种shape整体授予产品路由资格。未进行完整prefill/Chat验证、服务部署或默认分派切换，不把36.48%外推为TTFT或tokens/s改善。

## 实际预算与清理

| 计账项 | 实际 / 冻结上限 |
|---|---:|
| 数值场景 | 4 / 4 |
| direct Op | 20 / 20 |
| Graph capture | 4 / 4 |
| Graph replay（含warmup） | 184 / 184：8 correctness＋16 warmup＋160 timing |
| 算法kernel | 384 / 384：16 direct＋368 replay |
| 模型提交 / HTTP | 0 / 0 |
| raw提取copy | direct host调用12、capture host调用6、replay执行276，均到原上限 |

辅助传输独立计账，包含初始化、poison、reset、guard与导出，无helper compute kernel或memset：

| 辅助方向 | 实际次数 / 上限 | 实际bytes / 上限 |
|---|---:|---:|
| H2D | 214 / 508 | 1,134,373,888 / 4,447,860,736 |
| D2D | 44 / 128 | 2,725,888 / 7,929,856 |
| D2H | 240 / 768 | 1,153,720,320 / 5,386,141,696 |

24条reservation全部`COMPLETED`，ledger为`COMPLETE`，无unknown。窗口控制器耗时6.767秒，候选于启动后6.701秒清理，早于420秒清理点及600秒硬限。候选exit0/PID0，GPU无计算进程、lease已释放；原容器、镜像、argv、缓存device/inode身份保持不变，原服务仍exited/PID0。窗口已single-use消耗，无追加余额，不重启或补测。

运行前后的clock/power是只读spot记录，未锁频，也没有逐kernel硬件计数器。初始GPU为RTX4090、driver610.57.04；没有改GPU/采样/模型配置。完整checkpoint设备张量未另存为内存dump，保留的是实际逐bit/oracle/guard结果、可重现输入生成代码、原始日志和完整Graph诊断。

## 身份、证据与保留项

- 候选树：`3ea537c00c759ef2a4577b525ae691f694ae102e`。
- 原冻结SHA：`7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc`。
- probe SHA：`b1679dd61eee7eae0a3990129f32a0e8a0af8262fdb23e43d10dbef49aea7c19`。
- 8份冻结输入及源码身份均前后匹配，没有覆盖冻结工具或修改候选源树。
- 原始证据归档SHA：`aae1f54f298327f20c4c7b409ab6e3cdabecf5c1fde738714265777263c6a98c`。

[最终摘要](../output/ninfer-v4-k2-t05-hardware-20261023/final-summary.json)、[native summary](../output/ninfer-v4-k2-t05-hardware-20261023/remote/prepared-window-r1/native-summary.json)、[24条原始outcomes](../output/ninfer-v4-k2-t05-hardware-20261023/remote/prepared-window-r1/native-outcomes.jsonl)、[原始ledger](../output/ninfer-v4-k2-t05-hardware-20261023/remote/prepared-window-r1/budget-ledger.json)、[清理readback](../output/ninfer-v4-k2-t05-hardware-20261023/remote/hardware-r1/postflight.json)、[归档回执](../output/ninfer-v4-k2-t05-hardware-20261023/archive-receipt.json)。4份逐节点诊断位于[持久证据目录](../output/ninfer-v4-k2-t05-hardware-20261023/remote/prepared-window-r1)。

原16项CPU合同和[BO实施证据](ninfer-v4-k2-t05-implementation-20261023.md)直接复用，没有重跑。18处G1差异、C1附件缺口、初次依赖复制/构建失败及全部历史失败保留。C0、K2-T01、K1-T01保持关闭和追加预算0。`p95=null`；本轮段级信号不授予K4、完整sampling或生产发布资格。
