# F04 · QSA长索引与精确选择的条件分支

**状态：DEFERRED_NEW_EVIDENCE；当前硬件资格：无；数值意图：E0。**

作用域：长warm decode的indexer/selection，不是dense128K attention。旧项映射：O20/O24/O27/O29；SELECT_LONG尚未取得资格。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

长context增长可能主要在score/index/top-k而非最多2051cells的attention。旧SELECT_LONG“未编入”不是新证据；现成SELECT_LONG/DX受SM60构建门保护，4090不能直接开。本卡仅为当前真实长索引暴露成本显著改变后，设计SM89且保持原score/tie顺序的选择算法。

## 2. 来源与现有入口

- [QSA选择](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_select.cu)
- [QSA定义](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/include/strata/kernels/qsa.hpp)

src/kernels/cuda/qsa_select.cu与include/strata/kernels/qsa.hpp；不改attention budget、qsa_selection_width或KV量化。新增实验函数exact_select_sm89及明确dispatch，原算法保留。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

分开测score、top-k、KV resolve与attention；旧合同转引646ms/3.07%不能当当前严格上界，更不能用全部QSA时间。当前删光可省<4%或依赖不明直接停。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

先定义原score位模式、相等值tie顺序、NaN处理、causal mask；再考虑块内有序候选/两阶段精确merge，只在不会漏掉最终top-k的容量证明成立时实现。不能用近似阈值/少候选“通常够用”。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

每query输出canonical selected IDs和顺序完全一致；相同score量化/舍入、不改变recent tail；所有有效上下文和窗口长度均成立。数学上选同集合但顺序不同不够。

## 6. 最小验证与阶段验证

最小：全相等、边界同分、最后页mask、maxcontext附近、top-k临界分数与随机固定输入逐项对照；错误tie负例必须失败。阶段门state/logits逐字节和完整warm请求。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

只能以当前score+selection因果暴露比例算上界，绝不能以全部128K attention FLOPs估算。

**停止条件：**旧份额仍低、仅改kernel名/新表、需要近似筛选、SM60路径无法在保持数值下适配、scratch或launch增量吃掉节省。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
