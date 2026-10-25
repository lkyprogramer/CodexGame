# 完整具名断言矩阵

继承P0—P6共100条；H0—H8为52任务×3+H1-T07八条=164条，53任务合计264条。P4/P6的工程数目已按plans/06替代历史20×3，历史任务原件未改。全部待实施/待执行，不是本次通过计数。性能按plans/06分层，只运行相关合同，H5/H8集中声明profile发布资格；264条不替代真实实机证据。

| Assertion ID | Owner Task | 断言 | 当前状态 |
|---|---|---|---|
| P0-T01-V01 | [P0-T01](../previous-v2/plans/tasks/P0-T01.md) | PinMismatch：任一 SHA/共同祖先/11与34计数不符必须停止。 | PENDING |
| P0-T01-V02 | [P0-T01](../previous-v2/plans/tasks/P0-T01.md) | SourceUnchanged：审计前后原工作区 HEAD、index 和未跟踪状态保持不变。 | PENDING |
| P0-T02-V01 | [P0-T02](../previous-v2/plans/tasks/P0-T02.md) | NoCredentials：归档argv脱敏，不采集完整容器env或HTTP授权头。 | PENDING |
| P0-T02-V02 | [P0-T02](../previous-v2/plans/tasks/P0-T02.md) | SharedCapacity：并发测试占用按共享KV池计算，不能按每lane262144计算。 | PENDING |
| P0-T03-V01 | [P0-T03](../previous-v2/plans/tasks/P0-T03.md) | LegacyPinned：O构建后的原oracle输出不随candidate变化。 | PENDING |
| P0-T03-V02 | [P0-T03](../previous-v2/plans/tasks/P0-T03.md) | G1Routing：real applied=53、synthetic applied=74；缺素材标BLOCKED，禁止降计数。 | PENDING |
| P0-T03-V03 | [P0-T03](../previous-v2/plans/tasks/P0-T03.md) | TemplateBytes：fixture尾部newline处理与O read_pinned_template一致。 | PENDING |
| P0-T04-V01 | [P0-T04](../previous-v2/plans/tasks/P0-T04.md) | ReplayIsolation：拒绝未显式声明sandbox的执行型工具；历史HTTP写入不直放生产。 | PENDING |
| P0-T04-V02 | [P0-T04](../previous-v2/plans/tasks/P0-T04.md) | ProgressIsNotToken：progress不计作首content；reasoning/content/tool分别标记。 | PENDING |
| P0-T04-V03 | [P0-T04](../previous-v2/plans/tasks/P0-T04.md) | MatchedSamples：重复或缺失case_id/repeat、warmup混入、缺失GPU/model/dataset身份均失败。 | PENDING |
| P1-T01-V01 | [P1-T01](../previous-v2/plans/tasks/P1-T01.md) | UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。 | PENDING |
| P1-T01-V02 | [P1-T01](../previous-v2/plans/tasks/P1-T01.md) | Retention：43项定制账本有对应文件/替代测试，不能静默丢失。 | PENDING |
| P1-T02-V01 | [P1-T02](../previous-v2/plans/tasks/P1-T02.md) | EveryByteCut：≤256字节所有切点对照独立完整前缀LCP；覆盖NFC、NUL、invalidUTF8与added-token重叠。 | PENDING |
| P1-T02-V02 | [P1-T02](../previous-v2/plans/tasks/P1-T02.md) | OneEncode：main_encode_calls==1；重复offset memo_hits增长而local_encode_calls不增长。 | PENDING |
| P1-T02-V03 | [P1-T02](../previous-v2/plans/tasks/P1-T02.md) | TraceInvariant：起点(0,0)，只记录selected added token结束；ordinaryEOF不得冒充restart。 | PENDING |
| P1-T02-V04 | [P1-T02](../previous-v2/plans/tasks/P1-T02.md) | LifetimeAndCopy：copy/move tokenizer与并发只读请求无悬空指针；release_ids后不再prefix。 | PENDING |
| P1-T03-V01 | [P1-T03](../previous-v2/plans/tasks/P1-T03.md) | NoProductDto：legacy_boundary_contract不include生产processor；旧算法与P0 oracle输出一致。 | PENDING |
| P1-T03-V02 | [P1-T03](../previous-v2/plans/tasks/P1-T03.md) | ComparatorNegative：missing/duplicate case、resource不等、token/error差异必须失败。 | PENDING |
| P1-T03-V03 | [P1-T03](../previous-v2/plans/tasks/P1-T03.md) | ContractSplit：旧implicit字段映射与新explicit边界分别断言，不能拿新规则改旧golden。 | PENDING |
| P1-T04-V01 | [P1-T04](../previous-v2/plans/tasks/P1-T04.md) | TimerIdentity：带/不带work观察产生同样tokens、boundaries、identity。 | PENDING |
| P1-T04-V02 | [P1-T04](../previous-v2/plans/tasks/P1-T04.md) | ThreeBodies：Chat/Messages/Responses rawbody准确，previous_response_id展开不增加body_bytes。 | PENDING |
| P1-T04-V03 | [P1-T04](../previous-v2/plans/tasks/P1-T04.md) | MediaUnknown：未拆分tokenize=-1，不算为0或负速率；缺字段日志可读。 | PENDING |
| P1-T05-V01 | [P1-T05](../previous-v2/plans/tasks/P1-T05.md) | AliasAtomic：payload准入失败不发布alias；同payload frontier/session不双份驻留。 | PENDING |
| P1-T05-V02 | [P1-T05](../previous-v2/plans/tasks/P1-T05.md) | ExplicitBoundary：非对齐cut回退LCP；去0/重叠；不越rewrite frontier。 | PENDING |
| P1-T05-V03 | [P1-T05](../previous-v2/plans/tasks/P1-T05.md) | RoutingIndependent：关闭implicit发布不等于关闭session routing；改system/tools/adapter不误命中。 | PENDING |
| P1-T06-V01 | [P1-T06](../previous-v2/plans/tasks/P1-T06.md) | DraftNotCommitted：拒绝draft不计入重复周期；guard触发finish reason可序列化。 | PENDING |
| P1-T06-V02 | [P1-T06](../previous-v2/plans/tasks/P1-T06.md) | FaultScope：本轮受影响lane失败，排队请求可继续；非round异常不能被错误吞掉。 | PENDING |
| P1-T06-V03 | [P1-T06](../previous-v2/plans/tasks/P1-T06.md) | ProgressOnly：长prefill期间有合法进度、不伪造content/tool token。 | PENDING |
| P2-T01-V01 | [P2-T01](../previous-v2/plans/tasks/P2-T01.md) | UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。 | PENDING |
| P2-T01-V02 | [P2-T01](../previous-v2/plans/tasks/P2-T01.md) | Retention：43项定制账本有对应文件/替代测试，不能静默丢失。 | PENDING |
| P2-T02-V01 | [P2-T02](../previous-v2/plans/tasks/P2-T02.md) | InFlightMutation：export中reset/restore/evict/cancel不得提前改写buffer。 | PENDING |
| P2-T02-V02 | [P2-T02](../previous-v2/plans/tasks/P2-T02.md) | PublicationAfterComplete：copy失败/取消后无半成品alias；job失败有可见状态。 | PENDING |
| P2-T02-V03 | [P2-T02](../previous-v2/plans/tasks/P2-T02.md) | Drain：shutdown等待或明确取消所有job，未完成source ownership不丢。 | PENDING |
| P2-T03-V01 | [P2-T03](../previous-v2/plans/tasks/P2-T03.md) | AsyncAccounting：publish下降时导出工作仍可追踪；两request重叠不按总时长平摊。 | PENDING |
| P2-T03-V02 | [P2-T03](../previous-v2/plans/tasks/P2-T03.md) | MissingMetric：阶段缺字段返回unavailable，禁止0补值制造性能收益。 | PENDING |
| P2-T04-V01 | [P2-T04](../previous-v2/plans/tasks/P2-T04.md) | LongHotCold：热长会话加入冷请求后，合法复用不失效，队列能排空。 | PENDING |
| P2-T04-V02 | [P2-T04](../previous-v2/plans/tasks/P2-T04.md) | ResourceRecovered：请求取消、cache驱逐后capacity回归稳定；没有持续正增长的不可归还字节。 | PENDING |
| P3-T01-V01 | [P3-T01](../previous-v2/plans/tasks/P3-T01.md) | UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。 | PENDING |
| P3-T01-V02 | [P3-T01](../previous-v2/plans/tasks/P3-T01.md) | Retention：43项定制账本有对应文件/替代测试，不能静默丢失。 | PENDING |
| P3-T02-V01 | [P3-T02](../previous-v2/plans/tasks/P3-T02.md) | SmallTTails：T=1,2,3,4,8,12,16,24,32,33跨路由对独立数值oracle。 | PENDING |
| P3-T02-V02 | [P3-T02](../previous-v2/plans/tasks/P3-T02.md) | GraphReplay：capture/replay不同活跃row数不越workspace；q4/q5/w8有效路由不可skip。 | PENDING |
| P3-T02-V03 | [P3-T02](../previous-v2/plans/tasks/P3-T02.md) | DeletedRoute：旧small_t/SIMT/conv_snapshot源已删时CMake/plan无悬空引用。 | PENDING |
| P3-T03-V01 | [P3-T03](../previous-v2/plans/tasks/P3-T03.md) | DeltaJoin：多chunk参数连接等于nonstream完整JSON；字符串看似JSON仍保留string类型。 | PENDING |
| P3-T03-V02 | [P3-T03](../previous-v2/plans/tasks/P3-T03.md) | IncompleteNotExecutable：截断/cancel/断连后无tool end，历史不保存成完整可执行调用。 | PENDING |
| P3-T03-V03 | [P3-T03](../previous-v2/plans/tasks/P3-T03.md) | ThinkRecovery：未闭合think后的工具调用正确分类；混合普通文本与工具只发一次。 | PENDING |
| P3-T03-V04 | [P3-T03](../previous-v2/plans/tasks/P3-T03.md) | ThreeProtocols：native与compatproxy两层均通过schema和tool replay。 | PENDING |
| P3-T04-V01 | [P3-T04](../previous-v2/plans/tasks/P3-T04.md) | SkipIsNotPass：无设备返回77而非1，但4090资格中required77使gate失败。 | PENDING |
| P3-T04-V02 | [P3-T04](../previous-v2/plans/tasks/P3-T04.md) | TargetUnion：fork standalone/G1与所有上游新tests都出现在构建图，不能只数ctest总数。 | PENDING |
| P3-T05-V01 | [P3-T05](../previous-v2/plans/tasks/P3-T05.md) | AcceptanceNotAssumed：固定draft=3，记录实际accepted/rounds，而非只看理论window。 | PENDING |
| P3-T05-V02 | [P3-T05](../previous-v2/plans/tasks/P3-T05.md) | LongStillGood：128K/192K/248K热增量TTFT与decode满足冻结门槛。 | PENDING |
| P4-T01-V01 | [P4-T01](../previous-v2/plans/tasks/P4-T01.md) | UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。 | PENDING |
| P4-T01-V02 | [P4-T01](../previous-v2/plans/tasks/P4-T01.md) | Retention：43项定制账本有对应文件/替代测试，不能静默丢失。 | PENDING |
| P4-T02-V01 | [P4-T02](../previous-v2/plans/tasks/P4-T02.md) | CodecBytes：A1/A2/A3 encoder字节按独立参考；全零h=0/饱和/FP16rounding有用例。 | PENDING |
| P4-T02-V02 | [P4-T02](../previous-v2/plans/tasks/P4-T02.md) | OwnColumns：A4 readonly prefix、BF16 own K/V、page/split边界与causal mask正确。 | PENDING |
| P4-T02-V03 | [P4-T02](../previous-v2/plans/tasks/P4-T02.md) | RejectOldPayload：旧版本/codec/flag不匹配拒绝或cache miss，不按新格式读旧字节。 | PENDING |
| P4-T02-V04 | [P4-T02](../previous-v2/plans/tasks/P4-T02.md) | OldOptionRejected：rk4v4-e8明确不可用，错误不被自动转成rk4v4。 | PENDING |
| P4-T03-V01 | [P4-T03](../previous-v2/plans/tasks/P4-T03.md) | BranchIsolation：question只续接state、不读另一question结果；swap/permute顺序符合契约。 | PENDING |
| P4-T03-V02 | [P4-T03](../previous-v2/plans/tasks/P4-T03.md) | AdapterKind：生成拒绝decisionadapter，base与不同adaptercache不混用。 | PENDING |
| P4-T03-V03 | [P4-T03](../previous-v2/plans/tasks/P4-T03.md) | NoDraft：decision请求spec rounds/decode均不伪增；statepluslongestbranch满足容量。 | PENDING |
| P4-T03-V04 | [P4-T03](../previous-v2/plans/tasks/P4-T03.md) | Reference：有真实adapter时对冻结reference测每题概率；无adapter标该资格BLOCKED，不捏造概率。 | PENDING |
| P4-T04-V01 | [P4-T04](../previous-v2/plans/tasks/P4-T04.md) | TelemetryAvailable：长prefill/decision期间health/telemetry不因execution mutex长期阻塞。 | PENDING |
| P4-T04-V02 | [P4-T04](../previous-v2/plans/tasks/P4-T04.md) | AdapterSnapshot：pool/slabs驻留和actualmodel类型同server_start/telemetry。 | PENDING |
| P4-T04-V03 | [P4-T04](../previous-v2/plans/tasks/P4-T04.md) | HistoricalLog：fork20/upstream20/22fixture都能显示正确单位/缺值。 | PENDING |
| P4-T05-V01 | [P4-T05](../previous-v2/plans/tasks/P4-T05.md) | SplitCodePoint：合法中文/emoji跨token及SSEchunk最终完整。 | PENDING |
| P4-T05-V02 | [P4-T05](../previous-v2/plans/tasks/P4-T05.md) | MalformedOutput：非法序列按上游规则替换U+FFFD，flush结束不遗留字节。 | PENDING |
| P4-T05-V03 | [P4-T05](../previous-v2/plans/tasks/P4-T05.md) | InputStillStrict：同样非法UTF8作为输入仍维持既有异常，不因output修复放松。 | PENDING |
| P4-T05-V04 | [P4-T05](../previous-v2/plans/tasks/P4-T05.md) | ToolUtf8：参数chunk修复不重复emit/破坏完整JSON。 | PENDING |
| P4-T06-V01 | [P4-T06](../previous-v2/plans/tasks/P4-T06.md) | FullContext：248K实际tokens+输出/系统余量不越262144；5needle和代码细节全部按判定器验证。 | PENDING |
| P4-T06-V02 | [P4-T06](../previous-v2/plans/tasks/P4-T06.md) | ChatQuality：plans/06选定工程与repo集的编译测试/工具正确率不下降；差异不以“浮点”直接豁免。 | PENDING |
| P4-T06-V03 | [P4-T06](../previous-v2/plans/tasks/P4-T06.md) | DecisionTolerance：启用真实decisionadapter时使用冻结per-questionreference容差；BF16资格与压缩codec偏差分开。 | PENDING |
| P5-T01-V01 | [P5-T01](../previous-v2/plans/tasks/P5-T01.md) | UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。 | PENDING |
| P5-T01-V02 | [P5-T01](../previous-v2/plans/tasks/P5-T01.md) | Retention：43项定制账本有对应文件/替代测试，不能静默丢失。 | PENDING |
| P5-T02-V01 | [P5-T02](../previous-v2/plans/tasks/P5-T02.md) | NativeWire：有序input/answers/confidence/usage按各协议自己的规则。 | PENDING |
| P5-T02-V02 | [P5-T02](../previous-v2/plans/tasks/P5-T02.md) | NoFabrication：无adapter/未支持modality报真实错误；不添加未训练refusal或虚拟外部模型别名。 | PENDING |
| P5-T02-V03 | [P5-T02](../previous-v2/plans/tasks/P5-T02.md) | Discovery：decisionadapter只广告decisioncapability，生成model解析拒绝误用。 | PENDING |
| P5-T02-V04 | [P5-T02](../previous-v2/plans/tasks/P5-T02.md) | RemovedRoute：旧/systemone无未声明兼容alias；保留Chat三端点。 | PENDING |
| P5-T03-V01 | [P5-T03](../previous-v2/plans/tasks/P5-T03.md) | SameBytesDifferentProfile：同图片不同detail/resize不得误命中；相同语义profile可合法复用。 | PENDING |
| P5-T03-V02 | [P5-T03](../previous-v2/plans/tasks/P5-T03.md) | VisionOnce：cachedstate图像不按每question重复encodevision。 | PENDING |
| P5-T03-V03 | [P5-T03](../previous-v2/plans/tasks/P5-T03.md) | MRoPE：positions/rope_delta与参考一致；snapshot restore不丢image identity。 | PENDING |
| P5-T03-V04 | [P5-T03](../previous-v2/plans/tasks/P5-T03.md) | BudgetReject：超限拒绝不静默降画质；cancel后hostlease释放。 | PENDING |
| P5-T04-V01 | [P5-T04](../previous-v2/plans/tasks/P5-T04.md) | OrderedInputs：primitive/answer顺序保持；大整数文本不因JS Number转换丢精度。 | PENDING |
| P5-T04-V02 | [P5-T04](../previous-v2/plans/tasks/P5-T04.md) | ImageRoundTrip：detail/dataURL/分享与恢复正确，不泄漏localfilepath/secret。 | PENDING |
| P5-T04-V03 | [P5-T04](../previous-v2/plans/tasks/P5-T04.md) | LogCompatibility：forkprepare_detail/schema24/未知扩展展示正确缺值与单位。 | PENDING |
| P5-T04-V04 | [P5-T04](../previous-v2/plans/tasks/P5-T04.md) | NoPhantomFeature：未加载decisionadapter时UI提示实际不可用，不展示假结果。 | PENDING |
| P5-T05-V01 | [P5-T05](../previous-v2/plans/tasks/P5-T05.md) | GeneratedEndpointRegression：三个生成端点/compatproxy仍正确；tools/history/progress/timers全链路有效。 | PENDING |
| P5-T05-V02 | [P5-T05](../previous-v2/plans/tasks/P5-T05.md) | StateVersionNegative：在候选测试目录尝试旧版本payload，明确拒绝且不损坏新状态。 | PENDING |
| P5-T05-V03 | [P5-T05](../previous-v2/plans/tasks/P5-T05.md) | MixedModeIsolation：有adapter时混合Chat/decision/image不跨lane/adapter复用；无adapter时错误资源释放可测。 | PENDING |
| P6-T01-V01 | [P6-T01](../previous-v2/plans/tasks/P6-T01.md) | AncestryBoth：O/U均为candidate祖先；无 -s ours伪合并，patch内容逐项对照。 | PENDING |
| P6-T01-V02 | [P6-T01](../previous-v2/plans/tasks/P6-T01.md) | RetentionComplete：43项账本无未处理；B0/B1/计时/standalone/skip/Docker都映射到证据。 | PENDING |
| P6-T02-V01 | [P6-T02](../previous-v2/plans/tasks/P6-T02.md) | FrozenSuite：模型/resource/dataset/seed/reasoning/tooljudger不变。 | PENDING |
| P6-T02-V02 | [P6-T02](../previous-v2/plans/tasks/P6-T02.md) | NoRegression：建议TTFT p50≤+5%/p90≤+10%、decode p50≥-3%/p10≥-5%，prepare相同相对门槛，精确以P0冻结值为准。 | PENDING |
| P6-T02-V03 | [P6-T02](../previous-v2/plans/tasks/P6-T02.md) | QualityAndCapacity：plans/06选定工程/repo判定/长5needle、共享KV拒绝策略满足冻结条件；样本不足不能说统计非劣。 | PENDING |
| P6-T03-V01 | [P6-T03](../previous-v2/plans/tasks/P6-T03.md) | NoBakedModel：镜像层不包含模型；runtime可读.ninfer但不可写。 | PENDING |
| P6-T03-V02 | [P6-T03](../previous-v2/plans/tasks/P6-T03.md) | NoSharedCache：candidate/prod目录不同；旧profile保留旧codec不被替换。 | PENDING |
| P6-T03-V03 | [P6-T03](../previous-v2/plans/tasks/P6-T03.md) | DrainNoReplay：切换前拒绝新任务/等待活跃请求结束；进行中的tool calls不得自动重放。 | PENDING |
| P6-T04-V01 | [P6-T04](../previous-v2/plans/tasks/P6-T04.md) | ApprovalRequired：未明确批准生产目标时仅test执行，final release状态PENDING而非伪PASS。 | PENDING |
| P6-T04-V02 | [P6-T04](../previous-v2/plans/tasks/P6-T04.md) | CanaryHealth：从受控少量Java会话起步，监测error/toolcorrectness/TTFT/cache/memory，不仅health200。 | PENDING |
| P6-T05-V01 | [P6-T05](../previous-v2/plans/tasks/P6-T05.md) | RollbackUsable：旧实例实际恢复health、一次正常生成和完整tool-call回路；旧cache可用或合法coldmiss。 | PENDING |
| P6-T05-V02 | [P6-T05](../previous-v2/plans/tasks/P6-T05.md) | VersionIsolation：候选payload未写进旧namespace；旧启动参数不混入rk4v4新格式。 | PENDING |
| P6-T05-V03 | [P6-T05](../previous-v2/plans/tasks/P6-T05.md) | ReleaseTruth：源码完成、chat生产资格、optional资格和实际发布状态分别列出。 | PENDING |
| H0-T01-A1 | [H0-T01](tasks/H0-T01.md) | P6GateRequired：B29测量可独立执行；但缺真实P6记录/commit不一致不得宣称H0资格。 | PENDING |
| H0-T01-A2 | [H0-T01](tasks/H0-T01.md) | NoSourceMutation：运行前后用户worktree/index/未跟踪状态不变；source未知不能填猜测SHA。 | PENDING |
| H0-T01-A3 | [H0-T01](tasks/H0-T01.md) | ShapeInventory：每个限制及logicalV/physicalW包含layout/kernel/Graph/commit消费者；B29/E8与B6/rk4v4不得混同。 | PENDING |
| H0-T02-A1 | [H0-T02](tasks/H0-T02.md) | ActualDepth：配置262K但实际只4K不能满足长桶；计数与生成P不符、O_eff/页合同不符或cold实际hit需保留gap，不伪造通过。 | PENDING |
| H0-T02-A2 | [H0-T02](tasks/H0-T02.md) | NoLeakage：相同项目/会话跨calibration/locked-test拒绝；Pi不同分支/压缩状态不能混成同wire。 | PENDING |
| H0-T02-A3 | [H0-T02](tasks/H0-T02.md) | PairIntegrity：缺配对/重复ID/删慢样本/错采样cache/缺raw质量证据拒绝；固定轨迹不能标真实闭环。 | PENDING |
| H0-T03-A1 | [H0-T03](tasks/H0-T03.md) | CommitDenominator：accept=3/completion=2或bonus=1时按原许可/停止合同计交付，anchor不重复。 | PENDING |
| H0-T03-A2 | [H0-T03](tasks/H0-T03.md) | SchemaPreserved：schema20/24与prepare_detail显式映射；缺metric或reasoning补0不能伪造真值。 | PENDING |
| H0-T03-A3 | [H0-T03](tasks/H0-T03.md) | NoSyncHotPath：观测OFF/ON配对，超2%则降采样重测；缺ID映射不能关联错误请求。 | PENDING |
| H0-T04-A1 | [H0-T04](tasks/H0-T04.md) | TokenRowsNotSequences：B4/W16按64列而不是4列分配。 | PENDING |
| H0-T04-A2 | [H0-T04](tasks/H0-T04.md) | NoDoubleSpend：旧head未释放、共享region重复计或负增量来源未知时拒绝free-memory结论。 | PENDING |
| H0-T04-A3 | [H0-T04](tasks/H0-T04.md) | UnknownIsBlocked：缺graph/host/pinned/峰值证据不能标fits=true。 | PENDING |
| H0-T05-A1 | [H0-T05](tasks/H0-T05.md) | SameStartState：prefill拆分或KV不同的两条trace不能当verify单因素A/B。 | PENDING |
| H0-T05-A2 | [H0-T05](tasks/H0-T05.md) | FirstDivergence：人为改变一列position或hidden时能定位第一处差异。 | PENDING |
| H0-T05-A3 | [H0-T05](tasks/H0-T05.md) | BaselineNotFabricated：缺真实artifact/GPU时输出77/BLOCKED，不能生成candidate自指expected。 | PENDING |
| H0-T06-A1 | [H0-T06](tasks/H0-T06.md) | SkipCannotPass：0tests/GPU77/缺required/空metrics或未知quantile-rule拒绝；A1/B100仅p95规则必须FAIL。 | PENDING |
| H0-T06-A2 | [H0-T06](tasks/H0-T06.md) | CommitBound：review/binary/profile/data/hash/schema不一致、配对重复/缺失、warmup混样或p95样本不足均不得通过。 | PENDING |
| H0-T06-A3 | [H0-T06](tasks/H0-T06.md) | NoGoHonest：缺资产/数值失败/未测不能写NO_ADOPTION或QUALIFIED；派生scope不改排除任务真值，baseline不替phasegate。 | PENDING |
| H1-T01-A1 | [H1-T01](tasks/H1-T01.md) | LegacyOff：未传policy时原sampling/greedy CLI/graph/输出保持；不能以greedy资格冒充production sampling。 | PENDING |
| H1-T01-A2 | [H1-T01](tasks/H1-T01.md) | CapabilityReject：未知fingerprint/字段/width、资源或sampling资格未ready时拒绝新配置；请求回原合格sampling，不能暗降ctx/codec/temperature。 | PENDING |
| H1-T01-A3 | [H1-T01](tasks/H1-T01.md) | PhysicalShape：K1/V2和K2/V3都按W4、B*W预算；budget1/2不多发bonus，padding不计有效候选。 | PENDING |
| H1-T02-A1 | [H1-T02](tasks/H1-T02.md) | CrossEpoch：同slot被新请求/改写复用时不能返回旧suffix候选。 | PENDING |
| H1-T02-A2 | [H1-T02](tasks/H1-T02.md) | CollisionAndOverlap：碰撞、同4gram多实例及重叠match均不越界且逐token真实匹配。 | PENDING |
| H1-T02-A3 | [H1-T02](tasks/H1-T02.md) | BudgetTruth：全局早期候选可达；超64候选截断标记与oracle最优差异不伪报exact-search。 | PENDING |
| H1-T03-A1 | [H1-T03](tasks/H1-T03.md) | ConsistentTail：[10,20,30]与同头[10,20,30,40,50]可拼尾，异头不得拼。 | PENDING |
| H1-T03-A2 | [H1-T03](tasks/H1-T03.md) | PartialHead：[11]强匹配替换后不得接依赖旧prefix的[20,30]。 | PENDING |
| H1-T03-A3 | [H1-T03](tasks/H1-T03.md) | BoundsAndSources：K=0/1/5及invalidID/epoch错时明确拒绝或短回退，source mask与有效长度一致。 | PENDING |
| H1-T04-A1 | [H1-T04](tasks/H1-T04.md) | AlignmentAllCommitted：lookup接受数超过神经有效数时，所有已计算且许可hidden均正确对齐。 | PENDING |
| H1-T04-A2 | [H1-T04](tasks/H1-T04.md) | BonusFrontier：全接受bonus已输出但hidden未计算时不提前写aux archive。 | PENDING |
| H1-T04-A3 | [H1-T04](tasks/H1-T04.md) | GreedySameTarget：W4/5/6对ordinary同起始状态完整token序列一致。 | PENDING |
| H1-T05-A1 | [H1-T05](tasks/H1-T05.md) | NoRejectedPublication：未许可token/record不能进入cache或SSE。 | PENDING |
| H1-T05-A2 | [H1-T05](tasks/H1-T05.md) | LaneIsolation：活动lane重排/零长度padding不改变其他请求输出。 | PENDING |
| H1-T05-A3 | [H1-T05](tasks/H1-T05.md) | RewriteWarmReuse：Target热缓存有效时aux冷重建成本可见且不退回完整Targetprefill。 | PENDING |
| H1-T06-A1 | [H1-T06](tasks/H1-T06.md) | SameWidthAttribution：A1/A2的Target/KV/W/语料一致。 | PENDING |
| H1-T06-A2 | [H1-T06](tasks/H1-T06.md) | TokenNotFrame：SSE合并不改变引擎已许可token ID计数与usage契约；不能重tokenize格式化输出代替计数。 | PENDING |
| H1-T06-A3 | [H1-T06](tasks/H1-T06.md) | NoncopyGuard：无命中lookup不会强制长验证，额外CPU成本纳入结果。 | PENDING |
| H1-T07-A1 | [H1-T07](tasks/H1-T07.md) | DeltaProposal：神经/Lookup/selector最终确定链逐位置q=delta，不用softmax/score或accept随机数挑候选。 | PENDING |
| H1-T07-A2 | [H1-T07](tasks/H1-T07.md) | ConditionalMixedPrefix：替换头与保留/截断tail均按最终mixed prefix验证Target p，旧神经prefix的概率/hidden不可错用；C14保守策略独立。 | PENDING |
| H1-T07-A3 | [H1-T07](tasks/H1-T07.md) | ProcessedTargetPrefix：复用实际温度/支持集/penalty顺序与归一化；count=已安装历史+本列前候选overlay，无未来列污染。 | PENDING |
| H1-T07-A4 | [H1-T07](tasks/H1-T07.md) | FractionalAcceptResidual：精确枚举p=(.6,.3,.1)、d=第二项及首拒/中拒/全接受；GPU覆盖非top_k1分数概率，拒绝残差屏蔽d后正确归一化。 | PENDING |
| H1-T07-A5 | [H1-T07](tasks/H1-T07.md) | ZeroOneSupport：p(d)=0/1、support外token、top-k/p/min_p边界与tie/CDF边界不越界、不除零、不裁剪Target全域。 | PENDING |
| H1-T07-A6 | [H1-T07](tasks/H1-T07.md) | BonusCommitStopCancel：all-accept bonus、budget1/2、EOS/stop/取消复用preview/resolve/commit；区分license计数与最终发布前缀，终止/重装后合法请求无污染。 | PENDING |
| H1-T07-A7 | [H1-T07](tasks/H1-T07.md) | SeedDistributionVsPath：同路径完整state/seed可重复，eager/graph/restore/lane分别验证；ordinary/spec分布检验不强求跨路径同seed token相同。 | PENDING |
| H1-T07-A8 | [H1-T07](tasks/H1-T07.md) | LegacyFallback：未资格组合默认OFF并回原合格sampling，原请求T/p/k/reasoning不变；fallback、Target-greedy和旧top_k1不计新sampling资格。 | PENDING |
| H2-T01-A1 | [H2-T01](tasks/H2-T01.md) | ByteFragmentKept：由多个ID拼成中文字符的片段按频次可入选。 | PENDING |
| H2-T01-A2 | [H2-T01](tasks/H2-T01.md) | CoveragePerBucket：不能用英文总体97.5%覆盖中文失效。 | PENDING |
| H2-T01-A3 | [H2-T01](tasks/H2-T01.md) | LockedTestExcluded：评测ID出现在计数输入时fail。 | PENDING |
| H2-T02-A1 | [H2-T02](tasks/H2-T02.md) | TargetUnchanged：转换前后Target SHA256完全一致。 | PENDING |
| H2-T02-A2 | [H2-T02](tasks/H2-T02.md) | MapRejection：重复/负/超域/paddingID与缺scale均拒绝。 | PENDING |
| H2-T02-A3 | [H2-T02](tasks/H2-T02.md) | AtomicPublish：中断在tensor写入后时不能留下可见半成品manifest。 | PENDING |
| H2-T03-A1 | [H2-T03](tasks/H2-T03.md) | TargetVocabFull：Target logits仍完整token_domain，无draft shortlist裁剪。 | PENDING |
| H2-T03-A2 | [H2-T03](tasks/H2-T03.md) | GraphIdentity：换head或resource_generation后不能命中旧图。 | PENDING |
| H2-T03-A3 | [H2-T03](tasks/H2-T03.md) | MemoryActual：同驻旧head时报告额外成本，不能声称理论净节约。 | PENDING |
| H2-T04-A1 | [H2-T04](tasks/H2-T04.md) | RareTargetToken：不在草稿词表的正确Target token仍能输出。 | PENDING |
| H2-T04-A2 | [H2-T04](tasks/H2-T04.md) | MappingExact：row index不能直接当token ID。 | PENDING |
| H2-T04-A3 | [H2-T04](tasks/H2-T04.md) | PerProfileExact：每个拟启用profile过Target-greedy完整输出诊断及生产sampling的H1-T07对应shape/processor/state资格，不要求ordinary与spec同seed逐token一致。 | PENDING |
| H2-T05-A1 | [H2-T05](tasks/H2-T05.md) | CoverageNotTPS：高覆盖但head慢的profile不能仅因覆盖获选。 | PENDING |
| H2-T05-A2 | [H2-T05](tasks/H2-T05.md) | BucketFloor：中文/Java/tools任一较原下降>0.5个百分点时拒绝通用默认。 | PENDING |
| H2-T05-A3 | [H2-T05](tasks/H2-T05.md) | NoGainHonest：未达5%整轮改善时保持旧profile并记录NO_ADOPTION。 | PENDING |
| H3-T01-A1 | [H3-T01](tasks/H3-T01.md) | SeparateMaxima：MTP仍最多5神经草稿，外部K7/逻辑V8由物理W8验证。 | PENDING |
| H3-T01-A2 | [H3-T01](tasks/H3-T01.md) | PhysicalRows：B4/W8按32物理token行，K1/2仍按物理W4而不是validV预算；B*W溢出拒绝。 | PENDING |
| H3-T01-A3 | [H3-T01](tasks/H3-T01.md) | BoundaryBudget：剩余1/2/7/8token按O_eff/文本页和合法物理shape分别判断；padding无许可、bonus不多发，P超C拒绝与输出容量提前结束分开。 | PENDING |
| H3-T02-A1 | [H3-T02](tasks/H3-T02.md) | FullVisibleKV：第0/中/末端key均参与，tail mask因果正确。 | PENDING |
| H3-T02-A2 | [H3-T02](tasks/H3-T02.md) | IndependentOracle：W8单/多lane与独立decode oracle容差一致。 | PENDING |
| H3-T02-A3 | [H3-T02](tasks/H3-T02.md) | ScratchWritten：NaN填充scratch不被未初始化读取，padding行隔离。 | PENDING |
| H3-T03-A1 | [H3-T03](tasks/H3-T03.md) | ReplayPrefixOnly：第j列拒绝后状态等于只提交前j个许可输入。 | PENDING |
| H3-T03-A2 | [H3-T03](tasks/H3-T03.md) | LayerLaneIsolation：多层多lane的conv/key/value/gate地址不互相覆盖。 | PENDING |
| H3-T03-A3 | [H3-T03](tasks/H3-T03.md) | FP32Retained：不得更改persistent GDN dtype以通过显存。 | PENDING |
| H3-T04-A1 | [H3-T04](tasks/H3-T04.md) | Alignment8：全7候选接受后的next proposal状态与独立对齐一致。 | PENDING |
| H3-T04-A2 | [H3-T04](tasks/H3-T04.md) | RejectEveryPosition：每个拒绝位置0..7后续多轮输出一致。 | PENDING |
| H3-T04-A3 | [H3-T04](tasks/H3-T04.md) | NoARInflation：计数器证明没有无意生成7步神经草稿。 | PENDING |
| H3-T05-A1 | [H3-T05](tasks/H3-T05.md) | GraphEagerExact：同shape eager/graph完整输出一致。 | PENDING |
| H3-T05-A2 | [H3-T05](tasks/H3-T05.md) | RouteReached：W8测试必须命中W8kernel/图计数而非fallback。 | PENDING |
| H3-T05-A3 | [H3-T05](tasks/H3-T05.md) | ShapeResourceKey：不同W/B/envelope/资源代次不得复用错误图。 | PENDING |
| H3-T06-A1 | [H3-T06](tasks/H3-T06.md) | LongActual：实际131072及253952输入覆盖，非仅max-context设置。 | PENDING |
| H3-T06-A2 | [H3-T06](tasks/H3-T06.md) | BaselineQuality：Java编译/测试与tool schema不退化；W8生产sampling通过H1-T07对应组合，Target-greedy仅作诊断。 | PENDING |
| H3-T06-A3 | [H3-T06](tasks/H3-T06.md) | NoDefaultWithoutGain：无净收益或不满足长上下文容量则不默认启用W8。 | PENDING |
| H4-T01-A1 | [H4-T01](tasks/H4-T01.md) | WideNotMtp15：W16不能改变MTP神经上限。 | PENDING |
| H4-T01-A2 | [H4-T01](tasks/H4-T01.md) | RowUnits16：token行容量与HQ05负例对应，不混seq单位。 | PENDING |
| H4-T01-A3 | [H4-T01](tasks/H4-T01.md) | ExactCapacity：context及KVpool不能为通过W16启动被静默缩短。 | PENDING |
| H4-T02-A1 | [H4-T02](tasks/H4-T02.md) | FullContext16：首/中/末页依赖与因果mask均正确。 | PENDING |
| H4-T02-A2 | [H4-T02](tasks/H4-T02.md) | ProjectionRoute：所需projection/GQA均达到16列路径，无暗中fallback。 | PENDING |
| H4-T02-A3 | [H4-T02](tasks/H4-T02.md) | NumericBound16：独立oracle+NaN scratch+边界shape通过原容差。 | PENDING |
| H4-T03-A1 | [H4-T03](tasks/H4-T03.md) | AllRejectPoints16：0..15拒绝后KV/GDN/MTPfrontier符合原事务。 | PENDING |
| H4-T03-A2 | [H4-T03](tasks/H4-T03.md) | BonusNotHidden：terminal bonus不能产生伪造projected feature。 | PENDING |
| H4-T03-A3 | [H4-T03](tasks/H4-T03.md) | WidthSwitchExact：固定起始state下6→16→8与固定reference完整输出一致。 | PENDING |
| H4-T04-A1 | [H4-T04](tasks/H4-T04.md) | FreshEvidence：重复round_id、旧requestepoch或DMA未完成均不推进状态。 | PENDING |
| H4-T04-A2 | [H4-T04](tasks/H4-T04.md) | RejectBeatsSticky：任何真实拒绝立即退出skip-proposal，不能hold宽模式掩盖。 | PENDING |
| H4-T04-A3 | [H4-T04](tasks/H4-T04.md) | NoCrossLaneControl：A的复制状态不能让B改变宽度，C>1首版禁Copy。 | PENDING |
| H4-T05-A1 | [H4-T05](tasks/H4-T05.md) | SkipIsReal：copy阶段proposal kernel计数减少，alignment计数按许可状态仍存在。 | PENDING |
| H4-T05-A2 | [H4-T05](tasks/H4-T05.md) | GraphPolicyLive：host状态不会只在capture时运行一次。 | PENDING |
| H4-T05-A3 | [H4-T05](tasks/H4-T05.md) | LateDMAReuse：cancel和lane回收后旧event完成不能污染新请求。 | PENDING |
| H4-T06-A1 | [H4-T06](tasks/H4-T06.md) | CopyEnds：复制结束/源耗尽后不持续浪费宽块，controller按新反馈退出。 | PENDING |
| H4-T06-A2 | [H4-T06](tasks/H4-T06.md) | GreedyDynamicExact：所有动态schedule在冻结prefill下完整token相同。 | PENDING |
| H4-T06-A3 | [H4-T06](tasks/H4-T06.md) | CostNotAcceptance：接受数更多但ms/committed更差时不promotion。 | PENDING |
| H5-T01-A1 | [H5-T01](tasks/H5-T01.md) | RetentionAll：原定制保留账本没有未解释删除。 | PENDING |
| H5-T01-A2 | [H5-T01](tasks/H5-T01.md) | CombinedCommit：数值、build与review绑定同一提交。 | PENDING |
| H5-T01-A3 | [H5-T01](tasks/H5-T01.md) | UnsupportedOff：未合格width/vocab组合在资格表外明确不可启用。 | PENDING |
| H5-T02-A1 | [H5-T02](tasks/H5-T02.md) | AgentOracle：编译、测试、工具schema从真实命令结果取得。 | PENDING |
| H5-T02-A2 | [H5-T02](tasks/H5-T02.md) | ColdWarmSeparated：cold前缀0hit，warm不隐藏初始化成本。 | PENDING |
| H5-T02-A3 | [H5-T02](tasks/H5-T02.md) | AdoptionThresholds：copy快但自由生成退化时只允许特定profile或全部拒绝。 | PENDING |
| H5-T03-A1 | [H5-T03](tasks/H5-T03.md) | ReleaseIdentity：启动模型/镜像/policyhash与资格记录一致。 | PENDING |
| H5-T03-A2 | [H5-T03](tasks/H5-T03.md) | NoSilentFit：不能通过改codec/context让profile运行。 | PENDING |
| H5-T03-A3 | [H5-T03](tasks/H5-T03.md) | ControlledTraffic：流量切换前active=0且exportdrain完成。 | PENDING |
| H5-T04-A1 | [H5-T04](tasks/H5-T04.md) | RollbackTriplet：不是只关flag，旧三件套和schema真正恢复。 | PENDING |
| H5-T04-A2 | [H5-T04](tasks/H5-T04.md) | ResumeWorks：回切后原真实请求/缓存恢复验证通过。 | PENDING |
| H5-T04-A3 | [H5-T04](tasks/H5-T04.md) | ScopeTruth：未做DFlash2不能把E1命名为全融合完成。 | PENDING |
| H6-T01-A1 | [H6-T01](tasks/H6-T01.md) | AssetComplete：任何revision/license/tensor缺项都BLOCKED。 | PENDING |
| H6-T01-A2 | [H6-T01](tasks/H6-T01.md) | GeometryBound：35B checkpoint或错误feature tap/hidden不允许作为27B。 | PENDING |
| H6-T01-A3 | [H6-T01](tasks/H6-T01.md) | NoTargetMutation：转换不改变Target bytes、tokenizer或KVcodec。 | PENDING |
| H6-T02-A1 | [H6-T02](tasks/H6-T02.md) | BlockReset：conv不跨两个请求的物理trained block。 | PENDING |
| H6-T02-A2 | [H6-T02](tasks/H6-T02.md) | NeuralRowsTruth：消费K5不等于只算5物理mask，记录实际行数。 | PENDING |
| H6-T02-A3 | [H6-T02](tasks/H6-T02.md) | IndependentExpected：修改candidate后reference不随之变化。 | PENDING |
| H6-T03-A1 | [H6-T03](tasks/H6-T03.md) | ReferenceLayer：与独立reference逐层一致到冻结容差。 | PENDING |
| H6-T03-A2 | [H6-T03](tasks/H6-T03.md) | NoCrossBlock：不同请求块的conv状态不互串。 | PENDING |
| H6-T03-A3 | [H6-T03](tasks/H6-T03.md) | ScoresNotQ：确定性selector的实际q为delta，分数不冒充概率；Target sampling只在相应资格后开放，真正随机proposal无general-q合同仍OFF。 | PENDING |
| H6-T04-A1 | [H6-T04](tasks/H6-T04.md) | TapsExact：reference指定各层hidden与捕获列一致。 | PENDING |
| H6-T04-A2 | [H6-T04](tasks/H6-T04.md) | CommitOnly：拒绝尾/未计算bonusfeature不进入ring。 | PENDING |
| H6-T04-A3 | [H6-T04](tasks/H6-T04.md) | AuxMissVisible：Target热命中而draft冷时日志和fallback准确。 | PENDING |
| H6-T05-A1 | [H6-T05](tasks/H6-T05.md) | SameTargetGreedy：DFlash2错误提案经Target后与reference完整输出一致。 | PENDING |
| H6-T05-A2 | [H6-T05](tasks/H6-T05.md) | NNotW：W16时DFlash2仍按自己的trainedblock卷积/selector。 | PENDING |
| H6-T05-A3 | [H6-T05](tasks/H6-T05.md) | FaultScope：proposal失败不污染Target；设备故障不伪装可恢复普通拒绝。 | PENDING |
| H6-T06-A1 | [H6-T06](tasks/H6-T06.md) | GraphPointerStable：capture/replay不动态分配或换未绑定buffer。 | PENDING |
| H6-T06-A2 | [H6-T06](tasks/H6-T06.md) | AllCopiesBudgeted：fusedKV/denseweights/head副本等实际驻留均计账。 | PENDING |
| H6-T06-A3 | [H6-T06](tasks/H6-T06.md) | ProfileFallbackReady：MTP未ready时不能宣称无成本动态回退。 | PENDING |
| H6-T07-A1 | [H6-T07](tasks/H6-T07.md) | QualifiedScope：短ctx成功不能覆盖262K主力资格。 | PENDING |
| H6-T07-A2 | [H6-T07](tasks/H6-T07.md) | PreparationCounted：冷/热draft准备和feature构建全部进入TTFT/E2E。 | PENDING |
| H6-T07-A3 | [H6-T07](tasks/H6-T07.md) | ResearchVsPromotion：no gain与not run不同状态，不能混作PASS。 | PENDING |
| H7-T01-A1 | [H7-T01](tasks/H7-T01.md) | IndependentIdentity：不同feature/projection/adapter不互相恢复。 | PENDING |
| H7-T01-A2 | [H7-T01](tasks/H7-T01.md) | CommittedArchive：拒绝尾与bonus缺hidden不写archive。 | PENDING |
| H7-T01-A3 | [H7-T01](tasks/H7-T01.md) | HostCap：与L2/checkpoint/pinned预算共同超过64GBprofile时拒绝。 | PENDING |
| H7-T02-A1 | [H7-T02](tasks/H7-T02.md) | GlobalCoverage：0/25/50/75/尾页均可选，最近65K截断mutation必须失败。 | PENDING |
| H7-T02-A2 | [H7-T02](tasks/H7-T02.md) | BudgetedSelection：返回数量不超过预算且不重复/越范围。 | PENDING |
| H7-T02-A3 | [H7-T02](tasks/H7-T02.md) | NotConstantMemory：索引随页数增长的字节真实计账，不能标O1总内存。 | PENDING |
| H7-T03-A1 | [H7-T03](tasks/H7-T03.md) | ReconstructionReference：与独立逐层DraftKV计算比较。 | PENDING |
| H7-T03-A2 | [H7-T03](tasks/H7-T03.md) | PositionIdentity：相同内容不同映射不能误命中旧stage。 | PENDING |
| H7-T03-A3 | [H7-T03](tasks/H7-T03.md) | TargetUntouched：retrieval选择不改变Target可见KV或GDN状态。 | PENDING |
| H7-T04-A1 | [H7-T04](tasks/H7-T04.md) | LateRefresh：旧request DMA完成不能推进新请求stage。 | PENDING |
| H7-T04-A2 | [H7-T04](tasks/H7-T04.md) | GraphStillUsed：启用retrieval后Draft真实Graph计数仍可验证，不能只声称固定shape。 | PENDING |
| H7-T04-A3 | [H7-T04](tasks/H7-T04.md) | StagingFallback：超预算/超时回ring并记录，不偷偷fullDraftKV。 | PENDING |
| H7-T05-A1 | [H7-T05](tasks/H7-T05.md) | AuxColdTargetHot：不为了建立Draftarchive隐藏重做完整Targetprefill。 | PENDING |
| H7-T05-A2 | [H7-T05](tasks/H7-T05.md) | RewriteInvalidation：被改写页与后继projection/索引失效，之前前缀可保留。 | PENDING |
| H7-T05-A3 | [H7-T05](tasks/H7-T05.md) | VersionRejected：不兼容旧snapshot明确拒绝，不按相同文件名误读。 | PENDING |
| H7-T06-A1 | [H7-T06](tasks/H7-T06.md) | CostComplete：忽略PCIe/rebuild的mutation会被判为不完整输入。 | PENDING |
| H7-T06-A2 | [H7-T06](tasks/H7-T06.md) | ReadyRequired：无resident/auxready的后端不能用0成本参与选择。 | PENDING |
| H7-T06-A3 | [H7-T06](tasks/H7-T06.md) | NoSamplingShortcut：selective每个backend/selector/width/processor组合需Target sampling资格；greedy诊断、fallback或score不替代delta-q/状态证明。 | PENDING |
| H7-T07-A1 | [H7-T07](tasks/H7-T07.md) | FirstPageReachable：actual248K第0页依赖确实进入候选与测试。 | PENDING |
| H7-T07-A2 | [H7-T07](tasks/H7-T07.md) | WholeTaskGain：只有draft局部快而E2E慢不promotion。 | PENDING |
| H7-T07-A3 | [H7-T07](tasks/H7-T07.md) | StateRestoreQuality：跨回合恢复/重写后Target-greedy诊断、生产sampling的delta-q/processor/state与Java任务质量分别不退化。 | PENDING |
| H8-T01-A1 | [H8-T01](tasks/H8-T01.md) | SingleAuthority：无绕过原accept或直接发布Lookuptoken。 | PENDING |
| H8-T01-A2 | [H8-T01](tasks/H8-T01.md) | AllMapped：旧P7–P12每任务都有新owner/处置。 | PENDING |
| H8-T01-A3 | [H8-T01](tasks/H8-T01.md) | AttributionComplete：搬入代码保留文件许可与修改说明，模型许可独立。 | PENDING |
| H8-T02-A1 | [H8-T02](tasks/H8-T02.md) | MatrixComplete：所有对外声明组合都有测试，未测不能靠fallback假通过。 | PENDING |
| H8-T02-A2 | [H8-T02](tasks/H8-T02.md) | NumericsAndQuality：L0–L3诊断、delta-q/processor/RNG/commit的实际sampling组合与旧业务质量门槛分别通过。 | PENDING |
| H8-T02-A3 | [H8-T02](tasks/H8-T02.md) | FailureIsolation：负例后服务仍可处理后续合法请求或按原致命契约退出。 | PENDING |
| H8-T03-A1 | [H8-T03](tasks/H8-T03.md) | NoPeakRanking：381或273不可替代同Target业务A/B。 | PENDING |
| H8-T03-A2 | [H8-T03](tasks/H8-T03.md) | MemoryAndContext：实际主力262Kcontext及KVpool不缩减。 | PENDING |
| H8-T03-A3 | [H8-T03](tasks/H8-T03.md) | PromotionExplicit：研究完成不等于默认启用，未达门槛保持OFF。 | PENDING |
| H8-T04-A1 | [H8-T04](tasks/H8-T04.md) | SnapshotIsolation：旧实例不读新schema/aux数据目录。 | PENDING |
| H8-T04-A2 | [H8-T04](tasks/H8-T04.md) | OperationalRollback：旧镜像+配置+缓存实测恢复。 | PENDING |
| H8-T04-A3 | [H8-T04](tasks/H8-T04.md) | NoUndeclaredChange：无换driver/功耗/权重/联网下载等未批准操作。 | PENDING |
| H8-T05-A1 | [H8-T05](tasks/H8-T05.md) | EvidenceComplete：commit/config/datahash和所有mandatoryassertions互相吻合。 | PENDING |
| H8-T05-A2 | [H8-T05](tasks/H8-T05.md) | HistoricalNotCurrent：旧63helpertests和donor性能不计本版GPU资格。 | PENDING |
| H8-T05-A3 | [H8-T05](tasks/H8-T05.md) | TruthfulScope：高级路线阻断时仅交付已合格E1，不宣称完整H8完成。 | PENDING |
