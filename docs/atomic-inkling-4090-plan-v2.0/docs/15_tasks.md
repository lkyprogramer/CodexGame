# Atomic × Inkling × RTX4090 实施计划

> **For agentic workers:** 按 [AGENTS.md](../AGENTS.md) 逐任务实施、测试和审查。若环境提供 superpowers，可用 subagent-driven-development 或 executing-plans；没有这些插件时直接执行本包相同的步骤与门槛，不形成工具依赖。

**Goal:** 形成可测试、可回退、针对4090资格认证的Inkling服务候选。  
**Architecture:** Atomic通用CUDA全驻留主线优先；状态事务与证据工具作为公共基础；分层预算由容量触发；改变目标的研究支线独立。  
**Tech Stack:** 现有C++/ggml/CUDA/CMake/server；实验工具Python标准库为起点，确需统计/模型参考依赖时独立锁版本。  
**Spec:** [01目标合同](01_product_contract.md)、[05架构](05_architecture.md)。

## 全局约束

- 固定源SHA与所有模型文件hash；SM89，正式Mini R3，per-loop KV，single active generation，Vision Off为主线。
- 24GB GPU与64GB host分开计费；预算包含state、draft、scratch、graph、staging和保留量。
- 当前源已有的guard必须保留，新增能力按白名单逐行资格验证。
- 性能实验一次只占用同一GPU；研究任务可并行读代码/写CPU测试，不并行GPU计时。
- 每个任务只能报告实际证据；无硬件/模型/实现为BLOCKED，不能假测。
- 新增文件均标NEW；下面提到的 `tools/inkling-lab/lab.py` 和C++测试是**计划创建**，不是本包已有脚本。

## 审查重点

1. SWA被覆盖与conv历史恢复，不能只恢复length（T05）。
2. loop visit/slot混淆与草稿feature错位（T02/T06）。
3. graph缓存引用预算回收后的buffer（T07/T09）。
4. 实际输入被模板/客户端截断、capacity遗漏输出预留（T04/T10）。
5. 工具调用和多子代理排队造成重复副作用或父子死锁（T11）。

## 依赖图与完成语义

机器可读权威副本为 [task-graph.json](../manifests/task-graph.json)。主线T00–T12共13任务，研究R01–R05共5任务，Ghost G00–G05共6个，Kernel K00–K07共8个；v2另有L00–L07及Magnitude M任务，总数以当前机器DAG为准。研究与未选Ghost任务不成为正式主线的强制依赖；新增任务细节见[25](25_ghost_tasks.md)。

**任务交付完成与能力gate通过分开。** 机器图的status只描述任务交付，`produces_gate_evidence`表示它为哪些gate提供证据，不要求在该任务完成前通过这些gate的全部能力行。T03的质量初筛完成不等于完整G5；T04交付可复现的FIT/DOES_NOT_FIT/UNSUPPORTED诊断可完成任务，容量缺口正是启动T09的合法输入，绝不能把该profile的G4改成PASS。完整G4在T10/T12、完整G5在T12聚合。后续执行仍须检查所选能力前置资格。

~~~mermaid
flowchart TD
  A["T00–T02 冻结与串行"] --> B["T03–T04 质量和容量"]
  A --> C["T05 状态事务"]
  B --> D["T06–T08 投机和CUDA优化"]
  C --> D
  B --> E["T09 条件分层预算"]
  C --> E
  B --> F["T10–T12 长上下文与服务"]
  C --> F
  D --> F
  E --> F
  C --> G["R01–R04 独立研究"]
  G --> H["R05 交互实验"]
~~~

图中D/E到F表示选中该运行特性时的资格依赖；不表示无收益优化必须保留。优化可在有审查结论后NO_BENEFIT，容量分支可SKIPPED_WITH_EVIDENCE。任何真正启用的特性都必须PASS其对应能力行。

## 公共实验接口（T01负责创建）

~~~text
lab.py validate --manifest RUN.json
lab.py run --manifest RUN.json --out EVIDENCE_DIR
lab.py qualify --suite G1|G2|G3|G4|G5|G6 --manifest RUN.json --out EVIDENCE_DIR
lab.py compare --baseline BASE_DIR --candidate CAND_DIR --out REPORT_DIR
~~~

退出码：0=指定操作完成且其检查通过；1=已执行但失败；2=缺能力/模型/环境或未实现；3=输入/版本合同不合法。空测试集合不得exit0；上游进程exit0不能替代qualification PASS。run原始成功与gates分别记录。run的PASS仅指本次采集及oracle检查完成，统计收益/能力授权由独立gate记录决定；run中不得嵌入自报G7。

