# F08 · 按row成本和未完成复制债务决定CPU/GPU归属

**状态：DEFERRED_QUALITY；当前硬件资格：无；数值意图：E1。**

作用域：prefill/特定expert miss分派；质量前提阻塞。旧项映射：O07/O08；不同于已拒绝固定share，但不得复活NP3分行。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

Maya把每expert rows成本与尚未完成prestage H2D债务一起比较。A0/P6已有row排序、measured share；新增变量是绝对未完成复制债务，不是再扫描pcie-frac。改变CPU/GPU归属会改变数值，不能称E0调度。

## 2. 来源与现有入口

- [Maya成本选择](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)
- [P6已有分派](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/prefill.cpp)

src/prefill/prefill.cpp CPU选择loop与实际CPU pool/copy计时接口；拟独立PlacementDecision choose_placement(costs,remaining_copy_debt,budget)，不得把GLM路由/维度带入。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

先满足质量前提，再证明动态债务变量在当前负载可预测真实join且旧控制不覆盖。只离线replay成本预测，不先写live scheduler。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

离线与oracle最优小实例比较预测误差；实际实现保持明确回退和保守误差带，采用决定前计入profile/决策开销。固定归属对照与自然分派分开，不用前者冒充性能。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

数学意图同expert集合，但CPU/GPU舍入不同→E1；需记录每expert归属与后续完整状态偏差。不得通过减少expert/保留旧计算结果近似。

## 6. 最小验证与阶段验证

最小：零债务、copy已完成、偏斜rows、模型误差、fallback确定性；阶段门长链质量/数值与真实ms/committedtoken。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

可能减少max分支尾部，不从两边成本相加估收益。当前无本机收益数字。

**停止条件：**质量前提未满足、仅固定分担新名字、预测不可靠、decision成本大于节省、DDR与PCIe争用让成本模型失效。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
