# QCB-4090 模型对比：work-udq4xl-optimized-112k-mtp2 vs v3-udq4xl-200k-q4-mtp2

- 赛道：`optimized`
- Suite：`smoke`
- 完整配对运行数：12

## 总体对比

| 指标 | A | B | B-A |
|---|---:|---:|---:|
| Hard Success | 25.0% | 41.7% | 16.7% |
| Partial Pass | 28.3% | 45.0% | 16.7% |
| Balanced Index | 25.7% | 42.3% | 16.7% |
| Worst Category | 0.0% | 0.0% | 0.0% |
| Invalid Output | 0.0% | 0.0% | 0.0% |
| 成功耗时中位数(s) | 30.1 | 81.7 | 51.6 |
| 成功生成 Token 中位数 | 2273.0 | 6058.0 | 3785.0 |

## 六类差异

| 分类 | A Index | B Index | B-A |
|---|---:|---:|---:|
| single_file | 50.0% | 100.0% | 50.0% |
| bug_fix | 50.0% | 50.0% | 0.0% |
| repo_engineering | 0.0% | 0.0% | 0.0% |
| agent_tool | 50.0% | 100.0% | 50.0% |
| long_context | 0.0% | 0.0% | 0.0% |
| code_review | 4.0% | 4.0% | 0.0% |

## 配对统计

- Hard Success 分层配对 Bootstrap 差值：16.7%
- Hard Success 95% CI：[-8.3%, 41.7%]
- P(B>A)：80.0%
- Partial Score 差值：16.7%，95% CI [-8.3%, 41.7%]
- McNemar：A-only=1，B-only=3，双侧精确 p=0.6250

## 预声明决策门槛

| 检查 | 通过 |
|---|:---:|
| Hard Success 95% CI 下界 ≥ -3pp | 否 |
| Worst Category 回退 ≤ 8pp | 是 |
| Invalid Output ≤ 8% 且相对 A 增幅 ≤ 3pp | 是 |
| CBI 提升 ≥ 2pp | 是 |
| 可声明 practical win | 否 |

## 解释限制

该判断只适用于当前基准版本、Lane、Suite、Seed、GGUF 与运行配置。统计显著性不能替代实际意义；效率提升也不能抵消质量门槛失败。
