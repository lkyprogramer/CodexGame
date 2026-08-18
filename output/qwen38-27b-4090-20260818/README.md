# Qwen3.8-27B · RTX 4090 · 2026-08-18

本目录是 **192.168.10.29 / 单卡 24GB 4090** 上 Qwen3.8-27B 的第二轮方案，目标不是再跑一遍“能启动、能 spew token”，而是给出一份 **性能/质量可工作** 的部署与验收标准，供后续真正接入 OpenClaw / 编码 agent。

| 文档 | 内容 |
|---|---|
| [OPENCLAW-QWEN38-4090-RUNBOOK.md](OPENCLAW-QWEN38-4090-RUNBOOK.md) | **现网部署与运维（主文档）** |
| [../../OPENCLAW_QWEN38_4090_RUNBOOK.md](../../OPENCLAW_QWEN38_4090_RUNBOOK.md) | 仓库根目录同一份运维文档 |
| [reports/11-capability-portrait.md](reports/11-capability-portrait.md) | Full 能力画像 |
| [11-capability-eval-plan.md](11-capability-eval-plan.md) | 能力深测方案 |
| [reports/final-decision.md](reports/final-decision.md) | 上线决策（部署轮） |
| [reports/s0-preflight.md](reports/s0-preflight.md) … [s7-restore.md](reports/s7-restore.md) | 各套件实测 |
| [01-deployment-and-eval-plan.md](01-deployment-and-eval-plan.md) | 主方案 |
| [02-community-sources.md](02-community-sources.md) | X / HF / llama.cpp 来源 |
| [03-previous-round-critique.md](03-previous-round-critique.md) | 08-17 复盘 |
| [launch/work-balanced.sh](launch/work-balanced.sh) | 已验证的工作启动脚本 |

## 现网状态（2026-08-18 第二轮）

**Qwen3.8 已是 18343/28343 主力。** Qwen3.6 已 stop+disable。

空正文用 llama.cpp 补丁修掉：思考预算按 `max_tokens` 预留正文额度。生产回归 10/10，S4 空正文 2→0。

见 [reports/10-iteration-primary-deploy.md](reports/10-iteration-primary-deploy.md)。

本轮推荐默认（`work-balanced`，已验证可起、可干活，但未切流量）：

- 量化：已有的 `Qwen3.8-27B-UD-Q4_K_XL.gguf`（不必换成社区帖里的 `Q4_K_M`）
- 服务：llama.cpp + `--jinja` + native MTP
- MTP：`--spec-default --spec-type draft-mtp --spec-draft-n-max 2`
- KV：weights / draft 都用 `q8_0`，`-np 1`，默认 `-c 65536`
- 推理：`reasoning_effort=medium` + `--reasoning-budget 16384` + cutoff message
- 采样：官方 thinking 档 `temp=1.0 top_p=0.95 top_k=20 min_p=0.0 presence_penalty=0.0`
- 端口：测试仍走 `19343`，生产 `18343` / NGINX `28343` 在门禁通过前不动

08-17 可复用：模型文件、SHA256、llama.cpp commit `4df29be`、no-spec ≈ 44.6 tok/s、64K q8 ≈ 20.6GB。其余速度/质量数字必须按新标准重测。
