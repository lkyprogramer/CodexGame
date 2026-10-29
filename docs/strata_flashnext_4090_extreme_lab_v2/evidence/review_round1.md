# 独立设计审阅 Round 1

审阅时间：2026-10-25。范围：`output/strata_flashnext_4090_extreme_lab_v2/docs/` 当前10份文档，共490行。只读审阅，未修改被审文件；64方向catalog、完整plans、最终工具实现尚未纳入本轮。

结论：**机器/版本/授权主线可靠；建议先修4项验收定义问题、4项统计或模型表达问题，再交给执行者。** 下述是文档设计问题，不是已经观察到实现出错；后续脚本若已有正确处理，应把规范补成与代码一致。

## 已核实正确，勿在后续修订中改错

1. `01_MACHINE_AND_PROGRESS.md` 使用最新部署报告覆盖旧入口，生产已是A0+EXACT6、performance+C6 off，perf已安装；与 `DEPLOY-A0-EXACT6-20261025.md` 相符。两DIMM/36GB/s、偶奇层真实格式、POOL8失败和Q2_0旧bench调用错误均正确。
2. `02_LATEST_BASELINE_DELTA.md` 对 `STRATA_ADAPT_OVERLAP=1` 已排除 **new auto async** 的陈述正确。实际 `adapt_async_self_decides()`明确 `if (a.adapt_overlap) return no("STRATA_ADAPT_OVERLAP")`。本轮**没有**发现“baseline升级后会自动混入new async策略”的错误；13文档的conditional effective-mode记录也不应被误判成这个错误。
3. AVX512-VNNI、AVX-VNNI与VBMI分开，且不允许只删CPUID门控，正确。4216特定TU隔离和SASS/反汇编检查仍需保留。
4. 本地运行 `git diff --name-only 5c8dd322… 41cf05a0… -- src/kernels/cuda src/prefill src/kernels/cpu/pool.cpp` 返回空，支持02文档该处事实。03文档源码地图中列出的15个具体路径均实际存在。
5. Amdahl表三个数值计算正确；历史20GB/s明确是粗估，未包装成硬件测量；没有编造4090最终速度。
6. E/N/Q/X分类本身可成立：N允许数值精度变化，Q保留模型/请求语义变化。无需为了沿用donor报告的E0/E1/Q标签而强行重分类；但最终汇总不得把通过2pp任务非劣的N称为逐位无损。
7. 授权边界未发现实质越权：无自动停生产、修改systemd或杀外来进程；复用既有授权，不重复批准只读动作，正确。隔离port/tree不等于GPU资源隔离，13已经禁止其它服务并发，执行计划应继续落实。

## 必须修正

### R1 — “失败都阻止采用”与任务质量非劣逻辑冲突

**优先级：高。位置：14_STATISTICS_AND_SELECTION.md:28；12_NUMERICS_AND_QUALITY.md:31、40–42；13_BENCHMARK_PROTOCOL.md:46。**

14第28行把“重复、失败、OOM、timeout……”一概写成阻止采用。12同时要求保留真实生产已有失败、报告paired四格，并允许任务级非劣；Q-JAVA还明确编译失败计任务失败。若执行者把所有`success=false`都当无效run，基线本身的模型失败会使所有候选永远无法采用；若为求通过删除失败，又造成选择偏差。“不可比输出”也不能包括N/Q正常产生不同但可评分的代码。

**修正建议：**明确至少三类结果字段：

- `run_valid`：完成回执、资源/配置身份、日志完整、协议是否有效。缺失、配置漂移、工具崩溃等使该比较BLOCKED/INSUFFICIENT。
- `task_success`：模型答案是否通过oracle；false仍是有效质量观测，进入全部四格和预定任务时间规则。
- `failure_kind`：区分环境/基础设施timeout与模型达到任务时间预算；后者是有效的任务失败。OOM/引擎异常可设为硬退回门，但要明确不是普通oracle失败。

建议把该句替换为：“基础设施失效、身份漂移、缺失或不可验证记录阻止采用；模型任务失败保留为有效观测，按质量非劣与预注册时间规则处理，不删样本。”

### R2 — spec速度公式会重复计算stall，且token分子需要包含target补充token

