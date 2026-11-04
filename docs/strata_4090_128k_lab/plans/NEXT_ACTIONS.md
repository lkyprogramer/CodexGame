# 当前结束点 · 保留 Qwen Next

[v0.2.10 PT0 与三组版本配对](../reports/V0210-PT0-VERSION-COMPARISON-20261104.md)已收口。保留 v0.2.3 并已恢复服务。PT0 只保留隔离适配，暂不移植 #1536。当前没有待执行的版本切换或 GPU 批次。下列计划和服务状态为历史记录。

## 原 D1U 停止点 · context Q/D

D1U 完成 n2300 的一次原路径逐层捕获。中立性三次前向逐 bit 匹配 D1S。只替换 context `hidden_norm` 的 Q/D，CPU 第 4 项由 `212522` 变为 GPU 的 `209087`，七个 token 均匹配。已定位因果边界，未证实可单点修复的缺陷。按补丁门停止候选，第二个 GPU 程序未运行。原 FAIL 和参考保留，D1 未通过，D2 未开始，生产保持停机。 [D1U 执行回执](../reports/DF01-D1U-N2300-CAUSAL-STOP-20261103.md)。

D1U 原件见 `workspace/dflash2/df01-d1u-20261103/`。保留 [D1T 单文件离线交接](../handoffs/DFLASH2_DRAFTER_TOKEN_CPU_GPU_MISMATCH_HANDOFF_20261102.md) 作为历史证据。

## 2026-11-02较早 · D1T唯一CPU终审后停止候选

[D1T停止回执](../reports/DF01-D1T-FINAL-CPU-STOP-20261102.md)与[Astra唯一终审](../reports/DF01-D1T-ASTRA-REVIEW-20261102.md)：本轮30分钟截止内，仅做一个CPU尾部程序/两个保存行输入。冻结CPU参考token和概率逐bit复现；同GPU行尾部7/7匹配、最大概率差6.71e-7。两候选在两侧top16中且前驱相同，输入行差异使分数排序翻转；未找到首个错误算子或最终原因，没有可证实单点修复。

**按用户要求STOP_CANDIDATE，停止当前DFlash2候选的排查与后续测试。** 不继续完整前向、计算顺序组合、改参考、放宽token门或GPU采集。不沿D1S未用额度开跑，不进入D2，不保留自动执行的下一轮CPU定位计划。以下旧段落的建议仅作历史，不是当前行动。

Astra实际gpt-6-astra/xhigh仅一次，只读且没有数值前向；主代理完整backbone/GPU/生成/服务启停均0。原Python缺NumPy的启动失败保留，改用已有CPU解释器后实际数值计算只运行一次。1143历史/源文件及13保护SHA一致，21:27:06生产inactive/dead，无GPU计算进程或18343/18089监听。D1仍未通过，生产继续停机。

## 较早D1S · 冻结v2执行收口

[D1S报告](../reports/DF01-D1S-V2-QUALIFICATION-20261102.md)：新授权绑定D1Q FINAL_FREEZE.json与COMMANDS_V2.json，CPU绑定2正/5负及1122项预检通过。实际1个GPU资格程序、4组夹具、0生成；前三组v2 drafter硬门通过，n2300第4项GPU token209087对原CPU参考212522，6/7一致，exit1后停止。完整drafter置信度差只记诊断，不能覆盖token硬失败。

后12组（独立selector3组、target-state9组）及六次生成NOT_RUN。GPU窗口2.119秒，无重跑、补样本或D2。23原件本地bytes/SHA通过；1104历史/源文件、13保护SHA和1122冻结身份保持。20:04:38生产inactive/dead，继续停机。

**D1未通过；本轮按硬失败规则收口。** 根因未确认，不把该差异直接解释为最终target输出错误，也不作性能或升级判断。若后续另获定位授权，先复用n2300原件做CPU审计；本轮不执行该审计、不改参考、不放宽token门，不使用剩余GPU额度。

## 较早D1Q · 最小适配与CPU封存

[D1Q回执](../reports/DF01-D1Q-V2-ADAPTER-20261102.md)和[适配源码](../tools/dflash2_v2/README.md)：完整drafter置信度差仅作诊断；原比较器/FAIL及原四组参考不改，其余硬门保持。29项分类、原target/selector表达式9项、原状态10项和host采样201项、EOS三正例与两负例、两组保存原件回放通过。n2048仍记录legacy FAIL，不代表重新运行或放行D1。

