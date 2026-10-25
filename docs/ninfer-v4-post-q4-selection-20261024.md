# Q4 方向收尾与下一实验：现有 W6 的完整 decode 边际收益

2026-10-24。本轮只做证据分析、`jssh 29` 只读核对与文档更新；没有修改远端源码，没有构建、测试、GPU、模型或推理 HTTP 请求。

## 结论

**关闭 Q4 FFN 紧凑 shared-memory／五级预取方向，不追加补测。下一项优先完成已有 W6/K5 路径的自然 MTP 完整 decode 对照。** 这是一项尚未完成、改造范围较小的实验，不是重新开发 W8，也不是重跑已通过任务。

选择它的原因是：现有 W4/K3 在三个已完成的自然请求上接近每轮4 token，而 W6 的性能部分从未运行；已有源码、控制器和六项数值／Graph证据可直接复用。下一次应回答“多验证两列增加的正式产出能否覆盖整轮成本”，而不是继续从局部 kernel 的微小变化推断用户收益。W6收益仍未知。

Q4 首筛中，紧凑四级／五级相对原路径耗时分别增加 **0.583%／1.325%**，32组中仅8组／7组更快；不具备采用信号。数值通过与性能无收益分别保留。候选exit0后控制器因root所有0600文件读取失败而exit1，原始权限和失败证据也保留，不能把整套工具报为PASS。[原结果](ninfer-v4-q4-compact-t4-hardware-20261024.md)

## 现有证据说明了什么

以下从原始结果派生，没有新跑请求；`Program ms/轮`不包含全部调度／输出／宿主间隔，**不是完整 round wall**。

| 已完成原请求 | 正式 decode token/轮 G4 | Program ms/轮 | 原结果 |
|---|---:|---:|---|
| Java | 3.660 | 23.224 | PASS |
| 中文推理 | 3.800 | 23.188 | PASS |
| 工具调用 | 3.767 | 23.239 | PASS |
| control | 3.505 | 23.264 | FAIL_MODEL_BEHAVIOR，保留 |

[逐字段计算与来源SHA](../output/ninfer-v4-post-q4-selection-20261024/evidence-analysis.json)。这些短请求不是总体业务分布，也不能掩盖97fc7be6输出耗尽、Gson／RE003失败。旧Pi参考的39条HTTP200按accepted统计得到约2.566 token/轮的条件估计，属于另一种teacher-forced分布；不能据高接受率短请求承诺全部Pi都受益。

令 `C` 为同一计时边界内的完整轮成本，`G` 为正式提交token数，则单位token成本为 `U=C/G`。要使W6的U下降10%，需要：

```
C6/C4 <= 0.9 × G6/G4
```

例如，**只有当G6实际达到5且单轮成本增幅不超过约18%～23%，才可能达到10%的单位token耗时下降**。若G6只有4.5，允许的成本增幅缩小到约6.6%～10.7%。第4、5个草稿位置的接受率尚未测到；这只是盈亏条件，不是收益预测。

