# P3 Chat Completions 最小实机验收

**结论：P3_MINIMUM_CHAT_ONLY_NOT_PASSED。** Small-T 数值/Graph 的136场景全部通过；Chat Completions 六项为 **4 PASS、1 FAIL、1 INCONCLUSIVE**。原服务已经恢复并验活。没有为消除失败追加请求或重跑。完整 P3、性能及生产发布仍未资格。

按用户最新指令，当前支持及验收只要求 OpenAI Chat Completions。Messages/Responses 不再作为本范围的前置或阻塞，也不声明它们通过；原代理 Responses 缺口保留为历史证据。此次只收窄驱动和文档合同，没有删除现有协议处理代码或改动现网配置。

通过 `jssh 29`（`ssh -J jump 29`）执行。隔离源码树保持 `b3fc67df1a7fd3fbac318a3505b38c0d48a3beb2`；原 frozen bundle 未覆盖。工作目录 `/home/hhtele/ninfer-v4-p3-20261022/hardware/driver-v1-20261022`，版本化接续为 `scope-chat-v2`。原 Baseline、BO、G1、P1/P2/P3 已通过任务均复用。

## 实际范围与结果

10个原有测试的有限入口全部完成，原始 stdout 的目录、唯一 case、完整终态和零 failures 已重新解析并独立核对。按已执行冻结程序记账为 **136 场景、139 次直接语义 Op、130 次 Graph capture、260 次 replay**；这些是 Op/Graph 调用数，不是 CUDA profiler 的 kernel launch 数。没有放宽 oracle、容差、guard 或 state/reset 断言。snapshot 独立参考与 record 同实现对照的证据边界沿用原合同，AllowA8 标签不冒充 INT8 GPU 命中。

| Chat 场景 | 结果 | 原始观测 |
|---|---|---|
| native nonstream | FAIL | 工具名、调用结构和 JSON 合法，但解码后的 text 多出6个字面反斜杠，不符合逐字符输入要求；未执行错误工具输入 |
| native stream | PASS | 9个非空参数增量，拼接语义正确；首参数早于同机服务完成时间约230.947ms |
| native tool replay | PASS | 实际本地 SHA256 工具结果以真实调用 ID 回放，最终文本包含正确 hash |
| native cancel | PASS | 看到实际参数后取消，持久终态 cancelled、incomplete=1，无 completion export |
| proxy stream | INCONCLUSIVE | 9个逻辑参数增量且拼接正确，但首参数到达晚于服务完成时间约42.684ms，未取得提前增量交付资格 |
| proxy tool replay | PASS | 原冻结 shim 路径的实际工具历史与结果回放成功 |

非流式失败是实际语义差异，不是 JSON 展示转义：预期 UTF-8 长38字节，实际44字节。服务记录的 `tool_calls_invalid_arguments=0` 与此不矛盾：JSON 合法并不保证内容满足任务。一次 T=1 结果不能区分模型随机行为、输入表达或 P3 回归；未做旧 Baseline 重跑或配对归因。见 [解码差异](../output/ninfer-v4-p3-hardware-20261022/nonstream-input-diff.json) 与原件 `campaign/native-chat-nonstream/response.raw`。

代理观测不能改判 PASS，也不能仅凭−42.684ms认定缓冲根因。原 shim 的 SSE 循环使用 `resp.read(8192)`；它是后续离线排查线索。本次 native/proxy 分别收到246/140个 transport chunks，逻辑参数均9段；SSE 分段、到达时间和真实逐 token ITL 分开记录，ITL仍null。见 [逐项结果](../output/ninfer-v4-p3-hardware-20261022/case-results.json)。

六个候选请求的服务日志累计 P=4915、O=2280；其中 FAIL 的740输出 token 和 INCONCLUSIVE 的404输出 token 保留在分母与成本中。这是请求计数之和，不是唯一 token、正式性能样本或优化收益。

## 收窄范围与预算

原窗口于2026-10-22 15:26:19.871 UTC开始。用户收窄协议时，10个 Op 测试已通过，候选模型正在加载，HTTP、代理和观测请求尚未发出。控制器暂停后，模型于15:28:23.514 UTC达到监听就绪，在原180秒启动上限内。接续包经过3项新增 BO 无GPU/无网络合同检查和独立只读评审后，在同一窗口登记新 owner，再终止已撤回的旧控制器。复用同一已加载模型及全部 Op 结果，guardian、window ID和原2160/2400秒截止不变。

