# 交接、回滚与长期证据维护

## 交付最小集合

每个进入过实施的候选保存：spec、budget、source/binary/model锁、baseline与candidate diff、raw manifest、最小测试输出、数值/服务/质量/性能各层结论、独立review、已用额度和明确下一步。只做R0/R1也需保存关闭原因，防止后续Agent再命名重跑。

在 `Decision.json` 中分别设置 `cpu_contract/numeric/state/service/observer/task_quality/performance/deployment`。没跑为NOT_RUN，缺证为BLOCKED/INCONCLUSIVE；部署永远不能从performance PASS自动变PASS。

## 默认关闭与回滚

- D1/H2开关名称和解析语义先在R0冻结；默认关闭且错误配置fail-closed。不能让`ENV=0`因“变量存在即真”意外开启。
- 单一请求开始时固定策略，不能在pending transaction中切换；运行中的state不能用不同policy或资产解释。
- H2sidecar不匹配立即走baseline，并记录reason；若fallback需释放资源，等真实last consumer完成，不删正确性同步。
- D1关闭前完成合法commit/cancel和草稿历史交接；不能遗留“copy选中、MTP未追平”的状态给下一请求。
- 生产升级/回退只在另获批准维护窗口；停止/替换的进程必须是OwnedServer记录的精确PID/startticks/instance，不用进程名批量kill。
- 不自动删除实验目录或失败数据；清理需明确目录、保留期限、用户许可和可恢复方式。

## 防止下一轮重复

把新结论追加到旧台账，而不是覆盖旧FAIL：`candidate_id/previous_route_ids/mechanism_delta/contract_hash/result/evidence_refs/reopen_requirements`。D1-P、D1-S分开记录；H2保留旧计划与本适配的双层状态；K-PAIR若ALREADY_COVERED就关闭源码缺口；M0记录部署commit与精确回归用例而非“升级了”。

来源刷新只触发只读diff。只有相关机制改变才申请新实验，不能用版本监控自动启动GPU。作者README更新不能覆盖已锁raw；未来采用更新donor时保留旧pin和迁移理由。

## 给接手AI的短提示

> 先读本包AGENTS、历史台账与Decision。当前是研究文档，不是GPU许可。检查实际部署与后续P3身份，逐项复用已有能力；没有真实差量则停止。最多选择D1/H2之一，保持Target、codec、context和W。Task最小测试，Phase独立审阅与验证。状态/质量/性能分别出结论。不得补样本、修改golden、扩大预算或替用户上线。

## 待用户输入的最少内容

不要求用户再次重做旧benchmark。下一次若愿意实施，只需先提供：当前NInfer/Strata部署的build与配置摘要、P3/P4实际使用状态，以及是否允许读取已保存的真实Java编辑token轨迹。之后根据R1选择结果，再讨论是否值得授予一个小硬件窗口。
