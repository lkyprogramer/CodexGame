# P1 最小实机验证与验收结论

**结论：4 个真实 native 场景全部 PASS；本轮 P1 整体验收暂不通过（代理环境证据缺口），完整 P1-GATE 仍 UNQUALIFIED。原生产服务已恢复并验活。** 两次隔离代理请求因固定端口 28343 已占用而返回 nginx 401，未到达预期兼容代理；不能算 NInfer 模型失败，也不能算代理资格通过。没有追加请求获取通过。

本轮没有重跑旧 Baseline、Pi、编程题或 grader。T=1、top_p=.95、top_k=20、presence=0、生产默认输出 32768 保持；没有实施新 greedy proposal / Target sampling、kernel 或 codec 优化。旧 18 处 G1 严格差分仍保留，不改 golden 或分母。

## 已交付与身份

隔离分支 `codex/p1-frontend-cache-20261022`，最终树 `06dc421059087f9c614e0245702c05a8dead49e3`。HEAD=O、MERGE_HEAD=U10，未创建提交、tag、PR 或推送。复用此前 [P1 源码/CPU/集成评审](ninfer-v4-p1-contracts-20261022.md)；此次增量是实际 Program 驱动及仅属于独立 native executable 的注入点。普通 CLI/服务不包含注入入口，正常二进制 SHA 在 driver 增量前后相同。

[完整补丁](../output/ninfer-v4-p1-hardware-20261022/P1-PATCH.diff) · [driver 增量](../output/ninfer-v4-p1-hardware-20261022/P1-HARDWARE-DRIVER-DELTA.diff) · [源码快照](../output/ninfer-v4-p1-hardware-20261022/P1-SOURCE.tar.gz) · [补丁重放](../output/ninfer-v4-p1-hardware-20261022/patch-replay-validation.json)。补丁在 O 的新临时目录重放得到同一树。

固定 BO 工具链镜像 `sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`；SM89 / CUDA 13.2 / 27B Release。最终执行 `cmake --build /build --parallel 4 --target ninfer_p1_native_driver ninfer ninfer-serve`、native `--help`、普通服务注入字符串隔离检查，全部通过。[原始构建记录](../output/ninfer-v4-p1-hardware-20261022/hardware-build-r5/status.json)。最初三个驱动构建的 include 配置错误均保留，属于构建夹具失败，不当成功能 RED。

## 实际预算与耗时

| 项目 | 实际 |
|---|---:|
| HTTP 预算账本 | **32 / 32** |
| 客户端实际 HTTP 请求 | 28，含两次 401 |
| 保守计入的代理上游额度 | 3，失败代理未退回预留 |
| 发连接前的脚本失败 | 1，仍占额度 |
| native 场景 | **4 / 4，各执行一次** |
| Engine submit 尝试 / 实际 admission | **12 / 11**；fatal 场景的 C 在队列中失败，未 admission |
| native 合计 wall（含四次模型加载） | 434.53 秒，低于 20 分钟 |
| 独占/恢复窗口 | **11:54:07—12:05:35，11 分 28 秒**，Asia/Shanghai |

首次预检因 Python 模块名 `http` 被同名函数遮蔽，在构造连接前失败；原容器当时仍 PID2037。保留 [r1 原现场](../output/ninfer-v4-p1-hardware-20261022/evidence/pre-wire-failure-r1/window-failure.json)，核对旧 controller/guardian 已退出及唯一 reserved row 后，仅修复驱动命名、版本化接续。没有重发未知模型结果。后续没有 HTTP 重试、native 重跑或超额。

每条实际 HTTP 的原 body/raw/headers/status/SHA 都在 [HTTP 原记录](../output/ninfer-v4-p1-hardware-20261022/evidence/http/)；[预算/进程账本](../output/ninfer-v4-p1-hardware-20261022/evidence/state.json)、[离线逐条审计](../output/ninfer-v4-p1-hardware-20261022/http-analysis.json)、[测量 CSV](../output/ninfer-v4-p1-hardware-20261022/http-metrics.csv)可复核。

## 真实 HTTP 与缓存

| 范围 | 结果与可支持的结论 |
|---|---|
| 原生 Chat / Messages / Responses，stream 与 nonstream | 均 HTTP200；完整 stream 的唯一终态通过。Responses parent/child 实际展开，24,636 prompt tokens 的新长 prefill 有 progress 事件 |
| 观测合同 | 19 个候选模型请求的实际 body_bytes、resolved sampler 与日志对应；已返回 outcome 的六个 prepare_detail 字段及版本扩展通过。复用 CPU 证据证明其 UTF-8/未知值语义 |
| L1 warm | 6,171 prompt tokens 命中 6,169，实际 source=l1 |
| L2 路径 | 显式 erase 后观察到 source=l2、恢复 11-token 公共前缀及约 148 MiB 状态；**未证明完整 6,171-token 长前缀 L2 roundtrip**。erase 是删除操作，不是无损驱逐，不能以该夹具名推导完整命中 |
| explicit + routing | 实际 routed_session alias、命中 3,085 tokens |
| system / tools 改变 | 均 full_reset、cache hit=0，未错误复用旧上下文 |
| 取消与接续 | Chat 断开后记录 cancelled，新请求完成；Responses 断开后记录 Request was cancelled，新请求完成；并发请求均完成，最终 processing/deferred=0 |
| 隔离兼容代理 | **未资格**。复制的原代理因 28343 bind 失败退出，端口原有 nginx 返回 401；两次失败完整保留，未重试 |

