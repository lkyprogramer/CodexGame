# Strata · RTX 4090 / 128K 实验主目录

2026-10-30 已将 GPT Pro v3 后续方案并入 `frontier/`。本目录继续作为唯一实验主目录；历史结果和执行工具原位保留。2026-10-31经Astra复核，当前冻结合同下零合格候选，本轮已收口；不沿旧计划继续探索。

## 当前结论

- [v0.2.10 PT0 与三组版本配对](reports/V0210-PT0-VERSION-COMPARISON-20261104.md)完成。保留 Qwen Next v0.2.3，暂不移植 #1536。冷读首字延迟中位改善 2.7%，同输入暖态生成速度下降 14.5%。两版两轮任务均为 0/3。生产已恢复，NGINX 冒烟通过。

## 历史结论

- [v0.2.10 DFlash2 发布版评估](reports/DFLASH2-V0210-READINESS-20261103.md)记录当时的源码核查与只读计划。原 D1 FAIL 保留。

- D1U 完成 n2300 的一次原路径逐层捕获。中立性三次前向逐 bit 匹配 D1S。只替换 context `hidden_norm` 的 Q/D，CPU 第 4 项由 `212522` 变为 GPU 的 `209087`，七个 token 均匹配。已定位因果边界，未证实可单点修复的缺陷。按补丁门停止候选，第二个 GPU 程序未运行。原 FAIL 和参考保留，D1 未通过，D2 未开始，生产保持停机。 [D1U 执行回执](reports/DF01-D1U-N2300-CAUSAL-STOP-20261103.md)。

- [DF01/D1T停止回执](reports/DF01-D1T-FINAL-CPU-STOP-20261102.md)及[Astra唯一终审](reports/DF01-D1T-ASTRA-REVIEW-20261102.md)：D1T完成最后一轮纯CPU审计及唯一一次Astra xhigh终审。冻结CPU尾部逐bit复现；同GPU行CPU尾部7/7匹配，最大概率差6.71e-7，确认前向行差经相同尾部导致候选排序翻转。首个错误算子和最终根因仍未定位，无可证实单点修复；按用户要求STOP_CANDIDATE，停止当前DFlash2候选排查与后续测试。原FAIL/参考/硬门保持，D1未通过，GPU/完整backbone/生成0，D2未开始，生产继续停机。

- [DF01/D1S v2执行回执](reports/DF01-D1S-V2-QUALIFICATION-20261102.md)：D1S绑定冻结v2后执行1个GPU程序、4组夹具、0生成。n32/n2048/n2064通过v2 drafter硬门；n2300为6/7 token一致，第4项实际209087、参考212522，selector token 3触发exit1后停止。置信度差只作诊断，原token门及其余硬门不改。后12组和六次生成未运行，无重跑/替补，GPU窗口2.119秒。原FAIL/原四组参考保持，D1未通过，D2未开始，生产继续停机。

- [DF01/D1Q适配回执](reports/DF01-D1Q-V2-ADAPTER-20261102.md)：D1Q完成v2最小分类适配及CPU检查。仅完整drafter置信度绝对差为诊断；原行/token、概率有限值/范围、独立selector、target采样、提交状态和EOS硬门保留。原四组参考及旧FAIL不改，独立GPU程序只编译/链接，GPU/完整模型前向/生成0。最终身份为FINAL_FREEZE.json，D1命令为COMMANDS_V2.json，全部execute=false；D1未放行、D2未开始，生产继续停机。

- [DF01/D1P合同复核](reports/DF01-D1P-EXACT-MATCH-CONTRACT-20261102.md)：默认exact-match下，完整drafter置信度CPU/GPU绝对差可在[后续v2合同](plans/DF01_D1_EXACT_MATCH_V2.md)改为诊断项；目标采样、提交状态和EOS硬门保留。源码身份及104976组有限模型比较、三负例通过，GPU/模型前向/生成0。旧FAIL不改，旧程序未修改，v2适配及GPU硬门未完成，不直接放行D1，不进入D2。17:23:28生产inactive/dead，13保护SHA及1037历史/源文件一致，继续停机。

