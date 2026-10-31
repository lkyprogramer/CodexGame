# P04 · 匹配数值、生命周期与成本

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。本文列出的frontier适配器与测试是未来计划新增，当前包未包含live适配器。

**Goal：**先证明候选做同样工作且影响真实可省成本。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

本Phase前置：P03。独立Task可并行，资源启动/同文件编辑必须串行。

### P04-T1 · 匹配分派oracle

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**复用原oracle，先同快照A/A。比较canonical有效值/scale/IDs/order/mask和所有提交状态；物理重排按映射校验。实际chunk而非输入长度覆盖4096/16384、尾块。

**文件/接口/产出：**计划新增tools/frontier/numeric_run.py::run_numeric(plan_path,output_dir)->Path，只包装原oracle；输出NUMERIC_RECEIPT、首差异算子与rawmanifest。

**最小验证：**该候选最小正/负例，故意错1byte必须失败；任何未知数值差异停止，不去性能。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P04-T2 · 真实生命周期与资源边界

**依赖：**P04-T1。

**任务内容与边界：**针对候选覆盖cancel/short-long-short/restore/graph recapture/loan epoch。memory改动运行必要memcheck/redzone；只调诊断加载配置时单独命名，不带进正式臂。

**文件/接口/产出：**输出LIFECYCLE.json、SANITIZER.json、资源峰值/生存区间、NORMAL_CONFIG_RESTORE.json。

**最小验证：**复用仍适用的P20/P21/P22证据，只增改变的边界；无目标GPU记录NOT_RUN，OOM等硬拒绝。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P04-T3 · 成本机制命中

**依赖：**P04-T1, P04-T2。

**任务内容与边界：**最多一对有界机制trace，核实际hit、减少的是load/bytes/allocation/暴露等待中的哪项，新增代价完整记。固定分派证明不能替代自然分派结果。

**文件/接口/产出：**输出COST_RECEIPT.json，具体单位和raw引用，不含性能采用结论。

**最小验证：**无实际命中、只减隐藏bytes、资源账变坏或自然路径升级E1且质量缺前提，分别结束为campaign的NO_GAIN，或候选DEFERRED_QUALITY并映射campaign的BLOCKED_QUALITY后收口。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P04-T4 · 独立oracle与归档验证

**依赖：**P04-T3。

**任务内容与边界：**Reviewer逐条核canonical映射与数据生命周期，Validator核raw数量/完整性、负例/实际命中/诊断配置恢复。禁止因为成本门通过直接采用。

**文件/接口/产出：**输出P04_REVIEW/P04_TEST/PHASE_GATE，成功仅NUMERIC_LIFECYCLE_SUPPORTED。

**最小验证：**hash与字节比较复算在离线完成，不为“独立”重跑全部长GPU回放。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
