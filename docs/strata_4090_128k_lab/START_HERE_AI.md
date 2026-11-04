# Strata 当前执行入口

保留 Qwen Next v0.2.3，生产已恢复。[v0.2.10 PT0 与三组版本配对](reports/V0210-PT0-VERSION-COMPARISON-20261104.md)记录 CPU 适配、6 次引擎启动和 12 次请求。两条 Pi 会话未观察到复用损失，暂不移植 #1536。同输入暖态生成减速，两版两轮任务均为 0/3，不切换生产。

以下为历史批次，服务状态以各自记录时间为准。

D1U 完成 n2300 的一次原路径逐层捕获。中立性三次前向逐 bit 匹配 D1S。只替换 context `hidden_norm` 的 Q/D，CPU 第 4 项由 `212522` 变为 GPU 的 `209087`，七个 token 均匹配。已定位因果边界，未证实可单点修复的缺陷。按补丁门停止候选，第二个 GPU 程序未运行。原 FAIL 和参考保留，D1 未通过，D2 未开始，生产保持停机。 [D1U 执行回执](reports/DF01-D1U-N2300-CAUSAL-STOP-20261103.md)。

**仅携带一个文件或无法访问29时**，使用[完整离线Handoff](handoffs/DFLASH2_DRAFTER_TOKEN_CPU_GPU_MISMATCH_HANDOFF_20261102.md)。文件内实际包含151项可提取资料及关键源码全文，不把workspace路径当依赖；正文明确完全离线能力、可选CPU依赖/公开权重恢复及缺失真值。该文件的证据截点为 D1T。D1U 逐层原件单独封存。

较早为[DF01/D1T停止回执](reports/DF01-D1T-FINAL-CPU-STOP-20261102.md)与[Astra唯一终审](reports/DF01-D1T-ASTRA-REVIEW-20261102.md)。D1T完成最后一轮纯CPU审计及唯一一次Astra xhigh终审。冻结CPU尾部逐bit复现；同GPU行CPU尾部7/7匹配，最大概率差6.71e-7，确认前向行差经相同尾部导致候选排序翻转。首个错误算子和最终根因仍未定位，无可证实单点修复；按用户要求STOP_CANDIDATE，停止当前DFlash2候选排查与后续测试。原FAIL/参考/硬门保持，D1未通过，GPU/完整backbone/生成0，D2未开始，生产继续停机。 没有自动后续动作，不按旧预算或旧CPU定位建议继续。首次Python缺NumPy的启动失败保留，改用原CPU解释器后只做一次数值重放，不安装依赖。

较早为[DF01/D1S v2执行回执](reports/DF01-D1S-V2-QUALIFICATION-20261102.md)。D1S绑定冻结v2后执行1个GPU程序、4组夹具、0生成。n32/n2048/n2064通过v2 drafter硬门；n2300为6/7 token一致，第4项实际209087、参考212522，selector token 3触发exit1后停止。置信度差只作诊断，原token门及其余硬门不改。后12组和六次生成未运行，无重跑/替补，GPU窗口2.119秒。原FAIL/原四组参考保持，D1未通过，D2未开始，生产继续停机。 20:04:38生产inactive/dead，13保护SHA与1122冻结身份、1104历史/源文件保持。根因未确认；当前按停止条件收口，不使用剩余额度，不自动修改参考或继续GPU。

较早为[DF01/D1Q适配回执](reports/DF01-D1Q-V2-ADAPTER-20261102.md)。D1Q完成v2最小分类适配及CPU检查。仅完整drafter置信度绝对差为诊断；原行/token、概率有限值/范围、独立selector、target采样、提交状态和EOS硬门保留。原四组参考及旧FAIL不改，独立GPU程序只编译/链接，GPU/完整模型前向/生成0。最终身份为FINAL_FREEZE.json，D1命令为COMMANDS_V2.json，全部execute=false；D1未放行、D2未开始，生产继续停机。 CPU 29项分类、原表达式9项、状态10项、host采样201项、EOS三正例/两负例及两组保存原件回放通过；这些检查不替代GPU验收。下一步只有另行授权的新GPU批次，须绑定最终清单和新预算；不得沿用旧未用额度。

较早为[DF01/D1P合同复核](reports/DF01-D1P-EXACT-MATCH-CONTRACT-20261102.md)和[后续D1 v2合同](plans/DF01_D1_EXACT_MATCH_V2.md)：仅在冻结默认exact-match路径中，将完整drafter置信度绝对差≤0.05改为诊断；独立selector概率、原行/token、target采样/提交状态/EOS及资源硬门保持。104976组有限模型比较、三负例及源码身份核对通过，GPU/模型前向/生成0。原FAIL与冻结参考保持；旧GPU程序和runner未改，v2适配未实现，GPU硬门未运行，D1未放行、D2未开始。17:23:28生产inactive/dead，13保护SHA及1037历史/源文件一致。下一项仅为另行授权的v2最小适配/CPU负对照准备，不可忽略旧exit1后开跑；生产继续停机。

