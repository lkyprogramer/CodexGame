# P13 · 同 chunk HC scratch 复用资格验证

结论：**BLOCKED_NUMERICAL_ORACLE，停止在资格阶段；尚无请求性能结论。** HC-only 候选在启动分配时少借601个专家槽，容量方向成立。原版完整配置自身的同 token A/A 不逐 bit 一致，当前跨引擎 oracle 不能可靠归因候选差异。B/C 仅启动核验分配，没有执行候选计算；没有进入正式配对性能、采用或部署。原六项 FAIL 保留。

## 预登记与冻结边界

- [PREREGISTRATION.json](../workspace/combination/hc-scratch-20261028/PREREGISTRATION.json) 于 **2026-10-28 15:03:15.557 UTC** 冻结，SHA256 `9a5b4700db6999fc1d1907531bf06b10fde87d717decaef45e6ed12efe206a01`。首个GPU资格 phase plan 为15:04:57.236，PID启动记录为15:04:57.658；登记在先。
- [STATISTICS_ADDENDUM.json](../workspace/combination/hc-scratch-20261028/STATISTICS_ADDENDUM.json) 于15:11:43补充估计器定义，晚于首对数值A/A、早于任何正式性能测量。没有修改门槛，也不把它写成早于全部GPU诊断。
- 主指标：100K冷读TTFT，6对全新引擎，顺序AC/CA/CA/AC/AC/CA，固定2048输出。改善至少4%，整对log-ratio bootstrap的95% CI下界大于0。完整请求及完整decode的C/A时间比CI上界均须≤1.02；4K和32K→3K append各2对只作筛查。正式预算20个引擎、24个工作请求，**本轮实际正式样本为0**。
- 同P6 v0.2.7 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`，原二进制SHA `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`。保留六文件#1536/PT移植、同IQ3_XXS GSQ-RCO权重、EXACT6、KV int8/resident20480、spec4/minp0.5、15workers+host、CPUSHARE_MAX4096、AUTO_MAX16384、context131072/safety4096及保守026开关。
- 经 `jssh 29` 操作隔离树 `workspace/trees/hc-scratch-20261028`。生产目录只读；没有下载模型、修改系统参数、提交、推送或部署。HTTP #1536/PT行为复用P6证据，本轮只核文件身份，没有重跑HTTP回归。

## 容量结果

最小补丁只移动`xn16/lo/lo16/gated`到原GDN/QSA/MoE共享region。保留`inj/mixed`等跨主体状态、256B分配垫片、历史额外计数、计算kernel、CPUshare、MMQ分组及stream/event顺序。未实现GROUP_SCRATCH或改变chunk。

| 启动分配，T=16384 | A 原布局 | B 复用但保留旧借槽 | C 复用并减少借槽 |
|---|---:|---:|---:|
| 总专家缓存槽 | 10272 | 10272 | 10272 |
| 借槽数 | 4388 | 4388 | 3787 |
| 实际借区cap / bytes | 7,656,345,600 | 7,656,345,600 | 6,618,342,400 |
| bytes_needed | 7,656,100,864 | 7,656,100,864 | 6,618,009,600 |
| carve_used | 7,479,939,840 | 6,441,848,576 | 6,441,848,576 |
| shared region bytes | 3,907,494,912 | 3,907,494,912 | 3,907,494,912 |

四个HC buffer含垫片为 **1,038,091,264 bytes（990.00098 MiB）**，恰等于计数及carve的节省；实际借区减少 **1,038,003,200 bytes（989.91699 MiB）**。共享区仍由MoE集合决定，没有扩大。当前实取`f16_io=0, bf16x2_hc=0, hc_pad=0, fused_layout=0`。

槽位使用native pack的变长`slot_offsets`，不能用601乘一个假定固定粒度反推字节。启动日志与实际Alloc分别证实槽数、字节差；**未完成请求期间保留expert ID、路由命中、H2D及暴露等待的因果链**。B/C各零GEN请求，容量通过不代表其计算路径正确。证据为[ANALYSIS.json](../workspace/combination/hc-scratch-20261028/ANALYSIS.json)及[source loan片段](../workspace/combination/hc-scratch-20261028/source-evidence/generate-loan.cpp.txt)。

## 原版数值 oracle 的阻塞与最小定位

共8次`GEN 1`诊断、另2次仅启动。所有数值请求使用冻结token，不参与性能估计。

| 原P6 fresh-engine A/A | logits值数 | bit不同值数 | max abs差 | argmax |
|---|---:|---:|---:|---|
| 冻结4K请求的4095个token | 248320 | 248320 | 1.401077 | 两次均1596 |
| 冻结100K输入的前16384个token | 248320 | 248320 | 0.544063 | 两次均22956 |

两对均核对同二进制、args、env、token文件SHA/FNV。它们只证明相同配置及输入，不等于已经证明所有执行分派和中间状态相同。argmax相同不构成逐bit通过，也不修复六项任务FAIL。

**执行长度修正**：4095输入的诊断实际batched prefill为4090；原P6的16384输入实际是`88 + 16295`两个prefill段。输入长度不能代替实际chunk，后者仍含CPUshare适用的小块。启动时`carve(T=16384)`也不证明实际计算过完整16384块。本轮没有补做4096精确边界或真实16K计算块覆盖。

关闭HC alias的诊断构建记录层0..8的90个检查点。首39个阶段hash相同，首个记录差异在`p0=0,T=4090,layer=3,half=1,exit:R`。同层驻留映射hash相同，CPU分派为33与54个专家。FNV仅用来定位，没有作为此前所有阶段逐bit相同的证明。

再做一对原布局A，保留同一half的全部有效原始字节：[RAW_AA_COMPARISON.json](../workspace/combination/hc-scratch-20261028/RAW_AA_COMPARISON.json)。代码`layer=3`从0计数。

| 原始字节检查 | 比较范围 | 结果 |
|---|---:|---|
| 进入HC的R | 167,526,400 bytes | 完全相同 |
| HC输出mixed | 41,881,600 bytes | 完全相同 |
| HC输出inj | 65,440 bytes | 完全相同 |
| HC输出lo16 | 2,617,600 bytes | 完全相同 |
| FFN主体结束后的R | 41,881,600个float | 3,340,590个bit模式不同；max abs `4.424527287483215e-5` |

这对运行在该层分给CPU的专家数为49与53，share为0.146475与0.156323。源码在上一共享层完成后用实测CPU/GPU时间更新`cpu_share_now=g/(c+g)`，再决定`take`和`on_cpu`。差异边界与动态CPU/GPU分派变化吻合，支持其为当前A/A不稳的直接候选解释；尚未通过固定dispatch的干预排除FFN内部其他来源，不能称唯一根因。同步readback会扰动计时，因此诊断运行的CPU比例和耗时不能代表未插桩生产分布。

这些运行全部关闭HC alias，不能将既有差异归因于新复用，也尚未证明新复用数值等价。下一项最小工作应是**捕获相同实际输入、状态及CPU/GPU分派的数值回放oracle**，先区分纯地址复用，再单独验证自然回收槽位的C路径。不得关闭原CPUSHARE或放宽容差换取PASS。

## 完成边界与复现

- PASS：P6身份、最小补丁静态独立审查、CUDA12.3/sm89隔离构建、A/B/C启动分配、原版A/A及首差异字节诊断。`PASS`仅指这些检查完成，数值门状态仍为BLOCKED。
- 本机8项定向工具测试PASS；所有P13 Python AST通过；根仓库`pnpm typecheck / lint / test / test:integration / build`均exit0，保留既有Phaser chunk警告。独立审查没有重跑模型。
- **NOT_RUN**：B/C候选计算逐bit、KV/GDN/PLE有效状态对照、redzone/poison、compute-sanitizer、候选短→长→短/恢复/取消生命周期、实际保留专家成本链、有效频率、正式配对TTFT/全请求/decode、任务质量及采用验证。没有因A/A失败跳过这些门去测速度。
- 第一次收尾工具将成功返回`None`的`port_free()`误当布尔false，造成假资源占用错误；修正调用后重新检查，保留`FINALIZE_ATTEMPT_1.json`。没有改变实验数据或资源门槛。
- 13个生产保护hash、P6源码/二进制及1,466份旧证据hash不变；10个拥有的引擎PID退出，GPU为1MiB/45°C且无计算进程，18089可绑定，生产为inactive/dead/enabled。405个资源样本无abort，最高62°C、最低MemAvailable11322MiB。见[FINAL_PROTECTION.json](../workspace/combination/hc-scratch-20261028/FINAL_PROTECTION.json)。诊断源码、补丁和二进制身份均保留；隔离树已还原HC-only源码/二进制，默认开关关闭。

核心复现入口（在29实验包内使用现有venv Python，重新运行须新phase名）：

```bash
python -B tools/hc_scratch/qualify.py --variant P6 --name NEW_AA_PHASE --case think-4096
python -B tools/hc_scratch/analyze.py workspace/combination/hc-scratch-20261028 --output /tmp/p13-analysis.json
python -B tools/hc_scratch/compare_raw.py workspace/combination/hc-scratch-20261028 --output /tmp/p13-raw-recheck.json
```

`prepare.py`只允许首次登记；已有目录会拒绝覆盖。诊断phase须使用对应已归档诊断构建，当前还原后的HC-only二进制不包含阶段dump钩子。

归档：29的`RAW_MANIFEST.json`登记187文件、783,570,499 bytes；其中177份日志、输入、源码、比较结果和清单（24,335,619 bytes）已本地/29双端SHA校验。10份原始阶段dump共759,234,880 bytes完整保留在29，已在29逐字节比较和计算SHA；因jssh大文件同步慢，中止本地全量传输，校验不匹配的本轮局部文件已删除，**不声称这10份dump完成双端校验**。可执行文件也留在29的`binaries/`，身份另见`BINARY_ARCHIVE.json`。完整范围见本地[ARCHIVE_RECEIPT.json](../workspace/combination/hc-scratch-20261028/ARCHIVE_RECEIPT.json)。实验包固定MANIFEST保留旧237成员并新增10项，共247项通过校验。
