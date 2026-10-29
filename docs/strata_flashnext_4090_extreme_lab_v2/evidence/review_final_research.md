# 最终只读交叉审阅：research / plans / catalog

日期：2026-10-25。审阅范围：主包`REPORT.md`、`config/directions.json`、P00/P02/P09/P11/P12，及已交付P03/P04/P08/P10；为核对接口实际覆盖，抽读`lab/{cli,runner,corpus,statistics,java_eval}.py`、`tools/quality_gate.py`/README和Strata固定源码。未修改主包；未执行GPU、模型、服务、系统维护或扩展新研究。

## 结论

没有发现需要推翻整体路线的硬件事实、Amdahl数值或latest版本错误。建议在最终封包前解决下列R1/R2；R3补齐发布决策边界。另有一项小范围表述/归属整理，避免以后实施者重复工作。

当前正确且应保留：

- `sources/LOCK.json`最终base为`4b9e05a2a806a3fe24f7b2560d98626c37dade35`，release v0.2.6；明确Qwen包仍0.1.50，Control/DeepSeek/project CMake为0.1.51。四份额外计划保留41cf实现锚并追加freshness，不存在把Qwen包错写0.1.51的冲突。
- baseline `ADAPT_OVERLAP=1`排除autoasync，不把旧生产自动混策略当事实；CPU明确无VBMI/AMX，没有从AVX512-VNNI推导AVX-VNNI。
- P03/P04/P08已把lookahead、DraftPolicy、suffix索引、VMM、kv-grow、q4_0/k8v4列为已有能力。catalog相关O11/O27/O29/O33/O44/O46/O47已经对应纠正。
- REPORT Amdahl示例计算正确；18.5/6.2ms的17.5%被明确限制为有前提的估算，不是4090实测。int8QSA约1.547GiB被标理论布局，不是实时分配。
- P00-06、P02-06、P12和REPORT明确正式任务adapter/性能分析器尚未实现；现stats与quality_gate分开，后者不会运行模型。以下R1是局部顺序措辞仍可能冲掉这个全局界限。
- E/N/Q/X、PR2964当前不适用、EAGLE许可、GPU unlock微测不等于应用收益、zapabob撤回placeholder资格都与四计划一致。

## R1 — 高：P00-03的“通过条件”超出现有MIG命令能力，应拆初筛与正式基线资格

**位置：** `plans/P00_BASELINE_AND_MEASUREMENT.md` P00-03（审阅时L28–41）；对照P00-06（L63–74）、`lab/corpus.py::body/build`、`lab/runner.py::campaign`、`lab/statistics.py::summarize`。

P00-03给出`corpus --suite full`和`mig --execute --corpus ...`后，紧接要求“greedy与真实sampled-thinking、8/32/64K……分别报告”及“协议/状态/质量门合格”。实际corpus `body()`固定`temperature=0`、`enable_thinking=False`、`reasoning_effort=none`；full的长ledger目标为4096/32768/65536/98304/122880，并非真实sampled-thinking或真实Pi任务。现MIG为该corpus的两臂重放，stats是严格smoke，正式state adapter、restricted-time和质量任务仍在P00-06/07待实现。

**风险：** 按章节顺序执行的AI可能在P00-03完成现成命令后就标`BASELINE_READY`，将后面的adapter任务当可选增强；也可能误以为`--suite full`代表正式全协议/任务非劣。代码本身未伪造NI；是本节资格范围不够明确。

**最小修正：**

1. P00-03改名“最新基线初筛（现有MIG）”，明确现成命令只给`MIG_SMOKE_PASS`/初筛回执。
2. 将sampled-thinking、真实Pi、8K新增case、park/restore state和正式NI列为“P00-06/07完成后的正式资格矩阵”，不得由当前`full`语料自动覆盖。
3. `BASELINE_READY`总回执拆`smoke_ready`与`formal_quality/performance/state_ready`；未实现的adapter保持`NOT_RUN/BLOCKED`，不能总PASS。

此修正不要求现在实现adapter，也不阻止已经可做的初筛。

## R2 — 中高：O51存在悬空计划归属，P11缺前缀编辑多级recurrent checkpoint任务

**位置：** `config/directions.json` O51；`P08_KV_AND_MEMORY.md` Spec把O51委托P11；`P11_COPY_AND_STATE.md` scope（L3）只列O13/O30/O37/O41–43/O45，现有6个任务中没有O51。

