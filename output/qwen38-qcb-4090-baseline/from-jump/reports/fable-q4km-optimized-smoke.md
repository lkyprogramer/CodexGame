# fable-q4km-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `fable-q4km-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M` |
| Template | `fable-native-medium-override` |
| 模型 SHA-256 | `f5eeeee69f5cf9dfea8412a01a1c2ef594b93c5683675e275b9c2936fab7623f` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `smoke` |
| Context | `112000` |
| Reasoning effort | `medium` |
| MTP | `True` |
| Seeds | `[42]` |

## 2. 数据完整性

| 指标 | 结果 |
|---|---:|
| 运行数 | 12 |
| 唯一题目 | 12 |
| 重复 task/seed | 0 |
| Reasoning Token 覆盖率 | 0.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 100.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 16.7% |
| Partial Test Pass Rate | 28.1% |
| Category Balanced Index | 18.9% |
| Worst Category Index | 0.0% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 0.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 2 | 0.0% | 8.3% | 1.7% | N/A |
| bug_fix | 2 | 2 | 0.0% | 10.0% | 2.0% | N/A |
| repo_engineering | 3 | 3 | 0.0% | 0.0% | 0.0% | N/A |
| agent_tool | 2 | 2 | 100.0% | 100.0% | 100.0% | 54.1 |
| long_context | 1 | 1 | 0.0% | 0.0% | 0.0% | N/A |
| code_review | 2 | 2 | 0.0% | 50.0% | 10.0% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 54.1 s |
| 成功任务耗时 P90 | 81.2 s |
| 成功任务生成 Token 中位数 | 4244.0 |
| Reasoning Token 中位数 | N/A |
| 成功任务/Wall-hour | 5.06 |
| Prompt tok/s 中位数 | 722.3 |
| Decode tok/s 中位数 | 78.8 |
| MTP acceptance | 61.7% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 196 |
| Invalid tool calls | 6 |
| Valid tool-call rate | 96.9% |
| Tool operation success | 44.2% |
| Public test runs | 2 |
| Public-test recovery candidates | 0 |
| Public-test recovery rate | N/A |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22272 MB |
| Median average GPU utilization | 86.8% |
| Peak power | 447.4 W |
| Peak temperature | 84.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 1 | 100.0% | 100.0% | 20.2 | 1351.0 |
| AT002 | agent_tool | 1 | 100.0% | 100.0% | 88.0 | 7137.0 |
| BF001 | bug_fix | 1 | 0.0% | 0.0% | 83.9 | 7124.0 |
| BF004 | bug_fix | 1 | 0.0% | 20.0% | 84.8 | 6510.0 |
| CR001 | code_review | 1 | 0.0% | 40.0% | 45.7 | 2985.0 |
| CR002 | code_review | 1 | 0.0% | 60.0% | 39.6 | 2555.0 |
| LC001 | long_context | 1 | 0.0% | 0.0% | 55.6 | 4696.0 |
| RE001 | repo_engineering | 1 | 0.0% | 0.0% | 267.2 | 20039.0 |
| RE004 | repo_engineering | 1 | 0.0% | 0.0% | 157.5 | 14082.0 |
| RE007 | repo_engineering | 1 | 0.0% | 0.0% | 84.8 | 6552.0 |
| SF001 | single_file | 1 | 0.0% | 0.0% | 473.0 | 32638.0 |
| SF002 | single_file | 1 | 0.0% | 16.7% | 22.4 | 1662.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 10 |
| `tool_budget_exhausted` | 2 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
