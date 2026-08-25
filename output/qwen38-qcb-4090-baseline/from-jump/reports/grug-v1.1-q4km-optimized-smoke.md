# grug-v1.1-q4km-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `grug-v1.1-q4km-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M` |
| Template | `grug-native` |
| 模型 SHA-256 | `c158a0ffad48c3a0de56f502340dc9d588625212ca7175495132445c3825134d` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `smoke` |
| Context | `112000` |
| Reasoning effort | `medium` |
| MTP | `False` |
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
| Partial Test Pass Rate | 16.1% |
| Category Balanced Index | 16.6% |
| Worst Category Index | 0.0% |
| Invalid Output Rate | 16.7% |
| 不稳定题目率 | 0.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 2 | 0.0% | 0.0% | 0.0% | N/A |
| bug_fix | 2 | 2 | 0.0% | 0.0% | 0.0% | N/A |
| repo_engineering | 3 | 3 | 0.0% | 0.0% | 0.0% | N/A |
| agent_tool | 2 | 2 | 0.0% | 16.7% | 3.3% | N/A |
| long_context | 1 | 1 | 0.0% | 0.0% | 0.0% | N/A |
| code_review | 2 | 2 | 100.0% | 80.0% | 96.0% | 16.4 |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 16.4 s |
| 成功任务耗时 P90 | 21.1 s |
| 成功任务生成 Token 中位数 | 707.0 |
| Reasoning Token 中位数 | N/A |
| 成功任务/Wall-hour | 3.33 |
| Prompt tok/s 中位数 | 275.0 |
| Decode tok/s 中位数 | 46.3 |
| MTP acceptance | N/A |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 345 |
| Invalid tool calls | 3 |
| Valid tool-call rate | 99.1% |
| Tool operation success | 30.4% |
| Public test runs | 3 |
| Public-test recovery candidates | 1 |
| Public-test recovery rate | 0.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 20196 MB |
| Median average GPU utilization | 91.3% |
| Peak power | 402.9 W |
| Peak temperature | 82.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 1 | 0.0% | 0.0% | 62.8 | 2768.0 |
| AT002 | agent_tool | 1 | 0.0% | 33.3% | 132.5 | 5711.0 |
| BF001 | bug_fix | 1 | 0.0% | 0.0% | 200.2 | 8774.0 |
| BF004 | bug_fix | 1 | 0.0% | 0.0% | 211.7 | 9255.0 |
| CR001 | code_review | 1 | 100.0% | 80.0% | 22.3 | 972.0 |
| CR002 | code_review | 1 | 100.0% | 80.0% | 10.6 | 442.0 |
| LC001 | long_context | 1 | 0.0% | 0.0% | 204.1 | 8930.0 |
| RE001 | repo_engineering | 1 | 0.0% | 0.0% | 360.5 | 15996.0 |
| RE004 | repo_engineering | 1 | 0.0% | 0.0% | 461.5 | 20282.0 |
| RE007 | repo_engineering | 1 | 0.0% | 0.0% | 128.3 | 5449.0 |
| SF001 | single_file | 1 | 0.0% | 0.0% | 326.5 | 14428.0 |
| SF002 | single_file | 1 | 0.0% | 0.0% | 44.0 | 1940.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 4 |
| `patch_failed` | 2 |
| `tool_budget_exhausted` | 6 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
