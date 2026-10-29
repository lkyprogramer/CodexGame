# 实验报告：ID / 名称 / 日期

## 1. 结论与证据等级

Decision填写ADOPTED/NO_GAIN/NOT_APPLICABLE/QUALITY_REGRESSION/BLOCKED/INSUFFICIENT等；明确H/S/P/L/I、主指标、估计值、区间与是否达到预登记边界。不要将SCENARIO_PASS写成已部署。

## 2. 身份与处理变量

填写base/candidate/donor SHA、patch、binary SHA、GGML/compiler/flags、host/inventory/model/template/MTP/dataset hash、实验开关与activation证据、真实dtype/shape、有效策略。列处理变量和所有保持条件；给完整脱敏config diff。

## 3. 假设与机制验证

本来哪段关键路径慢；已有实现是什么；本次真正delta是什么；真实callsite/branch计数、phase/bytes/资源账如何证明命中；插桩是否改变图、关闭插桩后的测量是否一致。

## 4. 实验协议

登记日期、任务分布、case/task数、paired round/block数、顺序、warmup/reset、cache冷热、实际context、seed、预算B、oracle、固定输出/完成规则、预定停止规则、主要/次要metric、CI方法、流量权重。若偏离计划逐条列出，不补写成原计划。

## 5. 结果

| stratum | arm | independent units | task success | restricted time | raw wall | committed tokens | peak VRAM | peak RSS | failure kinds |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 待填 | | | | | | | | | |

另列paired四格、CP相对非劣、绝对质量门、数值/state误差与所有新失败。严禁删失败、混场景、将event间隔当token ITL、将kernel累计当请求wall。

## 6. 验证与限制

逐项列已执行命令、退出码、raw文件与hash；NOT_RUN/SKIPPED明确列出。micro/model/scenario/holdout/combination分开；模板中的示例数字不能作为成绩。

## 7. 决策、回滚与重开条件

是否保留、为什么、资源机会成本、功能/质量边界、关闭开关与已知好binary/config、后续仅在何种新证据下重开。生产采用需P12完整证据。
