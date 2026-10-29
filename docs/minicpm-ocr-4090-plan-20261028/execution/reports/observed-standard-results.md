# 标准解码已观察结果与最终汇总入口

## 停止状态与最终执行终态

用户已明确“不再继续测试，基于已有数据最终对比汇报”。所有新测试、模型调用、预解码、单测与部署停止；后续仅整理已有归档，不把准备项写成即将运行。

root于2026-10-29 14:09:35 CST实际readback：66 paired均终态，65 PASS、1 FAIL（原Ovis D0 p4 `p06-1` 的图内补读4096输出截断保留）。Mini E0接纳窗实际3600.0042597秒，admitted=terminal=pass=437、drained=true、PASS；Ovis E0接纳窗实际3600.0024557秒，admitted=terminal=1523、pass=1521、2 FAIL、drained=true，故wrapper FAIL、master sequence FAIL。9 steps全部终态，steps_not_run=0。排空不代表全部识别成功，也不代表资源稳定性完整验收。

Ovis E0的两次FAIL为 `E0-C0005-P010` 与 `E0-C0017-P010`，同一原PDF-001-p010图内补读，均378 prompt＋4096 completion=4474 tokens、finish_reason=length / TRUNCATED_OUTPUT；原分母和失败保留，不重跑覆盖。原187/74评分、冻结阈值和旧历史快照均不改。

14:09:50 root核对全部source_hashes未变；标准Mini/Ovis容器均stopped，GPU compute apps为空。旧CPU OCR保持同一容器ID（前缀13c9）、同StartedAt `2026-10-28T09:05:17.890543747Z` 且healthy。该证据由root实际读回，本次文档整理未执行29命令。

新增43 controls、24基页/164 variants、chart10、pure6、P05、F07新OS component及F09新SSE仅准备、未执行，按用户要求停止，保留NOT_RUN/GAP。DSpark为NOT_RUN / NOT_ADMITTED_QUALITY_GATE。宏CER的Mac本地a536修复及既有31项PASS保留，但29旧42153评分源不再部署；不称远端已修或全部关闭。已有归档的资源、正式速度、能耗与RSS/显存等离线分析已完成，见[最终对比报告](final-comparison-20261029.md)和[正式性能CSV](final-performance-20261029.csv)；D0 p4失败组CI不可用，Ovis E0两次失败保留，不将资源分项PASS改写为全项通过。

快照日期：2026-10-29。本文记录已完成的 S0 全量标准解码诊断，以及已完成执行与离线汇总的入口。**Ovis 420/420、Mini 419/420 是解析完成数，不是文字准确率，不能仅据这些执行数作质量或正式性能排名。** 已完成的AI评分、场景差异与失败见[主评质量结果](ai-quality-results.md)及[补充AI结果](supplement-ai-results.md)。

本次整理只读取本地已回传的运行元数据及现有文档，没有访问29、读取 sealed-map 或审阅匿名候选正文。29任务根为 `/data/ocr/dual-ocr-20261028`。部署与比较合同见[统一方案](../../comparison-plan.md)、[部署细节](../../deployment-details.md)和[Ovis部署](../../ovis-deployment.md)。

## S0 标准解码诊断

| 指标 | OvisOCR3 | MiniCPM-OCR-1.0 |
|---|---:|---:|
| 运行目录标识 | `ovis-full-c0-v3` | `mini-full-c0-v3` |
| 计划 / 接纳 / 终态输入单元 | 420 / 420 / 420 | 420 / 420 / 420 |
| 解析 PASS / 非 PASS | 420 / 0 | 419 / 1 |
| 文档产物 PASS / 计划文档 | 93 / 93 | 92 / 93 |
| completion 调用数（含恢复预热字段口径） | 652 | 4654 |
| 实测批次墙钟，秒 | 2011.350715 | 2767.172343 |
| `run_status` | `COMPLETED` | `COMPLETED` |
| `primary_performance_eligible` | false | false |
| 已记录的不具备主性能资格原因 | `COLD_ADAPTER_NO_SAME_WORKER_WARMUP` | `COLD_ADAPTER_NO_SAME_WORKER_WARMUP` |

分母是冻结清单的420个输入单元，包含页面、长图、裁剪和场景图，不能统称420张独立试卷或420个独立源家族。输入来源及划分见[资料执行记录](../../corpus-execution.md)。`COMPLETED` 表示执行器完成该固定任务流，不表示所有页面成功，也不表示文字、表格、公式与图内字已验收。

两批均没有同一持久 worker 的开发预热，不具备正式性能资格；既有实施记录还保留了 Ovis 批次的构建干扰。因此这里只保留原始墙钟与调用数，不计算横向正式速度比或胜者。Ovis 使用修正后实际生效的顶层预处理参数；旧嵌套 `images_kwargs` 运行与定向补跑保留为历史诊断，不拼接成新全量结果。参数更正过程见[实施记录](../../execution-report.md)。

