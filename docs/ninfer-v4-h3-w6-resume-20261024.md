# W6/K5 接续实验：平均收益与稳定性边界

2026-10-24。**W6/K5 接续实机已完成：数值／Graph及状态一致性通过；两条短样本的完整轮单位token耗时分别下降22.75%和20.38%，但Java后半段反向增加13.75%，未通过冻结的稳定性首筛门槛。** 按既定规则，本固定W6实验收尾，不追加Chat、扫K或W8验证。默认分派未改，原GPU服务保持停止。

本次有可观测的短样本平均净收益，不能称“完全无收益”；也不能将平均值宣称为稳定业务或生产提升。r1夹具错误、修复、用户增量授权、r2成功结果分别保存，没有覆盖或退回失败成本。

## 实现与测量合同

从原 H3 树 `49bee647112ee171de35529028fc271494260751` 继续。产品 `src/`、`include/`、`apps/` 未修改，默认 serve 二进制复用；默认分派、Target 采样、Pi medium／32768 不变。变更限于 bench 的实验模式入口、`tests/h3_w6` 驱动／工具和 `tests/k2_full/audit.cpp` 的 allocation 计数。新增头文件仅由实验目标的私有宏启用。

自然路径使用 C1、W4/K3 对 W6/K5、262144 context／KV、rk4v4、1024 prefill chunk。每个请求保持 32768 输出预算；每轮传入 `32768 - 已正式提交 token 数` 的真实剩余额度，包含 prefill 生成的首 token，不以轮数或 K+1 替代请求预算。使用自然 proposal，不注入 Oracle；复用既有 `OutputSession` 的 preview／resolve／commit 和取消终态。

四个自然请求为两个新 prompt 的 W4/W6 配对，每侧最多 2 warmup＋16 计时轮。记录 actual accepted、licensed、committed token、输入位置、fallback 和终态。主指标为 `sum(计时轮完整 wall) / sum(计时轮正式 committed token)`；保留 CUDA event 时间和 Program aggregate decode 时间。计时覆盖 `decode_batch → output preview → resolve_pending_batch → commit_preview`，并等待 GPU 完成；持久化 journal、发布字符串累积及诊断取消在轮外。它不等于 HTTP 或完整请求延迟。

阶段归因仍为 `stage_attribution_complete=false`、`stage_timings_seconds=null`。原因：现有 Program 只公开 aggregate decode 记账，未公开 Target verify／MTP draft 独立时间；本轮未向被测路径插入阶段同步。不能将 null 当作阶段成本为零或声称已完成阶段归因。[实现及评审记录](../output/ninfer-v4-h3-w6-resume-20261024/evidence/review-summary.json)

## 已执行的非 GPU 验证

- BO r1：在固定镜像、`runc`、无网络、无 NVIDIA 设备的容器中，构建 `ninfer_h3_numeric_chain`、`ninfer_h3_w6_native`、`ninfer_h3_w6_natural`，exit 0。[命令与回执](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/evidence/BO-r1.json)
- CPU：6 个唯一合同最终通过，共执行 7 次。首次 case3 因环境存在 NVIDIA 设备触发 `CPU-only freeze requires no NVIDIA devices`，保留失败；仅将 case3 移到 BO 无 GPU 容器复跑，没有放宽 guard，也没有重复已通过用例。这是 CPU 合同通过，不是数值／GPU 通过。[CPU6 汇总](../output/ninfer-v4-h3-w6-resume-20261024/evidence/CPU6-summary.json)
- r1 独立源码评审未报告剩余阻塞；allocation 额度缺口已补计数和入场检查。评审者没有运行测试。该评审仍漏掉后续实机暴露的 Fold 层数约束，不能作为 GPU 正确性证明。[评审汇总](../output/ninfer-v4-h3-w6-resume-20261024/evidence/review-summary.json)

## r1 失败、成本与保全

r1 冻结 SHA 为 `20bc78f3dda59e84c1adb95e34bcbd8d65b6c1fa079b95bb41953fdb9fb6d6cc`。数值链使用 `layers=1`，而 Fold 仅注册 48／30 层几何，故报 `gdn_replay_fold: unsupported record geometry`。这是驱动夹具错误，尚不能判断 W6 状态资格或性能。[失败摘要](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/prepared-window-r1/runtime/numeric-chain/numeric-summary.json)

r1 尝试 3 个语义 Op，前 2 个完成；Fold 在 host 校验失败，没有启动 Fold kernel。失败 audit 记录实际 3 algorithm／direct kernels、0 capture、0 replay；H2D 为 9 次／55,781,636 B，memset 为 16 次／1,037,056 B，cudaMalloc 为 15 次／56,278,021 B。native、decode、Chat、HTTP、wire 均未进入。[原始失败 audit](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/prepared-window-r1/runtime/numeric-chain/audit.json)

