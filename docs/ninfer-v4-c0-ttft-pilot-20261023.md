# C0最小实机补测：L2恢复正常，TTFT收益未证明

通过`ssh 29`按冻结合同完成P4→C0。四个新Chat及其工具断言全部通过，两侧均真实恢复55,293个L2 token，仅计算81个token。客户端语义TTFT为943.6→959.9ms，本次未观察到改善。冻结判定为`INCONCLUSIVE_TTFT_CONTROL_NOT_SATISFIED`，不给C0整轮服务收益、V04、K4或发布资格。

窗口实际246.143秒（4分06秒），使用4Chat、含2次内置warmup共6次模型提交、10wire。没有追加请求或重跑旧任务。候选、驱动、控制器及监护均退出，GPU计算进程为空，原服务仍停止。生产镜像/参数/cache目录、采样、context及Pi medium/32768未改。

## 实际L2和TTFT

固定独立分支输入在P4/C0逐字节相同，P均55,374。分支包含明确标注的合成assistant输入，不冒充实际seed输出或真实工具结果续轮。下列TTFT是客户端首个非空content/reasoning/tool delta，不计仅role的首帧。

| 指标 | P4 | C0 |
|---|---:|---:|
| 实际缓存来源 | L2 / stable_prefix | L2 / routed_session |
| 恢复token | 55,293 | 55,293 |
| 恢复bytes | 1,333,980,256 | 1,336,349,835 |
| 实际computed prefill | 81 | 81 |
| 客户端语义TTFT | 943.552ms | 959.943ms |
| 服务端TTFT | 963.593ms | 972.223ms |
| restore耗时 | 571.270ms | 602.861ms |
| 日志queue字段 | 618.972ms | 641.932ms |
| seed DONE到分支发送 | 10.041s | 10.049s |
| 分支O | 93 | 169 |
| 分支完整客户端wall | 1.619s | 2.285s |

两端`source=l2`、`restored_bytes>0`、`prefix_reuse_path=restore_turn_checkpoint`；无目标续轮的preflight_rejected。真实L2恢复已经得到实机证据。C0本次TTFT描述性增加1.737%，n=1且对照不合格，不能断言稳定退化；也没有满足≥5%收益目标。两端O不同，不能用完整wall判断吞吐或整体服务退化。

## 为何仍为INCONCLUSIVE

原冻结分析器原样拒绝本次配对，理由为：

1. P4也深L2命中55,293 token，不符合预声明的P4浅命中≤512/近全量prefill。
2. 两端日志queue均大于50ms。
3. seed导出大小不同：1,333,034,412 / 1,335,401,900 bytes；seed O分别102/225。

固定+10秒调度及150ms容差成立，工具精确断言成立；上述失败条件没有放宽，没有追加请求寻找通过样本。

这里需要修正前一轮实验设计的两个假设：

- **整个发布job完成不等于第一个深前缀开始可恢复。** `publication_loop`先发布boundary_alias，再发布session，最后才记录`publication_finished_ns`。本次P4命中stable_prefix，C0命中routed_session；P4可在seed最终session发布结束前恢复深层稳定前缀。因此“P4最终publication未完成”不能推出“P4没有可用深前缀”。原设计没有隔开预期的未就绪/已就绪路径。
- **日志queue不是纯竞争等待。** 当前源码以admitted−submitted计算该字段，而`try_restore_continuation`在admit之前执行，包含恢复和准入工作。本次queue>50ms不证明有其他请求竞争，也不能与restore再相加。冻结门槛仍按原样判失败；本轮不改实现或门槛来制造资格。

[源码口径证据](../output/ninfer-v4-c0-ttft-pilot-20261023/runtime-metric-semantics.json)绑定实际C0产品树和源码blob。原始throughput在P4分支request_start前已记录publication增加、L2占用从624,130,693增至1,958,110,949；结合实际stable_prefix恢复和发布顺序，支持“boundary先可见、session仍发布”的解释。日志没有所选对象的精确ContentId，不能进一步唯一定位具体对象或给出首次就绪精确时刻。