- [DF01/D1O CPU审计](reports/DF01-D1O-N2048-CPU-AUDIT-20261102.md)：Astra xhigh用同GPU行重算尾部，7/7 token一致、概率最大差4.77e-7，差异定位至前向行数据。来源一致的RMS/RoPE/分块attention候选在n2048离线过原门（最大差0.0386763），但同实现n32回归失败（0.0853075），不采用统一新参考。4次CPU完整前向后停止，GPU/生成0；首个n2048偏离算子未确认，旧FAIL/gold不变，D1仍阻断，生产继续停机。

- [DF01/D1N补验收口](reports/DF01-D1N-REMAINING-QUALIFICATION-20261102.md)：四组新CPU参考与原输入前缀身份冻结，CPU准备14分52秒，正例/三负例控制通过。GPU实际1程序/2组夹具/0生成：n32回归PASS，n2048第2项概率实际0.624771178、参考0.704674721、差0.079903543超0.05后停止。后14组与六次生成未运行，无重跑/补样本，D1继续数值资格阻断，不进入D2。旧FAIL/gold保持，生产继续停机。

- [DF01/D1M CPU收口](reports/DF01-D1M-CPU-REFERENCE-CLOSURE-20261102.md)：本轮GPU/生成均0。来源一致的CPU卷积＋planar整数GEMM组合使原首组保存原件的token由5/7至7/7，最大概率差0.0451068低于原0.05。原C++比较器及三个负例控制通过，Astra xhigh独立复核接受单夹具离线边界。旧FAIL/gold保持，完整D1未完成，其他夹具/target-state/六次生成未运行，不进入D2。633历史/源文件及13保护SHA一致，15:46:03生产inactive/dead，保持停机。

- [DF01/D1L逐层定位](reports/DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)：按新增授权完成1 GPU程序/原首组1夹具/0生成，无重跑。Astra xhigh参与复核，定位首个实际Q码错误为CPU `127/tensor`反除导致双舍入；改真除后5项CPU检查通过，五段FC Q/D与GPU逐bit一致。首项概率误差降至0.00491863、token由2/7至5/7，但最大概率误差0.0718193仍超门，D1继续阻塞。334历史/源文件及13保护SHA一致，生产保持停机。后续优先复用323项原件做CPU核对，不自动GPU/D2。

- [DF01/D1R单夹具诊断](reports/DF01-D1R-SINGLE-FIXTURE-20261102.md)：按新增授权执行1个GPU程序/原首组1夹具/0次生成，无GPU重跑。首概率0.787050843对0.734110057，原门失败。采集实际行及尾部；同GPU行在CPU重算7项token全匹配、概率最大差6.56e-7，差异定位到drafter前向，首个偏离算子未确认。修复可确认的CPU算术/适配问题，完整差异未消除；D1继续阻塞，不进入D2。14:33生产inactive/dead、13保护SHA和289历史/源文件身份一致，保持停机。

- [DF01/D1C CPU审计](reports/DF01-D1C-CPU-ORACLE-AUDIT-20261102.md)：概率定义与原D1 binary一致，四组28项概率CPU重放差0；修复参考head同值排序，补充后续失败诊断。CPU六项selector、324组门判定差分及新诊断检查通过，新资格程序仅编译/链接。原GPU失败唯一根因仍未确认，D1继续阻塞，GPU追加0，不进入D2。**按用户新要求，11:30停止原v0.2.3，11:46复核inactive/dead；保持停机，恢复等待用户要求。**

- [DF01/D1](reports/DF01-D1-QUALIFICATION-20261102.md)按新增授权执行并收口：首项GPU程序的首组夹具在`selector probability 0`失败，资格BLOCKED_NUMERICAL_ORACLE。实际1项GPU程序/1组失败/0次生成，后15组与六次生成NOT_RUN，无重试或替补，不进入D2。11:16原v0.2.3恢复，11:17独立复核健康、13保护SHA和原argv/环境一致。性能与质量仍未验证。

