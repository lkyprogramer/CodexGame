# 离线配对质量非劣性门

`quality_gate.py`只使用Python标准库，不调用模型、服务、GPU、包管理器或网络。它检查**预登记的独立任务成功率非劣性**，不判断总体发布资格，也不替代绝对质量、工具安全、性能或稳定性门。

```bash
python -B tools/quality_gate.py --input tools/examples/quality-smoke-30.json \
  --output /tmp/quality-report.json
```

示例是合成的格式/数值回归夹具，**不是模型实测结果**。30对全部成功的示例会退出1，因为不能建立默认2%非劣性。`quality-zero-loss-184.json`只演示该公式在更大独立样本量下的结果。

## 输入

```json
{
  "schema_version": 1,
  "preregistration": {
    "task_ids": ["task-a", "task-b"],
    "margin": 0.02,
    "unit": "independent_task",
    "aggregation": "one_pair_per_task"
  },
  "pairs": [
    {"task_id":"task-a","baseline_success":true,"candidate_success":true,"run_valid":true,"failure_kind":"none"},
    {"task_id":"task-b","baseline_success":true,"candidate_success":false,"run_valid":true,"failure_kind":"model_oracle"}
  ]
}
```

`margin`缺省0.02，必须在看结果前冻结；没有事后CLI改margin的参数。每行只接受上述五个字段，三个布尔值必须是真正JSON boolean，不能用0/1。重复键、NaN/Infinity及数值溢出会被拒绝。

同一task的多seed、多个turn、多个kernel不是新的独立样本。必须先按预登记规则把同一task每个arm的结果聚合成一个binary outcome，再输入一行。重复task_id和带raw seed字段的行会被拒绝；改造task_id无法证明独立性，工具只核查形式，不能证明事前登记、抽样独立或分布代表性。

| failure_kind | 处理 |
|---|---|
| `none` | 两臂均成功；若某臂false则输入不一致 |
| `model_oracle` | 有效模型/断言失败，保留在四格与N中 |
| `task_budget_exhausted` | 有效任务失败，保留；与基础设施超时不同 |
| `infrastructure` | 整实验失去资格，不对幸存样本给NI结论 |
| `infrastructure_timeout` | 同上 |
| `oom` / `crash` | 硬拒绝 |

任何 `run_valid:false`、缺任务、额外任务或重复任务都阻止资格成立。`model_oracle/task_budget_exhausted`必须至少有一个arm失败。当前未实现restricted-time gate，不能用此工具声称“失败计入预算B后的时间收益”。

## 计算

完整四格为：两者成功a、仅baseline成功b、仅candidate成功c、两者失败d，`n=a+b+c+d`。a/d也在分母中，模型断言失败不会被丢弃。

定义损害概率差：`p_harm = P(b) - P(c)`。工具计算：

```text
U_harm = upperCP(b,n,alpha=.025) - lowerCP(c,n,alpha=.025)
```

两条单侧Clopper–Pearson界各至少97.5%覆盖，Bonferroni给联合覆盖至少95%；不要求b、c两条边界事件互相独立。满足 `U_harm <= margin` 才建立相对非劣性。二项置信保证需要任务对来自预登记目标分布、可按独立同分布任务对解释；重复、相关、适应性挑选或非代表性任务不能因输入ID不同就满足这些假设。

CDF按较小尾部相对最大项求和，使用log质量和`expm1`减少下溢/消减；CP通过单调二分反解，不依赖SciPy。边界 `upperCP(0,n)=1-.025^(1/n)`、`lowerCP(0,n)=0` 使用稳定闭式。数值采用双精度，不是形式化区间算术证明。

默认2% margin、b=c=0时：n30不能NI；n182不能NI；n183已达到门槛，n184也达到。**184不是最小N，也不是通用样本量建议**：有discordance、其它margin、任务相关或质量目标变化时需要重新设计。30题smoke不能提升为正式质量证明。

两臂都失败的184对也可能相对NI，因为工具只问“是否比baseline差超过margin”。输出始终包含绝对成功率、`absolute_quality_gate=NOT_EVALUATED`和`deployment_approved=false`，避免把“同样差”解释成质量合格。

## 输出与退出码

输出包含完整有效四格、包含无效行的原始四格、全部无效原因、failure_kind计数、b/c/n、CP边界、`U_harm`以及输入/计划hash。任何资格错误时`inference=null`，不会用部分有效样本挽救结论。

| 退出码 | status | 含义 |
|---:|---|---|
| 0 | `NONINFERIORITY_ESTABLISHED` | 只通过本相对binary质量门 |
| 1 | `NONINFERIORITY_NOT_ESTABLISHED` | 数据有效，但证据不足以建立所选margin下的NI |
| 2 | `INVALID_EXPERIMENT` / `INVALID_INPUT` | 完整性、独立单位声明、类型、基础设施或输入错误 |
| 3 | `HARD_REJECT` | OOM或crash |

本工具独立于 `lab.statistics` 的速度筛选。不能将速度筛选的bootstrap CI当成本工具的质量界，也不能把质量退出0当作性能、生产部署或安全批准。