## CPU发布耗时的描述性观察

seed的GPU copy结束到整个publication job完成：P4 14.372s，C0 7.060s，描述性减少50.875%。但导出shape/实际输出不同，且两种alias的可用时刻不同，这不是严格同样本配对，不能代表首次缓存可用提前或TTFT改善。

此结果与已有CPU SHA加速方向相容；它没有证明本次Chat能从该加速获益。已有CPU结果继续复用，不重跑。下一项性能改造无需以重复本窗口为前置；本轮到此结束，不自动追加补测。

## 完整请求、预算和收尾

| 请求 | P | O | 缓存 | 客户端TTFT | 工具/传输 |
|---|---:|---:|---|---:|---|
| P4 seed | 55,295 | 102 | none | 17.901s | PASS |
| P4 branch | 55,374 | 93 | L2 | 0.944s | PASS |
| C0 seed | 55,295 | 225 | none | 17.916s | PASS |
| C0 branch | 55,374 | 169 | L2 | 0.960s | PASS |

10wire包含4Chat、4telemetry和2个digest条件slot erase。内置warmup各1次，没有HTTP warmup或额外readiness请求；无新native Op/capture/replay。预算预约和实际发送/模型admission总计一致，未知结果、未发送预约、未结束导出均为0。四条SSE各有唯一DONE且finish_reason=tool_calls；模型内部finish_reason=stop_token单独保留，未混同。

硬窗900秒、清理边界720秒；实际在246.143秒已完成`ORIGINAL_STOPPED_CANDIDATE_CLEANED`，不是等到第12分钟才清理。两个候选容器保留为stopped，原服务未恢复；owner全退，原cache dev/inode保持66306/24150039，模型stat及两个serve二进制SHA一致。

窗口ID `c0-sha-pilot-20261023-l2-r3`，远端`/home/hhtele/ninfer-v4-c0-l2-preflight-20261023/prepared-window-l2-r3`现已消耗，禁止再次启动。driver tree `130bcf5414fc89d971f368fc81e9aafdda7753dd`，冻结SHA `1b0f1c596aa15f5e41d337f139d936c51ac52131ecd6d3c5efabc1e384127dd1`；P4/C0树及serve SHA见[机器汇总](../output/ninfer-v4-c0-ttft-pilot-20261023/final-summary.json)。没有产品代码修改、重建、提交或部署。

## 证据与限制

- [原始运行归档](../output/ninfer-v4-c0-ttft-pilot-20261023/remote-evidence.tar.gz)：SHA `e3b19b9b915c5f3952df18d4e4d0ef3b8132cddb88c4a00600ec6167ff2e4844`；123个原文件哈希索引已逐个核验，21份冻结文件和10组request/raw SHA及长度一致。
- [离线审计](../output/ninfer-v4-c0-ttft-pilot-20261023/audit.json)、[逐请求指标CSV](../output/ninfer-v4-c0-ttft-pilot-20261023/chat-metrics.csv)、[冻结分析器原始判定](../output/ninfer-v4-c0-ttft-pilot-20261023/prepared-window-l2-r3/pilot-analysis.json)、[最终主机回读](../output/ninfer-v4-c0-ttft-pilot-20261023/execution-l2-r3/final-host-readback.json)。
- [独立运行证据复核](../output/ninfer-v4-c0-ttft-pilot-20261023/runtime-evidence-review.md)无阻断发现；审查代理只读，未运行SSH、模型或测试。复核不替代统计资格。
- 本轮没有新原始附件缺口。旧r1失败、r2性能INCONCLUSIVE、CPU夹具首版失败、18处G1差异、C1附件缺口及全部历史成本保留；三个旧远端归档SHA未变。
- `p95=null`、`optimization_qualification=false`、`K4_qualified=false`。本轮完成的是实际恢复与最小功能验证；实际TTFT收益未证明，不宣称优化PASS或生产发布资格。
