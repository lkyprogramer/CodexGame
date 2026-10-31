> 历史实验规范与记录。后续探索的当前阶段见 [NEXT_ACTIONS](../plans/NEXT_ACTIONS.md)；本文原口径用于解释原报告，不覆盖 frontier 新阶段合同。

# 冻结基线与“最新”的含义

检索日：2026-10-23。本包固定 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4`（提交时间 2026-10-23 05:57:09 UTC）作为开发基线。初稿编写时它还是领先 `v0.2.2`（`011c9e60`）127 个提交的未发布 main；同日 07:44 UTC 发布的 **v0.2.3（引擎 0.1.48）的 tag 正好指向这个提交**，所以 A0 就是正式版 0.2.3。13:45 UTC 的 v0.2.3.1 只修了 Control（#3810，版本 0.1.48.1），引擎包不变；main 之后多出的 4 个提交都是 Control/setup/测试改动。

来源：[v0.2.3](https://github.com/Niko1221/Strata/releases/tag/v0.2.3)、[v0.2.3.1](https://github.com/Niko1221/Strata/releases/tag/v0.2.3.1)、[固定树](https://github.com/Niko1221/Strata/tree/5c8dd322528cc84f68f461ad54a506b9da8fa8d4)、[相对 v0.2.2 的差异](https://github.com/Niko1221/Strata/compare/v0.2.2...5c8dd322528cc84f68f461ad54a506b9da8fa8d4)。

## 不能继续沿用旧假设

v0.2.3 发布说明里的“DFlash2 drafting, opt-in, in the Terminal only”**不能在 29 的服务形态下生效**：引擎在 `--serve`、`--batch`、多卡切分下会打印 `--draft dflash2 is off: ...; the MTP drafts instead`（`src/program/generate.cpp:5478`），Control 的 `ENGINE_SERVES_DFLASH2 = False`（`strata_control/drafting.py:146`），`strata launch --drafting dflash2` 实际以 MTP 启动并提示 `Drafting: MTP (DFlash2 isn't available in this mode)`。截至 v0.2.3.1 之后的 main 仍是如此。#3322必须变成差量审核与服务集成实验，并先过命令行上限测试（见 `prs/10_PR3322.md`）。

main 已有部分工具解析修复、thinking budget行为、自动会话缓存预算变化。原PR显示open不代表其中代码没被改写吸收。所有任务首先执行符号/行为审计，不直接按PR数量计算工作量。

## 四个控制面

P是用户真正的现网：29 上是 0.1.43.1（部署树 `a0116b27`，带本地改动），与 A0（0.2.3）差距很大。P→A0 迁移评估（MIG，START_HERE P0-T2b）排在所有诊断和对照之前。MIG-PASS：后续全部在 A0 上做，P 上不重复测。MIG-REGRESS：生产留在 P，实验仍在冻结 A0 上完成，只有 CFG-MMAP 与 CFG-IL0 可在 P 上作为生产候选另测。

A0/A1/B必须使用相同工具链和模型身份；A1的功能关闭不是换回旧二进制。主要对照是B/A1；A1/A0用于发现移植副作用。禁止把从旧版升级得到的收益算到PR。

## 以后 main 再变化

不要在本轮执行 `git pull`。若必须使用更新代码，另建实验编号，重写LOCK、重新审计全部实验项状态，至少重做A/A与关键正确性测试。两个不同base的结果不能放进同一配对统计。

若冻结SHA无法取得，停止为BASE_UNAVAILABLE；不能静默改成latest。原PR被关闭/重写时同理保留锁定head，或明确重新立项。
