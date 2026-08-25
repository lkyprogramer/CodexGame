# coldfusion-v1.1-q4km-mtp-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `coldfusion-v1.1-q4km-mtp-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M-MTP` |
| Template | `coldfusion-native-medium-override` |
| 模型 SHA-256 | `db466a9432a52b87a7b7560f432f0e1caafeb111dbe3d168acf74dfe143a637c` |
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
| Hard Task Success Rate | 47.9% |
| Partial Test Pass Rate | 57.3% |
| Category Balanced Index | 51.0% |
| Worst Category Index | 23.7% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 53.1% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 72.2% | 78.2% | 73.4% | 134.7 |
| bug_fix | 6 | 18 | 50.0% | 64.8% | 53.0% | 207.5 |
| repo_engineering | 8 | 24 | 29.2% | 30.6% | 29.4% | 89.7 |
| agent_tool | 4 | 12 | 75.0% | 75.0% | 75.0% | 128.1 |
| long_context | 4 | 12 | 50.0% | 56.2% | 51.3% | 77.8 |
| code_review | 4 | 12 | 16.7% | 51.7% | 23.7% | 71.7 |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 113.0 s |
| 成功任务耗时 P90 | 322.4 s |
| 成功任务 end-to-end completion token 中位数 | 8424.5 |
| 失败任务 end-to-end completion token 中位数 | 5349.0 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 18805.5 |
| 失败任务 thinking chars 中位数 | 12205.5 |
| 全部任务 thinking chars 中位数 | 16866.0 |
| 可见回答 chars 中位数 | 2356.0 |
| 成功任务/Wall-hour | 10.75 |
| Prompt tok/s 中位数 | 714.8 |
| Decode tok/s 中位数 | 68.4 |
| MTP acceptance | 62.2% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 1757 |
| Invalid tool calls | 83 |
| Valid tool-call rate | 95.3% |
| Tool operation success | 63.4% |
| Public test runs | 27 |
| Public-test recovery candidates | 9 |
| Public-test recovery rate | 88.9% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 23290 MB |
| Median average GPU utilization | 87.5% |
| Peak power | 444.2 W |
| Peak temperature | 90.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 66.7% | 66.7% | 41.7 | 2718.0 |
| AT002 | agent_tool | 3 | 100.0% | 100.0% | 35.3 | 2303.0 |
| AT003 | agent_tool | 3 | 100.0% | 100.0% | 157.9 | 11059.0 |
| AT005 | agent_tool | 3 | 33.3% | 33.3% | 269.1 | 19281.0 |
| BF001 | bug_fix | 3 | 66.7% | 66.7% | 61.6 | 4787.0 |
| BF004 | bug_fix | 3 | 33.3% | 73.3% | 47.9 | 3280.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 125.7 | 8804.0 |
| BF006 | bug_fix | 3 | 66.7% | 93.3% | 225.3 | 14883.0 |
| BF008 | bug_fix | 3 | 66.7% | 88.9% | 104.2 | 7578.0 |
| BF009 | bug_fix | 3 | 66.7% | 66.7% | 220.9 | 17245.0 |
| CR001 | code_review | 3 | 0.0% | 46.7% | 51.9 | 2988.0 |
| CR002 | code_review | 3 | 0.0% | 60.0% | 42.7 | 2477.0 |
| CR003 | code_review | 3 | 33.3% | 40.0% | 55.8 | 3140.0 |
| CR004 | code_review | 3 | 33.3% | 60.0% | 60.5 | 3466.0 |
| LC001 | long_context | 3 | 33.3% | 33.3% | 217.9 | 15428.0 |
| LC002 | long_context | 3 | 100.0% | 100.0% | 87.8 | 5531.0 |
| LC003 | long_context | 3 | 0.0% | 0.0% | 55.9 | 4472.0 |
| LC004 | long_context | 3 | 66.7% | 91.7% | 53.6 | 3963.0 |
| RE001 | repo_engineering | 3 | 33.3% | 33.3% | 286.1 | 20475.0 |
| RE002 | repo_engineering | 3 | 0.0% | 0.0% | 39.7 | 2447.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 28.5 | 1933.0 |
| RE004 | repo_engineering | 3 | 0.0% | 0.0% | 90.6 | 7118.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 129.6 | 9081.0 |
| RE006 | repo_engineering | 3 | 66.7% | 77.8% | 73.7 | 4948.0 |
| RE007 | repo_engineering | 3 | 33.3% | 33.3% | 255.3 | 17777.0 |
| RE009 | repo_engineering | 3 | 100.0% | 100.0% | 89.7 | 5512.0 |
| SF001 | single_file | 3 | 100.0% | 100.0% | 113.3 | 8853.0 |
| SF002 | single_file | 3 | 33.3% | 44.4% | 129.9 | 9165.0 |
| SF003 | single_file | 3 | 33.3% | 33.3% | 355.8 | 30005.0 |
| SF006 | single_file | 3 | 100.0% | 100.0% | 69.0 | 4781.0 |
| SF008 | single_file | 3 | 100.0% | 100.0% | 134.7 | 8205.0 |
| SF012 | single_file | 3 | 66.7% | 91.7% | 104.1 | 7434.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 79 |
| `tool_budget_exhausted` | 17 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
