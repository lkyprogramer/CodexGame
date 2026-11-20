# 05｜核心数据模型与可计算的测量口径

状态：PROPOSED，待 P1/P2 实施。旧 REQUESTS/WINDOWS/DEPENDENCIES 为兼容主记录，新事件为 sidecar 附件；不强改旧档，不建立第二个控制器。实际上游字段名和语义以 [04](04_STRATA_METRICS_AUDIT.md) 为准。

## 1. 四个层次不得混淆

| 层 | 回答的问题 | 记录归属 |
|---|---|---|
| Harness/task | 真任务从什么时候可运行，何时模型调用/工具调用，何时答案正确 | task/turn/child/attempt 与 client 单调时钟 |
| HTTP/service | 收到请求、渲染准备、服务排队、加载、交给引擎、SSE发送 | server instance/request 与 server 单调时钟 |
| Native/engine | 执行哪个 leg/slot/epoch、cache 状态、读了多少、每轮提交了多少 | engine process epoch/leg/slot/round |
| Device/resource | GPU kernels/copies/events、CPU worker、SSD/DRAM、真实依赖 | context/stream/correlation 与独立时钟映射 |

server 活跃记录是短期环；不能仅靠反复轮询猜一个已经结束的请求归属。指标摘要是投影，事件日志才是本次完整性依据。

## 2. 最小身份闭包

每个 run 绑定：

- 仓库 commit、dirty diff hash、source tree、构建开关/compiler/CUDA、binary SHA256、release tar digest、实际 INFO build；来源不同就分别记录，不相互代填。
- host/GPU UUID/compute capability、CPU/NUMA/内存/PCIe 实际 link、驱动、有效 power/clock 与共存进程摘要；只有有授权的现场读取才是 OBSERVED。
- 模型每分片内容 hash、GGUF architecture/quant、tokenizer/template、draft/MTP、KV codec/layout、会话缓存、有效 argv/env；意向配置与 resolved 配置分栏。
- PID + process_start + engine_epoch + server_instance；PID 单独不唯一。
- corpus/gold/rendered input hash、工具顺序、tool_choice、thinking/history策略、采样/RNG/stop、输入与输出预算；不在公开结果保存明文。
- clock_domain、timer_resolution、offset/uncertainty 的来源；run 时钟与 wall time 日期各司其职。

模型校验如已有可信 manifest 可在冷态验；不要在正式计时前强行重读几十 GB，改变 page cache 后还称相同 warm。

## 3. 关联键

`run_id → task_id → turn_id → request_id → engine_leg_id → slot_id + slot_epoch → round_id`。

- task/turn 是匿名可复现编号；父子关系保存在 `parent_turn_id`，不靠时间近似。
- 一条 HTTP 可能有 restore/prefill/generate 多个 leg；一 slot 会复用，epoch 递增。
- 前缀对象另有 `cache_object_id + cache_generation`；restore 不等于新 request，publication 不等于 token 已发给 client。
- 多线程日志记录 `producer_id + producer_seq`。native fixed buffer 满了只增 overflow，不阻塞；一旦所需窗口缺事件，该窗口不授归因资格。
- HTTP自带trace标识若已存在先复用；若没有，新增显式无语义的关联元数据。不得把ID插入prompt或改变tokenization。
- 对不能安全关联的旧 source：`join_status=unbound`，保留孤立摘要，不用“唯一活跃请求”冒充长期并发正确性。

## 4. 公共事件封套

[JSON Schema](../schemas/measurement_event.schema.json)定义封套；下面 payload 字典为实施合同。单位 ns/B/token/row，duration 与 count 不共用字段。

| 字段 | 要求 |
|---|---|
| schema_version / record_kind | 本增补 `strata-evidence-event/1`；event/summary/loss |
| run_id / producer_id / producer_seq | 运行与进程内顺序；不得跨重启累减 |
| source_kind / observer_level | harness、server、native、gpu、system；L0/L1/L2 |
| runtime_id / request_id / engine_leg_id | 关联不到可 null，同时 availability 表明原因 |
| mono_ns / clock_domain | 同域 ns；wall_time 仅检索，不能算阶段耗时 |
| name / payload | event名称与其受控字段，不接受任意明文对象 |
| availability | OBSERVED / DERIVED / ESTIMATED / UNAVAILABLE / NOT_APPLICABLE；missing_reason |
| sample_policy_id | 全量低频或确定性采样；没有这一项不推总体频率 |

**null≠0。** UNSUPPORTED、NOT_ENABLED、NOT_CAPTURED、DROPPED、AMBIGUOUS_JOIN、SCHEMA_UNKNOWN 必须可区分。算法派生值附 input hashes、derivation version、置信限制。

## 5. 生命周期事件与耗时

建议名称（不是声称已有上游字段）：

`turn.ready`、`client.request_start`、`server.received`、`server.render_done`、`server.queue_enter`、`server.admission_granted`、`engine.leg_start`、`cache.restore_start/end`、`prefill.start/end`、`generation.start`、`token.commit`、`server.sse_write`、`client.chunk_received`、`request.terminal`。

