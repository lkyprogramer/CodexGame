# HyperQwen → NInfer：值得吸收，但应重排后半程

## 结论

保留 NInfer 的单一 Target、`.ninfer`、FP32 GDN 状态、ReplaySSM、完整 Target KV、B0/B1 与 continuation cache；吸收 HyperQwen 的 **Lookup 条件融合、神经草稿长度与验证长度解耦、复制模式控制、草稿词表校准和容量验证方法**。不要合并 vLLM 运行时，不因 donor 的峰值数字改变 Target 量化或默认 KV。

前一版已安排 MTP/Lookup，再追加一个“实现 Lookup”的任务会重复建设。V3 因此保留原 P0—P6（35 个任务），替换原 P7—P12 的执行顺序；tqLLM 的 DFlash2、独立 archive 和全局检索并未删除，而是接入统一的提案/验证契约，后置到 H6/H7。旧方案到新任务的逐项映射见 [迁移表](../plans/01-v2-migration-map.md)。

本次成果是实施规格，不是已经优化好的 NInfer。用户分支/上游 SHA 仍与前包一致；没有 P6 已完成的证据。[来源锁](00-source-lock.md)

## 381 tok/s 应如何理解

HyperQwen 作者在约 25K 文档复述工作负载报告：无 Lookup 为 159 tok/s、8 列融合为 260、16 列融合为 381；相应每轮有效 token 约 4.72、7.83、14.97。用两项相除反推每轮约 29.7、30.1、39.3 ms。扩宽不是让一轮更便宜，而是让更多已提交 token 分摊同一轮 Target 代价。[HQ01/HQ02，来源锁]

这些不是统一 Java Agent 测试，不与 NInfer 或 tqLLM 的不同权重/不同 prompt 数据直接排名。尤其 donor 对不同宽度报告了浮点分叉和显存压力，不能把“最终 Target 验证”当成任意 kernel 改动都严格无损的证明。[HQ02/HQ05]

对本项目，真正的收益函数是：

`任务总耗时 = 前端准备 + 队列 + 恢复/预填充 + 所有生成轮 wall time + 工具/测试执行等待`。

`有效生成速度 = 实际交付的新 token / 生成关键路径 wall time`。

Lookup、DFlash2 都可能提高接受数；但若重算草稿历史、扩大 Graph、热缓存重建、CPU 查找或 MTP 对齐抵消收益，端到端仍会退化。

## 三条可选路线及取舍

| 路线 | 好处 | 主要问题 | 选择 |
|---|---|---|---|
| 整体换 HyperQwen/vLLM | donor 的调度、量化与生态可直接使用 | 丢掉专门的 frontend/continuation 资产，模型与缓存变量变化，无法归因 | 不作为融合主线，可独立跑外部参考 |
| P12 后追加 HyperQwen | 保留旧编号 | Lookup、策略、Graph 会重复开发，DFlash2 成为不必要前置 | 不采用 |
| 重排 P6 后，统一提案层 | 先拿低资源收益，再接昂贵 drafter；一套验证/状态权威 | 需要显式迁移表与接口修订 | V3 主方案 |

## 投入顺序

H0 冻结真实基线及测量 → H1 在现有最多 6 列内做 MTP+Lookup → H2 做中文/Java 草稿词表 → H3 验证 8 列 → H4 条件性验证 16 列及动态复制模式 → H5 低成本路线独立发布 → H6 原生 DFlash2 → H7 全局 selective drafting → H8 最终组合资格。

这不是“先追求 381”。低成本路线在 H5 就有独立发布闭环，不必为不确定的 DFlash2 资产或 archive 等待。8/16 列不能通过或没有收益时保留较窄已合格路径；不得把未实现标为通过。

## 明确不纳入默认生产的项目

不移植 fp16 GDN 状态；不复制 vLLM 页大小 864；不以 KVarN 替换 `rk4v4`；不直接搬 40K 英文词表；不把 W4A8 扩展到 Verify/Decision；不把 Target KV 做稀疏裁剪；不在本轮增加多卡或树形 GDN 分支；不把 donor `.patch` 原样应用到 C++ NInfer。[HQ01/HQ04/NI02]

## 交付使用顺序

完整执行规格在[统一计划](../plans/00-master-plan.md)，每个新任务包含修改/新增文件、接口、前置依赖、至少3条具名断言（H1-T07八条）、最小验证命令及阶段review责任。具体来源均为固定SHA链接，作者速度、附件判断和本方案拟建内容分栏。

只执行已通过P6的真实分支；没有该证据先回原上游整合阶段。优先争取H5的低成本净收益，W16是条件性实验，不是交付成功的预设数字。

## 2026-10-20 执行修订

当前主力29默认temperature1/.95/k20；未来路线明确greedy/deterministic提案+保持Target sampling，利用已有delta-q接受器而不改为Target-greedy。新增组合资格前OFF，现网收益须同生产参数/实际route对照。先按 [B29合同](../plans/05-baseline-29-execution.md)完成真实基线、Pi两层与可追溯计量；原P0—P6的PROD/O/C设计并未遗漏，缺的是现场资格。H0后的投入顺序继续作为未来研究，不授权本轮实现优化。未完整取得的donor核心patch要在相应实施前补齐，不把固定SHA当作已经全读或编译。

## 2026-10-21成本与采样合同修订

已采用plans/06的初始278/阶段≤240/发布26任务variant安排；672保留声明但不逐阶段全跑，20×3通用下限撤回。design/11将greedy proposal与Target sampling分开，补H1-T07实际delta-q/processor/residual/RNG/state资格；不是已有算法已上线。外部donor greedy guard仍是其固定源码事实，不限制本地复用已有sampler的目标，也不自动证明本地组合正确。
