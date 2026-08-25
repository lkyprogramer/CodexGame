# salience-r5-q4km-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `salience-r5-q4km-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M` |
| Template | `salience-native` |
| 模型 SHA-256 | `09283343875f15f318ba8ceab76a7d24972f1dca01c91b06f944784e098ec2a2` |
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
| Hard Task Success Rate | 58.3% |
| Partial Test Pass Rate | 70.0% |
| Category Balanced Index | 55.1% |
| Worst Category Index | 0.0% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 0.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 2 | 100.0% | 100.0% | 100.0% | 404.4 |
| bug_fix | 2 | 2 | 50.0% | 90.0% | 58.0% | 35.8 |
| repo_engineering | 3 | 3 | 66.7% | 66.7% | 66.7% | 172.3 |
| agent_tool | 2 | 2 | 100.0% | 100.0% | 100.0% | 73.4 |
| long_context | 1 | 1 | 0.0% | 0.0% | 0.0% | N/A |
| code_review | 2 | 2 | 0.0% | 30.0% | 6.0% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 122.1 s |
| 成功任务耗时 P90 | 428.0 s |
| 成功任务生成 Token 中位数 | 10787.0 |
| Reasoning Token 中位数 | N/A |
| 成功任务/Wall-hour | 15.37 |
| Prompt tok/s 中位数 | 714.9 |
| Decode tok/s 中位数 | 79.3 |
| MTP acceptance | 64.1% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 185 |
| Invalid tool calls | 8 |
| Valid tool-call rate | 95.7% |
| Tool operation success | 61.0% |
| Public test runs | 3 |
| Public-test recovery candidates | 1 |
| Public-test recovery rate | 100.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22622 MB |
| Median average GPU utilization | 84.2% |
| Peak power | 449.0 W |
| Peak temperature | 84.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 1 | 100.0% | 100.0% | 24.7 | 1557.0 |
| AT002 | agent_tool | 1 | 100.0% | 100.0% | 122.1 | 10787.0 |
| BF001 | bug_fix | 1 | 100.0% | 100.0% | 35.8 | 2956.0 |
| BF004 | bug_fix | 1 | 0.0% | 80.0% | 31.3 | 2700.0 |
| CR001 | code_review | 1 | 0.0% | 0.0% | 66.9 | 4292.0 |
| CR002 | code_review | 1 | 0.0% | 60.0% | 45.2 | 2956.0 |
| LC001 | long_context | 1 | 0.0% | 0.0% | 103.0 | 8976.0 |
| RE001 | repo_engineering | 1 | 100.0% | 100.0% | 134.2 | 11048.0 |
| RE004 | repo_engineering | 1 | 100.0% | 100.0% | 210.4 | 20062.0 |
| RE007 | repo_engineering | 1 | 0.0% | 0.0% | 57.2 | 5372.0 |
| SF001 | single_file | 1 | 100.0% | 100.0% | 754.5 | 32516.0 |
| SF002 | single_file | 1 | 100.0% | 100.0% | 54.3 | 4289.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 12 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
