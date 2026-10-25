# 导出与 CPU 缓存发布串行阻塞：隔离修复与 CPU 验证

2026-10-25，经 `jssh 29` 等价入口 `ssh -J jump 29` 完成隔离补丁、BO 构建、10 项 CPU 合同及独立集成复审。状态为 **`CPU_VERIFIED_BUILDABLE_HARDWARE_NOT_RUN`**。修复了源码中已定位的跨 job 串行依赖；**真实 queue/TTFT 收益尚未测量**。本轮 GPU、模型、推理 HTTP 请求均为 0。

原服务保持停止，容器 ID、镜像、启动参数摘要、缓存目录设备/inode 均与已有冻结证据一致；GPU 无计算进程。未改 kernel 默认分派、Target 采样、Pi medium/32768，不重跑旧 Baseline 或旧实机场景，不重开关闭实验，不部署或提交代码。

## 原因与修改

[P1—P4 实测](ninfer-v4-p14-performance-hardware-20261025.md)已记录：P4 前一个 CPU 发布阻挡下一个 GPU 导出，后者又通过 lane barrier 阻止 C1 准入。job3/job4 分别等了约 1.197/3.124 秒才开始导出，且都紧接前一 job 的 publication 完成；自身导出仅约 90ms。这条链有源码和实测时间关联，不能把全部发布耗时归给 SHA 或缓存锁。

现在使用一个导出线程、单槽有界交接、一个 FIFO 发布线程。后续 job 可以在前一个 job 做 CPU 发布时完成导出。原 GPU fence/失败排空路径不变，lane reader 仍只在导出完成或失败排空返回后释放，并且释放发生在等待 ready 槽容量之前。CPU 发布仍逐项串行完成，未把发布顺序改成并行竞争。

- 发布完成序号只在 CPU 发布终态之后推进；GPU 复制结束不会冒充 alias 发布完成。
- ready 与 ingress 在原 publication mutex 下共同参与 session 合并。沿用 head/generation/parent CAS；新任务入队成功后才使旧 ticket superseded、释放旧 stable-flight。保留旧导出任务的 boundary 与终态观测，活动 producer/consumer 的私有任务不参与合并。
- 关闭先停止入队，等待导出端排空，再等待发布端排空；线程启动失败会回收已经启动的线程。
- 单槽只限制新交接层：最多一个 ready、一个 producer 私有项和一个 consumer 私有项。原 prefill ingress 的完整镜像、boundary/session 复制及缓存载荷不在此计数内。额外重叠可能增加主机内存，**不是全局三镜像上界或显存优化**。

修复没有减少 CPU 发布自身的工作，也不宣称提高 GPU decode token/s。它针对本次已观察到的 Chat 准入阻塞。

## 补丁与身份

| 项目 | 身份 |
|---|---|
| 隔离分支 | `codex/p14-export-publication-20261025` |
| 远端根 | `/home/hhtele/ninfer-v4-export-pipeline-20261025` |
| 产品 P4 原树 | `35d3dd9e4aa96b1f56f2e9c55482946bd9911cde` |
| 本次直接基点：已有 P14 P4 诊断树 | `d002a2183d54e1562cd1f53c50cf47155b1cb38f` |
| r2 最终暂存树 | `7477294d629edffddef713d22c2d7589493d4271` |
| BO 镜像 | `sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251` |
| 最终 serve SHA-256 | `9b6fed4a0e1e3b0af1dbd196a0eae158c11aa03a368fbe3df0f8db65fdbfd0d3` |

相对直接基点只有 7 个文件变化：executor、生产流水线 helper、生产 publication/coalescing helper、CPU 测试及 CMake、两份运行时说明。产品构建明确 `NINFER_P14_PERF_DRIVER=OFF`，生产 engine 编译记录不含 P1/P2/P14 测试/trace 宏；继承的诊断代码不启用。原 P14 source 与原证据未修改。分支未创建新 commit。

[完整补丁](../output/ninfer-v4-export-pipeline-20261025/remote-evidence/final/patch-r2.diff) · [源码镜像](../output/ninfer-v4-export-pipeline-20261025/source/src/runtime/engine/concurrent_executor.h) · [源文件冻结摘要](../output/ninfer-v4-export-pipeline-20261025/source-delta-r2.json) · [最终身份回读](../output/ninfer-v4-export-pipeline-20261025/remote-evidence/final/final-attestation.json)

## 实际验证与评审

复用既有 BO 依赖及构建目录，以不暴露 GPU、不挂载模型、禁用网络的 BO 容器构建。`engine.cpp` 实际重新编译，生成新的 `ninfer-serve`，没有启动服务。

```bash
cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DNINFER_P14_PERF_DRIVER=OFF \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build /build --parallel 4 --target ninfer-serve ninfer_export_publication_pipeline_test
timeout 60s /build/tests/ninfer_export_publication_pipeline_test
```

r1 构建和 6 项流水线合同通过。独立评审指出这些测试没有直接调用新增的缓存合并业务规则；随后将真实生产规则小范围抽取为共享 CPU 函数，补了 4 项合同。r2 对变更后的同一目标构建/执行，**10/10 通过**，不是 16 项不同场景。r1/r2 耗时约 33.0/13.3 秒，均是增量构建加测试时间，不是性能基准。

