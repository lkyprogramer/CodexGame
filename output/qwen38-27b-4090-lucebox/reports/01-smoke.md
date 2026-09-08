# Lucebox Qwen3.8 4090 — bench_lane smoke

时间：2026-09-04 00:12–00:17 EDT（机器本地）  
结论：**SMOKE_OK**。6/6 非空，工具调用命中，28k 三针全中。测完 trap 已把 **WORK 拉回 18343**。

## 流水线

| 项 | 结果 |
|---|---|
| `wait_build_smoke.sh` | 已退出；`SMOKE_OK 2026-09-04T00:17:04-04:00`；`prod_ready after 6s` |
| `dflash_server` | smoke 期间占 18343；现已不在；当前监听是 `llama-server` pid 2067323 |
| IQ4 | `/data/models/qwen/qwen38-lucebox/Qwen3.8-27B-UD-IQ4_XS.gguf` 14G（`14252845984`） |
| DFlash2 Q8 | **有**：`/data/models/qwen/qwen38-lucebox/qwen38-dflash2-q8_0.gguf` 2.0G（00:16）；旁路 F16 3.6G |
| 配置 | `--max-ctx 32768`，`--draft-block-size 16`，KV q8_0，idle VRAM **16916 MiB** |
| `TIMEOUT` / `server died` | **无**（`wait-smoke.out` + `server.stderr.log`） |
| WORK | `openclaw-qwen38-work-64k.service` **active**；18343 id **`openclaw/Qwen3.8-27B-WORK`**，`n_ctx=200192`，ftype Q4_K |

编排两次 `convert draft`（00:12:12 pid=2064883、00:12:33 pid=2065164）叠在 uv 拉 torch 上；第二次写完 Q8 后停 WORK、5s 起服、跑 lane、EXIT trap restore。未改 NGINX、未 enable、未测 Pi。

## summary.json

`/home/hhtele/lucebox-qwen38-4090/results/smoke/summary.json`  
lane `lucebox-smoke`，model `qwen38-lucebox`，`n=6`，**empty=0**。

| id | class | empty | finish | tok/s | 要点 |
|---|---|---|---|---|---|
| `S_off_code` | S | false | stop | 38.06 | `merge_sorted` Python，`reason_len=0` |
| `T_medium_code` | T | false | stop | 53.95 | Dijkstra，`reason_len=2113` |
| `T_empty_budget` | T | false | stop | 53.86 | InnoDB 四隔离级别中文，`reason_len=0` |
| `A_tools` | A | false | **tool_calls** | 42.28 | `read_file` `{"path":"CodexGame/Agents.md"}` |
| `A_chat` | A | false | stop | 53.53 | 单卡 4090 装不下两个 27B 的中文闲聊 |
| `L_28k_needles` | L | false | stop | 1.63* | **tick/protocol/replay 全 true**；`{"tick":200,"protocol":"v1","replay":"data/replay"}` |

\* `avg_decode_L=1.63` 含 26963 tok prefill（stderr：prefill 13.1s + decode 0.4s **51.1 tok/s**）。  
均值：S 38.06 / T 53.90 / A 47.91。峰值 GPU 19664 MiB / 92% / 64°C。6 条 `http=200`、`error=null`。

`draft_n` / `accept_rate` 在 summary 里全是 null（bench_lane 没解析 speculative timings）；stderr 也没有 accept 计数。不能据此断言 DFlash2 草稿是否在吃 token。

## 现网

- 18343 `/v1/models` id：`openclaw/Qwen3.8-27B-WORK`（不是 `qwen38-lucebox`）
- GPU idle：22958 MiB used / 0% util（WORK 200K 常驻）
- 调度监控应停：smoke 已结束，不要重跑、不要删权重
