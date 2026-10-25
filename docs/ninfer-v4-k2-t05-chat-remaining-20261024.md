# K2-T05 Chat接续完成：4/4 PASS，性能收益不足以采用

**请求ID采集缺陷已修复，剩余4个Chat全部PASS。文本/工具TTFT各观察改善0.881%/0.362%，只有两对样本；复用的完整Prefill配对中位改善0.314%，低于冻结1%门槛。没有建立稳定的端到端提速证据，保持原发布路径。** 本窗口已全部记账并清理，不自动追加测试。`p95=null`、`optimization_qualification=false`。

## Chat与TTFT结论

| 冻结场景 | raw客户端TTFT（秒） | candidate客户端TTFT（秒） | 本次观察改善 | raw / candidate |
|---|---:|---:|---:|---|
| 文本 | 2.296332 | 2.276107 | 0.881% | PASS / PASS |
| 工具 | 2.206091 | 2.198108 | 0.362% | PASS / PASS |

文本均精确输出`READY`；工具均以`tool_calls`结束，恰好调用一次`report_value`，解析后的参数精确为`{"value":"READY"}`。四个请求均有HTTP200、完整SSE DONE、服务端唯一request_start/request_done、匹配的Engine/request/实例身份；四个请求均实际观察到增量交付。没有放宽断言、改变`tool_choice:auto`或添加其他协议测试。

TTFT定义为客户端收到首个有语义的SSE delta，包括reasoning/content/tool数据；不是仅最终正文出现的时间，也不含服务器权重加载。每侧都是新加载且已就绪的诊断服务器，按text→tool测量，测量前均没有显式HTTP warmup；candidate剩余warmup放在两项测量之后。两侧保留同一请求字节、8193个实际prefill token、零prefix/cache命中，采样为temperature1/top_p0.95/top_k20。seed沿用原服务“未指定则随机”的合同并保存实际值，没有改成greedy或人为固定新seed。

每种场景每侧仅一次，raw整组在candidate之前，且计时含诊断审计开销；因此这些百分比只是本次观察，**不能宣称稳定TTFT收益、p95改善或生产资格通过**。文本生成量143→89、工具66→58，输出长度和seed不同，不能把总耗时差当成decode提速证据。原始数值见[分析JSON](../output/ninfer-v4-k2-t05-chat-remaining-20261024/analysis.json)和[Chat CSV](../output/ninfer-v4-k2-t05-chat-remaining-20261024/chat-metrics.csv)。

## 完整Prefill和逐bit：复用已完成实机，不重跑

旧r3的12次native原始summary、对照、日志和target logits已从远端恢复原字节；此前仅有本地观察摘要的缺口已补回，不是重新生成日志或重测。两侧各72个状态段、每侧306,659,921字节及496,640字节target logits的大小/SHA重新核验，完整比较仍为`PASS_BITWISE`。logits SHA为`5ca9d6ba955f3a10ce0d900ccc9781d5ca305937ccabfb2cb720faeaaa5dd547`。大状态原字节仍只在远端原目录和完整归档，本地不声称存在完整状态payload。

每侧1次correctness warmup＋5次measured；五对全更快，配对中位改善**0.313951%**，低于原定≥1%门槛。raw/candidate的event中位分别为2184.687988/2178.350586ms；“配对改善中位”不等于“两组中位数相除”。计时包含真实完整Prefill、首token采样、MTP准备和终态提交，测量轮不含原始状态导出；含审计和host投递影响，不是纯kernel/K4计时。[原始五对CSV](../output/ninfer-v4-k2-t05-chat-remaining-20261024/native-pairs-reused.csv)。

本次没有native调用；累计native仍13次＝首轮导出失败1次＋r3完成12次。新Chat实际kernel见证：raw为768次raw／0次split；candidate为96次raw／672次split，证明限定T1024候选真实可达，也保留其它路径。未将部分命中写成全路径替换，未补测T512、旧Baseline或已通过数值/Graph任务。

## 请求ID根因、修复与最小CPU验证

服务端`http_server.cpp:260`的`ensure_request_id(Response&)`为响应创建`x-request-id`，Chat日志上下文取的是该响应头。它没有承诺回显客户端任务标签。旧驱动却用`chat-raw-warmup`标签查找服务端记录，完整响应结束后因此误报缺少终态。属于采集关联错误；服务端协议与模型实现未修改。

