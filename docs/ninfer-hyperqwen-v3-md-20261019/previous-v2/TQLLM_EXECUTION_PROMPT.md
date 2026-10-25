> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 给后续开发Agent的指令：tqLLM性能融合扩展

阅读README、plans/01-tqllm-extension.md、docs/tqllm/00—09及当前阶段task。先确认原P0—P6真正完成及P6-GATE.source_commit，不把模板或源U当成合格集成结果。若未完成，继续原AI_EXECUTION_PROMPT.md；本扩展不替代上游合入。

目标是在不改变Targetartifact/模板/rk4v4/context的前提下，逐步实现P7—P12。tqLLM固定参考4d27324a124f92b7b7dcc554e6406ab6dc645b49，不merge无关history。先MTP/Lookup/完整KVverify，后原生27B DFlash2与独立全局DraftArchive。沿用C01—C08接口、唯一Targetverify/ReplaySSM权威；不得以为现有35B DFlash就是27B DFlash2。

从plans/tasks.json读依赖，按文件owner分配独立worktree。每task先写具名失败测试，reference独立，完成局部review；每phase合入一个固定commit做统一代码review与全部必测。公共头文件、CMake和Program集成由Integrator串行；GPU测试单队列串行。stage提交允许暂时UNQUALIFIED，但不得默认部署。

保留全部原自定义能力与日志扩展。新后端默认off；非greedy、decision、图像、LoRA或缺state只走明确合格fallback；不伪造q、不裁Target词表、不隐藏长prompt重算。缺HuggingFace固定revision/tensorinventory/license时只阻断高级资产路径；P8/P9可按已冻结主Target基线进行，P10必须补齐。

预算不够就NO_GO，不能缩context/改Targetquant/搬TargetKVhost。DFlashKV不是TargetL2payload，异步hostarchive在图外，epoch/lease/fence必须验证。观测用实际committedtokens含bonus和关键路径roundwall；reportedacceptance或峰值tok/s不代替Agentwalltime。

每phase从templates/Pn-phase-result.json复制到OUT，填真实source/asset/profile/GPU指纹和rawhash；运行phase_gate。缺设备/模型、skip、无授权都记BLOCKED/PENDING，不写PASS；只有收益不足时独立标promotion=DECLINED，绝不写性能合格。不得更改golden/退化阈值来让测试通过。部署仅在明确批准的具体目标窗口执行，单卡A/B/A并实际演练旧镜像+旧参数+旧cache回滚。

本包的Python辅助工具已自测，不表示NInfer代码已实现。最终输出实际新增/改造文件、每项精确性和业务结果、性能/内存表、启用范围、已知限制和回滚证据；不得引用研究15%门槛为测量收益。
