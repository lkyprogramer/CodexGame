> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# v2变更记录｜2026-10-15

新增tqLLM固定源码T评估、15项附件主张审计、12项采用账本、C01—C08设计、P7—P12的32实施task/6统一gate及对应验收矩阵。原P0—P6任务内容与状态不修改；只更新阅读入口、总体DAG/CSV、总矩阵及HTML/校验和。

新增Python预算/候选域/成本工具与31项CPU测试，连同原32项测试共63项。没有移植NInfer产品代码，没有CUDA构建、模型测试或4090性能结果；执行范围和所有PENDING模板保持真实。

重要修正：新基线采用原P4之后rk4v4；27B没有现成DFlash2；全局draftstate不能从TargetL2直接恢复；hostarchive不在CUDAgraph里；有效token成本包含bonus；大context参数不等于真实长prompt测试。

本扩展保留原输入分析字节及原包hash。详细原文件保留记录见evidence/tqllm/original-package-integrity.json。
