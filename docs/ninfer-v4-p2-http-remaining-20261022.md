# P2 剩余 HTTP 验证：C1 关键功能通过，取消采集器停测，现网已恢复

**P2 最小实机验收仍未通过：C3 尚未执行。** 本轮通过 `jssh 29` 发出9/17个候选HTTP，前8项通过；第9个取消请求实际成功，但我方客户端把“引擎取消完成＋传输断开”两个正常可达事件误判为歧义，安全停止。本轮窗口 **190.117312秒（3分10秒）**，原服务已在4/4恢复单位内恢复验活。该采集器缺陷已修复并通过新增host回归、真实日志离线核对及独立评审，未重发任何模型请求。

时间为2026-10-22 **20:21:05—20:24:15（Asia/Shanghai）**。未重跑4个已通过native、原冷A、Baseline、BO、G1、P1或grader；采样、context/KV262144、Pi medium/32768均未改变。本轮Pi请求为0。

[汇总账本](../output/ninfer-v4-p2-http-remaining-20261022/final-summary.json) · [原失败账本](../output/ninfer-v4-p2-http-remaining-20261022/evidence/campaign/campaign.json) · [恢复验活](../output/ninfer-v4-p2-http-remaining-20261022/evidence/restoration.json) · [最终只读核查](../output/ninfer-v4-p2-http-remaining-20261022/final-live-validation.json)

## 冻结、身份与复用

新持久目录为 `/home/hhtele/ninfer-v4-p2-20261022/hardware/http-remaining-20261022`，使用独立campaign，未改写[首窗口](ninfer-v4-p2-hardware-20261022.md)的3条请求、规范ID关联失败、原始成本和ledger。先前4个native/7次提交及冷A P20057/O52、Engine2/job4证据原样复用。

本轮HTTP冻结源码树为 `34d6fd408ab90214ba549401bb6a7c102b2b3a57`；原native树为 `4c58698eda334ad3fc2c27c4fc22fc8c08dabbcc`，差异仅客户端/测试。`ninfer-serve` 仍为原r5二进制，SHA256 `c08d46f2c06179c0f713f556c199eac2d4052868a3266c2a6c979ea6c1ec16a6`，没有重编或切换引擎代码。

[工具清单](../output/ninfer-v4-p2-http-remaining-20261022/evidence/script-freeze.json)和[冻结回执](../output/ninfer-v4-p2-http-remaining-20261022/evidence/freeze-receipt.json)绑定新wrapper、规范ID修复后的runtime-v1、原body/raw/完成事件、4native结果及旧ledger。开窗前11项新增wrapper host测试在固定BO/runc/network=none、无GPU环境通过，独立只读评审无剩余finding。评审没有执行实机请求。

旧服务退出后L2内存不再存在。因此先校验旧L3的590个文件、chunk/content-address、manifest、compatibility与24小时有效期，再复制到新C1目录；无hardlink，原目录未修改TTL或内容。首次请求明确记为 **L3恢复准备**，不冒充新的冷A测量。它替代C3重复health的额度，保持C1=10、C3=7、总17。C3仍计划保留实际PID/listener/readiness和真实telemetry/生成验证。

## 实际请求与结果

| 范围 | 本轮实际 | 上限/复用 | 结果 |
|---|---:|---|---|
| 新native场景/提交 | 0/0 | 复用4/7 | 未重跑 |
| C1候选HTTP | 9 | 10 | 前8 complete；cancel原ledger unresolved，派生核对已知成功 |
| C3候选HTTP | 0 | 7 | 未启动，容量未测试 |
| 候选HTTP合计 | 9 | 17 | 未超过预算，无重发 |
| 恢复wire计账单位 | 4 | 4 | health1＋代理生成2（含上游）＋metrics1 |
| 窗口 | 3分10秒 | 硬上限40分钟，36分钟恢复预留 | 未超时 |

| C1项目 | 实际观察 | 结论 |
|---|---|---|
| restore-A-from-L3 | P20057，source=l3，restored/hit=20055，computed=2；job1 publication完成 | PASS；不是新冷A样本 |
| cold-B | P20057，source=none，computed=20057；job3完成 | PASS |
| warm-A | source=l2，restored/hit=20055，computed=2；job4完成 | PASS；真实L2，满足P−4门槛 |
| append-A | 从原A响应构建history；P20126，L2恢复20108，仅重算18；job5完成 | PASS |
| rewrite-A | P20060，full_reset；job7与实际lane/digest匹配并完成 | PASS；未把改写误算增量命中 |
| save/erase/restore | 实际slot0；保存/恢复20104 tokens、681130055 bytes；digest均为 `8d2234574661c5ea` | 3项PASS |
| cancel | 收到真实delta后断连；同server/规范ID/Engine7/internal request6，cancelled/O1，无完成export；随后client disconnected | 实际取消成功；采集器停测原件保留 |
| telemetry-after | 未发HTTP；已有取消后同server throughput显示running/waiting/prefilling/decode_ready均0 | HTTP附件缺口保留，不回填为已执行 |

