# 17 · 服务候选、切换与回退

## 1. 运行边界

本方案准备可审查发布候选，不自动授权改动现有服务。候选使用独立二进制、端口、模型目录、状态缓存namespace和配置。单卡性能比较按时间交错，不让NInfer、Strata和候选同时争用显存。独占窗口由实际执行会话解决，不擅自停生产。

主线默认single active generation、Vision Off。2–3个子代理的并发请求进入有界队列；并发2推理属于新profile，不从queue测试继承资格。

## 2. API与Pi协议

兼容真实Pi调用的messages、tool schema、tool_call_id、system prompt、reasoning配置、stop、SSE、取消和超时。确认Inkling的chat template/tool parser版本，不用“普通chat能回复”代替工具协议验证。

计时分开：排队、tokenization/prefill、first model token、first visible token、tool-call完整输出、工具执行、下轮prefill与总任务。reasoning tokens、visible tokens和tool argument tokens都计入资源，不只统计用户可见文本。

父代理在等待子代理时不得占有GPU generation slot。工具执行发生在已commit且完整验证的tool call之后；重试与网络重连使用明确request/tool idempotency策略，避免重复修改文件、执行构建或其他副作用。

## 3. 两级回退

| 级别 | 场景 | 回退目标 | 状态处理 |
|---|---|---|---|
| 同模型功能回退 | DSpark无益、图不可用、局部kernel失败 | 同一target契约的串行/通用CUDA | 从已commit前缀重建或恢复；不切换模型分布 |
| 服务代际回退 | 新模型质量/协议/稳定性不合格 | 已冻结的NInfer/Strata旧服务 | 重新渲染会话并prefill；不能把Inkling KV传给旧模型 |

last-loop、LoopCD、varloop改变了target身份，不能在同一已开始请求中无声明切换回另一分布并继续复用旧cache。必要时终止候选请求、保留已完成工具日志，由应用按明确恢复策略重试。

表中的功能回退不授权继续使用已经failed的executor/context。准入失败或无污染的spec禁用可原位处理；expert execution/CUDA错误必须按05退役context/必要时worker，在原预算内重建。移除budget不是回退；无法满足预算就明确失败。SV04必须覆盖这个负例。

## 4. 发布单位

一个release generation包含：源码commit、binary hash、编译环境、完整模型/草稿器锁、tokenizer/template、profile、cache format、能力矩阵、评测集hash、原始结果引用、回退目标和故障阈值。缺任何会影响结果的字段都不是完整候选。

镜像tag或分支名不是冻结版本。自动更新上游、hf main和环境依赖均关闭；升级重新跑影响范围内的资格测试。

## 5. 灰度前的演练

1. 在隔离业务fixture中测试进程退出、CUDA OOM、取消/断线、损坏session文件、超时、无效请求、磁盘不足。
2. 验证下一请求状态干净，失败日志可追，未commit文本不触发工具。
3. 使用本地路由/模拟流量验证回退目标、会话重建、重复工具动作防护和恢复时延。
4. 长时间运行按20的G6执行；至少记录资源基线、增长趋势、温度/频率与失败分布，不能只报告“72小时进程没退出”。

这些是候选验证，不等于生产灰度已发生。

## 6. 获得明确授权后的灰度步骤

首版使用排空后切换，不要求复杂热更。保存旧进程配置与启动命令；停止接新请求、完成/显式取消在途请求；启动新generation；执行小型健康/工具测试；按已同意的少量任务流量观察，再扩大。流量比例与观察时长在实际发布记录里冻结。

遇到任何错误工具动作、静默截断、跨会话污染、无法回滚的状态错误立即回退。若超时/失败率、p95或质量超过预先阈值，也按发布合同回退；不得边看结果边改阈值。

## 7. 回退演练记录

使用 [RELEASE模板](../templates/RELEASE.md)，记录触发原因、版本、活跃请求处理、恢复耗时、是否重复工具调用、数据损失/重算范围和后续处置。保留候选日志以供定位，避免回退后证据消失。

生产切换只在G0–G6相关能力通过、回退演练通过并有明确授权时进行G7。若新模型某项能力不如现有主线，则保留旧服务负责该类任务，而不是宣布全面替换。

## v2.0 · Pi/Java8可选观测与单GPU所有权

M03可增加被动InferenceObservation：queue/load/restore/prefill/decode阶段时间、实际命中/处理token及终止状态。默认token/tool/SSE合同仍由原服务负责，观察器不能把partial tool、EOF或进度done当成成功。慢观察器用有界队列/可丢弃指标，不阻塞或重排业务流；客户端abort不提前释放DMA引用，也不自动重试已可能产生副作用的工具。若未来运行Magnitude作异模型机制参考，必须使用同一全局GPU lease，与Atomic生成和KernelLab串行。MGX12–14不是额外生产功能的默认开关。[42](42_magnitude_integration.md)。