## T00 · 现场调查、仓库与资产冻结

**依赖：** 无。**输出：** G0输入。**所有者：** 环境/资产代理。

**Files:** NEW `evidence/inventory/`、`profiles/models.lock.json`、`profiles/toolchain.lock.json`；读取上游AGENTS/CMake与本包source-lock。

**接口：** 输出hardware inventory、source commit、binary/toolchain、tokenizer/template/weights/draft指纹；未得到的字段为null并阻断相关任务。

- [ ] 运行包内preflight只读工具；记录当前服务进程的占用与独占实验可行性。
- [ ] 固定checkout，核对源与已有工作树；单独build目录，不覆盖生产二进制。
- [ ] 只下载/登记本阶段所需资产，校验SHA256与GGUF metadata；不一次下载全部研究模型。
- [ ] 按16的构建命令建立SM89二进制，保存configure/build日志、CMakeCache与二进制hash。
- [ ] 评审现场事实与规划差异，交付TASK记录和G0结论，再开始T01。

**验收：** 第三方能按锁文件重建；没有把nvidia-smi显示的CUDA上限当nvcc版本；没有未解释的显存占用。无机器访问时BLOCKED，不要求猜测。

## T01 · 实验工具与证据合同

**依赖：** T00。**Files NEW:** `tools/inkling-lab/lab.py`、`tools/inkling-lab/manifest.py`、`tools/inkling-lab/compare.py`、`tools/inkling-lab/capabilities.py`、`profiles/capabilities.json`、`tests/inkling4090.cmake`、`tests/inkling_lab/test_manifest.py`、`tests/inkling_lab/test_measurements.py`。

**接口：** 实现上面的4个CLI。run接受single-run记录或kind=paired_run的计划（见pair-plan-example.json）；paired计划由同一runner按预生成顺序交错执行A/B，输出baseline/candidate子目录，不能用两次独立全组run冒充交错。输入结构以 [run-example.json](../manifests/run-example.json) 和 [run-contract.json](../manifests/run-contract.json) 为准，资格决策另按 [gate-contract.json](../manifests/gate-contract.json)；输出 `manifest.json / raw.jsonl / metrics.json / gate.json / stdout.log / stderr.log / artifacts.sha256`。`capabilities.query_capability(key, registry)`实现05的profile级查验，C++资格测试由后续任务注册，未实现的suite返回2。

- [ ] 写负例：缺hash、错误model epoch、NaN/null终点时间、截断输入、zero tests、只存在synthetic数据、未知GPU/隔离条件都不能被判成GPU性能PASS。
- [ ] 必做语义负例：P期望131072但actual=1；capacity不足P+N+实现reserve；oracle失败；required tests漏项；artifact不存在/hash不符；formal R≠3；spec资产/feature错配；NOT_RUN自报gate PASS；无授权自报G7。Schema不能做的比较与文件核查必须由语义验证器拒绝，不允许默认放行。
- [ ] gate候选key与输入角色绑定；baseline/reference保留各自key。写正例确认同目标AR/DSpark在预登记差异内可合法比较，写负例拒绝未登记目标/模板/硬件/P/N变化及候选key错配；G3不以A/B完整key相同为条件。
- [ ] 运行测试，确认这些错误能触发失败/阻塞。
- [ ] 实现验证器、subprocess超时/退出码传递、原始事件日志和确定性摘要；不自动修改profile。
- [ ] 用合成fixture验证计时边界与统计程序；明确 `evidence_kind=synthetic_test`。
- [ ] 再运行全部工具测试与malformed输入测试，审查后独立commit。

**验收命令（实现后）：** `python3 -m unittest discover -s tests/inkling_lab -v`。所有GPU suite的缺失状态仍正确返回2；工具测试绿不能让模型状态变绿。

## T02 · 正式Mini普通CUDA串行基线

**依赖：** T01。**现有:** `src/models/inkling2.cpp`、`inkling2-loop.cpp`、相关CUDA算子。**NEW:** `tests/test-inkling-contract.cpp`、`profiles/mini-fixed-r3-serial.json`、`profiles/tolerance_registry.json`。后者由reference噪声、算子dtype/shape和预先误差预算生成，在看candidate结果前冻结。

**接口：** `describe_loop_layout()`导出physical/slot/visit表；lab捕获完整prompt IDs、每层shape/route/state检查点与最终logits。参考可以慢，但必须同资产/目标契约。

