# frontier/P01 · 真实Pi历史诊断（2026-10-30）

结论：**STOPPED / INSUFFICIENT。** 最小采集适配已实现并执行，但第一条真实请求自然EOS，仅输出941token，未满足冻结的2048输出条件。按首个短输出停止，两个warm append均NOT_RUN；无重试、无替补、不进入P02候选或P05性能。不能说完成了暖态关键路径验证或已经证明无优化空间。

## 实际执行与结果

只启动一个原P6 native引擎PID2350922，实际10272槽。完整STRATA环境恰等P00预备环境；二进制SHA、模型/模板身份保持，未编译或修改native。P00全资产hash证据复用，启动/收尾检查资产元数据及路径集合，未重复读取78.2GB。

| 请求 | 输入 | read / reused | 输出 | TTFT | 完整wall | 验收 |
|---|---:|---:|---:|---:|---:|---|
| prime | 103183 | 103183 / 0 | 941 | 30.6003s | 37.1579s | INSUFFICIENT_SHORT_OUTPUT，finish_reason=stop |
| append_1 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 前序短输出停止 |
| append_2 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 前序短输出停止 |

TTFT为首个thinking事件；首个正文35.5202s。服务计时prefill29378.6ms、decode6573ms，decode报告143.2tok/s。这是一条短输出冷读观察，不能当固定2048性能、暖态吞吐、配对增益或任务完成率。SSE独立解析为917个JSON事件及一个DONE；915个非空输出事件不等于941token。

SSE另外记录两项`bash/undeclared`工具调用被服务拒绝；没有执行工具。诊断投影保留历史但tool_choice=none，这些事件也不能视为真实Pi任务质量通过。原六项长检索FAIL保持。

整个live adapter墙钟109.9625s，含启动、加载、请求和首次清理；未超3600秒。只消耗1引擎/1HTTP尝试，三个所属PID最终均退出。

## 采集范围与缺失

复用原OwnedServer、全局GPU锁、SSE exchange、资源guard、MemorySampler；未添加校准chat、第二引擎、native打点、profiler或锁频。启动前实际授权、GPU无外来进程和18089空闲核对，并在原全局锁内重查。

原件保存请求/原始SSE/响应/完整渲染token hash、native PID/env/argv、每秒内存、聚合native计时。聚合计数不是逐window轨迹；WINDOWS为空，CPU完成/CUDA事件依赖、实际expert dtype/nt和原始采样token IDs均UNKNOWN。没有填造DAG、可删墙钟或加速上界。

资源观察：70个guard样本，无guard中止；峰值68°C、23702MiB显存。native内存样本32条，最大VmSwap460.543MiB，最大RSS44741.984MiB，采样范围major-fault增量22303。系统与native内存数据只作为背景；仅有cold prime，不能归因到暖态阻塞，也不以swap数字立项。

## 收尾失败与资源交还

原适配器将wait_released上限写成30秒，首次释放检查超时，保存在`run/CLEANUP_ERROR.json`；首个原因仍为短输出，未覆盖。原错误没有区分端口和GPU，不推断其唯一原因。

随后现场只读复核确认：13保护SHA未变、实验控制配置和引擎配置SHA与P00一致、生产inactive/dead/enabled、GPU1MiB无计算进程、18089可bind、native/server/coordinator三个PID均不存在、临时key已移除。见`FINAL_READBACK.json`。没有重启或重放请求。

独立源码审阅发现启动前缺实验控制配置SHA门，已在本地后续版本补上；实际本轮两份配置的SHA回读均匹配P00，未观察配置漂移。后续版本还将actual env改为等值检查、释放等待改为120秒收尾预算的剩余时间。**这些修复只有CPU验证，没有GPU复测。**

`executed_sources/`保存此次实际执行版本，原45文件下载清单不变；两份原始CPU测试从首次传输包补回并与TRANSFER清单匹配。当前本地修复版与实际运行版分开，不能用修复版倒写运行证据。

## 验证与归档

- 实际执行版在29运行：warm_run5项、critical_path6项CPU测试PASS，然后唯一GPU启动；启动前无负载preflight、传输SHA检查通过。
- 本地最终版本：`python3 -B -m unittest discover -s tests -p 'test_frontier_*.py' -v`，32项PASS（含P00的19项，P01的7+6项）。修复后没有重新GPU执行。
- 独立Reviewer/Validator核原件：45/45长度/SHA匹配，原件2619625bytes；SSE、请求/历史/响应canonical hash、ACTIVATION、13保护和两个配置SHA一致；执行版ANALYSIS路径归一化后重算一致。
- Reviewer与Validator未独立SSH/GPU；前者未重跑CPU测试，后者复用已通过CPU结果，分别记录实际检查范围。
- 原始压缩包SHA：`bbae182cd879fc046358495a3ccfc15b473463d016eb6123b82bb230e0cc7847`。runtime.private.json与模型权重未导出。
- 初次本地测试命令cwd错误导致0 tests，未计为通过；正确实验主目录后通过。最终包清单与diff检查在收尾执行，不重复业务全仓测试。

原件位于 `workspace/frontier/p01-20261030`，阶段门`PHASE_GATE.json`，实际run原件、执行源、RAW_MANIFEST、STAGED_TEST_PROVENANCE及最终现场回执均保留。

## 结束点

P01以INSUFFICIENT关闭；已有采集不足和短输出事实不会自动触发补样本。后续若重新考虑warm诊断，先形成明确的新输入/输出合同；当前不开发内核、不重开旧候选，P05仍BLOCKED_EVIDENCE。