**优先级：高。位置：04_BOTTLENECK_MODEL.md:45–51。**

公式用 `draft + verify + commit + stall`。现有Strata verify wall已经包含CPU专家等待及部分同步；照phase日志代入会把stall计算两遍，违反03文档正确强调的嵌套口径。另“本轮真实接受输出token”若落到`draft_accepted`字段，漏掉target bonus/correction token，spec0轮甚至会被记成0收益。

**修正建议：**生产策略目标直接使用

`effective_tps = sum(committed_target_tokens_including_bonus) / sum(round_wall_seconds)`。

`draft_accepted`、proposal count、target bonus各自单列诊断。只有phase timer明确互斥、不重叠且覆盖round边界时才允许求和；否则各phase只用于归因。动态round成本用总tokens/总wall，不平均每轮的tokens/ms比值。

### R3 — 主指标“正确完成wall time”尚未定义失败/超时的估计量

**优先级：高。位置：00_SCOPE_AND_DECISIONS.md:7；04_BOTTLENECK_MODEL.md:5；13_BENCHMARK_PROTOCOL.md:9；14_STATISTICS_AND_SELECTION.md:24。**

文档已禁止丢失败，但未规定无法正确完成的任务如何进入主时间指标。“只对成功任务平均wall”会使做错慢任务的候选显得更快；“只取两臂都成功交集”也改变估计对象。质量差异在2pp容忍内时仍可能出现这种速度选择偏差。

**修正建议：**在campaign中冻结一个可计算的主估计量，并另报完成率。例如每任务固定时间/重试/token预算，成功记time-to-success，未成功记预定budget上限，形成restricted time-to-success；同时披露成功率、超时比例和未惩罚的条件成功延迟。也可采用明确的联合完成率/时间规则，但不能靠执行者事后选择。基础设施失败依R1处理，不冒充模型超时。

### R4 — 2pp非劣没有规定区间算法，朴素bootstrap可错误输出PASS

**优先级：高。位置：12_NUMERICS_AND_QUALITY.md:38–42；14_STATISTICS_AND_SELECTION.md:38。**

“任务级95%区间”不足以唯一实现。若30个paired任务全部concordant，直接bootstrap observed paired差值会得到退化的`[0,0]`，从而误称已经排除2pp退化；实际上未观察到新引入错误并不证明其总体概率为0。文档把30项写成筛查并允许INSUFFICIENT是正确的，但必须阻止实现使用上述退化区间认证非劣。

**修正建议：**冻结 `delta = p(candidate_success)-p(base_success)`、检验方向、置信水平和paired二项风险差的区间方法；正式非劣判定为相应下界不低于`-0.02`。任务与多seed重复按task聚类，不能当独立任务。可以选保守的paired score/exact方法；若采用bootstrap，必须有小样本/零discordance保护，不能输出虚假零宽区间。

说明性算例：若独立任务中0/30次出现“仅基线成功”，该harm事件率的单侧95%精确上界为 `1-0.05**(1/30)≈9.50%`。这是帮助理解样本规模的保守示例，不是规定所有非劣试验都必须149题，也不替代完整paired风险差计算。

## 统计/模型表达应补齐

### R5 — ABBA、进程块和bootstrap统计单位没有一一对应

**优先级：中。位置：13_BENCHMARK_PROTOCOL.md:20–23、40；14_STATISTICS_AND_SELECTION.md:22。**

“每块启动独立引擎”与“顺序ABBA/BAAB”存在两种读法：一个块是一个process，还是包含A1/B1/B2/A2四个process的macroblock？最小字段只有round/arm/case，没有配对块与process身份，无法可靠恢复依赖结构。若A/B使用不同进程，不能在单进程块内部配对。

**修正建议：**采用一个明确例子：`paired_block_id`下按ABBA或BAAB启动四个独立`process_instance_id`，每process固定warmup+case_order；同一paired block内先聚合A的两个重复和B的两个重复，再计算paired结果，bootstrap重采样paired_block。记录`order_position`、`replicate_id`、seed、warmup/profile reset身份。另一种配对设计也可，但文档和工具必须同定义。

