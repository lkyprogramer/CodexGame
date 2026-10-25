# P3 实机驱动准备与最小窗口

状态：**P3_HARDWARE_DRIVERS_PREPARED_GPU_NOT_RUN**。本轮完成隔离驱动、无 GPU 构建、离线合同和集成评审；没有运行 GPU 数值、模型或真实 HTTP，没有切换现网。完整 P3、性能和发布资格仍为 UNQUALIFIED。

通过 `ssh -J jump 29` 访问。隔离分支 `codex/p3-small-t-tool-stream-20261022`，根 `/home/hhtele/ninfer-v4-p3-20261022`。输入为上一轮 P3 树 `caf56ac9ab48de0a5802c19c7a1b672667eff4aa`；本轮最终树为 `b3fc67df1a7fd3fbac318a3505b38c0d48a3beb2`。HEAD O 和 MERGE_HEAD U17 保留，没有创建提交、推送或声称双亲 merge ancestry 已资格。可复现 [补丁](../output/ninfer-v4-p3-driver-20261022/p3-driver.patch)、[完整源码快照](../output/ninfer-v4-p3-driver-20261022/source.tar.gz) 与 [冻结回执](../output/ninfer-v4-p3-driver-20261022/freeze-receipt.json) 均已保存。

## 已交付的驱动

10 个原有 Op 测试增加有限入口 `--p3-small-t` 和纯 host 目录 `--p3-catalog`，无参数仍为原矩阵。范围包含 Q5 residual、Q4 SwiGLU、Attention/GDN input projection、W8 residual/SwiGLU、GDN snapshot/record。普通族覆盖 T=1/2/3/4/8/12/16/24/32/33 与已有实际维度；详细 case ID、布局和路由见 [Op 目录](../output/ninfer-v4-p3-driver-20261022/remote-preparation-r1/ops-catalog.json)。

成功路径固定 **136 场景、139 次直接 Op 调用、130 次 Graph capture、260 次 replay**。两次 replay 检查复用原 oracle、容差、guard、输入保全和 reset。snapshot 包含独立数值/state oracle；record 与 snapshot 的对照为补充证据。AllowA8 标签和 host 路由目录不代表 GPU 实际 INT8 命中；小 T 的共享 A16 路径如实记录。实际窗口须校验精确 case ID、唯一终态及零失败，77 不算 PASS。

`replay_p3.py` 对原生 Chat/Messages/Responses 各准备非流式工具调用、增量流、实际本地 SHA256 工具执行后的 history replay、部分参数取消。回放使用当次模型输出的工具调用 ID 与参数，不预造模型历史。请求、原始响应、代理实际转发字节和身份关联先持久化；未知结果不自动重发。分块只记录字节到达，真实逐 token ITL 仍为 null。

Responses 校验 delta 拼接、arguments.done、item.done 和 terminal 参数；Chat/Messages 没有同等的完整终态参数副本，验证边界保持为合法完整参数、结束标志和实际工具回放。取消若只有严格关联的 error-only 终态，只证明 drain，缺失 finish/incomplete/export 指标明确记 INCONCLUSIVE。

窗口控制器默认只输出计划；`--prepare` 只复制冻结资料并创建无效授权模板。实际执行必须有新授权，独立 guardian 才会接管恢复。控制器绑定源码、ELF、工具、夹具、原容器/镜像/参数/缓存和代理 PID/start/argv/listener。候选使用独立缓存与日志。恢复原容器并验活的动作没有在本轮执行。

## 新增验证与保留缺口

