# 29 / 27B Baseline 先行执行合同（2026-10-21 分层范围修订）

## 当前范围与权威

**当前精简执行选择/顺序/预算以[plans/06](06-staged-evidence-budget.md)为准；本页保留B29身份、参数、计数、cache与可复现合同。**

当前工作模式为 **BASELINE_ONLY**：修订方案/采集工具，在29已有27B执行 [已采纳的分层范围](06-staged-evidence-budget.md)：初始174core+104专项=278请求、Pi44一次/O32768、8工程一次+2repo一次。原672完整目录继续保留但不是首次/每阶段全跑；保存raw/metrics/指纹/可恢复进度，未覆盖仍未资格。未来目标补为greedy/deterministic proposal+原Target sampling，新增引擎实现仍未授权。用户已授权 29 本地推理及有监控的长任务/定时唤醒；本次不开始上游合并、codec 迁移、词表替换、Lookup/W8/W16/DFlash2 等优化实现，不调用付费或其他外部模型。

依据：[2026-10-20 主审查报告](../../ninfer-hyperqwen-v3-review-29-20261020.md)；[本次执行工作流](../../../output/ninfer-baseline-29-20261020/WORKFLOW.md)。主审查报告区分现场实测与待执行合同；专项 review 文档只提供调查证据。2026-10-21新 [范围预算](06-staged-evidence-budget.md) 与 [sampling合同](../design/11-sampling-acceptance-and-proposal.md) 已获授权，替代原672首次展开、Pi×5和20×3通用下限；本页、现行design/07/09及任务修订优先于previous-v2的历史命令/统计缺陷；previous-v2 围栏原件保持字节不变。引用它们不等于允许旧 helper 静默忽略规则。

本 baseline 是原 P0-T04 的生产测量前置，可以在没有 P6 资格时先执行。它不是 H0-GATE，也不免除 P0 的源码/BO 构建任务。P0—P6→H0—H8 的phase级DAG与e1_w6/e1_w8依赖保持，H1内新增T07 sampling资格前置：P6→H0、H5→H6 仍含真实生产 canary/rollback 前置。后续缺该实证时相应阶段 BLOCKED；不能用 B29 baseline 或取消决定填 PASS。

## 1. 四个对象及已知事实

| ID | 对象 | 本次修订时的证据状态 |
|---|---|---|
| B29 / PROD | 29 真实 image、binary、原启动参数、proxy、模型、E8、schema20 | 指纹与短 smoke 已采集；完整 baseline 必须由本次 run 实际结果填写 |
| BO / O | clean `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923` 的冻结构建 | 未认证与 B29 等价；不得用远端无 Git 目录替代 |
| B6 | 实际通过 P0—P6 的集成提交，合格 rk4v4/schema24 | 合格提交仍未提供；不是上游 U 的别名 |
| Cn | B6 后的单因素优化候选 | 本次不实施 |

原 [validation](../previous-v2/docs/05-validation.md) 已规定 PROD/O/C、codec 独立迁移，当前缺的是现场资格，不是重新发明三层 baseline。比较链保持 `B29↔BO`、`B29↔B6`、`B6↔Cn`，最终候选再对 B29 回归。不能把 E8→rk4v4、frontend overlay、schema 改变的收益一起归给 Lookup。

冻结 B29 的已观察锚点：[baseline-manifest.json](../../../output/ninfer-hyperqwen-v3-review-20261020/baseline-manifest.json)。这些锚点必须在每次 run 重新匹配，不当作永远不变的主机状态：

