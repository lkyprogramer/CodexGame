# 投资顺序、显存账与真实收益计算

## 1. 为什么Suffix先行不是宣称Suffix一定最快

现网已加载MTP，Suffix首版只增加CPU索引和合法共享verify接线。它的问题更小：本机真实rewrite/Java流量是否存在可利用的重复，以及MTP状态bridge成本是否抵消收益。即使失败，也无需处理新五层模型的converter、selector和localring。

DFlash2仍是独立主要研发方向，可与Suffix的CPU测试并行设计。GPU实验串行。Suffix没有优势不构成停止DFlash2的理由；DFlash2 AL偏低也不否定d256prefill的研究价值。不要把路线图写成“所有阶段必须乘起来”。

## 2. 阶段性退出点

| 阶段 | 最小可回答的问题 | 可接受的结束结果 |
|---|---|---|
| 事实/控制组 | 实际baseline同medium、同题、同测量器是多少？rk8@200192与DFlash2争同一块显存，选哪个？ | 新鲜比较报告 + 二选一决策，不写GPU代码 |
| W8路径门（T07） | W7/W8合法decode attention路径在184K的每轮额外耗时`Δ_w8`是多少？ | 数字进`22 §4.1`停止公式；不过门则DFlash2降为可行性研究 |
| Suffix链延长v1 | 在MTP的3个草稿之后延长到W≤6，命中率与净收益如何？ | 默认off、场景限定，或实测NO_GO；命中率足够才做v2 bridge |
| DFlash K3/W4诊断 | 5层/selector/q/frontier在本目标是否正确？ | 数值/状态通过，不报生产胜出 |
| DFlash W8 @200192 | same-target每轮耗时和AL是否更好，会话持久化是否等价MTP？ | 一小时筛选候选或明确失败 |
| W16 | 减少round数量能否抵消更贵的verify？ | 只对copy/rewrite启用，或放弃 |
| d256prefill | baseline实际attention占比与新kernel速度，能否降低冷TTFT？ | 独立prefillprofile，不与proposal速度混账 |
| A4 | target近似带来的质量损失是否值得？ | 默认关闭；质量无充分证据就不发布 |

每个热点最多5个有单一假设的candidate小迭代，然后重新评估是否继续。昂贵分支只在前一可行性门通过后启动；不是为达到预设“极致”分数而无限调参。

## 3. 资源账必须按component和stage记录

启动前由loader plan输出：

```text
target always-resident weight tensors
selected proposal-head tensors
selected MTP OR selected DFlash2 weight tensors
vision tensors (capability与生产一致，不偷偷关闭一个已有能力)
main Attention KV capacity / bytes per physical page
GDN StateImage count / bytes
DFlash2 ring count × 40MiB (when selected)
pending feature buffers / ReplaySSM records
prefill / verify / graph-capture transient peaks
allocator alignment, reserved headroom, driver overhead
```

每个tensor只能计入一次。embedding/head共享按真实alias处理；“文件存在”不代表它materialize。DFlash2启动不加载MTP能节省多少，只能从44a改后分配计划得出，不能把MTP `.ninfer`节的全部diskbytes直接当节省。

显存账独立于RAM账。host suffix预算、L2 8GiB、GDN checkpoints、模型mmap页缓存、编译进程都计入62.5GiB实际RAM，不把“free缓存可回收”误判为硬OOM。PCIe Gen3上的restore wall需包含序列化/重定位/同步，而不只bytes÷12GB/s。

候选必须达到受保护**200192**容量（`tools/metrics.py::PROTECTED_CAPACITY`，用户2026-09-09决策）并有至少512MiB实测最差峰值余量；更高1GiB余量为偏好，不是通过不可能的承诺。实例总窗口是input+output+runtime必要lookahead，不是允许200192输入再无限输出。生产仍是262144，候选能否装下262144只作事实记录。

**初始账（2026-09-09按artifact目录+上游inventory+`nvidia-smi`算出；T08 loader plan实测确认）**：

