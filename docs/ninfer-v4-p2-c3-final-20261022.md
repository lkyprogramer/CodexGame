# P2 最小功能验收通过：C3 七项完成，原服务已恢复

**按本次限定范围，P2 最小功能验收通过，保留 C1 最后一次 telemetry HTTP 附件缺口。** C3 的7个候选HTTP全部通过；复用既有4个native及C1功能证据，未重跑。两次历史采集器失败、原ledger及成本均保留。完整P2-GATE仍为UNQUALIFIED，生产发布未执行。

2026-10-22 **21:33:56—21:38:30（Asia/Shanghai）**，通过`jssh 29`完成独占GPU窗口，实际 **273.323946秒（4分33秒）**，远低于40分钟硬上限。原容器、镜像、完整参数与缓存目录已恢复，4个恢复计账单位内完成健康、原代理真实生成及队列排空验证。没有修改采样、context/KV262144或Pi medium/32768预算；本轮Pi请求为0。

[汇总账本](../output/ninfer-v4-p2-c3-final-20261022/final-summary.json) · [逐请求账本](../output/ninfer-v4-p2-c3-final-20261022/evidence/campaign/campaign.json) · [恢复验活](../output/ninfer-v4-p2-c3-final-20261022/evidence/restoration.json) · [最终只读核查](../output/ninfer-v4-p2-c3-final-20261022/final-live-validation.json)

## 身份、冻结与预算

隔离分支为`codex/p2-async-export-20261022`，源码树为`ee49b8979f0d00c6add28328cfddd589f1cca136`。这次真实使用取消修复后的客户端，复用原r5的未变C++二进制；`ninfer-serve` SHA256仍为`c08d46f2c06179c0f713f556c199eac2d4052868a3266c2a6c979ea6c1ec16a6`。未commit、push或发布。

新持久根为`/home/hhtele/ninfer-v4-p2-20261022/hardware/c3-final-20261022`。先冻结工具、原失败只读引用、C1附件缺口和空campaign，再启动窗口。C3专用工具只有7请求额度，不存在C1/native入口；6项新host测试、29固定BO/runc/network=none/无GPU的实际文件校验及独立只读评审通过。评审发现请求附件序列化与wire不一致的问题，已在冻结前修复，并逐项断言SHA一致；未消耗模型请求。

[冻结清单](../output/ninfer-v4-p2-c3-final-20261022/evidence/script-freeze.json) SHA256为`0c0bbb3dde4cb749c33db5a5ca1aa6e8551511aac799555efc91f7212aa5a5fd`；[回执](../output/ninfer-v4-p2-c3-final-20261022/evidence/freeze-receipt.json)绑定客户端、normalizer、wrapper、历史两份失败ledger、原native结果与C1日志。请求在wire前持久预留额度，逐请求检查候选PID、ELF和监听归属；未知结果禁止重发或隐式续跑。独立guardian负责36分钟恢复边界与40分钟硬上限，实际无需触发超时恢复。

| 计账项目 | 实际 | 上限/复用 | 结果 |
|---|---:|---|---|
| C3候选HTTP | 7 | 7 | 全部complete，无重发/未知 |
| C1请求 | 0 | 0 | 未重跑，原附件缺口保留 |
| 新native场景/提交 | 0/0 | 0/0 | 复用原4场景/7提交 |
| 恢复wire单位 | 4 | 4 | health1＋代理生成2（含上游）＋metrics1 |
| 窗口wall | 4分33秒 | 40分钟 | 恢复验活在截止内完成 |

三个P2窗口累计19个候选HTTP、12个恢复wire单位；4个native始终只执行原先一次。首次3HTTP关联失败、第二次9HTTP取消采集失败和此次7HTTP分别记账，不把失败成本抹掉。

## C3 结果

实际配置为C3、context/KV262144、E8、MTP3/原lm-head-draft、prefill1024，原T1/top_p0.95/top_k20/presence0及默认32768保持。候选只挂载私有cache/log/slot，未挂载原生产cache；没有以降context解决容量问题。

7请求依次覆盖：telemetry-before、cold-A、并发cold-B/warm-A、rewrite-A、cancel、telemetry-after。每个生成请求都绑定响应规范ID、真实Engine ID、lane、digest及唯一完成export job；并发时不依赖发送顺序或数组下标关联结果。具体token、缓存来源与导出结果由原始events和汇总账本逐题保留。

| 生成请求 | P / O | Engine / lane / job | 实际复用与终态 |
|---|---|---|---|
| cold-A | 20057 / 35 | 2 / 1 / 4 | full_reset；两alias成功 |
| cold-B | 20057 / 59 | 4 / 2 / 7 | full_reset；两alias成功 |
| warm-A | 20057 / 64 | 3 / 1 / 6 | L1复用20055，重算2；session成功，output_limit |
| rewrite-A | 20060 / 47 | 5 / 0 / 8 | L2复用共同前缀20042，重算18；两alias成功 |
| cancel | 20057 / 1 | 6 / 0 / 无job | cancelled；精确disconnect伴随错误保留，无export |

