# P4最小实机验证结果

结论：**P4_MINIMUM_NOT_PASSED_WITH_PRESERVED_EVIDENCE**。数值/Graph与新旧缓存恢复通过；Chat在发送前因驱动进程身份登记缺陷停止，未取得本轮Chat实机结果。该失败归类为编排工具失败，不是模型质量失败。没有重跑已通过任务，没有放宽断言，也没有超出预算。

本次直连`ssh 29`，使用已冻结并评审的源码树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`、freeze SHA `d0850be9004505295b90335772fe480afb0c4ec9328299fe2f3c0ddbd8094ca8`。执行前核验冻结依赖、三份二进制、真实旧slot、模型stat、原服务已停止、GPU空闲与初始空账本。原冻结bundle未覆盖；新授权文件和本次状态/账本独立保留，不将失败窗口重新初始化。

## 实际结果与计账

| 项目 | 授权上限 | 本次实际与结论 |
|---|---|---|
| midrise数值 | 8场景/36 direct Op | **8/8 PASS，36 direct Op** |
| standalone Graph | 14 capture/28 replay | **14/28全部PASS**；capture内14次Op声明另列 |
| 新旧缓存隔离与恢复 | 1场景/2模型提交 | **scenario5 PASS，2次提交** |
| Chat Completions | 2客户端模型请求 | **0/2执行，NOT_RUN**；驱动在发送前退出 |
| HTTP wire | 5（2 client+1 upstream+2 telemetry） | **0/5**；原始空wire账本保留 |
| 全部模型提交 | 含warmup≤5 | **3次**：native2 + serve warmup1 |
| 窗口 | 硬20分钟，第17分钟开始清理 | **233.053041秒（3分53秒）**；故障后立即清理 |
| 清理 | 仅本轮候选；原服务不恢复 | **PASS**，3个候选容器停止保留，子进程退出，GPU空闲 |

窗口约为Asia/Shanghai `2026-10-23 11:09:15` 至 `2026-10-23 11:13:08`。原计划8–12分钟是完整最小窗口的估计，本次提前失败的3分53秒不能作为完整验收耗时或性能收益。

数值固定目录为rk8v4/rk4v4/rk2v4-e8各T6/T66、base61，以及rk4v4 A4的prefix63/1000；没有运行旧P3的136场景。36 direct + 28 replay为64次执行的语义Op，capture中的14次Op声明不额外算实际执行；14/28不代表Engine内部Graph总数。沿用原独立FP64 oracle、codec参考、cache字节/guard及容差。

缓存场景实际拒绝旧snapshot4，拒绝后lane未污染；新snapshot5保存与恢复digest一致。重建Engine后从L3完整恢复并复用263个token，期望frontier=263；两个Engine各1次admission。旧v4原件按SHA复用，不重跑P2造附件；它不补齐C1缺失的HTTP附件。

## Chat失败的确切证据

原始[driver.stderr.txt](../output/ninfer-v4-p4-hardware-20261023/remote-evidence/window/driver.stderr.txt)为`RuntimeError: driver ownership not registered`。父进程在state中登记driver PID `107388`，`argv_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`，恰为**空字节SHA256**。驱动要求同PID/start_ticks与真实非空cmdline SHA一致，因不匹配在2秒登记期限后退出。

已确认的实现缺陷是父进程把空cmdline采集结果当作有效ownership登记；具体为何出现空读的底层时序没有复现，启动/exec瞬态只是推断。不能只延长超时或放宽身份断言。前轮离线合同与只读评审没有覆盖这次空proc快照情形；其PASS继续只代表原检查范围。

驱动失败发生在`protocol-result.json`及任何wire reservation之前。服务日志只有server_start、warmup export和最终throughput，没有HTTP request_start/done；最终durable scheduler为admitted_requests=1且running/waiting/prefilling/decode_ready全0。结合native两次完成admission，确认累计3提交，**没有未结束HTTP请求**。两份HTTP telemetry附件未创建是因为根本未发请求；不拿后来的GET补造原时点附件。原server日志中的warmup计数作为计账来源，不代替Chat结果或HTTP附件。

控制器以`HTTP driver failed/unknown; no replay`停止并执行清理；未知期间未重发。核对原件后已将本次结果澄清为已知的发送前失败。phase-ledger中的server_warmup仍保留原始RESERVED状态，最终审计单独记录从durable throughput证明的已完成warmup，不回写原账本制造PASS。

## 为什么本轮不再启动

当前已消耗2次native和1次warmup。候选服务已按故障合同清理，重新启动并完成两项Chat需要1次新warmup+2次请求，累计 **6>5**，超出明确授权。因此没有重启服务、刷新deadline或另开账本绕过总额度。

剩余范围只有先版本化修复进程登记工具并作CPU回归，再补原生nonstream和代理stream两项Chat及prefix复用；数值/Graph与scenario5证据直接复用。这个后续独立窗口最低需要**2 Chat请求/5 wire/含新warmup共3次提交**，预计3–5分钟；这是未授权的下一步估计，本次没有执行。不得复用本轮旧预算或把两项Chat记PASS。

## 身份、资料与门禁

原GPU服务保持STOPPED；Id/image/Config/HostConfig/Mounts与窗口前一致，原缓存dev/inode保持66306/24150039，原proxy PID1950与脚本SHA相同。候选清理未恢复原服务。实际argv和server日志确认context/KV262144、temperature1/top_p0.95/top_k20/presence0、MTP3及default32768保持；native检查resolved sampling，Pi medium/32768未改，没有Pi/旧Baseline/grader请求。

保留本次驱动失败、全部历史失败、18处G1差异和C1附件缺口。执行前403份活动文档逐字节归档；前轮P4准备交付、源码归档与冻结回执只读保留。完整远端记录、原始slot/缓存、stdout/stderr、数值事件、native admission、serve日志、状态与账本均复制到本轮持久[证据目录](../output/ninfer-v4-p4-hardware-20261023/)。逐文件SHA结果见[备份核验](../output/ninfer-v4-p4-hardware-20261023/remote-delivery-verification.json)，独立预算与清理审计见[final-audit.json](../output/ninfer-v4-p4-hardware-20261023/final-audit.json)。

本轮最小P4验收**未通过**，完整P3/P4、长上下文质量/容量、真实decision adapter、配对性能与发布继续UNQUALIFIED。p95=null，optimization_qualification=false。不以8个数值场景、缓存PASS或server成功启动替代Chat、完整P4-T06 V01—V03或发布资格。