- [ ] 写24物理/48访问、core[6,18)、错误meta拒绝、feature计数边界测试。
- [ ] 跑128/1024/4096输入和greedy128输出，先关闭预算/spec。初始G1能力范围为P4K；16K扩展由T04诊断并在T10资格，未测16K不提前标PASS。
- [ ] 若失败，修最小loader/op问题；不改模型语义，记录所有CPU fallback。
- [ ] 比较对齐prefix下的logits/KV/conv，确认FA/KV类型支持矩阵。
- [ ] 注册 `test-inkling-contract`，通过G1与相关G2项后锁定serial baseline commit。

**验收（实现后）：** `lab.py qualify --suite G1 --manifest profiles/mini-fixed-r3-serial.json --out evidence/T02`；所有命令须带 `python3 tools/inkling-lab/` 前缀，简写只用于本计划阅读。

## T03 · 量化选择与业务质量基线

**依赖：** T02。**NEW:** `profiles/quantization-candidates.json`、`fixtures/quality/manifest.json`、`evidence/T03/`。无必要引擎改动。

**接口：** 产出选定资产ID与不可变quality holdout hash；将weight precision、K precision、V precision分开。

- [ ] 建立smoke、开发集、holdout三组；真实Java任务与工具schema用可执行oracle，禁止调参时偷看holdout答案。
- [ ] 同源量化候选逐一建立AR参考；启动锚点IQ2不得直接被选为主力。
- [ ] 对照高质量参考和当前生产业务完成情况，记录失败种类与生成长度。
- [ ] 在内存能满足的候选中选质量合格者，冻结基线；若无候选合格，记录失败并停止性能迁移。
- [ ] 交付QC记录，T12重跑完整G5，不能把小smoke当最终质量验收。

## T04 · 容量与早期长上下文

**依赖：** T03。**现有:** KV/SWA与context代码。**NEW:** `profiles/context-ladder.json`、`fixtures/long-context/manifest.json`、`evidence/T04/`。

- [ ] 实现实际P与C校验，负例证明客户端截断、遗漏输出reserve会被抓住。
- [ ] 按04填实际allocation表，4K→16K→64K→P128K；失败就在该行停止，不调小P伪装通过。
- [ ] 对prefill峰值、decode末尾、SWA/full模式、q8与F16支持做明确记录。
- [ ] 判定主线是否全驻留足够；不足时启动T09，足够时给出可审查skip理由。
- [ ] 交付完整容量诊断后可完成T04任务；能力G4保持该profile真实状态。T09可消费DOES_NOT_FIT报告，T10补齐长期状态/质量组合，二者不能互相代替。

## T05 · 状态事务与完整回放

**依赖：** T02。**现有:** KV、hybrid memory、context状态序列化；**NEW:** `src/llama-inkling-state.h/.cpp`、`tests/test-inkling-state.cpp`。

**接口：** 实现05的 `begin_speculation / commit_verified_prefix / discard_uncommitted_suffix / cancel_request_and_release`。以现有state API为基础，必要时扩展，避免双份状态所有权。

- [ ] 写人为覆盖SWA/conv后只恢复length的失败测试，以及模型epoch不匹配恢复拒绝。
- [ ] 定义可重算scratch与必须持久化状态，形成字节级布局/生命周期文档。
- [ ] 实现事务、COW/delta、event/lease释放与RNG事件消费规范。
- [ ] 对reject每个位置、cancel阶段、save/restore后64token continuation进行reference比较。
- [ ] 通过G2；空测试、仅比较当前输出、缺conv比较均不得完成。

## T06 · 原生DSpark固定宽度

**依赖：** T03、T05。**现有:** `src/models/inkling2-dspark.cpp`、`common/speculative.cpp`及context；**NEW:** `tests/test-inkling-spec.cpp`、`profiles/mini-fixed-r3-dspark.json`。

**接口：** target与draft独立fingerprint；proposal ledger保存真正q；返回accepted candidates、emitted tokens和完整周期时间。

- [ ] 写错feature visits、错head、错target revision拒绝测试。
- [ ] 接通普通CUDA原生DSpark，先k1、k3、k7固定宽度greedy；预算路径仍独立限制。
- [ ] 通过全状态拒绝/stop/取消测试，再实现sampling的质量守恒及负例。
- [ ] 与同资产AR交错A/B，比较最佳固定宽度；减少draft挤压专家/容量的隐含混杂。
- [ ] G2先通过，G3有净收益才默认启用；无收益以NO_BENEFIT结案保留AR。

## T07 · SM89局部kernel优化

**依赖：** T04、T05；涉及spec B形状时另需T06。**现有/NEW:** 见08，新增 `tests/test-inkling-kernels.cpp`。

