# F12 · 已具graph/doorbell/overlap的供给缺口诊断

**状态：COVERED_DIAGNOSTIC_ONLY；当前硬件资格：无；数值意图：E0。**

作用域：warm decode主机供给，只找新的实际缺口。旧项映射：O01/O02/O03/O09/O17/O25/O26/O31/O62；NP3已覆盖重要子项。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

A0已有verify/commit/MTP graph、mapped-pinned doorbell、shared延后、distinct-expert复用。Maya没有可直接移植且保留dispatch的新deadline调度器；Edge0 StepPrefetch是FIFO/ticket cancel。仅当当前主线程可运行却不被调度、graph必要供给存在新依赖空洞时研究局部修复。

## 2. 来源与现有入口

- [P6 prefill overlap](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/prefill.cpp)
- [Maya GLM调度](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)
- [Edge0队列](https://github.com/Edge0-AI/Edge0/tree/d4a2fa02fcf06c08961248a2da1d8fc861d842ef)

先只instrument真实submit/complete/commit边界；选定后PATCH_SCOPE必须具体到某个唤醒/事件/host-work前移点。禁止先重写全runtime或persistent megakernel。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

以实际runnable/running、pool task工作与idle、GPU就绪/CPU依赖区分等GPU/等CPU。NP3同步2.5µs/miss等是旧观测，不把早期17µs固定开销复活。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

只减少已证明冗余的同步或把不依赖GPU结果的metadata前移，保持归属、地址、计算/提交顺序。线程亲和性不是先扫参数项；需要真实调度饥饿和与旧pool实验不同的原因。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

event不能提前signal，polling不会读未publish值，memory order匹配CPU/GPU可见性；cancel/watchdog/下一请求继续可用；不更改模型/采样。

## 6. 最小验证与阶段验证

最小：延迟完成/错误完成/取消/正常发布、负例早signal被拒；阶段门自然窗口与raw状态，不用人为slowdown制造收益。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

从可消除供给空洞的并集估上界，不从所有cudaEventSynchronize耗时估算。

**停止条件：**等待来自实际expert计算；GPUidle份额很小；旧pool/overlap已覆盖；减少wait仅把等待挪位置；额外busyspin争用CPU/DDR。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