warm-A的output_limit为原诊断O64实际结果，不是质量通过或Pi预算耗尽结论；请求/输出均保留。并发pair使用两个lane，未把C3配置上限3称为已测三条同时执行。

warm-A在C3的真实L1复用了20,055 tokens，P20057，仅重算2，满足P−4门槛。L1代表驻留状态复用，不冒充L2导入。取消请求在收到真实生成delta后断连，记录cancelled且无完成export；修复后的客户端正确处理并保留伴随的`client disconnected`事件，没有再次停测。末次telemetry确认running/waiting=0。

[并发证据](../output/ninfer-v4-p2-c3-final-20261022/concurrency-evidence.json)区分请求生命周期与执行器状态：cold-B和warm-A使用不同Engine ID/lane，各自规范ID/job关联正确；请求生命周期重叠6.795秒，区间内两次日志采样均为running=2、prefilling=1、decode_ready=1。此项证明已准入lane的重叠，不声明CUDA kernel实际并行或实测吞吐收益；本轮没有GPU trace。

[资源快照](../output/ninfer-v4-p2-c3-final-20261022/resource-snapshots.json)保留真实前后GPU、allocator分类、slot与scheduler数据。有限窗口的空闲终态不能证明长期无泄漏、持续allocator稳定性、完整262144-token长请求容量或完整ResourceRecovered断言；相关正式门禁仍保留。实测前后sequence容量均为5,815,866,624 bytes，workspace容量均为180,953,088 bytes且used归零；NVML占用由24,819,269,632增至24,821,366,784 bytes（+2MiB），保留差值而不宣称全部GPU字节回到原值。

## 原服务恢复与历史证据

恢复同一原容器`86cb6d9ae7348fb928570e60290d2dc8ac933170a3c7bca32016ff347e2e1ddd`，原镜像`sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`，新PID **63407**。原完整argv、两个原二进制SHA、binds、cache路径和device/inode均与开窗前一致。原代理PID1950始终active/running，未停止或改写。

恢复后健康、经原代理的真实生成、processing/deferred=0均通过，候选容器停止，controller/guardian退出。原代理直接PID-FD读取的历史权限限制仍如实保留，沿用同PID/start/argv/script/socket连续性并以真实代理推理验活；候选PID/listener归属检查未放宽。

[首次失败报告](ninfer-v4-p2-hardware-20261022.md)和[第二次失败报告](ninfer-v4-p2-http-remaining-20261022.md)均保留。两个旧ledger仍保留原始unresolved值，独立派生核对已确认语义未知请求为0；此次不覆盖旧记录。原C1最终GET附件依然缺失，复用的是同server取消后throughput中running/waiting/prefilling/decode_ready=0的真实日志，不重新生成旧时点HTTP，不称缺失附件已找回。

本轮原始request/raw/result/events、完整server日志、状态、工具及部署身份进入持久目录与SHA清单；大cache/CUDA产物保留远端原路径，元数据及全部请求/响应另下载校验。本轮868项远端文件共2,085,489,188 bytes已登记SHA/size；97项元数据和所有请求/响应下载校验通过，cache/CUDA大文件留在远端原路径，未声称已全量下载。[远端回执](../output/ninfer-v4-p2-c3-final-20261022/evidence-collection-receipt.json)和[本机校验](../output/ninfer-v4-p2-c3-final-20261022/metadata-collection-receipt.json)保留。原388份V4文档有改前快照，后续只更新真实状态，不改具名断言和依赖。

## 验收结论

| 层级 | 结论 | 边界 |
|---|---|---|
| 本轮C3最小HTTP | PASS，7/7 | 相同配置成功启动并完成本轮负载，非全长容量证明 |
| P2最小功能收尾 | PASS_WITH_DISCLOSED_C1_ATTACHMENT_GAP | 复用4native及C1结果；原两次失败和C1附件缺口保留 |
| 完整P2-GATE | UNQUALIFIED | 完整P1前置、18处G1严格差分、上游ancestry、配对开销及长期资源等未由此窗口补齐 |
| 生产发布/性能采用 | NOT_RUN | 现网恢复原版本，p95=null；没有优化收益或新sampling资格结论 |

**本次授权的最小实机范围已完成，不再追加HTTP/native/GPU。** 完整验收和生产发布门禁继续独立；未自动进入P3或更宽矩阵，未重跑旧Baseline、BO、G1、P1、Pi或grader。