新独立GPU程序仅CPU编译/链接。`FINAL_FREEZE.json`为最终身份；`COMMANDS_V2.json`仅描述D1两程序/16夹具/六生成，全部`execute=false`，本轮GPU与生成预算0。准备阶段包含旧D2命令的描述文件和清单只作来源，不作执行入口。完整模型前向/GPU执行/生成/服务启停均0，生产保持inactive/dead。

**D1仍未放行，D2未开始。** 本轮CPU工作收口。下一项若获GPU授权，明确新预算并将监督器绑定最终身份、v2记录及D1命令；运行前只做必要身份/资源预检。保留程序非零退出即停止，不忽略旧exit1，不借原剩余额度。不得再以置信度诊断项通过代替target采样、提交状态、EOS或实际资源/机制检查。

## 较早D1P · 纯CPU合同复核与后续v2边界

[D1P报告](../reports/DF01-D1P-EXACT-MATCH-CONTRACT-20261102.md)与[默认exact-match合同v2](DF01_D1_EXACT_MATCH_V2.md)：默认路径下接受判定依赖target逐位置输出与有效前缀提交，完整drafter置信度只调度窗口。确认可将该置信度的跨CPU/GPU绝对差改为后续诊断项；独立selector概率、原行/token、target采样、提交状态、EOS、机制/资源硬门保留。PROB/COUPLED/GUMBEL及其他路径不适用。

三份CLI关键源码、真实verifier/sampler及构建身份核对通过。104976组有限模型比较覆盖草稿/置信度/窗口变化；首拒后保留、随机数位置复用、EOS后输出三个负例均检出。该证明有明确前提，不替代GPU采样、KV/GDN/PLE/index或EOS硬门。旧CLI终态可提交多于可见输出的输入前缀，但必须等待commit并丢弃状态；不认可API恢复生命周期。

**本轮不放行D1，不追加GPU，不进入D2。** 原D1/D1N及其他FAIL、D1O统一参考失败和旧gold保持。旧GPU程序/runner未改，仍会在0.05差异处exit1，不能直接忽略退出码。下一项若获授权，准备独立v2最小分类适配、硬失败负对照、源码/binary/原四组参考与命令冻结；完成这些前置后，GPU仍须新的独立预算与授权。当前不执行适配或GPU。

17:23:28收口为生产inactive/dead、MainPID0，无GPU计算进程或18343/18089监听，13保护SHA及1037历史/源文件一致。12原件本地bytes/SHA一致，模型前向/GPU/生成/服务启停均0；继续保持停机。

## 较早D1O · n2048 CPU审计及回归收口

[D1O报告](../reports/DF01-D1O-N2048-CPU-AUDIT-20261102.md)：按新增60分钟CPU-only授权，派发gpt-6-astra / xhigh检查尾部及review。冻结CPU rows逐bit重放，同GPU rows尾部7token一致、最大概率差4.77e-7，差异定位至进入尾部前的行数据；尚不能定位n2048首个前向偏离算子。

来源确定的RoPE、RMS、分块attention次序形成独立CPU候选，四次完整前向及全部正负结果保留。最终n2048原门通过（maxp差0.0386763，第2项差0.0136324），但同一实现n32回归失败（首项差0.0853075），原C++比较器分别exit0/exit1。Astra接受停止并拒绝推广统一参考。不得按context拼接参考，也不继续寻找组合或改容差。

**本轮GPU/生成0，不进入D2。** 原D1N FAIL及冻结参考保持，统一修复未闭合，D1剩余资格、target-state及六次生成未运行。现有n2048原件缺逐层真值，本轮不继续补采或补算其他组合。

16:58:27生产inactive/dead、MainPID0，无GPU计算进程及18343/18089监听；968历史/源文件及13保护SHA一致。69原件本地bytes/SHA一致。数值试验停止，报告包检查后收口；生产保持停机，恢复等待用户明确要求。

## 较早D1N · 四组参考冻结及GPU补验收口

[D1N报告](../reports/DF01-D1N-REMAINING-QUALIFICATION-20261102.md)：按新增授权先完成四组CPU参考冻结及检查，14分52秒内收口；原输入前缀不变，n32新参考与D1M逐byte一致，965项身份在新GPU前冻结。原比较器正例与三负例通过。元数据helper重复读取模型的中断exit143保留，后续仅完成唯一文件流式封存，没有重复前向、编译或比较器。

