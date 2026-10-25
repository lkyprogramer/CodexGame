# C0收尾与下一项选择：SM89 gated RMSNorm小形状CTA实验

C0关闭，不再追加补测。下一项选择 **K2-T01：D128 gated RMSNorm的CTA映射实验**，先用小补丁和不加载模型的GPU算子筛选，验证128/256线程是否优于现有512线程。它是当前边界最小、最容易止损的GPU执行候选；尚无norm耗时占比，不能称为已确认的最大热点或承诺整机收益。

本轮仅通过`ssh 29`只读核查，不修改产品、不构建、不运行新旧产品测试，不发GPU/HTTP/模型请求；仅做文档与合同一致性检查。原服务继续停止。

## C0关闭与现况

[C0关闭回执](../output/ninfer-v4-k2-selection-20261023/C0-closeout.json)将额外补测预算设为0，禁止自动接续或重开旧窗口。保留CPU加速结果、真实L2恢复成功以及TTFT收益未证明的全部原始结论，不将收尾改成性能PASS。

当前回读确认：原服务exited/PID0，原image `e753e228...`、cache dev/inode66306/24150039不变，GPU计算进程为空；C0控制器/驱动/监护均退出。原21冻结文件、P4/C0 serve二进制SHA与C0运行归档SHA一致。12份相关源码与C0产品树逐文件blob匹配。[回读与源码见证](../output/ninfer-v4-k2-selection-20261023/remote-read-only-snapshot.json)。

新实验的工程基点为已构建的C0树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`，只在相同基点上比较norm改动，避免另改CPU后端。P4原参考树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`继续保留。这不授予C0生产或完整性能资格。

## 为什么先选这一项

- 当前27B有48个GDN层，value head数48、head dimension128。真实执行链在GDN输出之后调用已有RMSNorm＋SiLU gate，再进入输出投影；不是再加一次融合。
- aligned gated D128当前进入512线程的通用warp kernel，每warp负责一行。T1共48行，只有3个CTA；改同一kernel为128/256线程时分别为12/6个CTA。T4对应192行，分别为48/24/12个CTA。
- 单warp中的归约、gate表达式、乘法顺序和BF16输出可保持原样。改变的是行到CTA的调度，可用很少形状直接否证；不增加记录空间、状态或工作区。
- 当前MTP draft_tokens=3，verify width=K+1=4，因此只选T1和T4。T6、W8/W16、大prefill矩阵均不纳入本次。

源码位置：`src/ops/launcher/rmsnorm.cu:23–42,89–90`；`src/ops/kernel/rmsnorm.cuh:28–79`；`src/targets/qwen3_8/impl/runtime/text_context_impl.h:1060–1065`；`src/targets/qwen3_8_27b/impl/config.h:21–26,67`；`src/targets/qwen3_8/impl/runtime/mtp_impl.h:80`。它们均已在29只读核对并绑定源码见证。

L2恢复的extra payload副本暂不排第一。当前已有lookup共享image、decode-ahead和消除preflight重复decode的实现；本次没有prepare hits/inline分项，无法证明副本位于观测到的602.861ms同步恢复关键路径。原1.3GB内存L2 image也未持久化，候选退出后不存在，不能声称可直接复用真实冻结snapshot。仅看到额外复制，不足以再次推导TTFT收益。

GDN correction的记录/事务/显存代价更大；更宽草稿、Lookup及资产路线的第一证明也更重。它们继续保留可选资格，本次不同时实施。

## 实施范围

1. 只比较同一个`rmsnorm_warp_bf16x2_kernel<Gated,Block>`的原512与128/256候选。不改用专门plain D128表达式，避免改变浮点运算顺序。
2. 第一份可构建补丁只补bench/test的显式Gated候选及计数驱动，原产品默认分派不动。胜者出现后，才在SM89隔离候选中加入D128、aligned、rows48/192的静态路由。T2/T3尾轮、大prefill、unaligned、其它epilogue/维度继续原路径。
3. 复用已有double oracle、原数值阈值和guard检查，并要求相同输入的新旧BF16输出逐字节一致。`__launch_bounds__`改变仍可能影响编译结果，不能仅凭表达式相同跳过实际数值验证。
4. 不新增autotuner、环境变量接口、workspace、allocator或采样分支；原模型、codec、SHA/ContentId/缓存格式、RNG/许可权威、采样及Pi medium/32768不变。
5. 只构建受影响的launcher、Op、bench和必要集成目标，复用BO及P1—P4证据；不重跑旧Baseline、P3矩阵、G1、题目或grader。

