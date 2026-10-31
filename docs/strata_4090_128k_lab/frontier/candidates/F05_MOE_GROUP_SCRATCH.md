# F05 · 保留全Dm的MoE中间行窗复用

**状态：HYPOTHESIS_UNQUALIFIED；当前硬件资格：无；数值意图：E0。**

作用域：prefill/长append；不是当前warm decode即时候选。旧项映射：O15/GROUP_SCRATCH；HC失败不覆盖它，也不为它提供资格。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

Maya GLM有真实row-window实现，P6非fused GU/H/Xq/Hq仍按T×K分配。保守派生仅复用这些中间张量，保留全Dm及Qwen原K10 combine；不能照搬GLM窗口部分和。它是O15的更具体实现路径，不是自动恢复旧优先级。

## 2. 来源与现有入口

- [Maya窗口布局](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)
- [P6 prefill](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/prefill.cpp)
- [Maya combine](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/kernels/cuda/glm_batch.cu)

src/prefill/prefill.cpp::moe_bufs/moe_set_bytes/Prefill::carve/Prefill::run_impl 与include/strata/prefill/moe_mmq.hpp；拟增加GroupScratchPlan{capacity_rows,byte_offsets,epoch}及窄trace，不动HC区域。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

离线按实际dtype/T分配公式证明MoE是max(GDN,QSA,MoE)最大项，且能消除真实borrow/refill或allocation压力。若AUTOMAX16384或热边界才是约束，不加chunk。当前仅warm诊断若没出现相关prefill证据，则另行延期。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

构建基于原expert group计划的live-range表，在消费者完成的group边界复用GU/H/Xq/Hq；Dm仍有T×K行，每行N个FP32元素。保留原MMQ调用shape与row顺序；若必须拆调用导致stream-K/规约变化则退出E0，而不是放宽parity。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

true router、CPU/GPU归属、stable row/scatter、原MMQ量化/规约和最终k0…9 combine不变。不能复用仍被量化/down/另一stream读的区间；natural loan/residency变化另验，不能用固定dispatch掩盖。

## 6. 最小验证与阶段验证

最小：interval-live重叠负例、短尾/一个超大expert组、off布局一致、Dm写入唯一；actual4096/16384块raw parity。阶段门短→长→短/取消/loan还回及memcheck。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

T16384/K10/N2560的FP32 Dm单项1.5625GiB是尺寸算术，非节省量。释放空间不等于请求加速；必须量完整TTFT/wall/decode。

**停止条件：**MoE不是union主项；full Dm下限抵消空间；只能改变reduce/shape实现；少borrow未减少暴露成本；冷读更热；复现HC式decode回退。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
