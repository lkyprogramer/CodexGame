# Strata 4090 单候选研究 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将一个获准的新机制转化为可审计的研究结论；证据不足时有界停止，不改变生产。

**Architecture:** Phase串行，独立离线取证Task可并行，硬件执行严格串行。先做身份/原件/机制资格，再做最小语义和资源验证，最后才是已预注册的性能与任务质量；每个Phase以独立审查回执作为下游输入。

**Tech Stack:** 既有Strata C++/CUDA引擎与Python控制层、现有离线统计/质量工具、Markdown/JSON/JSONL证据；禁止为本计划先建大型框架或升级CUDA环境。

**Spec:** [02_CANDIDATE_DESIGNS.md](02_CANDIDATE_DESIGNS.md)；约束协议为 [04_BENCHMARK_QUALITY_PROTOCOL.md](04_BENCHMARK_QUALITY_PROTOCOL.md)，字段模板为 [06_HANDOFF_TEMPLATES.md](06_HANDOFF_TEMPLATES.md)。执行者必须同时阅读。

## Global Constraints

- 原冻结合同 F：GSQ-RCO IQ3_XXS 混合包、INT8 KV、resident=20480、max-context=131072、另留4096 token安全余量、spec=4、spec-min-p=0.5、会话缓存6144 MiB总预算/4 slots；其余按 P6 身份原件。
- A0 指历史生产保护对象；B 指 P6 研究基线；A1 指候选二进制关闭路径；C 指候选开启路径。统计里的 A 必须显式绑定 B 或经桥接验证的 A1。
- 不升级生产，不改 unit/NGINX/18343，不操作旧回滚树，不安装驱动/CUDA，不降低资源保护门，不关闭 thinking 或缩短上下文换取成绩。
- 只批准文档不等于批准 GPU、降精度、改服务或下载新模型。未来实验须单独批准候选、身份、预算、端口和退出方式。
- 同一轮只准入一个候选、一个主要假设、一个主指标。新引擎版本、编译器、KV、resident、词表、COUPLED 和 HC 不一起改变。
- 原六项长检索 FAIL、P05 `BLOCKED_EVIDENCE` 和 `NO_QUALIFIED_CANDIDATE` 保留；没有新证据就停止，不自动补跑。
- GPU温度达到85°C、MemAvailable低于4096 MiB、外来GPU负载、身份/预算违约或OOM即停止。本包未核查当前机器是否空闲。

## Review Focus

1. 文档授权被误解为GPU/生产授权：Task2检查缺批准或预算为0时没有任何硬件动作。
2. 同名模型/版本不同二进制，或草稿参数偷偷改变target：Task1/3检查hash、env不存在状态与采样语义。
3. 自然prime改变append历史，recipe hash掩盖不匹配：Task1/4检查实际body/token身份，首次不符停止。
4. 资源门、OOM、短输出或swap被事后剔除：Task3/4保存所有失败和累计消耗，不补跑替换。
5. 性能PASS掩盖两臂都失败或质量样本不足：Task5/6分别检查相对质量、绝对质量和最终状态。

---

## 0. 授权与目录说明

本轮已经执行的是**调研与本套Markdown文档生成**。下列checkbox表示未来研究任务，不表示已经批准或运行。当前GPU预算0、生产变更预算0；本计划不需要被“全部跑完”才算交付成功。

将来如果用户要求纳入CodexGame，建议新建文档目录：

`docs/strata_4090_128k_lab/frontier/proposals/N20261102/`

下文以 `R/` 表示这个**建议的、尚未在仓库创建的目录**，不覆盖历史文件。运行原件仍放独立gitignored目录：

`docs/strata_4090_128k_lab/workspace/frontier/n20261102/<candidate_id>/<run_id>/`

简称 `W/`；尖括号必须在授权时替换为唯一实际ID。不要把私有原件上传公开仓库。仅新建本候选允许修改的文件，保留用户脏工作区；分支/提交/推送均服从后续授权，不由本计划自动执行。

### 文件职责与依赖