- image ID `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`；`RepoDigests=[]`，不能冒称 registry digest。
- `ninfer-serve` SHA256 `447e37e36deed07e3359609ca41ad248ddf490c4b628c9fd487e0572be3f3c98`；模型 SHA256 `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`。
- 单 RTX4090，GPU UUID `GPU-381cb85f-8ebf-b33e-5076-9305e6af4be5`；driver610.57.04、450W；24564MiB VRAM、约62.46GiB host RAM。空载剩余显存不是负载 headroom 资格。
- `max_context=kv_capacity=262144`、active concurrency=1、pending=8、prefill chunk=1024、rk4v4-e8、MTP3/lm-head-draft、rolling-tool、L1/L2=6144/8192MiB、preserve-thinking、默认max_tokens32768。
- 生产 sampling：temperature1、top_p.95、top_k20、presence_penalty0；proxy 默认 medium。直接 native 省略 reasoning 不能视为与 proxy 等价。
- 生产日志 schema20/prepare_detail 六段；不是方案未来的 schema24。远端 PINNED_COMMIT=44a2c6c、无.git，选定603文件对照仍有旧 frontend 差异，不能证明运行 B0+B1 镜像由该目录构建。

每 run 保存 binary/image/model/launch/proxy hash、完整 resolved argv、非敏感配置、工具链/加载库、source/build provenance、GPU/CPU/RAM/driver、客户端位置。缺 source 构建证明写 `SOURCE_PROVENANCE_UNKNOWN`；可以完成二进制 B29 测量，不能声称源码重建已认证。保留可恢复 image/model/config 位置；不为 benchmark 清理原 image/cache 或更换权重、driver、功耗。

## 2. 两条采样轨与计量合同

`production_sampling_29` 是主力服务收益依据，保留生产采样、thinking/reasoning、工具协议。深度矩阵每格显式 O 与 seed；Pi 原请求回放保留其真实预算，尤其两条异常保持 medium/32768。`research_greedy`另列temperature0的Target数值诊断轨，不能代替保留生产sampling的未来优化资格，也不把其收益扩到production sampling。

未来新hybrid先base/text，greedy/deterministic只指proposal，不改Target生产T1/.95/k20/presence0/preserve-thinking/medium。现有greedy-draft接受器已有delta-q sampling seam，未来优先复用processor/RNG/accept/residual/bonus/commit；新增组合经design/11/H1-T07及shape资格前OFF，未资格请求回原合格sampling。Target-greedy仅诊断；真正随机draft/general-q未在本轮实现。相同seed跨普通/spec不保证逐token同路径，分布资格另证。

计数与时钟要求：

- 保留 engine 许可/停止合同下的 completion token 数、reasoning/content/tool 分项来源；accepted_drafts 不代替 committed/completion。schema20 不具备的 round/ID/分项写 null+原因，不补0、不重新 BPE 显示文本冒充原 token IDs。
- 保存 client ID→响应 X-Request-Id→server_instance_id/request_id 映射。响应 ID 可能被重写，不可只按提交 ID 搜空就断言无日志。
- E2E、首 reasoning/content/tool、工具完整可执行时间、server TTFT 分开；progress/空role/HTTP首字节不算首 token。SSE合并只允许 chunk-gap，不伪造逐 token ITL；全输出单chunk不报0 TPOT/无限吞吐。
- prefill 分子是 computed_prefill；reused 不进重算分子。分别记录总 prompt、请求 output cap、实际输出、缓存来源、prepare六段、queue/restore/prefill/decode/publish。
- GPU/host 序列与 allocator 高水位共同保留，采样100–200ms起步，记录监控OFF/ON成本。能耗按整卡积分并明确并发归属；短请求漏采峰值是下界，不假称最坏资源。

每个 metric 回指原始记录、单位、公式、有效时间区间、缺失原因、schema adapter/hash。旧代理 reasoning_tokens=0 是默认补值，不当真实计数。必需 metric 缺失阻断对应 gate；可测 E2E/总completion 不因缺未提供的逐层数据被改写为0。记录测量覆盖与无法观测范围。

## 3. 声明目录、首次薄覆盖、容量与状态

