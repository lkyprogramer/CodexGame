# work-udq4xl-optimized-112k-mtp2 — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `work-udq4xl-optimized-112k-mtp2` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `UD-Q4_K_XL` |
| Template | `official-jinja-medium` |
| 模型 SHA-256 | `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` |
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
| Hard Task Success Rate | 25.0% |
| Partial Test Pass Rate | 28.3% |
| Category Balanced Index | 25.7% |
| Worst Category Index | 0.0% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 0.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 2 | 50.0% | 50.0% | 50.0% | 80.6 |
| bug_fix | 2 | 2 | 50.0% | 50.0% | 50.0% | 30.1 |
| repo_engineering | 3 | 3 | 0.0% | 0.0% | 0.0% | N/A |
| agent_tool | 2 | 2 | 50.0% | 50.0% | 50.0% | 23.4 |
| long_context | 1 | 1 | 0.0% | 0.0% | 0.0% | N/A |
| code_review | 2 | 2 | 0.0% | 20.0% | 4.0% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 30.1 s |
| 成功任务耗时 P90 | 70.5 s |
| 成功任务生成 Token 中位数 | 2273.0 |
| Reasoning Token 中位数 | N/A |
| 成功任务/Wall-hour | 5.21 |
| Prompt tok/s 中位数 | 625.0 |
| Decode tok/s 中位数 | 78.3 |
| MTP acceptance | 59.4% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 213 |
| Invalid tool calls | 7 |
| Valid tool-call rate | 96.7% |
| Tool operation success | 50.5% |
| Public test runs | 1 |
| Public-test recovery candidates | 0 |
| Public-test recovery rate | N/A |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22730 MB |
| Median average GPU utilization | 85.4% |
| Peak power | 437.1 W |
| Peak temperature | 85.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 1 | 0.0% | 0.0% | 179.1 | 11938.0 |
| AT002 | agent_tool | 1 | 100.0% | 100.0% | 23.4 | 1623.0 |
| BF001 | bug_fix | 1 | 0.0% | 0.0% | 47.2 | 3886.0 |
| BF004 | bug_fix | 1 | 100.0% | 100.0% | 30.1 | 2273.0 |
| CR001 | code_review | 1 | 0.0% | 0.0% | 58.5 | 3806.0 |
| CR002 | code_review | 1 | 0.0% | 40.0% | 34.7 | 2415.0 |
| LC001 | long_context | 1 | 0.0% | 0.0% | 97.5 | 8535.0 |
| RE001 | repo_engineering | 1 | 0.0% | 0.0% | 466.8 | 31815.0 |
| RE004 | repo_engineering | 1 | 0.0% | 0.0% | 95.6 | 7885.0 |
| RE007 | repo_engineering | 1 | 0.0% | 0.0% | 108.7 | 9786.0 |
| SF001 | single_file | 1 | 100.0% | 100.0% | 80.6 | 7439.0 |
| SF002 | single_file | 1 | 0.0% | 0.0% | 850.4 | 54991.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 9 |
| `tool_budget_exhausted` | 3 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
