# P4最小验收收尾：身份登记修复与两项Chat补测

结论：**P4_MINIMUM_CHAT_ONLY_PASS_WITH_DISCLOSED_LIMITATIONS**。本轮身份登记修复、CPU回归与两项Chat实机验证通过；复用前轮已通过的8数值场景、14 capture/28 replay及缓存scenario5，P4当前最小范围闭合。完整P4、正式性能/长上下文质量容量和生产发布仍未资格。

本轮直连`ssh 29`，新隔离根`/home/hhtele/ninfer-v4-p4-chat-recheck-20261023-r2`，冻结运行目录`window`。NInfer源码树仍为`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`，沿用已构建的27B serve；没有改产品源码、重建模型或切换原服务。新冻结SHA为`efa849c7ceb46048d4e26318d8a13660357df7b7cb3aba6656246b61e5fe2243`，20个工具/输入哈希与本远端字节一致。旧P4准备与首次实机失败目录均保持原样。

## 修复及CPU回归

前轮父进程将空`/proc/PID/cmdline`的SHA登记为owner，严格driver校验拒绝后没有发送HTTP，详见[前轮失败报告](ninfer-v4-p4-hardware-20261023.md)。本轮修复的是采集/编排工具，不是模型、引擎、codec或采样。

- `controller_common.process_proof`在读cmdline前后核对start_ticks，拒绝空字节，子进程还必须逐字节匹配Popen的预期argv。`alive`也拒绝空指纹。
- 只有空身份未就绪允许2秒内有界等待；错误argv、PID身份变化或已退出立即拒绝。登记和清理共用state lock；失败时终止并回收自己创建、尚未登记的Popen，不留下无归属子进程。
- driver继续严格比较PID/start_ticks/argv；登记等待5秒给父进程有界采集及持久化留出时间，没有放宽比较。不是只延长超时。
- 新controller删除数值/native执行函数及调用；phase ledger只允许一次serve warmup。数值、Graph、缓存的新增预算均0。

先在旧实现执行空cmdline回归，得到预期FAIL（[RED原件](../output/ninfer-v4-p4-chat-recheck-20261023-r2/registration-red.log)）。随后在29的Linux上执行新8项CPU合同，**8/8 PASS，0.235秒**：空指纹拒绝、ticks变化、错误argv、关闭窗口禁止spawn、持续空读终止回收、错误身份终止回收，以及真实Popen/`/proc`在强制两次空读后通过严格子进程登记。没有Docker/GPU/HTTP调用；没有重跑旧通过测试。见[远端CPU日志](../output/ninfer-v4-p4-chat-recheck-20261023-r2/remote-evidence/execution/registration-green-r1.log)。

## 实机结果与预算

| 项目 | 本轮授权 | 本轮实际 |
|---|---|---|
| 新数值/Graph/native缓存 | 0 | 0；原PASS证据按SHA绑定复用 |
| Chat模型请求 | 2 | **2/2 PASS**，原生nonstream与代理stream |
| HTTP wire | 5 | **5/5**：2 client+1 proxy上游+2 telemetry |
| 模型提交（含warmup） | ≤3 | **3**：warmup1+两Chat2 |
| 窗口 | 硬15分钟、第12分钟开始清理 | **114.356786秒（1分54秒）**，完成后立即清理 |
| 原服务恢复/重试 | 0 | 0；原GPU服务保持停止 |

原生输出的工具参数严格解码为**38字节**，与固定内容SHA一致，无多余转义。代理有**9个参数delta**，首个参数接收比同server的durable done早 **228.823730毫秒**，满足增量交付断言。这个时间差是同主机传输观察，不是逐token ITL或正式性能统计。

代理请求P=411，实际前缀命中/恢复 **409 tokens**，computed prefill **2 tokens**，source=l1，满足新midrise profile的复用断言。两次请求均只有一个结构完整工具调用，无无效/不完整参数；request/response、canonical ID、Engine ID、同server instance和durable done均已关联。

两份真实HTTP telemetry显示同一server instance，admissions从1到3，末次running/waiting/prefilling/decode_ready全0。wire账本五项均完成，2个request_start对应2个durable terminal，无未结束attempt，也未自动重发。实际登记的driver owner为非空、匹配预期argv的指纹，旧空cmdline失败没有覆盖。

本轮与前轮分开记账：前轮3提交（native2+warmup1）及233.053041秒失败成本继续保留；本轮另3提交及上述耗时。两个P4窗口累计6提交，来自两次分别授权的窗口，未挪用旧额度或抹去旧warmup成本。

## 已复用证据与清理

原数值8/8、36 direct Op、14 standalone capture/28 replay全部复用；1个缓存scenario5旧snapshot4明确拒绝、新snapshot5保存/恢复一致、跨Engine L3完整复用263 tokens的PASS也复用。它们都绑定同源码树35d3与同构建身份，没有重跑，也不拿本轮两Chat覆盖完整128K/192K/248K质量容量门禁。

原生38字节与代理增量断言沿用P3合同；没有重跑P3其它通过任务。Baseline、BO、G1、P1—P3原始资料保留。18处G1差异、C1旧时点HTTP附件缺口以及全部历史FAIL/INCONCLUSIVE和缺失资料不改写；本轮telemetry不是C1原附件的替代品。

清理回执为`ORIGINAL_STOPPED_CANDIDATE_CLEANED`，无错误。候选容器已停止保留，driver/proxy/guardian/controller均退出，GPU compute进程为空。原服务Id/image/Config/HostConfig/Mounts与窗口前一致，原缓存dev/inode为66306/24150039，原proxy PID1950与脚本SHA保持。原服务没有自动恢复。

context/KV262144、temperature1/top_p0.95/top_k20/presence0、MTP3、medium/default32768均保持。两请求诊断O4096不属于Pi任务，Pi medium/32768未改，没有新增Pi/Baseline/grader请求，也未实施greedy proposal/Target sampling优化。

## 集成评审与交付

**Standards：** 独立只读评审无规范阻断及必要smell建议。

**Spec：** 独立只读评审无具体finding，身份/生命周期/预算/无native重跑路径符合本轮要求。两位评审未运行测试、SSH、GPU或HTTP；CPU和实机结果由主代理实际执行。prepare/freeze生成器由主代理核查，不属于两位评审的覆盖范围。

[集成评审记录](../output/ninfer-v4-p4-chat-recheck-20261023-r2/INTEGRATION-REVIEW.md)、[最终审计](../output/ninfer-v4-p4-chat-recheck-20261023-r2/final-audit.json)、[逐文件哈希核验](../output/ninfer-v4-p4-chat-recheck-20261023-r2/remote-delivery-verification.json)及[冻结回执](../output/ninfer-v4-p4-chat-recheck-20261023-r2/freeze-receipt.json)均保存在持久output。167份远端文件全部按SHA校验，包括HTTP原件、请求/转发body、canonical bridge、server日志、账本、状态与清理回执。执行前403份活动MD另按字节封存。

本次授权最小范围已完成，不自动扩到完整P4/P5或上线。p95=null，optimization_qualification=false；没有宣称统计吞吐改善、正式质量资格或生产发布通过。
