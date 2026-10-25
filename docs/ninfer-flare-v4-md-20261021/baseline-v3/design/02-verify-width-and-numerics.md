# W6 → W8 → W16：完整形状闭合与数值资格

## 不等价的三个参数

神经草稿上限N、外部候选K、逻辑有效Target列V=K+1、物理Target宽度W≥V分开。现有MTP最多5草稿，已有GQA小T路径1..6；它们不是同一个限制。V3保留旧MTP AR上限，不通过把全局max从5改15强迫MTP预测15步。

H3新增物理W8/最多K7，H4条件性新增物理W16/最多K15。W1/4/5/6保留原路径；K1/2分别用V2/3+物理W4，映射与budget1/2见design/00。输出budget接近尾部时先截逻辑K并选合法物理shape，padding的计算/内存仍计账，不将V2/3当作未实现W2/3。

## Shape closure 清单

| 层面 | 必须核查的实体 | 失败方式 |
|---|---|---|
| public/startup | policy widths、variant capability、上下文和并发 | flag接受了但没有kernel |
| Frame | ids/drafts/positions/logits/hidden/valid_columns | 只扩大tokens，没有扩大hidden/logits |
| ReplaySSM | width、record_capacity、层数、g/beta、conv/key/value | 多lane alias、未接受状态进入commit |
| KV | main/backend page entitlement、scratch append/frontier | 拒绝后逻辑可见范围未回退 |
| Ops | projection/GQA/GDN/scatter/accept/MTP alignment | GQA支持了，但alignment仍最大6 |
| Graph | W/B/context envelope/codec/workspace/pointers | W8调到W16图、padding仍付大图成本 |
| Continuation | snapshot format、ready frontiers、proposal身份 | 旧缓存恢复出不一致MTP状态 |
| Serving | cancel、stop、output budget、fault作用域 | 末尾bonus多发布一次 |

NInfer现有small-T row-split MMA可能已覆盖部分更大T，但**路径可编译不表示完整链正确**。H0输出每个真实符号的shape map；NI05列出实际实现文件，避免凭模板猜路径。

## 物理行单位

若同构子batch实际B行、每行W列，物理token行至少B×W（有padding时按paddingB）；workspace不得只按B或sum有效token分配。split partials按实际Q heads、split容量、dtype和物理列推导。CPU属性测试包含 `[16,1]` 与 `[17]` 的区别：前者是可分组的17token batch，后者是非法单请求W17，不能混成同一拒绝理由。[HQ05]

测试scratch先填NaN/guard bytes，验证所有读取前均写入；未参与的padding不得污染有效行。单模型多层可能复用workspace，不把每层的共享暂存重复乘层数；ReplaySSM逐层保留的记录则要乘层数。

## 数值资格不是“Target都会纠正”

Target logits本身会随归约顺序、量化、GDN chunk、batch packing变化。HQ02的Sticky多请求反例、HQ05的编译谱系现象明确表明：不能用相同网络结构保证任意路径逐token相同。

分四层验收：

- **L0整数/布局**：token、positions、许可数、页/record地址必须精确。
- **L1算子数值**：沿用已有独立oracle与容差；对新shape增加边界。不能用候选输出重新生成expected。
- **L2同形状路径**：eager/graph、replay/direct、连续运行同输入比较；padding不改变有效请求。
- **L3 Target-greedy诊断**：同Targetartifact、同KV/停止/采样、同真实输入，普通解码与候选route完整token序列一致；W切换、lane变化均覆盖。发现差异必须定位第一处分叉，不以“近似tie”放宽greedy声明。

不得扩大原P0—P6中所有冷/热算术的承诺：旧工程已说明某些不同prefill切分可能存在合法数值差异。新lossless资格在**冻结同一prefill起始状态**下隔离verify/commit变化，再独立跑冷/热业务质量。若为了exactness改变普通路径，需要作为新Target计算配置重新冻结和披露，不能偷换baseline。

W16若不获益或无法在现有数值契约内合格，保持feature off/移除未资格产物。不能为了过门槛降低GDN到fp16、修改Target权重或删除严测。

## B29实际容量与padding不能混用

当前baseline不扩宽；其源码容量合同见 [plans/05](../plans/05-baseline-29-execution.md)：O_eff=min(O,C−P+1)，文本ceiling=P+max(O_eff−1,0)，末采样token不再写入KV；初始4096输出window后动态growth，MTP backend clamp到C。未来宽verify仍应分别验证逻辑有效位置/页frontier和物理W/Bscratch，不将padding列算成已许可KV，也不因W额外臆造固定R。P>C输入拒绝与O过大ContextCapacity提前结束是不同边界，不能混成通用400。

## Target sampling另证分布与每列processor

L0–L3保留但L3是Target-greedy数值诊断，不把它的同token声明扩到生产sampling。新路径目标是确定性草稿、保持原Target sampling；按 [design/11](11-sampling-acceptance-and-proposal.md)验证delta-q、最终mixed prefix的p/count overlay、fractional接受/残差/bonus、stop/commit及RNG。相同合格路径seed/state重复性与跨普通/spec路径的分布等价分开，不能要求跨路径同seed token必一致。W8/W16、padding、分组/动态width每个声明组合需真实sampling资格；未通过继续OFF并保留原sampling路径。性能筛选按plans/06相关小集，不逐shape重复全部672，但硬数值/状态边界不省略。