### Mini 已确认失败

`LOCAL-GOVPDF-01-p003` 的 `block-0016` 发生真实截断。该页结果保留 `TRUNCATED_OUTPUT`、`TRUNCATED_FINISH_REASON_LENGTH` 与 `ONE_OR_MORE_MODEL_CALLS_FAILED`；对应 `mini:16:image` 请求为 `status=FAIL`、`finish_reason=length`，输入1491 tokens，输出4096 tokens，总计5587 tokens。

这证明该区域在冻结输出上限处截断，不能因请求返回 HTTP 成功、页面其他区域完成或文档仍有部分导出而改记 PASS。它也不是本次请求16K总上下文耗尽的证据。该失败继续保留在420分母内；任何后续改预算或重跑必须另列配置和运行，不覆盖原批。

## 证据定位

本地回传元数据：

- `/private/tmp/ocr-ai-judge-20261029/candidate-runs/ovis-full-c0-v3/summary.json`
- `/private/tmp/ocr-ai-judge-20261029/candidate-runs/mini-full-c0-v3/summary.json`
- Mini失败页的 `pages/LOCAL-GOVPDF-01-p003/result.json`，本次仅检查状态、错误、finish reason及usage元数据，没有审阅识别正文。

本次读取的summary SHA256：Ovis `6943249c3a28a5623dcde7d0e2aa1a958cf69afb572070d73da11f3ee80194b4`；Mini `8669413156d8d9ce68c97b3a9ebad238ff7198bd253c377ed6a0eb583cd8f4b5`。

运行目录名相同不代表源码、资源和预热合同相同。正式比较还需对应冻结计划、effective-config、像素及源哈希、运行时策略、事件与资源采样共同通过核对。

## 已完成的正式执行与离线汇总

**历史实际readback快照：2026-10-29 13:08:14 CST。** root经ssh29读回Mini E0 wrapper PASS；summary为 `run_status=COMPLETED`、`endurance_status=PASS`，submitted=terminal=pass=437，`admission_elapsed_seconds=3600.0042597170686`，`admitted_workload_drained=true`。父sequence的last_step已记录Mini、kind=E0、PASS；master PID `1745300` 实际匹配，主sequence仍RUNNING。Ovis当时NOT_STARTED，后续串行执行，不推断已开始。

这是Mini E0的实际接纳、执行与排空证据；RSS增长、显存余量、采样完整性和能耗尚待离线分析，不能把wrapper PASS写成完整稳定性验收。正式66轮仍保留65 PASS、1 FAIL，原截断及187/74评分不变，不发布新性能赢家。

**历史实际readback快照：2026-10-29 12:07:31 CST。** 主配对66/66 trials已终态，65 PASS、1 FAIL；不是66次质量通过，也不代表全部测试结束。R0 c1/c2/c4各6/6 PASS，D0 p1/p2各12/12 PASS，D0 p4为12/12终态、11 PASS/1 FAIL，P0子组12/12 PASS。唯一失败仍是原Ovis D0 p4 `p06-1` 图内文字补读截断，原run与失败均保留。正式性能CI及资源报告仍待汇总，不发布全部性能赢家。

主sequence仍RUNNING；root实际核对master PID `1745300` 的argv匹配本序列。Mini E0 wrapper与entry均RUNNING，已开始3600秒接纳窗，截止后按合同排空；实际 `timed_workload_start` 的batch_start_monotonic对应约12:07:08，12:07:31读回时elapsed约23.5秒。Ovis E0为NOT_STARTED、后续串行执行。父sequence只在run_e0返回后append该step，不能因last_step仍显示P0 PASS就判断Mini E0未开始；不根据时钟推断接纳窗已结束、已排空或验收成功。此处不发布尚未核全artifact的逐页总和，不给总完成百分比，原187/74评分不变。

**历史实际readback快照：2026-10-29 10:41（北京时间）。** 正式序列仍RUNNING，66 trials中53个已终态，首次出现1个执行FAIL；不推断此后的数量或序列终态。

失败trial为 `g3g4-e0-r1-g4-d0-p4-p06-1-ovis`：49个输入均已submitted/terminal，48 PASS、1 FAIL，`run_status=COMPLETED`、executor exit 1，文档产物2/3通过。失败页 `PDF-001-p010` 最后一次图内文字补读 `b0014` 为 `finish_reason=length`、request status FAIL / `TRUNCATED_OUTPUT`；输入378、输出4096、总计4474 tokens。顶层错误保留 `TRUNCATED_OUTPUT` 与 `ONE_OR_MORE_MODEL_CALLS_FAILED`，执行完成不等于全部成功。

