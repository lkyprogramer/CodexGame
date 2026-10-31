# F06 · 非fused路径的稳定整数count/rank/scatter

**状态：HYPOTHESIS_UNQUALIFIED；当前硬件资格：无；数值意图：E0。**

作用域：prefill CPU metadata，先查P6 mapped基线。旧项映射：O12/O17/O25；不把已有fused::group算新功能。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

Maya每expert生成稳定(token,k) rank/count，host读E个counts再生成bounds，GPU scatter。P6已默认mapped pinned group tables，STRATA_GROUP_COPY=1可强制复制对照；mapped分配/映射失败或force_pageable()也会回退copies，必须核实际grp_mapped；本卡不能宣称“首次删除普通D2H/H2D”。只比较实际mapped基线的host histogram/scatter与新完整整数流程。

## 2. 来源与现有入口

- [Maya count/scatter](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/kernels/cuda/glm_batch.cu)
- [Maya host计划](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)
- [P6分组](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/prefill.cpp)

src/prefill/prefill.cpp host histogram/scatter段；新增 src/prefill/frontier_group.cu 和 include/strata/prefill/frontier_group.hpp，接口分为 count_rank(ids,T,K,E,counts,rank,stream) 和 scatter(ids,rank,base,n,K,row_tok,pos,stream)，其中n=T×K且已验证维度。前者完成后host读取counts，验证sum(counts)==T×K，按原placement/group-order/CPUshare/resident-sort形成base/off/bounds并发布，再调用后者。不得替换route_kernel。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

必须确认非fused路径、host分组真正暴露、不是被shared expert/H2D覆盖。Maya示例O(E×T×K)扫描在E512/T16384/K10约8388万entry检查，不能以回传bytes更少推断更快。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

先从冻结ids生成稳定rank与counts，再保留host规划和原CPUshare选择，scatter输出原slot/src顺序。CPU仍需token-row列表，明确实际发布/传输方式，不通过丢列表换速度。host读取mapped counts/row列表前，GPU写入必须完成；下一层复用mapped slot/src/bounds前，上一层消费者必须结束。mapped不消除同步或所有权边界。只对一种已证明热点分支开启，fused分支原样。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

counts求和TK；每expert组内(token,k)稳定；row_tok/pos/slot/src逐项相同；CPU/GPU归属、MMQ调用、combine完全相同。GLM sigmoid+bias、K≤8数组不能移入K10 Qwen。

## 6. 最小验证与阶段验证

最小：所有路由同expert/均匀/偏斜/重复、TK尾和空expert，逐项对照CPU参考；无越界/重复写，wrong K负例。阶段门实际raw/state与长append完整流程。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

比较GPUcount+hostcounts/plan+scatter+必要同步的总暴露区间，不能只报CPU histogram或传输量。

**停止条件：**fused已覆盖；mapped host阶段隐含在其他工作；GPU扫描与同步更贵；为缩bytes丢CPU数据；改变组排序造成数值差异。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
