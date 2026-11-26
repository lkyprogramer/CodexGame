# Ghost补充实施计划：G00–G05

> **For agentic workers:** 先读[AGENTS](../AGENTS.md)、[24设计](24_ghost_transfer_design.md)与[原任务图](15_tasks.md)。G00–G05是任务ID，G0–G7是资格gate，二者不可混用。保持原执行/审查方式；本篇没有授权上线。

**Goal:** 将有证据支持的Ghost机制转成Atomic上的可证伪候选，并保留失败、无收益和有依据跳过的结果。  
**Architecture:** 固定R3/per-loop/full-resident主线保持；独立参考与测量先行，容量分支和优化按profile启用。  
**Tech Stack:** Atomic C++/ggml/CUDA；Ghost Rust只作隔离参考；由T01实现后的Python lab负责证据。  
**Spec:** [23来源审计](23_ghost_source_audit.md)、[24迁移设计](24_ghost_transfer_design.md)、[26验证](26_ghost_validation_runbook.md)。

## 全局合同与接口

主任务图 [task-graph.json](../manifests/task-graph.json) 已加入六个可选任务；它们不是T12的统一必选项。实际启用某机制时，其资格行成为T12前置条件；未选机制可保留NOT_RUN/DEFERRED。全驻留profile可按证据跳过异构驻留任务。

NEW配置键放在run的 `config` 下：`residency_policy`、`runtime_layout_sha256`、`prefill_grouping`、`relay_mode`、`snapshot_policy`。值与实际dispatch由lab读取，不能把这些逻辑字段直接拼成上游CLI。它们及相应实现revision纳入完整capability key；只有改变实际算术/目标时才改变03的target_fingerprint。

每任务沿用lab退出码与独立gate合同。目标测试ID为GX01–GX20，完整定义在26和test-catalog。所有新增C++测试必须注册CTest；尚不存在时返回BLOCKED，禁止空测试通过。

## G00 · 固定来源、参考适配与失败oracle

**依赖：** T01、T02、T03。**类型：** 可选参考基础，初始NOT_RUN。**产出：** G0/G2输入，不能单独授G3。

**Files NEW:** `tools/inkling-lab/ghost_reference.py`、`profiles/ghost-source.lock.json`、`profiles/ghost-reference.json`、`tests/inkling_lab/test_ghost_reference.py`。修改T01的manifest/compare工具；只读Ghost固定树。

**接口：** `run_reference(profile_path, token_ids_path, output_dir) -> ReferenceRecord`。ReferenceRecord至少包含engine/build/asset指纹、入口模式、实际argv、input/output token IDs、逐层/loop trace路径和hash、dtype/dispatch清单、exit/timeout、原始stdout/stderr及oracle是否可判定。缺token/路径信息为UNAVAILABLE并阻断相应比较，不能从可读文本猜token。

- [ ] 写GX01/GX02/GX20负例：错误版本、同名不同资产、EXACT开关被误当完整FP32、空fixture、陈旧oracle、初始hash、缺一侧pair、输出不等却exit0、usage缺失。
- [ ] 实现固定源与资产检测。只有双方能运行同一GGUF/metadata时做跨引擎算术对照；Ghost UD-Q3_K_XL不取代主线选定资产。
- [ ] 在launch前校验正式Mini/R3、head/conv/pool等完整几何与tensor格式；R4/R5或未知结构不得借Ghost入口直接运行。
- [ ] 为参考缓存生成完整hash键，含binary、资产内容、tokenizer、模板、dtype/dispatch、输入ID、loop/cache/算术策略；不使用basename+prompt作为充分键。
- [ ] 按26运行隔离Ghost CPU与GPU诊断，采集同一短输入的中间状态；若源缺必要trace，在独立Ghost参考分支增加最小观测补丁并记录新SHA。
- [ ] 与Atomic串行参考逐层比较，先定位第一个偏差，区分存储解码、算术量化和模型语义。只有已冻结容差的N类变化才进入质量评估。
- [ ] 审查原始证据与失败出口，提交参考adapter；缺GPU/资产可交付来源与CPU工具，但相应GPU能力保持BLOCKED。

**验证命令（实现后）：** `python3 -m unittest discover -s tests/inkling_lab -p test_ghost_reference.py -v`。GPU比较使用T01实现后的 `lab.py qualify --suite G2 --manifest profiles/ghost-reference.json --out evidence/G00`，不新增未经实现的CLI。

## G01 · 循环感知专家驻留与有界交换

**依赖：** G00、T04、T05、T09。**类型：** 条件容量优化，初始NOT_RUN。T09若对选定完整profile已有全驻留豁免，G01只能同profile有依据跳过，不能假装已完成CUDA bank改造。

