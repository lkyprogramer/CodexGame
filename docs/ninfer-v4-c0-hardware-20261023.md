# C0最小实机验证结果

**结论：INCONCLUSIVE_PRE_ADMISSION_FIXTURE_REJECTION。实机最小验收未完成，未形成性能对照；安全收尾通过。** P4服务启动后，首个新Chat在模型准入前被完整HTTP400拒绝。C0没有启动，不将这次夹具/采集故障算成模型质量或C0性能失败。既有CPU阶段通过的结论保留；不能据此授予Chat、K4或生产资格。

## 实际执行和预算

通过直连`ssh 29`，执行窗口`c0-sha-pilot-20261023-r1`。启动前核对原冻结回执SHA `b09cb8d9ac7adc8f63af562ca6221a5f1522896c4aab8904b0d931f87aabffe7`、20份工具/夹具SHA、空账本、P4/C0二进制、BO/模型身份及原服务停止状态。原准备期未授权标记保留，另有本次用户授权和单次启动回执；未改冻脚本。[启动前核验](../output/ninfer-v4-c0-hardware-20261023/verified-before-launch.json) · [启动回执](../output/ninfer-v4-c0-hardware-20261023/launch-receipt.json)

| 项目 | 窗口上限 | 账本预留 | 实际已观察 |
|---|---:|---:|---:|
| 新Chat | 8 | 1 | 1次HTTP400；0次入模 |
| 内置warmup | 2 | 1 | 1次入模 |
| 模型提交（含warmup） | 10 | 2 | 1次，仅warmup |
| wire | 12 | 2 | 1次telemetry GET＋1次Chat POST |
| 新direct Op / capture / replay | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

P4服务就绪约106.919秒，包含约104.661秒模型加载。整个控制窗口约301.748秒（5分2秒）即收尾，早于720秒清理点及900秒硬截止。其余P4 3个Chat、C0 4个Chat、3个telemetry、C0启动warmup均未执行；不把它们记为通过或复用历史任务补数。[机器汇总](../output/ninfer-v4-c0-hardware-20261023/final-summary.json)

## 原因及证据

冻结`chat_analysis.py:40`使用具名`tool_choice`对象。P4已有`src/serve/openai_schema.cpp:446`明确返回`tool_choice_not_supported`，不是本次SHA补丁改变了协议。此前准备与集成评审未发现这个真实合同不兼容，离线测试不能替代它。

失败单元`baseline-a-seed`的canonical响应ID为`req_fcb3ef3c8dfa8fd0bb6512a923a15bde_2`。原响应146字节与Content-Length一致，SHA `f29fc404a955808c1be88b2ce8106b5dea1c2f5a64ce66e5da738d8b8b6640b7`。错误为`named tool_choice is not supported`，`param=tool_choice`。Engine日志没有新Chat的request_start/request_done；实际scheduler累计admitted=1且全部队列/运行计数为0，与仅内置warmup一致。[原始响应](../output/ninfer-v4-c0-hardware-20261023/prepared-window-r1/chat-baseline/baseline-a-seed.raw) · [独立准入核对](../output/ninfer-v4-c0-hardware-20261023/execution-r1/pre-admission-audit.json)

驱动`run_chat.py`先等待Engine终态，再检查HTTP状态和传输；schema拒绝不会产生Engine终态，因而等待。确认完整响应、无入模和空闲队列后，显式停止本窗口候选，没有重发。终止驱动后，控制器缺少`stage-baseline-result.json`的FileNotFoundError另保留，不能覆盖首个400原因。

## 收尾、原始失败和缺口

候选P4容器已退出，controller/guardian/driver均退出，GPU compute apps为空。原`ninfer-4090-prod`仍exited/PID0；镜像保持`e753e228…`，原cache dev/inode仍`66306/24150039`，模型stat身份不变。没有恢复原服务，没有改变产品代码、采样、context或Pi medium/32768。[清理结果](../output/ninfer-v4-c0-hardware-20261023/manual-cleanup.json) · [最终机器回读](../output/ninfer-v4-c0-hardware-20261023/final-host-readback.json)

原账本仍保留`RESERVED_BEFORE_WIRE`；原`baseline-a-seed.outcome.json`和stage结果未写出。外置核对说明该请求已有已知完整400终态，不补造原附件、不回写PASS。冻结分析器因stage摘要缺失输出`INCONCLUSIVE_NOT_EXECUTED`，该标签不能被理解为完全未执行；本报告和final-summary明确记录实际启动与失败请求。18处G1差异、C1附件缺口和全部旧失败保留。

64个远端文件全部采回并逐字节核验，含冻结脚本/夹具、原请求/raw/header、日志、账本、授权、Docker inspect和清理证据。完整压缩包SHA为`26bf1d64d03a73aa57292266c61a5b340ade4c149362ae25dc6d95c9ce5c4d61`，远端同份保存在`/home/hhtele/ninfer-v4-c0-hw-prep-20261023/execution-r1-evidence.tar.gz`。[证据包](../output/ninfer-v4-c0-hardware-20261023/remote-evidence.tar.gz) · [可复现离线核对脚本](../output/ninfer-v4-c0-hardware-20261023/verify_evidence.py)

root运行离线核对通过，独立代理只读复核预算、完整400、无模型准入和收尾，未执行SSH或测试。没有重跑CPU、旧Baseline、native、已通过任务或grader。p95=null、optimization_qualification=false、K4=false；没有新Chat输出/质量结果，也没有C0实机cache/export配对或服务收益证据。

## 下一项最小工作（未执行）

先只修驱动：使用已有Chat合同支持的`tool_choice=auto`，仍严格要求模型真实产生目标工具调用；未产生则照实质量失败，不放宽断言。对完整准入前HTTP拒绝先做传输/错误结构和无admission核对，再持久记已知结果；未知/传输错误继续阻断。控制器缺失stage与离线分析的“已尝试但未完成”应保留准确分类。修复需版本化、定向CPU回归、评审和新冻结账本，预计30–60分钟，未改产品API或执行GPU。

之后若执行新的两版本对照，仍需明确新窗口总预算，不能把本次未用额度当作继续授权：提议≤8全新Chat/2warmup/10提交/12wire、900秒硬窗/720秒清理，预计8–15分钟。该预估只参考本次P4约107秒启动；medium实际输出耗时仍未知。原失败永久另计成本，不重跑已通过CPU或旧任务。
