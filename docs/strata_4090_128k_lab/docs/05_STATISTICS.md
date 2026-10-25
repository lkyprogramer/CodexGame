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

## 输出

`requests.jsonl`原始每请求记录；`requests.csv`表格；`summary.json`机器判定；`REPORT.md`人工阅读。`CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION`不等于自动部署。`NO_ESTABLISHED_NET_BENEFIT`也不表示PR普遍无效，只表示当前配置没有证实收益。

## 性能来源标记

文档中的旧数据统一标记为作者/社区报告。本包本地测试只验证框架和可信Java oracle。目标GPU结果必须由目标机器生成，记录源码SHA、二进制SHA、模型身份、配置和原始timings。

自动统计采用严格门槛：即使是base已有的质量失败，也会阻断自动“候选”结论，但不能据此归因PR。AI应逐例区分基线模型失败、协议失败和新增回归，保留原报告，再提交人工评审的非劣性分析；不得删除失败样本重跑出漂亮结果。