较早为[DF01/D1O CPU审计](reports/DF01-D1O-N2048-CPU-AUDIT-20261102.md)：本轮GPU/生成0，Astra xhigh同GPU rows尾部重算最大误差4.77e-7，排除尾部为原0.0799差异来源。来源顺序RMS/RoPE/分块attention组合使n2048单保存夹具满足原门（maxp差0.0386763），但n32同实现回归失败（0.0853075）；不采用统一新参考，不按context挑规则。四次CPU完整前向及原C++比较器结果、候选正负结果全部保留。首个n2048偏离算子未确认；16:58:27生产inactive/dead，968历史/源文件和13保护SHA一致。原D1N FAIL/gold保持，D1继续阻断，D2未开始；停止继续CPU组合或GPU，生产保持停机。

较早为[DF01/D1N补验](reports/DF01-D1N-REMAINING-QUALIFICATION-20261102.md)：四组CPU参考在14分52秒内冻结；n32逐byte复现D1M，四组输入前缀不变，原比较器正/负例通过。新GPU实际1程序/2组夹具/0生成，n32回归PASS；n2048第2项概率差0.079903543超原0.05，按门停止。后14组与六次生成未运行，无重跑/补样本。D1继续数值资格阻断，不进入D2，生产保持停机。不得沿未用额度继续诊断、修改参考或执行生成。原FAIL/gold及D1M单夹具结论保持。

较早为[DF01/D1M CPU收口](reports/DF01-D1M-CPU-REFERENCE-CLOSURE-20261102.md)：GPU/生成0，基于现有逐层原件修正CPU卷积与planar整数GEMM算术顺序。原首组保存的GPU观察值对独立CPU参考，token7/7一致，最大概率差0.0451068，原C++比较器和三个负例控制通过。Astra xhigh独立复核接受单夹具离线边界。旧FAIL与gold保持，完整D1仍未完成，其他资格夹具/target-state/六次生成未运行；D2未开始。633历史/源文件及13保护SHA一致，15:46:03生产inactive/dead，保持停机。CPU修复闭合本轮问题后停止，不自动GPU或继续追逐逐bit一致。

较早为[DF01/D1L逐层定位](reports/DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)：1 GPU程序/原首组1夹具/0生成、无重跑，323项逐层记录与D1R最终输出逐bit一致。Astra xhigh独立核实首个实际Q码错误：CPU `127/tensor`实际reciprocal→multiply，位置22/特征1928为60而GPU59；最小改为真除，保留zero/scale/RN-even/head，5项CPU检查通过。首项概率误差0.00491863、token5/7，最大误差0.0718193仍失败，D1不放行。334历史/源文件和13保护SHA一致；生产保持停机，D2未开始。GPU额度已用完，后续可复用现有逐层原件做CPU核对，不自动启动。

较早[DF01/D1R单夹具诊断](reports/DF01-D1R-SINGLE-FIXTURE-20261102.md)：用户授权最多1 GPU程序/原首组1夹具/0生成/60分钟，实际1/1/0、无GPU重跑。原门复现失败：实际概率0.787050843、参考0.734110057。实际行和尾部原件完成；同GPU行CPU重算7项token全匹配，概率最大差6.56e-7。差异来自drafter前向行数据，首个偏离算子仍未确认。可确认CPU算术顺序/漏量化问题修复并验证，完整差异未消除，不替换冻结金标。D1继续BLOCKED_NUMERICAL_ORACLE，不进入D2。14:33生产inactive/dead，13保护SHA及289历史/源文件SHA一致；保持停机。唯一GPU额度用完，不重跑原run。

较早[DF01/D1C CPU审计](reports/DF01-D1C-CPU-ORACLE-AUDIT-20261102.md)：用户授权CPU审计/修复，并停止原v0.2.3直到另行要求恢复。11:30停机，11:46复核inactive/dead、MainPID0，无GPU计算进程、18343/18089无监听。13保护SHA及226历史/源文件SHA一致。概率定义相同、四组28项CPU概率差0；修复head同值排序与失败诊断缺失，CPU验证通过。原GPU实际值缺失，唯一根因仍未确认；原D1 BLOCKED_NUMERICAL_ORACLE不变。新资格binary只编译/链接，GPU追加0，不进入D2。

