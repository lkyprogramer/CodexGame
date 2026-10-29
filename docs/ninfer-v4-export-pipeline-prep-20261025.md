# 导出与 CPU 发布修复：实机对照工具与空账本冻结

2026-10-25 经 `jssh 29`（`ssh -J jump 29`）完成现有控制器的窄适配、14 项新工具 CPU 合同、真实旧日志的离线解析核对及独立集成复审。**新窗口已冻结，账本全0，尚未执行实机。** 状态为 `CPU_ONLY_PREPARED_FROZEN_NOT_EXECUTED`。

本轮 GPU、模型、推理 HTTP 请求均为0。原 GPU 服务继续停止，镜像、启动参数及缓存目录身份一致；模型文件 stat 未变，沿用历史模型 SHA，未重算18GB模型摘要。没有修改产品源码或 serve、默认分派、Target采样或Pi medium/32768，没有重新构建或重跑旧 Baseline、native、前轮10项产品CPU合同及frontend预检。

## 冻结身份

- Profile：`P4_EXPORT_PUBLICATION_PIPELINE_HTTP_V1`
- 远端窗口：`/home/hhtele/ninfer-v4-export-pipeline-prep-20261025/prepared-window-r1`
- **Freeze SHA-256：`0dca60d4e89be0205011b30bb8824154eca74aed209620b36337419c7edbeb4a`**
- 工具归档 SHA-256：`9e8046824552b188cb2f222a462ec8d2211d0d0636a140a2e9268040ce536386`
- 原 P4 serve：`8884da24e63856355a2db1048c942452fe6bdd6d25aaaf517cb162f231ad8846`
- 修复 P4 serve：`9b6fed4a0e1e3b0af1dbd196a0eae158c11aa03a368fbe3df0f8db65fdbfd0d3`

两端产品基点均为P4树 `35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`；修复候选树 `7477294d629edffddef713d22c2d7589493d4271`，直接继承P14诊断树 `d002a2183d54e1562cd1f53c50cf47155b1cb38f`，产品构建的trace关闭。补丁与构建沿用[上一轮已完成的证据](ninfer-v4-export-pipeline-20261025.md)。本轮没有加入其它优化。

[冻结回执](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/prepared-window-r1/freeze-receipt.json) · [空账本](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/prepared-window-r1/budget-ledger.json) · [最终远端回读](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/evidence/final-readback.json)

## 已补齐的执行和验收行为

复用P14的 `controller.py`、owner/guardian、WireJournal、ChatSSE、request-ID关联及freezer，共窄改8个既有工具文件，没有另建控制器。移除该profile的native执行入口和BO/旧codec分支；只允许原P4→修复P4，两端schema22/midrise `rk4v4`、C1/W4/K3、context/KV262144、prefill1024、Target T1/p0.95/k20、medium/preserve-thinking、output32768。

原四个HTTP输入字节与P4 token/position证据直接复用，原预检完整文件SHA `8385f7014a1e0c290e6ffa76a80e889942694f7b99ef852b177605ca850cbe78`。四个输入分别569、593、16993、17049 tokens，没有重新执行tokenizer/frontend任务。新窗口使用独立请求标识和空私有缓存目录，不复用旧执行状态。

1. 短冷和短热在EOF及必要durable核对后立即接续，不先等待后台publication。实际短热必须来自L1，长热必须从L2恢复正数bytes/tokens，才能取得对应性能比较资格。
2. 仅在长冷→私有slot擦除前等待其关联的stable boundary publication成功，并使用准确retained digest；session成功不能代替boundary成功。
3. 最终Chat和telemetry之后，先核对候选容器、PID/start/argv、listener与原服务身份，再记录SIGTERM意图并只发一次信号。**SIGTERM之前不等待最后publication完成。**
4. 最多30秒内、且不跨越第17分钟清理线，要求自然exit0、无OOM、无重启，保留日志至正常退出或故障清理完成。超时、137、缺终态、残缺JSONL或身份变化均失败保全，不自动重发请求。
5. 退出后逐项重连四个Chat的canonical request ID、HTTP/Engine/instance和声明的export job；缺失、重复或错配会显式列为证据缺口，并禁止完整修复/性能资格。不能只检查最后一个job。
6. SIGTERM记录发送前与返回后的宿主monotonic时间区间：publication在返回后完成才是 `LIVE_DRAIN`；发送前已完成是 `IDLE_CLOSE`；落在区间内是 `SIGNAL_INTERVAL_INDETERMINATE`，不声称活跃排空。
7. 可见export job按发布完成时间验证顺序；完整队列FIFO仍复用已有CPU合同，因为host-only发布不产出export事件，job序号不必连续。只有后一个导出开始且source释放均早于前一个publication完成，才记真实重叠。

任何可见publication失败或声明job的证据缺口，都明确使本轮功能/机制验收失败并排除性能比较，原始耗时保留。没有其它失败但未观察到重叠时为机制证据不足。queue已包含restore，不重复相加；报告queue、prefill、首个语义delta TTFT和完整HTTP wall，不将其解释为decode算力改善。