P11-05的ReplaySSM针对verify reject/commit回滚，不能自动代替O51“长前缀中间编辑时，从编辑前最近完整checkpoint恢复并重算剩余”的问题。两者checkpoint位置、保存频率、存活周期与资源代价不同。

**风险：** catalog显示O51有实施计划，但执行者无法得到中间编辑恢复合同；若误拿KV前缀重用替代GDN/conv/MTP历史状态，会产生错误结果。当前P11没有直接指示错误实现，但交付覆盖缺口需要补齐。

**最小修正：** 在P11增加O51任务，至少包括：

- 先测真实edit位置/频率与可避免prefill量；无复用价值就NOT_APPLICABLE。
- checkpoint以明确token位置和model/tokenizer/template/state-format身份定位，完整保存GDN/conv/MTP及所需KV前缀/metadata。
- 编辑位置之前的最近合法checkpoint可用，之后所有受影响状态失效；从checkpoint重放真实修改后的token到当前末尾。
- checkpoint数量/bytes/保存带宽设界，接P08/P02预算，不能把每一页KV都配一份完整recurrent状态而不计RAM。
- 测edit在checkpoint前/恰好/后、多个编辑、state版本不符、取消/失败回滚、恢复后继续spec；E时用同算术reference，N改动另行质量门。
- 无净prefill节省、保存/restore竞争更大则退出。

若本次不补，明确将O51标“待设计/研究”，取消“详细计划已覆盖”的暗示即可。

## R3 — 中：P12应显式接上quality_gate不负责的绝对质量资格

**位置：** `P12_HOLDOUT_AND_RELEASE.md` P12-02；`tools/QUALITY_GATE_README.md`末段及`quality_gate.py`输出。

quality_gate正确声明`absolute_quality_gate=NOT_EVALUATED`，两臂都失败的足够多任务也可能相对NI。P12-02已正确要求真实oracle和NI、性能、资源，但没有一句明确要求检查绝对功能质量/项目必过项或解释baseline本身的失败；读者容易把这个联合清单当全部发布资格。

这不是NI公式错误，不建议修改工具为“任何baseline失败都拒绝NI”。建议给P12加独立条款：正式采用前冻结关键功能必过项/绝对可用性要求，报告base/candidate的绝对完成率和关键失败类型；NI_PASS不填写总体`QUALITY_PASS`，尚无绝对质量判定时发布回执保持未完成。允许用户明确接受的Q质量换速应单独签署具体Pareto选择，不能由相对NI自动替代。

## R4 — 中低：P11应先沿用现有单owner分段复用，避免直接升级到共享/COW；并整理O61归属

**位置：** `P11-03`（审阅时L27）；O41 catalog；固定源码`include/strata/core/conversation_buffer.hpp`与`src/core/conversation_snapshot.cpp::conversation_kv_save`。

catalog已正确写“保留已存在16MiB段与unchanged-prefix复用，只补真实dirty范围”。P11-03却直接提出“拟新增segment version/refcount和dirty map”，没有先确认缺口。当前`ConversationBuffer`注释明确parked image与retained active buffers为单owner、无需sharing/COW，已有分段和append不迁移payload。新增跨快照共享/refcount可以是独立候选，但属于所有权结构变化，不能当已有增量快照的必要实现。

**建议：** P11-03先增加一段“已有单owner16MiB分段与unchanged前缀保存→测剩余copy→只有跨快照重复不可避免时才试共享/refcount”，保留owner合同和回退。文中“quant KV本来已低熵”改成“已低比特，熵和可压缩比待实测”，低位宽不推出低熵。

O61 catalog指P11，但P02自述也覆盖O61，P09-04承载host/allocator/NUMA具体叙述，P11 scope未列。不是阻断缺陷，建议固定一个owner计划，其他写依赖链接，避免重复线程/allocator实验。

## 不作为错误的构建中事项

审阅开始时主包尚未拷入4份额外计划，`VALIDATION.md`也尚不存在；root已说明正在并行封包，因此未把这两项记为交付错误。最终manifest/链接完整性由封包自检确认。

本报告只提出上述具体校正，没有追加新donor、无界研究或实际实现要求。修正后的版本若保持现有严格smoke/NI边界和新的执行锁，即可进入最终封包检查。