| CPU 覆盖 | 结果 |
|---|---|
| 前一发布被阻塞时，后一导出仍完成并释放 lane；完成序号不提前推进 | PASS |
| ready 满时先释放 source，再等待容量；FIFO 与容量不被越过 | PASS |
| ready 合并/移除能继续消费，导出失败仍传递终态并继续后项 | PASS |
| 关闭等待已有发布并排空；空队列、未启动及重复关闭 | PASS |
| 真实 ready+ingress 的 CAS/generation/parent、ticket、flight 及 boundary/观测保留 | PASS |
| host 镜像移除、immutable/其他 session/私有任务保护、入队 bad_alloc 原子性 | PASS |

[构建回执及原始命令](../output/ninfer-v4-export-pipeline-20261025/remote-evidence/final/build-r2/receipt.json) · [CPU 原始结果](../output/ninfer-v4-export-pipeline-20261025/remote-evidence/final/build-r2/cpu-contract.stdout) · [r1 评审缺口](../output/ninfer-v4-export-pipeline-20261025/evidence/review-r1.md) · [r2 独立复审](../output/ninfer-v4-export-pipeline-20261025/evidence/review-r2.md)

r2 复审无阻塞发现，r1 覆盖缺口已闭合。评审者仅静态阅读，实际构建与测试由主代理执行。CPU 失败场景用 host gate 模拟操作完成/失败，不等于真实 D2H 异常排空或进程 SIGTERM 验证。线程创建失败路径只有静态检查，没有资源耗尽注入。

收尾核验曾因按 `engine.cpp` 文件名假设编译记录唯一而失败；实际有生产和两个旧测试驱动共三条。已改为精确匹配生产 object、保留宏检查并通过；只重新读取身份，未重建或重测。[原失败与修正说明](../output/ninfer-v4-export-pipeline-20261025/evidence/final-attestation-r1-failure.json)保留。

## 最小实机范围与预算（建议，尚未冻结或执行）

只比较**原 P4 serve 与修复 P4 serve**，两端均为 schema22/midrise rk4v4、C1/W4/K3，同样 context/KV262144、Target T1/p0.95/k20、medium/32768。使用新输入命名空间与独立空私有缓存；不复用旧已消费账本，不运行 BO/旧 codec 或 native 矩阵。

| 项目 | 合计上限 |
|---|---:|
| 新 Chat：每端短冷、短热、长冷、真实 L2 长热 | 8 |
| 内置启动 warmup | 2 |
| 模型提交 | 10 |
| wire：每端 4 Chat＋readiness/私有 slot erase/telemetry | 14 |
| native / native decode / 新算子数值场景 | 0 |
| 硬窗口 / 开始清理 | 20 分钟 / 第 17 分钟 |

候选容器 4 CPU/24GiB，L1/L2 6144/8192MiB；独占 GPU，一次只运行一个候选，原服务继续停止。HTTP 路径没有逐 GPU 调用拦截，kernel/capture/replay/传输计数为 `null`，不填 0 或套用 native 上限。保留请求、context、输出、容器和窗口限制，并观察真实主机内存占用；不能声称已有 allocator 高水位资格。

关键判据是：短请求 EOF 和必要 durable 检查后立即续请求，不插入等待 publication 的延时；至少观察到后一个 job 的导出及 source release 与前一个 CPU publication 重叠。记录 queue、prefill、首个语义 delta TTFT、完整 HTTP wall、真实 L1/L2 恢复及逐 job alias 结果。queue 已含 restore，不重复相加。只在长冷 boundary 明确成功后擦除其私有 slot，以验证长热确实使用 L2。

最终 Chat 后采用身份绑定 SIGTERM，最多等 30 秒自然 exit0，并核对最后 `completion_export_job_id` 的发布终态。若其发布在 SIGTERM 后完成，才算真实关闭排空证据；若之前已完成，只算 idle-close smoke。超时、137 或缺终态均保留失败/缺口，不能沿用旧 `stop -t2` 并宣称排空通过。

**预计：无需 GPU 的工具窄适配、CPU 回归、评审与新冻结 1.5–3 工程小时；实机 6–10 分钟，硬限 20 分钟；证据核算与报告另 20–40 分钟。** 实机估算依据此前每端约 102 秒加载、两组 Chat 及自然退出。沿用现有 controller/owner/guardian/HTTP 驱动，只调整 profile、两端 P4 身份和最终发布排空；目前没有新实机冻结回执或可消费空账本。真实 SIGTERM 能否在 30 秒内退出仍是待测项。

[完整拟议预算](../output/ninfer-v4-export-pipeline-20261025/proposed-hardware-budget.json) · [预算审阅](../output/ninfer-v4-export-pipeline-20261025/evidence/hardware-plan-review.md)

## 保留事项与交付边界

旧 BO 两次 publication 失败、P4 job7 缺发布终态、旧 HTTP 候选退出137、18处 G1 差异、C1附件缺口、Baseline坏raw及CLI/评分附件缺口全部保留。本次 CPU 修复不把这些旧结果改成 PASS，也不补造或重测。

可构建与 CPU 合同通过不等于性能或发布验收。真实 GPU 导出生命周期、Chat质量/缓存效果、进程排空、TTFT收益和额外内存峰值仍需上述新窗口确认。`performance_gain=null`、`p95=null`、`optimization_qualification=false`、`production_release_qualified=false`。

[机器汇总](../output/ninfer-v4-export-pipeline-20261025/final-summary.json) · [交付校验回执](../output/ninfer-v4-export-pipeline-20261025/delivery-receipt.json) · [远端原始证据清单](../output/ninfer-v4-export-pipeline-20261025/remote-evidence/final/checksums-final.json)。19份远端证据文件逐项SHA验证；原始归档另保留完整校验。所有旧材料未覆盖。
