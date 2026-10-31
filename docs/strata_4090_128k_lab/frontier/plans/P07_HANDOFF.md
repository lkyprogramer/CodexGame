# P07 · 报告、回滚与资源归还

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。本文列出的frontier适配器与测试是未来计划新增，当前包未包含live适配器。

**Goal：**交付可审阅结果；保持生产原状态。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

成功路径前置：P06。任意Phase出现终态时，可以直接进入本Phase的报告、资源归还与终态审核，不要求P06成功；跳过的Phase仍为NOT_RUN，不标通过。清理优先于其他收口任务。独立Task可并行，资源启动/同文件编辑必须串行。

### P07-T1 · 收口科学结论

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**从任何终态都能走此收口工作；列所有执行/未执行项、局部与完整结果、限制、新增候选是否为0。保留旧结论，不把少数1%相乘。

**文件/接口/产出：**输出FINAL_REPORT.md、DECISION.json，链接rawmanifest/统计/质量/资源。采用templates/FINAL_REPORT.md。

**最小验证：**关键数字与原件交叉核对；结论不超证据，所有单位/分母/CI清楚。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P07-T2 · 可审阅补丁和回滚

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**若有有效候选，给源码diff、build/env差量、off默认、回滚说明和生产拟变更清单；没有候选则明确无变更。不推送、merge、部署或开生产。

**文件/接口/产出：**输出PATCH_MANIFEST.json、ROLLBACK.md、PROPOSED_CHANGE.md；不含模型/binary/密钥。

**最小验证：**离线检查patch scope和关闭路径回退证据；生产变更必须另有明确授权，不将READY文件当授权。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P07-T3 · 保护复核和归还

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**只终止本轮拥有的PID/进程组；关闭实验端口，核13保护hash及生产状态未变，记录GPU归还时点。未实际占资源时写未占用，不编造现场核查。

**文件/接口/产出：**复用tools/frontier/handoff.py::finalize_owned_resources(run_manifest)->dict；输出PROTECTION_AFTER/HAND_BACK。

**最小验证：**负例确保外来PID不清理；检查本轮process ledger闭合，artifact脱敏。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P07-T4 · 最终独立验收与停止

**依赖：**P07-T1, P07-T2, P07-T3。

**任务内容与边界：**Reviewer检查完整结论、Validator检查manifest/文档/原件计数。任何未满足门保留。归档后结束本campaign，不新增轮询/自动优化任务。

**文件/接口/产出：**输出DELIVERY_CHECK.json和最终摘要。READY_FOR_HUMAN_REVIEW仅指可审阅，deployment=false。

**最小验证：**python3 -B tools/validate.py --root .；python3 -B tools/verify_manifest.py --root . --manifest MANIFEST.sha256；只证明交付完整。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