核心矩阵：[planned-core-matrix.csv](../../../output/ninfer-hyperqwen-v3-review-20261020/planned-core-matrix.csv)，[test-plan-manifest.json](../../../output/ninfer-hyperqwen-v3-review-20261020/test-plan-manifest.json)。672单元=14P×3O×4负载×2cache×2track；它是完整声明目录/历史计划，不等于全部已测，也不再默认一次展开或逐阶段重复。当前执行选择按plans/06的174core+104专项278请求，P256/tool不可表示单列；旧记录状态/manifest保留，不能以精简把未测项改PASS。

| 维度 | 冻结取值 |
|---|---|
| 最终实际 P | 256、1024、4096、8192、16384、32768、65536、98304、131072、163840、196608、229376、245760、253952 |
| 显式 O | 128、512、2048；额外长输出8192与Pi原32768另列 |
| 负载 | copy/patch、自由Java、中文分析、tool JSON；多份冻结语料，不用一句重复填充 |
| cache | request-cold：reused=0；warm-prefix：明确前置轨迹与实际命中来源/数量 |
| track | production_sampling_29、research_greedy |
| 主要引擎配置 | 原262144共享KV、C1、prefill1024与E8不因P变动 |

P由最终模板/system/tools/历史/思考控制处理后实际token数确定。使用运行模型同资源的计数/prepare路径校准并由生成日志复核，目标不可达则报错或事前冻结真实P，不测后归入近似档。B29不能将“P+O+固定正reserve≤C”当真实输入准入公式；下述实际容量合同替代本包/历史资料中的通用P+O+R说明。

令C为实际max_context，O为请求上限。只读核查clean O的 [request_plan_impl.h](../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/targets/qwen3_8/impl/runtime/request_plan_impl.h) 第61–123行与 [program.h](../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/targets/qwen3_8/impl/runtime/program.h) 第62行得出以下合同；这是源码证据，B29镜像含overlay，必须由实际prompt/finish日志及边界用例复验，不宣称所有边界已运行：

```text
P > C                         → 输入拒绝
O_eff = min(O, C - P + 1)      → 实际容量输出上限，不等于一定生成这么多
F = max(O_eff - 1, 0)         → 最后一个采样token无需再作为下一步输入进入KV
initial_text_extent = P + min(F, 4096)
ceiling_text_extent = P + F
MTP_backend_extent(T) = min(C, T + draft_window - 1)
```

文本KV按extent取页，初始只预留4096 decode window，后续增长不超过ceiling；MTP backend/物理scratch/Graph/GDN资源另行计账，不从逻辑context扣拍脑袋固定R。原请求O超过容量输出上限时可正常生成后以内部ContextCapacity提前结束；不是一律400。外部OpenAI的length可能不能区分OutputLimit/ContextCapacity，必须保存server request_done.finish_reason与请求O、源码推导O_eff、实测completion。自然EOS/stop也可能更早结束。

精确边界：`P=C−O+1`可容纳O；P再+1时O_eff=O−1并走ContextCapacity，而`P=C+1`才应输入拒绝。253952输入在C262144时容量上限为8193输出，不意味着默认32768都能生成。可以预登记保守qualification预算`P+O≤C`，但需注明比真实+1合同少一个可用末token；不得把保守预算当实际API语义。

计数优先预检 `/v1/messages/count_tokens`：该产品frontend包含system/tools/thinking，count不提交KV、不生成，因此不把计数校准本身算作prefix预热。`/v1/responses/input_tokens`仅支持窄字段，不能拿它省略tools/reasoning来算完整chat。简单无历史chat+tools转换须保留description存在性、schema、strict:false归一化、thinking/effort/preserve_thinking；代理默认medium不能被native默认污染。复杂Pi历史的tool arguments空白/键序、多system/developer和text拼接可能跨协议变字节，同tokenizer不等于同prompt。必须保留校准body/hash/response，并与相同正式chat的server prompt_tokens核对；不一致记TOKEN_COUNT_MISMATCH/BLOCKED。只有count值而无token IDs时明确IDS_UNAVAILABLE，禁止重BPE显示文本伪造。