- [ ] profiler先定位成本占比，写一页假设和Amdahl收益上限。
- [ ] 为选中一个kernel写shape/dtype/stride/alias边界测试并冻结容差。
- [ ] 实现SM89版本及fallback，禁止带入PDL/TMA/cluster硬依赖。
- [ ] 跑数值、race/memory检查与微基准，再同profile请求和Agent A/B。
- [ ] 两轮可解释修正后仍无端到端净益则停止，不扩大为全引擎重写。

## T08 · 图复用、自适应k与lookup

**依赖：** T06。**现有:** ggml CUDA Graph、spec协调；**NEW:** `tests/test-inkling-graph-lifetime.cpp`、`profiles/spec-policies.json`。

- [ ] 验证固定B图、buffer generation、resize/reload失效与取消寿命。
- [ ] 先host选已资格固定图，再做conditional API probe；probe失败不阻断固定图。
- [ ] 自适应k与prompt lookup分别建立独立flag和ablation，不能同一提交归因。
- [ ] 用未调参任务比较最佳固定k，记录切换、fallback和capture成本。
- [ ] 只有G2/G3均通过才加入默认profile；复制样例提速不足以通过。

## T09 · 条件性的离散预算与loop驻留

**依赖：** T04、T05。**现有:** 06列出的所有gate、ledger、expert store/executor；**NEW:** `tests/test-inkling-budget.cpp`、必要时 `src/llama-inkling-cuda-banks.h`。

- [ ] 先写上游未支持组合仍拒绝的回归测试。
- [ ] 4K单slot无spec实现CUDA bank与两域账本，保持同步读取参考。
- [ ] 测physical alias、OOM/短读/部分加载、active lease/graph安全，逐type放开能力。
- [ ] 只有I/O profiler支持收益时添加有界pinned双缓冲和event链。
- [ ] 独立扩大context，再与T06合格DSpark组合；每组合有自己的G2/G4记录。增加sticky executor失败后旧context禁止续跑、同预算重建与不能移除budget的负例。

**可跳过条件：** 选定完整profile的目标context、draft/k/B、ubatch、graph与workspace实测全驻留且满足余量；须保存证据，不能只写“应该够”。T04 serial数据只可豁免serial profile，加入T06/T08后重测，失败可重开T09。

## T10 · 长上下文与continuation资格

**依赖：** T04、T05；选择spec/预算profile时增加T06/T09能力证据。**现有:** KV/state/server-prefix相关代码；**NEW:** `tests/test-inkling-session.cpp`、`profiles/long-context-qualified.json`。

- [ ] 写精确prefix、编辑历史、wrong epoch/codec、损坏cache失败测试。
- [ ] 实现或补齐完整状态save/restore，明确draft状态重建策略。
- [ ] 运行C64K/C128K与P128K，实际Java文件/工具历史，包含拒绝、cancel和续接。
- [ ] 比较重算与恢复的logits/后续输出，测GPU/RAM/SSD层次净收益。
- [ ] 将200K/262K保持独立未资格行，只有真实测过才更新；通过G2/G4。

## T11 · 服务协议、队列与故障隔离

**依赖：** T10。**现有:** `tools/server/server-context.cpp`、`server-prefix-checkpoints.h`、`common/parsers/inkling.cpp`；**NEW:** `tests/inkling_lab/test_service.py`、`profiles/service-candidate.json`。

- [ ] 写SSE/tool JSON/UTF-8/stop/cancel/超时/错误请求隔离测试。
- [ ] 单GPU active generation=1、有界排队；parent等待child时释放执行slot，避免父子死锁。
- [ ] 检查未commit token不触发工具、同tool_call_id不重复执行副作用。
- [ ] 运行连续请求、2–3子代理排队、长短交错、模型epoch切换演练。
- [ ] G6阶段验证通过，保留独立候选端口与旧服务配置。

## R01 · last-loop KV

**依赖：** T04、T05。详见10。NEW测试 `test-inkling-cache-policy`。实现自身policy参考、容量门、per-loop对照质量门；不把短greedy一致当等价。通过G2/G4/G5后，R05才可组合。

## R02 · varloop oracle与adapter

**依赖：** T02、T05。详见12。NEW `src/llama-inkling-loop-adapter.h/.cpp`、`tests/test-inkling-loop-adapter.cpp`。输出结构态、逐loop readout、feature契约，默认先R3，R1..5各自目标。R改变必须新state arena；原生DSpark只在已验证默认R启用。

## R03 · 完整Inkling 2DSD

