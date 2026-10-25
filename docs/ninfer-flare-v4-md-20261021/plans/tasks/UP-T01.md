# UP-T01｜上游性能改动选择性或完整合并对照

状态：PENDING / PROPOSED。前置：`K0-GATE`。

性能假设：上游的缓存、prefill、small-T与共享路径可能提速；合并范围必须由真实收益/依赖支持。

准入：候选入口保留；本轮未找到U28—U34纯文本Chat直接提速证据，完整合并当前不优先。

## 修改边界与步骤

范围：固定O/U与P4之间必要共享路径；不以协议/UI完整性扩验收。

1. 复用本轮U01—U34源码审计：U01—U27已在P1—P4吸收，性能收益尚需配对；U28—U34余量见专项报告。
2. 默认选择有纯Chat收益或必要耦合依赖的最小改动；若拆分成本/风险更高，允许从干净P4分支建立完整U34候选，先与P4配对；选择性版本已有适用证据时再复用其对照，不强制三版本新测试。
3. 完整合并携带的未启用API/UI是源码范围，不变成开发/性能验收必做；共享格式变化必须验证缓存隔离，不覆盖原cache目录。

## 必须证明

- **CHATPERF-UP-T01-V01** 每个被选改动有当前纯Chat调用可达证据、性能假设或必要耦合依赖；提交名不能代替源码判断。
- **CHATPERF-UP-T01-V02** 保留18处G1差异及已修复前端/增量流/并发合同；不采用P5未评审树冒充可构建候选。
- **CHATPERF-UP-T01-V03** 对实际触及的共享状态/缓存版本、取消/故障和Chat做必要验证，完整merge不等于所有模型/协议重新全验。
- **CHATPERF-UP-T01-V04** 完整版计入构建、内存、cache冷启动/迁移与服务wall；无净收益或更大回归则用选择性版本或P4。

## 预算、证据和退出

拟议上限：{"wire_max": 32, "client_model_requests_max": 24, "warmup_submissions_max": 2, "total_model_submissions_max": 26, "gpu_minutes_max": 45, "native_shapes_max": 4, "native_calls_max": 84, "traces_max": 2}。预计：选择性0.5–2工程日；完整U34预计2–5工程日（含9冲突重做/评审），pilot20–45分钟。这些是规划值，当前不执行GPU、模型、HTTP、grader或产品修改。

复用[统一预算](../08-validation-budget-and-estimate.md)与[适用验收合同](../../design/05-validation-and-qualification.md)，在一个集成树上保留所有原始输入、request/raw、构建/镜像/脚本身份和失败成本。必要验证通过即停止；只复测失败及受影响路径。不改采样/context/Pi预算，不重跑旧Baseline、题目或grader。未知结果先readback，不自动重发。

无热点、资产或资源条件不成立时记录NOT_SELECTED/BLOCKED，不能造PASS。试验失败保留原路由及证据，不提升为生产候选。实际生产另走[发布门禁](../phases/K4-GATE.md)。

来源任务：P5-T01, P5-T05, P6-T01；旧合同的原字节与去向见[范围审计](../10-task-scope-audit.md)。
