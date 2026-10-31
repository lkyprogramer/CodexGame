> 2026-10-30实际执行已收口：1engine/1prime，941<2048，两个append NOT_RUN，结果INSUFFICIENT。最小适配器已实现；下文保留原合同，不表示三请求全通过或允许重跑。

# P01 · 一次限额暖态长会话诊断

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。根tools/frontier的最小适配器与测试已实现；下文保留原预登记要求，实际执行及未覆盖项以上方结果与报告为准。

**Goal：**用单引擎、最多3请求观察真实暖态完成路径，判定是否有可消除成本；不作因果加速或无插桩严格上界结论。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

本Phase前置：P00。独立Task可并行，资源启动/同文件编辑必须串行。

### P01-T1 · 低开销采集与有界执行适配

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**复用既有低开销日志与guard，保持真实graph/fusion。STRATA_VERIFY_PROFILE必须从env移除且核实际PID。只监听本轮owner进程，统一clock domain。新增打点的扰动若无法分离，结果为INSUFFICIENT；不自动增加profiler或off/on对照。

**文件/接口/产出：**计划新增tools/frontier/warm_run.py::run_diagnostic(plan_path,identity_path,output_dir)->Path；复用旧runner。新增窄native打点时PATCH_SCOPE必须不改数学/分派，并输出off/source差量。

**最小验证：**新增tests/test_frontier_warm_run.py：模拟单引擎最多3请求计数、3600秒全程deadline、每请求不超过600秒及至少120秒收尾预留、超时/温度/外来GPU/进程退出时停止，mock不得启动真实服务；错误身份或剩余预算不足不得发送新请求。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P01-T2 · 冻结实际prime与append输入

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**按04协议固定单引擎prime→append_1→append_2；来自原语料或授权脱敏任务。离线冻结template/tokenizer、100K级prime body/token hashes、采样seed及两次append渲染配方、真实Pi追问消息hash、来源和保守预算。每请求目标和上限均2048输出，deadline不超过600秒。每次使用自己实际生成的完整正文/thinking历史按PT0合同回传，再渲染下一请求并核hash、完整context预算。2026-10-30用户决定保留真实Pi短追问并观察实际新读量，替代旧3K目标/区间提案。new_read_policy=observe_actual_pi_followup；target和allowed_range均null。实际read含PT0重读正文，只记录不以新读目标设门。每条append冻结用户消息hash/来源及append_user_tokens_upper_bound（当前256）；保守输入上界至少为前一上界+2048+用户上界+64模板/BPE余量。运行仍逐次核验完整渲染预算与真实历史，不符即保留并INSUFFICIENT停止。禁止重写历史、缩prompt、填充追问或强迫相同回答凑数。

**文件/接口/产出：**输出PREREGISTRATION.json、REQUEST_PLAN.json与budget清单；单引擎最多3请求、100K prime及两次真实Pi短追问append，实际新读量仅观察；每请求target/max_output2048、deadline≤600秒，全程≤3600秒，收尾≥120秒。实际token数用冻结tokenizer。

**最小验证：**离线用warm_plan验证1个prime与2份append配方及最坏输出预算；运行时逐请求验收完整token预算、hash与真实read/reused。输出少于2048（含正常EOS）保留并INSUFFICIENT停止，不强迫延长。无tokenizer/真实模板则BLOCKED_EVIDENCE，不用字符估算。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P01-T3 · 目标机一次执行

**依赖：**P01-T1, P01-T2。

**任务内容与边界：**仅在本次执行范围和GPU交接已成立时取全局锁，核服务/保护与无外来负载；执行唯一矩阵。总预算包括加载和收尾。任一硬失败保留并结束，不补跑；自己的PID清理，不恢复生产。

**文件/接口/产出：**输入冻结PLAN/IDENTITY；输出REQUESTS.jsonl、WINDOWS.jsonl、MEMORY.jsonl、原始SSE、guard、HAND_BACK。原来已PAUSED的自动化不修改。

**最小验证：**最小实际验收：1/3上限、实际nativePID、正确端口、实际渲染输入与配方一致、真实history原样回传、warm read/reuse、资源guard全覆盖；未跑项目明确NOT_RUN。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P01-T4 · 重建依赖并独立复核

**依赖：**P01-T3。

**任务内容与边界：**从实际window起止、CUDA依赖与CPU完成重建DAG。unknown不填零。单臂日志只支持本次观察条件下的资格；不归因采集开销、因果加速或外推无插桩严格上界。新打点扰动无法分离则INSUFFICIENT。Reviewer查因果，Validator查计数/时间域/原件哈希。

**文件/接口/产出：**计划新增tools/frontier/critical_path.py::summarize_windows(trace_paths,identity)->dict；输出DEPENDENCIES.json、QUALIFICATION.json、P01_REPORT.md。

**最小验证：**用离线headroom验证区间并集和条件模型；测试重叠区间/错误时钟/缺依赖均拒绝或INSUFFICIENT。P01不产生PERFORMANCE_GATE_ONLY。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
