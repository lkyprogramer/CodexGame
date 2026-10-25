# K2-T05 T1024：完整Prefill／Chat实机准备已冻结

**真实驱动、控制器、r2空账本、四个诊断可执行文件及资源上限已完成冻结。BO构建、29项新CPU检查和主代理集成评审通过。本轮0 GPU／模型／HTTP请求；窗口尚未开启，原服务保持停止。** 不补测T512，不重跑旧Baseline或已通过GPU任务。

## 唯一当前入口与身份

- 远端连接：`jssh 29`。
- 当前入口：`/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023/prepared-window-r2`。
- 冻结SHA：`4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d`。
- 候选分支：`codex/k2-t05-full-prefill-prep-20261023`；树`abc974d38d861c4fa72692345aadfc8565624fa3`，基点`9818eafa5d2660c2ea9682cc7653e6603f21ebb5`。
- raw对照分支：`codex/k2-t05-full-prefill-raw-20261023`；树`a5ba33de12d75ab1e16a153020e4068094ee1757`，基点`3ea537c00c759ef2a4577b525ae691f694ae102e`。
- r1因CPU复查发现关闭中FD枚举竞态而退役；原目录、回执和零账本保留，未执行GPU。**只使用r2，两个版本预算不相加。** r2仅修复主机工具，四个BO可执行文件与r1逐字节相同，无需重建已通过C++。

冻结后实际执行过`controller.py --plan-only`，退出0；当前ledger为`PRISTINE`，used/completed/GPU envelope/actual均0，reservations为空，runtime不存在。[冻结回执](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/prepared-window-r2/freeze-receipt.json)、[空账本](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/prepared-window-r2/budget-ledger.json)、[最新入口记录](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/LATEST-PREPARATION.json)。

## 固定工作量：一个窗口，不叠加旧额度

| 工作 | raw | candidate | 合计 |
|---|---:|---:|---:|
| native完整Prefill | 1 warmup＋5 measured | 1 warmup＋5 measured | **12次** |
| 新Chat测量 | 文本＋工具各1 | 文本＋工具各1 | **4请求** |
| 明确计账的HTTP warmup | 1 | 1 | **2次模型提交** |
| readiness | 1 GET /health | 1 GET /health | **2个无模型wire** |
| HTTP wire，包含warmup | 4 | 4 | **8个** |

总计18个模型工作单位＝12 native＋4 Chat＋2 HTTP warmup。native工作单位是直接Program Prefill调用，不能说成18个HTTP或Engine请求。显式HTTP模型提交仅6次。

native固定8193个token，chunk1024、8个完整块＋T1尾块。使用真实27B Program/权重/目标sampling/MTP3，源码核查确认完成路径会采样首个token并准备MTP，因此已修正前次“采样前停止”的提案。首个warmup同时保存完整状态和真实target logits；5次measured不做这些诊断导出。每次预期raw对照384次raw输出kernel、candidate384次split输出kernel，另一条为0；由实际CUDA kernel句柄/Graph节点见证核对，不从predicate推定命中。

首个warmup在target logits刚生成时、MTP覆盖其工作区之前复制原字节；终态提交后导出全部GDN/conv、逻辑attention/backend KV原字节，并保存frontier/schema及prefix/compatibility摘要。导出在warmup中完成，不增加Prefill次数。控制器重新读取文件并核对SHA/bytes，再比较canonical state及logits；不拿只有“相等”字样的摘要代替原始字节。原始state/logits不一致立即停，不再发Chat。

顺序为native raw→candidate→状态比较→Chat raw→candidate；每个阶段独占GPU并核查上阶段退出。native计时含完整Prefill、首token sampling、MTP准备和终态提交，不是单个卷积Op。两组按同序号配对，不是AB/BA；计时含审计开销，结果仅为诊断信号，不直接授予K4净收益资格。

Chat夹具用冻结的真实tokenizer/template在CPU完成解析与计数，两个长输入为8193–8194 token。普通文本要求`READY`；工具只提供`report_value`，使用当前支持的`tool_choice:auto`，要求恰好一次该函数且JSON精确为`{"value":"READY"}`。不调用、参数多余转义、reasoning-only/length等照实记模型行为失败，不为完成测试放宽断言。named/required choice均不受该源码支持，原失败保留，不增加这类API功能。

两个Chat测量＋warmup均为新夹具，输出上限2048；这是新工作负载，不是Pi重跑或缩减Pi预算。原服务默认输出32768、native请求预算32768、Pi medium/32768均保留，temperature1/top_p.95/top_k20不变。客户端保存完整raw SSE、headers、真实到达时间、usage、Engine/request身份和完整server终态；到达时间在证据fsync前记录。不能观察到分批交付时明确记录`incremental_delivery_observed=false`，不冒充已验证增量交付。

## CUDA／Graph与传输：四个进程的全局保守上限

| 计账项 | native单进程 | Chat单进程 | 全窗口（各两个进程） |
|---|---:|---:|---:|
| capture尝试 | 64 | 64 | **256** |
| replay提交 | 4096 | 32768 | **73728** |
| 显式direct kernel提交 | 524288 | 1048576 | **3145728** |
| capture期间kernel API记录 | 524288 | 1048576 | **3145728** |
| 算法kernel：direct＋replay展开 | 1048576 | 16777216 | **35651584** |
| capture期间copy/memset API记录 | 524288 | 524288 | **2097152** |
| H2D calls／payload bytes | 65536／64GiB | 131072／64GiB | **393216／256GiB** |
| D2D calls／payload bytes | 65536／64GiB | 1048576／2048GiB | **2228224／4224GiB** |
| D2H calls／payload bytes | 65536／16GiB | 131072／16GiB | **393216／64GiB** |
| memset calls／bytes | 32768／64GiB | 65536／64GiB | **196608／256GiB** |