实际GPU1程序/2组夹具/0生成：n32回归PASS；n2048的第2项概率实际0.624771178、参考0.704674721、差0.079903543超过原0.05。程序exit1后停止，不使用剩余额度诊断或修复复测。n2064/n2300两组、独立selector三组、target-state九组及六次生成均NOT_RUN；没有重跑或替补。

**D1继续数值资格阻断，不进入D2，生产保持停机。** 新失败不否定n32回归，也不证明DFlash2性能无收益；剩余原因未确认。若后续获新授权，只能先围绕保存的n2048观察值制定CPU审计范围；本轮不自动开始任何新检查或采集。旧FAIL/gold、六FAIL、P05和关闭方向保持。

## 较早D1M · CPU参考修复与收口

[D1M报告](../reports/DF01-D1M-CPU-REFERENCE-CLOSURE-20261102.md)：按新增CPU-only授权复用现有逐层原件，派发gpt-6-astra / xhigh协助定位和review。CPU卷积顺序沿用已确认修复；drafter planar Q8 GEMM改为原始int8/FP16 scale、整数点积、FP32 FMA和32-lane XOR归约。head保持Q8_1＋Torch矩阵乘法，GPU数据只用于比较，不注入独立CPU前向。

两个完整CPU组合均保留：真除＋卷积为2/7、最大概率差0.348147，失败；增加原生顺序planar整数GEMM后7/7、最大概率差0.0451068，满足原门。原C++比较器正例及三个负例控制通过。Astra独立复核接受单夹具离线边界。attention局部仍有一个量化码差的负结果保留，未接入完整前向，不继续追逐逐bit一致。

**本轮GPU0、生成0，不进入D2。** 原FAIL/gold不变；当前原首组在修正参考下的离线数值阻断闭合，但完整D1未完成，其他资格夹具、target-state及六次生成未运行，性能和质量未验证。下一项若获授权，先冻结新CPU参考版本和夹具身份，再明确剩余D1资格范围；本轮不自动生成其他参考、重复GPU或恢复服务。

15:46:03生产inactive/dead、MainPID0，无GPU计算进程及18343/18089监听。633历史/源文件和13保护SHA一致，继续保持停机。277导出原件本地bytes/SHA一致；报告包检查后停止。恢复等待用户明确要求。

## 较早D1L · 逐层首因与CPU修复

[D1L报告](../reports/DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)：新增授权仅原首组逐层诊断，实际1 GPU程序/1夹具/0生成，无重跑。323项原件、最终rows/probs与D1R逐bit一致。用户要求后派发Astra xhigh；采集前复核无阻断，采集后独立找到并闭合首个tap量化错误：CPU `127/tensor`执行倒数再乘，位置22/列1928量化60，GPU与真除为59。

最小修复仅将planar inverse改为torch.div，保留scale、zero、RN-even/head。5项CPU检查通过，五段FC的409600个Q码、12800个scale与GPU逐bit一致；101项同输入原生GEMM逐bit相同。Astra复核接受首个缺陷修复。原NumPy代理摘要遗漏Torch反除，旧摘要保留并明确更正。

完整参考修正后token由2/7至5/7、首概率误差降至0.00491863，但最大概率误差0.0718193仍超0.05。原GPUFAIL、冻结gold与各失败记录保持，D1继续BLOCKED_NUMERICAL_ORACLE，不进入D2，不升级生产。

下一项有价值的工作是复用当前323项逐层原件做纯CPU核对，定位修正参考之后的剩余差异；无需继续补采同一前向数据。本轮不自动开始该阶段，不重复GPU，不改容差。15:19:46生产inactive/dead，13保护SHA及334历史/源文件SHA一致，保持停机，恢复等待用户明确要求。

## 较早D1R · 单夹具诊断收口

[D1R实际报告](../reports/DF01-D1R-SINGLE-FIXTURE-20261102.md)：新增授权仅1个GPU程序、原首组夹具、0次生成、60分钟。实际1/1/0，原概率门失败复现，GPU实际0.787050843、参考0.734110057，绝对差0.0529407859。实际行、head、top16与selector projection完成采集。无GPU重跑或替补，唯一GPU额度用完。

