# 01 · 实验设计

## 假设层级

- **H1 权重质量：** 在 Normalized 条件下，finetune 的分类平衡指数优于 Original，且 Hard Success 非劣。
- **H2 Agent 效率：** 在成功率非劣前提下，finetune/template 降低成功任务耗时、reasoning token 或无效工具调用。
- **H3 部署效率：** Optimized 组合在 24GB 显存约束下提高成功任务/小时，且最差类别无重大回退。

## 实验单位

最小单位是 `(task_id, seed, model_config, lane, benchmark_version)`。模型比较必须按 task+seed 配对，禁止比较不相交样本的简单平均。

## 分阶段策略

| 阶段 | Suite | Seeds | 用途 |
|---|---:|---:|---|
| Gate | smoke 12 | 1 | 排除工具调用损坏、严重退化和部署不稳定 |
| Main | core 32 | 3 | 主质量与效率比较 |
| Full | full 48 | 3 | 全覆盖诊断 |
| Final | finalists 27 | 5 | 对前三名提高统计稳定性 |

## Seed

推荐固定 `11,29,47`；决赛增加 `71,97`。temperature=0 的后端仍可能受并行调度、采样实现和 MTP 影响，因此保留多次运行。

## 阻断与轮换

一次 block 中每个模型跑相同题目/Seed，顺序按 Latin-square 轮换。不要“先跑完模型 A 全部，再跑 B”，否则温度、缓存、系统负载和服务长期漂移会与模型混杂。

## 故障处理

- 端点连接失败、进程崩溃：标为 infrastructure error，可按预先规则重跑一次；
- 无效 JSON、无 patch、patch 应用失败、超 tool budget：模型失败，不人工重跑；
- 隐藏测试超时：保留日志，区分模型补丁导致与基础设施导致；
- 任何选择性重跑必须在报告中列出。
