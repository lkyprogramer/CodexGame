# 本轮最终报告

结论先写：NO_QUALIFIED_CANDIDATE / INSUFFICIENT / BLOCKED_* / RESEARCH_RESULT_ONLY / READY_FOR_HUMAN_REVIEW等真实状态。READY仅指材料可审阅，绝不自动部署。

## 身份与范围

campaign、source/binary/patch/asset/config/template、实际机器、授权范围、执行起止、目标负载、预登记及所有偏离。生产A0和研究B分开。

## 实际执行账

| Phase/条件 | 计划引擎/请求 | 实际引擎/请求 | 完成/失败/未执行 | 原件 |
|---|---:|---:|---|---|
| P01诊断 | 待填 | 待填 | NOT_RUN | 待填 |
| 数值/成本 | 待填 | 待填 | NOT_RUN | 待填 |
| P05 A/A、主批次、支持层分别列 | 待填 | 待填 | NOT_RUN | 待填 |
| 质量/热边界 | 待填 | 待填 | NOT_RUN | 待填 |

## 机制与整体结果

先写实际减少了什么，再写是否位于完成路径。累计kernel、bytes、alloc、slot与完整请求分开。报告TTFT、完整decode、wall、committed/thinking/content tokens、ms/token；时间下降与吞吐增长不混用。列主六对ratio/95% CI/预登记门，保留所有非目标及失败。

## 分项门

| 门 | 结论 | 证据/限制 |
|---|---|---|
| source/actual hit | NOT_EVALUATED | 待填 |
| matched numeric/canonical | NOT_RUN | 待填 |
| natural dispatch/lifecycle | NOT_RUN | 待填 |
| complete-request performance | NOT_RUN | 待填 |
| relative quality NI | NOT_ESTABLISHED | 待填 |
| original six absolute failures | UNRESOLVED | 不删除/换题/改评分 |
| thermal/resource | NOT_RUN | 待填 |
| production change | false | 必须与实际一致，发生意外则明确事件不能写false掩盖 |

## 归还、限制与后续

实际归还证据、13项保护前后差异、生产状态、owned PID闭合、GPU owner、原件清单。未读目标机就写未读。列尚未知的范围，解释本轮结论不能外推到其他模型/精度/并发/热稳态。零候选就是停止结果，不附自动下一候选。