原账本仍保留 `numeric-chain: RESERVED`，没有清零、退回或重放。账本的 `GPU_actual_completed=0` 只表示没有完成可结算的阶段，不能解释为 GPU 零消耗；实际失败成本以上述 audit 为准。r1 原始目录已完整归档，302,811,625 B，SHA `d8ad9b1def9a4106e432cfa6c9b832cbd1fb306c87c625da87f544e3544cbdf5`。[归档回执](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/evidence/r1-failure-archive-receipt.json)

r1 终态读回显示候选已停止／无活动候选，GPU compute 为空，原服务 exited／PID0 且身份不变，GPU lease 可取得。该结论对应 r1 的 2026-10-24 13:09:37 UTC 快照，不替代 r2 最终清理证明。[清理回执](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/prepared-window-r1/runtime/cleanup.json) · [独立终态读回](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/evidence/r1-failure-drain.json)

## r2 修复、冻结与批准预算

r2 只修复 `tests/h3_w6/numeric_chain.cpp` 的夹具。使用注册的 48 层 state／record，保留 layer0 输入、FP64 oracle、bitwise／guard 断言；其余 47 层明确初始化为惰性零状态并完整读回检查。合法零 workspace 查询仍分配最小 1 B。没有扩大 Op 的注册几何或放宽数值标准。[修复差异](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/repair-r2/evidence/repair-only.patch)

BO r2 仅重建受影响的 `ninfer_h3_numeric_chain` 并运行 `--plan-only`，exit 0；实际计划回读为 layers48／active1／inert47，3 direct Op、1 capture／2 replay。原 native／performance 二进制及 r1 源码、冻结、账本不变。[BO r2 回执](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/repair-r2/evidence/BO-r2.json) 独立源码复审核对注册几何、惰性递推、全层检查和预算后未报告新阻塞；未运行测试，GPU 实际结果见下节。[r2 评审](../output/ninfer-v4-h3-w6-resume-20261024/repair-r2/evidence/review-summary.json)

r2 source tree 为 `a728df11f92360108a3f12bb619137dafe4eed3d`；新冻结目录为 `/home/hhtele/ninfer-v4-h3-w6-resume-20261024/prepared-window-r2`，freeze SHA 为 `273b37f4ec71945d3cd0865886d0c23db2ddefdd77bfa7ce66d7ab5409904679`。[源码与二进制身份](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/prepared-window-r2/source-identity.json) · [准备回执](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/repair-r2/evidence/preparation-receipt.json)

用户增量授权覆盖新增 3 次 direct Op 尝试；r1＋r2 两窗口合计最多 6 次尝试，旧成本不退回。数值链 D2H 字节上限由 64 MiB、memset 字节上限由 8 MiB 分别提高到 512 MiB，其余原计数上限保留。源码推导的成功路径预计 D2H 505,855,488 B、memset 496,039,168 B、cudaMalloc 累计请求 217,518,853 B／15 次，为冻结前推导，最终数值链 audit 与这三个值完全一致。[完整增量与累计预算](../output/ninfer-v4-h3-w6-resume-20261024/repair-r2/evidence/numeric-resource-budget.json)

剩余模型额度仍为 **8 native／最多 81 decode，0 Chat／HTTP／wire**：旧状态诊断 4 请求／9 decode，四个自然请求最多 72 decode。硬限 1200 秒，第 1020 秒进入清理；不追加 warmup 请求，不重试提前 EOS／失败请求。r2 全局冻结包含 capture55／replay137、algorithm kernels1,204,272；完整 16 类计数以冻结为准。[冻结资源上限](../output/ninfer-v4-h3-w6-resume-20261024/remote-evidence/prepared-window-r2/freeze-receipt.json)

cudaMalloc 计数是项目发起的累计请求字节／次数，入场前预留，失败不退款；**不是实时存活内存或 allocator 高水位**。高水位仍为 null，驱动／库内部 allocation 未被该计数完整观测。r1＋r2 的累计也不能宣称覆盖更早原 H3 缺失 failure audit 的历史总量。

## 完整实机结果与解释

窗口从2026-10-24 13:17:09 UTC（北京时间21:17:09）开始，运行 **297.884秒，约4分58秒** 后完成清理，未触及第17分钟清理阈值。8个native请求／81次decode全部完成，0 HTTP／wire；没有提前EOS或自动重试。4个自然请求均在18轮诊断上限走许可取消，不能称为完整答案质量验收。请求和有效输出预算仍为32768。

- 完整链：1个场景、3 direct Op、1 capture／2 replay通过；layer0独立参考、输出guards、Graph逐bit、其余47层状态／记录不污染全部通过。
- 状态资格：4请求／9 decode通过，完整提交和部分提交的正式前缀与持久状态均逐bit一致；完整提交还比较next MTP。旧6个数值／Graph PASS没有重跑。
- 自然性能：两个新prompt，每题W4/W6各1请求、每侧2warmup＋16计时轮。使用所有计时轮，不剔除末段或不利数据。

| 新prompt | W4 ms/正式token | W6 ms/正式token | 整段耗时下降 | 前8轮下降 | 后8轮下降 | 冻结首筛 |
|---|---:|---:|---:|---:|---:|---|
| Java | 7.7943 | 6.0214 | 22.75% | 48.20% | −13.75% | 未通过 |
| 中文推理 | 6.0908 | 4.8497 | 20.38% | 15.93% | 24.08% | 通过 |