在672目录之外还有以下合同场景；首次按plans/06挑104专项，后续按实际变更/发布声明覆盖，不要求每阶段全部重跑：service-cold/ready（OS page cache 状态单列）；长输出8192；Pi原预算；历史ladder精确锚点；context临界/+1、chunk/page/graph边界；S0–S8缓存/会话、队列/取消/故障、实际支持协议、隔离Agent任务。最大可行与不支持案例明确记录 UNSUPPORTED/BLOCKED 并验证受控拒绝；不静默缩P/O。

正式core保持B29原argv，不启用`--no-prefix-reuse`或其他禁缓存变体。每次请求保留expected_cache_state与observed_cache_state：request-cold只有server `prefix_cache_hit_tokens=0`、`computed_prefill_tokens=prompt_tokens`且实际full_reset路径对上才达标；不以“第一次”、nonce、新session/key当证明。预期cold实际hit的attempt原样保留，记CACHE_CONDITION_MISMATCH与coverage gap，不能删掉或暗改expected以凑通过。允许把它作为额外warm观察，但不能抵扣cold必测单元。warm有指定前置轨迹并核对真实source/reused，checkpoint可能重算尾部，不要求computed=0或整个P全命中。

B29没有通用clearcache或每请求cache_prompt:false控制。`POST /slots/0?action=erase`需要slot-save-path，否则501；即便erase成功也不清continuation L2 aliases/images。DELETE Response不是清KV，换prompt_cache_key只是路由hint。不能通过这些操作宣称已经制造cold。监控/runner将不达标的core单元留gaps，不能为“全通过”偷偷改原argv。未来若另行明确选择cold_no_reuse，只能作为独立测量profile冻结仅增加`--no-prefix-reuse`的差异，绝不混入或顶替本轮正式core。

状态集仍覆盖exact、固定历史append、近/远tool或system/tools改写、branch A→B→A、受控L1驱逐→L2恢复→miss、重启、target热/aux冷；该版本无控制能力则明确BLOCKED/UNSUPPORTED并保存证据。L1/L2均为进程内，重启不虚报L2持久化。暖固定回放使用冻结历史assistant/toolResult，不把新生成结果接入下一固定请求；真实闭环另用自己的真实结果。测试实例/独立cache路径不自动保证物理cold，不drop_caches、不清生产用户缓存。

B29 activeC1；先测2/4客户端排队/公平性/超时，不改配置冒充C4 baseline。C2/C3/C4只属后续候选独立资格：按各lane初始/ceiling文本页、clamp后的MTP backend页、状态/物理scratch预算核对shared pool和运行时growth。`Σ(Pi+Oi)`仅是可预登记的保守最坏检查，不是源码唯一准入公式；预算可行也不保证显存可行，不承诺每lane262144。pending8与超额、取消释放测实际准入。取消请求不能臆造可用后台cancel端点：B29 Responses cancel对已存在Response会返回background_not_supported；SSE断开后还需slots/日志证明在途结束和下一合法请求可处理。正向工具走支持的auto，named tool_choice=400作为旧能力负例，不混进旧成功分母。

## 4. Pi 真实 session 的两层验证

当前 Pi 1.3.0/Node22.19.0 与当前默认 contextWindow/maxTokens 不是历史 wire 配置。session 是 parentId 事件树；必须恢复选定 leaf/entry 前的父路径、compaction/context_edit/custom扩展和system/tools投影，不能简单筛全部messages或直接resume。私有session/wire只留受控位置，报告存hash与结构；不复制凭据或读取无关auth。

