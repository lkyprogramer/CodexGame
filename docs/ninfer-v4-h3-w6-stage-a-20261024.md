# H3-T01 Stage A：现有W6最小驱动、BO与CPU准备完成

**隔离分支已完成C1/W6/K5最小驱动、默认/诊断BO构建、16个具名CPU合同与两路集成评审，并冻结新工具和全零账本。GPU/模型/HTTP请求均为0，原GPU服务保持停止。** 没有开发W8，也没有修改默认分派、Target采样、Pi medium/32768或缓存格式。真实W6数值、Graph、状态与性能仍未运行，不能宣称加速或候选资格通过。

## 身份与冻结入口

| 项目 | 当前值 |
|---|---|
| 连接 | `jssh 29`，实际`ssh -J jump 29` |
| 隔离根 | `/home/hhtele/ninfer-v4-h3-w6-20261024` |
| 分支 | `codex/h3-w6-existing-route-20261024` |
| raw基点 | `a5ba33de12d75ab1e16a153020e4068094ee1757` |
| 当前源树 | `49bee647112ee171de35529028fc271494260751` |
| 实机单次入口 | `/home/hhtele/ninfer-v4-h3-w6-20261024/prepared-window-r1` |
| 冻结SHA-256 | `4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc` |
| 账本/运行 | `PRISTINE`，所有used/completed/reservation/GPU计数为0；runtime不存在 |
| 当前阶段 | `CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN` |

HEAD仍为原`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，本次没有新commit或push；上表源树为实际暂存内容身份，不声称新的合并祖先。原服务镜像/argv/cache身份按历史快照实时核对未变，GPU idle、lease free。模型复用原完整SHA，当前只核对同inode/size/mtime/stat与6份前端资源SHA，没有重新读取18GB权重计算SHA。

[冻结回执](../output/ninfer-v4-h3-w6-20261024/remote-final/prepared-window-r1/freeze-receipt.json) · [准备结果](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/preparation-receipt.json) · [源树/二进制身份](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/source-identity.json) · [源码补丁](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/H3-T01-stage-A.patch)。

## 完成的补丁

1. 复用原MTP K≤5的buffer、Target全词表head、rk4v4、GDN raw Record/Fold和Graph。一个诊断server可分别以显式K3/K5运行W4/W6；产品`SpeculativeOptions`默认仍为None/0/Full，原服务参数仍保留。W4/K3是对照的显式参数，前一轮“默认K3”表述已澄清。
2. 新`NINFER_H3_W6_DRIVER`默认OFF。只在独立模型TU与驱动启用观测和测试用入包；生产数学/codec/dispatch/采样文件均未改。实际消费模型TU的编译参数与object符号已核对；关闭诊断的default构建没有宏和probe符号。
3. native单进程只加载一次模型，完成4个请求：同物理W6的Target逐步参考6轮与oracle全许可1轮，以及同前缀参考1轮与oracle终态许可1轮，合计计划9次、上限16次decode/verify。oracle取真实Target参考生成的5个ID，在原Target verify前入包；接受和许可必须来自真实执行，不改logits或采样。请求预算保持32768。
4. 每轮导出实际BF16 `[248320,6,1,1]` verify；完全许可检查对应6个因果列、canonical FP32 state/conv/KV及清理前下一轮MTP；部分许可仅比较共同首列和正式许可状态。参考和候选均物理W6，不要求W4对W6的不同数值路由全量逐bit。oracle只用于状态正确性，不作为自然MTP接受率或计时样本。
5. 新数值入口仅T6，复用原FP64参考/原判据，Q6补独立参考后的Graph，GDN链同时检查projection、卷积、recurrent/Fold和Graph直接执行的位相等。没有重跑旧P3或P4矩阵。Q6执行完整248320×5120形状，数值误差沿用原sampled FP64行/列参考，guard和输入保持检查不变；不声称所有logits都与FP64穷举比较。
6. Chat使用唯一行代码、唯一记录的具名工具JSON和低重复控制；期望输出经真实tokenizer与原RepetitionGuard检查。采样参数不在请求中覆盖。仍只执行Chat Completions；response ID、耐久终态、HTTP400停止/不重发和精确owner控制复用既有修复。完整round wall与正式committed token、服务时序、TTFT分别导出。

## BO、CPU与评审证据

BO镜像固定`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，sm89/CUDA13.2、复用既有OpenSSL/资源与对象缓存。构建容器使用runc、network none、NVIDIA_VISIBLE_DEVICES=void，并检查不存在NVIDIA设备；没有挂载模型。默认server和诊断server/native/fixtures/CPU及6个数值程序均构建PASS。未执行任何旧测试suite。

精确执行与原始输出保存在[BO诊断r3](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/BO-diagnostic-r3.json)、[默认BO](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/BO-default-r1.json)、[CPU运行argv](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/CPU-contract-r1.json)。模型TU实际编译与符号见[诊断参数](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/diagnostic-consuming-TU.json)、[默认参数](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/default-consuming-TU.json)。

16个具名场景=12个C++ host合同＋2个真实tokenizer/原guard检查＋2个新控制器/账本合同。两个期望正例分别255/164 token，guard均未触发；实际模型输出仍待测。

Spec首轮发现许可边界覆盖不足，保留原case11辅助检查PASS及原源包，仅把该具名场景修订为真实`row_commit_is_licensed`的深度0..5、许可1..6、终态部分许可/取消，以及真实`GenerationBudget`从32768递减至remaining2/1。只构建CPU目标并执行`--case 11`，run1/failed0；其他15场景复用。**具名场景16，实际场景执行17次，包含这1次评审所需定向修订复验。** GPU实际接受/取消后state和分布未由host合同证明。

