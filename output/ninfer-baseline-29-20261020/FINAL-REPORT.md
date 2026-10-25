# 29 / Qwen3.8-27B 精简 Baseline 结果

278 项参考覆盖和 8+2 个编程任务已完成记账。本次仅测量现有部署，未实施引擎优化；不代表优化或未来 sampling 资格通过。

参考单元：278/278；复用 28，新采集 250；保留原始 gap 4 个。
Pi 输入拒绝：容量 1 条，非法冻结工具参数 4 条；均不属于有效性能样本。39 条 HTTP200 回放也不等于任务质量通过。

| 编程任务 | 结果 |
|---|---|
| qcb-BF009 | PASS |
| qcb-LC003 | PASS |
| qcb-RE003 | FAIL |
| java-agent-3-reconnect-loop | PASS |
| java-agent-2-retry-contract | PASS |
| java-agent-1-idempotency | PASS |
| qcb-RE007 | PASS |
| qcb-AT005 | PASS |
| javaparser__javaparser-4561 | PASS，4/4 |
| google__gson-2158 | FAIL，8/10 |

| 编程 attempt（原请求组） | 模型请求轮数 | 提议工具调用 | 实际 P / O / cache hit | 总 token |
|---|---:|---:|---:|---:|
| java-agent-1-idempotency/repeat-1/ordinal-1 | 7 | 9 | 23551 / 1369 / 20647 | 24920 |
| java-agent-2-retry-contract/repeat-1/ordinal-2 | 5 | 9 | 15837 / 815 / 12730 | 16652 |
| java-agent-3-reconnect-loop/repeat-1/ordinal-3 | 5 | 12 | 64542 / 1163 / 49313 | 65705 |
| qcb-BF009/repeat-1/ordinal-4 | 4 | 4 | 18050 / 4866 / 11805 | 22916 |
| qcb-RE003/repeat-1/ordinal-5 | 5 | 10 | 16024 / 1020 / 12652 | 17044 |
| qcb-RE007/repeat-1/ordinal-6 | 4 | 6 | 15599 / 3816 / 10715 | 19415 |
| qcb-AT005/repeat-1/ordinal-7 | 8 | 10 | 39981 / 5347 / 35004 | 45328 |
| qcb-LC003/repeat-1/ordinal-8 | 4 | 7 | 16376 / 2424 / 11859 | 18800 |
| google__gson-2158/repeat-1/ordinal-9 | 8 | 9 | 141936 / 2815 / 123001 | 144751 |
| google__gson-2158/repeat-1/attempt-2/ordinal-9 | 8 | 7 | 90549 / 3819 / 79268 | 94368 |
| javaparser__javaparser-4561/repeat-1/attempt-1/ordinal-10 | 8 | 8 | 663235 / 1935 / 576818 | 665170 |

轮数是实际 HTTP 模型请求数，工具数是响应中提议的调用数；原 CLI turn 及执行器原生统计无法等价恢复。P 包含重复及缓存输入，不等于独立输入或计费金额。Gson r2 ordinal-9 中止与 r3 attempt-2 单独列项，成本未删除。

两条历史 Pi 异常：

- pi-pi-ee064ce94fbb-f89c5dcc：P=25575，O=298，请求上限=32768，finish=tool_calls，reasoning_only=False，output_budget_exhausted=False。
- pi-pi-ee064ce94fbb-97fc7be6：P=31421，O=32767，请求上限=32768，finish=length，reasoning_only=True，output_budget_exhausted=True。

Gson r2 的工具策略中止及 8/10 部分评分另行保留，未被 r3 完整评分覆盖。完成失败仍计入结果和成本；未为提高成绩重跑任务。

| 测量组 | 记录数 | 请求耗时合计（秒） | HTTP200 / HTTP400 |
|---|---:|---:|---:|
| core | 174 | 5990.94 | 174 / 0 |
| long_output_8192 | 12 | 975.28 | 12 / 0 |
| pi_teacher_forced | 44 | 1695.03 | 39 / 5 |
| capacity_boundary | 16 | 503.40 | 15 / 1 |
| protocol | 8 | 8.21 | 6 / 2 |
| C1_queue | 6 | 59.21 | 6 / 0 |
| disconnect | 1 | 2.00 | 1 / 0 |
| disconnect_recovery | 1 | 1.73 | 1 / 0 |
| negative_contract | 1 | 0.00 | 0 / 1 |
| S3_append | 4 | 131.49 | 4 / 0 |
| S4_S5_branch | 4 | 13.86 | 4 / 0 |
| S4_system | 2 | 120.82 | 2 / 0 |
| S6_L2 | 5 | 527.63 | 5 / 0 |

上述耗时是请求耗时合计，包含复用结果；不能当作本次运行的总墙钟时间或候选性能收益。分组聚合也不构成 p95 或 A/B 置信区间。

原始指标与完整性：

- [最终备份回执](/Users/luo/.codex/task-evidence/ninfer-baseline-29-20261020/backups/final-20261021T093140528906Z/BACKUP-RECEIPT.json)
- [完整汇总及证据缺口](final-summary.json)
- [278 项逐记录指标](reference-metrics.csv)
- 逐项 record/request/raw 哈希和原 manifest 已核验。旧矩阵 513 条记录保留，原 3 个损坏 raw 不计入有效统计；历史游标副本不是独立样本。
- 本机原始 CLI、部分补丁和 grader 附件目录已缺失。恢复审计区分历史 SHA 相同字节、仅派生内容和无法恢复附件；未补造原始日志。
- 恢复审计：/Users/luo/.codex/task-evidence/ninfer-baseline-29-20261020/recovered-derived-20261021/recovery-audit.json。
- token IDs、真实逐 token ITL、可靠 reasoning token 拆分、round wall、allocator 高水位不可观测，保持 null 和原因。p95=null。
- 生产采样参数及 Pi medium/32768 预算保持原值；greedy 参考仅为原计划中的独立诊断样本。
- 运行期间发生过采集/接续修复和证据备份，时间与副作用由各回执记录；不从本次单参考推导优化收益。

协议证据补充：18343 非流式代理丢弃响应请求 ID，原采集器记下两项关联失败并停测。完整 HTTP200 JSON 与冻结服务日志中唯一时间窗的 start/done、usage 和 timing 相符，已后验核对完成；原 row/raw、失败和 null 指标均保留，未重发，该条不计入有效性能样本。详见 final-summary.json 的 protocol_reconciliation。

Responses 接口覆盖缺口：2 条原样请求被完整 HTTP400 拒绝，服务不支持 chat_template_kwargs.enable_thinking。未删除该参数、未重发已完成请求；原失败/null 指标保留，不计有效性能样本或模型质量失败，也不宣称 Responses 成功覆盖。详见 protocol_option_rejections。
