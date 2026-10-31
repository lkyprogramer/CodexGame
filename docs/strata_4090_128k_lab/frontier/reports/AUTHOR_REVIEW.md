> 原作者交付记录，保留原验证时间与计数。合并后验证另见实验主目录 `reports/DOC-MERGE-20261030.md`；原始69文件身份见 `history/IMPORT_MANIFEST.sha256`。

# 文档与离线工具作者审阅记录

日期：2026-10-30。范围：固定源码/历史证据、本包执行合同与离线工具。没有目标机硬件实验，没有引擎补丁部署。

## 三条独立审阅线

| 审阅线 | 已完成范围 | 关键修正 |
|---|---|---|
| 历史证据与统计 | 原44份报告、旧64项映射、新旧门槛、Phase依赖与停止路径、离线统计工具 | 保留P3/P24终态；修正新增A/A后的P05预算；固定decode主指标及对应噪声；两对支持层不宣称正式非劣；非目标TTFT回归也拒绝 |
| Maya/Edge0机制 | A0/P6定点源码与Maya三个prefill差量、Edge0各平台路由/回退 | mapped失败也可fallback；count/rank→host base/bounds→scatter完整接口及同步；保全Dm/原规约；运行时开关与同binary off/on一致；预测替代true router归Q |
| CPU/GPU内核与KV | tqLLM相对旧pin、kv_stream同blob、既有GU融合/QSA/SM89、数值oracle | 区分resolve epoch和内容generation；分开KV失效与核内load分支；B/A1/C不混入生产A0；canonical比较域；真实prime历史与采样轨迹限制 |

独立复核确认：没有把旧tqLLM跑分视为新收益，没有把Maya机制差量升级为本机候选通过，没有复活HC、P5、P12、旧Ada表或配置扫描。64行旧编号唯一且原题名一致。O07/O08保留“分析不立项，未实施”的历史边界。

## 工具验证的具体修正

离线六对工具曾遗漏主指标为decode时对TTFT非目标回归的检查。新增“decode快20%、TTFT慢10%”反例先复现错误，再修为对其余两个关键指标均检查CI上界≤1.02。合成P24舍入数据仅作方向/回归sanity，不称为raw重算。

区间计算器只算人工确认依赖后的区间并集和条件模型；unknown或未经证明依赖返回INSUFFICIENT。包验证只检查JSON/固定政策/完整SHA/相对链接/DAG，不校验远端提交或实验真实性。SHA256清单只证明交付字节一致。

## 本次结论边界

新性能候选合格数为0。E0/E1/Q数值、完整请求性能、原六项绝对质量、相对非劣和热稳定分别记账。生产状态仅来自用户/仓库历史记录，本次没有新现场复核。

离线命令、实际退出码、测试范围和最终包验证见[VALIDATION.md](../VALIDATION.md)。此审阅记录不能替代目标机实验，也不把计划接口写成已有实现。

最终协议补充：将稳定warm探针资格前移到P05任何GPU启动之前；当前缺原件则BLOCKED_EVIDENCE/NOT_RUN。逐引擎prime后再次核实际append hash，首个不符即止。受控状态重放单独命名，不冒称自然会话收益。
