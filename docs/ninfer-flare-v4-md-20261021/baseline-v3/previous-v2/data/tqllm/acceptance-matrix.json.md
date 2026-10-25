# V2 支撑材料：`data/tqllm/acceptance-matrix.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/tqllm/acceptance-matrix.json -->
<!-- payload-sha256: 45a53f3dbc9cd8c2c28c16c262dee0c99222d31806181c2c4aebfdf70b84b4ef -->
<!-- payload-bytes: 30384 -->

<!-- payload-begin -->
````json
[
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
