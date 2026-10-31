# P06 · 绝对质量、非劣与运行边界

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。本文列出的frontier适配器与测试是未来计划新增，当前包未包含live适配器。

**Goal：**明确性能研究是否具备进一步实际使用条件。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

本Phase前置：P05。独立Task可并行，资源启动/同文件编辑必须串行。

### P06-T1 · 原六FAIL与任务预算账

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**先复用当前有效质量证据。原六FAIL依然未解决就标BLOCKED_QUALITY，不花183对任务伪造相对一致。若有新独立质量修复项目的冻结证据，单独审其模型/提示变化，不能抹旧FAIL或归因本性能补丁。

**文件/接口/产出：**输出QUALITY_BASELINE_STATUS.json、FAILURE_LINEAGE.md。任务模型/提示更改必须新baselineID，不与本轮性能混统计。

**最小验证：**检查六个原ID、body/gold/评分合同均存在；0/1不当bool，未跑不记PASS。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P06-T2 · 独立任务非劣和真实Pi

**依赖：**P06-T1。

**任务内容与边界：**只有绝对质量前提成立且已有范围/预算时，用冻结独立任务/留出集、原quality_gate和受限Docker评估。真实Pi保持compaction/codemode/plugins、只换复制profile端口；无Java镜像NOT_RUN。

**文件/接口/产出：**输出TASK_PAIRS.json、relative/absolute分离结果、真实任务restrictedtime报告。多seed先按任务聚合，不造独立ID。

**最小验证：**原tools/quality_gate.py严格2pp；相对PASS不能替代绝对PASS；预算不足INSUFFICIENT，不能放宽margin。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P06-T3 · 必要热稳态与混合边界

**依赖：**P06-T1。

**任务内容与边界：**仅当前候选有采用可能且质量/授权范围允许时，按目标使用时长事前登记混合负载；沿85°C停止。至少覆盖candidate会触发的长append/恢复/取消，不继承P4“全天”结论。

**文件/接口/产出：**输出THERMAL_PROTOCOL/THERMAL_RESULT、实际持续时间/最大温度/频率/内存趋势。未执行保持NOT_RUN。

**最小验证：**护栏触发即终止；样本/时长不够不宣称24h或p99。没有新增热风险证据时不无意义重复全部旧压力测试。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P06-T4 · 独立质量/边界复核

**依赖：**P06-T1, P06-T2, P06-T3。

**任务内容与边界：**若T1阻塞，T2/T3按依赖不运行，Reviewer/Validator仍可审核终态。质量、性能、数值、稳定性分别列出，不压成一个绿灯。

**文件/接口/产出：**输出P06_REVIEW/P06_TEST；可能RESEARCH_RESULT_ONLY/BLOCKED_QUALITY/QUALITY_AND_BOUNDARY_SUPPORTED。

**最小验证：**核全部NOT_RUN/失败和来源；不以新增代码的单测替代任务质量。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
