# V2 支撑材料：`data/test-matrix.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/test-matrix.json -->
<!-- payload-sha256: 6c4ffcd7671c2a15673a321448e8fc642c7e243ce9d11b4c19a902203aa2d6de -->
<!-- payload-bytes: 60228 -->

<!-- payload-begin -->
````json
[
  {
    "id": "P0-T01-V01",
    "phase": "P0",
    "task": "P0-T01",
    "assertion": "PinMismatch：任一 SHA/共同祖先/11与34计数不符必须停止。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T01-V02",
    "phase": "P0",
    "task": "P0-T01",
    "assertion": "SourceUnchanged：审计前后原工作区 HEAD、index 和未跟踪状态保持不变。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T02-V01",
    "phase": "P0",
    "task": "P0-T02",
    "assertion": "NoCredentials：归档argv脱敏，不采集完整容器env或HTTP授权头。",
    "owner": "Deployment",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T02-V02",
    "phase": "P0",
    "task": "P0-T02",
    "assertion": "SharedCapacity：并发测试占用按共享KV池计算，不能按每lane262144计算。",
    "owner": "Deployment",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T03-V01",
    "phase": "P0",
    "task": "P0-T03",
    "assertion": "LegacyPinned：O构建后的原oracle输出不随candidate变化。",
    "owner": "Frontend QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T03-V02",
    "phase": "P0",
    "task": "P0-T03",
    "assertion": "G1Routing：real applied=53、synthetic applied=74；缺素材标BLOCKED，禁止降计数。",
    "owner": "Frontend QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T03-V03",
    "phase": "P0",
    "task": "P0-T03",
    "assertion": "TemplateBytes：fixture尾部newline处理与O read_pinned_template一致。",
    "owner": "Frontend QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T04-V01",
    "phase": "P0",
    "task": "P0-T04",
    "assertion": "ReplayIsolation：拒绝未显式声明sandbox的执行型工具；历史HTTP写入不直放生产。",
    "owner": "Performance QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T04-V02",
    "phase": "P0",
    "task": "P0-T04",
    "assertion": "ProgressIsNotToken：progress不计作首content；reasoning/content/tool分别标记。",
    "owner": "Performance QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P0-T04-V03",
    "phase": "P0",
    "task": "P0-T04",
    "assertion": "MatchedSamples：重复或缺失case_id/repeat、warmup混入、缺失GPU/model/dataset身份均失败。",
    "owner": "Performance QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T01-V01",
    "phase": "P1",
    "task": "P1-T01",
    "assertion": "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T01-V02",
    "phase": "P1",
    "task": "P1-T01",
    "assertion": "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T02-V01",
    "phase": "P1",
    "task": "P1-T02",
    "assertion": "EveryByteCut：≤256字节所有切点对照独立完整前缀LCP；覆盖NFC、NUL、invalidUTF8与added-token重叠。",
    "owner": "Frontend implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T02-V02",
    "phase": "P1",
    "task": "P1-T02",
    "assertion": "OneEncode：main_encode_calls==1；重复offset memo_hits增长而local_encode_calls不增长。",
    "owner": "Frontend implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T02-V03",
    "phase": "P1",
    "task": "P1-T02",
    "assertion": "TraceInvariant：起点(0,0)，只记录selected added token结束；ordinaryEOF不得冒充restart。",
    "owner": "Frontend implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T02-V04",
    "phase": "P1",
    "task": "P1-T02",
    "assertion": "LifetimeAndCopy：copy/move tokenizer与并发只读请求无悬空指针；release_ids后不再prefix。",
    "owner": "Frontend implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T03-V01",
    "phase": "P1",
    "task": "P1-T03",
    "assertion": "NoProductDto：legacy_boundary_contract不include生产processor；旧算法与P0 oracle输出一致。",
    "owner": "Frontend QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T03-V02",
    "phase": "P1",
    "task": "P1-T03",
    "assertion": "ComparatorNegative：missing/duplicate case、resource不等、token/error差异必须失败。",
    "owner": "Frontend QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T03-V03",
    "phase": "P1",
    "task": "P1-T03",
    "assertion": "ContractSplit：旧implicit字段映射与新explicit边界分别断言，不能拿新规则改旧golden。",
    "owner": "Frontend QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T04-V01",
    "phase": "P1",
    "task": "P1-T04",
    "assertion": "TimerIdentity：带/不带work观察产生同样tokens、boundaries、identity。",
    "owner": "Serving observability",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T04-V02",
    "phase": "P1",
    "task": "P1-T04",
    "assertion": "ThreeBodies：Chat/Messages/Responses rawbody准确，previous_response_id展开不增加body_bytes。",
    "owner": "Serving observability",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T04-V03",
    "phase": "P1",
    "task": "P1-T04",
    "assertion": "MediaUnknown：未拆分tokenize=-1，不算为0或负速率；缺字段日志可读。",
    "owner": "Serving observability",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T05-V01",
    "phase": "P1",
    "task": "P1-T05",
    "assertion": "AliasAtomic：payload准入失败不发布alias；同payload frontier/session不双份驻留。",
    "owner": "Cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T05-V02",
    "phase": "P1",
    "task": "P1-T05",
    "assertion": "ExplicitBoundary：非对齐cut回退LCP；去0/重叠；不越rewrite frontier。",
    "owner": "Cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T05-V03",
    "phase": "P1",
    "task": "P1-T05",
    "assertion": "RoutingIndependent：关闭implicit发布不等于关闭session routing；改system/tools/adapter不误命中。",
    "owner": "Cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T06-V01",
    "phase": "P1",
    "task": "P1-T06",
    "assertion": "DraftNotCommitted：拒绝draft不计入重复周期；guard触发finish reason可序列化。",
    "owner": "Runtime QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T06-V02",
    "phase": "P1",
    "task": "P1-T06",
    "assertion": "FaultScope：本轮受影响lane失败，排队请求可继续；非round异常不能被错误吞掉。",
    "owner": "Runtime QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P1-T06-V03",
    "phase": "P1",
    "task": "P1-T06",
    "assertion": "ProgressOnly：长prefill期间有合法进度、不伪造content/tool token。",
    "owner": "Runtime QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T01-V01",
    "phase": "P2",
    "task": "P2-T01",
    "assertion": "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T01-V02",
    "phase": "P2",
    "task": "P2-T01",
    "assertion": "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T02-V01",
    "phase": "P2",
    "task": "P2-T02",
    "assertion": "InFlightMutation：export中reset/restore/evict/cancel不得提前改写buffer。",
    "owner": "Runtime implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T02-V02",
    "phase": "P2",
    "task": "P2-T02",
    "assertion": "PublicationAfterComplete：copy失败/取消后无半成品alias；job失败有可见状态。",
    "owner": "Runtime implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T02-V03",
    "phase": "P2",
    "task": "P2-T02",
    "assertion": "Drain：shutdown等待或明确取消所有job，未完成source ownership不丢。",
    "owner": "Runtime implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T03-V01",
    "phase": "P2",
    "task": "P2-T03",
    "assertion": "AsyncAccounting：publish下降时导出工作仍可追踪；两request重叠不按总时长平摊。",
    "owner": "Observability QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T03-V02",
    "phase": "P2",
    "task": "P2-T03",
    "assertion": "MissingMetric：阶段缺字段返回unavailable，禁止0补值制造性能收益。",
    "owner": "Observability QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T04-V01",
    "phase": "P2",
    "task": "P2-T04",
    "assertion": "LongHotCold：热长会话加入冷请求后，合法复用不失效，队列能排空。",
    "owner": "GPU QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P2-T04-V02",
    "phase": "P2",
    "task": "P2-T04",
    "assertion": "ResourceRecovered：请求取消、cache驱逐后capacity回归稳定；没有持续正增长的不可归还字节。",
    "owner": "GPU QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T01-V01",
    "phase": "P3",
    "task": "P3-T01",
    "assertion": "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T01-V02",
    "phase": "P3",
    "task": "P3-T01",
    "assertion": "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T02-V01",
    "phase": "P3",
    "task": "P3-T02",
    "assertion": "SmallTTails：T=1,2,3,4,8,12,16,24,32,33跨路由对独立数值oracle。",
    "owner": "CUDA implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T02-V02",
    "phase": "P3",
    "task": "P3-T02",
    "assertion": "GraphReplay：capture/replay不同活跃row数不越workspace；q4/q5/w8有效路由不可skip。",
    "owner": "CUDA implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T02-V03",
    "phase": "P3",
    "task": "P3-T02",
    "assertion": "DeletedRoute：旧small_t/SIMT/conv_snapshot源已删时CMake/plan无悬空引用。",
    "owner": "CUDA implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T03-V01",
    "phase": "P3",
    "task": "P3-T03",
    "assertion": "DeltaJoin：多chunk参数连接等于nonstream完整JSON；字符串看似JSON仍保留string类型。",
    "owner": "Serving implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T03-V02",
    "phase": "P3",
    "task": "P3-T03",
    "assertion": "IncompleteNotExecutable：截断/cancel/断连后无tool end，历史不保存成完整可执行调用。",
    "owner": "Serving implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T03-V03",
    "phase": "P3",
    "task": "P3-T03",
    "assertion": "ThinkRecovery：未闭合think后的工具调用正确分类；混合普通文本与工具只发一次。",
    "owner": "Serving implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T03-V04",
    "phase": "P3",
    "task": "P3-T03",
    "assertion": "ThreeProtocols：native与compatproxy两层均通过schema和tool replay。",
    "owner": "Serving implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T04-V01",
    "phase": "P3",
    "task": "P3-T04",
    "assertion": "SkipIsNotPass：无设备返回77而非1，但4090资格中required77使gate失败。",
    "owner": "Build QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T04-V02",
    "phase": "P3",
    "task": "P3-T04",
    "assertion": "TargetUnion：fork standalone/G1与所有上游新tests都出现在构建图，不能只数ctest总数。",
    "owner": "Build QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T05-V01",
    "phase": "P3",
    "task": "P3-T05",
    "assertion": "AcceptanceNotAssumed：固定draft=3，记录实际accepted/rounds，而非只看理论window。",
    "owner": "Performance QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P3-T05-V02",
    "phase": "P3",
    "task": "P3-T05",
    "assertion": "LongStillGood：128K/192K/248K热增量TTFT与decode满足冻结门槛。",
    "owner": "Performance QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T01-V01",
    "phase": "P4",
    "task": "P4-T01",
    "assertion": "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T01-V02",
    "phase": "P4",
    "task": "P4-T01",
    "assertion": "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T02-V01",
    "phase": "P4",
    "task": "P4-T02",
    "assertion": "CodecBytes：A1/A2/A3 encoder字节按独立参考；全零h=0/饱和/FP16rounding有用例。",
    "owner": "CUDA / cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T02-V02",
    "phase": "P4",
    "task": "P4-T02",
    "assertion": "OwnColumns：A4 readonly prefix、BF16 own K/V、page/split边界与causal mask正确。",
    "owner": "CUDA / cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T02-V03",
    "phase": "P4",
    "task": "P4-T02",
    "assertion": "RejectOldPayload：旧版本/codec/flag不匹配拒绝或cache miss，不按新格式读旧字节。",
    "owner": "CUDA / cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T02-V04",
    "phase": "P4",
    "task": "P4-T02",
    "assertion": "OldOptionRejected：rk4v4-e8明确不可用，错误不被自动转成rk4v4。",
    "owner": "CUDA / cache implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T03-V01",
    "phase": "P4",
    "task": "P4-T03",
    "assertion": "BranchIsolation：question只续接state、不读另一question结果；swap/permute顺序符合契约。",
    "owner": "Decision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T03-V02",
    "phase": "P4",
    "task": "P4-T03",
    "assertion": "AdapterKind：生成拒绝decisionadapter，base与不同adaptercache不混用。",
    "owner": "Decision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T03-V03",
    "phase": "P4",
    "task": "P4-T03",
    "assertion": "NoDraft：decision请求spec rounds/decode均不伪增；statepluslongestbranch满足容量。",
    "owner": "Decision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T03-V04",
    "phase": "P4",
    "task": "P4-T03",
    "assertion": "Reference：有真实adapter时对冻结reference测每题概率；无adapter标该资格BLOCKED，不捏造概率。",
    "owner": "Decision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T04-V01",
    "phase": "P4",
    "task": "P4-T04",
    "assertion": "TelemetryAvailable：长prefill/decision期间health/telemetry不因execution mutex长期阻塞。",
    "owner": "Telemetry implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T04-V02",
    "phase": "P4",
    "task": "P4-T04",
    "assertion": "AdapterSnapshot：pool/slabs驻留和actualmodel类型同server_start/telemetry。",
    "owner": "Telemetry implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T04-V03",
    "phase": "P4",
    "task": "P4-T04",
    "assertion": "HistoricalLog：fork20/upstream20/22fixture都能显示正确单位/缺值。",
    "owner": "Telemetry implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T05-V01",
    "phase": "P4",
    "task": "P4-T05",
    "assertion": "SplitCodePoint：合法中文/emoji跨token及SSEchunk最终完整。",
    "owner": "Frontend output QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T05-V02",
    "phase": "P4",
    "task": "P4-T05",
    "assertion": "MalformedOutput：非法序列按上游规则替换U+FFFD，flush结束不遗留字节。",
    "owner": "Frontend output QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T05-V03",
    "phase": "P4",
    "task": "P4-T05",
    "assertion": "InputStillStrict：同样非法UTF8作为输入仍维持既有异常，不因output修复放松。",
    "owner": "Frontend output QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T05-V04",
    "phase": "P4",
    "task": "P4-T05",
    "assertion": "ToolUtf8：参数chunk修复不重复emit/破坏完整JSON。",
    "owner": "Frontend output QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T06-V01",
    "phase": "P4",
    "task": "P4-T06",
    "assertion": "FullContext：248K实际tokens+输出/系统余量不越262144；5needle和代码细节全部按判定器验证。",
    "owner": "GPU qualification",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T06-V02",
    "phase": "P4",
    "task": "P4-T06",
    "assertion": "ChatQuality：20Java任务×3重复的编译测试/工具正确率不下降；差异不以“浮点”直接豁免。",
    "owner": "GPU qualification",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P4-T06-V03",
    "phase": "P4",
    "task": "P4-T06",
    "assertion": "DecisionTolerance：启用真实decisionadapter时使用冻结per-questionreference容差；BF16资格与压缩codec偏差分开。",
    "owner": "GPU qualification",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T01-V01",
    "phase": "P5",
    "task": "P5-T01",
    "assertion": "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T01-V02",
    "phase": "P5",
    "task": "P5-T01",
    "assertion": "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T02-V01",
    "phase": "P5",
    "task": "P5-T02",
    "assertion": "NativeWire：有序input/answers/confidence/usage按各协议自己的规则。",
    "owner": "Protocol implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T02-V02",
    "phase": "P5",
    "task": "P5-T02",
    "assertion": "NoFabrication：无adapter/未支持modality报真实错误；不添加未训练refusal或虚拟外部模型别名。",
    "owner": "Protocol implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T02-V03",
    "phase": "P5",
    "task": "P5-T02",
    "assertion": "Discovery：decisionadapter只广告decisioncapability，生成model解析拒绝误用。",
    "owner": "Protocol implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T02-V04",
    "phase": "P5",
    "task": "P5-T02",
    "assertion": "RemovedRoute：旧/systemone无未声明兼容alias；保留Chat三端点。",
    "owner": "Protocol implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T03-V01",
    "phase": "P5",
    "task": "P5-T03",
    "assertion": "SameBytesDifferentProfile：同图片不同detail/resize不得误命中；相同语义profile可合法复用。",
    "owner": "Vision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T03-V02",
    "phase": "P5",
    "task": "P5-T03",
    "assertion": "VisionOnce：cachedstate图像不按每question重复encodevision。",
    "owner": "Vision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T03-V03",
    "phase": "P5",
    "task": "P5-T03",
    "assertion": "MRoPE：positions/rope_delta与参考一致；snapshot restore不丢image identity。",
    "owner": "Vision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T03-V04",
    "phase": "P5",
    "task": "P5-T03",
    "assertion": "BudgetReject：超限拒绝不静默降画质；cancel后hostlease释放。",
    "owner": "Vision implementation",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T04-V01",
    "phase": "P5",
    "task": "P5-T04",
    "assertion": "OrderedInputs：primitive/answer顺序保持；大整数文本不因JS Number转换丢精度。",
    "owner": "Web QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T04-V02",
    "phase": "P5",
    "task": "P5-T04",
    "assertion": "ImageRoundTrip：detail/dataURL/分享与恢复正确，不泄漏localfilepath/secret。",
    "owner": "Web QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T04-V03",
    "phase": "P5",
    "task": "P5-T04",
    "assertion": "LogCompatibility：forkprepare_detail/schema24/未知扩展展示正确缺值与单位。",
    "owner": "Web QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T04-V04",
    "phase": "P5",
    "task": "P5-T04",
    "assertion": "NoPhantomFeature：未加载decisionadapter时UI提示实际不可用，不展示假结果。",
    "owner": "Web QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T05-V01",
    "phase": "P5",
    "task": "P5-T05",
    "assertion": "GeneratedEndpointRegression：三个生成端点/compatproxy仍正确；tools/history/progress/timers全链路有效。",
    "owner": "Integration QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T05-V02",
    "phase": "P5",
    "task": "P5-T05",
    "assertion": "StateVersionNegative：在候选测试目录尝试旧版本payload，明确拒绝且不损坏新状态。",
    "owner": "Integration QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P5-T05-V03",
    "phase": "P5",
    "task": "P5-T05",
    "assertion": "MixedModeIsolation：有adapter时混合Chat/decision/image不跨lane/adapter复用；无adapter时错误资源释放可测。",
    "owner": "Integration QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T01-V01",
    "phase": "P6",
    "task": "P6-T01",
    "assertion": "AncestryBoth：O/U均为candidate祖先；无 -s ours伪合并，patch内容逐项对照。",
    "owner": "Integrator / independent reviewer",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T01-V02",
    "phase": "P6",
    "task": "P6-T01",
    "assertion": "RetentionComplete：43项账本无未处理；B0/B1/计时/standalone/skip/Docker都映射到证据。",
    "owner": "Integrator / independent reviewer",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T02-V01",
    "phase": "P6",
    "task": "P6-T02",
    "assertion": "FrozenSuite：模型/resource/dataset/seed/reasoning/tooljudger不变。",
    "owner": "Performance / quality QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T02-V02",
    "phase": "P6",
    "task": "P6-T02",
    "assertion": "NoRegression：建议TTFT p50≤+5%/p90≤+10%、decode p50≥-3%/p10≥-5%，prepare相同相对门槛，精确以P0冻结值为准。",
    "owner": "Performance / quality QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T02-V03",
    "phase": "P6",
    "task": "P6-T02",
    "assertion": "QualityAndCapacity：20×3Java判定/长5needle、共享KV拒绝策略满足冻结条件；样本不足不能说统计非劣。",
    "owner": "Performance / quality QA",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T03-V01",
    "phase": "P6",
    "task": "P6-T03",
    "assertion": "NoBakedModel：镜像层不包含模型；runtime可读.ninfer但不可写。",
    "owner": "Deployment",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T03-V02",
    "phase": "P6",
    "task": "P6-T03",
    "assertion": "NoSharedCache：candidate/prod目录不同；旧profile保留旧codec不被替换。",
    "owner": "Deployment",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T03-V03",
    "phase": "P6",
    "task": "P6-T03",
    "assertion": "DrainNoReplay：切换前拒绝新任务/等待活跃请求结束；进行中的tool calls不得自动重放。",
    "owner": "Deployment",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T04-V01",
    "phase": "P6",
    "task": "P6-T04",
    "assertion": "ApprovalRequired：未明确批准生产目标时仅test执行，final release状态PENDING而非伪PASS。",
    "owner": "Deployment / user approval",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T04-V02",
    "phase": "P6",
    "task": "P6-T04",
    "assertion": "CanaryHealth：从受控少量Java会话起步，监测error/toolcorrectness/TTFT/cache/memory，不仅health200。",
    "owner": "Deployment / user approval",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T05-V01",
    "phase": "P6",
    "task": "P6-T05",
    "assertion": "RollbackUsable：旧实例实际恢复health、一次正常生成和完整tool-call回路；旧cache可用或合法coldmiss。",
    "owner": "Deployment / final reviewer",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T05-V02",
    "phase": "P6",
    "task": "P6-T05",
    "assertion": "VersionIsolation：候选payload未写进旧namespace；旧启动参数不混入rk4v4新格式。",
    "owner": "Deployment / final reviewer",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P6-T05-V03",
    "phase": "P6",
    "task": "P6-T05",
    "assertion": "ReleaseTruth：源码完成、chat生产资格、optional资格和实际发布状态分别列出。",
    "owner": "Deployment / final reviewer",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T01-V01",
    "phase": "P7",
    "task": "P7-T01",
    "assertion": "SourcePin: P6-GATE.source_commit等于基线HEAD且包含O/U ancestry；变动HEAD拒绝。",
    "owner": "Integrator + Artifact owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T01-V02",
    "phase": "P7",
    "task": "P7-T01",
    "assertion": "AssetInventory: 缺必需tensor/完整revision时记录asset_ready=false及缺项清单；重复id/错误Targetdomain拒绝资产；低风险P8/P9仍可进行。",
    "owner": "Integrator + Artifact owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T01-V03",
    "phase": "P7",
    "task": "P7-T01",
    "assertion": "LicenseLedger: 所有拟复制文件对应T的path/blob/许可，第三方NOTICE和模型权重许可分开登记。",
    "owner": "Integrator + Artifact owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T02-V01",
    "phase": "P7",
    "task": "P7-T02",
    "assertion": "ActualTokens: 设置context262144但只有6000tokens的输入不得通过128K覆盖。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T02-V02",
    "phase": "P7",
    "task": "P7-T02",
    "assertion": "OutputReserve: 253952prompt+2048output合法；超过实际max_context或共享KV entitlement拒绝，不能自动截prompt。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T02-V03",
    "phase": "P7",
    "task": "P7-T02",
    "assertion": "FrozenQuality: Java expected来自冻结测试而非候选输出；同case改模板/权重hash拒绝配对。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T03-V01",
    "phase": "P7",
    "task": "P7-T03",
    "assertion": "CommittedCost: rounds(4tokens,20ms)+(1token,30ms)有效吞吐100tok/s，不得用3accepted得到60。",
    "owner": "Telemetry owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T03-V02",
    "phase": "P7",
    "task": "P7-T03",
    "assertion": "Overlap: retrieval与verify重叠时roundwall只计关键路径；GPUevent未就绪不得序列化为0ms。",
    "owner": "Telemetry owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T03-V03",
    "phase": "P7",
    "task": "P7-T03",
    "assertion": "LegacyLog: 原schema24/prepare_detail字段和值保留；未测量项为null/absent不伪造0，日志无原始prompt。",
    "owner": "Telemetry owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T03-V04",
    "phase": "P7",
    "task": "P7-T03",
    "assertion": "OffPath: instrumentation关闭结果token完全相同；抽样开销有独立off/on实测。",
    "owner": "Telemetry owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T04-V01",
    "phase": "P7",
    "task": "P7-T04",
    "assertion": "BudgetNoGo: baselinepeak+新权重/ring/index/stage/graphs超过显存减512MiB预留时拒绝。",
    "owner": "Performance + Runtime owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T04-V02",
    "phase": "P7",
    "task": "P7-T04",
    "assertion": "ArchiveAccounting: 262144×5120×2=2.5GiB；原始5层12.5GiB不能当同大小；4lane不漏重复ring。",
    "owner": "Performance + Runtime owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P7-T04-V03",
    "phase": "P7",
    "task": "P7-T04",
    "assertion": "NoSilentDowngrade: 不得改变Targetcodec/context或把TargetKV搬host使预算表通过。",
    "owner": "Performance + Runtime owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T01-V01",
    "phase": "P8",
    "task": "P8-T01",
    "assertion": "PolicyFilter: decision、non-greedy、adapter/media、unready/未加载backend只选合格fallback。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T01-V02",
    "phase": "P8",
    "task": "P8-T01",
    "assertion": "CostChoice: output128时fixed20ms+0.01/token与fixed0+0.1/token选后者；output2048选前者。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T01-V03",
    "phase": "P8",
    "task": "P8-T01",
    "assertion": "InvalidCalibration: NaN/负成本/缺项或Targethash不匹配拒绝auto，不能最小值选择0。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T02-V01",
    "phase": "P8",
    "task": "P8-T02",
    "assertion": "WidthGeometry: K3/4/5的全部projection/attention/GDN/rowcommit形状合法；K6清晰拒绝。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T02-V02",
    "phase": "P8",
    "task": "P8-T02",
    "assertion": "WidthExact: sameTarget普通与K3/4/5在greedy完整token序列一致，graph/eager均测。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T02-V03",
    "phase": "P8",
    "task": "P8-T02",
    "assertion": "WidthBoundary: capacity尾部、0/部分/全接受、stop/取消时无越界和statefrontier错位。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T03-V01",
    "phase": "P8",
    "task": "P8-T03",
    "assertion": "LookupMatch: ngram8→6→4优先，tie最新已提交历史；返回最多5tokens且后继范围合法。",
    "owner": "CPU worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T03-V02",
    "phase": "P8",
    "task": "P8-T03",
    "assertion": "Collision: 哈希冲突、末尾匹配无后继、短文本、K0均不伪造提案。",
    "owner": "CPU worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T03-V03",
    "phase": "P8",
    "task": "P8-T03",
    "assertion": "ScopeReset: 中途重写reset、会话/adapter切换不保留旧索引；取消草稿不append。",
    "owner": "CPU worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T04-V01",
    "phase": "P8",
    "task": "P8-T04",
    "assertion": "ExternalAccept: 错误Lookup首token立即修正；部分/全接受输出与ordinary一致，bonus最多一次。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T04-V02",
    "phase": "P8",
    "task": "P8-T04",
    "assertion": "Transaction: 重复预测内容不绕过repetitionguard；取消/fault后lane和下一个请求可正常生成。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T04-V03",
    "phase": "P8",
    "task": "P8-T04",
    "assertion": "MixedLanes: MTP与Lookup/None交错时token、usage、toolstream正确，不能串lane的GDN或adapter。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T05-V01",
    "phase": "P8",
    "task": "P8-T05",
    "assertion": "SameTarget: baseline/candidate权重、codec、prompttokenhash一致；严禁引用外部TQ结果替代。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T05-V02",
    "phase": "P8",
    "task": "P8-T05",
    "assertion": "EndToEnd: 对复制/长引用/低重复case报告walltime，Lookup失败开销不能从统计删除。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P8-T05-V03",
    "phase": "P8",
    "task": "P8-T05",
    "assertion": "DefaultSafety: policyoff时原P6行为不变；未资格的新路由不能进入生产manifest。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T01-V01",
    "phase": "P9",
    "task": "P9-T01",
    "assertion": "VerifyOracle: FA representedKV独立FP64参考覆盖rk4v4/INT8/BF16及width1/4/5/6，所有历史页必须可见。",
    "owner": "Numerics worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T01-V02",
    "phase": "P9",
    "task": "P9-T01",
    "assertion": "FirstDivergence: near-tiecase保存首次分歧前hidden/GDN/logits，不能仅比较最终自然语言。",
    "owner": "Numerics worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T01-V03",
    "phase": "P9",
    "task": "P9-T01",
    "assertion": "HotspotDecision: 没有可证主瓶颈不扩展kernel；NO_CHANGE需完整测量/理由不是skip。",
    "owner": "Numerics worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T02-V01",
    "phase": "P9",
    "task": "P9-T02",
    "assertion": "AllKeysVisible: 在最早/跨split/末页放针，任意key不能被稀疏裁掉。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T02-V02",
    "phase": "P9",
    "task": "P9-T02",
    "assertion": "Determinism: 改tile/split时执行顺序与浮点变化按oracle检查，greedy差异不能默许。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T02-V03",
    "phase": "P9",
    "task": "P9-T02",
    "assertion": "KernelBenefit: 报graph/eager以及SM时钟相同对照；不利profile不替换既有route。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T03-V01",
    "phase": "P9",
    "task": "P9-T03",
    "assertion": "EnvelopeEdges: 窗口128/160/512/4096/5000/8198/16390附近及128K/248K均满足launchcapacity。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T03-V02",
    "phase": "P9",
    "task": "P9-T03",
    "assertion": "GraphFixed: resize/slotgeneration变更不能重放旧指针图，图上界内实际width符合task契约。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T03-V03",
    "phase": "P9",
    "task": "P9-T03",
    "assertion": "NoFeatureTax: 新routeoff时原MTPworkspace/graph数量不增长；有分配必须计入资源账本。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T04-V01",
    "phase": "P9",
    "task": "P9-T04",
    "assertion": "LongActual: 131072/253952真实token输入及2048output可完成；大context短prompt不算覆盖。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T04-V02",
    "phase": "P9",
    "task": "P9-T04",
    "assertion": "Quality: Java编译/测试/远端事实/工具调用与exact输出均不退化。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P9-T04-V03",
    "phase": "P9",
    "task": "P9-T04",
    "assertion": "NoGainNoDefault: walltime无5%收益的route不默认启用；若NO_CHANGE，证据仍完整。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T01-V01",
    "phase": "P10",
    "task": "P10-T01",
    "assertion": "TypedInventory: wrongTargethidden/tokenizerhash/missingconv/selector/非法特征层和词表重复id均拒绝。",
    "owner": "Artifact owner + Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T01-V02",
    "phase": "P10",
    "task": "P10-T01",
    "assertion": "NoRequantCascade: 默认从原始BF16单次量化，量化profile和tensorchecksum冻结；不默用TQ3再量化。",
    "owner": "Artifact owner + Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T01-V03",
    "phase": "P10",
    "task": "P10-T01",
    "assertion": "NoFlagOnly: 无完整companion资产不能通过supported=true进入执行；Targetartifact字节不变。",
    "owner": "Artifact owner + Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T02-V01",
    "phase": "P10",
    "task": "P10-T02",
    "assertion": "FeatureTap: pre/postlayer和norm前后错一个位置会命中失败golden。",
    "owner": "Numerical reference worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T02-V02",
    "phase": "P10",
    "task": "P10-T02",
    "assertion": "Lattice: 相同unary而不同前驱产生不同后继；tie按全域tokenid规则固定。",
    "owner": "Numerical reference worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T02-V03",
    "phase": "P10",
    "task": "P10-T02",
    "assertion": "ProjectedG: 同一G重建全部drafter层历史KV与直接注入reference一致，按dtype冻结数值准则。",
    "owner": "Numerical reference worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T03-V01",
    "phase": "P10",
    "task": "P10-T03",
    "assertion": "ConvTaps: 两侧dynamic+base、group映射与block边界符合独立CPU公式；不得带入Target4-tap GDNconv。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T03-V02",
    "phase": "P10",
    "task": "P10-T03",
    "assertion": "SelectorTie: top16/lattice连续相等值选择确定，id映射不越过token域。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T03-V03",
    "phase": "P10",
    "task": "P10-T03",
    "assertion": "OpIsolation: repeatbitidentity、eager/graph、无热路径allocation、输入未被意外覆写均检查。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T04-V01",
    "phase": "P10",
    "task": "P10-T04",
    "assertion": "CaptureCommit: 丢弃的verify候选G不进入可复用ring；bonus未forward时featurefrontier不虚增。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T04-V02",
    "phase": "P10",
    "task": "P10-T04",
    "assertion": "RingWrap: 绕ring多次、短partialblock、边界rollback后visibleKV只对应合法原位置。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T04-V03",
    "phase": "P10",
    "task": "P10-T04",
    "assertion": "BudgetLayout: rings按lane、scratch按同时存活、checkpoint/graphs逐项计费；超预算startup拒绝。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T05-V01",
    "phase": "P10",
    "task": "P10-T05",
    "assertion": "ChainExact: 强制0/1/K接受与bonus/stop边界，结果对相同Targetordinary逐token一致。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T05-V02",
    "phase": "P10",
    "task": "P10-T05",
    "assertion": "UnsupportedFallback: 采样/LoRA/图像/无archive不得误入DFlash2，日志resolvedbackend与实际调用一致。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T05-V03",
    "phase": "P10",
    "task": "P10-T05",
    "assertion": "FaultRecovery: Draft异常只放弃提案或请求，不污染下一轮Target/GDN；取消不发布未许可toolcall。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T06-V01",
    "phase": "P10",
    "task": "P10-T06",
    "assertion": "GraphReplay: slotlayout/B/K/weightsgeneration改变后不复用错误图，graph/eager完全一致。",
    "owner": "Performance worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T06-V02",
    "phase": "P10",
    "task": "P10-T06",
    "assertion": "PhysicalRows: 降K仅截候选时physicalB不变，报告不能虚称draftFLOPs按K减少。",
    "owner": "Performance worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T06-V03",
    "phase": "P10",
    "task": "P10-T06",
    "assertion": "HeadAblation: 65536/131072/完整draft词表对比接受和成本，Target合法token不被draftmap裁掉。",
    "owner": "Performance worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T07-V01",
    "phase": "P10",
    "task": "P10-T07",
    "assertion": "AssetMeasured: 发布资产revision、convertedhash、实际deviceweight/head/graph bytes完整可追溯。",
    "owner": "Evaluation + Runtime owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T07-V02",
    "phase": "P10",
    "task": "P10-T07",
    "assertion": "LongHotCold: 128K/248K cold、same-lanewarm、Target-onlyL2恢复的额外初始化成本均统计，不能删fallbackcase。",
    "owner": "Evaluation + Runtime owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P10-T07-V03",
    "phase": "P10",
    "task": "P10-T07",
    "assertion": "AdoptionGate: 只有128K≥15%、248K原门槛、Agentwalltime及预算全部满足才能promotion=QUALIFIED；速度未达则DECLINED而不是伪造性能PASS。",
    "owner": "Evaluation + Runtime owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T01-V01",
    "phase": "P11",
    "task": "P11-T01",
    "assertion": "Reconstruct: 从G重建所有层draftKV等价于P10直接注入reference；任一层不满足阻断。",
    "owner": "Archive worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T01-V02",
    "phase": "P11",
    "task": "P11-T01",
    "assertion": "Identity: draft/target/tokenizer/adapter/rope/profile/epoch任一不同不得复用；Targetcache仍可独立有效。",
    "owner": "Archive worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T01-V03",
    "phase": "P11",
    "task": "P11-T01",
    "assertion": "BudgetLease: 总sessiontoken预算、未完成D2H、淘汰lease和迟到写入均不UAF，未许可G不发布。",
    "owner": "Archive worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T02-V01",
    "phase": "P11",
    "task": "P11-T02",
    "assertion": "OldestCoverage: 262144/1536产生16288合法16token远端chunks，index包含page0；强早期针必须可进入coarsetop8。",
    "owner": "Index worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T02-V02",
    "phase": "P11",
    "task": "P11-T02",
    "assertion": "PageOracle: 代表取最大L2的两条K，tie小position；不满页/空prefix/overwrite一致。",
    "owner": "Index worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T02-V03",
    "phase": "P11",
    "task": "P11-T02",
    "assertion": "Complexity: 输出记录page数量/bytes，随N增长O(N/256)；不得把整个索引宣称常数。",
    "owner": "Index worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T03-V01",
    "phase": "P11",
    "task": "P11-T03",
    "assertion": "GlobalSelect: 最早页可选；coarse/refine按独立CPUoracle，ties、重复、partialchunk/padding屏蔽正确。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T03-V02",
    "phase": "P11",
    "task": "P11-T03",
    "assertion": "Positions: 直接从G产生K并在virtualpos旋转，与reference对应；recent原位置不变，Targetpositionhash不变。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T03-V03",
    "phase": "P11",
    "task": "P11-T03",
    "assertion": "Bounds: 每head<=32remotechunks，stagebuffer不越界；0remote/anchor重复/页淘汰均有定义。",
    "owner": "CUDA worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T04-V01",
    "phase": "P11",
    "task": "P11-T04",
    "assertion": "LateResult: 刷新中取消、rewrite、adapter/lane变更后结果不得publish，lease全部释放。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T04-V02",
    "phase": "P11",
    "task": "P11-T04",
    "assertion": "GraphBoundary: D2Hids/CPUarchive/H2D在图外，graph只捕获device计算；实现不得假装端到端CPUfree。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T04-V03",
    "phase": "P11",
    "task": "P11-T04",
    "assertion": "RefreshFallback: deadline内未ready继续合法旧selection或recent-only，不同步阻塞Targetworker或读磁盘。",
    "owner": "Runtime worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T05-V01",
    "phase": "P11",
    "task": "P11-T05",
    "assertion": "TargetOnlyHit: 从原TargetL2恢复成功但Draftarchive缺失，选择MTP/None且无隐藏全prefill。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T05-V02",
    "phase": "P11",
    "task": "P11-T05",
    "assertion": "RewriteScope: 改早期工具输出只能保留exactprefix页，边界页及后续Draft状态失效。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T05-V03",
    "phase": "P11",
    "task": "P11-T05",
    "assertion": "LeaseIsolation: slot复用/adapter切换/restore/服务结束期间无跨identity读取或内存泄漏。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T06-V01",
    "phase": "P11",
    "task": "P11-T06",
    "assertion": "CostNotAcceptance: 接受率高但hostrefresh总时间更长时不选择selective，按committed/time而非acceptance决策。",
    "owner": "Telemetry + Policy worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T06-V02",
    "phase": "P11",
    "task": "P11-T06",
    "assertion": "MissingHistory: 只有Targethit无Draftready时selective不被选为零成本路由。",
    "owner": "Telemetry + Policy worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T06-V03",
    "phase": "P11",
    "task": "P11-T06",
    "assertion": "NoPolicyDrift: auto policy的校准/预算hash变更须新qualification，不在线偷偷换Target参数。",
    "owner": "Telemetry + Policy worker",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T07-V01",
    "phase": "P11",
    "task": "P11-T07",
    "assertion": "FarDependency: 第0页/中间/末尾不同Java签名及中文约束，selectedcoverage、greedy结果和编译测试同时证明。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T07-V02",
    "phase": "P11",
    "task": "P11-T07",
    "assertion": "FullLifecycle: 全局检索在cold/L1/Target-onlyL2/rewrittenhistory/cancel/mixedload下都满足状态及无退化准则。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P11-T07-V03",
    "phase": "P11",
    "task": "P11-T07",
    "assertion": "RealGain: 128K≥15%增益、248K原门槛、真实Agentwalltime改善且24GB/64GB预算合格；无收益标NO_GO。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T01-V01",
    "phase": "P12",
    "task": "P12-T01",
    "assertion": "CustomPreserved: B0单一scanner/计数/计时/oracle/无权重镜像、原协议和cache行为无隐性替换。",
    "owner": "Independent reviewer + Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T01-V02",
    "phase": "P12",
    "task": "P12-T01",
    "assertion": "OneAuthority: Targetverify/rowcommit/ReplaySSM唯一，原35B DFlash语义未被27B路径覆盖。",
    "owner": "Independent reviewer + Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T01-V03",
    "phase": "P12",
    "task": "P12-T01",
    "assertion": "Provenance: 实际移植函数有immutableT出处/许可证/改写说明；模型asset单独许可核查。",
    "owner": "Independent reviewer + Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T02-V01",
    "phase": "P12",
    "task": "P12-T02",
    "assertion": "FinalComposition: MTP/Lookup/DFlash2/global/graph组合在声明支持范围exact，non-greedy/adapter/media fallback原质量保留。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T02-V02",
    "phase": "P12",
    "task": "P12-T02",
    "assertion": "ActualContextMatrix: 2K—248K实际tokens，单并发/部署并发，长输出、冷/热/重写/取消全部覆盖。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T02-V03",
    "phase": "P12",
    "task": "P12-T02",
    "assertion": "AgentOutcome: 编译/测试/工具调用无新增失败，至少30冻结Java任务统计walltime和失败原因；达到采用线。",
    "owner": "Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T03-V01",
    "phase": "P12",
    "task": "P12-T03",
    "assertion": "NoBake: 镜像不打包Target/draft权重，启动参数与assetfingerprint明确。",
    "owner": "Deployment owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T03-V02",
    "phase": "P12",
    "task": "P12-T03",
    "assertion": "NoSharedCache: 新旧实例不共享可写cache目录；Draftarchive进程内销毁不污染回滚。",
    "owner": "Deployment owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T03-V03",
    "phase": "P12",
    "task": "P12-T03",
    "assertion": "FailClosedStart: 错asset/license/profile/显存预算不足清楚拒绝，不能自动下载/缩context/改KV。",
    "owner": "Deployment owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T04-V01",
    "phase": "P12",
    "task": "P12-T04",
    "assertion": "CanaryScope: 原服务排空后串行运行candidate，不越过授权主机/端口/时间窗口。",
    "owner": "Deployment + Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T04-V02",
    "phase": "P12",
    "task": "P12-T04",
    "assertion": "RollbackWorking: 旧镜像+旧参数+旧cache恢复后真实生成/工具流/监控有效，不能只检查进程存在。",
    "owner": "Deployment + Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T04-V03",
    "phase": "P12",
    "task": "P12-T04",
    "assertion": "Trigger: OOM/enginefailed/错误token/协议问题立即回滚；性能超原门槛按冻结观察窗口处理。",
    "owner": "Deployment + Evaluation owner",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T05-V01",
    "phase": "P12",
    "task": "P12-T05",
    "assertion": "EvidenceIdentity: reviewcommit/requiredchecks/运行结果与最终source一致；任一错hash/缺GPU/skip使gate失败。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T05-V02",
    "phase": "P12",
    "task": "P12-T05",
    "assertion": "ExplicitScope: 未过的route/context/concurrency不出现在releaseenabled集合。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  },
  {
    "id": "P12-T05-V03",
    "phase": "P12",
    "task": "P12-T05",
    "assertion": "Reproducibility: 包内链接/校验和/DAG完整；原计划历史证据不被改写成新GPU测试。",
    "owner": "Integrator",
    "mandatory_for_task": true,
    "status": "PENDING",
    "evidence": ""
  }
]
````
<!-- payload-end -->
