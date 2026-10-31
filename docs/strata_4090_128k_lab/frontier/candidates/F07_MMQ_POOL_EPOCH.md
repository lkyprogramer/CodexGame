# F07 · MMQ尺寸分级与有代际的scratch借还

**状态：HYPOTHESIS_UNQUALIFIED；当前硬件资格：无；数值意图：E0。**

作用域：prefill allocation高水位/生命周期，性能未获资格。旧项映射：O15/O44/O61；不同于HC专家保留。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

P6 ggml_cuda_host.cu与A0同文件：已有足够大空闲buffer缓存，但缺Maya的2次幂sizeclass/slab。Maya的sizeclass可以减少相近尺寸cache条目；slab让MMQ fixup用当前loan尾部。不能说P6没有缓存allocator，不能把资源维护收益当decode提速。

## 2. 来源与现有入口

- [Maya pool](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/prefill/ggml_cuda_host.cu)
- [P6 pool](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/ggml_cuda_host.cu)
- [Maya loan](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)

src/prefill/ggml_cuda_host.cu::CachingPool 先独立sizeclass；完整slab需另外修改prefill loan接口。拟定义 LoanToken{base,bytes,epoch}，allocate(size,token)返回pointer/actual_size/epoch，release_after(event,token)。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

记录实际request-size序列、cache复用、cudaMalloc次数/位置、held高水位与chunk/loan影响。先算向上取整内部碎片；warm无新增alloc且预算无变化即关闭性能方向。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

先只做sizeclass并保留原fallback；只有确证预算收益才引入slab。slab缓存以epoch+base+range验证，所有consumer的完成fence后归还。不能仅按base指针变化失效，也不能硬编码Maya针对30SM示例的16MiB上限。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

MMQ数学/shape/stream-K规约不变，kernel只访问requested bytes；同地址新epoch不能复用旧span；free只对所属allocation种类和代际操作；失败回退不得吞错误。

## 6. 最小验证与阶段验证

最小：尺寸边界/溢出、samebase不同epoch/smaller range、双free、alloc失败、旧event未完成、备用cudaMalloc路径；阶段门graph复用/长短切换/取消、memcheck与峰值资源。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

先报告held/alloc变化；TTFT改善需要对应暴露allocation或借槽链，稳态decode无alloc不承诺提速。

**停止条件：**P6现有缓存已够；sizeclass增大held；slab不降低真实预算；需要变kernel分派；引入新隐式同步；epoch/fence无法清楚证明。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
