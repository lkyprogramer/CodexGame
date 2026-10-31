# 05 · 数值等价、目标语义和任务质量

## 三个等级

| 等级 | 允许变化 | 最少证明 | 当前推进边界 |
|---|---|---|---|
| E0 | 表示/内存布局/整数metadata/生命周期改变；数学、分派和规约顺序保持 | 同输入同分派基线重复成立；B/A1及A1/C的有效中间值、最终logits、KV/GDN/PLE/draft状态在canonical域逐字节一致；边界与生命周期 | 可在资格后做研究实现；不豁免任务质量 |
| E1 | 同目标数学意图，但FP求和、CPU/GPU归属、kernel形状或verify状态路径改变 | 冻结数值容差/损害预算；长链漂移与任务质量；证明不是吞掉专家/状态 | 原六FAIL、正式质量前提未满足时DEFERRED_QUALITY |
| Q | 减专家/降低目标精度/剪KV/改attention预算/少thinking等 | 独立模型/产品质量速度Pareto研究 | 不属于当前主线的无损引擎优化 |

“无损转码”仅表示权重数值可恢复；若乘加、规约、分派变了，整个推理不自动是E0。“draft-only近似”也不自动等于采样分布保持。

## 复用P13–P21的正确教训

自然A/A跨引擎不逐bit，可能因为实际CPU/GPU分派、resident mask、分组顺序不同。不能把这称为候选免责，也不能强制整个baseline关闭CPUshare来制造一致。

匹配oracle应捕获真实有效输入、expert IDs、token-row/scatter顺序、resident mask、dispatch、MMQ参数、MTP batch与必要状态。先同快照的基线重复执行逐bit，再比较未改P6基线B与候选二进制关闭路径A1，然后比较候选开启C。同路径一致只证明该路径；恢复自然分派后须另验。A0始终指生产v0.2.3保护对象，不进入跨版本bitwise比较。正式统计工具中的A仅是对照臂标签，必须绑定研究基线B的同一身份。

比较有效初始化区域，不比padding；哈希用于索引和完整性，逐字节检查才是内容证明。必须有负控制：输入/route/layout/state身份错误被拒绝；故意错一字节被发现。不要重建一个比优化本身更大的通用回放系统，复用原工具并针对候选最小扩展。

来源：[oracle报告](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P14-P15-NUMERICAL-REPLAY-ORACLE-20261029.md)、[16K及生命周期](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P20-P21-HC-16K-LIFECYCLE-20261029.md)。

## 真实边界

- actual executed T与输入长度分开；16K输入不保证执行16K块。覆盖1、奇数尾、真实4096边界、实际16384块和最后短块。
- KVRES跨resident阈值、4cell页边界、epoch pin、slot eviction、图地址复用。
- 短→长→短、A→B→A、取消后下一请求、错误后重入、graph destroy/recapture、loan归还。
- 先已有redzone/poison与小scope memcheck，按候选风险选最小必要覆盖；只有改变异步内存生命周期才扩大sanitizer范围。
- 为memcheck使用的诊断资源/加载/managed memory配置必须单独命名，不能进入正式性能臂。

## 六项FAIL与质量门

固定长检索FAIL仍为FAIL。P8独立llama.cpp与P9较高精度对照只是排除了部分引擎/格式解释；不证明基础模型无错，不证明量化无影响。无权重/资源做更高精度独立对照时保留未解决，不下载一个放不下的模型作为必做项。

相对非劣使用原 `tools/quality_gate.py`：独立任务对四格a/b/c/d，保守上界`CP_upper(b,n,.025)−CP_lower(c,n,.025)≤.02`。多seed、多轮、多token不是独立新任务。30对全一致无法建立2pp非劣；全一致时183对才达该公式门槛。这只是此公式边界，不是通用样本量建议。

两臂都错也可能相对非劣，所以绝对质量单列。原六FAIL不解决时可以报告“E0数值支持”或“性能门研究通过”，不能报告总体质量合格、可生产采用。正式留出集成本过高则 `INSUFFICIENT/BLOCKED_QUALITY`，不能放宽2pp或换轻题。

来源：[质量工具规范](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/tools/QUALITY_GATE_README.md)、[P3](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P3-COMBINATION-KVRES-20261027.md)、[P8](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P8-INDEPENDENT-LOGITS-20261028.md)、[P9](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)。

## Speculative特殊合同

greedy下证明target验证与rollback正确，不足以证明temperature1的采样分布正确。若改proposal、树结构、接受或残差采样，必须明确target分布p、proposal分布q、接受`min(1,p/q)`及拒绝后的残差，或证明现有算法的等价耦合；不得只比较一批输出看起来相似。维护每分支KV/GDN/PLE/position和提交状态，一次拒绝必须完整回滚。

这是方案验收要求，不能假设当前Strata/Maya所有spec策略已经实现同一种数学验证。先审计实际算法，再决定是否适用。原target tail-skip行为也必须冻结，不用“同GGUF”偷换成全计算target。

## 布局变化的canonical比较域

E0允许物理布局改变，因此逐字节比较应先还原到相同逻辑坐标：`(layer, logical_token, head/expert, row/column, K/V或state角色)`下的有效值、scale和提交位置。canonical IDs、query cell顺序、valid/causal mask、token/scatter顺序也必须独立比较，防止“值没变但行错位”。物理cache slot编号、padding、临时span与重排metadata按映射/所有权合同核查，不强求物理buffer整体memcmp相同。

保留Dm只支持一个局部布局假说。释放scratch若改变natural chunk、CPU/GPU归属、MMQ group/shape或规约，必须分别报告固定路径E0和自然路径结果；后者按实际变化重新分级，不能由局部oracle自动提升为整机E0。
