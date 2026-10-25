> TECHNICAL_REFERENCE_ONLY：以下固定源码/计算/旧论证保留，原先的“当前”时态或阶段要求不再调度任务。当前身份见[证据](../research/05-completed-baseline-and-current-state.md)，执行以[根注册表](../plans/02-task-registry.md)为准。原始字节另保存在本轮403份快照。

# 27B记录成本、状态流量与收益边界

状态：**DERIVED**。按N01/N02已读维度计算，不是cudaMalloc计数或Nsight实测。使用48个GDN层、Hk=16、Hv=48、D=128、conv_channels=10240；不把Flare Flash的36个GDN层和hidden2560代入本目标。

## 每个layer × record-row × verify-column

| 记录plane | 原始raw | correction方案 |
|---|---:|---:|
| conv，BF16 | 20,480 B | 20,480 B |
| key | BF16 4,096 B | FP32 normalized 8,192 B |
| value / delta | BF16 v 12,288 B | FP32 delta 24,576 B |
| gate / decay | FP32 g,beta 384 B | FP32 alpha 192 B |
| 合计 | **37,248 B** | **53,440 B** |

净增16,192 B，即约43.47%。这里按完整conv保留，不把别的路径负责的卷积状态删除掉。

## 紧密payload的MiB（不含对齐、Graph、descriptor、其他workspace）

| C=record rows | W | raw MiB | correction MiB | 若可互斥共用，净增MiB | 若保守双池共存，合计MiB |
|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 6.8203 | 9.7852 | 2.9648 | 16.6055 |
| 1 | 6 | 10.2305 | 14.6777 | 4.4473 | 24.9082 |
| 4 | 6 | 40.9219 | 58.7109 | 17.7891 | 99.6328 |
| 1 | 8 | 13.6406 | 19.5703 | 5.9297 | 33.2109 |
| 4 | 8 | 54.5625 | 78.2812 | 23.7188 | 132.8438 |
| 1 | 16 | 27.2812 | 39.1406 | 11.8594 | 66.4219 |
| 4 | 16 | 109.1250 | 156.5625 | 47.4375 | 265.6875 |
| 8 | 16 | 218.2500 | 313.1250 | 94.8750 | 531.3750 |

K1初版可保守使用独立raw/correction backing，新增预算是**完整correction payload**，不是表中的净增。K3证明两套records不会同时活跃后才可用同一字节arena的不同typed视图，容量取最大值。生产必须同时保留raw fallback；不允许因省掉fallback导致非合格请求失效。

W8/W16为后续形状的容量推导，不是本次确认完整engine已支持；首轮拟资格产品仅C1/W4 production sampling，其余实际P6支持形状逐项资格。C/W是物理record容量，不是当前active数，也不是用户并发乘各自262K上下文。

## 原state R/W并不会消失

单层FP32 state为48×128×128×4 = 3 MiB；48层共144 MiB/row。原始ReplaySSM已经避免每个候选token写整份state。若按一次verify读state、一次fold读写state粗计，两条路线都约有432 MiB/row的逻辑state traffic，不能再宣称从W次state写回降到一次。实际DRAM bytes可能受cache、重复加载、并行安排影响，必须用profiler测。

correction主要省fold内的key normalization、exp以及`S·k`和delta重算。归一化/exp本来就可能很小；state带宽若主导，新增记录可能抵消收益。重点测**verify+fold总时间**而不是只测fold。

## B/W目录而非独立max乘积

示例：仅有(C=8,W=6)、(C=1,W=16)两种graph时，最大物理行数是48而非128。这只是示意；应从实际Program导出captured/eligible目录计算每个资源，不能自行假设所有资源都只按C×W缩放。Attention scratch还受KV深度、splits、head、dtype影响，all-layer records受层数与物理row布局影响。

## 主机及GPU整机预算

沿用H0账本并增加记录编码、shared-memory/CTA、register/thread、local spills、tuning表、Graph变体数和双流workspace。GPU硬预算由实际free bytes和P6 headroom确定；不沿用旧README的1.37GiB当当前余量。主机64GB是整机RAM，需扣除L2、OS、源码构建、模型映射、pinned buffers；不得把pinned host当免费显存。

[来源锁](00-source-lock.md) · [设计](../design/01-gdn-correction-records.md)

## 以实际线上形状和尾轮约束解释成本

现网C1/MTP3对应首轮W4：raw6.8203MiB、correction9.7852MiB，保守双池新增完整9.7852MiB。C4/W6的58.7109MiB新增是推导场景，不能当当前实际分配。payload不包括alignment、Graph和其它workspace，不能用其差额声称整机显存下降。容量采用profile要求同context/功能下实测固定占用释放≥64MiB并且延迟不退化，与延迟收益profile分别冻结。

B29存在尾轮剩余1/2token的context_capacity与KV增长被截停；未证OOM，也未定位页ceiling/池压力/保守整窗headroom原因。新增池或扩宽前先记录实际source/build、remaining、frontier、main/aux entitlement与free pages；不削减Pi32768输出、不把历史请求重发。当前没有allocator高水位，必须null+原因；计算payload不能补填实测字段。

K0需测完整verify+fold与round wall，fold即使自身快一倍也受Amdahl限制；新增store、register/spill、Graph目录和alignment都可能让净收益为负。详见[Baseline](05-completed-baseline-and-current-state.md)及[验证预算](../plans/08-validation-budget-and-estimate.md)。
