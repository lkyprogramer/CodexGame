# 06 · 多模型对比与决策

## 分层决策

1. **正确性层：** Hard Success、CBI、Worst Category、Invalid Output；
2. **工程层：** repo/agent/long-context 子集和工具恢复；
3. **效率层：** 成功任务时间、Token、VRAM、功耗；
4. **稳定性层：** Seed 方差、崩溃、格式错误、长任务退化；
5. **部署层：** 24GB 余量、最大可用 context、服务兼容性。

## 不同实验的正确结论

- Original vs Grug 同 Q4/template：主要归因于 finetune；
- Original official vs Original Sharp：归因于 template/reasoning 行为；
- Original Q4 vs Pearson IQ4：归因于 quant/imatrix，不是新模型智力；
- Cold Fusion optimized+MTP vs Original normalized：只能比较最终系统，不能证明权重单独更强。

## 推荐分类

最终不要只给 1–N 总排名，还应给：

- 最高质量；
- 最佳 Coding Agent；
- 最佳成功任务/小时；
- 最佳 64K+ 检索部署；
- 最稳定；
- 最佳 template-only 提升；
- 不推荐及原因。

## 胜出规则

“B 优于 A”至少满足预声明 practical-win 门槛：

- 六类等权配对 Hard 差值的 95% CI 下界不低于 -3pp；
- CBI 至少提升 2pp，或在报告中预先声明另一实际意义阈值；
- 最差类别无不可接受回退；
- 效率提升不是由早失败造成；
- 结论在私有回放集方向一致。


多模型 Pairwise McNemar p 值必须使用 Holm 修正；缺失或重复 `(task, seed)` 的模型不进入正式配对结论。