**A层：固定请求/固定轨迹回放。** 冻结原session SHA、leaf/entry、分支、serializer/Pi/扩展、工具schema、reasoning/采样/预算、client wire与proxy规范化engine payload hash。能与原wire/token/server记录唯一对齐的标 `HISTORICAL_WIRE_VERIFIED`；历史材料不齐、由冻结当前serializer重建的标 `FROZEN_SESSION_DERIVED`。两者都可做后续字节一致A/B，但后一种不冒称历史精确复现。只向29本地27B请求；历史assistant/toolResult是固定下一轮上下文，不执行返回工具，不据此宣布任务成功。

必须包含真实长会话，及session `01a0f307-01d6-768d-92ec-f8512b8c047e` 中 `f89c5dcc`、`97fc7be6` 和相邻轨迹：原 prompt分别20597/22345（Pi usage.input+cacheRead）、medium、O32768、曾仅thinking/output_limit且无tool。不得插入 `</think>`、降低预算、丢弃失败来“修好” baseline。历史引擎无法唯一确认标 `ENGINE_IDENTITY_UNKNOWN`，可作语料，不作旧27B速度证据。

**B层：隔离 Pi 闭环。** 从冻结项目/fixture创建独立工作区与新session，固定Node/Pi/system/tools/extensions/model/reasoning/采样/轮次/超时。各variant执行自己的真实工具并把自己的结果接回；自然分叉，比较任务总wall、模型等待、工具时间、编译/测试、循环/失败/耗尽，不能喂历史结果冒充真实执行。历史bash/edit/write不在原cwd重放，不调用外部写入/付费provider。撤回20Java×3通用下限。现行工程初始旧3题+QCB5题各1次、真实repo2题各1次；发布8题×3seed+2repo=26任务/variant，逐题/seed配对而非pass@3。合成17题可留诊断，真实repo环境未齐NOT_RUN，不阻塞全P参考，且这些小工程不冒称Spring/MyBatis/数据库集成资格。

A、B层分别报告。当前授权“Pi真实session回放”必须完成A层；需要对任务成功率或Agent总wall作声明时，B层是不可省略的证据。若本轮未执行B层，明确 CLOSED_LOOP_NOT_RUN，不能把A层命名为真实任务闭环。所有assistant/request去重汇总全任务usage，不能复用只取last_usage的旧parser。

## 5. 统计与 fail-closed

初始T0按plans/06的278请求+8工程/2repo，优先两条Pi异常/旧三题与全P薄层；已有A/A/监控前置按最早有效证据复用，不整套重跑。44Pi每个一次，O32768不改；初始不承担发布p95/CI。

T1每阶段相关A/B总额≤240、至少3交错时间block，状态前置/warmup/重试与哨兵模型调用先留预算，必要时减少格数；硬数值/状态合同不省。T2仅H5/H8对实际发布profile做关键case≥10有效配对/至少5block/3warmup、p95桶≥100/variant和CI；不足INCONCLUSIVE。672仍是声明目录，正式采纳须对具体声明有足够证据，但不把全部目录都安排到第一次或每阶段。一次预登记追加仍不清楚就停止采用，不无限采样。20×3不再是通用必选。

基线A/A应先测漂移；不同candidate采用A/B/A或ABBA。bootstrap建议10000次/95%CI/固定seed，按case/会话聚类并配对重采样block。相关turn/tokens不算独立请求；不同长度/cache/采样比例不测后拼桶凑100。异常排除只按事前环境规则，整block归档重跑；候选自身OOM/超时保留为可靠性失败，timeout是censored/deadline而非0ms。探索样本不能升级为正式尾延迟资格。

已复现旧 `merge_tools.py` 对 `p95_relative` 静默忽略、100倍恶化仍passed=true。因此恢复旧工具只作历史支撑；执行门禁必须验证规则allowlist、未知quantile/字段拒绝、metrics非空、缺值、配对缺失/重复、样本数、身份、错误schema、warmup混入、错误hash、required skip/0tests。必须保留A=1/B=100且唯一p95=.05的失败负例。p95/配对聚类CI未实现或数据不足为BLOCKED/INCONCLUSIVE，不能把空检查当通过。

