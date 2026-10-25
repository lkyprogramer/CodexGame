# K2收尾与下一项选择：GDN correction records

K2-T01正式关闭，追加补测预算为0。下一项选择 **K1-T01：GDN correction records隔离原型**。先验证真实27B几何下的48层recurrent Record＋统一Fold段；不接入Engine，不改产品默认分派。源码已确认存在重复计算，但其当前耗时份额和净收益尚未测得，不能称为已证实的最大热点。

本轮通过`jssh 29`只读核查。按本机既有函数使用`ssh -J jump 29`，没有改连接配置。未修改远端源码、构建、运行测试或发起GPU/HTTP/模型请求。原服务保持停止。

## 已收尾结果与当前身份

[K2关闭回执](../output/ninfer-v4-post-k2-selection-20261023/K2-closeout.json)保留数值/Graph PASS和四组性能NO_SIGNAL，禁止重开已消耗窗口、不进入有赢家后的整轮验证。原K2汇总和原始归档SHA未改。C0同样保持关闭；其CPU收益、真实L2恢复成功与TTFT收益未证明的结论不回写。

当前回读确认：原服务exited/PID0、GPU计算进程为空；容器ID、原镜像、启动参数SHA和cache dev/inode66306/24150039不变。K2源树仍为`13223b2b2989d0cf580715b197b276d74acffc86`，无index或工作区漂移，6个冻结输入哈希一致。后续工程仍以C0产品树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`为基点；K2相对它只有bench/test增量，产品583个src文件未变。不会把旧K2驱动当作待运行任务。[只读快照](../output/ninfer-v4-post-k2-selection-20261023/remote-read-only-snapshot.json)。

17份相关源码从29读取，逐文件与当前index blob及本地副本匹配，原始字节与SHA已保存。[源码见证](../output/ninfer-v4-post-k2-selection-20261023/source-witnesses.json)。Baseline、BO、G1及P1—P4证据直接复用，18处G1差异、C1附件缺口、CPU19项原始stdout未保存的披露及全部历史失败保留。

## 为什么选择这一项

1. 真实27B为48个GDN层、Hk16/Hv48、D128；当前MTP3对应W4。`text_context_impl.h:1033–1038`在verify中调用recurrent Record；`program_impl.h:1031–1056`由既有许可确定前缀，再统一Fold。
2. `recurrent.cuh:729–749`显示Record与Fold共用同一递推。`:186–202`中二者均计算`exp(g)`、state与normalized key的点积、delta及状态更新；Fold还重复key归一化。候选有明确的“保存已算结果、避免重算”机制。
3. 当前已经有紧凑raw records与一次all-layer Fold，不能把减少全state快照或“48次Fold降成1次”算作新收益。下一列key预载、Q4/Q5 small-T MMA/split-K、传输descriptor合并/双slot和启动时workspace arena也已存在，不再列为新增改造。
4. 既有Baseline描述中长输出decode占elapsed合计54.17%，Pi HTTP200样本为70.27%，支持关注持续decode，但不能据此确定GDN占比。C0之后缺少restore内联解码/传输分项，不能把602.861ms归因于某个副本，也不再开缓存类HTTP补测。

仓库历史`docs/udp-fork-comparison.md:244–261`记载，两次GDN shuffle优化的aggregate变化约0.1%，并解释为内存受限。这是风险提示，不是当前29的trace。correction不减少原有state流量，更多记录store可能抵消少算的收益；本次选择是可止损的假设筛选。

## 首补丁实施范围

- 在新隔离分支新增内部typed correction布局、Record/Fold候选和有界驱动。保留原raw实现与独立池；候选Record只写correction，raw对照只写raw，不同时双写。若以后产品必须双写，必须重新计入成本，不能继承只写correction的性能结论。
- 在现有helper实际运算点保存FP32 normalized key、实际alpha与delta。保持归约、beta、FMA/舍入和state更新顺序，不复制Flare/KDA的不同数学。key、alpha等记录按head/tile指定唯一writer，避免重复写竞争。
- 两个记录池各自保留conv平面，不做alias或workspace改造。首驱动预置相同conv记录，比较recurrent readout、FP32最终state及conv；复用既有FP64 `gdn_ref`和原阈值，另外要求raw/correction逐bit一致，不能以容差替代。
- 仅C1/W4、48层/Hk16/Hv48/D128。现有`gdn_replay_bench`固定capacity8、state slots11，并分别跑warm/cold/host循环，不能原样执行或沿用其循环计数。新驱动必须使用物理record capacity1并明确state slots。
- 最多16个新增CPU合同场景，完成受影响BO构建、驱动账本和独立集成评审；复用旧suite、Baseline及G1证据，不重跑。原服务、采样/context/Pi medium/32768和缓存/codec格式不变。

本阶段不修改Program许可、epoch、slot、cancel/stop权威，不接真实模型。算子commit0通过不等于Program取消资格；这些由后续K1-T02及独立采用门禁验证。源码重复计算证据足以支持bench原型开发，无需先做完整GPU资格；产品集成仍需真实份额、净收益与运行合同证据。

## 最小验证预算与耗时

以下是**未来提案，不是本轮执行授权**；不叠加旧任务的32wire/84native模板额度。

| 阶段 | 范围与上限 | 预计耗时 |
|---|---|---|
| CPU补丁/参考/BO/评审 | ≤16新增合同场景；受影响目标构建，旧测试只复用 | 6–12工程小时 |
| 有界驱动与冻结 | 新profile、空账本、唯一writer、实际node census及传输计数 | 2–4工程小时 |
| 后续GPU首筛 | 8数值场景、784 direct Op、6 capture、276 replay；0模型/HTTP | 3–8分钟，硬15分钟，第12分钟清理 |

工程准备合计 **8–16小时，约1–2工程日**。物理记录容量为1并不表示削减产品context；算子试验不加载模型，不能替代真实context262144的运行资格。

8个数值场景为normal commit0/1/2/3/4和stress commit0/2/4。commit3覆盖conv通用分支第一个边界；部分场景valid2/3，先检查无效输出清零和未写记录canary，再poison拒绝suffix验证Fold不受影响。stress覆盖近零key、有限非正衰减g和beta∈[0,1]，不制造不符合生产域的正g溢出夹具。

每侧完整算子段为48次Record＋1次all-layer Fold＝49次Op。因此8场景×2版本×49＝**784 direct Op**，不能把49次调用偷算为1次。

计时选commit1/2/4的raw/correction共6配置，各capture一次，每图49个算法kernel节点。每配置2次正确性＋4次warmup＋5批×8次计时，共46次replay；总计 **12＋24＋240＝276 replay**。算法kernel执行上限为`784＋276×49＝14308`；capture记录的294个节点另记，不当作已经执行。

每个配对批次从相同初始state开始，reset在event外，图内按相同顺序滚动递推；raw/correction按AB/BA交错，同时记录完整算子段GPU event和host提交wall，每批核对state/conv。不能只计Fold，也不能把49节点段称为完整Target Verify/整轮：projection/conv Record、attention/MLP、proposal、sampling及host许可不在此图内。

初始化、reset和导出拷贝的次数/字节尚未由驱动枚举，合同保留null及原因；**驱动完成后必须列账并冻结，未闭合不得执行GPU**。禁止隐式计算warmup或reset kernel，实际node数不符即停止。只冻结这次方案，不为提高成绩扩形状或自动重试。

## 收益门槛、资源与停止条件

采用目标是完整Record＋Fold算子段的配对中位耗时降低≥10%，至少4/5批方向一致，同时数值、mask、guard和布局全部通过。目标不是预测；当前GDN份额与整轮/Chat收益均为null。首筛最多获得`SEGMENT_SIGNAL_NOT_K4`，未满足则保持raw并关闭候选。

C1/W4/48层的紧密payload推导：raw约6.8203MiB，correction约9.7852MiB。保守双池新增完整 **9.7852MiB**，合计约16.6055MiB，不是只增2.9648MiB；不含对齐、Graph或其它workspace，也不是实测分配。FP32 state每份144MiB，现有逻辑state流量不会消失。当前模型未加载时的空闲显存不能证明真实context下headroom，不能为多容纳记录而降低context或Pi输出预算。

首筛胜者才考虑K1-T02：真实许可/取消/epoch和Target production sampling route命中、完整round净收益及资源回退。预计另需1–2工程日准备，GPU/model/Graph预算尚未冻结，不在本轮待执行范围。候选资格与生产发布门禁继续分开，`p95=null`、`optimization_qualification=false`。

[完整选择合同](../output/ninfer-v4-post-k2-selection-20261023/selection.json)记录范围、拟议计数、未验证字段与停止条件，[独立评审](../output/ninfer-v4-post-k2-selection-20261023/review.json)未发现剩余选型阻断。V4入口、注册表与K1准入已同步，原文及SHA另存；候选资格模板不等于已完成状态。此轮仅完成关闭、只读核查和选型，产品/构建/测试/GPU/模型/HTTP新增均为0。