| 文件 | 责任 | 产生任务 |
|---|---|---|
| `R/evidence/IDENTITY.json` | 身份字段、报告来源与实际观测分离 | Task1 |
| `R/evidence/ARTIFACT_INDEX.json` | 原件路径/hash/可访问性；不重造原件 | Task1 |
| `R/evidence/COMPARISON.md` | 5060/4090同口径差异和缺证 | Task1 |
| `R/gates/CANDIDATE.md` | 仅一张候选卡、机制成本账 | Task2 |
| `R/gates/AUTHORIZATION.json` | 人工批准范围、预算和停止规则 | Task2 |
| `R/gates/PREREGISTRATION.json` | 指标/状态构造/样本/统计/质量冻结 | Task2 |
| `R/reports/SEMANTIC_RESOURCE.md` | 桥接、语义、显存/RAM与生命周期结果 | Task3 |
| `W/REQUESTS.jsonl`、`W/EVENTS.jsonl` | 原始请求、失败、阶段与资源事件 | Task3/4/5，按合同记录 |
| `R/reports/PERFORMANCE.md` | 资格、完整配对与失败；不承诺采用 | Task4 |
| `R/reports/QUALITY.md` | 独立任务四格、原六FAIL、绝对验收 | Task5 |
| `R/reports/DECISION.md`、`R/reports/RESULT.json` | 最终分项状态、审查与未决问题 | Task6 |

只记录已知或本任务授权获得的事实。不存在的文件登记 `MISSING`，不是占位生成一份空日志假装测试已做。

## Phase N0：离线证据与同口径合同

### Task 1：身份、原件和探针资格清单

**Files:** 创建上表三个 `R/evidence/` 文件；只读既有 `docs/02_ENVIRONMENT.md`、`frontier/docs/00_SNAPSHOT.md`、P00/P01B/P24/F03报告、NEXT_ACTIONS，以及用户明确提供的既有原件。

**Interfaces:** 输入为固定提交来源和可访问原件；输出 `identity_status`、`artifact_status`、`warm_probe_status`、缺件清单和当前可继续范围。身份字段采用06模板，不把历史值标成当前观测。

- [ ] 1. 将历史B、生产A0、社区配置、上游donor分四列；记录模型/二进制/草稿/模板/采样/缓存和计时的已知值与来源。
- [ ] 2. 在用户提供的现有材料内，核对P01B REQUESTS/ANALYSIS/token manifest、P00 IDENTITY/资产表、P24预注册/分析、F03生命周期ledger；没有就标MISSING，不重新跑模型取得。
- [ ] 3. 检查实际请求身份、read/reused、prime历史和自然fixed2048资格。仅有配置/recipe/短EOS结果时输出 `warm_probe_status=BLOCKED_EVIDENCE`。
- [ ] 4. 离线验收：报告SHA与当前观测分离；cache6144是总预算；Gist不能充当性能日志；同名IQ3_XXS不能跳过hash；warm缺件不会产生启动命令。
- [ ] 5. 独立审查Task1三个输出；若无可访问原件，交付缺件表即可，不追加目标机访问或大范围审计。

**停止/依赖：** 本Task可以以BLOCKED完整交付。离线只做一轮定向整理，建议最多60分钟人工审查预算；超出需重新说明必要性，不自动接力调查。

## Phase N1：只准入一个候选

### Task 2：冻结候选、分支与执行许可

**Files:** `R/gates/CANDIDATE.md`、`AUTHORIZATION.json`、`PREREGISTRATION.json`。

**Interfaces:** 消费Task1身份/缺件状态和02中的一张候选卡；输出 `candidate_id`、`route`、`workload_contract`、`primary_metric`、`admission_status`、明确授权与数值预算。所有硬件预算默认0。

