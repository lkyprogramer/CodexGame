# F01 · 现有selected-KV路径：只查尚未解释的读取/失效

**状态：COVERED_DIAGNOSTIC_ONLY；当前硬件资格：无；数值意图：E0。**

作用域：warm长decode；只诊断已存在的page cache路径。旧项映射：O27/O29/O49/O50、CFG-KVRES/KVGROW。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

tqLLM新增compact selected-row gather/cache不构成直接迁移机会。Strata A0与P6的kv_stream.cu同blob，已经跨query去重、epoch pin、CLOCK和16B向量搬入GPU。唯一剩余假说是：当前实际调用存在多余失效/冗余读取，或在既有attention内部跨verify query复用同一KV载入，而不改变顺序和规约。没有该缺口就关闭。

## 2. 来源与现有入口

- [Strata P6 kv_stream](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/kernels/cuda/kv_stream.cu)
- [QSA decode](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_decode_attn.cu)
- [tqLLM gather](https://github.com/turbo-tan/tqllm/blob/b35b2ce9df8927c672f888651946849219a0effa/src/models/qwen/qwen4exp/qwen4exp_qsa.cu)

审查 src/kernels/cuda/kv_stream.cu、qsa_decode_attn.cu 及 include/strata/kernels/kv_stream.hpp。实现时仅改一个已证明缺口；不添加第二套全contextscan/compactcache。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

采P01的page miss/hit/epoch、必要bytes、resolve→copy→attention依赖；attention width最多2051，测真实跨query交集而非以128K当width。只有选中行重复load在关键路径、且改法没有被现有缓存覆盖才可新提案。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

若是多余失效，新增明确request/KV/graph epoch标识，修一处错误失效边；若是核内load复用，保留原CHUNK和merge树，只共享已证明相同canonical cell的读取。两者不能一次一起做。新增计数 off/on 实际命中。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

每query selected IDs、validmask、causal cutoff、K/V量化字节与scale、逻辑行序、CHUNK/归约树均相同；page重新分配的物理slot可不同但必须还原同canonical地址。拒绝/rewind/restore后无stale KV。

## 6. 最小验证与阶段验证

最小：同K/V与selected IDs重复/不重复/页尾/碰撞各一个，canonical回读逐字节。必须区分resolve epoch与内容/所有权generation：前者每次resolve更新，用于本次pin和CLOCK，有效resident页在下一epoch仍应命中；只有映射、内容或所属会话实际失效的页才不得命中。host/resident写入一致性沿用原合同，不能为reject/resume无条件清空缓存。阶段门：跨20480 resident阈值、graph recapture、spec拒绝与A→B→A。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

只报告实际去重后必要bytes与暴露等待的差额。当前没有收益估计，不借用tqLLM 109GB/256K数据。

**停止条件：**失效分支没有额外失效则关闭该分支；核内复用分支没有可消除的重复resident load或暴露成本不足则关闭该分支；两者均无缺口时整卡保持COVERED_DIAGNOSTIC_ONLY；暴露成本不足；新增scan/remap/副本高于减少的读取；驻留expert减少；需改attention归约。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