**Files NEW:** `src/llama-inkling-residency.h/.cpp`、`tests/test-inkling-residency.cpp`、`profiles/inkling-residency.json`。修改T09的 `src/llama-inkling-cuda-banks.h`（由T09在需要时创建）、现有expert store/executor与预算ledger。

**接口：** `plan_residency(trace, inventory, limits, policy) -> ResidencyPlan`；`commit_residency(plan, safe_boundary, expected_generation) -> AppliedGeneration`。输入trace含physical/expert/visit/phase、CPU/GPU成本、实际bytes；plan含保留/移入/移出、H2D与host成本、layout fingerprint、受影响图及总预算。generation不匹配必须失败，不能覆盖旧slot。

- [ ] 写GX03–GX07：共享物理权重只计一次、各visit热度独立、布局扩张、held-out phase shift、上升context挤压、租约未结束、取消/短读/错误slot发布。
- [ ] 先实现同步、固定完整层优先策略；与按热度策略逐项对照，证明状态和输出一致。
- [ ] 增加24定义的可测收益/字节评分；保存评分输入、预测与实测误差，不把loop次数当固定速度倍数。
- [ ] 最后增加带滞回的动态交换；明确定义按committed token还是forward call计步，以及prefill、拒绝候选的计数规则。
- [ ] 在完整profile下测H2D、CPU critical path、尾延迟和峰值；动态策略必须对比最佳固定策略，不只对比无缓存。
- [ ] 两轮有trace支持的修正后无收益则NO_BENEFIT；保留固定合法放置策略。不能为提升hit率降低质量或减少context。

**验证命令（实现后）：** `ctest --test-dir build-inkling4090 -R '^test-inkling-residency$' --output-on-failure --no-tests=error`；再执行对应G2/G3/G4 profile。

## G02 · 精确runtime布局与格式执行

**依赖：** G00、T03、T05。**类型：** 资产/热点条件优化，初始NOT_RUN。

**Files NEW:** `src/llama-inkling-weight-layout.h/.cpp`、`tests/test-inkling-weight-layout.cpp`、`profiles/inkling-layout.json`。GPU kernel只在T07明确选中后修改既有CUDA分派；不先创建一套独立NVRTC运行时。

**接口：** `make_runtime_layout(source_tensor, layout_version, budget) -> OwnedPackedTensor`。返回owning buffer、源hash、源/目标stride、scale布局、真实分配字节与layout hash。`release_after(event)`接入原lease；不能用泄露owned数据换稳定地址。

- [ ] 先枚举实际tensor类型；没有IQ3_S或支持的候选格式时，给出具体资产表并SKIPPED_WITH_EVIDENCE。
- [ ] 写GX04/GX08/GX09：所有合法code/scale/sign、行与专家边界、空/畸形block、padding、同资产dequant与dot比较。
- [ ] 实现精确重排，单独记录110→134字节等真实扩张；保留原格式回退，不改磁盘模型文件或假冒GGUF类型。
- [ ] 如果进一步修改activation量化/融合归约/CPU指令顺序，建立独立N类profile与目标算术身份，不能沿用E标签。
- [ ] 测局部dot、整层、完整请求三个层级；包括load/repack时间、RAM峰值、CPU缓存与page fault、必要的H2D成本。
- [ ] 只有实际关键路径改善且满足原质量/资源门才默认启用；无收益及时停止。

**验证命令（实现后）：** `ctest --test-dir build-inkling4090 -R '^test-inkling-weight-layout$' --output-on-failure --no-tests=error`。

## G03 · Prefill专家分组与权重复用

**依赖：** G00、T05、T07；使用预算时另需T09对应能力。**类型：** 条件性能优化，初始NOT_RUN。

**Files NEW:** `src/llama-inkling-expert-batch.h/.cpp`、`tests/test-inkling-prefill-grouping.cpp`、`profiles/inkling-prefill-grouping.json`。修改现有expert executor与CUDA dispatch，沿用原graph/预算设施。

**接口：** `group_expert_tokens(routes, logical_visit, token_positions) -> ExpertBatchPlan`。plan返回每expert的有序token索引、原始top-k槽与权重、源/目标stride、padding和scatter映射；禁止跨依赖visit重排。聚合输出必须能回到原token/原expert顺序。

- [ ] 写GX10/GX11/GX18：B1/Bn、非整块尾、不同slot、relative bias/sink/softcap、SWA和conv边界；固定输入ID做teacher forcing。
- [ ] 先实现CPU分组/回散参考，再GPU候选；只有合法可交换的工作并行。
- [ ] 探索各已支持B，保持相同P/N/context/KV/精度；记录sort、gather、scatter、weight decode和scratch各自成本。
- [ ] 对捕获与未捕获图、暖/冷prefix分别测试；graph按B/地址/layout/generation正确失效。
- [ ] 短/长context的TTFT、请求E2E、峰值及关键p95均达门槛后启用；只在重复句上变快则不授业务G3。

