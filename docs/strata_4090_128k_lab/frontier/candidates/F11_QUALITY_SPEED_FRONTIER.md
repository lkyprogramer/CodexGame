# F11 · 改变目标计算的质量—速度前沿

**状态：OUT_OF_MAINLINE；当前硬件资格：无；数值意图：Q。**

作用域：独立产品/模型实验，当前不进入主线。旧项映射：O46/O47/O48/O52–O57/O58。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

更低比特KV、专家裁剪/更深tail-skip、预测路由替换true router、减少attention预算、提前截thinking都能减少工作，但改变目标行为。现用基线已有哪些近似要冻结记录；“当前已有近似”不授权继续加深。

## 2. 来源与现有入口

- [KV量化格式](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/include/strata/kernels/kv_q4.hpp)
- [Edge0预测路由](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/python/src/edge0/prerouter/install.py)
- [Edge0 staged miss](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/python/src/edge0/streaming/layer.py)

不改主线。若未来明确立项，另建MODEL_VARIANT_ID/独立权重与评测manifest；与本包E0结果不同namespace，禁止合并指标。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

必须单独明确接受怎样的质量—速度取舍、目标分布和绝对质量。当前六项长检索失败与正式NI未建立，使该路线保持延期。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

先建立失败诊断与可运行的更高精度/原始模型对照是否可行，资源不够就停止；再按独立任务评估Pareto，不为了快只选简单题。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

不能宣称lossless；记录目标算子/选中专家/cells/表示/输出预算变化、能力损失与回滚。

## 6. 最小验证与阶段验证

最小方案审查；未来完整质量矩阵包括原长检索、代码/工具/恢复和难题，必须真实独立任务。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

可能更大，但本包没有证据给倍率；不能与exact路径收益相加。

**停止条件：**用户未接受质量换速度；只在删失败/换prompt/减少输出后通过；绝对质量不能建立；资源不可容纳对照。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
