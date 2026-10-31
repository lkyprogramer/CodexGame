# F02 · 保留既有融合与算术的载入布局改造

**状态：DEFERRED_NEW_EVIDENCE；当前硬件资格：无；数值意图：E0。**

2026-10-31[Astra复核](../reports/ASTRA_REASSESSMENT_20261031.md)不支持继续优先推进本卡。旧P11 trace按实际PID/首末输出区间重算，GU-SwiGLU全家族并集6.8911%/6.5884%，但最大单格式TG21仅2.2188%/2.1287%；本卡限制一个格式、一个内核，不能拼全家族凑4%。共享解包、codebook staging和融合已存在，尚无已证load/layout新机制，取消原拟追加的四小时审计。

这是旧profile条件成本，不是当前真实暖态暴露时间或严格上界，不写为全局NO_GAIN或实测退化。当前本轮零候选收口；重开须先有独立新机制、当前真实暖态命中与可闭合依赖、可信净省时≥4%依据及明确执行范围。下文保留条件合同，不构成待执行任务。

作用域：warm decode，GPU或CPU二选一。旧项映射：O06/O21；P5/P12/DEQUANT_SIDE均不得重命名续跑。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

仅在新证据满足重开条件时，考虑现有native_gu_swiglu_kernel内部对齐载入、activation跨输出行复用，保持GU/SwiGLU/q8_1融合。CPU备选只在新的布局缺陷证据下做同字节数interleave，不是把P5 VNNI扩格式/nt。NIBBLE已存在于P6且受SM60门保护，是roundtrip证明参考，不是4090开关。

## 2. 来源与现有入口

- [GPU IQ dispatcher](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/iq_kernels.cu)
- [CPU expert入口](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cpu/native_expert.cpp)
- [无损转码证明参考](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/include/strata/core/expert_nibble.hpp)

GPU分支：src/kernels/cuda/iq_kernels.cu中的native_gu_swiglu_kernel及原row_dot；CPU分支：src/kernels/cpu/native_expert.cpp实际linked ggml入口。拟新增独立实验TU与layout descriptor，路径在选定分支后写入PATCH_SCOPE.json。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

P01证明具体kernel/dtype/nt/shape处于关键路径；区分load事务、整数依赖、codebook、寄存器spill和DRAM饱和。权限不足就UNKNOWN。若仅静态指令减少而完整专家没有可省空间，不实现。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

GPU分支保持原权重字节数/量化scale、lane到元素映射和加法树，仅合并对齐读取或共享重复activation words；CPU分支保持原packed值/scale并实现双向布局转换，禁止gather和放宽VBMI门。只选一个真实热点格式，一个内核，不开全格式矩阵。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

原integer dot、溢出约束、浮点FMA/规约顺序、fp32→fp16、SwiGLU/q8_1舍入、每entry独立性完全保持。off路径同二进制回原函数；on未命中时回退。EXPDEC会跳过GU_SWIGLU，不能直接代替本候选。

## 6. 最小验证与阶段验证

最小：真实blob roundtrip、极值/边界对齐、nt1与真实nt分布、有效输出逐字节；检查off命中0/on命中>0。CPU用超过LLC的blob轮转走真实ExpertPool全链；GPU查ptxas寄存器/spill并全层回放。阶段门回完整warm请求。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

GPU/CPU局部收益不能相乘。先给f与局部s的有证上界，扣repack/额外bytes；全流程仍需请求门。

**停止条件：**无新layout证据；只是重复VNNI/gather/Ada表；引入全模型双副本或展开bytes挤掉缓存；fusion减少；仅热L1/单dot快；full expert没有跨过预登记扩展门。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