同GPU行在CPU重算7项token全匹配、概率最大差6.56e-7；直接用GPU尾部重算最大差1.79e-7。差异定位到selector之前的drafter行数据，首个前向偏离算子仍未确认。修复CPU卷积算术顺序及本轮inference漏量化适配缺陷，3项CPU测试通过；原卷积下可精确复现冻结参考。卷积修正没有消除完整前向差异，RMS略增，不作为新金标，不改原失败。

D1继续BLOCKED_NUMERICAL_ORACLE，不进入D2，不升级生产。后续重开须围绕未定位的drafter前向制定新的范围；不自动重复本次尾部诊断、改容差或补样本。target-state九组及生成/性能/质量仍未执行。

**生产继续保持停机。** 14:33:07复核inactive/dead、MainPID0，无GPU计算进程及18343/18089监听，13保护SHA及289历史/源文件SHA匹配。本轮服务启停0，恢复等待用户明确要求。当前没有自动执行任务，本轮在报告包检查后停止。

## 较早D1C · CPU概率审计与修复

[D1C报告](../reports/DF01-D1C-CPU-ORACLE-AUDIT-20261102.md)：CPU参考与原D1 binary的selector概率定义一致，四组28项冻结概率精确重放。修复参考head同值排序不稳定与资格失败未保存实际值的问题。旧同值反例exit1保留，新selector六项、324组原门差分、新诊断和新header七项控制通过。新资格binary仅编译/链接，未GPU执行。

原D1实际GPU概率与中间结果缺失，唯一根因仍未确认。修正后原四组期望值不变，不能宣布修复原GPU差异。D1继续BLOCKED_NUMERICAL_ORACLE，不进入D2，不补样本，不升级生产。原D0/D0B/D1及六FAIL/P05/关闭结论保持。

**生产按用户新要求保持停机。** 11:30:36停止原v0.2.3，11:46:26复核inactive/dead、MainPID0，无GPU计算进程与18343/18089监听；13保护SHA及226历史/源文件身份一致。本轮没有恢复，后续只按用户明确要求恢复。新GPU实验、目标生成、完整reference forward均0。

D1C收口时没有自动执行任务。当时下一项证据是D1实际概率与行数据，后由D1R单独授权采集；不沿原D1/D2数组开跑。CPU修复不替代GPU资格。本轮在CPU报告与原件检查后停止。

## 较早D1 · 首门失败收口

[D1实际回执](../reports/DF01-D1-QUALIFICATION-20261102.md)：按用户新增授权通过ssh 29执行D1并临时停生产。首项GPU程序首组drafter-n32-seed1在`selector probability 0`失败，资格BLOCKED_NUMERICAL_ORACLE。实际1项GPU验证程序、1组失败、0次生成；后15组夹具和六次生成NOT_RUN，无重试、无替补。D2未授权且未执行。

11:16:02原v0.2.3恢复，11:17:13独立复核active/running/enabled、health loaded=true、13保护SHA及原argv/环境一致。监督窗口41.348秒。D1数值/状态资格未建立，性能和质量仍未验证；不升级生产。

D1收口时没有待执行GPU任务。当时下一项是单独授权的CPU概率定义/参考审计，解释运行时selector与CPU参考的首项差异；本轮不自动开始。GPU实际概率没有写入原件，不能编造差值、放宽门或用额外探针补齐。后续GPU复测须有新的限额合同。

## 较早D0B · CPU准备完成

[D0B实际回执](../reports/DF01-D0B-CPU-READY-20261102.md)：参考用户指定的两个仓库构造缺失代码样本，实际7907/6717/105962 tokens。七项性能输入和18项质量输入完成CPU渲染；实际Q8权重/激活参考、selector硬断言和KV/GDN/PLE/index/MTP状态程序准备完成。两项GPU程序编译成功，16组夹具尚未GPU执行。

D0B收口时CPU_preparation_ready=true。当时下一项仅为另行授权的D1：两项GPU验证程序、最多6次生成、≤60分钟；任一硬门失败停止，不自动进入D2，不补样本。首次完整GPU维护窗口的原预算不变。本轮生产active/running、health loaded=true、13保护SHA一致；没有停启服务。

新输入明确标为仓库代码构造请求，不冒称Pi历史。原D0阻断回执、旧失败样本、六FAIL、P05与关闭结论全部保留。

## 较早D0阻断，历史保留

