# 修改边界与复用

当前只改本V4文档及本次范围审计输出。不改NInfer/P5源代码、旧Baseline/BO/G1/P1—P4报告或评分附件，不运行产品测试、GPU、模型、HTTP、grader，不启动原服务。

未来选中实验复用现有模块：GDN helper/typed records、原kernel launcher、现有workspace planner/Graph目录、原MTP/Target sampler/processor/许可提交、已有请求/job观测。共享public头、CMake、缓存格式和生命周期有一个明确owner，必要修改在同一集成树评审；不为模块化另建第二套权威。

每个任务具体modify边界在[注册表](02-task-registry.md)。需要跨路线联动时先说明现实依赖与选中scope，不因文件同目录就扩大到全模型/多协议/UI。评审/实现不伪造独立性，本轮文档由当前代理检查，未启动新的独立reviewer。