三个驱动陷阱必须先修正：现有rmsnorm candidate只支持plain，未传gate；现有`--control`是payload带宽控制，不是原512 RMSNorm算法；现有`gdn_layer_bench`是35B的hidden2048/32heads/W8，不能替代本机27B真实整轮。现有27B `target_mtp_round_bench`默认BF16、小context及未显式冻结采样，也不能原样作为现况资格。

## 首轮最小验证预算

这是后续建议预算，本轮未执行，也没有继承C0额度。先交付CPU可构建补丁和驱动，再执行下表GPU筛选；不把完整GPU验收挡在开工前。

| 项目 | 冻结提案上限 |
|---|---:|
| 数值逻辑场景 | 8：2个T×普通/near-zero/饱和gate共6，加2个回退场景 |
| 新direct Op调用 | 22：6×3种CTA＋2×原/候选回退 |
| Graph capture | 6：2个T×3种CTA，每图仅一个norm节点 |
| 正确性replay | 12：每图2次 |
| 计时配置 | 6；每配置10次warmup＋5批×64次计时 |
| 计时replay | 1,980 |
| 全部单节点Graph replay | 1,992，含正确性与warmup |
| HTTP wire / 完整模型请求或准入 | 0 / 0 |
| 实际GPU时间估计 | 2–5分钟 |
| 硬窗口 / 清理开始 | 10分钟 / 第7分钟 |

这些是微小norm算子的调用，不是1,992个模型请求。现有bench没有这一冻结计数接口，实施时必须补齐并在真实GPU前冻结回执、空账本及计划；禁止默认无界循环。bench/Graph helper的隐式预热及首调也须计入22次direct或1992次replay，不能在表外另发射。编译不需要切换GPU服务。

数值、真实Gated route与guard必须全部通过；同输入和同Graph交错5批比较。至少一个当前可达形状的单Op中位耗时降低≥10%，且至少4/5批方向一致，才进入后续整轮验证。没有稳定收益、数值不等或资源回退即停止，保留原512，不扩形状追求通过。若只T1变快但当前MTP3没有实际T1 route命中，不算现网MTP收益。

## 采用门禁与耗时

预计CPU补丁、BO增量构建、驱动/预算CPU合同及集成评审 **3–5工程小时**。首次GPU筛选 **2–5分钟**；完整数值比较在GPU上执行，不能将CPU构建通过冒作数值PASS。

只有首筛胜者才准备真实27B完整round：同一输入/初始state/RNG权威，保留context262144、现有codec及Target sampling，计入draft＋verify＋commit＋同步与实际许可token。拟最多2次native请求准入（旧/新各1），每侧2个warmup round＋10个测量round，共24次decode_batch调用，HTTP为0。不能直接运行旧bench的BF16/小context默认配置。

该真实驱动预计另需 **1–2工程小时**，GPU **5–10分钟**，拟硬窗15分钟、第12分钟清理。内部Graph capture/replay数尚未由新驱动枚举，合同保留null和原因；在准备完成并冻结这部分精确账本前不得执行。它是胜者的后续采用门禁，不是开发前置，也不是本轮授权。若两个阶段以后均获准，GPU硬上限合计25分钟，不叠加各任务通用额度。

没有norm实际耗时份额，整轮和Chat收益目前为null。若norm占比为f、算子加速s，整体理论加速为`1 / ((1-f)+f/s)`；CTA数增加不等于同倍提速。单Op通过但完整round无改善，实验仍结束，不宣称推理提速或K4；候选资格与生产发布继续独立。

[完整选择合同](../output/ninfer-v4-k2-selection-20261023/selection.json)保留范围、计数、止损与未知字段。C0既有结果、18处G1差异、C1附件缺口及所有失败/成本保持原样。本轮新GPU/HTTP/模型/构建/测试均0，`p95=null`、`optimization_qualification=false`。
