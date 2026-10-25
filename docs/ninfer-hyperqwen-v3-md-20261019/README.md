# NInfer 性能融合文档包 V3

**2026-10-21 分层范围与sampling合同修订 · 当前 BASELINE_ONLY，优化尚未实施**

278参考与8+2闭环评分已全部记账，结果含明确证据缺口。最新入口：[完成Baseline后的瓶颈/失败评估](research/04-completed-baseline-assessment.md)与[下一轮验证顺序/收益/耗时](plans/07-baseline-informed-validation.md)。97的容量截停、RE003未公开trim断言和Gson缺失逐项评分已分别处理；当前只评估及修订文档，不重新启动测量或改现网。完整结果见[原始最终报告](../../output/ninfer-baseline-29-20261020/FINAL-REPORT.md)，原成绩/raw不回写。

已按 [29 Baseline合同](plans/05-baseline-29-execution.md) 与 [分层范围/预算](plans/06-staged-evidence-budget.md)完成初始174core+104专项=278参考、Pi44各1遍/O32768、8工程各1遍+2repo各1遍的记账。后续阶段相关A/B≤240，发布8×3+2=26任务/variant；672目录保留为声明覆盖，未测仍未资格。本轮只评估已完成证据并更新文档，不实施引擎优化或重新发起Baseline。

核心路线：保留原上游整合P0—P6；统一后续MTP＋Lookup＋词表＋条件宽验证，再接tqLLM的DFlash2及全局检索。HyperQwen参考提交`30dba4f11b57`；不是合并vLLM。

## 阅读入口

[结论与优先级](research/01-executive-analysis.md) · [附件逐项核验](research/02-input-claim-audit.md) · [技术吸收/冲突图](research/03-donor-adoption-map.md) · [固定来源](research/00-source-lock.md)

[统一架构](design/00-architecture-and-contracts.md) · [完整执行计划](plans/00-master-plan.md) · [旧任务迁移表](plans/01-v2-migration-map.md) · [88个实施任务与16个gate](plans/02-task-registry.md) · [264条待执行断言](plans/03-acceptance-matrix.md)

Agent从 [AI_EXECUTION_PROMPT](AI_EXECUTION_PROMPT.md)进入。原P0—P6资料保留在 [previous-v2](previous-v2/README.md)。原旧P7—P12不再执行；其设计/数据作为来源承接到H0—H8。所有MD文件见 [目录](INDEX.md)。

## 本次修订与执行边界

29 实际 B29 是 e753…/binary447e…、rk4v4-e8、MTP3、schema20、C1，生产采样temperature1/top_p.95/top_k20。BO重建和P6/rk4v4/schema24尚未取得资格；已有PROD/O/C与codec迁移设计继续有效。未来目标为greedy/deterministic proposal+保留生产Target sampling，新增组合资格前OFF；Target-greedy独立诊断，不代表现网收益。

原统计helper会静默忽略p95规则，执行必须fail-closed；首次薄覆盖与阶段筛选不做发布级重复，H5/H8对实际声明profile集中正式关键case≥10配对、p95桶≥100及CI资格；不足INCONCLUSIVE。Pi固定轨迹与真实闭环分开；缺字段保持null，warm/cold要有真实cache来源。逻辑有效列与物理verify宽度已明确分离。

## 本版关键决定

Lookup不是一个新神经backend；每个候选的source与resident MTP/DFlash2分开。MTP最多5步不妨碍外部候选K15/W16，但必须完整扩展frame、ReplaySSM、Attention、MTPalignment、Graph和资源资格。COPY只省proposal，不省必要的state alignment。

保持P6已经合格的rk4v4、Target、tokenizer/template、上下文和原定制。附件E8描述保留原文但不回写为新默认。40K词表不直接照搬，中文/Java/工具/bytefragment按真实ID校准。W16与DFlash2没有收益或预算失败时保持OFF，不以381 tok/s作为目标。

## 文件形式与执行边界

ZIP仅包含`.md`。原V2非MD支撑材料以可读、可校验的Markdown围栏保存；需要旧P0—P6工具时按 [恢复指南](support/REHYDRATE.md)在包外还原。没有HTML、独立脚本、JSON附件、模型或图片文件；MD中的接口代码和命令是文档内容。

[2026-10-19 交付验证](DELIVERY-VALIDATION.md) 是原文档封包历史，不代表当前baseline状态。新修订检查见 [2026-10-20 修订验证](REVISION-VALIDATION-20261020.md)；实际29指纹/smoke与未完成项见 [主审查报告](../ninfer-hyperqwen-v3-review-29-20261020.md)。NInfer候选构建、优化CUDA资格、词表/DFlash2转换尚未执行；完整baseline状态由新run记录。

## 最新合同

[确定草稿与Target sampling](design/11-sampling-acceptance-and-proposal.md) 明确复用已有accept/kernel/processor/RNG/commit，greedy是proposal而不是强制最终输出。H1内新增H1-T07八组sampling断言；未资格请求回原合格sampling路径。新增文档/任务仍是拟实施，不宣称B29已得到新算法。最新文档一致性检查见 [2026-10-21修订验证](REVISION-VALIDATION-20261021.md)，旧验证只保留其原日期结果。