下降是 `1 - (W6总wall/W6正式token)/(W4总wall/W4正式token)`，**不是吞吐增加百分比**。冻结要求两题各降至少10%，且各自前后半段方向一致；整体`pilot_signal=false`，不能事后取消半段要求。

| 新prompt | W4平均整轮ms | W6平均整轮ms | W4正式token/轮 | W6正式token/轮 |
|---|---:|---:|---:|---:|
| Java | 23.3830 | 25.5908 | 3.0000 | 4.2500 |
| 中文推理 | 23.2213 | 25.4608 | 3.8125 | 5.2500 |

**收益来自更多正式产出摊薄每轮成本，W6单轮本身慢约9.4%～9.6%。** Java前半段token/轮为2.375→5.0，后半段为3.625→3.5；后半段已失去产出优势，而整轮仍慢约9.8%，因此单位token耗时反向增加。两个Java半段的整轮时间变化很小，数据首先指向接受／正式产出沿生成路径的变化；这不是“GPU突然变慢”的证据。两种宽度即使seed相同，也可能生成不同文本，不能把相同轮号当作相同token路径。本轮不据此推导长期分布或提出自动宽度策略。

[原始逐轮结果与自动汇总](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/prepared-window-r2/runtime/summary.json) · [独立离线复算](../output/ninfer-v4-h3-w6-resume-20261024/evidence/final-independent-metrics.json) · [完整数值结果](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/prepared-window-r2/runtime/numeric-chain/numeric-summary.json) · [状态逐bit比较](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/prepared-window-r2/runtime/native-w6/comparison.json)。

## 实际资源、证据和清理

r2实际 **55 capture、88 replay、95,027算法kernel**；所有16类计数均在冻结上限内。r1＋r2合计95,030算法kernel，语义direct Op尝试共6次（r1两次完成、一次Fold入场拒绝；r2三次完成）。这些累计仅覆盖本轮两个窗口，不能补齐更早原H3缺失的failure audit。

r2显式cudaMalloc累计请求116,536,932,357字节／30次，包含五个模型进程的不同生命周期，**不是同一时刻占用116GB**；失败r1再加56,278,021字节／15次。原始分配、传输、memset及全部累计值见[最终核验](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/repair-r2/evidence/final-verification.json)。

六个候选容器均退出，控制器／guardian结束、GPU compute为空；原服务镜像、argv和cache目录身份保持，服务仍停止。旧r1 freeze和ledger SHA未变，修复r2源树与冻结树一致，未留下未知模型请求。[原始清理回执](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/prepared-window-r2/runtime/cleanup.json)

完整失败原件（含二进制）留在远端`/home/hhtele/ninfer-v4-h3-w6-resume-20261024/evidence/r1-failure-original.tar.gz`。本机下载并SHA校验了小型原始日志／账本／回执归档；取消了耗时的大二进制重复下载并删除本轮临时残片，没有将部分文件当作完整备份。r2全部raw state／verify二进制及可执行文件继续保留在远端`prepared-window-r2`；本机保存全部JSON、journal、stdout/stderr和完整[附件SHA清单](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/repair-r2/evidence/final-attachment-manifest.json)，不声称大附件已全部复制到本机。[传输说明](../output/ninfer-v4-h3-w6-resume-20261024/evidence/evidence-transfer-receipt.json)

最终元数据归档SHA：`b4ae72a07962962569de34aaa8fa84ee71f923253ca79bda0c63e39c089b9fbb`。原始状态payload由controller在比较前核验bytes/SHA，最终收集再次计算全部附件hash。

## 结论边界与停止状态

本轮证明既有W6路径在当前小范围数值／Graph／许可状态合同下可运行，也观察到两个短样本的平均完整decode净收益；它没有证明长期稳定收益、HTTP／TTFT改善、质量或生产发布资格。两个prompt、每题一个seed、16个相关计时轮，且输出路径不同：Java从第10个生成token、中文从第7个开始分歧（计数含prefill首token）。guardian保留了[约5秒间隔GPU遥测](../output/ninfer-v4-h3-w6-resume-20261024/final-remote-evidence/prepared-window-r2/runtime/gpu-telemetry.jsonl)，但每个计时块约0.4秒，没有逐轮时钟／温度见证。

原六项数值／Graph PASS复用；全部失败、18处G1差异、C1和Baseline附件缺口保留。`p95=null`、`optimization_qualification=false`；Target/MTP分段时间与allocator高水位继续null及原因。采样、Pi输出预算、默认分派和原服务状态不变。

状态为`CLOSED_FIXED_W6_PILOT_STABILITY_GATE_NOT_MET`。追加请求预算0，不自动发Chat、不扫K、不开发W8，也不恢复已经关闭的其他实验。修复版补丁、最小驱动及全部原始结果保留，后续若有新的研究目标需单独定义。
