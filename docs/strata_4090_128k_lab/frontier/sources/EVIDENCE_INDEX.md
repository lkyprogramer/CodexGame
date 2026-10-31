# 证据与来源索引

截止2026-10-30。核心用户仓库固定在`3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0`；本次取读93个核心文档/指定工具文件，其中正式reports目录44份报告。这里的“取读”不表示覆盖整个仓库，也不表示恢复了报告引用的私有workspace原件。

外部来源账记录74条代码/文档审阅记录，URL去重后74个；重复观察不算独立性能证据。公开GitHub代码固定commit，NVIDIA官方页面按取读日期记录；未打包第三方完整源码、模型、引擎二进制或凭据。

## 机器可读账本

- [LOCK.json](LOCK.json)：用户仓库、生产记录、研究基线、donor、工具链、完整P6 env/build合同。
- [DONOR_SOURCES.json](DONOR_SOURCES.json)：文件、symbol、观察范围与事实边界；本地临时路径已去除。
- [USER_EVIDENCE_MANIFEST.json](USER_EVIDENCE_MANIFEST.json)：实际取读的固定仓库文件、字节数与SHA256；不是目标机raw manifest。

## 使用证据的优先次序

先看终态与后续正式对照，再看早期筛查。P3/P24优先于早期汇总中的采用表述或分项相乘。P6只确认隔离版本身份；P13–P22正确性/生命周期/memcheck不能替代P24性能。用户2026-10-30的新状态与Astra建议标为用户提供，本次未现场复查。

## 核心报告完整入口

| 报告 | 固定提交链接 |
|---|---|
| DEPLOY-A0-EXACT6-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-A0-EXACT6-20261025.md) |
| DEPLOY-KVRES-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-KVRES-20261026.md) |
| DEPLOY-PROD-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/DEPLOY-PROD-20261026.md) |
| GATE-P0-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/GATE-P0-20261025.md) |
| P0-T2b-MIG-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-T2b-MIG-20261025.md) |
| P0-T5-DIAG-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-T5-DIAG-20261025.md) |
| P0-T6-CFG-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-T6-CFG-20261025.md) |
| P0-T7-NP0-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-T7-NP0-20261025.md) |
| P0-baseline-qualify-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-baseline-qualify-20261025.md) |
| P1-PR2253-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P1-PR2253-20261025.md) |
| P1-SESSION-1536-PT-20261025 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P1-SESSION-1536-PT-20261025.md) |
| P10-DEQUANT-SIDE-QUALIFICATION-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P10-DEQUANT-SIDE-QUALIFICATION-20261028.md) |
| P11-ADA-DELTA-QUALIFICATION-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P11-ADA-DELTA-QUALIFICATION-20261028.md) |
| P12-GU-GATHER-PROBE-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P12-GU-GATHER-PROBE-20261028.md) |
| P13-HC-SCRATCH-QUALIFICATION-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P13-HC-SCRATCH-QUALIFICATION-20261028.md) |
| P14-P15-NUMERICAL-REPLAY-ORACLE-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P14-P15-NUMERICAL-REPLAY-ORACLE-20261029.md) |
| P16-HC-SCRATCH-BC-MINIMAL-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P16-HC-SCRATCH-BC-MINIMAL-20261029.md) |
| P17-HC-GUARD-FIX-BC-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P17-HC-GUARD-FIX-BC-20261029.md) |
| P18-HC-C-COMPLETION-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P18-HC-C-COMPLETION-20261029.md) |
| P19-HC-REAL-BOUNDARIES-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P19-HC-REAL-BOUNDARIES-20261029.md) |
| P2-CFG-ADAPT-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-CFG-ADAPT-20261026.md) |
| P2-CFG-CPUSHARE-S-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-CFG-CPUSHARE-S-20261026.md) |
| P2-CFG-KVGROW-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-CFG-KVGROW-20261026.md) |
| P2-CFG-KVRES-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-CFG-KVRES-20261026.md) |
| P2-CFG-SPEC-S-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-CFG-SPEC-S-20261026.md) |
| P2-CFG-SPECCOST-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-CFG-SPECCOST-20261026.md) |
| P2-NP3-PERF-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-NP3-PERF-20261026.md) |
| P2-NP3-TRACE-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-NP3-TRACE-20261026.md) |
| P2-NPRES-PCIEFRAC-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-NPRES-PCIEFRAC-20261026.md) |
| P2-PR3307-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-PR3307-20261026.md) |
| P2-PR3871-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-PR3871-20261026.md) |
| P2-PR4040-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P2-PR4040-20261026.md) |
| P20-P21-HC-16K-LIFECYCLE-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P20-P21-HC-16K-LIFECYCLE-20261029.md) |
| P22-HC-MEMCHECK-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P22-HC-MEMCHECK-20261029.md) |
| P23-HC-RETAINED-EXPERT-COST-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P23-HC-RETAINED-EXPERT-COST-20261029.md) |
| P24-HC-PAIRED-PERFORMANCE-20261029 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md) |
| P3-COMBINATION-KVRES-20261027 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P3-COMBINATION-KVRES-20261027.md) |
| P4-RUNTIME-BOUNDARIES-20261027 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P4-RUNTIME-BOUNDARIES-20261027.md) |
| P5-GU-VNNI-PROBE-20261027 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P5-GU-VNNI-PROBE-20261027.md) |
| P6-V027-BASELINE-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P6-V027-BASELINE-20261028.md) |
| P7-LONG-RETRIEVAL-ROOTCAUSE-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P7-LONG-RETRIEVAL-ROOTCAUSE-20261028.md) |
| P8-INDEPENDENT-LOGITS-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P8-INDEPENDENT-LOGITS-20261028.md) |
| P9-HIGHER-PRECISION-LOGITS-20261028 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P9-HIGHER-PRECISION-LOGITS-20261028.md) |
| SUMMARY-GAINS-20261026 | [原文](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/SUMMARY-GAINS-20261026.md) |

## 阅读路径

历史判定先读[关闭台账](../docs/01_EVIDENCE_AND_CLOSURES.md)，新来源先读[机制对照](../docs/07_DONOR_DELTA.md)。需要重新执行时，先恢复原P6 `BUILD_COMPLETE`、六文件port、资产与13项生产保护原件；链接可证明报告存在，不能代替这些输入。

引用规则：报告中的统计只能称“原报告观察”；源码只能证明机制和门控存在；本包尺寸公式、Amdahl模型和新门槛是推导/政策。不能把任一层改写为本机新增实测。

## 本地整合的新增证据（2026-10-30）

[29只读回执](HOST29_READONLY_20261030.json) 是整合时新取读的现场快照。USER_EVIDENCE_MANIFEST.json、DONOR_SOURCES.json、LOCK.json 继续标识原作者固定检索来源，没有重写其历史 path/url/hash；原始69文件身份另存 history/IMPORT_MANIFEST.sha256。外部donor的作者定点审阅在本次整合中未重新联网验证，实施前只复核实际拟用差量。
