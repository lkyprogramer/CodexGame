# Strata · RTX 4090 / 128K 实验主目录

2026-10-30 已将 GPT Pro v3 后续方案并入 `frontier/`。本目录继续作为唯一实验主目录；历史结果和执行工具原位保留。2026-10-31经Astra复核，当前冻结合同下零合格候选，本轮已收口；不沿旧计划继续探索。

## 当前结论

- 生产仍是 A0/v0.2.3 + EXACT6 + 已部署的 reply/PT、主机及 prefill/KVRES 配置。10-31按用户明确要求[恢复既有服务](reports/PRODUCTION-RESTORE-20261031.md)：12:49健康接口loaded=true；12:50:44为active/running/enabled、NRestarts0，GPU由生产引擎占用，实验18089无监听。13项保护文件身份仍引用F03回执，本轮未重复hash。
- 后续研究基线为 P6 原生 v0.2.7 + 六文件 reply/PT port。原 P6 二进制仍存在且 SHA 匹配；完整port、3574依赖和16项资产已在P00逐一hash核齐。P24 HC 二进制和 donor main 均不能替代它。
- P24 HC 已关闭：TTFT 改善 0.824%，CI 跨零；完整 decode 耗时增加 4.428%，未部署。原六项长检索 FAIL 保留，质量非劣未建立。
- frontier/P00 身份、真实Pi请求、源码去重与离线接口已完成；见 [P00报告](reports/P00-EVIDENCE-20261030.md)。[P01](reports/P01-PI-WARM-DIAGNOSTIC-20261030.md)已执行1引擎/1请求，941自然EOS触发短输出停止，两个append NOT_RUN，阶段INSUFFICIENT；当前合格新候选为0。
- [P01B](reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)按新的自然EOS合同完成1引擎/3请求，采集939完整窗口与2291原始token IDs；窄host间隙不足4%，资格INSUFFICIENT，未进入候选开发。本批次关闭。
- [F03](reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md)会话快照审计及CPU验证已完成，无泄漏/安全回收对象的充分证据；唯一同步零填原型正确性通过、CPU三对均更慢，NO_QUALIFIED_CANDIDATE关闭。缓存预算/PT0不变，GPU追加0。
- [Astra复核与收口](reports/FRONTIER-CLOSURE-ASTRA-20261031.md)：撤回优先推进F02的建议，F02保持DEFERRED_NEW_EVIDENCE；旧profile最大单格式条件成本仅2.22%/2.13%，且无已证新机制，不作当前暖态严格上界。当前零合格候选，P05 BLOCKED_EVIDENCE及六FAIL保留。

## 只从这里进入

| 目的 | 入口与权威范围 |
|---|---|
| 接续工作 | [AI 入口](START_HERE_AI.md)、[下一步行动计划](plans/NEXT_ACTIONS.md) |
| 当前收口与重开条件 | [Astra复核与收口报告](reports/FRONTIER-CLOSURE-ASTRA-20261031.md) |
| 当前生产运行状态 | [生产恢复回执](reports/PRODUCTION-RESTORE-20261031.md) |
| 本次合并依据、现场证据、验证 | [合并记录](reports/DOC-MERGE-20261030.md) |
| 后续研究及候选合同 | [frontier](frontier/README.md)、[研究报告](frontier/REPORT.md) |
| 最新完成的 GPU 工作 | [P01B实际报告](reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)、[独立合同](frontier/plans/P01B_DIAGNOSTIC.md) |
| 历史采用与质量边界 | [关闭台账](frontier/docs/01_EVIDENCE_AND_CLOSURES.md)、[P3](reports/P3-COMBINATION-KVRES-20261027.md)、[P24](reports/P24-HC-PAIRED-PERFORMANCE-20261029.md) |
| 历史部署 | [A0/EXACT6](reports/DEPLOY-A0-EXACT6-20261025.md)、[reply/PT/prefill](reports/DEPLOY-PROD-20261026.md)、[KVRES](reports/DEPLOY-KVRES-20261026.md) |
| 原始实验与执行工具 | 原位 `reports/`、`workspace/`、`lab/`、`tools/`、`tests/`；frontier 不复制另一套 runner |
| 历史阶段安排 | [原 README](history/README_PRE_FRONTIER_20261030.md)、[原 AI 入口](history/START_HERE_PRE_FRONTIER_20261030.md)、[已关闭续测合同](history/CONTINUATION_20261029.md) |

## 主从与统计规则

实际现场与带原件的实验报告决定事实；`frontier/` 决定未来阶段设计；旧 `docs/`、`prs/` 和历史计划仅用于解释原实验。P3、P24、旧通用 stats 各自的历史门槛保留，frontier 新统计政策只向前生效。过去分项相乘的 decode +23% / 墙钟 −9% 不是当前组合实测。

`frontier/P00`…`frontier/P07` 是新命名空间；文内短写 P00/P01 只在 frontier 下解释，不重命名旧 P0…P24 报告和原件。

## 离线检查

从本目录运行：

```bash
python3 -B -m lab.cli verify
python3 -B frontier/tools/validate.py --root frontier
python3 -B -m unittest discover -s frontier/tests -v
python3 -B frontier/tools/verify_manifest.py --root frontier --manifest frontier/MANIFEST.sha256
```

以上只验证包与离线工具。GPU 诊断、实现与部署状态分别记录；文档中的执行计划不构成新的远端实验授权。