| 计账项 | 实际 | 原授权上限 |
|---|---:|---:|
| 候选客户端模型请求 | 6 | 最多16次模型提交范围内 |
| 私有代理上游 wire | 2 | 包含在候选上限 |
| 候选 telemetry GET | 2 | 包含在候选上限 |
| 候选 wire 合计 | **10** | 22 |
| 恢复 wire：health、代理推理及其上游、metrics | **4** | 4 |
| wire 总计 | **14** | 26 |
| 恢复推理 | 1次模型请求 | 无额外探测或重试 |
| Messages/Responses | **0请求** | 用户排除，不转移额度 |

候选6次模型请求、恢复1次推理分开计账；启动过程自身的 warmup 不另发 HTTP。按两次服务启动各一次内置 warmup 保守记账，共9次，仍在16次上限内；warmup计数来自源码和启动过程，不伪装成新增HTTP记录。诊断请求 O4096 与 Pi medium/32768 无关。模型、codec、context/KV262144、E8/MTP3/lm-head、T=1/top_p≈0.95/top_k20/presence0和服务默认输出32768保持。候选使用私有缓存和日志，没有缩 context、改采样或重载候选模型。

## 恢复与证据

**RESTORED_AND_PROBED。** 恢复于原窗口第470.492秒开始，第577.828秒完成，最终控制器计时577.832秒，即 **9分37.83秒**。包含范围收窄、离线检查和接续准备，不是纯推理或 GPU 性能耗时。第36分钟恢复边界和40分钟硬上限均未触及。

恢复的是同一原容器 `86cb6d9ae734…`、原镜像 `sha256:e753e228…`、原 argv/binds、原缓存路径及 device/inode，二进制和启动/代理脚本 SHA 相同。新服务 PID **77758**；原代理 PID **1950**、start/argv/listening inode连续。4个恢复 wire 全部完成；health、代理推理、metrics三个客户端响应均200，推理生成16 tokens，processing/deferred均0。11个候选容器均已退出，未结束候选请求0。

196份原件已冻结并逐文件核对 size/SHA，远端归档在 `/home/hhtele/ninfer-v4-p3-20261022/hardware-delivery-chat-v1`。归档 SHA256为 `835787d3ef0b4fe1e1f1ec637b2e90ec9785932feee567a8f5581f5f50f3a581`。本地 [收集回执](../output/ninfer-v4-p3-hardware-20261022/remote-delivery/collection-receipt.json)、[不可变原始归档](../output/ninfer-v4-p3-hardware-20261022/remote-delivery/evidence.tar.gz)、[文件清单](../output/ninfer-v4-p3-hardware-20261022/remote-delivery/evidence-manifest.json) 和 [Op原件核验](../output/ninfer-v4-p3-hardware-20261022/ops-raw-validation.json) 完整保留。

独立审计复核了原始参数解码、SSE、真实工具回放、取消终态、预算、完整性及恢复原件，支持上述未通过结论，未发现新增交付阻塞。审计者没有执行 GPU、HTTP 或远端操作。版本化接续中发现的 `/proc` 消失竞态已在执行前修复；新范围测试首次函数名定位错误另记为测试编写失败，仅有工具对话记录，不伪造原始日志附件。

18处 G1 差异、P2两次失败和C1附件缺口、旧P3 fixture失败、原 Baseline 坏 raw/拒绝/缺失附件、原代理 Responses 缺口均保留。当前需要闭合的是 Chat 非流式语义失败归因与代理提前增量资格；其它接口不再是当前必需支持项。没有基于此次有限功能样本声明 p95、性能收益、完整P3或生产发布通过。

V4 [中央支持合同](ninfer-flare-v4-md-20261021/design/09-chat-completions-only-scope.md)、执行入口、任务说明和预算已同步。文档校验通过：397份MD、113任务、30门禁、373断言、16scope、15个内存负例全拒绝；原节点/依赖/断言原文、340份原V4、288份源V3、192份历史材料及3项Baseline交付SHA保持。见 [最终汇总](../output/ninfer-v4-p3-hardware-20261022/final-summary.json)、[独立审计](../output/ninfer-v4-p3-hardware-20261022/independent-audit.json) 与 [文档校验](../output/ninfer-v4-p3-hardware-20261022/documentation-validation.json)。
