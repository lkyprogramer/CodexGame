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
| Suite | `core` |
| Context | `112000` |
| Reasoning effort | `medium` |
| MTP | `True` |
| Seeds | `[11, 29, 47]` |

## 2. 数据完整性

| 指标 | 结果 |
|---|---:|
| 运行数 | 96 |
| 唯一题目 | 32 |
| 重复 task/seed | 0 |
| Reasoning Token 覆盖率 | 0.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 100.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 46.9% |
| Partial Test Pass Rate | 55.4% |
| Category Balanced Index | 46.7% |
| Worst Category Index | 6.0% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 53.1% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 61.1% | 64.3% | 61.7% | 119.9 |
| bug_fix | 6 | 18 | 66.7% | 66.7% | 66.7% | 161.4 |
| repo_engineering | 8 | 24 | 41.7% | 54.2% | 44.2% | 125.9 |
| agent_tool | 4 | 12 | 58.3% | 58.3% | 58.3% | 55.5 |
| long_context | 4 | 12 | 41.7% | 50.0% | 43.3% | 87.1 |
| code_review | 4 | 12 | 0.0% | 30.0% | 6.0% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 119.1 s |
| 成功任务耗时 P90 | 239.6 s |
| 成功任务生成 Token 中位数 | 10790.0 |
| Reasoning Token 中位数 | N/A |
| 成功任务/Wall-hour | 10.08 |
| Prompt tok/s 中位数 | 714.1 |
| Decode tok/s 中位数 | 76.7 |
| MTP acceptance | 62.6% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 1760 |
| Invalid tool calls | 78 |
| Valid tool-call rate | 95.6% |
| Tool operation success | 57.4% |
| Public test runs | 28 |
| Public-test recovery candidates | 8 |
| Public-test recovery rate | 62.5% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22730 MB |
| Median average GPU utilization | 86.0% |
| Peak power | 446.1 W |
| Peak temperature | 88.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 100.0% | 100.0% | 49.9 | 3419.0 |
| AT002 | agent_tool | 3 | 100.0% | 100.0% | 55.5 | 4171.0 |
| AT003 | agent_tool | 3 | 33.3% | 33.3% | 212.0 | 14872.0 |
| AT005 | agent_tool | 3 | 0.0% | 0.0% | 116.5 | 10185.0 |
| BF001 | bug_fix | 3 | 66.7% | 66.7% | 33.7 | 2749.0 |
| BF004 | bug_fix | 3 | 100.0% | 100.0% | 60.9 | 5496.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 479.6 | 33572.0 |
| BF006 | bug_fix | 3 | 66.7% | 66.7% | 93.2 | 7118.0 |
| BF008 | bug_fix | 3 | 100.0% | 100.0% | 235.9 | 20060.0 |
| BF009 | bug_fix | 3 | 66.7% | 66.7% | 319.4 | 23937.0 |
| CR001 | code_review | 3 | 0.0% | 20.0% | 69.6 | 4583.0 |
| CR002 | code_review | 3 | 0.0% | 46.7% | 53.8 | 3513.0 |
| CR003 | code_review | 3 | 0.0% | 26.7% | 57.3 | 3615.0 |
| CR004 | code_review | 3 | 0.0% | 26.7% | 61.6 | 4056.0 |
| LC001 | long_context | 3 | 33.3% | 33.3% | 83.0 | 6487.0 |
| LC002 | long_context | 3 | 33.3% | 50.0% | 127.9 | 12341.0 |
| LC003 | long_context | 3 | 66.7% | 66.7% | 87.1 | 7791.0 |
| LC004 | long_context | 3 | 33.3% | 50.0% | 144.1 | 12629.0 |
| RE001 | repo_engineering | 3 | 33.3% | 33.3% | 370.0 | 25587.0 |
| RE002 | repo_engineering | 3 | 66.7% | 66.7% | 171.7 | 13167.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 84.2 | 6675.0 |
| RE004 | repo_engineering | 3 | 33.3% | 77.8% | 83.6 | 7877.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 141.8 | 11999.0 |
| RE006 | repo_engineering | 3 | 33.3% | 66.7% | 132.9 | 11915.0 |
| RE007 | repo_engineering | 3 | 100.0% | 100.0% | 119.1 | 11354.0 |
| RE009 | repo_engineering | 3 | 66.7% | 88.9% | 132.7 | 12215.0 |
| SF001 | single_file | 3 | 33.3% | 33.3% | 129.4 | 11736.0 |
| SF002 | single_file | 3 | 33.3% | 38.9% | 119.9 | 10790.0 |
| SF003 | single_file | 3 | 33.3% | 33.3% | 251.9 | 22125.0 |
| SF006 | single_file | 3 | 66.7% | 80.0% | 36.5 | 2523.0 |
| SF008 | single_file | 3 | 100.0% | 100.0% | 223.3 | 16945.0 |
| SF012 | single_file | 3 | 100.0% | 100.0% | 99.3 | 8919.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 80 |
| `tool_budget_exhausted` | 16 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