原始推测解码论文同样把最优草稿长度与接受率、草稿成本联系起来，但其简化模型不能替代29的实际轮成本。[原论文 §3.3、§3.5](https://proceedings.mlr.press/v202/leviathan23a/leviathan23a.pdf) · [一手资料核查及适用边界](../output/ninfer-v4-post-q4-selection-20261024/primary-research.md)

## 源码依据与必要修正

在已有27B源码中：

- Q4 FFN与Q5 residual的T4/T6均走Small-T MMA，T≤8映射Tile8，因此这部分不是宽度增加50%就必然增加50%计算成本。
- **27B hidden=5120，完整Q6 head的T4走SIMT c4、T6走SIMT c6。** 权重解码可跨列复用，但activation读取、FMA和accumulator增加；不能引用hidden2048的MMA16分支，或声称head成本不变。
- `mtp_impl.h` 实际执行K次proposal head及K−1次串行AR。K3→K5会多两次AR/head，GDN/Attention有效列与采样开销也增加。必须测完整decode与提交，不能仅测Target矩阵乘。

引用位置：Q4 `q4_linear_swiglu_plan.cpp:34–36`，Q5 `q5_linear_add_plan.cpp:44–57`，H3 `small_t_rowsplit_mma.h:62–63`；Q6 `q6_dispatch.cpp:11–17`、`q6_rowsplit_gemm_simt.cuh:148–177`；H3 `mtp_impl.h:157–179`。[远端源码身份及哈希](../output/ninfer-v4-post-q4-selection-20261024/remote-readback.json) · [保存的H3源码哈希](../output/ninfer-v4-post-q4-selection-20261024/h3-source-sha256.json)

W6上次已通过六个独立数值／Graph场景。第七条链在3个Op之前因合法零workspace查询传给`WorkspaceArena(0)`失败；native和Chat均未运行。这是驱动失败，不能据此判定W6性能失败。原账本、缺失failure audit和未知资源总量继续保留，不补造、不清零、不退回额度。[W6原失败及边界](ninfer-v4-h3-w6-hardware-20261024.md)

## 最小实施范围

当前状态是 `SELECTION_ONLY_NOT_IMPLEMENTED_NOT_FROZEN`。后续实施限定在以下内容：

1. 从原H3隔离树 `49bee647112ee171de35529028fc271494260751` 继续，保留原消费过的冻结目录；修复失败链的最小workspace容量与异常审计。原六个PASS不重跑。
2. 复用H3控制器、guardian、BO和旧状态诊断。H3控制器已有宿主`--user uid:gid`，新冻结仍核对终态文件所有权；不复制Q4的权限缺陷，不新建控制器体系。
3. 为现有`target_mtp_round_bench.cpp`增加显式合同和有界自然性能模式：C1、W4/K3对W6/K5、262144 context/KV、rk4v4、Target原采样、32768请求输出预算。**不能沿用原bench的短context、BF16 KV、由测量轮数派生的输出预算、每轮仅K+1的剩余预算。** 按真实剩余输出额度调用，按诊断轮数结束测量并走既有许可终态；采样策略不变。
4. 保持自然proposal，不注入Oracle；记录实际accepted、正式committed token、fallback、逐轮输入位置与阶段成本。完整轮计时覆盖`decode_batch → resolve_pending_batch`，并有GPU完成见证；分别报告CUDA事件时间、宿主墙钟与阶段记账时间，不能互相替代。
5. 新增最多6个必要CPU合同，复用旧16场景及BO依赖；只构建受影响驱动与必要目标，做独立集成评审。禁止扩展W8、动态宽度切换、采样修正、词表或缓存格式。

**旧4个native请求使用Reference／Oracle，固定6＋1＋1＋1＝9次decode，只能证明状态资格。新自然性能4请求另计，不能用旧状态结果冒充性能。**

旧native仍有`<=16`的宽松保护。新冻结必须在实际decode入场前落实状态≤9、自然≤72、总量≤81的限制；不能只靠事后assert，也不能将旧账本中的未使用额度直接视为新授权。

## 拟议最小实机预算

| 部分 | 拟议新增上限 | 用途 |
|---|---|---|
| 原失败链 | 1场景、3 direct Op、1 capture／2 replay | 只补未进入的完整链 |
| 原未执行状态诊断 | 4 native请求、固定9 decode | 全许可／部分许可与canonical state |
| 自然性能 | 2个新prompt×W4/W6＝4 native请求 | Java与中文技术推理，各固定同一个配对seed |
| 自然性能轮数 | 每请求2 warmup＋16计时，共≤72 decode | warmup包含在总资源中，不增加warmup请求 |
| 合计 | **8 native请求／模型工作提交、≤81 decode；0 Chat、0 HTTP、0 wire** | 新账本独立记账，不重跑旧请求 |

选择每侧16个计时轮而非3个计时轮，是为了降低单轮偶然波动，同时不增加请求数；仍只有两个新prompt、每题一个seed，不能授予稳定性能或发布资格。按promptA W4→W6、promptB W6→W4的相反顺序做两对，记录GPU状态。提前EOS／失败不重试；样本不足就如实结束。不同宽度即使seed相同也可能产生不同输出，不能伪装成同token路径对照。

主指标为每个prompt的 `sum(计时轮完整wall) / sum(实际正式提交token)`；2个warmup轮不进入此比值，但token、耗时和资源全部保留。终态／截断轮不择优删除，缺测或边界不一致不形成信号。逐半段结果检查方向，保留raw逐轮信息。

进入下一步的首筛信号：数值／状态正确，两对单位token完整轮耗时均下降至少10%，前后半段不反转，未发现状态或合同异常。**10%是投入下一次Chat确认的门槛，不是承诺，更不是生产采用门槛。** 没有信号则结束本固定W6实验，不追加Chat、不扫K、不顺延到W8。若有信号，只提出单独有界的Chat确认范围。

上表1/2 capture/replay仅是数值链，**不含模型启动、Graph构建和warmup**。完整窗口的capture/replay、算法kernel、辅助传输和分配上限，必须基于新驱动与既有BO资源推导后冻结；当前为null，不存在可执行回执或空账本。拟议预算不构成当前GPU授权。[机器可读预算](../output/ninfer-v4-post-q4-selection-20261024/proposed-budget.json)

预计无GPU准备、构建和评审 **4–6工程小时**；后续实机 **5–10分钟，硬限20分钟，第17分钟清理候选**；分析 **0.5–1小时**。时间为工程估计；若需产品状态重构或改变数值合同，停止本小范围方案并报告，不默认扩大实施。

## 为什么暂不优先其他方向

| 方向 | 具体机会 | 当前排在后面的原因 |
|---|---|---|
| 选择性MTP alignment | 当前算W4所有输出列后只取accepted frontier；prefill已有全KV、单列tail先例 | 需要device索引、masked KV append和Graph状态证明；T1/T4数值路径可能不同，范围中等，尚无alignment占比。保留研究线索，不新增强制待办 |
| 物理缩K／跳过草稿 | 能减少真实AR/head工作 | 高接受率短请求会明显丢失每轮产出；logical extent变小并不省原Graph，动态K0还涉及历史和状态容量 |
| T4长上下文GQA Bc64 | 可减半key-loop／online-softmax合并次数 | KV字节不减，shared资源增加，softmax浮点顺序变；缺少当前热点占比，不能直接承诺收益 |
| 再扫Q5/Q6或其他Q4参数 | 可能存在shape特化机会 | 尚未发现更有力的新冗余证据；现有Q5融合、Q6跨列权重复用已在，不能靠试参数代替完整轮实验 |

W6是当前“证据基础、剩余工作量、潜在整轮收益”之间最值得先验证的一项，**不是证明它的绝对潜在收益最大**。DFlash2、全局检索及调度研究不由本次自动转成实施任务。

## 当前身份、保留项与实际验证

2026-10-24 12:30:33 UTC（北京时间20:30:33）通过`ssh -J jump 29`只读确认：H3/Q4工作树分别仍匹配冻结树，均无untracked；原服务exited／PID0，镜像、argv SHA和缓存inode匹配；GPU无compute进程，锁表未见GPU lease持有者。没有启动、停止或恢复任何服务。

本次实际只执行来源读取、SHA比较、旧JSON指标推导和文档一致性检查；**未运行CPU合同、构建或实机验证**。原服务继续停止。默认分派、Target采样、Pi medium／32768不变。C0、K1、K2-T01、K2-T05、H1、随机MTP和本次Q4关闭状态不变；全部原失败、18处G1差异、C1及Baseline附件缺口保留。`p95=null`，`optimization_qualification=false`，W6真实收益为null。

独立只读评审未发现本轮选型的阻塞问题；评审特别指出旧native宽松计数需要在未来冻结前收紧，已写入上面的实施范围。评审没有运行构建或测试，不能作为实机PASS。

当前执行入口与注册表只追加Q4关闭和W6选型状态；旧条目和原始材料保留。交付索引：[选型记录](../output/ninfer-v4-post-q4-selection-20261024/selection.json)。
