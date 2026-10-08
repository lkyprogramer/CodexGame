# 本次生成物验证报告

本报告仅记录交付包在生成环境中的验证，不等于用户4090或候选NInfer通过。

| 检查 | 实际结果 | 证据 |
|---|---|---|
| Python单测 | **66/66通过** | self-check.txt；含CPU采样公式、SSE、配对统计、缺证据、命令失败/超时和恢复顺序 |
| 原Java夹具 | **23文件逐字节匹配** | references/fixture-lock.json；check_bundle |
| 原题负对照 | **3/3预期失败** | java-fixtures.json |
| 临时参考修复正对照 | **3/3通过** | java-fixtures.json；修复仅在已删除临时目录 |
| 附加Java语义答案 | **30题实际JDK求值** | java-semantics-oracle.txt |
| 任务DAG | **19任务无环** | self-check.txt |
| Shell/Python静态 | **通过** | self_check.sh；Python compileall；bash -n |
| C++接口头 | **语法通过** | g++ -std=c++20 -fsyntax-only；cpp-contract.txt |
| 空资格事实 | **BLOCKED，退出2** | empty-gate.json |
| 真实GPU/SSH/Pi | **NOT_RUN** | generation-environment.json |

生成环境使用JDK21进行原题及语义求值。原题含record，目标要求JDK17+；不要把本次控制测试改写成“已在目标JDK17实测”。

本次写了维护与日志辅助代码，并测试了回调状态机和本地子进程；真实Debian sudo策略、Docker故障、SSH断连及生产服务恢复必须在T01授权维护演练中确认。代码包含恢复尝试，不保证断电/SIGKILL/主机故障可自动恢复。

C++ header是计划接口，ninfer_lab_validate是执行AI需要创建的真实验证器。包内没有实现新DFlash2/Suffix/W8/W16 CUDA执行路径。不能仅将qualification.template.json的ready改成true并写PASS完成计划。
