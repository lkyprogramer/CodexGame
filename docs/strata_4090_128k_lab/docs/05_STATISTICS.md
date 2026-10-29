# 统计、证据级别与采用门槛

## 抽样单位

以**整轮fresh-engine运行**为配对单位，而不是每token、每CUDA kernel或每条SSE chunk。默认5个匹配round；A/A判断噪声，最终建议10个round及额外留出任务。冷请求与热追加分别分组，不跨模型、不同context或不同base合并。

时间收益定义为 `100 * (1 - exp(mean(log(B_i/A_i))))`。95% CI用固定seed的5000次配对bootstrap；这里是工程筛选置信区间，不是严格质量非劣性证明。不同PR多重筛选会产生选择偏差；只把最优项送独立留出集，不能将10次挑选后的p值当作一次检验。

## 主要指标预先确定

3453/2964：固定输出下的decode_ms、verify-window耗时和完整请求wall。1536/3517/3584：固定任务序列wall、re-read tokens、restore成本。3307/3281：新输入prefill+资源重载+TTFT，不能仅看kernel PP。3711：capture/shuttle耗时及内存代价。2822：短请求p95/配对TTFT、长请求完成时间、总吞吐，三者都报。3322：冷/热任务wall、draft成本、接受率及显存，不仅tok/s。

通用`stats`输出base→off与off→on的整轮时间，以及各group时间。专用scenario输出Java完整工具循环或preemption的pair wall/short TTFT。上游timings有缺失就保留null；不拿字符数或事件数补算。

## 失败不可丢弃

HTTP/CUDA错误、NaN、OOM、超限、错误工具调用、空回复、未执行Java、定长输出未达目标都保留原记录。失败/缺失导致对应配对不可比较，并显示原因。报告中同时列全部失败数，不能只统计幸存请求。

## 默认工程筛选门

- A1关闭路径相对A0：95% CI需处于[-3%, +3%]之内作为粗筛；若噪声大，先增样本，不能直接采用。
- B开启路径：主要指标至少改善5%，CI下界>0，且无新增安全/正确性失败，才成为留出集候选。
- 绝不因微内核1.5倍就说整个Agent1.5倍。
- 质量门：所有工具授权硬断言通过；Java整体不劣于基线，新增失败逐例复现；上下文恢复错误零容忍。
- 内存门：至少保留4096MiB实际可用RAM，无swap持续增长，无逐turn泄漏；显存保留与显示用途一致。
- 长时门：通过预先冻结的真实Pi/Java任务集合、compaction与取消；报告未执行项。

以上3%/5%是本实验的工程决策阈值，不是Strata官方标准。它们可在**看结果之前**按用户目标修改并留档。

## 正式采用门（2026-10-26 从 v2 包收编，项目政策）

上面的筛选门决定“能否进入留出集”。进生产前再过下面的正式门；阈值在首次实验前冻结一次，看完候选结果后不得再改：

- **最小有意义改善** `m = max(3%, 2 × A/A 噪声)`，A/A 噪声 = 预登记的配对 round ratio 相对 1 的绝对偏差中位数。按已测噪声（引擎 ms/窗口约 ±0.75%，decode 组级约 ±2%），decode 类改动的 m 在 3%～4%。
- **主指标**：时间 ratio（candidate / base）的 95% 配对区间上界 ≤ 1 − m。修复明确正确性 / 缓存失效问题的项例外：主时间 ratio 上界 ≤ 1.03 且质量门通过即可（#1536 属于这一类）。
- **关键非目标场景**：冻结的时间 ratio 95% 区间上界 ≤ 1.03；OOM、错误率、严重尾延迟单独审查。尾部数据不够就标 INSUFFICIENT，不用均值代替；少于 1000 个请求不宣称 p99。
- 状态机：`IDEA → ELIGIBLE → MICRO_PASS → NUMERIC_PASS → SCENARIO_PASS → HOLDOUT_PASS → COMBINATION_PASS → READY_FOR_DEPLOY`；旁路状态 `NOT_APPLICABLE / NO_GAIN / QUALITY_REGRESSION / BLOCKED / INSUFFICIENT / REJECTED`。没有目标机运行到不了 SCENARIO_PASS。

