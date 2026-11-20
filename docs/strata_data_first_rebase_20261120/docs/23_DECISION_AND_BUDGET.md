# 23｜决策、预算与结果状态

## 1. 延续旧四合同，不另造执行体系

ExperimentSpec定义问题/版本/工作负载/等价/预算；RunEvidence保存事实与附件；Decision给限定结论；BudgetLedger记录费用与授权边界。本包 `templates/*.json` 是**兼容映射草案**，不是可直接喂旧validator的既成实现。P1需显式adapter version，不能静默覆盖旧schema。

**预算数值是上限，授权是外部事实。** JSON中authorized=true也不能授予权限；当前文件全部planned、GPU与请求授权额为0。启动模型、服务或压力负载前需当轮用户给定范围。

## 2. 状态分层

| 状态 | 意义 | 可否启动下一GPU阶段 |
|---|---|---|
| DOCUMENTED / SOURCE_REVIEWED | 方案与源码事实可读 | 否 |
| CPU_FIXTURE_PASS / BUILD_PASS | 对应离线/编译范围通过 | 否 |
| RUNTIME_BOUND | 现场身份成立，不代表负载许可 | 否 |
| DATA_VALID | 已执行的合同范围中数据可比较 | 仅该scope明确允许时 |
| INSUFFICIENT | 缺必要证据/统计功效 | 否；说明最小缺口 |
| CONDITIONAL_AWAITING_AA | 唯一shortlist过4%最低上界筛选，尚缺独立正式AA | 只可另申请P5.0测噪；不能原型/AB |
| NOT_APPLICABLE | 架构/模型/接口不匹配 | 否 |
| ALREADY_PRESENT / NO_NEW_DELTA | 新版已含或只是旧路线改名 | 否 |
| NO_HEADROOM / NO_GAIN | 理想空间不足 / 实测没有净收益 | 否 |
| STOP_CORRECTNESS / STOP_RESOURCE / STOP_BUDGET | 硬停止 | 否 |
| RESEARCH_RESULT_ONLY | 合法研究结论，非上线决定 | 否 |
| READY_FOR_HUMAN_REVIEW | 所有该候选正式门通过 | 仍非自动部署 |

各维度单列：data、numeric、state、task、performance、resource、deployment。不能让单一“PASS”覆盖一堆未执行维度。

## 3. 每次消耗的计账

- request包括prime、warmup、empty/error/cancel、重试、校验及正式生成。
- engine_start包括失败启动与OOM；profile单列，同一个service产生的新engine_epoch计新实例。
- GPU wall按独占研究占用时长，失败也计；CPU-only分析不混入GPU耗时。
- 不允许把P2-L0/P3未用额度转给P5，或因“先做一个小实验”跳过旧路线资格；P5-AA与P5-AB各自预登记与记账。
- 可复用原件优先，缺raw优先列缺口，不自动重跑历史。
- 默认最多评估C01与C02两项，最多一个进入正式原型；其他项目只贡献观测，不用无穷atlas。

live启动前预留在途轨迹与cleanup时间；单调execution deadline必须早于总hard deadline，差额为事先约定的有限cleanup grace。watchdog只能撤销本实验拥有的请求/PID或进程组，owner不匹配不能杀。无法确保隔离、终止或清理可在硬上限内完成则不启动，不能只在超时后“停止新请求”而让长prefill继续占用。

## 4. 有限成本建议

P0/P1先做好来源、解析与CPU验证，P2.0先审L0，再按缺失决策字段选择最小hooks；工时按实际复杂度回报，不承诺固定两天完成。P2-L0与P3按 [19](19_PHASE_TASK_PLAN.md)逐段申请，全部所列可选段合计14引擎/45请求/4GPU小时，**这些不是已获授权额度**。该上限不含另行需要的source-build stock等价验证或P5；缺此类证据时列单独有限申请，不能悄悄挤入当前账本。

若L0已解释主要问题，停止L1/L2；若新基线本身未达绝对质量，交质量诊断，不拿速度弥补。P4离线两张卡若上界不足就结题，成果仍是可复用的可信采集基座。

## 5. 晋级与终止决策字段

最小Decision应有 `candidate_id, old_route_ids, source_delta_refs, runtime_binding_ref, evidence_refs, missing_evidence, headroom_method, estimated_or_measured, quality_gate, performance_gate, resource_gate, disposition, next_allowed_action`。

建议结论措辞：

- “有完整shape census，但未取得设备依赖，无法判断padding可省多少wall；INSUFFICIENT。”
- “同会话旧来源碰撞存在，但现行policy不会采用且乐观净空间不足；NO_HEADROOM。”
- “当前upstream已含相同机制，现场未开启；此为配置生效诊断，不是新算法项目。”
- “CPU fixture通过、GPU未运行；SOURCE_READY而非性能PASS。”

不使用“建议试试看，总会有提升”作为批准依据。

