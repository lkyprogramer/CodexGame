# OpenClaw Qwen3.8-27B RTX 4090

现网默认是 **NInfer**（调用名仍为 `openclaw/Qwen3.8-27B-WORK`）：

**[`docs/openclaw-qwen38-ninfer.md`](docs/openclaw-qwen38-ninfer.md)** — 部署、使用、回滚、后续优化

llama.cpp WORK / TEXT 回滚与无审核档：

**[`docs/openclaw-qwen38-4090-ops.md`](docs/openclaw-qwen38-4090-ops.md)**

| | 当前 |
|---|---|
| 开机 | `openclaw-qwen38-ninfer.service` **enabled** |
| 调用名 | `openclaw/Qwen3.8-27B-WORK`（兼容旧 WORK 名） |
| 配方 | NInfer 262K `rk4v4-e8` MTP n=3，默认 thinking=medium |
| llama.cpp WORK | `openclaw-qwen38-work-64k.service` **disabled**，回滚用 |
| 无审核 | `openclaw-qwen38-text.service` **disabled** |
| API | 本机 `127.0.0.1:18343` / 对外 `192.168.10.29:28343`（NGINX Bearer） |
