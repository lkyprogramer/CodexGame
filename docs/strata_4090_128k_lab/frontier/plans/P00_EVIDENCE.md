# P00 · 证据、基线与最小适配准备

> 2026-10-30 已完成，阶段门 EVIDENCE_LOCKED。实际报告见实验主目录 `reports/P00-EVIDENCE-20261030.md`；机器回执在 `workspace/frontier/p00-20261030/PHASE_GATE.json`。P01未运行。

> 给执行AI：按本Phase任务执行；每Task最小验证，阶段收口按实质变更做独立review/test并复用有效证据。用户既有执行方式与权限优先，不因技能默认流程重复请求确认。本轮已实现P00身份、Pi历史投影、计划校验和schema及测试；P01 live适配器仍未实现。

**Goal：**离线完成所有可完成工作，阻止错误基线进入唯一诊断。

**Architecture：**复用旧lab和当前P6基线；新包只补资格、精确差量和验收合同。每个输出都有原件身份，不自动部署。

**Tech Stack：**Python标准库、现有Strata C++/CUDA12.3、sm89、已有Docker评分器。

**Spec：**[AI入口](../START_HERE_AI.md)、[基线](../docs/00_SNAPSHOT.md)、[数值质量](../docs/05_NUMERICS_AND_QUALITY.md)、[性能合同](../docs/06_BENCHMARK_PROTOCOL.md)。

## 全局约束

131072总context、4096token余量；GPU85°C停止、MemAvailable4096MiB下限；实验18089；禁止STAGE_PIN/ROUTE_RESIDENT；生产/回滚树只读；六FAIL不变；GPU串行；最多一候选。P6 mandatory env/build、EXACT6和原资产身份必须成立。缺证据不补猜。

## Review重点

wrong baseline/hidden defaults；自然分派改变导致数值漂移；物理重排与canonical映射混淆；缺请求/失败被丢；trace或诊断配置混入正式结果。每个相关Task必须在最小测试或证据核查中覆盖，不能靠最终声明。

## Task DAG

本Phase前置：无；只读准备。独立Task可并行，资源启动/同文件编辑必须串行。

### P00-T1 · 恢复身份与保护清单

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**读取原P6 BUILD_COMPLETE、六文件port、资产/配置manifest、13项生产保护及原六FAIL定位。实际原件缺失时写BLOCKED_EVIDENCE；报告链接不能代替raw。构建source/env/build三个独立身份域，mandatory env/build按LOCK。只读源仓，不修改生产树。

**文件/接口/产出：**计划新增 tools/frontier/identity.py::collect_identity(config_path: Path)->dict；输出IDENTITY.json与PROTECTION_BEFORE.json。未获目标机执行范围时只完成本地映射，远端字段明确NOT_READ。

**最小验证：**新增tests/test_frontier_identity.py：缺原始hash、错误P6二进制、HC混入、默认env冲突、VERIFY_PROFILE键为0、资产不匹配必须拒绝；临时key不输出。纯mock读取即可。

- [x] 核实输入和依赖，记录source/config/请求身份。
- [x] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [x] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [x] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P00-T2 · 去重诊断相关来源与关闭项

**依赖：**本Phase前置门；可与无文件冲突的同Phase任务并行。

**任务内容与边界：**复用既有关闭项映射，聚焦本次暖态诊断可能命中的KV、活跃内存、CPU专家与供给/同步路径，核源码symbol与真实配置；固定A0、P6和相关donor SHA。将closed/new_delta/covered/hardware_blocked分开，不把仓库星数/跑分倍率作资格。不要求先扫完十二卡或64方向；与本次诊断无关的Maya prefill分支等保留研究状态。

**文件/接口/产出：**修改本轮workspace的SOURCE_DELTA.json，不改sources/LOCK.json历史；每行old_id/new_id/path/symbol/base_blob/donor_blob/presence/remaining_question。

**最小验证：**最小验证：抽查本次诊断相关路径的真实文件和symbol；不存在/默认已命中/不可构建为明确终态。校对引用不可变SHA，不需GPU。

- [x] 核实输入和依赖，记录source/config/请求身份。
- [x] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [x] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [x] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P00-T3 · 实现诊断计划和结果接口

**依赖：**P00-T1。

**任务内容与边界：**复用旧runner的资源锁/PID/guard，先完成纯计划检查和结果schema；明确哪些函数实际存在，哪些由本Task新增。不得复制一个新通用benchmark平台。复用本包offline工具与原quality gate，各自职责不重叠。

**文件/接口/产出：**计划新增 tools/frontier/warm_plan.py::validate_warm_plan(plan,policy)->dict；定义REQUESTS/WINDOWS/DEPENDENCIES字段。输出DIAGNOSTIC_PLAN.json草案，不能返回live PASS。正式P05仍须现存稳定warm fixed2048原件；缺失即BLOCKED_EVIDENCE，不因本次诊断完成而解除。

**最小验证：**新增tests/test_frontier_warm_plan.py：1引擎/最多3请求/3600秒上限；100K prime后两次真实Pi短追问append，观察实际新读量；每请求目标及上限2048输出、deadline不超过600秒、收尾至少120秒；输入+2048+4096；禁止env、额外对照/profiler、未知/重复engine、越界计数及不可用授权引用都拒绝。短输出保留并以INSUFFICIENT停止，不强迫延长。2026-10-30用户决定以真实Pi追问观察实际新读量，替代旧3K目标/区间提案；冻结消息hash和来源，禁止填充。append输入上界至少为前一上界+2048+append_user_tokens_upper_bound+64；运行仍强验完整context预算。

- [x] 核实输入和依赖，记录source/config/请求身份。
- [x] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [x] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [x] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

### P00-T4 · 独立Phase复核

**依赖：**P00-T1, P00-T2, P00-T3。

**任务内容与边界：**独立Reviewer核原证据与baseline，独立Validator运行最小离线测试并验证缺输入会拒绝。只对当前准备范围给结论；未读取目标机不宣称已经保护校验成功。

**文件/接口/产出：**输出P00_REVIEW.md、P00_TEST.md、PHASE_GATE.json；合格状态EVIDENCE_LOCKED，缺raw或权限BLOCKED_EVIDENCE。

**最小验证：**在隔离工具树运行本Phase新增单测；本包运行python3 -B frontier/tools/validate.py --root frontier（在实验主目录运行）。验证输出路径、原件只读和FAIL不被删除。

- [x] 核实输入和依赖，记录source/config/请求身份。
- [x] 完成本Task限定交付，保留失败与未知；不扩展范围。
- [x] 执行上述最小验证并写Task回执，标清offline/CPU/GPU。
- [x] 更新本轮台账；T4独立门后按已授权范围转下一Phase。

## 结束与证据复用

只有当前Phase明确通过才沿成功路径前进。硬门失败立即归档并归还资源；不自动修复环境后重跑同一统计批次。开发阶段的离线代码修正与必要测试可以继续，已消耗GPU样本仍保留，不伪装新样本。合格旧证据按源码/配置/实际路径有效性复用，失效原因必须具体。
