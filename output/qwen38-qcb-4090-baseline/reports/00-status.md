# QCB-4090 现网 WORK 基线状态

日期：2026-08-21

## apt

已从清华源 **改回阿里云**（`/etc/apt/sources.list.bak-20260820`）。`apt-get update` 走 `mirrors.aliyun.com` 正常。docker.com 源仍 handshake 失败，忽略。

`openjdk-17-jdk-headless` 已装，`javac 17.0.20`。

## 跑了什么

现网 **Optimized** 档，不改 18343 配方。

- Config：`work-udq4xl-optimized-112k-mtp2`
- 端点：`http://127.0.0.1:18343/v1`，`openclaw/Qwen3.8-27B-WORK`
- **smoke × seed 42：完成，审计通过**
- **core × 11,29,47：完成，审计通过**（96/96，无缺无重，artifact 108 份齐全）

## smoke 摘要

Hard Success **25%**（3/12）。n=1，不当智力分。详见 `work-smoke.md`。

## core 摘要（冻结基线）

Hard **46.9%（45/96）**，CBI **46.7%**，Worst **code_review 6.0%**。invalid 0，基础设施 0。`tool_budget_exhausted` 16/96。审查 0/12 Hard。

完整报告：[`work-core-full.md`](work-core-full.md) · 机器表：[`work-core.md`](work-core.md)

这是后续 Sharp / grug / Fable / Salience / Cold Fusion 的对照。未经授权不换 18343。