[D0实际回执](../reports/DF01-D0-PREPARATION-20261102.md)：固定权重与760353792bytes Q8 pack已校验；计量版单TU编译、链接通过；默认exact-match CPU检查通过，GPU未运行。实际S-C5947、D3-S-C81不满足冻结短档；独立D3-L-C投影受compaction阻断；Q8 reference、selector硬断言及target状态夹具尚缺。状态BLOCKED_PREPARATION，不能直接安排停机或D1。

当时的下一项工作是修复CPU准备缺口；该工作随后由用户授权D0B。没有填充、放宽长度或将余弦检查当完整selector验收。D1及后续仍未获本轮执行授权。旧六FAIL、P05和关闭结论保持。

## 上一轮U01R1收口

[U01R1实际报告](../reports/U01R1-VERSION-COMPARISON-20261031.md)：按用户新授权修复并独立完成3组/12请求，6个实验引擎，无重试、替补或额外生成探针。两版编码均3/3通过，工具v0.2.3为3/3、v0.2.7为2/3；新版仍有enabled字符串错误。编码耗时两组变慢、一组变快，三对wall比描述性几何均值1.092769，生成长度不同，不作引擎吞吐或正式性能结论。

计数修复已由CPU预检和两版6个实际编码请求验证：本地与服务usage均4408。原32-token容差不变。新回归3项加原helper5项PASS。

**当前不建议继续完整升级验收或切生产。** 本轮已收口，不追加实验。17:39:28原v0.2.3生产恢复，17:40:23复核active/running/enabled、loaded=true、NRestarts0，13保护SHA全部匹配，GPU只有生产引擎，18089可bind。原六FAIL、P05 BLOCKED_EVIDENCE和frontier关闭结论保持。合同见[U01R1](U01R1_VERSION_COMPARISON.md)。

## DF01原方案与D0授权边界

[DFlash2完整测试方案](DF01_DFLASH2_TEST_PLAN.md)和[第一方来源核查](../reports/DFLASH2-SOURCE-REVIEW-20261031.md)已交付。此前#3322只有源码/资格审查，未找到本包Flash-Next DFlash2本机性能A/B；固定MTP及HC/F02负结果不覆盖更换草稿算法。A0已有原生单卡CLI，服务仍回退MTP。D0首次准备受阻，D0B随后补齐CPU缺口；D0B之后由用户授权D1，实际首门失败并收口，见本页最新记录。DSpark保持观察。

2026-10-31为PLAN_ONLY；2026-11-02用户新增授权D0，已下载固定资产并完成CPU准备检查。该次D0授权不含GPU或服务启停；随后单独授权的D1不包含服务移植。未来MTP主对照仍保留974MiB预留，DF命令预声明1900MiB但尚未运行，不能把两臂都改为1900。初次GPU阶段上限仍为D1+D2合计28次自由生成及2个有界原生正确性程序、≤4小时并恢复原生产；不是当前执行授权。

## 上一轮U01失败保留

[U01实际报告](../reports/U01-VERSION-COMPARISON-20261031.md)：按用户授权执行v0.2.3与无HC v0.2.7对比，预登记3组/12请求。第一组A的两题评分均通过，但编码请求本地计数44108与服务usage4408不符，触发USAGE_DRIFT后中止；实际2请求、其余10 NOT_RUN，B未启动，没有重试或补样本。

原因是本轮worker计数器未继承服务PT0，CPU重渲染PT0后精确为4408。原执行源码/失败不改；本地修正未GPU复测。当前执行INCOMPLETE、版本比较INSUFFICIENT，不进入完整升级验收或切换生产；没有新版好坏结论，也不自动开新一轮。

16:29:12北京时间原v0.2.3生产已恢复，active/running/enabled、NRestarts0、loaded=true，13保护SHA全部匹配；16:30:59复核GPU只有生产引擎、实验18089无监听。当前停在[U01合同](U01_VERSION_COMPARISON.md)的失败收口点。若后续明确授权新合同，才使用修正适配，当前不补样本。

## 先前frontier零候选收口，结论保持

[Astra复核与收口报告](../reports/FRONTIER-CLOSURE-ASTRA-20261031.md)：2026-10-31独立复核已完成，root采纳结论，停止当前冻结合同下的性能探索。当前NO_QUALIFIED_CANDIDATE；撤回“优先推进F02”的建议，取消原拟追加的四小时离线审计。

