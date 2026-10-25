# K2-T05收尾：下一项选择H1-T01同宽整包Lookup

**K2-T05收尾，追加补测预算0。下一项选择H1-T01：request-local有界Lookup，在C1/W4/K≤3内整包选择Lookup或现有MTP草稿。** 首版不跳过MTP对齐或下一轮草稿计算，不扩宽、不改Target采样。当前只完成选型、源码核对和文档；没有实施补丁、构建、测试或GPU/HTTP/模型请求。性能收益仍未知。

## 收尾结果与研究基点

K2-T05已有完整状态/logits逐bit PASS、Chat4/4 PASS；完整Prefill配对中位改善0.313951%，低于冻结1%门槛，TTFT文本/工具仅观察改善0.881%/0.362%，各一对样本。两次warmup标点不符的原失败、最早native失败、请求ID失败、断联和成本全部保留。不再补测T512、native、Chat或旧Baseline，不进入该候选的K4/发布。原T1024算子段36.48%信号不能覆盖完整模型未达门槛的事实。

[关闭回执](../output/ninfer-v4-post-k2-t05-selection-20261024/K2-T05-closeout.json)绑定[原始报告](ninfer-v4-k2-t05-chat-remaining-20261024.md)及分析/交付SHA；不改旧成绩、账本或raw。C0、K2-T01、K1-T01继续关闭，额外预算0。

本轮`jssh 29`回读确认原服务exited/PID0、镜像/argv/cache身份未变、GPU无计算进程。后续开发基点选**raw对照树**`a5ba33de12d75ab1e16a153020e4068094ee1757`，分支`codex/k2-t05-full-prefill-raw-20261023`，不是带未采用T1024分派的候选树。1279个index项与该冻结树一致，working tree无未暂存差异；9份相关源码逐字节匹配index blob并保存本地SHA。[只读身份回执](../output/ninfer-v4-post-k2-t05-selection-20261024/live-snapshot.json)、[源码见证](../output/ninfer-v4-post-k2-t05-selection-20261024/source-witnesses.json)。新隔离分支尚未创建。

## 为什么选择Lookup

旧Baseline39条HTTP200 Pi描述中，decode占prefill＋decode合计约70.51%，接受草稿/round约1.566；最近4个新Chat合计120轮，接受243/草拟360个token，即每轮接受2.025个draft、整体67.5%。这些不同长度、随机seed的样本只说明现有MTP并非总能接受3个draft，**不等于Lookup命中率或新方案收益预测**，也不是生产流量权重。`accepted+1`不当作显示/正式提交token数。[重算与限制](../output/ninfer-v4-post-k2-t05-selection-20261024/evidence-assessment.json)。

四个新Chat的“请求decode累计秒数÷已报告MTP轮数”约为23.75–23.78ms/轮。这是请求汇总的成本proxy，**不是实测逐轮wall或Target/MTP分项时间线**；它支持研究减少整轮次数，不能据此声称Lookup会命中或省掉多少计算。

现有源码提供较窄的接入点：`decode_mtp_batch`先把host的`current_drafts`装入既有W4 Graph，再按这份完整前缀重新做Target verify/accept；许可后才把真正committed token写入ledger。因此可以只改变确定性proposal来源，测试是否减少昂贵Target轮数。它关注持续decode，避免继续把小算子段的改善外推为完整请求收益。

| 候选 | 当前取舍 |
|---|---|
| H1-T01同宽Lookup | 选中。可复用host ingress、Target验收和MTP状态流程；真实命中及净收益必须由新试验验证。 |
| 再调norm/correction/conv | 三轮已有结果不足以支持整体采用；相关任务关闭，不换shape继续补测。 |
| Q4/Q5或draft-head裁剪 | 有理论潜力，但已有small-T/optimized head实现，尚无分项时间证明该选哪个新配置；暂不同时开工。 |
| Workspace/fork-join | 缺真实allocator压力或独立关键路径证据；不能把容量差额直接当性能收益。 |
| W8/W16、DFlash2、全局检索、utility、上游合并 | 仍是可选实验，不是本项前置。扩宽/资产/检索/策略成本更高，当前不并行推进。 |

这是投入与可证伪性排序，不是已证明Lookup是最大热点。greedy proposal＋Target production sampling已经存在，不能换名字再开发或算作新收益。

## 首补丁的具体范围

profile：`REQUEST_LOCAL_LOOKUP_PACKET_C1_W4_K3_N4_RING8192_V1`。固定C1、W4、K3、4-gram、最近8192个已许可token、16384个索引槽；index新增host空间≤512KiB，诊断缓冲≤256KiB/请求，不新建GPU workspace或allocator。

1. 索引归`RequestControl`，不放进可复用`SequenceState`或continuation序列化。绑定新请求、terminal/clear/error必须显式清理；restore后只从当前请求已验证prefix/ledger重建。源码`clear_lane`不是整体赋空RequestControl，新成员不会自动清掉，不能遗漏这些生命周期。
2. 只索引正式许可的prompt/输出IDs。按`resolve`后的实际committed数增量更新，不录入拒绝draft，不用SSE重新tokenize冒充原token轨迹，不跨请求拼历史。固定容量、碰撞后精确核对token、越界/陈旧源视为miss；不扩大到全局检索。
3. 只在原extent恰为3且已有完整三-token后缀时选择整个Lookup packet，写入原host ingress；其余情况保持原MTP packet，包括remaining1/2、容量尾轮和no-hit。首版不逐列混合，避免新增条件前缀和MTP后缀重算分支。
4. 复用原`speculative_prepare_verify_inputs`→完整Target verify→`speculative_accept_greedy_drafts`。不重用被替换前缀的Target logits，不裁Target支持集，不改processor/RNG/bonus/permit/正式state/conv或缓存格式，也不新增speculative backend。
5. 原MTP alignment和下一轮proposal都继续执行。**命中一轮不会直接省掉这一轮的MTP计算**；只有接受改善、总轮数下降时，才可能节省那些不再执行轮的总成本。proposal-skip/COPY、W8等不属于首补丁。
6. 记录eligible/hit/selected/source-offset及分来源accepted深度。index创建/append/查找、host搬运、verify、alignment、permit和commit必须进入完整round/service计时；源码现有tail timer结束在ledger后处理之前，不能把新增append放到旧计时区间之外，再声称净收益。诊断缓冲不在逐token关键路径fsync。

