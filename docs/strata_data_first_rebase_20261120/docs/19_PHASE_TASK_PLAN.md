# 19｜AI 可执行 Phase / Task 计划

状态：PLAN_ONLY。实施根为既有 `docs/strata_4090_128k_lab`；上游patch放独立worktree，不改生产/回滚树。本包从P0重新建立新版证据，不续用旧P00/P01的执行权限。每个Task先失败fixture→最小实现→回归；每Phase独立review通过才进入下一Phase。

## 0. 执行合同

- Phase串行，任务内需相同文件的工作串行；仅接口冻结后可并行。GPU任务全局串行。
- 每次工作开始核当前branch/dirty/worktree，保留用户改动；没有可复用实现才创建标PROPOSED模块。
- 不运行本包不存在的CLI。所有下列新测试文件是要创建的目标，执行前列明选择的test runner与预期失败。
- 新字段遵循 [05](05_DATA_MODEL_AND_MEASUREMENT.md)，挂点见 [06](06_MINIMAL_INSTRUMENTATION.md)，测试ID见 [20](20_ACCEPTANCE_TEST_MATRIX.md)。
- 独立review检查事实/权限/统计/隐私/数值，不仅代码风格。Phase产物缺失就BLOCKED，不以“后面会补”跨门。

## P0｜权威基线、旧结论与现场可行性

| Task | 工作与文件 | 最小验证 | 产物 / 停止门 |
|---|---|---|---|
| P0.1 来源与版本锁 | 核本包source_lock，现repo最新commit与两个旧包；核上游release/refs/annotated tag；不跟随main自动升级 | T01/T02：tag/asset/build不同身份不能互填 | SOURCE_BINDING，已读范围/缺口 |
| P0.2 复用盘点 | 读 `lab/runner.py,http.py,tools/frontier/contracts.py,identity.py` 与P01B；检查现场是否新增实现；将 [03] 变实际文件清单 | T03：不存在控制器不可调用；老schema保持可读 | REUSE_MAP，精确模块与owner |
| P0.3 研究配置与权限 | 有授权才只读盘点目标机、当前运行PID/端口/资产；绑定SM89、主存、PCIe、model/draft/KV/tool模板 | T04/T05：prepared不等于running；超窗拒绝 | RUNTIME_BINDING或明确UNBOUND |
| P0.4 有限计划冻结 | 选择新source build或正式发布制品为唯一实验base；指定是否允许CPU构建/服务/模型；预登记所选诊断用例/oracle、统计方法与运行中截止，并列正式质量合同缺口；不改CUDA12.3保护规则 | 若新source不能在合法toolchain构建则BLOCKED，不自动升driver/toolkit；所选诊断oracle/owner/deadline未绑定不运行 | EXPERIMENT_SPEC与0预算初始ledger |

P0.1/P0.2可并行，P0.3取决权限；P0.4串行。版本研究可完成而现场未绑定，不能因此进入P2.0或P3的live部分。有限诊断必须冻结自己的case与协议/任务oracle；完整业务绝对质量另需required case IDs、既有gold引用、结构/真实工具执行、数值/状态等价、缺题政策与阈值。后一组尚未齐备可作明确限定的诊断，不得晋级候选正式正确性/性能PASS。

**Review P0**：old/new模型不混；latest稳定tag、engine归属和binaryhash分开；已测FAIL、未测、doc-only区分；各source许可和不适用项明确。

## P1｜先让现有数据能可靠进入证据合同

| Task | 精确改造目标（PROPOSED） | 最小测试 | 验收 |
|---|---|---|---|
| P1.1 规范化适配 | `tools/frontier/telemetry_adapter.py`：按source version适配JSONmetrics/telemetry/BSTAT；复用现有parsers，不改公共字段 | 新 `tests/test_frontier_telemetry_adapter.py`；T06–T12：0/缺值/代理指标/重启/scraper窗口/格式错 | 每值保留单位、scope、freshness、原始source |
| P1.2 关联与封套 | `tools/frontier/event_contracts.py,evidence_join.py`；给原contracts增附件引用，不改旧archived对象 | `tests/test_frontier_event_contracts.py,test_frontier_evidence_join.py`；T13–T18 | request/leg/epoch与clock不歧义；拒drop/错PID |
| P1.3 客户端分层 | 扩 `lab/http.py`：harness ready/send/首semantic事件/结束分开；保持 `token_itl_ms=None` 除非真timestamp | `tests/test_frontier_sse_semantics.py`；T19–T22 | SSE chunk不伪装token；失败/工具-only/重试保留 |
| P1.4 报告与预算 | `tools/frontier/evidence_report.py`；若缺薄控制器则在既定 `exploration_control.py` 补仅离线前置与账本 | `tests/test_frontier_decision_budget.py`；T23–T25 | 未授权不能调用runner；缺数据不能PASS；旧四合同可读 |