模型请求按唯一 request ID 计为 19：18 条 request_done、2 条 request_error；Chat 断开同时有 cancelled outcome 与传输断开 error，不能把它们计作两个模型请求。所有 start ID 均可在 done/error 找到，结束时无未决请求。完整 stream 的终态断言与故意断开场景分开，未声称断开的客户端收到终态。

这些是功能路径证据与单次观测，不能当配对速度收益或正式 p95。LoRA 未实测，无合格 adapter；HTTP 使用原 C1/vision=false，native 使用独立 C2/C1、raw-token、enable_vision=true 诊断 profile，不授予完整 HTTP C2/视觉资格。

## 4 个 native 场景

使用真实 decode_batch、真实 Program resolve/abort 与槽位/临时内存生命周期，没有 fake Program。场景 1/2/4 在注入点记录并断言 A=1 正在 decode、B=2 正在 prefill、C=3 仍在 pending。

| 场景 | 实际结果 |
|---|---|
| 1 ragged RoundFault | A 返回真实 ragged-layout 错误；B 完成 4 tokens、C 完成 8 tokens；PASS |
| 2 Program commit 许可错误 | 真实 Program 拒绝 committed 0 / produced 4；B/C 正常完成；PASS |
| 3 guard / cancel / capacity reuse | 真实 Program 返回 RepetitionCycle；下一请求 Cancelled；新请求完成 4 tokens；PASS |
| 4 非 RoundFault fatal | A/B/队列 C 均返回指定 fatal 错误；PASS |

四场均清理后 request_transient.used_bytes=0、槽位无 processing/retained，容器 exit0。场景 1/2/4 另有公开 memory_summary 查询完成证据；只证明此次查询无死锁，不是锁竞争压力或性能资格。[四场原始结果](../output/ninfer-v4-p1-hardware-20261022/evidence/native-1-result.json)及相邻 native-2/3/4-result.json 保留完整事件、实际 admissions、退出码与 wall。

场景 3 使用明确的**合成 guard-latch 注入**；真实 GPU token、logits、RNG、采样参数不改。它证明 guard 触发后的许可终止/资源复用，不证明自然循环检测概率、97fc7be6 已解决或模型质量改善。

## 评审与恢复

Spec 独立评审关闭了“C 最终成功但可能在故障前已离队”的证据缺口；Standards 独立评审关闭启动/停机与恢复 race、孤儿容器发现、未知 probe 重发、SSE 截断误判等问题。最终静态复核无剩余阻断，评审者没有独立执行 SSH/GPU。[预检接续复核](../output/ninfer-v4-p1-hardware-20261022/review-standards-prewire-recovery.md)与[最终原始证据离线复核](../output/ninfer-v4-p1-hardware-20261022/review-spec-evidence.md)另行保留。[Spec](../output/ninfer-v4-p1-hardware-20261022/review-spec-final.md) · [Standards](../output/ninfer-v4-p1-hardware-20261022/review-standards-final.md)。

只停止原 GPU 容器，保留原 proxy/systemd MainPID1950；验证后原地启动同一 ID `86cb6d9a…`，没有调用会删除容器的旧 stop 脚本。恢复镜像仍 `sha256:e753e228…`；CLI/serve SHA、全部原参数/挂载、缓存目录 inode/device、启动/代理脚本 SHA 均核对一致。原容器新 PID39134，所有五个候选容器已停止，controller/guardian 已退出。

原健康检查、原代理 `/v1/models`、新推理、最终 metrics 均 HTTP200；processing/deferred=0，systemd active/running，GPU 为原服务占用约 22.6 GiB。[恢复回执](../output/ninfer-v4-p1-hardware-20261022/evidence/restoration.json) · [最终实时身份核对](../output/ninfer-v4-p1-hardware-20261022/final-live-validation.json)。原缓存目录保留；重启后的内存缓存需要重新预热。

## 最终资格边界

本轮执行已结束，**最小实机范围为部分通过，代理环境与完整长前缀 L2 证据仍有缺口；不发 P1 整体 PASS**。这不是把两个环境 401 当模型质量失败。剩余工作是修正代理端口归属/readiness，以及以无损驱逐替代 erase 的长前缀 L2 夹具，再补这两项窄证据；不应再跑四个 native、旧 Baseline、旧题或 grader。建议后续单独冻结最多 14 个 HTTP 计账单位、0 native：idle 1、两次代理请求含上游 4、长前缀 A→B→A 3、候选末态 1、恢复 5。驱动准备约 30–60 分钟，GPU 窗口约 10–20 分钟；这是未执行的估计，不是追加授权。本次端口/readiness 与 erase 夹具选择属于驱动问题，未把它们归咎于模型。完整 P1 还保留原 G1 严格差分、未授权 merge-ancestry 与统计/未启用业务资格，不在此次预算中假装关闭。

`p95=null`，`optimization_qualification=false`，P6/生产发布未资格；P1 候选没有留在现网。最终 [机器账本](../output/ninfer-v4-p1-hardware-20261022/final-summary.json)和原始失败一起交付。推进入口前的 383 份活动文档已原字节封存到本轮 v4-before-hardware.tar.gz，历史 Baseline/BO/G1 原件未改写。