该轮service.log实际存在且capture exit 0；精确检索 `CUDA OOM` / `OutOfMemoryError` / `EngineDead` / `Traceback` / `ERROR` / `500` 未见匹配，源码和manifest changed列表均为空。此证据指向输出上限截断，**不是16K上下文耗尽，也不是观察到OOM**；日志未匹配不构成对所有潜在故障的排除证明。原run失败保留，不加预算或重跑覆盖。D0 p4该配对不能发布正式CI赢家，其他组独立评估；原187/74质量评分不变，尚无全部性能赢家。

**历史root实际readback快照：2026-10-29 09:49:17 CST。** `sequence-g3g4-e0-r1` 为RUNNING，正式计划66 trials中已有44个trial终态、0个失败。这里是运行/执行状态，**不是44次质量验收PASS**；没有正式速度赢家，不按未完成或成功子集发布主比较。以下进度仅对应该时间点，不推断其后状态。

| 计划组 | 输入 | 页面接纳 | 区域上限 | 配对块 / 计划trial数 | 该快照执行状态 |
|---|---|---:|---:|---:|---|
| G3 R0 c1 | 同一 mixed100 | 4 | 1 | 3对 / 6 | 6/6终态，执行PASS |
| G3 R0 c2 | 同一 mixed100 | 4 | 2 | 3对 / 6 | 6/6终态，执行PASS |
| G3 R0 c4 | 同一 mixed100 | 4 | 4 | 3对 / 6 | 6/6终态，执行PASS |
| G4 D0 p1 | 三份完整原PDF，共49页 | 1 | 4 | 6对 / 12 | 12/12终态，执行PASS |
| G4 D0 p2 | 同上 | 2 | 4 | 6对 / 12 | 12/12终态，执行PASS |
| G4 D0 p4 | 同上 | 4 | 4 | 6对 / 12 | 2/12终态；运行中的p02-1-ovis为5/49输入单元 |
| G4 P0 | 同一 selected40 预渲染输入 | 1 | 4 | 6对 / 12 | 未开始 |
| E0 | 同一三文档49张预渲染图循环 | 4 | 4 | 每模型一次3600秒接纳窗并排空 | 两模型均未开始 |
| G7 DSpark | Mini标准与DSpark内部配对 | 依冻结计划 | 依冻结计划 | 依已准备入口 | NOT_ADMITTED_QUALITY_GATE，GPU未运行 |

正式66 trials须保留全部计划试验，按profile、输入范围、页接纳和区域上限分别报告；不把成功子集拼成主比较。配对缺失、失败、像素或策略不可比时，正式配对结论不可得，原始诊断仍保留。D0只有三份原文档，不能将其配对重复当作新增独立文档家族或外推到所有文档。

E0以同一持久worker池运行，预热后接纳3600秒，截止后按原deadline排空。验收目标为至少300实际完成页；候选池未接纳项单列，不当作提交或失败。重复输入不增加独立质量样本，E0固定不具备主性能比较资格。源状态、接纳数、终态数、排空和最低完成数见最新终态；资源分段、RSS门、采样时间覆盖与显存余量均已完成已有归档分析，结论和口径见[最终对比报告](final-comparison-20261029.md)，不再新增实测。

## 质量与指标填充边界

用户已指定由助手验收打分，依[AI裁判方案](../../ai-judge-plan.md)执行。本文仅记录执行与性能证据边界；已交付的187主评、74专项及明确参考覆盖的AI文本CER见[主评报告](ai-quality-results.md)和[补充报告](supplement-ai-results.md)，不能因本页未重复评分而理解为尚无质量验收。严格结构GT或必需指标不足的good-page/s不由AI均分硬换算。正式人工金标仍为0；AI裁判结果需要保留参考来源、核对覆盖率和独立样本单位，不能改称人工金标。

后续填写应同时给出固定分母墙钟、解析完成与尝试吞吐、延迟观察数和p50；观察数不足200不报p95，不足1000不报p99。资源积分使用正式开始至实际批次结束窗口，区分GPU板卡焦耳、cgroup CPU时间、采样RSS和VRAM；无CPU功率计和整机功率计时不报告其能量，无电价不折算费用。

服务器Prometheus快照覆盖开发预热、恢复及正式API请求。TTFT/TPOT、prefill/decode直方图sum/count增量只能标为该API层口径，不能称正式整页TTFT；非流式客户端没有直接测量首token时间。缺文件、计数器重置或采样窗口不完整时保留不可得。

上层状态入口已同步S0诊断完成。主评质量另见[公开AI质量结果](ai-quality-results.md)；正式66 paired与两次E0终态见上，资源/正式速度离线汇总已完成，见[最终对比报告](final-comparison-20261029.md)及[性能CSV](final-performance-20261029.csv)；DSpark及未执行专项按用户要求停止，不再补跑。
