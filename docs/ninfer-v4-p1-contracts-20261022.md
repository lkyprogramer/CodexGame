# P1 观测、缓存和故障合同补证

已在 29 的隔离分支完成本轮源码修复、定向 CPU 补证和集成代码评审。最终树为 `663fd45930bb1160f60abe1396d000ea596f5262`。本轮 8 个 native 测试目标全部通过，随后仅为新增 guard 终态序列化断言重跑 request-log，并为 fatal/shutdown 清理加锁重建服务与复测 round-fault 目标，均通过。两个独立评审均复核到最终树，剩余可行动 finding 为 0。

这关闭本轮可在源码/CPU层证明的部分；完整 P1-GATE、真实 GPU 状态恢复及 HTTP/代理传输尚未资格。没有重跑旧 Baseline、模型任务、grader 或旧 G1。现网、采样参数和 Pi medium/32768 未变。

[完整补丁](../output/ninfer-v4-p1-contracts-20261022/P1-PATCH.diff) · [相对上一版 P1 的增量补丁](../output/ninfer-v4-p1-contracts-20261022/P1-CONTRACTS-DELTA.diff) · [源码快照](../output/ninfer-v4-p1-contracts-20261022/P1-SOURCE.tar) · [执行账本](../output/ninfer-v4-p1-contracts-20261022/execution-status.json)

## 实际修复

| 边界 | 原问题 | 修复与证据 |
|---|---|---|
| Stable alias | 先准入竞争 payload 再检查 owner；单 image 的 L2 容量下，竞争者可能驱逐原 owner 并夺取 write-once alias | 同锁内先核验存活 owner，再准入；保留同 ID 幂等、过期释放与 pin 规则。单 image 压力用例先失败后通过，另验证准入失败不发布 alias、session/stable 共用一个 payload |
| RoundFault | 外层 catch 已释放执行锁；恢复还会终止本轮之外正在 prefill 的健康请求 | 捕获收窄到持锁 decode 包装内，清理只接收原 round 的 lanes；保留健康 prefill、request-memory 和 admission protection；非 RoundFault 仍进入 fatal 路径，fatal/shutdown 清理自身也取得执行锁 |
| 观测版本 | 定制和上游都存在 core schema20，只有无版本的 prepare_detail 无法声明独立 producer 合同 | 增加 `extensions["lkyprogramer.prepare_detail"]` version=1、seconds/utf8_bytes 单位；保留六个原 timing 字段及媒体 tokenize=-1 未知约定，不提前升到 schema24 |
| Responses 终态 | failed 后仍可生成 in_progress 和内容 delta | failure 同时封闭 finish 状态；失败后不再发进度/内容，重复 terminal 被拒绝。原失败用例保留 |

没有改变 greedy proposal、Target sampling、codec、模型、Pi 预算或现网默认参数。新增 round helper 是实际生产 decode 异常分派路径，不是另建一个模拟 executor。

## 合同与执行证据

| 合同 | 本轮证据 | 明确边界 |
|---|---|---|
| T04 三协议 body/prepare | 实际 native parser → Responses history compose → request-log serializer；UTF-8 byte count、body_bytes 不随历史展开膨胀、六字段、扩展版本/单位、未知媒体值、日志不输出 prompt | HTTP owners 的 req.body.size 赋值已追踪；没有用这些 unit 检查代替真实 HTTP/compat proxy |
| T04 TimerIdentity | 原前端、prefix identity、G1 和 legacy reference 的 21 个相关源码路径与上一版逐字节一致；复用 BO/此前 CPU/G1 证据 | 本轮没有重新运行 G1；旧 real18 的严格 FAIL 与全部历史原始材料仍保留 |
| T05 alias/payload | 实际 ContinuationCache 的压力、幂等、过期、拒绝、typed kind、CAS/持久化与 payload 去重检查通过；显式模式仍传递 routing hint | 实际 GPU L1/L2 restore 与 adapter 状态隔离仍需实机，CPU 不授予这些资格 |
| T06 guard/row/终态 | 复用并定向运行 committed guard 和 row licensing；新增实际 log、Chat、Messages、Responses 的 RepetitionCycle 映射及 usage 不增加断言 | 没有通过改采样或修改 97fc7be6 输出获取通过；不宣称该历史行为异常已被实机修复 |
| T06 progress | 实际 ResponsesEventStream 的序号、prefill counters、无伪造输出/usage、单终态、失败后封闭检查通过 | 未执行真实长 prefill HTTP/SSE；到达的 progress 不是首输出 token |
| T06 故障边界 | 实际生产分派 helper 验证正常/仅 RoundFault/其他异常、原成员传递及调用者持锁；集成评审追踪 worker → Program validation/commit → abort | 不证明实际 Program/KV 回收、健康 prefill 继续或排队请求完成；这些列为剩余实机项目 |

本轮 GREEN 的 8 项为 request_log、responses_schema、continuation_cache、round_fault、repetition_guard、row_commit、continuation_candidate_selection、response_store，JUnit 零 failure/error/skip。CLI 与服务端增量构建、`--help` 通过。[r6 原命令与结果](../output/ninfer-v4-p1-contracts-20261022/contracts-r6-green/status.json)和[r7 仅 request-log 增量结果](../output/ninfer-v4-p1-contracts-20261022/contracts-r7-serialization/status.json)均保留。不是把旧 18 项与本轮重复目标相加，宣称一次新全量通过。