- [ ] 1. 只选Q1、T1a、T1b、Q2a/Q2b、T2、T3或P1之一；原F合同不合格时保留收口，不从列表自动轮换。
- [ ] 2. 写出相对B与旧负结果的新机制、完成路径可省成本、额外成本和完整请求净省至少4%的可信依据；没有依据就 `NO_QUALIFIED_MECHANISM`。
- [ ] 3. 明确数值级别与质量要求。Q1/Q2须用户另批Q合同；T候选须target采样/回滚说明；P1须另批Prefill主目标。
- [ ] 4. 依据04选择W-N/W-C/W-T之一。原W-N缺资格不得启动A/A；改用W-C/W-T要明确新合同，不能假称原问题已解决。
- [ ] 5. 固定唯一基线/候选commit、资产、允许差量、质量留出方案、主/非主指标、统计门、样本上限、温度与RAM门、时间/存储/下载预算、端口、退出方式及批准原文引用。
- [ ] 6. 离线验收：`approved=false`、缺批准来源或任何必要预算未填时硬件全部NOT_RUN；多变量变化会被拒绝；相同旧机制换名字会被拒绝。
- [ ] 7. 独立review候选资格与授权；只有所有必要门通过才交Task3。缺件回执给用户，不自动向后推进。

**范围：** 本包只提供上述表单，不代替用户签批准，不代填“预计+10%”或未知数值容差。

## Phase N2：最小语义与资源验证

### Task 3：证明候选是真实变化，且不会破坏基础合同

**Files:** `R/reports/SEMANTIC_RESOURCE.md`、相关 `W/` 原件；代码文件范围必须由Task2固定。

**候选源码入口（只读起点，不等于修改许可）：** Q1 `src/core/native_dense.cpp`；T1 `include/strata/core/coupled_draft.hpp`、`src/core/mtp.cpp`及已确认的词表加载入口；Q2现版本KV实现与 `strata_control/vram_fit.py`；T2固定PR4928差量；T3 `strata_control/drafting.py`和固定服务PR；P1既有F05引用的prefill实现。

**Interfaces:** 消费Task2获准范围；输出 `bridge_status`、`numeric_status`、`resource_status`、`lifecycle_status`、actual资源差及剩余预算；任一必要项未过，不交正式性能。

- [ ] 1. 先只读检查实时GPU/进程/端口/温度/RAM和身份，记录时间；生产占用或权限不足就停止，不能停服务清场。
- [ ] 2. 若既有开关已能实现单变量，不写移植代码。若需代码，先在批准的隔离环境做候选最小失败测试，再最小实现、通过测试、review；不要整包升级或顺手重构。
- [ ] 3. 按E0/E1/Q/T路径执行批准的最小语义校验；E0做B/A1/C桥接，T覆盖reject/rollback/RNG，Q做数值与质量早停哨兵，不用E0标准冒充Q质量。
- [ ] 4. 按候选风险覆盖最小必要的1/奇数尾/真实4096或16384块、短→长→短、取消后下一请求、graph重捕获/loan归还；只有涉及的边界才扩测，所有次数计预算。
- [ ] 5. 记录实际allocation/峰值/auto cache、RAM、fault/swap与新增计算成本。只测到少搬字节、没有暴露时间证据时，不能通过机制门。
- [ ] 6. 验收负控制：错误身份被拒绝；一字节错能检出；OOM/85°C/RAM门触发时停止并保留原件；profiler键设0不能进入正式臂。
- [ ] 7. 输出独立审查回执；失败或预算耗尽则关闭本轮，不加格式、不换指标、不增加样本挽救。

**注意：** 技术语义测试通过不等于原六FAIL解决，也不等于warm探针有资格。

## Phase N3：正式性能与任务质量

### Task 4：执行一个预注册性能合同

**Files:** `R/reports/PERFORMANCE.md`、`W/REQUESTS.jsonl`、`W/EVENTS.jsonl`和完整配对分析。

**Interfaces:** 消费Task3通过回执、Task2批准的实际探针和A/A；输出完整配对集合、噪声门、CI、失败与 `performance_status`。沿用04的统计单位，不发明更大样本数。

