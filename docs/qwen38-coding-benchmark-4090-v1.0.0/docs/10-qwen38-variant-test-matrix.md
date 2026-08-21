# 10 · Qwen3.8-27B 变种测试矩阵

4090 上 S 名单的部署、互斥切换、下载、smoke 门和 Latin-square 落地，见仓库根文档 [`docs/qwen38-4090-coding-agent-s-list-plan.md`](../../qwen38-4090-coding-agent-s-list-plan.md)。本文只保留实验矩阵，不重复运维步骤。

## 第一轮：行为/权重

| Config ID | 权重 | Template | 目的 |
|---|---|---|---|
| original-official | Original | official | 基线 |
| original-sharp | Original | Sharp/Dirk | 仅 template 行为改造 |
| grug-q4km | Grug v1.1 | native | tool/reasoning trade-off |
| fable-q4km | Fable-Distill | native | Agent trajectory distill |
| salience-q4km | Salience R5 | native | repo/terminal engineering 定向 |
| cold-fusion-q4km | Cold Fusion | native | reasoning 压缩 |

## 第二轮：量化/上下文

| Config ID | 权重 | Quant | 目的 |
|---|---|---|---|
| original-q5km | Original | Q5_K_M | 高精度对照 |
| pearson-iq4xs | Original | coding-aware IQ4_XS | 释放 KV/context |
| pearson-q5 | Original | coding-aware Q5 | imatrix 高精度 |
| ridge-3.7bpw | Original | mixed low-bit | 长上下文显存权衡 |

## 第三轮：Optimized

对每个进入决赛的权重分别搜索：reasoning effort、MTP、context/KV、template。搜索预算必须相同，避免只为某模型精调。

## 必做消融

- Original official vs Original Sharp；
- 每个 finetune native template vs common template（若可运行）；
- Regular vs MTP；
- Q4 vs Q5；
- 32K vs 64K 检索任务；
- medium vs xhigh 至少在 Agent 子集比较。