| 项 | MiB |
|---|---:|
| 现网free（total 24564，`ninfer-serve` 22592，驱动保留≈463） | 1509 |
| DFlash2 companion常驻（66对象逐项：fc 0.130 + 5层×0.341 + selector 0.237 GiB） | +2124 |
| 不加载MTP | −430 |
| 40MiB local ring | +40 |
| W8 verify/pending/graph/draft attention工作区（估） | +50…150 |
| **262144下余量** | **−225…−325（不成立）** |
| 200192释放（61952 token × 26.4KB/token） | +1597 |
| **200192下余量** | **≈1222…1322** |

rk8v4比rk4v4每token多≈8KiB → 200192下≈1564MiB，正好吃掉释放量，所以rk8与DFlash2 W8**互斥**。`vision` 0.275GiB不可拿来省（`vision:false`，很可能本就未materialize）；L1 6144MiB不是独立池（共享KV pool），不构成杠杆。

## 4. 有界估算（本机代入，推断）

下面不是承诺，是给每条线一个可否决的数量级与停止点；每个数字都可由`22 §2`的实测值和公式复算。

| 线 | 公式与代入 | 结果 | 停止点 |
|---|---|---|---|
| DFlash2固定成本 | draft权重2.07GiB ÷ ~900GB/s ≈2.3ms；减MTP 0.42GiB≈0.5ms | **+≈2ms/轮** | — |
| 现网轮时 | 184K：98.5t/s ÷ AL≈2.9 ≈34轮/s → 29ms；4K：127.1÷2.9 → 23ms | 打平需committed/轮 **+7%/+9%** | — |
| 同K换drafter | 模型卡AL +8.8–20.1% | 净 **0–12%**，接近噪声 | 不以同K结果推进 |
| K=7宽度 | 4-bit KV下W4→W8 verify读字节≈不变（4.9GB/轮@184K） | 收益来源；代价在draft/head计算与W8路径`Δ_w8` | T07测`Δ_w8`；`AL_K7/AL_K3−1`下界不能覆盖`(2ms+Δ_w8)/29ms`则不进T09 |
| d256 prefill | fork自测GQA prefill attention在混合天花板的41%；Amdahl `1/((1−f)+f/s)` | f=0.45、s=1.6 → **≈1.20×**，184K TTFT 94s→~78s（不是vLLM的66s） | 先用nsys测f；f<0.3则不投 |
| Suffix链延长v1 | 命中时每轮多≤2个候选，未命中与现网相同 | 上限W=6；copy类拿不到W16的3–4× | 命中率与净收益不足则保留off，不做v2 |

一个反例：AL 4.0/40ms（100tok/s）比AL 3.5/27ms（129.6tok/s）慢——接受更多却更慢。若候选为此破坏缓存导致每个tool回合多等5秒，它仍可能输实际Agent任务。量化、转换和workspace新开销会继续降低收益；基于旧阶段占比计算后，融合候选必须重新profile。

## 5. no-spec对照不能与MTP生产排名混淆

新增kernel的no-spec对照用于隔离执行路径；生产候选必须与MTP3/E8/medium比较。换precision、context、thinking、warm状态、输出长度、promptreuse任何一项都应生成新的profileID。

copy/query生成必须单列；重复输出或EOS被禁导致的高AL不计作真实质量收益。每request同时保存finish_reason、实际输出token数、task成功、重试次数；不能只保留最快成功样本。

## 6. 容量/质量/速度不能一次证明

本包分三条证据：

1. 实际近258K检索+输出headroom，证明选定profile资源与长状态可运行；
2. 4K/64K/184K自然任务持续输出，证明真实decode和prefill；
3. 原Java题、30语义题、真实长期Pi轨迹以及target近似所需的更大holdout，证明可用性。

任一条缺失，结果就只能描述已覆盖维度。尤其不能用一个needle通过代表整个200K代码库理解能力等价。
