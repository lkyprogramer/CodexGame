# synthetic-original — QCB-4090 测试报告

> **警告：这是合成数据，只用于验证报告管线，不代表任何真实模型性能。**

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `unknown` |
| 模型 | `synthetic-original` |
| 家族 | `SYNTHETIC-NOT-A-REAL-MODEL` |
| 量化 | `Q4_K_M` |
| Template | `synthetic` |
| 模型 SHA-256 | `N/A` |
| Hash 状态 | `not_checked` |
| 赛道 | `normalized` |
| Suite | `smoke` |
| Context | `32768` |
| Reasoning effort | `medium` |
| MTP | `False` |
| Seeds | `[11, 29, 47]` |

## 2. 数据完整性

| 指标 | 结果 |
|---|---:|
| 运行数 | 36 |
| 唯一题目 | 12 |
| 重复 task/seed | 0 |
| Reasoning Token 覆盖率 | 100.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 0.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 80.6% |
| Partial Test Pass Rate | 90.3% |
| Category Balanced Index | 81.7% |
| Worst Category Index | 70.0% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 58.3% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 6 | 83.3% | 91.7% | 85.0% | 25.0 |
| bug_fix | 2 | 6 | 83.3% | 91.7% | 85.0% | 26.5 |
| repo_engineering | 3 | 9 | 77.8% | 88.9% | 80.0% | 30.2 |
| agent_tool | 2 | 6 | 83.3% | 91.7% | 85.0% | 32.8 |
| long_context | 1 | 3 | 66.7% | 83.3% | 70.0% | 34.2 |
| code_review | 2 | 6 | 83.3% | 91.7% | 85.0% | 37.5 |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 30.2 s |
| 成功任务耗时 P90 | 36.7 s |
| 成功任务生成 Token 中位数 | 595.0 |
| Reasoning Token 中位数 | 218.5 |
| 成功任务/Wall-hour | 96.00 |
| Prompt tok/s 中位数 | N/A |
| Decode tok/s 中位数 | N/A |
| MTP acceptance | N/A |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 198 |
| Invalid tool calls | 0 |
| Valid tool-call rate | 100.0% |
| Tool operation success | 100.0% |
| Public test runs | 0 |
| Public-test recovery candidates | 0 |
| Public-test recovery rate | N/A |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 18443 MB |
| Median average GPU utilization | N/A% |
| Peak power | N/A W |
| Peak temperature | N/A °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 100.0% | 100.0% | 32.8 | 633.0 |
| AT002 | agent_tool | 3 | 66.7% | 83.3% | 34.0 | 652.0 |
| BF001 | bug_fix | 3 | 100.0% | 100.0% | 26.5 | 538.0 |
| BF004 | bug_fix | 3 | 66.7% | 83.3% | 27.8 | 557.0 |
| CR001 | code_review | 3 | 100.0% | 100.0% | 36.5 | 690.0 |
| CR002 | code_review | 3 | 66.7% | 83.3% | 37.8 | 709.0 |
| LC001 | long_context | 3 | 66.7% | 83.3% | 35.2 | 671.0 |
| RE001 | repo_engineering | 3 | 66.7% | 83.3% | 29.0 | 576.0 |
| RE004 | repo_engineering | 3 | 100.0% | 100.0% | 30.2 | 595.0 |
| RE007 | repo_engineering | 3 | 66.7% | 83.3% | 31.5 | 614.0 |
| SF001 | single_file | 3 | 100.0% | 100.0% | 24.0 | 500.0 |
| SF002 | single_file | 3 | 66.7% | 83.3% | 25.2 | 519.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 36 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
