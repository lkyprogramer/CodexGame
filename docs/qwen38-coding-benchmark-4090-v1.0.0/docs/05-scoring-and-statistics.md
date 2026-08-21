# 05 · 评分、效率与统计

## 1. 单任务评分

```text
h_t = 1  当隐藏验证全部通过，否则 0
s_t = passed_tests / total_tests
```

代码审查题的 `s_t` 是隐藏 Rubric 的高信号问题召回率；只有达到阈值且所有 required issue 命中，`h_t` 才为 1。

## 2. 六类平衡指数

对每类：

```text
CI_c = 0.8 × mean(h_t) + 0.2 × mean(s_t)
```

总体：

```text
CBI = mean(CI_c across available six categories)
Worst = min(CI_c)
```

正式 Suite 都覆盖六类。六类等权，避免 12 道单文件题压过 4 道代码审查题。Hard、Partial、CBI、Worst 必须同时报告。

## 3. 输出和基础设施错误

分开统计：

- `Invalid Output Rate`：无有效 diff/JSON、patch 无法应用；
- `Infrastructure Error Rate`：endpoint 连接、服务崩溃等；
- `Tool Budget Exhausted`：模型行为失败，不属于基础设施；
- 隐藏验证失败：普通能力失败。

不得把 infrastructure error 隐藏在模型失败中，也不得把模型格式错误改写成服务故障。

## 4. Agent 工具指标

- `Invalid tool call`：未知工具、非法 JSON/参数、路径越界、调用无公开测试的 `run_tests`；
- `Failed tool operation`：调用格式有效，但 patch 不能应用、公开测试返回非零等；
- `Valid tool-call rate = (calls - invalid) / calls`；
- `Tool operation success = (valid - failed operations) / valid`；
- `Public-test recovery`：首次/中间公开测试失败，后续公开测试最终通过。

公开测试失败是正常调试信号，不计为 invalid call。

## 5. 效率指标

只在质量门槛通过后比较：

- 成功任务 wall time P50/P90；
- 成功任务 completion token P50；
- reasoning token P50 与覆盖率；
- 成功任务/Wall-hour；
- prompt/decode tok/s（后端暴露时）；
- Peak VRAM、GPU 利用率、功耗、温度；
- MTP drafted/accepted token 和 acceptance（后端暴露时）。

失败任务的“快速失败”不算效率优势。TTFT 需要 streaming 或 server telemetry；当前非流式 Runner 不伪造该值。

## 6. Seed 稳定性

报告：

- 每题跨 Seed pass rate；
- `unstable_task_rate`：同一题在 Seeds 间既有通过又有失败；
- 平均 Bernoulli seed 标准差；
- 代表性分裂题和轨迹。

高一致性可能来自“始终失败”，所以稳定性不能脱离成功率解释。

## 7. 配对统计

最小配对键：

```text
(task_id, seed)
```

两模型正式比较要求键集合完全相同且无重复。使用：

- 按六类等权的 paired bootstrap，默认 10,000 次；
- Hard pass 的 McNemar 双侧精确检验；
- Partial score 的配对 Bootstrap；
- 多模型 Pairwise p 值的 Holm 修正；
- 效应量、95% CI 与方向概率。

Bootstrap 的观测效应与重采样都按类别等权，不能一边等权抽样、一边用题目数加权平均。

## 8. 预声明质量门槛

默认部署榜资格：

1. Hard Success 相对最高模型不低于 3 个百分点；
2. Worst Category 相对最高模型不低于 8 个百分点；
3. Invalid Output 不高于 8%，且不比最佳高 3 个百分点以上；
4. 完整 task/seed 配对，无重复样本；
5. 至少 3 Seeds；
6. 安全审查和路径安全题没有系统性回退。

两模型 `practical win` 还要求 CBI 至少提升 2 个百分点。阈值可以在实验前调整，但看见结果后不能改。

## 9. 可解释的结论

推荐措辞：

> 在 QCB-4090 v1.0.0、Normalized/Q4_K_M/32K、3 Seeds 下，B 对 A 的六类等权 Hard 差值为 X，95% CI 为 [...]；CBI 提升 Y，Worst 回退 Z，Invalid 变化 W。B 通过/未通过预声明质量门槛，因此……

不能仅凭 p 值、tok/s 或单项平均分宣布胜出。