主要修改`program.h`的请求私有成员、一个内部有界索引helper和`program_impl.h`的入包/正式commit/生命周期接点。`mtp_impl.h`、Target采样kernel和Graph拓扑原则上复用；若实现证据表明必须改动它们，应先更新范围和预算，不能悄悄扩大。复用r4修复后的响应ID、owner/端口、guardian和耐久账本工具，**只复用代码/合同，不重启旧single-use根目录**。

源码位置：[请求/保留状态分界](../output/ninfer-v4-post-k2-t05-selection-20261024/source-witnesses/src/targets/qwen3_8/impl/runtime/program.h:258)、[入包与预算裁剪](../output/ninfer-v4-post-k2-t05-selection-20261024/source-witnesses/src/targets/qwen3_8/impl/runtime/program_impl.h:3344)、[正式commit](../output/ninfer-v4-post-k2-t05-selection-20261024/source-witnesses/src/targets/qwen3_8/impl/runtime/program_impl.h:1121)、[Target与mandatory MTP对齐/下一轮](../output/ninfer-v4-post-k2-t05-selection-20261024/source-witnesses/src/targets/qwen3_8/impl/runtime/mtp_impl.h:120)、[共享Target接受权威](../output/ninfer-v4-post-k2-t05-selection-20261024/source-witnesses/src/targets/qwen3_8/impl/runtime/speculative_target_impl.h:9)。

## 最小验证预算与耗时

以下是**下一项提案，不是当前执行授权或已冻结可运行账本**。没有把H1旧32wire/84native通用模板相加进来，也不重新做旧Baseline或已通过算子/Graph矩阵。

| 阶段 | 最小新增范围/上限 | 预计耗时 |
|---|---|---|
| CPU补丁、BO、定向合同、集成评审 | ≤16新合同；复用依赖、原数学与旧已通过证据，0 GPU/模型/HTTP | 12–16工程小时 |
| 新驱动与回执冻结 | 记录真实token来源、资源/拓扑边界和新空账本；不执行旧驱动 | 4–8工程小时 |
| 未来GPU状态首筛 | 2个新状态场景，≤4次native请求、≤16次Program decode/verify调用 | 包含于下述同一窗口 |
| 未来Chat首筛 | 3个新场景×raw/Lookup＝6个Chat，另2次warmup；8次HTTP模型提交＋2次health＝10wire | GPU预计5–10分钟；硬20分钟/第17分钟清理 |
| 结果核对 | 全部失败/成本/状态和完整round净收益 | 0.5–1小时 |

工程准备合计**16–24小时，约2–3工程日**。新GPU窗口合计最多12个模型工作提交＝native4＋HTTP8，新增旧数值Op/Graph场景0；Program入口调用次数不是算法kernel次数。两种native状态场景为：Lookup与MTP packet相同的逐bit状态/conv/下一步对照；Lookup packet不同且发生拒绝/partial permit时，与正式Target前缀参考的一致性。尾轮、reset/restore索引隔离先做新增CPU合同；完整分布/restore/cancel资格仍由H1-T07/K4独立覆盖，不能拿该最小pilot冒充全部通过。

三个新Chat拟覆盖代码复制正例、重复结构化工具/代码输出、低重复控制；正例实际route必须命中，控制实际无命中才可评价no-hit成本。HTTP场景只用Chat Completions。context/KV仍262144，Target temperature1/top_p.95/top_k20及Pi medium/32768不变；新Chat夹具暂沿用2048输出上限，与Pi无关。

资源保守上限另列在[selection.json](../output/ninfer-v4-post-k2-t05-selection-20261024/selection.json)：capture≤256、replay≤73728、算法kernel≤35651584；拷贝/字节分方向有限。它们只是新窗口候选上限，不是预计实耗或重用旧授权。新驱动仍须枚举实际capture/replay/kernel/copy路径并冻结后才能发GPU，任何上限先到就停止，不缩context/输出、不自动加预算。

## 收益和停止条件

当前Lookup真实命中率、接受提升、完整round额外成本均未测得，预期收益记为null。首筛目标为正例decode wall/实际生成token下降≥5%，no-hit开销≤1%，且工具/状态/Target合同不退化；**5%是信号门槛，不是性能承诺**。单对波动无法支持1%判断时记INCONCLUSIVE，不增加样本来凑通过。

只要没有真实Lookup route-hit、没有净收益或出现正确性问题，就保留MTP并停止该profile，不自动加词长、ring大小、W8或全局库。CPU可以直接在隔离分支开工，不等待完整GPU分布/发布门禁；完整候选资格与生产发布仍独立。本次原GPU服务继续停止，18处G1差异、C1附件缺口及所有旧失败/成本保留。`p95=null`、`optimization_qualification=false`。