先冻结P1.1/1.2接口再并行客户端/报告；最后统一merge到独立实验分支。不得为了表格齐全引入第二套HTTP采集服务。

**Review P1**：全部CPU fixture与旧Lab自检；旧50tests不冒充新验证。产 `ADAPTER_COMPATIBILITY.md`、schema coverage、negative-case回执。尚无模型请求，不宣称observer开销达标。

## P2｜先用L0回答问题，再决定最小hooks

**P2.0是写新engine hook前的门。** 优先复用同一当前身份、合法窗口与工作负载的有效L0原件；不足且获得当轮授权时，先做下表P2-L0有限采集。先给出“哪一个决策字段缺失、为什么现成接口/日志回答不了”的清单，再逐项实例化P2.1–P2.3。cache疑问不自动授权round/shape挂点；L0已经回答问题则跳过全部新hooks，直接进入P3报告。没有原件或执行权限就BLOCKED，不以此理由先把全部hooks写完。

P2-L0若使用来源未知的Linux正式制品，其数据不能充当64524fb9源码构建的stock臂。L1必须绑定同一source/toolchain/build features的原版与patched-off/on，必要时单独申请source-build基线身份与比较范围；不能凭相同版本字符串继承L0有效性。P3-L1的6引擎/18请求只覆盖三对off/on；如还缺stock→patched-off实证，先列缺口、另行明确有限预算，不挤入或暗增该额度。

| Task | 上游/本地文件目标 | 测试与验收 |
|---|---|---|
| P2.0 L0资格 | 复用P1 adapter与已有runner，取当前同身份证据；记录决策缺口与每个拟补hook的必要性 | T38初筛；L0足够则后续hook均NOT_NEEDED；无原件/授权则BLOCKED |
| P2.1 生命周期关联（条件） | `terminal/serve/server.py`、`server_parts/core.py`及实际engine generate通道；匿名HTTP→leg/slot/epoch | T26/T27：串行/parallel admission不同含义；多leg/重启/cancel；不得改prompt |
| P2.2 cache与prefill（条件） | `engine/src/program/generate.cpp`、`engine/src/core/conversation_state.cpp`、`engine/src/prefill/prefill.cpp`；选择/restore/prepare/plan固定buffer | T28–T31：live/RAM/SSD/重算及组件bytes分开；logical与physical可重叠；合法release owner |
| P2.3 round与shape（条件） | `engine/src/core/verify.cpp`、`engine/src/core/expert_source.cpp`、`engine/src/kernels/cpu/pool.cpp`、generate；source/committed/ready-hit与physical shape | T32–T35：下一round draft归属、EOS裁剪、图capture/launch、计数分母与溢出 |
| P2.4 集成与关闭态（仅对已实例化hook） | 封装于新实验专用header（优先复用Lab P01B buffer设计）；闭合旧runner新 `engine/terminal` 路径 | T36/T37：关态无额外clock/allocation/sync/I/O；构建合法SM89；未授权不launch GPU |

只有通过P2.0必要性门的hook可在冻结统一record布局后分工；修改 `generate.cpp` 有同文件冲突必须一名integrator串行落地。不把“每层所有kernel全计时”加入本phase。未选择的hook与其GPU验证标NOT_RUN，不把范围缩减写成通过全部。

**Review P2**：先审L0原件与hook必要性，再审所选源码是否清晰、无热路径同步、字段只读、边界有测试、无需新调度policy。CPU/build测试通过仍为SOURCE_READY，不能称GPU正确。无hooks时按L0诊断路径交接，不强制构建引擎。

## P3｜先测观察器，再取得新版事实

### 建议的分段上限，而非自动额度

| 子段 | 最大新开引擎 / 请求 | 目的 |
|---|---:|---|
| P2-L0（前置） | 6 / 18 | 新hook前的3对现成observer off/on，每engine一个合法长prime+exact repeat+真实append；有合格原件则不重采 |
| P3-L1 | 额外6 / 18，必须单独获准且L0不足 | 相同合同对新hooks做关闭/开启比较；不改算法或draft模式 |
| P3-CASE | 额外1 / 6，仅确有会话/边界疑问 | W05/W07中一组，或明确内容采集授权下替换为C01所需W09；不叠加额度 |
| P3-L2 | 额外1 / 3，仅依赖仍未知 | 一次限定profile轨迹；仅与已有同构建/输入/状态可比off臂对照，不能塞入一次额外fresh off确认 |

P2-L0和全部P3可选段都批准时总上限 **14 fresh engines、45请求、4 GPU小时**，以先到者停；不含另立的source-build等价门或P5。当前授权额全部为0。请求包括warmup、prime和失败；不得把取消/重试藏在上限外。启动前预留每条轨迹的可行时间，锁单调时钟deadline、有限cleanup grace和仅实验自有PID/进程组的watchdog；到限撤销在途实验并清理，清理也计账。无法安全强制终止实验而不影响生产则BLOCKED。若单请求时间导致预算不可行，缩范围或结束，不擅降上下文改变合同。

