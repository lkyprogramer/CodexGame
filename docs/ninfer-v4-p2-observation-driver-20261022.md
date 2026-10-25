# P2 请求/job 导出关联与实机驱动交付

本轮已完成无需切换 GPU 服务的部分：请求/job 关联、真实 native 与 HTTP 驱动、隔离构建、必要主机验证和两路集成评审。评审发现项均已修复。真实 GPU 场景及 HTTP 流量尚未运行，完整 P2-GATE 仍为 UNQUALIFIED；本轮没有性能收益或生产发布结论。

直连 `ssh 29`，在 `codex/p2-async-export-20261022` 完成修改。远端源码 `/home/hhtele/ninfer-v4-p2-20261022/source`、构建目录 `/home/hhtele/ninfer-v4-p2-20261022/build`；本机镜像源码 `/tmp/ninfer-v4-p2-20261022/source`。最终树 `4c58698eda334ad3fc2c27c4fc22fc8c08dabbcc`，HEAD 仍为 O，MERGE_HEAD 为 U11，没有创建提交、push 或发布。

[相对上一轮 P2 的补丁](../output/ninfer-v4-p2-observation-driver-20261022/SUPPLEMENT-from-P2.patch)、[相对 O 的完整补丁](../output/ninfer-v4-p2-observation-driver-20261022/FULL-from-O.patch)、[源码快照](../output/ninfer-v4-p2-observation-driver-20261022/candidate-source.tar.gz)、[执行账本](../output/ninfer-v4-p2-observation-driver-20261022/execution-status.json)。两份补丁均已在独立临时 Git index 重放，得到相同最终树，见[重放回执](../output/ninfer-v4-p2-observation-driver-20261022/patch-replay.json)。上一轮 [P2 原报告](ninfer-v4-p2-20261022.md)及 63 项证据 SHA 保留。

## 实现与观测边界

`GenerationHandle::request_id()` 直接暴露 executor 的真实 request ID；serve 在 handle 仍有效时记录该 ID。沿用现有 publication sequence 作为 job ID，不新增 ID 权威。`request_done` 保留 lane、digest 和 export job ID，后台 `continuation_export` 终态通过 `(server_instance_id, job_id)` 连接，并核对 request ID、lane、digest。

现有 publication worker 在源 reader 释放后发出事件，分别记录 copy、session alias、boundary alias 的结果。被合并替代的 job 仍由同一 worker 释放 reader 并发出 Superseded，不在请求线程回调；没有新增 worker。回调在执行锁、队列锁和稳定状态锁外运行，异常只计入 observer failure，不改模型或发布结果。观察者必须比 Engine 活得久，server 的构造/析构顺序满足这一点。

schema20 和六项 `prepare_detail` 含义保留，以版本化扩展标识 P2 producer。normalizer 支持完成事件先于或晚于 request_done、请求重叠、失败与 superseded；保留原 raw SHA/行号，拒绝重复 job、冲突身份和非法时间顺序。缺失为 null+原因，失败成本保留，不把全局 export work 平摊给请求。

这些时间戳是 host steady clock。它们不等于 CUDA elapsed、真实逐 token ITL、完整 round wall 或 L3 fsync；segment bytes 不含 image framing。真实 GPU 顺序和观测开销尚待实测。

## 真实驱动与评审修复

新增 `ninfer_p2_native_driver`，链接带编译期测试 hook 的独立 Engine 翻译单元。普通 CLI/server 无法启用这些 hook。驱动调用真实模型、Program、CUDA stream、后台 D2H、slot 和 L3；本轮只构建并运行离线 `--describe`。

四个新增场景为：真实 fence 与源复用阻塞；同步/后台 image 逐字节一致、slot 与重启后的 L3 frontier 恢复；实际 D2H 后、alias 前受控故障及取消后下一请求恢复；Engine 析构等待 export 排空。故障场景不是 CUDA 传输错误证明。每场景只运行一次，共至多 7 次模型提交、5 次模型加载，不发 HTTP，不重跑 P1 的四个已通过场景。

`tools/bench/merge/replay_agent.py` 的 `--run` 是真实有限 HTTP 客户端。它校验候选 PID/ELF SHA、启动身份、argv、私有路径和监听 socket 归属，并在每次连接前复核同一 socket inode。只访问私有端口 18041/18043，不能启动或停止服务。发连接前持久计账，保存 body/raw/终态/关联；失败或未知结果停止，无自动重试或隐式续跑。

[独立评审记录](../output/ninfer-v4-p2-observation-driver-20261022/integration-review.json)分 Standards/Spec 两路。修复内容包括：copy 前再次确认延迟 fence 仍 pending，过期夹具记 INCONCLUSIVE；L2/L3 必须恢复完整 frontier，不能以浅命中通过；每个必需请求须有唯一完整 job 和成功 session alias；绑定客户端与 normalizer 两个 SHA；每次连接重新证明监听 socket 属于候选进程。最终无剩余确定性 finding。评审者只读源码，没有执行构建或 GPU 测试。

## 实际验证与证据复用

