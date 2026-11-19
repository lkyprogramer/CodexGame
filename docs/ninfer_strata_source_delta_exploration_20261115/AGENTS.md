# 本增补包的执行约束

## 权限与冻结边界

- 当前授权只包含研究、文档及文档校验。GPU、引擎启动、模型加载、HTTP 生成、远端写入预算全为 0。
- 后续实施、硬件资格、性能实验、生产部署分别授权；计划中的建议预算不是许可。缺批准 ID 必须 `BLOCKED_AUTHORITY`，不问工具绕过。
- 旧根目录 / 目标仓库更严格的 AGENTS、不可变 scorer、模型与部署合同优先。本包不替用户切换模型、KV codec、上下文、功耗、采样或引擎。
- 唯一编排控制器仍为既有设计 `tools/frontier/exploration_control.py`。若尚未实现，先把对应依赖记为未满足；不要为本包再造调度平台。

## 不可误报

- D1 是条件机制差量；H2 已规划而非新路线；K-PAIR 只是源码缺口；M0 是上游维护。
- GitHub 分支 / release / tag / engine 构建 SHA / 当前运行二进制必须分开。未绑定的生产身份是 null，不拿九月 b0 或十月 P4 代替。
- 不重新运行旧 H1、固定 W6、GDN K1、Q4 layout/prefetch、Strata DF2 等关闭窗口；新证据要列出旧实现没有的机制和新合同，不能换名字重开。
- 未找到后续回执只记 `SOURCE_UNBOUND`，不写“从未测试”。历史优化有局部效果但整链失败时两者都保留。
- 不把作者 5090、GB10、3090 数字外推为 4090；不把比率、总吞吐、单流速度、TTFT、自然任务 wall 混为一谈。

## 数值与状态

- Target 的权重、词表、采样/penalty/grammar 及现有正确性 oracle 不变；proposal 改动也必须证明 verifier 与 RNG 合同，不能仅说“Target 不变所以无损”。
- Greedy 第一阶段；sampled 未单独合格时强制走原 baseline，不沿用旧 proposal 的 q。
- KV、GDN、conv、hidden、MTP、position、token ledger、缓存身份均属于事务状态。取消、拒绝、EOS、预算截断、保存恢复都不能只裁 KV。
- 不删原有必要同步；观测不得新增热路径同步/IO/锁/分配。HES 对 Ada 不可用，沿用旧包的可支持回退方式。
- Graph capture 不是执行；分支选中不是证明 GPU 工作未执行；host query 结束不是设备精确完成时间。

## 协作与验收

- Phase 串行；同 Phase 无文件/依赖冲突的 Task 可并行。每个 Task 仅跑最小验证；每 Phase 统一派独立 reviewer 与 verifier，原作者不得自签全部门。
- 不得修改 holdout、golden、冻结门槛、删失败、补第七对、强制 ignore-EOS 或复用旧预算。
- CPU 合同、数值资格、服务正确性、任务质量、性能采用各自结论。最终需 observer-off 证据才可判断收益。
- 新目录文件无 remote write 权限。任何模型资产获取、真实 hidden 导出、私有代码上传、外部 API 消耗都需要单独授权。
