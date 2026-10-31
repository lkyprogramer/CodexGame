# F03 · 活跃内存压力与不必要驻留的生命周期诊断

> 2026-10-31本轮快照复制/生命周期审计已关闭：NO_QUALIFIED_CANDIDATE。未证明泄漏或可安全删除的已结束对象；唯一同步零填差量正确性通过但CPU三对均更慢，不追加GPU。预算6144MiB/4slots与PT0保持。见[独立审阅](../reports/F03_REVIEW.md)、[CPU回执](../reports/F03_TEST.md)和[本轮合同](../plans/F03_CPU_AUDIT.md)。下文保留原卡其他未知范围，不代表授权继续遍历。

**状态：DIAGNOSTIC_ONLY；当前硬件资格：无；数值意图：E0。**

作用域：warm单会话native内存与必要等待。旧项映射：O13/O39/O44/O61；不重复trim/MMAP/HC。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

P24所有引擎的majorfault/swap是需要解释的线索，不是已找到原因。新假说只能是当前warm请求的具体临时/重复驻留对象，结束生命周期后仍占用资源并导致必要活跃页反复换入。不能仅改swappiness、改MMAP、反复malloc_trim或加热缓存。

## 2. 来源与现有入口

- [P6配置/保护记录](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P6-V027-BASELINE-20261028.md)
- [P24内存记录](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)
- [Edge0 exact demand参考](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/windows/serve/prefetch.cc)

先不改native；在 tools/frontier/identity.py 和critical_path.py记录内存信息。若发现具体冗余owner，PATCH_SCOPE只列对应分配/释放/引用所有者与测试，不修改整个allocator。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

对native PID区分anon/file/locked、运行段fault delta、系统背景与本引擎活动，必要时只读可获取VMA信息；记录同窗被阻塞阶段。没有可归属对象或与关键等待的证据则保持相关性，不立项。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

对被证实已结束的单个对象缩短持有，或去除实际不必要的相同字节副本；如权重仍供GPU上传/回退使用不能释放。Edge0 hint-only思想只用于明确fault且保持true gate的未来分支，不重做learned profile。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

合法live snapshot、KV/GDN/PLE/MTP、guarded donor与graph指针不能被释放；同数据同分派。共享页按唯一物理对象计账，不把RSS下降等于DRAM流量下降。

## 6. 最小验证与阶段验证

最小：最后consumer仍在运行时不得释放；最后event后可归还；cancel/error再入不悬空。阶段门匹配oracle+内存/fault/时延记录，检查反复长短请求不增长。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

不能从P24的330–572MiB VmSwap推断必得提速。收益上界来自当前可归属fault/复制的暴露区间。

**停止条件：**仅系统swap背景、warm窗无nativefault、对象仍被需要、释放只减RSS不改变等待、额外copy/重算抵消、需改变cache产品预算。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