固定 BO 镜像 `sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，CUDA13.2/SM89/Release，容器 `--network=none`、无 GPU 设备。11 个目标增量构建通过，耗时 30.6235 秒，配置 0.7662 秒。新 C++ 夹具直接调用候选三协议解析器、RequestOptions 与 prompt semantics：24 份实际驱动/冻结代理派生 body，22 接受、2 指定拒绝。10 个 Op host catalog 通过；显式 GPU 模式均返回 77，没有执行数值/Graph。原始结果见 [R1 回执](../output/ninfer-v4-p3-driver-20261022/remote-preparation-r1/status.json)。

远端新增协议 **28 项 PASS**，窗口合同 **21 项 PASS**。原始协议 CTest 输出在 JUnit 被截短，已从同次实际 `LastTest.log` 恢复完整输出，未重跑测试。R2 窗口因 `/window` 挂载过浅而导入失败，用例未执行；原日志保留，仅该套件改为 `/work/window` 后在 R3 通过。更早尚未写完文件时的一次零测试 discovery 不计 PASS，只有工具对话记录，无独立日志附件。证据见 [完整协议日志](../output/ninfer-v4-p3-driver-20261022/remote-protocol-LastTest.log)、[R3 回执](../output/ninfer-v4-p3-driver-20261022/remote-preparation-r3/status.json) 和 [交付回执](../output/ninfer-v4-p3-driver-20261022/delivery.json)。旧 Baseline、BO、G1、P1/P2 native、上一轮 P3 已通过的 host/SDK 任务均复用，没有重跑。

独立集成评审发现六项驱动问题：成功状态不一致、error-only 取消、自然完成加断连、恢复绝对截止、转发 body 原件、客户端绝对截止。全部修复并按冻结字节只读复核，无未关闭 finding。评审者未执行测试。原失败与修复见 [评审账本](../output/ninfer-v4-p3-driver-20261022/review-and-failures.json)。

远端持久准备目录 `/home/hhtele/ninfer-v4-p3-20261022/hardware/driver-v1-20261022` 已实际完成文件准备，状态 **PREPARED_NOT_AUTHORIZED**；没有有效授权、controller、guardian、候选容器或活动客户端。只读核对现网仍为原容器/镜像/参数/cache、PID63407，代理 PID1950，未结束请求和队列均0，未发验活请求。见 [身份快照](../output/ninfer-v4-p3-driver-20261022/preflight.json) 与 [最终核验](../output/ninfer-v4-p3-driver-20261022/final-attestation.json)。

已确认的代理限制：冻结生产 shim 会给 Responses 添加候选严格解析器不接受的 `enable_thinking` / `reasoning_effort`。真实 C++ 解析已返回 `400 unknown_parameter`，不是模型质量失败。保留两个 proxy Responses 场景 **BLOCKED_BEFORE_WIRE**，不改 shim、不绕过代理冒称通过、不把额度转给其它场景。原生 Responses 仍在本次最小窗口范围内。

18 处 G1 差异、P2 两次失败账本与 C1 末次 telemetry 附件缺口、上一轮 P3 两项 fixture 失败、原 Baseline 坏 raw/拒绝/附件缺口全部保留。集成评审发现的驱动合同问题及修复单列记账。没有改模型、引擎、生产代理、采样或 Pi medium/32768 预算。

## 下一次最小实机范围与预算

| 部分 | 固定预算 | 验证目标 |
|---|---:|---|
| Op/Graph | 10 个有限测试；136 场景；139 direct、130 capture、260 replay | SM89 实际数值、guard/state 与双 replay；0 模型加载/提交 |
| 原生三协议 | 12 客户端/模型请求 | 每协议 nonstream、stream、真实工具 replay、cancel |
| 原冻结代理 Chat/Messages | 4 客户端 + 4 上游 wire | 流式与真实工具 replay，nonce/SHA/canonical ID 关联 |
| 候选 telemetry | 2 GET | 前后资源与最终 drain |
| 恢复原服务 | 4 wire 单位 | health、代理推理及其上游、telemetry |
| 总计 | **22 候选 + 4 恢复 = 26 wire；16 模型提交** | 另 2 个代理 Responses 不发请求，保留阻塞 |

不含隐式 health/models、warmup、重试或备用请求。诊断输出上限 4096 不属于 Pi；服务默认输出 32768、context/KV262144、E8/MTP3/lm-head、T1/top_p.95/top_k20/presence0/medium 保持。容量不足停止并留证，不降低 context。

Op 阶段最多 900 秒，每个 exe 最多 180 秒；模型启动最多 180 秒；HTTP 阶段最多 900 秒，每个请求绝对截止 90 秒。窗口 **40 分钟硬上限，36 分钟开始恢复，至少预留 240 秒**。预计 **25–35 分钟**，这是按冻结目录、启动与请求上限给出的规划估计，尚无本轮 GPU 实测。故障可能令场景未执行；失败不自动追加额度。硬件或 Docker 无响应时软件不能保证物理恢复时刻，超时明确失败并继续尝试恢复。

这个窗口不含吞吐调优循环或配对性能统计，不提供正式 p95、长上下文/长期资源、完整 P2/P3 或生产发布资格。后续若要比较性能，须另冻结成对样本与预算，不能从本轮正确性目录推算收益。

执行与冻结接口见 [window README](../output/ninfer-v4-p3-driver-20261022/window/README.md)；V4 入口及任务清单见 [最小验证计划](ninfer-flare-v4-md-20261021/plans/09-p3-hardware-minimum.md)。

V4 一致性检查通过：396 份 Markdown、113 个实施任务、30 个门禁、373 条断言、16 个 scope；15 个内存负例均拒绝。340 份原 V4、288 份源 V3、192 份历史材料及 3 项 Baseline 交付哈希保持。新增计划没有改任何任务依赖或具名断言，文档校验不代替产品测试。见 [校验结果](../output/ninfer-v4-p3-driver-20261022/documentation-validation.json)。