screening的5块可以保留；正式holdout的块数/停止规则需在解盲前冻结，不能默认5块就能得到可靠最终95%区间，也不能每增加一块就查看显著性并在首次PASS时停。

### R6 — 次要场景退化与“正确性修复性能不劣”的判定缺置信口径

**优先级：中。位置：14_STATISTICS_AND_SELECTION.md:34–37。**

主速度门明确CI上界≤0.97；但关键非目标场景“退化≤3%”未说明是点估计还是区间上界，正确性/缓存修复例外中的“性能不劣”也无容忍界和区间。不同执行者可能在同一数据上给不同采用结论。A/A“典型偏差”也未定义，无法执行max规则。

**修正建议：**冻结主/次指标、点估计、paired CI方法、退化边界、硬门与探索性指标。若采用稳健政策，可将关键次场景的时间ratio单侧上界≤1.03；正确性修复另定可接受时间边界。A/A典型偏差明确为例如宏块ratio的某个分位/绝对偏差，不能每次换算法。p99 1000请求下限只作资格下限，已有“仍需聚类区间”应保留。

### R7 — 简化层模型与18.5/6.2ms示例还需明确未被覆盖的critical-path假设

**优先级：中。位置：04_BOTTLENECK_MODEL.md:7–13、31。**

`max(T_gpu,T_cpu,T_transfer→gpu)`若第三项只指copy，遗漏同一cold expert的H2D→GPU compute串行依赖，且resident与cold GPU工作可能竞争同一执行资源。虽然下一段已经要求用DAG，这个公式仍容易被直接实现成分配器。18.5−6.2+6.2×20/36不仅要求6.2ms受带宽限制，还要求这6.2ms全部是缩短后可转化为round收益的未隐藏关键路径；CPU阶段时间不能自动满足该条件。

**修正建议：**定义第三项为“copy后执行的完整GPU分支，并包括GPU资源调度”，或者直接写`T_l = critical_path(layer_DAG)`并将max公式限定为独立分支的玩具模型。Amdahl条件例明确再加：同一运行口径、同一tokens/window、6.2ms完全未被其它工作覆盖、其它工作和驻留不变。算术本身正确，不需要删除有价值的条件示例。

### R8 — “所有arm相同…”需为明确处理变量留出口

**优先级：中低。位置：13_BENCHMARK_PROTOCOL.md:34；02_LATEST_BASELINE_DELTA.md:15–19；00_SCOPE_AND_DECISIONS.md:33–35。**

13写所有arm相同EXACT6、governor/C-state、sampling、template、MTP、context。对普通kernel候选应如此，但后续spec/drafter、MTP量化、资源配置或X实验会以其中某项为唯一处理变量。若照字面执行，会拒绝合法实验或产生未声明的例外。

**修正建议：**改为“除实验卡预先声明的处理变量外，所有arm保持……相同；处理变量必须进入config diff、分类与资格检查”。这不是授权扩张；生产停机、host/driver/启动链变更仍按现有权限边界处理。当前baseline的ADAPT_OVERLAP继续固定，研究async必须是独立arm，不是迁移副作用。

## 待最终交叉核验

- 64项catalog的E/N/Q/X标签、score、依赖和已NO_GAIN历史是否与本文一致。
- 计划中的campaign schema、缺失检测、block bootstrap与paired非劣实现能否逐项执行R1–R6。
- GPU独占锁、外来PID判定、只结束自有进程、生产维护授权是否落实到runner而不只存在文档。
- 主README/总结是否把N/Q不同质量契约混成“无损极限速度”；donor里的dense27B、sm103/120、AMX是否均有明确排除。
- 当前19文档引用的根`VALIDATION.md`在本轮审阅时尚未出现；这是进行中的生成状态，不在此判缺陷，最终封包前需核实链接和声明的测试数量。

## 本轮核验记录

- 读取全部10份docs；检查行号与跨文档矛盾。
- 读取附件最新部署报告与CFG报告；重核EXACT6、C6/performance、perf、POOL8等历史信息。
- 检查`adapt_async_default.hpp`的实际排除条件。
- 运行固定两SHA之间指定源码目录diff，返回无变化。
- 核对03源码地图15个文件路径，全部存在。
- 未对用户机器运行命令，未声称任何新性能或数值门通过。
