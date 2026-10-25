# V3变更记录

## 2026-10-21 · 完成Baseline后的只读评估

新增research/04与plans/07，基于278参考及66条编程wire复算瓶颈、decode-only收益情景与下一轮预算。补充97fc7be6的ContextCapacity/KV-growth截停证据，区分其reasoning重复行为；RE003-v1原FAIL保留但题意/隐藏trim不一致不能归因模型事务能力；Gson两项失败selector缺失继续unknown。首轮收敛同宽Lookup、沿用Target sampling，不启proposal-skip/W8/W16/DFlash2；64请求含准备并计入240，1680正式纯请求约20.77小时。design/11与plans/06同步来源、完成状态和实际grader外层450秒记录；本轮没有实施优化、重跑或修改现网。

本版基于2026-10-15 V2完整ZIP，核查HyperQwen至2026-10-19固定提交。

P0—P6的35个任务、上游合入里程碑、43定制文件保留账本、冲突/部署/回滚分析均保留。P7—P12的32个任务全部映射到新H0—H8的52个任务；新增条件融合、词表治理、W8/W16完整shape、per-lane控制、状态对齐/Graph和独立低成本发布闭环。总有效实施任务87、阶段16、待执行断言256。

调整了旧方案将Lookup当backend和按神经K限制verify的设计，显式补全MTPalignment；沿用V2已建立的Target/Draft缓存分离，并纠正附件把旧E8当新默认的描述。保留原文与独立核验表，不静默改写附件。原2026-10-19设计未将精确采样和复杂TokenTree纳入默认；2026-10-21确定性草稿/Target sampling修订见下，随机draft/TokenTree仍不实施。

交付形式调整为仅MD：原HTML省略，非MD文本支撑材料装入可读围栏，可校验恢复；所有原MD依赖链接改到对应MD表示。旧脚本并非本次新增代码或已执行产品测试。

## 2026-10-20 · 29实证审查修订，baseline先行

- 新增plans/05，当前范围为已有27B的B29 baseline/实际14档/Pi真实session回放和脚本监控、可恢复进度与定时唤醒；优化不实施，baseline完成不等于P0/P6/H0通过。
- 保留原PROD/O/C、codec独立迁移设计，填明B29 E8/schema20/实际sampling与BO/B6未认证的区别，source目录/PINNED_COMMIT不冒充运行binary构建来源。
- 修订C10逻辑K/V与物理W/B/tokenrows、K1/K2 padding/budget映射；新hybrid首版greedy资格不扩为主力sampling收益。
- 统一探索/正式样本、p95/CI和未知规则fail-closed；旧p95 helper缺陷由现行规则替代，原previous-v2围栏字节不改。
- 明确schema20→24 adapter、requestID/cache/实际tokens、Pi固定轨迹与隔离闭环、raw/metric/hash缺值及状态；同步registry/具名断言与现行任务入口。
- 原完整/窄scope DAG保持依赖不变，P6→H0/H5→H6生产门仍是后续前置。更新README/AI入口/INDEX/MANIFEST；原交付验证标历史，另记本次修订验证。

本条是文档修订，不是baseline、CUDA/模型资格或优化发布的完成记录。实际结果由各run文件记录。

### 同日runtime合同补正

按实际源码继续纠正容量为O_eff=min(O,C−P+1)、末token不入KV、4096初始decode窗口及动态页growth；P+O≤C仅保守资格预算，不强加固定正R。补齐messages/count_tokens不提交KV、复杂Pi跨协议校准限制。正式core冻结B29原argv，不启no-prefix-reuse；实际cold条件不达标留coverage gaps，nonce/key/slot erase不当清L2证明。同步H0-T02/H3-T01、registry/具名断言，原历史围栏不变。真实Java业务集仍需原合同资格，算术smoke不冲抵20业务任务×3。

## 2026-10-21 · 已采用分层范围与确定草稿/Target sampling合同

新增plans/06：保留672声明目录，首次174core+104专项=278请求，Pi44一次O32768；8工程一次seed1701+2固定外部repo一次，发布8×3+2=26任务/variant，撤回20×3通用下限。每阶段≤240相关A/B请求（准备/重试模型调用计入），H5/H8集中拟发布profile正式p95/CI；预算不构成性能资格。旧manifest/raw/损坏证据保留，ROOT管理切换/监控，不改生产参数。

新增design/11：greedy仅描述确定性delta proposal，最终Target保持生产sampling；复用已有accept/processor/RNG/preview/resolve/commit，不另造sampler；补fractional residual、条件mixed prefix、processor时序、support、bonus/stop/cancel和分布vs同路径seed合同。纠正license计数与最终发布前缀的边界；C14保守tail策略不冒充数学必要条件。新组合资格前OFF，回原合格sampling，不强改T0。

H1内新增T07八组断言并作为T06前置，H1gate纳入；无新phase，原P6/H5生产依赖保留。当前88实施任务+16gate、264待执行断言，full/e1_w6/e1_w8分别104/68/75节点。同步入口、现行registry/tasks/matrix、release scope与INDEX/MANIFEST；previous-v2/inputs历史字节保持。所有优化任务仍PENDING、B6仍null，本次不实施引擎优化或声称sampling资格通过。