- [DF01/D0B](reports/DF01-D0B-CPU-READY-20261102.md)于2026-11-02补齐CPU准备缺口：七项性能输入、18项质量输入、Q8权重/激活参考及两项原生程序准备完成。该批次未执行GPU；后续D1结果见上一条。原[D0阻断回执](reports/DF01-D0-PREPARATION-20261102.md)原样保留。
- [U01R1版本对比](reports/U01R1-VERSION-COMPARISON-20261031.md)完成新一轮3组/12请求，计数修复在两版实际请求中验证。编码两版3/3，工具v0.2.3为3/3、v0.2.7为2/3，未见稳定升级优势，不建议继续完整升级验收或切生产。17:39原生产恢复、13保护SHA匹配，17:40复核active/running/enabled、loaded=true；本轮收口。
- [U01版本比较](reports/U01-VERSION-COMPARISON-20261031.md)已按停止条件收口：实际第一组v0.2.3两题评分均PASS，但计数进程PT0遗漏导致USAGE_DRIFT；剩余10请求NOT_RUN，v0.2.7未运行，比较INSUFFICIENT。16:29原生产恢复、13保护SHA匹配，16:30复核active/running/enabled、loaded=true；不据本轮升级或补样本。
- A0/v0.2.3 生产配置来自 [部署报告](reports/DEPLOY-PROD-20261026.md) 和 [KVRES 上线回执](reports/DEPLOY-KVRES-20261026.md)。[10 月 31 日恢复回执](reports/PRODUCTION-RESTORE-20261031.md)和 [D1U 停机回执](reports/DF01-D1U-N2300-CAUSAL-STOP-20261103.md)保留各自时间点的状态。
- 后续研究基线为 P6 原生 v0.2.7 + 六文件 reply/PT port。原 P6 二进制仍存在且 SHA 匹配；完整port、3574依赖和16项资产已在P00逐一hash核齐。P24 HC 二进制和 donor main 均不能替代它。
- P24 HC 已关闭：TTFT 改善 0.824%，CI 跨零；完整 decode 耗时增加 4.428%，未部署。原六项长检索 FAIL 保留，质量非劣未建立。
- frontier/P00 身份、真实Pi请求、源码去重与离线接口已完成；见 [P00报告](reports/P00-EVIDENCE-20261030.md)。[P01](reports/P01-PI-WARM-DIAGNOSTIC-20261030.md)已执行1引擎/1请求，941自然EOS触发短输出停止，两个append NOT_RUN，阶段INSUFFICIENT；当前合格新候选为0。
- [P01B](reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)按新的自然EOS合同完成1引擎/3请求，采集939完整窗口与2291原始token IDs；窄host间隙不足4%，资格INSUFFICIENT，未进入候选开发。本批次关闭。
- [F03](reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md)会话快照审计及CPU验证已完成，无泄漏/安全回收对象的充分证据；唯一同步零填原型正确性通过、CPU三对均更慢，NO_QUALIFIED_CANDIDATE关闭。缓存预算/PT0不变，GPU追加0。
- [Astra复核与收口](reports/FRONTIER-CLOSURE-ASTRA-20261031.md)：撤回优先推进F02的建议，F02保持DEFERRED_NEW_EVIDENCE；旧profile最大单格式条件成本仅2.22%/2.13%，且无已证新机制，不作当前暖态严格上界。当前零合格候选，P05 BLOCKED_EVIDENCE及六FAIL保留。

## 只从这里进入

- **无法访问29时的单文件交接**：[草稿token与CPU参考不一致 Handoff](handoffs/DFLASH2_DRAFTER_TOKEN_CPU_GPU_MISMATCH_HANDOFF_20261102.md)。单个约7.8MB Markdown内嵌151项源码/原件/四组head与selector权重切片、离线提取和核对工具；不需要原仓库或29即可核对。完整 backbone 权重的恢复方法与 SHA 见交接文件。该文件截止 D1T，D1U 新采集原件单独封存。

