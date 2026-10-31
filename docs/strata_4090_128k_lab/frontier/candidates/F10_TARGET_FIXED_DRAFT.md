# F10 · 改变草稿成本结构，保持完整target验证

**状态：DEFERRED_SOURCE_AND_QUALITY；当前硬件资格：无；数值意图：E1。**

作用域：新的draft机制，尚无适配资格。旧项映射：O23/O33/O34/O35/O36/O38；MTPQ4/SPECCOST/spec扫描已关闭。本卡不授权自动重开旧实验。

## 1. 真差量与现有覆盖

只有减少真实draft成本/target无效工作的新结构才有意义。dense27B DFlash2的高吞吐不能直接迁到本MoE、Silver4216、当前MTP服务形态。把spec4改5、换min-p、重复Q4head不属于新方向。

## 2. 来源与现有入口

- [HyperQwen drafter](https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/drafter/README.md)
- [elpis作者说明](https://github.com/gildrb/elpis/blob/13e8b593ea4c65f605b5fe7ac7d5ebb7a24f3c19/README.md)

审查 src/program/generate.cpp 实际serve/draft禁用逻辑、target验证与GDN/KV rollback；拟单独DraftContract文档和适配层，不修改target数学路径。

所有拟新增接口都属于未来隔离实现，不表示当前仓库已存在。先核P6基线源码与实际分派，donor最新main只作参考。

## 3. 立项前必须回答

当前trace拆draft成本、验证成本、commit、重做与接受分布；已有兼容资产且24GB/64GB可容纳；真实服务分支确实支持。需新增下载/训练权重时另列范围，不默认获得。

填完 [资格回执](../templates/QUALIFICATION.md)，同时满足差量、依赖、资源和质量前提，P02只选一项。没有资格不构建候选。

## 4. 最小实现任务

先证明greedy和stochastic验证合同（p/q、残差或实际算法等价），然后小范围draft-only计算变化。改变verify batch造成target数值变化也要列E1，不能用“仅草稿”规避。

- [ ] 冻结PATCH_SCOPE、baseline和off/on路径，登记单项主指标、样本上限与停止条件。
- [ ] 先实现最小必要负控制/比较器；证明错误实现确会被拒绝。
- [ ] 只写上述窄改动；功能默认关闭，off/on实际命中计数可复核。
- [ ] 运行本卡最小验证；成功后交给Phase统一独立review与test。

## 5. 不可越过的数值与生命周期边界

target专家/模型/模板/采样不变；每拒绝位置的所有状态回滚；实际proposal概率可得且与产生proposal的算法一致。trained prerouter替换target不属于这条路线。

## 6. 最小验证与阶段验证

最小：全接受/首拒/中拒/全拒、EOS、取消、nonzero温度下已知小分布精确测试；阶段门真实任务和complete-state compare，不仅接受率。

必须区分离线/CPU/目标GPU结果。已有工具证据可复用，不能把未跑记PASS。除本卡范围外不扩展全格式、全长度或全部benchmark。

## 7. 性能主张与止损

衡量总draft+verify+redo/真实committedtokens，不能把acceptance提升当等幅速度提升。

**停止条件：**新草稿放不下、服务不支持、需target裁剪、正确采样证明缺失、acceptedtokens增但ms/token不降。

最终使用 [统一统计](../docs/06_BENCHMARK_PROTOCOL.md) 与 [数值质量门](../docs/05_NUMERICS_AND_QUALITY.md)。变快但质量阻塞只能RESEARCH_RESULT_ONLY；任何情形都不自动部署。

## 8. 必交证据

source-delta与命中表、预登记、代码/编译身份、off对照、最小正确性/负例、资源账、原始结果/失败、区间与限制、review/test回执、生产保护与资源归还。模板不能替代实际原件。
