# Strata × Flash-Next × RTX4090 极限优化实验室 v2

**研究日期：2026-10-25。交付：64方向图谱、13份实施计划、固定源码证据、附件进展审计、验证工具和测试。**

本包服务于一个明确目标：在单RTX4090 / Silver4216 / 64GB机器上，把真实Java/Pi任务的正确完成时间压低。它包含后续AI可执行的引擎改造设计与已实现的实验工具修复；**没有包含已完成的新引擎优化，也没有新的目标机性能成绩。**

## 从哪里开始

| 读者/目标 | 入口 |
|---|---|
| 先看结论、排序、适用边界 | [REPORT.md](REPORT.md) |
| 交给AI实施 | [START_HERE_AI.md](START_HERE_AI.md)，然后[P00](plans/P00_BASELINE_AND_MEASUREMENT.md) |
| 查64个方向与评分 | [图谱](docs/05_DIRECTIONS_ATLAS.md)、[排序](docs/06_PRIORITIES_AND_DEPENDENCIES.md)、[JSON](config/directions.json) |
| 深入源码与donor | [内核审计](docs/08_KERNEL_SOURCE_AUDIT.md)、[donor对照](docs/07_DONOR_RESEARCH.md)、[已有能力纠偏](docs/10_EXISTING_VS_NEW.md) |
| 核对本轮到底验证了什么 | [VALIDATION.md](VALIDATION.md)、[工具接口](HARNESS_UPGRADE.md) |
| 附件历史与本机事实 | [事实表](docs/01_MACHINE_AND_PROGRESS.md)、[原报告](history/reports/DEPLOY-A0-EXACT6-20261025.md) |
| 源码冻结/引用 | [LOCK](sources/LOCK.json)、[索引](sources/INDEX.md)、[最新delta](docs/02_LATEST_BASELINE_DELTA.md) |

## 三个身份不能混

- 旧生产：v0.2.3 / `5c8dd322…` + EXACT6 + 已完成host tuning。
- 深入审计：main `41cf05a0…`，审计文件保留固定源码引用。
- 最终执行基线：main `4b9e05a2…` / v0.2.6，最后刷新发现新发布并完成增量审查。Qwen发布包仍0.1.50；Control/DeepSeek是0.1.51。源码构建身份以SHA、依赖、flags和binary hash为准。

## 先运行离线检查

在解压后的包根目录：

```bash
python3 -B -m lab.cli verify
python3 -B -m lab.cli selftest
python3 -B -m lab.cli validate-plan --plan plans/park_restore.example.json
python3 -B tools/quality_gate.py --input tools/examples/quality-smoke-30.json
```

最后一个使用演示数据，预期返回NONINFERIORITY_NOT_ESTABLISHED、退出1（在总体实验状态中归INSUFFICIENT）；不是模型测试。参考准确命令、退出码与当前测试环境见VALIDATION和工具说明。无需GPU即可检查包、运行多数工具测试；JDK/网络loopback等缺失会明确跳过或失败。

## 状态与原则

所有候选默认IDEA/ELIGIBLE/NOT_APPLICABLE，未到SCENARIO_PASS。排序分数不是预测加速百分比。先测真实路径、再做一个最小改造、再验证数值与任务、最后看端到端wall。缓存修复、steady decode、cold prefill、质量近似分别报告；不能将收益相加。

原附件报告按历史证据保留，不改写成新的测试记录。`MANIFEST.sha256`校验随包内容；执行结果输出到新的workspace，不覆盖研究文本。若AI更新文档或工具，生成新版本manifest并记录变更，不能删完整性检查绕过。
