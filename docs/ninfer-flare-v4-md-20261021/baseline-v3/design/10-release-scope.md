> V4继承材料：原始当前V3保留在源目录；本副本按V4根执行合同使用。历史“先跑Baseline”、旧发布依赖和旧scope不能独立调度。请先读[V4唯一执行入口](../../AI_EXECUTION_PROMPT.md)；原文事实、旧实验记录和未改写的历史状态不等同本轮授权。

# 发布范围与条件门禁：取消分支不等于测试通过

本页只明确默认全量DAG之外的两条窄范围发布路线，避免出现“W8不合格，却必须伪造H4通过才能执行H5”的矛盾。所有当前任务仍为PENDING。本次没有批准、实施或发布任何缩小范围。

## 唯一可选范围

| scope_id | 实施范围 | 唯一依赖覆盖 | 完成标签 |
|---|---|---|---|
| `full` | P0—P6、H0—H8 | 无 | FULL_SCOPE |
| `e1_w6` | P0—P6、H0/H1/H2/H5 | H5-T01依赖H2-GATE，替代H4-GATE | E1_ONLY_W6 |
| `e1_w8` | P0—P6、H0/H1/H2/H3/H5 | H5-T01依赖H3-GATE，替代H4-GATE | E1_ONLY_W8 |

机器定义同时列在[任务注册表](../plans/02-task-registry.md)的`release_scopes`中。执行者不得任意改依赖来绕过失败。派生DAG选择上述phase中的节点，然后只应用对应的精确覆盖；其余所有依赖保持原样。

`e1_w6`不声明W8/W16/DFlash2/selective已完成；`e1_w8`不声明W16/DFlash2/selective已完成。H3/H4中已经失败或未跑的任务状态原样保留，不改为PASS或SKIPPED-success。以完整方案验收时，它们仍是未完成项。高级H6—H8恢复执行前重新选择完整范围并补齐缺失前置；另行修订更窄高级范围需要新版本的范围记录及review，本版不隐含授权。

## 范围记录的必填字段

`scope_id, registry_sha256, scope_reason, excluded_task_ids, last_qualified_gate, candidate_commit, candidate_build_fingerprint, allowed_profile_ids, prohibited_profile_ids, removed_or_disabled_paths, residual_resource_bytes, regression_evidence, review_actor, review_verdict`。

排除清单必须等于注册表派生范围排除的任务，不得把范围内失败任务单独去掉。candidate commit必须包含对残留宽块代码的明确处置：移除未采用实现，或证明配置准入和运行时分支不可达、没有未预算的常驻资源。即使关闭flag，也要复测旧路径及资源账本。

## H0-T06检查器的派生DAG算法

```python
# Pseudocode: execution-time checker, not a completed implementation.
selected = registry["release_scopes"][scope_id]
nodes = {x["id"]: x for x in registry["tasks"]
         if x["phase"] in selected["phase_sequence"]}
for node in nodes.values():
    deps = selected["dependency_overrides"].get(node["id"], node["depends_on"])
    # Reject every dangling dependency or cycle in this exact derived graph.
    # For selected mandatory tasks: require actual successful assertions/review.
    # Do not rewrite the status of excluded nodes in the original registry.
```

检查器必须验证所有实际声明profile均在范围允许列表内。`scope approved`只代表范围接受，不代表GPU资格。H5仍必须对保留的全部路径在同一commit执行完整数值、资源、协议、业务和回滚验收。

## 无收益、正确性失败与缺资产的不同处理

**无收益但所有实验完整**：记录NO_ADOPTION，关闭/移除优化，复测保留路线。可形成研究结论，不得称该优化已提速。

**正确性或资源失败**：原任务保持FAIL，停止该候选资格；只有排除后重新通过窄范围H5，才能发布保留路线。不能用NO_ADOPTION擦掉失败事实。

**缺GPU、缺权重或缺测试**：BLOCKED/NOT_RUN。不得“推测能过”。H6/H7被阻断不影响已经实际通过的H5发布，但H8完整融合不能宣布完成。

**部署环境尚未授权或窗口未知**：可以完成源码和离线资格记录，production状态仍NOT_RUN；不虚构host或执行记录。

## 当前baseline-only不属于新发布scope

2026-10-20本轮先完成B29已有27B baseline，见 [plans/05](../plans/05-baseline-29-execution.md)。它是原P0部署测量前置，不新增第四个优化发布scope、不覆盖P6/H5生产gate、不修改任何PENDING。full/e1_w6/e1_w8依赖仍按原注册表执行，后续需要解除技术/发布gate耦合须另行同步修订所有相关phase及registry，不能口头绕过。

## 2026-10-21测量scope与最终sampling资格

已采纳 [plans/06](../plans/06-staged-evidence-budget.md) 的初始278+8/2工程、阶段≤240、发布26任务/variant；它们是measurement scope，不新增第四个feature release scope，不免除原full/e1资格。672未测组合仍未资格，20×3不再是通用下限。

full/e1_w6/e1_w8都包含H1，因此共同包含新增H1-T07 sampling硬合同；H1-T06必须先取得其资格。每个allowed profile还绑定delta-proposal语义、真实Target sampling归一化/processor/RNG合同ID、W/B/模型/资源/aux状态。Target-greedy诊断只可单独标research，不自动授权production sampling；生产参数T1/.95/k20/presence0/preserve-thinking/medium不改。未资格组合新路径OFF、原合格sampling继续服务；不能用fallback绿测凑候选命中。width/head/DFlash/selective需对应组合证据。没有p95/CI仍INCONCLUSIVE，即使预算用完也不能推广；缩声明要保留未资格列表和原因。
