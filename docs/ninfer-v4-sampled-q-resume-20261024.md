# 随机 MTP 接续结果：修复完成，未形成稳定提速信号

**测试工具的 Graph memset 预算问题已修复，剩余 6 个 Chat、7 个 wire 全部执行并取得完整终态。没有再次停测。** 复用已通过的 q/Graph/native 状态证据；三组质量通过的配对中，Java、中文推理单位 token 耗时分别增加 1.75%、0.67%，工具调用减少 3.11%。没有足够证据将随机 MTP 切为默认或进入生产发布。

本窗口 162.739 秒完成候选清理。原服务保持停止，镜像、argv、缓存目录身份不变；默认分派、Target temperature=1/top_p=0.95/top_k=20、Pi medium/32768 不变。Chat 原冻结夹具的 max_tokens=2048 保持原样，不是降低 Pi 预算。

## 修复与验证

原 65,536 次 memset 上限遗漏了 Graph 节点随每次 replay 累乘的成本。新账本按启动/direct 65,536＋每图 280 次清零×(本阶段请求数×2048＋9) 给出有限上限：raw 1,214,936，candidate 2,361,816；其他 13 项有限资源上限及调用前保护保持。实际分别使用 101,061、161,547 次，无超限。旧 tool 的 exit95、部分 SSE、无 DONE/terminal 和原 RESERVED 账本原样保留，新 tool 单列 attempt2。

只修改接续工具、资源预算与证据合并，不改 C++/CUDA 或模型二进制。两份服务逐字节复用原 BO 成功构建；本轮无需重新构建。新增 CPU 合同 5/5 PASS，覆盖仅未完成范围、累计预算/防重放、权威终态合并、Graph 资源公式、Target/owner 不变。独立代码评审没有阻塞 finding。

原数值 4 场景、8 direct、4 capture/8 replay 及 native 4 请求/8 decode 全部复用，未重跑：q 最大绝对误差 2.6411775e-8（门槛 5e-6）；真实 K3 条件 q、完整 canonical state、normal/partial/cancel 和 direct/Graph 的最小一致性通过。它不等于统计分布资格，native 固定诊断输入也不等于真实 Chat 性能。

[修复与预算推导](../output/ninfer-v4-sampled-q-resume-20261024/REPAIR-AND-BUDGET.md) · [CPU 原件](../output/ninfer-v4-sampled-q-resume-20261024/remote-final/evidence/CPU-continuation-r1.jsonl) · [工具评审](../output/ninfer-v4-sampled-q-resume-20261024/INDEPENDENT-REVIEW.md) · [旧 q/native 原始结果](ninfer-v4-sampled-q-hardware-20261024.md)。

## 实际性能

greedy 指草稿路线，Target 仍为原随机采样。下表 Program decode ms/token 的分母为实际 completion_tokens−1，包含 reasoning/tool token，首 token 来自 prefill。正变化表示候选更慢。

| 样本 | 质量 raw / sampled | 输出 token raw / sampled | Program ms/token raw / sampled | 候选耗时变化 | 草稿接受率 raw / sampled |
|---|---|---:|---:|---:|---:|
| java | PASS / PASS | 1088 / 1093 | 6.345327 / 6.456588 | +1.75% | 88.78% / 86.91% |
| reasoning | PASS / PASS | 571 / 621 | 6.102092 / 6.142919 | +0.67% | 93.33% / 92.68% |
| tool | PASS / PASS | 649 / 808 | 6.168453 / 5.976494 | -3.11% | 92.64% / 97.10% |
| control | FAIL_MODEL_BEHAVIOR / FAIL_MODEL_BEHAVIOR | 2048 / 2048 | 6.637100 / 6.435198 | -3.04% | 83.50% / 87.54% |

控制题两端都 finish_reason=length、2048 token、最终 content 为空，只有 reasoning。原始输出显示反复核对中文字符数，未在预算内交付要求的 JSON；按冻结断言均记 FAIL_MODEL_BEHAVIOR。完整响应并不等于质量通过，其约 3.04% 的单位 token 耗时降低不计有效收益。没有改夹具、提高预算、缩减断言或重跑。

| 样本 | 客户端 TTFT raw / sampled（秒） | 客户端完整请求 raw / sampled（秒） |
|---|---:|---:|
| java | 0.150496 / 0.324492 | 7.057150 / 7.386684 |
| reasoning | 0.143473 / 0.142516 | 3.629144 / 3.958232 |
| tool | 0.351618 / 0.221157 | 4.355133 / 5.052768 |
| control | 0.135624 / 0.135659 | 13.737334 / 13.322297 |

