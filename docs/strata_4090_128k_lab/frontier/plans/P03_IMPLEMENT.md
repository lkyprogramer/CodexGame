# P03 · 最小native实现与关闭路径

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。本文列出的frontier适配器与测试是未来计划新增，当前包未包含live适配器。

**Goal：**仅实现通过资格的一项窄差量。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

本Phase前置：P02。独立Task可并行，资源启动/同文件编辑必须串行。

### P03-T1 · 隔离源码和负控制

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**从冻结研究B建独立实验checkout/worktree，不在生产repo建worktree，不运行updater。恢复P6六文件port，构建同flags；对比原二进制身份。先实现该卡最小比较器与故意错误负例。

**文件/接口/产出：**输入SELECTED_CANDIDATE；输出SOURCE_BASELINE.json、PATCH_SCOPE.json、对应candidate test。拟运行时开关STRATA_LAB_Fxx仅显式字符串1启用，缺省与字符串0都关闭；同一binary包含原路径与候选路径，分别验证。另需编译门时独立命名，不代替运行时off/on。

**最小验证：**运行候选最小失败测试观察预期拒绝；源码/构建/ISA不满足则BLOCKED，不安装系统依赖。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P03-T2 · 实现单一机制

**依赖：**P03-T1。

**任务内容与边界：**按候选卡限定源symbol改动，不附带重构/新cache/新量化。保留原路径，新增hit/fallback计数。一次只选CPU或GPU热点/一个format，不扫宽度/线程网格。

**文件/接口/产出：**修改仅PATCH_SCOPE列出的文件；产物同一binary的off/on，另留未改native B；OUTPUTS含diff和build完整receipt。

**最小验证：**最小单元/fixture测试、fallback不命中路径、编译资源/ISA检查；不跑完整性能或所有历史测试。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P03-T3 · 关闭路径副作用验证

**依赖：**P03-T2。

**任务内容与边界：**确认off路径回到原函数、无额外allocation/timer/同步；native实际env/args与B一致。若构建布局变化导致性能疑点记录，在P05校准，不能默认off无开销。

**文件/接口/产出：**输出OFF_CONTROL.json、hitcounts、source diff；native算术/数据差异按canonical域报告。

**最小验证：**匹配分派最小A/A与B/A1对照；错误布局/输入hash负例；off命中0、on预期入口>0。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P03-T4 · 独立代码与最小测试审查

**依赖：**P03-T3。

**任务内容与边界：**Reviewer审所有权/数值/分派/非法ISA及scope；Validator运行必要的最小测试，查未跟踪新文件是否进manifest。没有native硬件证据就不能填NUMERIC_PASS。

**文件/接口/产出：**输出P03_REVIEW/P03_TEST、IMPLEMENTED_OFF_VALIDATED或拒绝状态。

**最小验证：**只补review暴露的具体测试，不重复整个仓库game前端测试，除非实际修改到了那些文件。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