**依赖：** R02、T06。详见11。NEW scheduler、proposal ledger与 `tests/test-inkling-tree.cpp`；具体路径由R02 adapter落实后冻结。

v2改为NOT_RUN：S44公开实验分支已有Inkling runner；先做UX01–UX03和资产/Atomic适配/SM89资格，再进入GPU比较。不能把旧main缺码判断外推到当前全部分支。配对的训练target/草稿器不更换。G2/G3/G5及实际q多branch证明不能省略。

## R04 · LoopCD

**依赖：** R02、T05。详见12。NEW `src/llama-inkling-guidance.h/.cpp`、`tests/test-inkling-guidance.cpp`。输出guided readout与独立target指纹；omega0等价、非线性coda反例、reference只读分支、质量/成本门。先固定R/fixed omega，再少轮或adaptive；最终verifier使用guided p。

## R05 · 研究组合

**依赖：** R01/R03/R04各自通过的子能力；当前整条组合任务保守依赖三者。只测试清晰列出的pair，再决定三者联合。NEW `profiles/research-interactions.json`。

- [ ] 保存每个单项最佳冻结配置与相同baseline。
- [ ] 做最小2×2 factorial：A、A+x、A+y、A+x+y，禁止把各自speedup相乘。
- [ ] 全状态/目标一致性与G2先跑，再质量、容量、性能。
- [ ] 草稿接受率下降、extra memory触发spill、tail变差都计入总结果。
- [ ] 未通过单项的机制不参与“全融合”展示；可交付明确的不兼容结论。

## T12 · 主力候选交付

**依赖：** T03、T10、T11，以及实际启用的所有feature资格。无必须采用研究机制的要求。

- [ ] 冻结release candidate commit、binary、资产、profile、测试集和rollback generation。
- [ ] 重跑G3/G4/G5与长时间G6；不同模型业务比较以同任务oracle/预算衡量。
- [ ] 验证候选失败时回到同目标serial及旧NInfer/Strata的两级回退；模型间不能传KV。
- [ ] 形成20的能力表与发布记录，列明FAIL/BLOCKED/未测试行。
- [ ] 交付可审查候选；实际生产切换属于G7，按当时明确授权执行。

## 每个任务的共同收尾

检查代码diff、测试数与原始输出；更新任务记录而非改原始日志；提交最小独立commit；独立审查者核对目标/接口/证据/停止条件。若未得到性能收益，保留简洁的no-benefit结论和可复现实验，不继续堆功能。

## v1.1增量任务接入

G00固定参考与失败oracle，随后按profile选择G01驻留、G02布局、G03prefill、G04 relay或G05闲置会话。精确依赖和初始状态见机器图；G04初始DEFERRED。G03在预算模式下另需T09相应能力。G01在T09有同profile全驻留豁免时也须有据跳过，不把缺失bank当已实现。GX01–GX20在[26](26_ghost_validation_runbook.md)定义；原测试和资格门不削减。

## v1.2增量任务接入

[31](31_kernel_tasks.md)新增K00–K07；该阶段新增8任务；v2全量任务数见机器DAG。K00固定源与前端probe，K01扩展合同，K02选择单热点与预算，K03生成/编译/证明绑定，K04局部桥接，K05动态及模型验证，K06独立确认与候选registry。K07独立backend初始DEFERRED，需要新的trace和DECISION才开启。

K00–K06初始NOT_RUN，AX01–AX28见[32](32_kernel_validation_runbook.md)，原96项测试仍NOT_RUN；v2全量见test-catalog。新增任务不成为统一T12前置；只对被选中的profile要求相应K产物和原G2–G6证据。为避免循环依赖，K任务在T07触点局部工作，但不把T07的“全部优化完成”设为前置；正式发布仍由T12统一审查。K06服务/长上下文范围需要T10/T11交付，核心任务完成与特定能力gate仍分开。

## v2总体编排

按[00](00_integrated_master_plan.md)的A–G阶段执行：baseline→完整状态/预算→native DSpark/热点→Tier→条件Pool/专家→完整组合→服务。L任务细节见[38](38_cache_tasks.md)，M任务见[42](42_magnitude_integration.md)。任何可选功能未选中可保留NOT_RUN；选中后必须有其显式依赖和gate证据。

当前机器DAG为44任务，计划目录为148测试。M00–M03的固定/条件依赖、幂等共享组件及MGX归属见[42](42_magnitude_integration.md)。执行run只引用`config.mechanism_profile_ref`，条件测试从冻结profile求值，不自行解释自然语言skip。
