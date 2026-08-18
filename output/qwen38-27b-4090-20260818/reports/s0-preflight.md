# S0 预检

时间：2026-08-17 23:21–23:28 EDT  
主机：`192.168.10.29`（hostname `debian`）

| 项 | 结果 |
|---|---|
| SSH | 通过 |
| GPU | RTX 4090 24564 MiB |
| 测试前生产 | `openclaw-qwen36-mtp4-128k.service` active+enabled，占用 22466 MiB |
| 停生产 | `systemctl stop` 后 VRAM 3 MiB，18343/19343 无监听 |
| 模型 | `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf` 17923394624 bytes |
| SHA256 | `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` 与 08-17 一致 |
| Binary | `/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server` commit `4df29be` |
| 关键 flag | `--reasoning-budget`、`--reasoning-budget-message`、`--spec-default`、`--spec-type draft-mtp`、`--chat-template-kwargs` 均存在 |
| 未重建 llama.cpp | 当前 binary 已满足方案 |

结论：S0 通过。未升 commit。