**验证命令（实现后）：** `ctest --test-dir build-inkling4090 -R '^test-inkling-prefill-grouping$' --output-on-failure --no-tests=error`。

## G04 · 有界CPU/GPU relay实验

**依赖：** G00、G01、T05、T09。**类型：** 高风险条件优化，初始DEFERRED。只有新的Inkling profiler证据表明handoff开销可能跨越原G3门槛，才记录DECISION进入RUNNING；历史Strata no-benefit不自动重开。

**Files NEW:** `src/llama-inkling-cuda-relay.h/.cpp`、`tests/test-inkling-cuda-relay.cpp`、`profiles/inkling-relay.json`。修改expert executor、context错误传播和graph生命周期代码。

**接口：** `RelayTicket = (request_id, epoch, sequence, deadline_ns)`；`submit_cpu_experts(ticket, inputs)`；`complete_cpu_experts(ticket, outputs)`；`commit_relay_result(ticket) -> Result`。错误/超时后ticket永久失效；新context使用新epoch。实现先采用分段图+event，mapped等待只作为可单独关闭的候选。

- [ ] 写GX12/GX13/GX17：CPU超时、最后handoff超时、迟到ack、CPU异常、取消、GPU错误、context销毁、并发调用pool及相邻请求复用。
- [ ] 验证发生错误时没有logits/token/tool commit；drain/退役后在同预算重建，不能继续旧context。
- [ ] 建立分段安全baseline，记录host launch、GPU idle、CPU work与PCIe时间。能否重叠必须由trace证明。
- [ ] 如仍值得，再实现mapped协议并验证coherence、system fence、host memory能力、deadline与watchdog；不照抄cycle常量。
- [ ] 在取消/超时和反复load/unload压力下验证资源清理，再做配对E2E。任一未解释状态/资源异常立即FAIL。

**验证命令（实现后）：** `ctest --test-dir build-inkling4090 -R '^test-inkling-cuda-relay$' --output-on-failure --no-tests=error`。未满足启动条件保持DEFERRED，不妨碍T12使用其他合格主线。

## G05 · 完整Inkling闲置会话快照

**依赖：** G00、T10、T11。**类型：** 条件服务优化，初始NOT_RUN。

**Files:** 扩展T10的 `tests/test-inkling-session.cpp` 与T11服务测试；NEW `profiles/inkling-session-parking.json`。实现沿用已有state/server-prefix-checkpoints，不平行造第二个不兼容格式。

**接口：** `park_session(session_id, expected_epoch, host_budget) -> SnapshotRef`；`restore_session(ref, target_fingerprint, token_prefix, budget) -> RestoredSession`。SnapshotRef含版本、全部状态组件、committed边界、采样/RNG/draft、校验和、实际bytes和资源lease；不包含可被新epoch误用的裸设备地址。

- [ ] 写GX14/GX15/GX17：A→B→A、A→B→C→A、前缀编辑、不同模型/loop/codec、损坏快照、EOS/取消后立即park、预算不足。
- [ ] 先比较恢复与重prefill后的完整状态/后续输出，再接入队列；single active generation保持1。
- [ ] 按字节与重建成本淘汰，覆盖实际64GB host账本；不能固定缓存五个大上下文会话。
- [ ] 先reservation/驱逐，再复制并原子发布；opening、live snapshots、staging和恢复瞬时峰值统一计费，复制失败释放预留且保留原可用会话。
- [ ] 测首次请求、warm返回、会话切换、失效重算的完整E2E及H2D/D2H，报告实际净收益。
- [ ] 复用原G6 soak、工具调用副作用和回退测试；容量/尾延迟不合格时关闭parking并重算，不影响主线正确性。

**验证命令（实现后）：** `ctest --test-dir build-inkling4090 -R '^test-inkling-session$' --output-on-failure --no-tests=error`，并运行T11服务测试。

## 原任务的增量验收

- T01增加GX01/GX20的证据失败出口，配对schedule/target身份规则沿14执行。
- T05/T08增加GX16/GX17；lookup one-hot q与一般草稿q不可混用。
- T07/T10增加GX18；Ghost通用TC/Q4存在不代表Inkling对应路径已实现。
- T12按实际启用机制引用GX与原TC/QC/PF/SV记录，不能用新增测试替代150 Java/300工具案例、真实P128K或原G6/G7。

每个任务按模板保存计划、diff、原始run、负例、结果与独立审查。G00–G05不预设成功；可交付精确的NO_BENEFIT/BLOCKED/DEFERRED结论。

任何被选中进行性能比较的G任务负责创建NEW `profiles/ghost-transfer-paired.json`（多实验时使用不同文件名），按T01的pair-plan合同冻结双方manifest、各自能力key、固定因素、允许差异和共同schedule。其他任务不得覆盖已经使用的实验计划。