- 外层排队：harness 同域 `client.request_start − turn.ready`，工具等待单列。
- server queue：同一队列定义的 enter→grant；串行 FIFO 与 parallel slot admission 各一字段，不使用同名 `admitted`强合。
- engine load/prepare/restore/prefill：独立区间；先区分 inclusive 与 exclusive，再算求和。
- client TTFT 至首非空输出；另列首 reasoning/visible/tool name/tool args；若只有usage或角色帧不算token。
- engine first token 与客户端首字节不做无校准的相减；网络发布分析用同域发送/接收事件和带不确定度的时钟映射。
- E2E 直到自然任务终点；错误/取消/超时不能只从平均值中删除。
- render/cache prepare如服务路径不能分到更细则 `prepare_inclusive`，不硬切成零毫秒的子项。

## 6. ITL 与推测块

真实 native commit gaps：两次提交事件间隔及每事件提交的正式 token 数。若一次 verifier 提交 k tokens：

- 记录 `commit_batch_tokens=k` 和提交时间；没有逐token时间时不把 k 个token均匀摊开制造 k 个观测。
- client chunk gaps 单独输出；SSE chunk可包含多个token甚至半个字符串，不是token级ITL。
- 只可报告批次间隔分布、request-level TPOT、client-visible gaps；真实逐tokenITT/ITL不可得时填 null。
- Prometheus 现有均值型ITL保留兼容原名，但在本报告标 `source_semantics=request_mean_repeated`，禁止把其P95图题写“真实P95 token latency”。

## 7. cache：逻辑、物理、owner 三本账

每次查找/恢复/发布/驱逐记录 `cache_object_id, owner_scope, slot_epoch, action, reason, logical_prefix_tokens, compatible_prefix_tokens, gpu_ready_tokens, ram_restore_tokens, ssd_restore_tokens, recompute_tokens, bytes_read, bytes_written, duration_ns, completion_dependency`。

- 前缀相同必须同时匹配 tokenization/template/tools/history policy/model/KV contract。
- `reused`可能含恢复；不可直接当 gpu_ready_tokens。恢复量可能以state bytes不是全序列KVtokens体现，不能强行相加。
- 同一token逻辑reuse与物理恢复可同时成立，**不做互斥饼图**；只有明确互斥的来源分类才求和。
- 无 preemption 只表示没有抢占活跃工作，不保证idle parent prefix不被驱逐。
- GPU ready命中必须在需求时已满足可读依赖；刚分配槽、pending DMA不算ready。
- park/publish发生于请求终点外也要保持owner，并标注其对下次请求的必要性；不能全部计入本请求或全部剔除。

## 8. expert、内存、shape

| 对象 | 最小字段与理由 |
|---|---|
| 专家路径 | layer/phase/quant；resident_before_demand、new_admit、prefetch_ready/late/wasted、cold_cpu、cold_stage；各自需求数/唯一专家数/字节数分开 |
| CPU/DMA成本 | CPU worker计算、排队、H2D/D2H、等待、overlap和明确依赖；预估与实际分栏。CPU+DMA共享DRAM，不能用两个峰值相加推收益 |
| 内存 | owner、allocated/reserved/live、pool高水位、loan_active/reclaim、scratch、KV、checkpoint、pinned host、RSS/PSS/swap/fault；相交量不叠加 |
| dispatch signature | architecture/quant、phase、logical/physical shape、context、verify_width、kernel family、实际 route/tactic、fallback reason、graph state |
| 物理行 | actual rows/expert、tile rows、padded/issued rows、group/launch、resident/staged、extra launch count；occupancy不是时间 |
| 时间 | L1先用现有CPU阶段包络；L2才补设备时序。异步launch的CPU耗时不能当kernel执行时长 |

shape histogram默认聚合到phase/quant/route/bucket；layer/round/expert详细ID在有界附件，不进Prom label。

## 9. 推测策略成本账

每round：来源（MTP/lookup/其他）、eligible/off_reason、proposal_tokens、target_verify_rows、accepted_draft_tokens、bonus_tokens、committed_tokens、rejected_rows、rollback/catchup、source_index_CPU、draft_compute、verify、commit、next-round状态修复成本。

核心指标：
`committed_tokens / full_round_wall`，以及真实任务E2E；接受率仅辅助。提案多不等于提交多；草稿接受不等于减少一次verify；预取命中不等于节省完成路径；“跳过draft”的回放必须计下一轮conditioning catch-up。

## 10. 完成路径与可证伪上界

保留 source intervals 与依赖边。GPU/CPU/copy 区间先取并集；并发累计时长可以大于wall，但归因不能因此大于100%。

单一互斥、无交叠且可移除的关键段占比 f、局部加速 s 时，理想速度上界 `1 / ((1−f)+f/s)`。这仅适用于满足前提的段；一般场景用依赖图重算完成终点，并扣除新增CPU/launch/copy/replay。

- kernel family累计6.6%不是可删除6.6%。
- 没有依赖闭包就输出“观测占比”和unknown，不补critical百分比。
- 前缀对象生命周期、跨轮状态修复可能跨出计时窗口；必须保留显式boundary dependency。
- 观测丢失、错PID、混clock、跨run/corpus，拒绝候选资格而非裁掉异常。

完整性校验与负例见 [20](20_ACCEPTANCE_TEST_MATRIX.md)，统计门见 [10](10_EVALUATION_AND_STATS.md)。