**2026-10-31该批次生产恢复运行。** D1U 停机回执属于后续历史批次。用户在当时文档收口后明确要求恢复既有服务；[恢复回执](../reports/PRODUCTION-RESTORE-20261031.md)记录12:49健康接口loaded=true、12:50:44 active/running/enabled、NRestarts0。该次GPU占用为历史状态，不能替代本页顶部的最新回执。

F02保持DEFERRED_NEW_EVIDENCE。旧P11 trace按实际PID与首末输出区间重算，GU-SwiGLU全家族并集占6.8911%/6.5884%，但合同限定一个格式、一个内核；最大TG21仅2.2188%/2.1287%，且尚无已证load/layout新机制。这是旧profile条件成本，不是当前真实暖态暴露成本或严格上界，不能外推全局NO_GAIN。

## 当前行动

- 文档、入口与清单已收口；不进入P02/P03候选开发，不追加GPU，不换另一方向续测。
- P01原短输出停止、P01B执行COMPLETE/资格INSUFFICIENT、F03 NO_QUALIFIED_CANDIDATE及旧关闭结论保留；六FAIL不变，P05仍BLOCKED_EVIDENCE。
- 6144MiB/4slots、PT0和生产配置保持。生产恢复动作仅启动既有服务，没有改配置或追加GPU实验。未来停生产或占用GPU须明确对应执行范围；本次恢复不解除实验前置门。

## 未来重开条件

先提供独立新源码机制、当前真实暖态命中与可闭合依赖证据、可信局部方案和新增成本账，支持完整请求净省时≥4%；说明旧否决证据为何不覆盖新机制，并明确资源/质量前提、新编号和限额合同。缺证据保持DEFERRED_NEW_EVIDENCE/BLOCKED_EVIDENCE，不自动补采样。后续实施或GPU实验须由用户明确给出对应范围；本次收口不产生实验授权。

## 已关闭的F03 CPU审计

[F03实际报告](../reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md)：2026-10-31按用户授权完成会话快照复制/生命周期审计及必要CPU验证，结论NO_QUALIFIED_CANDIDATE，本轮关闭。

没有证明泄漏或可删除的已结束快照。现有take/retain、dirty边界、superseded、guard、容量回收和off-path move已覆盖对应语义。唯一新差量“同步KV保存避免先零填”在独立CPU目录验证：cache4834 checks、基线/原型各2068 host checks PASS，但固定三对完整CPU成本均慢6.08%–7.74%，不保留候选、不追加样本。

GPU启动0、推理0，无engine重建；生产停机，13保护hash、原P6和配置未变，6144MiB/4slots/PT0保持。无新优化采用，不进入P02/P03或GPU。六FAIL及P05 BLOCKED_EVIDENCE继续保留。重开须有独立新机制与当前暴露成本证据，不能重测同一零填、旧async/pool或trim/MMAP开关。

## 已关闭的P01B

[P01B实际报告](../reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)：2026-10-31按用户授权补齐host有界采集并验证，单引擎三请求全部完成，无重试。prime/append_1/append_2输出941/576/774，最后一次追问read291/reused89207。执行COMPLETE，候选资格INSUFFICIENT。

939个完整窗口、2291个原始token IDs已核对。两条warm请求的verify返回→commit进入全部host间隙仅占0.1340%/0.1224%，该窄方向没有4%空间。GPU内部和其他未知依赖保持UNKNOWN，不外推全局无优化空间。首个append大规模重读与PT0上下文相关渲染吻合，第二次已高复用；没有据此认定新的持续缓存缺陷。

生产保持停机，最终13保护SHA、原P6及配置未变，GPU1MiB、端口空闲、所属PID退出。本批次关闭，不追加GPU、不进入P02/P03、不遍历候选。新方向须先有明确机制差量和可闭合依赖证据；六FAIL和P05 BLOCKED_EVIDENCE保持。

## 上一批次保留

[P01实际报告](../reports/P01-PI-WARM-DIAGNOSTIC-20261030.md)：单引擎/1prime，103183输入、941自然EOS。按2048输出门停止，两次append NOT_RUN，阶段INSUFFICIENT。P00身份锁定仍有效；本轮无新候选资格、未部署，生产停机。

采集适配已实现并交付，但实际warm链、2048长输出、逐window依赖与原token IDs均没有得到证据。P05保持BLOCKED_EVIDENCE，原六FAIL不变。

P01原run保持关闭。其后由用户明确授权的新P01B自然EOS合同另行执行，未倒写P01原验收门或失败原件。