工具题接受率从 92.64% 到 97.10%，单位 token 耗时降低，但输出从 649 增至 808 token，整个请求反而从 4.355 秒增至 5.053 秒。Java/推理接受率也未共同改善，因此没有“一致增加接受率并显著缩短实际任务耗时”的采用信号。每题只有一对随机输出，不能把这些差异归因为稳定回退或收益，也不能仅凭结果断言 q 计算开销是瓶颈。

raw Java/推理复用上一窗口；本次不重复任何已结束 HTTP warmup，仍有服务原生启动/Graph 预热。新 raw 首题 tool、candidate 首题 Java，因此 TTFT 存在首请求与跨窗口差异。三个质量通过样本的完整请求都更长，同时输出长度不同；这不是等长、同内容、统计充分的吞吐实验。Program 时间不包含所有 host/scheduler/output 区间，完整 round wall 仍 null。没有汇总成一个“平均提速”掩盖边界。

## 计账与证据

| 项目 | 本次新增 | 两窗口累计（含失败） |
|---|---:|---:|
| Chat 模型请求 | 6，均完整 | 9 次正式 Chat：8 完整、1 旧中止 |
| native 模型请求 | 0 | 4，全部复用 |
| HTTP warmup | 0 | 1，完整复用 |
| 所有模型提交 | 6 | 14（13 完整＋1 中止） |
| wire | 7 | 12（11 完整＋1 中止） |
| GPU capture / replay | 18 / 1997 | 40 / 2493 |
| 算法 kernel 计账 | 1,627,289 | 2,044,488 |
| memset 次数计账 | 262,608 | 330,837 |

累计 GPU 值包含旧中断阶段调用前预留/已发起成本，不能一概当作全部同步完成工作；完整 14 项资源计数及各阶段上限见机器汇总和计划。新账本 COMPLETE，6 次模型请求各有唯一响应 ID、完整 SSE DONE 和 durable request_done。旧失败仍为原状态，没有补造完成记录。所有候选 PID=0、exit0，owner/guardian 退出，GPU 无计算进程，单 GPU lease 已释放。

新冻结回执 SHA256：`8213b6427eff4be604a49b0c7c780eb0a26a96cafb1300d5f3aeda7cf90dc512`。已消费入口：`/home/hhtele/ninfer-v4-sampled-q-resume-20261024/prepared-window-r2`，不得重启。源树仍 `b9d4bfb714d537e1b9a51d94d3716c9441035107`；两份服务 SHA 见冻结 source identity。

本地逐项验证 92 份文件与 22 项非二进制冻结文件 SHA；服务二进制在远端验证，未声称下载到本地。新原始 runtime 只读归档 `/home/hhtele/ninfer-v4-sampled-q-resume-20261024/execution-r2/full-runtime.tar`，1,075,200 字节，SHA256 `25b1b578c8728b325fb900b0203875ecfdcdf0f3befab68a16b624621560baef`。旧 4.17GB native 原始状态归档及所有原始失败保留，新 reuse-proof 绑定旧证据 SHA 和 drain 回执。

[机器汇总](../output/ninfer-v4-sampled-q-resume-20261024/final-summary.json) · [新计划/完整上限](../output/ninfer-v4-sampled-q-resume-20261024/remote-final/plan.json) · [冻结回执](../output/ninfer-v4-sampled-q-resume-20261024/remote-final/freeze-receipt.json) · [本地校验](../output/ninfer-v4-sampled-q-resume-20261024/local-verification.json) · [最终进程读回](../output/ninfer-v4-sampled-q-resume-20261024/remote-final/execution/final-readback.json) · [独立结果审计](../output/ninfer-v4-sampled-q-resume-20261024/INDEPENDENT-RESULT-AUDIT.md)。

## 结论与限制

`CONTINUATION_COMPLETE_NOT_QUALIFIED`：测试编排问题修复，授权接续已完成；q/状态最小正确性证据有效，性能没有形成稳定采用信号，控制题质量失败保留。默认路线保持 greedy，不切换生产，也不自动追加补测。分布、缓存恢复、模型活跃 penalty、真实每轮 wall 和生产发布资格仍未通过；p95=null、optimization_qualification=false。所有历史失败、18 处 G1 差异及 C1 附件缺口继续保留。

复现：CPU 使用本目录 `cpu_and_freeze.py` 所记录的无 GPU/无网络 BO 容器命令，结果已留存，不需重复执行；实机执行命令由 `launch_once.py` 和 `execution/launch-receipt.json` 绑定新回执，只允许本次一次性窗口；离线复核可运行 `python3 -B output/ninfer-v4-sampled-q-resume-20261024/verify_and_summarize.py`，不产生 GPU 或模型请求。