- [ ] 1. 再确认身份/空闲/预算与正式环境一致，删除诊断键；缺合格A/A时只在已经批准且探针具资格的前提下执行预注册最小校准。
- [ ] 2. 固定探针按AC/CA/CA/AC/AC/CA执行六对，每臂prime+append；每次发送append前校验实际hash，首次不符整轮停止。W-T则使用另批的任务合同与适配器，不能冒用固定输出工具。
- [ ] 3. 同步保存所有请求与失败；不替补短输出、OOM、错hash或慢轮；计算 `m=max(.04,2*median(abs(r_AA−1)))`。
- [ ] 4. 固定探针按整对log ratio和46656枚举bootstrap算95%CI；检验主指标CI上界≤1−m，非目标≤1.02，并列完整wall、TTFT、decode、tokens、read/reused。
- [ ] 5. 只有主门通过且预算事前包含支持层时，才运行4K/120K各2对；支持层不建立正式2%非劣，不并入主六对。
- [ ] 6. 验收：不得以token/window增加n；失败不剔除；不能用少输出/早EOS改善tok/s；CI太宽输出INSUFFICIENT，不追加直到显著。

### Task 5：独立任务质量与真实完成时间

**Files:** `R/reports/QUALITY.md`、批准的独立留出任务原件与评分依据。

**Interfaces:** 消费Task2预注册开发/留出集合及Task3语义回执；输出四格a/b/c/d、独立任务数n、相对门、绝对门、任务预算时间与失败分类。Task4/5可按预注册顺序交错，但GPU仍串行。

- [ ] 1. 运行批准的真实中英/Java/工具/长文任务，保持初始仓库、工具、任务预算与采样策略；允许自然轨迹不同，独立验收任务成功。
- [ ] 2. 对失败/预算耗尽记预算B，对成功记min(t,B)；基础设施错误单独使本轮无资格，不用成功子集算胜率。
- [ ] 3. 计算 `CP_upper(b,n,.025)−CP_lower(c,n,.025)≤.02`；保留任务独立性证据，不把多seed/多轮当多任务。样本不足输出INSUFFICIENT，不改2pp门。
- [ ] 4. 单列原六项长检索FAIL和新的关键错误。两臂都错即使相对门通过，也不通过绝对质量门。
- [ ] 5. 验收：30对全一致不能PASS2pp；183仅是全一致公式边界，不是通用保证；开发集不能冒充独立留出集。

**成本控制：** 若质量留出集超出用户可接受预算，可以停止并诚实交付研究结果；不因此降低难度或把质量当“以后补”。

## Phase N4：收口，不自动上线

### Task 6：独立审查、文档结论与交接

**Files:** `R/reports/DECISION.md`、`R/reports/RESULT.json`，更新本候选文档导航；不覆盖旧报告、不改生产。

**Interfaces:** 消费Task1–5全部回执/失败/原件索引；输出06定义的分项状态与结论，附剩余未知和本轮实际消耗。

- [ ] 1. 独立reviewer核对预注册与实做、版本/原件身份、样本数、统计口径、负结果、数值分级和质量声明。
- [ ] 2. 逐项写 `mechanism/numeric/performance/relative_quality/absolute_quality/thermal` 状态；未运行项用NOT_RUN、未知数值用null，不用单一PASS。
- [ ] 3. 核对报告只声称有证据的内容：原六FAIL未解决时最多RESEARCH_RESULT_ONLY/BLOCKED_QUALITY；生产状态历史与当前观测分离。
- [ ] 4. 给出结束决定：关闭本轮、等待指定新证据、或请求下一项独立授权；不得把候选失败变成自动执行下一候选。
- [ ] 5. 验证Markdown链接、JSON语法、计数/公式和归档；仅清理本任务明确定义的可恢复临时资源，保留原件及用户修改。

上线/迁移是另一项工作，需要新的批准、当前生产核对、回滚与质量合同；不在本计划中悄悄实施。

## 计划自检与本次交付状态

- 02中的候选都经过同一个Task2准入门，T3和P1不能跳过各自额外阻塞。
- 04的身份、warm资格、数值、性能、质量和安全约束分别落在Task1–6；上方五项Review Focus均有具体验收步骤。
- 未来输出字段在06统一，代码入口只用于审查；没有虚构已存在的测试脚本或运行记录。
- 本次已完成调研文档；Task1–6的未来硬件/仓库产物未执行，所有新实验仍NOT_RUN。