每张Graph定义另限8192节点、子图深度8。以上是包含加载、初始化、warmup、reset、导出和模型内部Graph工作的安全上限，**不是预计执行次数，也不是必须消费的测试矩阵**。D2D包含raw QKV提取及状态复制；辅助传输包含于全部CUDA copy上限中，无另一个未计账池。原32768/2048输出预算不因资源触顶而裁剪，任何一个上限先到即停止，不自动加预算。

预算在调用GPU API前扣减。capture记录单列，不算已执行算法kernel；每次Graph replay根据实际节点展开kernel/copy/memset成本，Graph更新后重新取元数据。二维copy按width×height，三维按width×height×depth计payload，不把pitch算作有效字节。未知copy kind、未登记Graph exec或不支持节点停止，失败调用仍消耗已预留额度。底层驱动隐式helper kernel不可见时不冒充算法kernel计数；memset另按API操作/字节限制。

每个进程先在持久ledger预留其不可退还资源envelope；进程完成且audit完整后才登记实际值。native另有逐次RESERVED/COMPLETED耐久日志，HTTP逐wire预留。断线/未知结果不重发，完整HTTP错误独立标为known terminal并保留raw；部分阶段不会被写成全部完成。[完整机器计划](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/prepared-window-r2/plan.json)、[CUDA链接入口闭合](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/evidence/CUDA-link-closure.json)。

## 控制、清理与现网边界

单GPU lease由控制器和独立guardian共同持有。GPU工作admission在第17分钟关闭，guardian只停止本窗口精确label/image/container ID匹配的候选，第20分钟为硬限。Chat发wire前再核验实际PID/start ticks/argv及监听socket归属；关闭中的FD允许跳过，必须仍找到真实listener。guardian每秒心跳、每5秒只读记录clock/power/温度，采集失败不使清理失效。原容器从不作为cleanup目标，不自动恢复。

诊断构建只在编译期跳过服务器隐式startup model warmup，改用上述恰好2次HTTP warmup，避免暗增提交。默认产品构建不启用该宏。无GPU执行授权和正确freeze SHA时，控制器在任何Docker/GPU动作前拒绝；只读plan模式不会创建runtime。

model SHA已在CPU完整复核：`eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`，与原BO/G1一致；六份资源SHA也一致。两个隔离版本都用P4 `rk4v4` midrise、context/KV262144、chunk1024、cache off/no-prefix-reuse；不挂载原cache目录。原生产legacy `rk4v4-e8`镜像/参数/缓存仍不变，本对照不是B29生产镜像对照。容量不足即停，绝不降低context。

## 已执行的最小CPU验证与评审

- BO固定CUDA13.2/SM89/Release/27B-only，最多4 worker，无网络、runc无GPU设备；raw和candidate的native/server均构建通过。
- 新CPU检查**29个唯一场景**：10个计数/溢出/预算合同，5个真实audit实现对记录型CUDA元数据边界的检查，13个编排/SSE/预算/终态合同，加1个关闭FD竞态检查。另仅对修改后的HTTP终态处理做过1项定向复查；未重跑旧CPU/GPU任务。
- 两个实际native二进制的`--plan-only`一致。真实三份Chat body已通过产品schema和前端CPU解析。CUDA13.2 SDK原型、导入符号与链接wrap集合已核对；这不等于真实设备元数据路径已通过。
- 主代理集成评审已闭合：隐式warmup、图成本更新、传输字节、进程/端口身份、已知HTTP错误与未知传输、原始状态hash、SSE时间戳和FD竞态等问题已修复。没有声称独立代理评审。

首轮PreparedPrompt私有成员访问编译失败，已改用公开view。两个不支持的tool_choice CPU预检失败均保留；归档首轮缺少远端stdin启动脚本的失败及部分包也保留，上传原脚本后另建完整包，不回写旧包。r1只读保留，r2增加FD处理，无GPU请求发生。[评审记录](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/evidence/integration-review-r2.json)、[r2复用证明](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/remote/evidence/r2-reuse-proof.json)、[最终host工具源码](../output/ninfer-v4-k2-t05-full-prefill-prep-20261023/source/tests/k2_full/controller.py)。

## 交付、剩余范围与预计耗时

源码/原始CPU日志/回执在本地持久镜像，19个变更文件与远端归档逐字节核验。4个Linux可执行文件在29当前r2冻结目录中；其不变二进制payload同时保存在原完整远端包，SHA`167a4c543d2752d5045096b60d9fe82177b1db9f5bf0e4c7bb9d2b2c32d281e1`。本地metadata镜像不复制这4个可执行文件，并非声称本地存在完整二进制；远端均完整保留，源码及构建/哈希可复现。r2 metadata包SHA`47214575b49fe95d5228cb485d105d200f08725e39b80860560afc28b9ef9003`，与不变二进制payload共同构成当前交付。

下一步只剩获得实机执行授权后开启上述一个窗口：预计8–15分钟、硬限20分钟/第17分钟清理；结果分析约0.5–1小时。当前未执行GPU数值、实际route-hit、全状态/logits比较、真实Graph审计或Chat，没有完整Prefill或TTFT收益结论。此窗口至多提供候选信号和4请求smoke，不提供p95或总体质量/分布证明。

18处G1差异、C1原附件缺口、全部旧失败及旧Baseline原始证据保留。`p95=null`、`optimization_qualification=false`；候选资格与生产发布继续独立。
