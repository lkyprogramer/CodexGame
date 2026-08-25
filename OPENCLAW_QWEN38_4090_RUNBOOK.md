# OpenClaw Qwen3.8-27B RTX 4090

完整部署与运维（现网 WORK + 无审核 TEXT）已写到：

**[`docs/openclaw-qwen38-4090-ops.md`](docs/openclaw-qwen38-4090-ops.md)**

| | 当前 |
|---|---|
| 开机 | `openclaw-qwen38-work-64k.service` **enabled** |
| 调用名 | `openclaw/Qwen3.8-27B-WORK` |
| 配方 | Dynamic V3 + 200K q4 KV + MTP n=2 |
| 无审核 | `openclaw-qwen38-text.service` **disabled**，同配方、HauhauCS 权重，用完切回 WORK |
| API | 本机 `127.0.0.1:18343` / 对外 `192.168.10.29:28343`（NGINX Bearer） |
