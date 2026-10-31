# 候选资格回执

状态：NOT_EVALUATED。campaign、时间、作者、独立reviewer及validator均待填。此模板不代表实施许可。

## 1. 历史与源码差量

| 字段 | 实际证据 |
|---|---|
| 候选ID/原O编号 | 待填 |
| 旧机制被关闭的报告与结论 | 待填，不得只写名称不同 |
| P6文件/symbol/实际分派 | 待填 |
| donor完整commit/文件/symbol | 待填 |
| 真正新增的机制及原反例为何不再适用 | 待填 |
| E0/E1/Q与理由 | 待填 |

## 2. 完成路径证据

列窗口、请求和原件hash；明确采集是否改变了路径，单臂实际历史、低开销日志来源与扰动是否可分离；off/on本轮NOT_RUN，扰动不明为INSUFFICIENT。写已证明暴露区间、未知依赖、不可重复计数项。source-only、kernel总和或系统swap相关性均不能填成因果通过。

`T=待测；暴露并集C=待测；删光上界C/T=待测；局部s=待测及依据；新增H=待测及依据；净模型C/T×(1−1/s)−H/T=待算`。

## 3. 工程和资源

PATCH_SCOPE文件/symbol、固定规约与canonical域、OFF默认、fallback、host/VRAM额外峰值、shape/dispatch变化、生命周期、取消与收尾。若预计更改自然chunk/驻留而造成数值变化，重新分类，不借局部bitwise遮盖。

## 4. 判定

- source delta：NOT_EVALUATED
- actual hit/dependency：NOT_EVALUATED
- optimistic/realistic headroom：NOT_EVALUATED
- numerical/resource prerequisites：NOT_EVALUATED
- candidate state：NOT_EVALUATED
- campaign state：NOT_EVALUATED
- selected count：0，只有P02完整门通过后才能变为1

候选DEFERRED_QUALITY映射campaign的BLOCKED_QUALITY。只有未知证据时用INSUFFICIENT；明确无新机制或净空间不足才NO_QUALIFIED_CANDIDATE。全部不合格时结束，不回atlas选下一项循环。