[16项最终汇总](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/CPU16-final.json) · [case11原始定向结果](../output/ninfer-v4-h3-w6-20261024/remote-final/evidence/CPU11-permit-r2.jsonl) · [CPU执行计账](../output/ninfer-v4-h3-w6-20261024/CPU-BUDGET-ACCOUNTING.json)。

两路评审只读：Standards最终0 finding；Spec首轮1项P2已修复并复核关闭，最终开放项0。评审者未运行测试或远端命令。[两轴评审](../output/ninfer-v4-h3-w6-20261024/INTEGRATION-REVIEW.md)。

r1源包展开因远端Python不支持`extractall(filter=...)`而失败，随后BO目标缺失；r2新增诊断头缺CUDA类型声明。二者均已修复，原BO日志/退出码、原源包保留。展开错误另保存明确标为衍生的失败说明，不伪造原CLI日志。历史编译警告未归因成模型失败。全部既有失败、18处G1差异、C1附件缺口和Baseline证据缺口保留。

## 复用决议与最小实机范围

前一轮提案8个数值场景中，rk4v4 T6 GQA在P4已经实测PASS（base61、seed1701、2capture/4replay）。本次核对原`CASE_FINISHED failures0`，并对P4树与raw基点的28个相关GQA/codec/core源码blob确认一致。因此直接复用，**新增改为7场景/9 direct Op/7capture/14replay**，不新增该GQA测量。历史selection原件保留，由本决议和当前注册表接续。[复用证据](../output/ninfer-v4-h3-w6-20261024/GQA-T6-reuse.json)。

| 新增阶段 | 严格上限 |
|---|---|
| 数值 | Q5残差K6144/K17408各1，Q4 SwiGLU1，Attention/GDN输入投影各1，Q6全Target head1，raw GDN projection-conv Record＋recurrent Record＋Fold链1，共7场景 |
| 独立数值Op/Graph | 9 direct Op、7capture、14replay（含warmup）；capture内9个Op声明，含链内3Op，实际执行语义Op最多27 |
| native状态 | 2场景、4次模型请求；计划9次、最多16次decode/verify；1次模型加载 |
| Chat | W4→W6，各warmup1＋代码/工具/控制3，合计6 Chat＋2warmup |
| wire/模型提交 | 10wire=8模型HTTP＋2health；模型工作提交总12=native4＋HTTP8；模型加载总3 |
| GPU进程 | 数值6个进程＋native1＋HTTP2，共9个按顺序运行的候选进程 |
| 窗口 | 预计5–10分钟，硬上限20分钟，第17分钟停止准入并清理候选 |

context/KV保持262144；native请求及Pi medium输出预算32768，Chat新夹具上限2048；生产sampling为temperature1/top_p.95/top_k20及原其余项。容量不足时停止、保留证据，不降context、不裁输出、不放宽逐bit/质量断言、不自动增加样本或重试未知请求。原GPU服务保持停止，不自动恢复。

## 完整GPU资源上限

以下为**已冻结的全窗口应用CUDA审计上限**，包含数值、3次模型startup、全部Graph捕获/回放、原mandatory MTP计算、state/logits导出、权重/重置/辅助传输；是保守有限额度，未声称已测得这些实际计数。9个进程各有独立额度，不能挪用失败进程的剩余额度重发。每张Graph另限8192节点；任一额度或时间线先触及即停止。

| 资源 | 全窗口上限 |
|---|---:|
| 实际算法kernel执行上限 | 34,652,160 |
| capture内copy声明 | 1,622,016 |
| capture内kernel声明 | 2,646,016 |
| 全窗口capture | 199 |
| D2D字节 | 4,518,305,595,392（4208 GiB） |
| D2D调用 | 2,211,840 |
| D2H字节 | 154,618,822,656（144 GiB） |
| D2H调用 | 376,832 |
| 直接kernel launch | 2,646,016 |
| H2D字节 | 257,698,037,760（240 GiB） |
| H2D调用 | 376,832 |
| memset字节 | 309,237,645,312（288 GiB） |
| memset调用 | 212,992 |
| 全窗口replay（含warmup） | 69,646 |

数值阶段7/14只指独立Op套件；全窗口199/69646还覆盖模型startup及所有Engine Graph。`captured_kernel_calls`与`captured_copy_calls`是捕获声明计数，不能再与回放实际kernel重复相加。[每个阶段全部14项精确计数与字节额度](../output/ninfer-v4-h3-w6-20261024/resource-budget.json)、[可执行计划](../output/ninfer-v4-h3-w6-20261024/remote-final/prepared-window-r1/plan.json)。

## 交付与下一步耗时

CPU准备已完成。剩余只需未来获准后的一个实机窗口，预计5–10分钟，硬20分钟/第17分钟清理；原始结果、逐bit和完整decode审计预计0.5–1小时。真实收益数值仍为null；新profile的正例完整decode/token节时≥10%、控制回退≤5%仅为取舍信号。单对样本不能给p95/置信区间或发布资格；W8原具名断言、完整候选资格与生产发布保持独立PENDING。

包含源码、冻结二进制、所有原失败的完整只读快照保存在29持久根；本机保存完整源码补丁、脚本、回执、资源表和失败日志，未把本机不含二进制的紧凑包称为完整二进制备份。[归档回执](../output/ninfer-v4-h3-w6-20261024/ARCHIVE-RECEIPT.json)。

本轮没有GPU启动、模型请求、HTTP或grader调用，没有部署现网。`p95=null`、`optimization_qualification=false`。[文档/证据一致性检查](../output/ninfer-v4-h3-w6-20261024/document-validation.json)。