较早[DF01/D1失败回执](reports/DF01-D1-QUALIFICATION-20261102.md)：用户授权D1、临时停生产，限两项GPU程序/16夹具/六次生成/60分钟。首组drafter-n32在selector probability 0失败，实际1项GPU程序、1组失败、0次生成；后15组和六次生成NOT_RUN。当前BLOCKED_NUMERICAL_ORACLE，不进入D2，不补样本。11:16原v0.2.3恢复，11:17独立复核健康、13保护SHA、argv/环境一致。性能和质量仍未验证。

较早[D0B回执](reports/DF01-D0B-CPU-READY-20261102.md)保留CPU_preparation_ready=true；不将CPU准备通过改写为GPU资格通过。

原[DF01/D0回执](reports/DF01-D0-PREPARATION-20261102.md)保留BLOCKED_PREPARATION及5947/81-token样本，原六FAIL、P05和旧关闭结果不变。新构造代码输入明确区分于Pi投影；具体执行仅使用D0B最终预登记清单，不扫描命令目录运行全部case。

上一轮[U01R1版本对比](reports/U01R1-VERSION-COMPARISON-20261031.md)：计数修复后按新授权完成3组/12请求，无重试或替补。编码两版3/3、工具A3/3/B2/3，未见稳定升级优势，不建议继续完整升级验收或切换生产。17:39原v0.2.3恢复、13保护SHA匹配。当前没有待执行GPU任务。

上一轮[U01失败](reports/U01-VERSION-COMPARISON-20261031.md)的2请求、10个NOT_RUN、原源码及USAGE_DRIFT保留；没有将其并入本次配对或重标PASS。

先读[下一步行动计划](plans/NEXT_ACTIONS.md)和[Astra复核与收口报告](reports/FRONTIER-CLOSURE-ASTRA-20261031.md)。当前冻结合同下NO_QUALIFIED_CANDIDATE，本轮已收口；撤回优先推进F02的建议，F02保留DEFERRED_NEW_EVIDENCE。P01/P01B/F03历史终态保留，P05 BLOCKED_EVIDENCE及六FAIL不变。生产随后按用户要求[恢复运行](reports/PRODUCTION-RESTORE-20261031.md)，该次恢复的GPU占用属历史；D1U 停机回执为后续历史状态。

## 权威与读取顺序

1. [合并记录](reports/DOC-MERGE-20261030.md)：先区分当前现场复核、作者历史研究、未完成准备。
2. [frontier AI 合同](frontier/START_HERE_AI.md)：只读当前阶段与直接依赖，十二张方向卡是条件分支。
3. 原实验事实以 `reports/` 和对应 `workspace/` 原件为准；生产保护和运行资源规则沿用本目录 `AGENTS.md`。frontier/sources/LOCK.json 冻结后续 P6 研究身份；根 sources/LOCK.json 保留 A0 历史身份，两者角色不同。
4. 工具继续使用根目录 `lab/`、`tools/`。frontier/tools只含离线计算器；根tools/frontier已实现P01最小live adapter，实际本轮已停止，不能重复原run。只有明确授权执行对应阶段时，才进入工具开发或目标机负载。

## 当前停止点

- Astra复核：2026-10-31已完成；旧profile最大单格式条件成本2.22%/2.13%，无已证load/layout新机制。取消原拟四小时F02审计，不改选另一卡，不追加GPU；不外推全局NO_GAIN。
- frontier/P00：已完成；身份/来源/请求/离线接口和独立门见P00报告及PHASE_GATE。无需重建已匹配P6。
- frontier/P01：已执行，103183token prime输出941后按门停止，两append NOT_RUN，结果INSUFFICIENT。原件和执行源码保留；不自动重跑。
- frontier/P01B：2026-10-31独立新合同已执行COMPLETE；完整host窗口/原始IDs已采集，窄host间隙不足4%，其他GPU/CPU内部依赖未知，候选资格INSUFFICIENT。本批次关闭。
- F03 CPU审计：2026-10-31已完成；合法旧快照保留，同步零填原型三对CPU均慢6.08%–7.74%，无合格候选，不追加GPU。
- frontier/P02及以后：当前不进入候选开发。未来重开须有独立新机制、当前真实暖态命中与可闭合依赖、可信方案及新增成本账支持完整请求净省时≥4%，并明确后续执行范围；缺证据不自动触发新采集。
- frontier/P05：目前缺稳定 warm fixed2048 原件，BLOCKED_EVIDENCE；P24 的 5-token append 不能替代。诊断完成不会自动解除该门。
- 原六 FAIL 不变；性能研究通过不等于生产采用。

## 历史入口

原 [AI 执行说明](history/START_HERE_PRE_FRONTIER_20261030.md) 和 [HC 续测合同](history/CONTINUATION_20261029.md) 仅供追溯。旧自动续测 PAUSED、旧 reset 授权到期；不沿其候选顺序继续开跑。