**实现覆盖**：`lab.cli stats` 只做配对 log-ratio bootstrap 的严格筛选（点估计 ≥5%、区间支持改善、off/base 约 ±3%），不直接给正式 PASS。正式门里的 restricted time-to-success（成功记实际 wall、失败记预算 B）、失败分类和冻结流量权重还没有实现（v2 P00 的开发项）；需要时由执行 AI 先实现并补测试。

## 退出码与判定

- `stats`：写完 `summary.json` / `requests.csv` / `REPORT.md` 后，有缺项、重复、失败、未评分、计划 hash 无效，或参数错误（未知 arm、非法 metric、坏 JSON）时退出 **2**；合法报告退出 0。0 不是采用许可。
- `tools/quality_gate.py`：通过退出 0（`NONINFERIORITY_ESTABLISHED`），未能证明非劣退出 1（`NONINFERIORITY_NOT_ESTABLISHED`），实验无效退出 2（`INVALID_EXPERIMENT`），OOM / crash 等硬拒绝退出 3（`HARD_REJECT`）。项目层可以把 1 映射为 INSUFFICIENT，但这不是 CLI 返回的字符串。

## 质量非劣（任务级，`tools/quality_gate.py`）

- 单位是预登记的独立任务对（同一任务 base / candidate 各一次；多 seed 先聚合）。四格中 b = base 成功、candidate 失败，c = base 失败、candidate 成功。
- 保守界 `U_harm = CP_upper(b, n, 0.025) − CP_lower(c, n, 0.025) ≤ δ`，默认 δ = 0.02。基础设施失败使该对无效，不能用幸存样本挽救；预算耗尽算有效失败；OOM / crash 硬拒绝。
- 样本量现实：n = 30 即使全部一致（b = c = 0）也证明不了 2pp 非劣（CP 上界约 0.116）；全一致时 n = 183 才达到门槛（示例用 184，见 `tools/examples/quality-zero-loss-184.json`）；有不一致对时还要更多。

**本机实际取舍（2026-10-26）**：Pi 的 xhigh 回合每轮 1.5～3.5 min。约 180 个独立任务对、每对 base / candidate 各一次：单轮任务约 15 小时，8 轮编码链约 5 天；题目还必须足够难才不撞天花板。正式 2pp 非劣在单 4090 上不现实。对 PT=0 这类服务层候选，采用：

1. 实验室配对筛查（已做：6 条 8 轮编码链全满分，有天花板效应，只能说“未测出差异”）；
2. 用户真实 Pi 会话作留出：用户在实际使用中对比，发现质量退化即回滚（服务端开关，回滚只需改 env 并重启）；
3. 如需更强证据，加一组更难的编码链（需求更多、存在相互冲突的修改）做筛查，按 `quality_gate` 报四格，不宣称 2pp 非劣。

报告中必须写明走的是哪条路径，不能把筛查结果写成正式非劣。

## 输出

`requests.jsonl`原始每请求记录；`requests.csv`表格；`summary.json`机器判定；`REPORT.md`人工阅读。`CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION`不等于自动部署。`NO_ESTABLISHED_NET_BENEFIT`也不表示PR普遍无效，只表示当前配置没有证实收益。

## 性能来源标记

文档中的旧数据统一标记为作者/社区报告。本包本地测试只验证框架和可信Java oracle。目标GPU结果必须由目标机器生成，记录源码SHA、二进制SHA、模型身份、配置和原始timings。

自动统计采用严格门槛：即使是base已有的质量失败，也会阻断自动“候选”结论，但不能据此归因PR。AI应逐例区分基线模型失败、协议失败和新增回归，保留原报告，再提交人工评审的非劣性分析；不得删除失败样本重跑出漂亮结果。