[冻结控制器](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/prepared-window-r1/tools/controller.py) · [HTTP与关闭合同说明](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/prepared-window-r1/tools/HTTP-DRIVER.md)

## 实际CPU验证与评审

在既有BO镜像、`--runtime=runc --network=none`、无GPU设备且无模型挂载的容器中执行：

```bash
python3 -m unittest -v test_cpu_tools
```

**14/14通过，测试10.910秒，整个CPU容器调用约11.45秒。** 覆盖新阶段/预算/截止、未知账本不重放、两端相同服务合同、关闭身份不匹配不发信号、只发一次SIGTERM、超时/137/缺终态/重启拒绝、三种时间分类、真实重叠与可见FIFO、四Chat发布覆盖、失败资格门控，以及真实两份二进制和原预检输入的临时freeze/哈希/单次使用验证。临时测试账本与正式空账本分离。

另在29仅对已有P4原始JSONL与四个outcome运行新解析器：识别原可见job2/3/4/6及合法序号空档；保留原L1/L2分类；明确识别long-warm所声明job7缺发布终态。**这是旧证据的离线合同核对，不是重跑测量，也没有将旧缺口改成PASS。**

[CPU原始结果](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/evidence/cpu-r1/stderr.log) · [CPU容器回执](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/evidence/cpu-r1/receipt.json) · [真实旧日志解析结果](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/evidence/existing-record-parser-check.json)

独立初审发现“可能遗漏早期Chat声明的发布终态”的门控缺口，已在首次测试与冻结前修复，最终复审无阻塞发现。[初审记录](../output/ninfer-v4-export-pipeline-prep-20261025/evidence/review-r1.md)与[最终复审](../output/ninfer-v4-export-pipeline-prep-20261025/evidence/review-r2.md)均保留。评审者只读，未运行测试；上述CPU执行由主代理完成。

## 已冻结的最小实机预算

| 项目 | 合计上限 |
|---|---:|
| native / native decode | 0 / 0 |
| Chat：每端短冷、短热、长冷、L2长热 | 8 |
| 内置启动warmup（无额外warmup POST） | 2 |
| 模型提交总数 | 10 |
| wire：每端4 Chat＋health/私有slot erase/telemetry | 14 |
| 硬限 / 开始清理 | 20分钟 / 第17分钟 |
| 每端自然关闭等待 | ≤30秒，受清理截止约束 |

运行时每端4 CPU、24GiB容器内存、256 PID、L1/L2为6144/8192MiB，一次只运行一个GPU候选。两端端口19528/19529在最终核对时空闲。HTTP逐kernel、capture/replay及辅助传输计数不可观测，冻结值为`null`，不冒充0或套用native预算。

准备已完成。**后续实机预计6–10分钟，硬限20分钟；证据核算和报告另约20–40分钟。** 窗口时间在以后明确授权执行时开始计时，当前没有运行中的窗口或guardian，不自动启动。

仅做身份/空账本核对的命令已实际执行并通过：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 /home/hhtele/ninfer-v4-export-pipeline-prep-20261025/prepared-window-r1/tools/controller.py \
  --root /home/hhtele/ninfer-v4-export-pipeline-prep-20261025/prepared-window-r1 \
  --plan-only --freeze-sha 0dca60d4e89be0205011b30bb8824154eca74aed209620b36337419c7edbeb4a
```

[严格计划](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/prepared-window-r1/plan.json) · [冻结准备回读](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/evidence/freeze-attestation.json)

## 保留限制与交付

CPU合同中的信号和容器状态为受控输入，不能代替真实SIGTERM排空。现有产品signal handler会进入带mutex的停止路径；析构顺序能保留日志接收端，但不能静态承诺30秒内退出。本轮只准备严格观测与失败保全，没有顺带修改信号实现。真实D2H排空、主机内存峰值、缓存效果及queue/TTFT收益仍未验证。

原P4 job7缺口、旧HTTP退出137、BO两次publication失败、18处G1差异、C1附件缺口及Baseline全部历史失败/附件缺口保留。不因新驱动准备完成而宣称优化或生产验收通过：`p95=null`、`optimization_qualification=false`、`production_release_qualified=false`。

远端20项冻结文件逐SHA验证；31项导出的工具/账本/预检/CPU和身份材料已在本机逐SHA核验。两份约262MB的serve保留在远端冻结目录，本机交付不重复下载二进制载荷，其SHA与位置完整保留。旧工具、旧窗口及旧报告不覆盖。

[机器汇总](../output/ninfer-v4-export-pipeline-prep-20261025/final-summary.json) · [交付回执](../output/ninfer-v4-export-pipeline-prep-20261025/delivery-receipt.json) · [导出校验清单](../output/ninfer-v4-export-pipeline-prep-20261025/remote-evidence/evidence/export-file-checksums.json)
