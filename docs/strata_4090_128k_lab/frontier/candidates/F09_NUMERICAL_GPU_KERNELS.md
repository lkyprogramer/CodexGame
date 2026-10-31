# F09 · SM89 tensor/attention/GDN数值路径重写

**状态：DEFERRED_QUALITY；当前硬件资格：无；数值意图：E1。**

作用域：深层kernel研究，非默认实施。旧项映射：O19/O20/O21/O28/O29/O32；原EXACT6不得重复算。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

将多query/专家行映射到Tensor Core、改变GDN扫描或attention split merge，可能改变规约/舍入。Strata现成qsa_decode_attn_split采用hi+lo/exp2/不同归约，不能写成精确无损。普通split-KV早已存在。

## 2. 来源与现有入口

- [QSA新split实现](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_prompt_attn.cu)
- [QSA旧decode](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_decode_attn.cu)
- [GPU IQ](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/iq_kernels.cu)

只选一个实际kernel入口；实际patch范围来自P02回执。先写数值contract/误差传播与完整状态测试，再选tile。禁止把多个GDN/attention/expert改写一次组合。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

当前具体shape有足够暴露时间、sm89/CUDA12.3可编译、额外转码/布局/scratch/数据来回后仍有净空间；同时质量前提满足。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

CPU/独立参考建立数据生成与长链oracle；sm89仅使用支持ISA。向量化/TC需要完整scale与溢出合同；配置关闭回原核。全部中间误差和接受率变化单列。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

E1不是“差不多即可”；tolerance/损害预算在观察候选前冻结，不能见差后放宽。保留选中集合与任务要求，不以任务错答为已有噪声免审。

## 6. 最小验证与阶段验证

最小：形状边界/NaN/极值/长序列递推/多querycausality；阶段门原六FAIL不得豁免，相对NI/绝对质量、memcheck、端到端。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

结构性变更的理论空间不能替代实测，当前不做百分比承诺。

**停止条件：**需要SM90/SM120；增大scratch破坏驻留；kernel快而完整慢；误差累积、任务退化或没有能力建立质量门。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
