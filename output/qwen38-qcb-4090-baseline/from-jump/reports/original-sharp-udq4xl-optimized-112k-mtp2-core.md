# original-sharp-udq4xl-optimized-112k-mtp2 — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `original-sharp-udq4xl-optimized-112k-mtp2` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `UD-Q4_K_XL` |
| Template | `sharp-v22.1-terse-medium` |
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
| API reasoning_tokens 覆盖率 | 0.0% |
| thinking chars 覆盖率 | 100.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 100.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 46.9% |
| Partial Test Pass Rate | 55.4% |
| Category Balanced Index | 49.8% |
| Worst Category Index | 7.3% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 50.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 66.7% | 72.2% | 67.8% | 90.9 |
| bug_fix | 6 | 18 | 50.0% | 50.0% | 50.0% | 106.4 |
| repo_engineering | 8 | 24 | 29.2% | 37.5% | 30.8% | 201.2 |
| agent_tool | 4 | 12 | 91.7% | 91.7% | 91.7% | 151.0 |
| long_context | 4 | 12 | 50.0% | 56.2% | 51.3% | 98.2 |
| code_review | 4 | 12 | 0.0% | 36.7% | 7.3% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 129.8 s |
| 成功任务耗时 P90 | 350.8 s |
| 成功任务 end-to-end completion token 中位数 | 10057.0 |
| 失败任务 end-to-end completion token 中位数 | 8818.0 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 24997.0 |
| 失败任务 thinking chars 中位数 | 20148.0 |
| 全部任务 thinking chars 中位数 | 23415.0 |
| 可见回答 chars 中位数 | 2541.5 |
| 成功任务/Wall-hour | 8.87 |
| Prompt tok/s 中位数 | 846.3 |
| Decode tok/s 中位数 | 74.9 |
| MTP acceptance | 60.9% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 1624 |
| Invalid tool calls | 72 |
| Valid tool-call rate | 95.6% |
| Tool operation success | 57.0% |
| Public test runs | 25 |
| Public-test recovery candidates | 10 |
| Public-test recovery rate | 80.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22730 MB |
| Median average GPU utilization | 86.4% |
| Peak power | 447.5 W |
| Peak temperature | 90.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 100.0% | 100.0% | 61.7 | 4446.0 |
| AT002 | agent_tool | 3 | 100.0% | 100.0% | 151.0 | 10900.0 |
| AT003 | agent_tool | 3 | 100.0% | 100.0% | 223.8 | 15771.0 |
| AT005 | agent_tool | 3 | 66.7% | 66.7% | 226.4 | 15744.0 |
| BF001 | bug_fix | 3 | 0.0% | 0.0% | 136.7 | 10774.0 |
| BF004 | bug_fix | 3 | 100.0% | 100.0% | 106.4 | 9418.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 132.0 | 11339.0 |
| BF006 | bug_fix | 3 | 66.7% | 66.7% | 60.7 | 4366.0 |
| BF008 | bug_fix | 3 | 100.0% | 100.0% | 607.0 | 40802.0 |
| BF009 | bug_fix | 3 | 33.3% | 33.3% | 83.2 | 7052.0 |
| CR001 | code_review | 3 | 0.0% | 40.0% | 41.9 | 2688.0 |
| CR002 | code_review | 3 | 0.0% | 40.0% | 55.9 | 3725.0 |
| CR003 | code_review | 3 | 0.0% | 33.3% | 48.3 | 3212.0 |
| CR004 | code_review | 3 | 0.0% | 33.3% | 65.8 | 4298.0 |
| LC001 | long_context | 3 | 66.7% | 66.7% | 146.8 | 11600.0 |
| LC002 | long_context | 3 | 33.3% | 33.3% | 177.9 | 14675.0 |
| LC003 | long_context | 3 | 66.7% | 66.7% | 58.4 | 5279.0 |
| LC004 | long_context | 3 | 33.3% | 58.3% | 54.6 | 4033.0 |
| RE001 | repo_engineering | 3 | 33.3% | 33.3% | 493.8 | 31105.0 |
| RE002 | repo_engineering | 3 | 33.3% | 33.3% | 70.6 | 6100.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 25.7 | 1879.0 |
| RE004 | repo_engineering | 3 | 66.7% | 88.9% | 141.6 | 10057.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 300.1 | 18507.0 |
| RE006 | repo_engineering | 3 | 66.7% | 66.7% | 201.2 | 14655.0 |
| RE007 | repo_engineering | 3 | 0.0% | 0.0% | 244.7 | 23037.0 |
| RE009 | repo_engineering | 3 | 33.3% | 77.8% | 743.6 | 45927.0 |
| SF001 | single_file | 3 | 66.7% | 66.7% | 153.7 | 12990.0 |
| SF002 | single_file | 3 | 66.7% | 83.3% | 122.1 | 8410.0 |
| SF003 | single_file | 3 | 33.3% | 33.3% | 293.1 | 29086.0 |
| SF006 | single_file | 3 | 100.0% | 100.0% | 42.8 | 3011.0 |
| SF008 | single_file | 3 | 100.0% | 100.0% | 237.5 | 18151.0 |
| SF012 | single_file | 3 | 33.3% | 50.0% | 93.8 | 7620.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 85 |
| `tool_budget_exhausted` | 11 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