固定 BO 镜像 `sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，CUDA13.2/SM89/27B Release。容器 runc、network=none、源码只读，无权重挂载、不暴露 GPU。CLI/server 与新 native 驱动构建成功；三次相关编译合计约 12 分 36 秒，包含公共类型变更触发的重编译，不能作为性能收益或完整工程工时。

5 个受影响 CTest 目标通过：`ninfer_request_log_test`、`ninfer_public_api_test`、`ninfer_serve_metrics_test`、`ninfer_async_export_metrics_test`、`ninfer_p2_replay_driver_test`。其中最终 Python 用例为指标 10 项、客户端合同 8 项。最终增量只复测变动的客户端并重编 native，其余复用同轮未变代码的通过结果。

精确命令、stdout/stderr/JUnit 见 [r3](../output/ninfer-v4-p2-observation-driver-20261022/observation-driver-r3/status.json)、[r4](../output/ninfer-v4-p2-observation-driver-20261022/observation-driver-r4/status.json)、[最终 r5](../output/ninfer-v4-p2-observation-driver-20261022/observation-driver-r5/status.json)。还通过 CLI/server `--help`、native `--describe`、Python 编译和 C1/C3 离线计划检查。测试没有打开真实 HTTP 连接。

[复用与保留核查](../output/ninfer-v4-p2-observation-driver-20261022/reuse-and-retention.json)：43 项定制责任中 35 项相对上一轮 P2 字节不变，8 项仅扩展观测或测试；前端/tokenizer/oracle/comparator 和 P1 场景源码未改。4 份 G1 raw SHA 保持原值，真实 G1 的 18 处严格差分仍为 FAIL。B29 的 278 项、8+2 编程题、BO、P1 证据均复用，没有重跑旧 Baseline、题目、grader 或已通过 GPU 任务。

## 剩余最小实机范围、预算与耗时

| 范围 | 冻结预算 | 目的与边界 |
|---|---:|---|
| 新 native 场景 | 4 场景、≤7 submit、5 次模型加载 | 真实 CUDA 顺序、逐字节 image/L3、故障恢复、shutdown drain；每场景至多一次，硬截止 240 秒 |
| C1 候选 HTTP | 12 请求 | health/telemetry、冷 A/B、L2 warm A、append/rewrite、slot save/erase/restore、cancel、末尾 telemetry |
| C3 候选 HTTP | 8 请求 | health/telemetry、冷 A、重叠冷 B/热 A、rewrite、cancel、末尾 telemetry |
| 原服务恢复探测 | ≤4 wire 计账单位 | 计入同一窗口，包含必要代理上游转发；不另开隐藏额度 |
| 总 GPU 窗口 | 预计 20–40 分钟，硬上限 40 分钟 | 每个 HTTP profile 外层 600 秒；预留恢复时间至少 4 分钟，不等耗尽硬时限才开始恢复 |

候选 HTTP 合计硬上限 20，共享持久 ledger；加恢复探测总上限 24。readiness、warmup、失败和发连接前未知成本均计账，不能按 profile 重置。native 独立记账，不藏在 HTTP 数里。C3 首先在同总 KV/显存预算下做容量预检；若不能容纳，记 BLOCKED/INCONCLUSIVE，不缩 context、不增上限、不重发未知请求。

保持 E8、context/KV262144、MTP3/optimized head、T1/top_p.95/top_k20/presence0。native 诊断的 O8/64 是新增夹具，不是 Pi 任务；Pi medium/32768 及生产默认不变。候选 cache/log/slot 路径限定在隔离 `hardware` 根，C1/C3 分 namespace。实机 launch 使用 host network 和相同绝对路径 bind mount，以便 PID 与 socket 归属核验。

20–40 分钟参考既有 P1 加载、L2 与恢复耗时及本次驱动的 5+2 次加载安排，是条件估计。该窗口只提供最小功能与生命周期证据，不提供正式 p95、长时间 allocator 泄漏证明、配对观测开销或完整 P2 性能资格；这些不足照实保留，不能改成 PASS。当前没有已知的源码/主机验证阻断，下一项是上述实机窗口；本轮未执行。

## 现网与交付状态

[最终只读核查](../output/ninfer-v4-p2-observation-driver-20261022/final-live-validation.json)确认：原生产容器/镜像、PID40985、启动时间、两二进制 SHA、完整 args 和缓存挂载未变；代理 MainPID1950、active/running。没有发送验活或推理请求，所以不声称本轮重做了推理验活；P1 原恢复验活证据继续适用。本轮 HTTP/模型请求和 native GPU 运行数均为 0。

V4 [执行入口](ninfer-flare-v4-md-20261021/AI_EXECUTION_PROMPT.md)、[注册表](ninfer-flare-v4-md-20261021/plans/02-task-registry.md)、[T03](ninfer-flare-v4-md-20261021/plans/tasks/P2-T03.md)、[T04](ninfer-flare-v4-md-20261021/plans/tasks/P2-T04.md)和预算已同步。原 386 份活动文档另有改前快照，历史 V3/V4、全部 373 条断言、原完整验收与发布门禁保留。请求/job 关联已具备源码与 host 证据，实际 GPU/HTTP 资格、UpstreamAncestry 与发布仍未通过。