r4 新测试第一次编译因 rvalue API 调用不正确停止，该失败完整保留，不算功能 RED。修正 fixture 调用后的 r5 实际复现日志版本、SSE 终态和 stable alias 三个回归；r6 全部 GREEN。r7 只有 request-log 测试增加 10 行，仅重建/重跑该目标。最后核对发现 fatal/shutdown 清理仍需同一执行锁，r8 只增加这一行锁；重新构建 CLI/服务并复测 round-fault，结果通过。最终两个评审均复核锁顺序与调用点，未发现反向锁序或重复加锁。没有通过删断言、改旧 golden 或重复整套矩阵获取通过。

## Standards

独立评审最初发现 2 项：故障恢复范围/锁边界，以及 stable alias 压力下的归属问题。源码修复后复核没有剩余 finding，最终测试增量也已复核。评审者未运行测试或 SSH；测试结果来自主执行器。[初评](../output/ninfer-v4-p1-contracts-20261022/review-standards-initial.md) · [最终复核](../output/ninfer-v4-p1-contracts-20261022/review-standards-final.md)。

## Spec

独立评审分别记录故障锁、故障成员范围、stable alias 共 3 项，均已源码闭合；观测扩展、失败终态及最终 RepetitionCycle 测试增量未发现新增阻断。实际 Program/KV/HTTP 边界明确保留。[初评](../output/ninfer-v4-p1-contracts-20261022/review-spec-initial.md) · [最终复核](../output/ninfer-v4-p1-contracts-20261022/review-spec-final.md)。两轴结论分别保存，不把重复发现计成两个不同缺陷。

## 剩余实机验证的最小范围

建议只跑当前 P1 新合成夹具，不重放旧 Baseline/Pi/编程题；采样保持当前 T=1/top_p=.95/top_k=20。该计划尚未执行，也不构成 GPU 服务切换授权。

| 集合 | 最小范围 | 上限 |
|---|---|---:|
| 观测/真实传输 | 三协议 stream/nonstream，Responses parent/child 展开，以及隔离 compat proxy；包含一条新长 prefill 的 progress-only/终态检查 | 8 个 HTTP 请求 |
| GPU cache | L1 warm、强制 L2 roundtrip、explicit+session routing、system/tools 改变后的安全 miss | 10 个 HTTP 请求 |
| 生命周期探针 | 取消、故障后的新请求与排队接续；核查终态唯一及槽位/资源可继续使用 | 6 个 HTTP 请求 |
| 统一预留 | warmup、负例、资源/漂移确认；LoRA 需已存在合格 adapter 才可用其中额度补测 | 最多 8 个 HTTP 请求 |
| 实际故障 native fixture | ragged/许可错误恢复、健康 prefill 与 queue 隔离、guard/取消后的提交与释放、非 RoundFault fatal；同时观察真实 Program/KV 和公开查询锁边界 | 4 个场景，各 1 次，合计最多 12 个 Engine admission；GPU 总时限 20 分钟 |

因此上限为 **32 个 HTTP 请求 + 4 个 native 场景（最多 12 个 Engine admission）**；native 开销单独记账，不藏在 HTTP 数中。准备、失败和重试占用同一额度；未知结果先 drain，不自动重发或超额。实际故障注入 driver 尚需补齐，不能把现有 helper 测试标成实机 driver 已就绪；注入仅放在隔离测试驱动，不增加现网开关。

C1 验证沿用当前容量；混合 prefill/decode 的故障隔离需要单独声明 C2 诊断 profile，在相同 context/KV 与采样下做启动容量预检。若不具备空间就保留缺口，不能静默缩容量、输出或改变采样以运行。无合格 adapter 时不宣称 LoRA 实机隔离通过。旧 48+16 是更宽 P0 诊断规划，不在本轮或这份最小 P1 smoke 中自动重跑；将来共用证据时请求只计一次。

预计补齐并冻结真实 driver **1–2 小时工程时间**；启动、上述实际验证与取证约 **1.5–2 小时 GPU 窗口**，整体预留 **3–4 小时**。这是按限定短夹具、新长 prefill 和显式超时估计的预算，不是已测工期、速度收益或完整 P0–P6 工期。32 次请求不足正式 p95，继续 `p95=null`、`optimization_qualification=false`。

本轮只读 `nvidia-smi` 观察到生产占用 22598/24564 MiB；不能假定还能并驻第二实例。保持不动现网的边界，需要独立 GPU，或后续另行授权的独占/恢复窗口。本轮没有停止或重启生产服务。

## 身份、保全与交付

远端仍为 `/home/hhtele/ninfer-v4-p1-20261022/source`，分支 `codex/p1-frontend-cache-20261022`。HEAD=O、MERGE_HEAD=U10，未创建 commit/tag/PR 或推送。完整补丁相对 O、增量补丁相对旧 P1 树都已在新临时副本重放，得到同一个最终树；[重放回执](../output/ninfer-v4-p1-contracts-20261022/patch-replay-validation.json)可复核。43 项定制责任全部保留。

最终生产容器 ID/image/PID/启动时间/参数和 CLI/serve/启动脚本/代理 SHA 与此前一致；旧 BO 源码仍 clean。所有运行在无网络、无 GPU 节点、无模型挂载的固定 BO 工具链容器中，复用既有 build。原失败和两个独立评审均保存，18 处 G1 差异未覆盖。[身份检查](../output/ninfer-v4-p1-contracts-20261022/final-state-validation.json)。

推进活动文档入口前已核验上一交付的 491 个文件，并把其 383 份活动 Markdown 原字节封存到本轮 `v4-before-contracts.tar.gz`。旧交付的 SHA 清单描述当时活动文档；当前入口前移后，以该封存快照复核历史版本，不修改旧回执冒充当前校验。旧报告/源码/补丁/原始记录不改写。[保全回执](../output/ninfer-v4-p1-contracts-20261022/prior-delivery-preservation.json)。
