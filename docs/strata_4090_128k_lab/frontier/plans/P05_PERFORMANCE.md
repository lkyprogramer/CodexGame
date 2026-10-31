# P05 · 正式无插桩完整请求配对

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。本文列出的frontier适配器与测试是未来计划新增，当前包未包含live适配器。

**Goal：**以完整请求时间门检验成本优化是否兑现。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

本Phase前置：P04。独立Task可并行，资源启动/同文件编辑必须串行。

### P05-T1 · 冻结A/A与正式计划

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**先核同B/模板/tokenizer/采样/PT0的现存稳定warm探针原件，实际prime/history、append完整hash、warm reuse及自然fixed2048均合格才允许任何P05 GPU启动；缺证据即BLOCKED_EVIDENCE/NOT_RUN，不搜新题。然后本轮warm decode固定primary_metric=decode_ms（fixed2048下等价于ms/token），再恢复普通配置并逐个删除presence-sensitive计时/采集env。仅使用同一主指标的A/A计算噪声，禁止拿TTFT噪声定decode门。若无同B同负载的合格A/A，最多先做预登记的3对A/A校准；固定m并封存后才看候选。A/A质量/长度不稳定则停止，不追加碰运气。

**文件/接口/产出：**计划新增tools/frontier/perf_plan.py::build_perf_plan(identity,case,aa_receipt)->dict；输出PREREG_PERF。六对AC/CA/CA/AC/AC/CA；12引擎/24请求主场景。若另需3对A/A，加6引擎/12请求；含支持层时本Phase上限为复用AA的20引擎/40请求或新增AA的26引擎/52请求，不含P01/P04/质量热测试。

**最小验证：**纯测试检查计数、pair/id/hash、warmchain、所有env真正unset；m不能事后变。A/A样本少的限制必须写明，不能假装noise精确已知。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P05-T2 · 执行唯一主批次

**依赖：**P05-T1。

**任务内容与边界：**有GPU租约且前门有效才执行。每臂fresh engine prime+append，固定2048探针输出，sample配置不变；prime后、append发送前核实际完整请求/token hash，首个不符立即停止，不能用recipe hash或替换历史过门。失败/温度/资源终止保留，不替补。

**文件/接口/产出：**计划新增tools/frontier/perf_run.py::run_paired(plan_path,output_dir)->Path，复用旧护栏；输出完整REQUESTS/SSE/RESOURCES/COMPLETION。

**最小验证：**先验收全部12engine/24requests，request/template/token/config等身份一致、fixed输出、warmreused成立。身份或轨迹无法比较则整批无资格。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P05-T3 · 统计及有限支持层

**依赖：**P05-T2。

**任务内容与边界：**用严格6对exact bootstrap计算时间ratio。main CI上界≤1−m，所有关键非目标≤1.02。主门通过才做4K与120K各2对支持层，不混进主统计；只做描述性支持与异常筛查，不据此宣称正式2%统计非劣，也不产生p99/全天结论。

**文件/接口/产出：**输出ANALYSIS.json、REPORT.md、支持层原件。离线输入适配到tools/paired_stats.py；真实采样任务另用restrictedtime，不塞进fixedtoken统计。

**最小验证：**离线重算一致；失败/缺对/错hash/重复engine要被工具拒绝。支持层不能成为主门失败后的新主指标。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P05-T4 · 独立性能审阅

**依赖：**P05-T3。

**任务内容与边界：**Reviewer查未插桩、自然配置、收益来源、时钟/内存/热限制；Validator从完整原件重算整对统计，检查无幸存者筛选。

**文件/接口/产出：**输出P05_REVIEW/P05_TEST；通过只PERFORMANCE_GATE_ONLY，拒绝或不足即收口。

**最小验证：**原报告指标与raw计算一致；同一脚本的两个输出不算独立原件验证。

- [ ] 核实输入和依赖，记录source/config/请求身份。
- [ ] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [ ] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [ ] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