采用门槛按design/07冻结；当前只测B29 baseline，无candidate，不产出“提速通过”或promotion。对未来跨codec用独立质量/数值门，同codec/同prefill的新greedy路线仍严格输出/状态合同。

## 6. 长任务、监控与恢复

单一GPU owner。启动前冻结runner/monitor/normalizer/statistics版本hash、expected cases与预算/截止、环境指纹、队列/服务owner；检查无其他推理负载。服务启动、切换和恢复由ROOT统一执行。不能由多个worker轮流占卡或同时驻留两个27B。

执行器写append-only attempts/raw、每case结果、原子status/heartbeat和checkpoint；至少包含run_id、manifest hash、job PID/启动身份、current case/attempt、completed/failed/remaining、last progress、deadline、error、next action。每次请求有HTTP/整体超时、取消/排空契约；故障保留raw和stderr，受控重试用新attempt ID，原失败不被覆盖。恢复时只认完整且hash匹配的case，warm链从受控前置状态重建，不能从未知cache继续冒充同态。

监控脚本负责检测job退出、心跳停滞、deadline、GPU/主机异常、状态与结果不一致，产生可恢复失败/完成摘要。实际监控周期与阈值写manifest，不假定“进程活着=在推进”。经一次正常推进与一次受控监控失败/退出路径验证，再安排已授权定时唤醒检查本线程。agent在确认job与监控已建立后让出回合；不主动频繁轮询、不断sleep/poll浪费token。自动唤醒也先读取status/新增证据，只在需要恢复/决策时操作。

不为制造故障杀生产服务。脚本收到取消信号先停止新请求并记录在途/排空情况；不得无限重启模型。资源/容量/协议错误先归因，禁止默默改ctx/codec/输出预算求通过。

## 7. 证据、完成与未完成

每run保留manifest、dataset/wire/token/hash、expected-case状态、client原始SSE/monotonic事件、server原日志、GPU/host序列、质量/编译测试、normalizer样本、statistics/CI/样本数、coverage、gate与SHA256SUMS。私有原件留受控本地，仓库只存非敏感指纹/摘要与采集器。包含任何失败、取消、重试、deadline与观测缺口。

状态分开：`PLANNED/NOT_RUN`、`RUNNING`、`COLLECTED`、`FAIL`、`BLOCKED`、`INCONCLUSIVE`、`BASELINE_QUALIFIED`；COLLECTED仅说明样本落盘，不代表统计、质量、资源或可复现通过。当前参考集交付要求plans/06所选mandatory案例有最终状态/证据或明确gap、B29 A/A与指纹可追溯、44Pi A层一次及工程8+2各自状态；未就绪repo或条件未达项保持未完成。参考集完成与正式性能资格分开，只有发布声明对应正式门槛满足才QUALIFIED；未跑的672组合继续未资格，不把启动job或278落盘称全scope通过。

基线结果不自动修改P0/H0或任何phase为PASS；须经相应组合review及原gate。优化仍OFF，BO/P6未构建/迁移时保持NOT_RUN。实际运行进展以本次run证据为准，本页不预填性能数字或完成时间。原argv/actual-cache约束未满足的单元必须留coverage gap，不能宣称完整BASELINE_QUALIFIED。

## 2026-10-21执行切换

已批准采用plans/06；旧重计划在当前请求可靠落盘后停发、排空并归档，实际停止/接续由ROOT执行，本文不冒称已做。新runner/analyzer/orchestrator须消费同一版本化计划，不只改manifest数字。复用最早有效记录，保留3份损坏raw等旧失败和runner修订/重启身份；单GPU锁、durability、unknown inflight禁止盲重试、监控/定时唤醒规则继续有效。未来sampling合同是拟实施OFF状态，不因原kernel已有能力就声明Lookup/宽块新组合已上线。
