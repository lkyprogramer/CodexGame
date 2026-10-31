> 当前收口：2026-10-31[Astra独立复核](reports/ASTRA_REASSESSMENT_20261031.md)不支持继续优先推进F02，root采纳。NO_QUALIFIED_CANDIDATE，F02保持DEFERRED_NEW_EVIDENCE，不再追加四小时审计或GPU。P01/P01B/F03原终态、六FAIL及P05 BLOCKED_EVIDENCE保留，预算/PT0保持。生产随后按用户要求恢复运行，GPU已占用；回执在父目录`reports/PRODUCTION-RESTORE-20261031.md`。

# Strata / RTX 4090 / 128K 后续极限优化实验室 v3

> 本文 P00–P07 均指 `frontier/P00`–`frontier/P07`，与历史 P0–P24 不同。当前阶段和授权范围由父目录 `plans/NEXT_ACTIONS.md` 确定。

**状态更新：2026-10-31（北京时间）；作者原研究截止2026-10-30。交付类型：研究结论、执行历史与条件合同、离线验收工具。**

当前冻结合同下没有值得继续投入的合格候选，本轮已以`NO_QUALIFIED_CANDIDATE`收口。P01/P01B限额诊断和F03审计均已结束；旧P11复算未支持F02的新机制与单格式空间，取消原拟继续审计。未知GPU/CPU内部依赖保持未知，不外推全局NO_GAIN，也不把条件卡排成新的执行队列。

本包已并入 `docs/strata_4090_128k_lab/frontier`，由父目录统一入口；并逐项消化 v2 的 64 个方向。沿用入口、docs、plans、config、sources、tools、tests、reports 的结构。旧报告、原六项长检索失败、P24 HC 性能失败都保留；不会把“尚未实现”自动变成“值得实现”。

## 应从哪里读

| 阅读目的 | 文件 |
|---|---|
| 判断还有没有投入价值 | [研究报告](REPORT.md) |
| 当前零候选收口与F02暂缓 | [Astra复核回执](reports/ASTRA_REASSESSMENT_20261031.md) |
| 交给 AI 接着做 | [AI 执行入口](START_HERE_AI.md) |
| 当前事实与基线 | [冻结快照](docs/00_SNAPSHOT.md)、[历史结论](docs/01_EVIDENCE_AND_CLOSURES.md) |
| 理解真正的性能上限 | [架构与关键路径](docs/02_ARCHITECTURE_AND_LIMITS.md) |
| 看有条件的研究分支 | [候选排序](docs/03_CANDIDATE_DECISION.md)、[逐候选合同](candidates/INDEX.md) |
| 本轮已执行并收口的硬件合同 | [限额诊断合同](docs/04_WARM_DECODE_DIAGNOSTIC.md)、[P01](plans/P01_DIAGNOSTIC.md) |
| 数值、统计和质量 | [数值合同](docs/05_NUMERICS_AND_QUALITY.md)、[测试统计协议](docs/06_BENCHMARK_PROTOCOL.md) |
| 哪些外部优化是真差量 | [引擎对照](docs/07_DONOR_DELTA.md) |
| 完整开发任务与依赖 | [阶段总表](plans/INDEX.md)、[机器可读 DAG](config/task_dag.json) |
| 旧 64 项如何处理 | [v2 逐项映射](history/V2_64_DIRECTION_CROSSWALK.md) |
| 工具究竟做了什么 | [工具说明](tools/README.md)、[交付验证](VALIDATION.md) |

## 当前状态

- 生产记录：v0.2.3 A0 + EXACT6 + 后续服务/配置项，10-31按用户要求恢复；12:49 health loaded=true，12:50:44 active/running/enabled、NRestarts0，GPU由生产引擎占用，实验18089无监听。恢复回执在父目录主报告；[整合时快照](sources/HOST29_READONLY_20261030.json)及后续停机回执保留原时间，不代表当前空闲。
- 研究基线：P6 v0.2.7 隔离树的原生代码与六文件 reply/PT port；**不是 P13/P24 的 HC 二进制，也不是最新 main**。
- 目标模型：现用 GSQ-RCO **IQ3_XXS 包**，内部含多种专家类型；不能以记忆里的 IQ3_S 包替代。
- 主场景：单会话、长上下文、采样 xhigh、MTP spec4。并发吞吐、dense 27B、别的 CPU 或不同量化的数字不计为本机收益。
- 执行状态：P00已完成，P01/P01B诊断与F03审计已结束；当前文档收口后停止。P01B有真实GPU执行，F03有CPU验证，均没有产生合格的新性能候选；本次Astra复核未追加GPU。
- 已有正式性能资格的新候选：**0**。十二张方向卡是诊断分支及拒绝/延期合同，不是十二项待实现功能。

## 离线启动

```bash
python3 -B tools/validate.py --root .
python3 -B -m unittest discover -s tests -v
```

具体参数见工具说明。上述工具不启动引擎、不连接SSH、不改生产；随包示例为合成数据。根tools/frontier已有最小live适配，实际P01/P01B执行历史由父目录报告保留；离线命令不构成重跑授权。

## 默认执行原则

Phase 串行；同一 Phase 内无文件/接口冲突的 Task 可并行。所有目标机 GPU 工作串行且独占。每 Task 只做最小验证；阶段收口按实质变更安排独立审阅或验证，复用仍有效的证据，首个硬门失败立即收口。最多同时立项一个候选。

不能把本包交付等同新一轮 GPU 授权。后续用户明确要求执行时，继承当次会话已有授权，按原仓库的硬件交接与生产隔离边界执行，不反复索要已给出的许可。生产部署另行形成可审阅的变更与回滚材料。

## 整合后的权限与最小范围

当前按父目录plans/NEXT_ACTIONS.md保持零候选收口。P01的941短输出停止和P01B后续独立自然EOS合同均保留；不倒写P01的2048门或P05正式性能合同。未来重开须有独立新机制、当前真实暖态命中与可闭合依赖、可信净省时≥4%依据及明确执行范围，缺证据不自动补对照或新采集。
