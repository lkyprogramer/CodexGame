# QCB-4090 现网 WORK 基线状态

日期：2026-08-20

## apt

已从清华源 **改回阿里云**（`/etc/apt/sources.list.bak-20260820`）。`apt-get update` 走 `mirrors.aliyun.com` 正常。docker.com 源仍 handshake 失败，忽略。

`openjdk-17-jdk-headless` 已装，`javac 17.0.20`。

## 跑了什么

现网 **Optimized** 档，不改 18343 配方。

- Config：`work-udq4xl-optimized-112k-mtp2`
- 端点：`http://127.0.0.1:18343/v1`，`openclaw/Qwen3.8-27B-WORK`
- **smoke × seed 42：完成，审计通过**
- **core × 11,29,47：已在 4090 后台跑**（96 样本，预计数小时）

## smoke 摘要

Hard Success **25%**（3/12）。审计 `passed=true`，无基础设施错误。

| 题 | 结果 |
|---|---|
| SF001 | PASS |
| SF002 | FAIL `tool_budget_exhausted` |
| BF001 | FAIL（完成但隐藏测试未过） |
| BF004 | PASS |
| RE001 | FAIL `tool_budget_exhausted` |
| RE004 / RE007 | FAIL |
| AT001 | FAIL `tool_budget_exhausted` |
| AT002 | PASS |
| LC001 / CR001 / CR002 | FAIL |

工具：213 次调用，合法率 96.7%，操作成功 50.5%。仓库/Agent 题容易把 40 次预算烧光。Decode 中位 78.3 tok/s，MTP accept 59.4%，峰值显存 22730 MiB。

这是 coding-agent 基线，不是 HumanEval。core 跑完后再出正式横评。

远程日志：`/home/hhtele/qcb-4090-baseline/logs-core.out`