| Task | 方法 | 最小验收 |
|---|---|---|
| P3.1 observer校准（条件） | L0结果复用P2.0；仅对所选L1做独立off/on，实际route与输出一致，thermal/cache顺序记账 | T38：L0≤1%/L1≤2%时间CI目标；3对为SCREEN_ONLY，方法/功效不足则INSUFFICIENT，不盲加次数 |
| P3.2 新基线 | 从有效P2.0/P3数据复用身份/请求/cache/shape/round摘要；输出可回答与未知 | T39：无旧baseline混入；错误任务不争速度；无新hooks不强制重采 |
| P3.3 有限依赖捕获 | 只在已经看到成本空间时做L2；绑定PID/clock/stream/request | T40/T41：区间并集与依赖闭包；丢失/扰动不授性能PASS |

**Review P3**：报告不是“几张utilization图”；能解释至少所选case的wall、reuse与数据覆盖。若绝对质量/资源不合格，先交问题诊断，不进P4优化。

## P4｜离线反事实，最多两张资格卡

| Task | 模块/输入（PROPOSED） | 最小测试 / 停止 |
|---|---|---|
| P4.1 C01 | `tools/frontier/suffix_counterfactual.py`；已获内容使用许可的W09同会话prompt/committed token trace + pinned old/new索引语义 + 当前DraftPolicy/verify成本 | T42/T43：生成proposal不读未来/跨会话；事后oracle可比已录答案但仅为上界；无trace则INSUFFICIENT，普通L1摘要不能替代 |
| P4.2 C02 | `tools/frontier/shape_census.py`；实际grid/rows/route+有依赖的时间 | T44/T45：padding分母正确，overlap不重复；NVIDIA归约改变退出exact |
| P4.3 统一资格 | 复用headroom与04/05证据，填写旧路线差量/不覆盖原因 | T46：上界不足NO_HEADROOM；未知INSUFFICIENT；上游已有ALREADY_PRESENT |

可并行做CPU分析；不写GPU策略、不改codegen/quant。完整资格门为至少max(4%,2×AA)可闭合净时间空间，而不是接受率或padding率超过某数。**若尚无同一R身份可复用的独立正式AA，不能令AA=0：乐观上界低于4%即可NO_HEADROOM；达到4%但AA缺失仅为CONDITIONAL_AWAITING_AA。** 只有机制、数据与正确性前提齐备的最佳单项可申请P5.0独立AA，尚无原型或A/B额度；AA取得后必须重算完整门。

**Review P4**：最多保留一个单项。已有独立AA且完整门成立才可申请实现预算；缺AA只可申请P5.0测噪预算，不能提前实现。全被淘汰也完成本次探索。

## P5｜一个候选的独立原型与正式验证

P5不预定义不存在的patch，也不给自动实验额度。不能借P3剩余额度执行。顺序如下：

0. **P5.0 AA资格门**：优先复用同一R身份的有效独立AA；没有则为P4唯一shortlist单独申请P5-AA有限同实现配对。先锁方法/独立单位/预算，测完重算max(4%,2×AA)。不满足就NO_HEADROOM/INSUFFICIENT并结束，不创建算法原型。P2/P3的off/on三对不能充当此独立AA。
1. **P5.1 独立原型**：完整门及质量前提成立后另获实施范围，补精确源码diff、oracle与资源cost；新开隔离worktree、feature默认off；先off对stock、局部数值/状态，再on。
2. **P5.2 局部验证**：真实形状与成本，不变更模型/量化/采样/窗口来躲问题。
3. **P5.3 正式AB**：另立P5-AB六对主指标计划（仅在既有paired_stats适用时），所有预登记护栏同时测，保留所有失败；不能把AA启动藏在六对AB内。
4. 质量、恢复、取消、内存与连续任务通过；达到相对收益门且预登记required cases/gold/阈值全部可审核，才READY_FOR_HUMAN_REVIEW。缺绝对质量合同、缺必测任务或工具未执行均不能晋级，不能用汇总均分补掉。
5. 单独决定是否部署；本计划不自动覆盖生产。

测试 T47–T50。任一正确性失败立即停；无净益归档NO_GAIN；预算耗尽INSUFFICIENT。不要追加第三第四个候选让失败“均摊”。

## 每 Phase 统一交接格式

`scope / source+runtime hashes / modified files / tests & exits / result level / missing fields / invalid cases / budget consumed / independent review / next_allowed_action`。

建议实施先交P0–P1与P2.0缺口清单；仅在证据与权限齐备时进入所需hooks。不承诺工程天数或最终提速幅度。可观测底座完成与找到性能收益分别验收。