| 目的 | 入口与权威范围 |
|---|---|
| 接续工作 | [AI 入口](START_HERE_AI.md)、[下一步行动计划](plans/NEXT_ACTIONS.md) |
| 当前模型选型 | [v0.2.10 PT0 与三组版本配对](reports/V0210-PT0-VERSION-COMPARISON-20261104.md) |
| 当前收口与重开条件 | [Astra复核与收口报告](reports/FRONTIER-CLOSURE-ASTRA-20261031.md) |
| 当前生产状态 | [v0.2.3 恢复回执](reports/V0210-PT0-VERSION-COMPARISON-20261104.md#生产恢复) |
| DFlash2方案与资格结果 | [DF01完整方案](plans/DF01_DFLASH2_TEST_PLAN.md)、[D0B实际回执](reports/DF01-D0B-CPU-READY-20261102.md)、[原D0回执](reports/DF01-D0-PREPARATION-20261102.md)、[第一方来源核查](reports/DFLASH2-SOURCE-REVIEW-20261031.md)、[D1失败回执](reports/DF01-D1-QUALIFICATION-20261102.md)、[D1C CPU审计](reports/DF01-D1C-CPU-ORACLE-AUDIT-20261102.md)、[D1R实际诊断](reports/DF01-D1R-SINGLE-FIXTURE-20261102.md)、[D1L首个算子修复](reports/DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)、[D1M CPU参考收口](reports/DF01-D1M-CPU-REFERENCE-CLOSURE-20261102.md)、[D1N补验失败收口](reports/DF01-D1N-REMAINING-QUALIFICATION-20261102.md)、[D1O CPU审计](reports/DF01-D1O-N2048-CPU-AUDIT-20261102.md)、[D1P合同复核](reports/DF01-D1P-EXACT-MATCH-CONTRACT-20261102.md)、[后续v2合同](plans/DF01_D1_EXACT_MATCH_V2.md)、[D1Q适配回执](reports/DF01-D1Q-V2-ADAPTER-20261102.md)、[D1S执行回执](reports/DF01-D1S-V2-QUALIFICATION-20261102.md)、[D1T停止回执](reports/DF01-D1T-FINAL-CPU-STOP-20261102.md)；旧FAIL保持，完整D1未完成，不进入D2 |
| 本次合并依据、现场证据、验证 | [合并记录](reports/DOC-MERGE-20261030.md) |
| 后续研究及候选合同 | [frontier](frontier/README.md)、[研究报告](frontier/REPORT.md) |
| 最新完成的 GPU 工作 | [v0.2.10 PT0 与 v0.2.3 三组 MTP 配对](reports/V0210-PT0-VERSION-COMPARISON-20261104.md) |
| 历史 GPU 工作 | [D1U n2300 捕获](reports/DF01-D1U-N2300-CAUSAL-STOP-20261103.md)；[D1S v2执行失败收口](reports/DF01-D1S-V2-QUALIFICATION-20261102.md)；[D1N补验失败收口](reports/DF01-D1N-REMAINING-QUALIFICATION-20261102.md)；[D1L逐层诊断](reports/DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)；[D1R单组失败诊断](reports/DF01-D1R-SINGLE-FIXTURE-20261102.md)；原[D1首门失败收口](reports/DF01-D1-QUALIFICATION-20261102.md)；原[P01B](reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)保留 |
| 历史采用与质量边界 | [关闭台账](frontier/docs/01_EVIDENCE_AND_CLOSURES.md)、[P3](reports/P3-COMBINATION-KVRES-20261027.md)、[P24](reports/P24-HC-PAIRED-PERFORMANCE-20261029.md) |
| 历史部署 | [A0/EXACT6](reports/DEPLOY-A0-EXACT6-20261025.md)、[reply/PT/prefill](reports/DEPLOY-PROD-20261026.md)、[KVRES](reports/DEPLOY-KVRES-20261026.md) |
| 原始实验与执行工具 | 原位 `reports/`、`workspace/`、`lab/`、`tools/`、`tests/`；frontier 不复制另一套 runner |
| 历史阶段安排 | [原 README](history/README_PRE_FRONTIER_20261030.md)、[原 AI 入口](history/START_HERE_PRE_FRONTIER_20261030.md)、[已关闭续测合同](history/CONTINUATION_20261029.md) |

## 主从与统计规则

实际现场与带原件的实验报告决定事实；`frontier/` 决定未来阶段设计；旧 `docs/`、`prs/` 和历史计划仅用于解释原实验。P3、P24、旧通用 stats 各自的历史门槛保留，frontier 新统计政策只向前生效。过去分项相乘的 decode +23% / 墙钟 −9% 不是当前组合实测。

`frontier/P00`…`frontier/P07` 是新命名空间；文内短写 P00/P01 只在 frontier 下解释，不重命名旧 P0…P24 报告和原件。

## 离线检查

从本目录运行：

```bash
python3 -B -m lab.cli verify
python3 -B frontier/tools/validate.py --root frontier
python3 -B -m unittest discover -s frontier/tests -v
python3 -B frontier/tools/verify_manifest.py --root frontier --manifest frontier/MANIFEST.sha256
```

以上只验证包与离线工具。GPU 诊断、实现与部署状态分别记录；文档中的执行计划不构成新的远端实验授权。
