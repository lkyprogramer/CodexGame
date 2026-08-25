# QCB-4090 模型对比：v3-udq4xl-200k-q4-mtp2 vs v3-udq4xl-200k-q4-dflash2-q2

- 赛道：`optimized`
- Suite：`smoke`
- 完整配对运行数：12

## 总体对比

| 指标 | A | B | B-A |
|---|---:|---:|---:|
| Hard Success | 41.7% | 50.0% | 8.3% |
| Partial Pass | 45.0% | 65.3% | 20.3% |
| Balanced Index | 42.3% | 61.2% | 18.9% |
| Worst Category | 0.0% | 2.2% | 2.2% |
| Invalid Output | 0.0% | 0.0% | 0.0% |
| 成功耗时中位数(s) | 81.7 | 150.9 | 69.2 |
| 成功生成 Token 中位数 | 6058.0 | 6709.5 | 651.5 |

## 六类差异

| 分类 | A Index | B Index | B-A |
|---|---:|---:|---:|
| single_file | 100.0% | 55.0% | -45.0% |
| bug_fix | 50.0% | 100.0% | 50.0% |
| repo_engineering | 0.0% | 2.2% | 2.2% |
| agent_tool | 100.0% | 100.0% | 0.0% |
| long_context | 0.0% | 100.0% | 100.0% |
| code_review | 4.0% | 10.0% | 6.0% |

## 配对统计

- Hard Success 分层配对 Bootstrap 差值：16.7%
- Hard Success 95% CI：[0.0%, 33.3%]
- P(B>A)：94.0%
- Partial Score 差值：27.7%，95% CI [15.0%, 40.2%]
- McNemar：A-only=1，B-only=2，双侧精确 p=1.0000

## 预声明决策门槛

| 检查 | 通过 |
|---|:---:|
| Hard Success 95% CI 下界 ≥ -3pp | 是 |
| Worst Category 回退 ≤ 8pp | 是 |
| Invalid Output ≤ 8% 且相对 A 增幅 ≤ 3pp | 是 |
| CBI 提升 ≥ 2pp | 是 |
| 可声明 practical win | 是 |

## 解释限制

该判断只适用于当前基准版本、Lane、Suite、Seed、GGUF 与运行配置。统计显著性不能替代实际意义；效率提升也不能抵消质量门槛失败。