L3准备请求在诊断O64处结束为`output_limit`，该事实保留；这不是Pi预算或模型质量结论。所有实际request/job/lane/digest、raw及export记录见[逐请求证据](../output/ninfer-v4-p2-http-remaining-20261022/evidence/campaign/c1/manifest.json)。

## 再次停测原因、修复及离线核对

这是我方驱动漏覆盖的取消合同，不是两次模型终态。NInfer现有`src/serve/http_server.cpp`在1218—1224行将不可写sink转为取消并先记录`request_done`；1247—1251行仍尝试写final SSE，`write_stream_item`在138—143行抛出`ClientDisconnected`，1260—1262行再记录`request_error("client disconnected")`。`concurrent_executor.h`的取消分支不发布completion export。本轮没有为此修改服务。

原客户端要求匹配到的终态只有一条，因此看见同请求的done和error就报`ambiguous concurrent request terminal`。原raw、错误、完整server-tail、失败账和冻结runtime-v1均保留。不能把原ledger的unresolved直接改绿。

仅修改隔离源码的`replay_agent.py`和`test_p2_replay_driver.py`：明确取消时允许唯一cancelled/no-job done，及最多一条**后继**精确disconnect error；server instance、规范ID、Engine ID、内部request ID必须一致。同请求的任何export、重复/乱序终态、其他错误仍拒绝。伴随error完整保存在派生结果，不静默丢弃。非取消路径维持原约束。

修复后源码树为 `ee49b8979f0d00c6add28328cfddd589f1cca136`，未commit/push/发布；本轮冻结runtime-v1不变。[增量补丁](../output/ninfer-v4-p2-http-remaining-20261022/client-cancel-repair-v2/cancel-companion-fix.patch)可以叠加原34d6树。

通过29固定BO的无GPU、network=none容器，仅执行新增3个`test_cancel_companion_*`用例，全部PASS；未重复旧10个已过用例。[完整命令及结果](../output/ninfer-v4-p2-http-remaining-20261022/client-cancel-repair-v2/verification.json)可复现。独立只读评审无剩余finding；真实取消raw/log的[离线核对](../output/ninfer-v4-p2-http-remaining-20261022/client-cancel-repair-v2/cancel-reconciliation.json)PASS，确认无未结束请求、无错误completion export、无重发，原ledger SHA未变。修复后没有新增HTTP/GPU请求。

## 原服务恢复与证据保全

原容器仍为 `86cb6d9ae7348fb928570e60290d2dc8ac933170a3c7bca32016ff347e2e1ddd`，原镜像仍为 `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`，新PID **59271**。完整argv、两个原二进制SHA、binds、cache路径及device/inode均与开窗前一致。原代理PID1950保持active/running，未停或修改。

health、经原代理的真实生成、processing/deferred=0均在4个恢复单位内验证。最终只读检查确认：候选容器已停，controller/guardian退出，GPU只有原服务，原请求无未结束项、scheduler.running/waiting=0。原代理直接PID-FD读取的历史权限限制仍披露为false；沿用同PID/start/argv/script/socket的连续性证明并实测代理生成，没有放宽候选PID/listener归属检查。

本轮770项远端文件共2,526,010,402 bytes已登记SHA/size，cache/slot/CUDA产物保留原路径；107项元数据、全部请求/raw/log及修复验证另已下载并逐项校验。[远端归档回执](../output/ninfer-v4-p2-http-remaining-20261022/evidence-collection-receipt.json)、[本机校验回执](../output/ninfer-v4-p2-http-remaining-20261022/metadata-collection-receipt.json)列明覆盖范围，未把只下载元数据说成完整payload已下载。旧590项cache和两个历史失败ledger均再次校验未变。V4原388份Markdown另有改前快照。

## 验收边界与剩余范围

**当前结论是P2最小验收NOT_PASSED/HTTP INCOMPLETE，完整P2-GATE仍UNQUALIFIED。** 原native、C1长前缀L3/L2、增量/改写、slot、实际取消已有证据；C3启动容量、并发请求/job/lane归属及其余HTTP合同尚无实机证据。18处G1严格差分、上游ancestry未提交、配对OFF/ON开销、长期allocator/正式性能与发布门禁仍独立，不因本次局部通过放宽。

冻结清单有8项HTTP未发，其中原C1末次telemetry无法在已退出的原候选进程上补采；现有同server取消后idle事件可复用，但保留缺失HTTP附件。后续不应为了补一个旧时点GET而重跑C1。最小新增实机范围可收敛为**C3的7个候选HTTP＋4个恢复wire单位、0 native、context/KV262144不降**，预计5—10分钟、硬上限仍40分钟；准备/归档时间另计。C3若容量不足即保留BLOCKED，不降context。

两个P2窗口累计12个候选HTTP、8个恢复wire单位；4个native仍只执行原先一次。两次采集器失败和全部成本分别保留。本轮恢复额度已用满，不再切换服务，也不把重启前的验活复用于下一窗口。后续须重新冻结有限窗口与恢复额度。未运行新采样、greedy proposal优化、旧Baseline、Pi或生产发布；没有实测加速和正式p95结论。
