# 给后续执行 Agent

先读 README、AGENTS 与 docs/03_BASE_INTEGRATION.md，再读原基础包对应章节。此次用户要的是增量文档；**本包没有任何默认 live 执行许可。**

## 你接手的不是空白工程

原包已有 completion-path/v1、身份/时钟/DAG、观察器资格、唯一 LabFlow 控制器设计、历史去重与统计门。当前 Strata 还已有 force_check.py、check_cuda_spills.py、dispatch_stats.hpp、run_manifest.hpp 和微基准。先判断这些能力在现场的状态：已有且合格就复用，已有但不合格就补缺口，只有确认不存在才实施计划中的模块。

## 第一个交付

E0 只输出三个文件（在后续获准的 lab 工程内）：

- reports/kernel-evidence/source-and-deployment-map.md：源版本与当前部署身份分开。
- reports/kernel-evidence/reuse-map.md：每项 REUSE / EXTEND / NOT_IMPLEMENTED，另列 BLOCKED / CLOSED。
- reports/kernel-evidence/contract-v1.md：基础能力范围、字段与白名单，engine/GPU预算为0，旧关闭项与下一步或 null。

精确后续任务见 [实施计划](plans/IMPLEMENTATION_PLAN.md)。它是开发说明，不是启动命令。

## 执行时保持五个独立结论

1. 输入完整性与来源可信度。
2. 观测资格与生产路径等价范围。
3. 算子/数值/状态/服务正确性。
4. 完成路径可达收益与实际任务质量。
5. 授权与预算。

一个上游 PASS、一个新脚本 exit0、一个 kernel 更快，都不能把这五项合并成“可采用”。

## 本包可立即复核的范围

在本包根运行：

~~~bash
python3 -B -m unittest discover -s tests -v
python3 -B tools/validate_addendum.py
~~~

可选择用已存在的、精确版本上游 force_check.py 运行三项离线反例：

~~~text
python3 -B tools/probe_upstream_force_check.py --source /absolute/path/to/audited/force_check.py
~~~

最后一条只接受本包锁定 SHA256；它不下载源码，不执行 gen/score，无法获得文件或 hash 不同就停止。合成反例不是任何模型的测量。

## 结束方式

没有新机制、证据不完整、工具无权限、没有设备授权，均可正常交付 STOP/BLOCKED。不要把“补齐底座”变成无限补采，也不要为了出现绿色结果修改原合同。