新驱动从实际响应头取得唯一、非空的权威ID，按server_instance/request_id/engine_request_id/协议/stream及顺序严格关联；客户端operation ID单独保存。缺失、重复header或不匹配的Engine身份仍停止。新增arrival文件在异常路径也保存实际到达时间；旧失败丢失的客户端TTFT保持null，不用服务端时间或原SSE重建伪造。修复源码见[run_chat.py](../output/ninfer-v4-k2-t05-chat-remaining-20261024/run_chat.py)。

执行了7项新CPU检查：正常header、header大小写、缺失/重复拒绝、health无EngineID、真实旧SSE/终态按响应ID关联，以及EngineID不匹配拒绝。全部PASS；复用既有CPU/BO构建证据，0次新BO构建、0次旧通过套件重跑。主代理检查了ID合同、剩余预算、deadline、端口/PID身份及精确清理；未声称独立代理评审。

## 冻结、账本和窗口

唯一新根`/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-chat-r4-20261024`，冻结SHA`b9512345eb6d511d6f242aff465404907ec02dbe8661ec15d6012f0c26ade317`。raw/candidate使用r3相同的修复后二进制，仍是BO CUDA13.2/SM89镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，未修改模型、codec或产品默认分派。对照沿用P4的rk4v4、context/KV262144；这不是B29生产legacy codec的A/B。

| 记账项 | 新窗口实际 | 原任务累计 |
|---|---:|---:|
| native | 0 | 12完成＋1原失败 |
| 测量Chat | 4 | 4 |
| HTTP warmup | 1 | 2，含旧raw完整终态 |
| wire | 6 | 8，含旧readiness和旧raw warmup |

原r3失败账本SHA`782f2ac9a5d5547f2eecf50d5de857f0766abb9802d8d199fba3fd99cd92b358`保持不变。新账本通过派生回执补齐已结束的旧warmup和旧进程完成状态，再只消耗剩余单位；没有回写旧失败、退款或重发。所有新reservation完成，无未知请求。旧GPU envelope原封保留，剩余资源各半分给两个新服务器，单进程capture≤32、replay≤16384；未扩大原总资源上限。真实累计资源详见analysis JSON，首个native失败的最终GPU总数仍null，原因是原审计最后只到MODEL_READY。

新窗口于北京时间2026-10-24 **10:24:28**派发，10:26:36控制器退出0；GPU窗口在**126.024571秒**完成清理，未触及17分钟清理或20分钟硬限。没有重启旧guardian/旧single-use目录。候选均exited/0、PID0，guardian/controller/supervisor均退出，GPU idle、lease free。原`ninfer-4090-prod`仍STOPPED，镜像、argv及cache dev/inode未变；未自动恢复原服务或部署候选。

## 保留的失败、缺口和证据

- 两次warmup实际均输出`OK.`，冻结断言要求精确`OK`，原分类`FAIL_MODEL_BEHAVIOR`保留。夹具原文是`Reply OK.`，存在句末标点歧义，因此不能据此推断模型的通用质量问题；本轮未修写夹具、放宽断言或重跑以改善成绩。
- 首轮native缺少logits、旧请求ID关联失败、只读权限准备失败、断联暂停及原始预算/成本全部保留。首轮不存在的logits和最终CUDA计数未补造。C1附件缺口、18处G1差异及旧Baseline损坏raw/附件缺口没有因本轮成功而被抹除。
- 本地[元数据目录](../output/ninfer-v4-k2-t05-chat-remaining-20261024/remote/)完整保存新旧相关request/raw SSE/headers、服务端终态、原生summary、原始logits和冻结工具，以及新请求的arrivals；旧raw warmup到达时间缺失，未补造。完整状态归档仅远端持久保存：`hardware-r4-complete-state-evidence.tar.gz`，477,417,758字节，SHA`e828bc57799d095389d0333692bb86ec14917a69a8aae86231feb3d95e0752ee`；本地元数据包SHA`b4cfe67def1e01e60a0063af449ffd0dad9d0cdfdd204564719bad6b5ac33986`。不拿元数据或hash代替本地完整状态payload。

原服务采样和Pi medium/32768均未改动；Chat夹具2048是此前冻结的新工作负载，不是裁剪Pi。完整交付回执、备份位置和SHA见[证据目录](../output/ninfer-v4-k2-t05-chat-remaining-20261024/)。本窗口已全部完成、余额0；不自动追加实机测试，候选资格与生产发布继续独立。
