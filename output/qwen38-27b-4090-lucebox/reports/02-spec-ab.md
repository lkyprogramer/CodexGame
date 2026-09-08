# Lucebox Qwen3.8 4090 — spec A/B（greedy / DDTree / sampled）

时间：2026-09-04 02:27:35–02:28:34 EDT  
结论：**SPEC_AB_OK**。上一轮 smoke ~51 t/s 是 **temp=1.0 走 AR fallback**，不是卡慢或草稿没挂上。greedy 与 `DFLASH_SAMPLED_VERIFY=1` 都进 `[spec-decode]`。测完 trap 已把 **WORK 拉回 18343**。

## 配置（四车道共用）

| 项 | 值 |
|---|---|
| 端口 | 18343（临时占，trap restore） |
| target | `Qwen3.8-27B-UD-IQ4_XS.gguf` 14G |
| draft | `qwen38-dflash2-q8_0.gguf` 2.0G，`--draft-block-size 16` |
| KV | q8_0 / q8_0，`--max-ctx 32768` |
| 提示 | 3 条短代码（merge_sorted / LRU / Dijkstra），`enable_thinking:false`，`max_tokens=256` |
| 脚本 | `scripts/run_spec_ab.sh` + `scripts/bench_spec.py` |

## 结果

decode tok/s 取 stderr `[spec-decode]` / `[ar-decode]`（不含首包 prefill）。HTTP tok/s 含 prefill，首条会偏低。

| lane | 采样 | 路径 | decode tok/s | accept | HTTP tok/s（含 prefill） |
|---|---|---|---|---|---|
| **G0** | T=0 greedy | **spec** | 341 / 239 / 230 | 87.5% / 57.6% / 55.5%，avg_commit 14.0 / 9.2 / 8.9 | 95.8 / 226.6 / 216.8 |
| **G1** | T=0 + `--ddtree --ddtree-budget 28` | **spec** | 292 / 245 / 241 | 日志 `accepted=N/1` 不可用；avg_commit 14.0 / 11.1 / 10.9 | 65.9 / 231.3 / 226.8 |
| **S0** | T=1.0 top_p=0.95 top_k=20 | **AR** `[ar-decode]` | 50.9 / 54.4 / 54.3 | 无 | 37.0 / 53.6 / 53.6 |
| **S1** | T=1.0 + `DFLASH_SAMPLED_VERIFY=1` | **spec** | 241 / 213 / 138 | 78.9% / 65.2% / 39.2%，avg_commit 12.6 / 10.4 / 6.3 | 88.1 / 201.2 / 134.0 |

token 加权 decode：G0 **261 t/s**，G1 **255 t/s**，S0 **53.5 t/s**，S1 **187 t/s**。  
相对 S0：G0 ×4.9，S1 ×3.5。G0 无任何 `[ar-decode]`；stderr 有 `DFlash 2 selector active for greedy chain decode`。

三条均为 `empty=false`、`finish=stop`，短代码预览正常（非乱码）。这不是质量评测。

## 判定

1. **上一轮 ~51 t/s 复现为 S0**，与 `01-smoke.md` 的 T/A decode 一致。根因已坐实：Lucebox `can_spec` 在 `temp>0` 且未开 sampled-verify 时强制 AR。
2. **greedy 规格解码在 4090 上成立**（G0 230–341 t/s）。社区 R9700 208 t/s / 4090 Qwen3.5+DDTree ~125 t/s 的数量级对得上；本机 IQ4+Q8 block-16 短代码甚至更高。
3. **DDTree 28 没有赢 G0**。G1 已 `ddtree=ON budget=28`，decode 略慢；accept 百分比被 DDTree 计数打成 `N/1`，不能用来比接受率。短 greedy 代码上不必开 DDTree。
4. **OpenClaw 现网采样（T=1）要吃 spec，必须 `DFLASH_SAMPLED_VERIFY=1`**。S1 仍是 spec，但第三题 accept 掉到 39%、138 t/s，波动比 greedy 大。
5. **未切默认、未改 NGINX、未 enable TEXT。** 现网仍是 WORK 200K MTP n=2。

## 现网（测后）

- 18343 `/v1/models` id：`openclaw/Qwen3.8-27B-WORK`
- `openclaw-qwen38-work-64k.service` **active**
- GPU idle：22958 MiB used / 0% util（与 WORK 常驻一致）
- `dflash_server`：无
- `SPEC_AB_OK 2026-09-04T02:28:30-04:00` → `prod_ready after 4s`

## 产物

远程：`/home/hhtele/lucebox-qwen38-4090/{logs/spec-ab.out,logs/{G0,G1,S0,S1}.stderr.log,results/spec-ab/*.jsonl}`  
本地：`output/qwen38-27b-4090-lucebox/{logs/,results/spec-ab/,reports/02-spec-ab.md}`

## 限制

- 3 条 ≤256 tok 短代码，无工具、无 28k needle、无 thinking。
- S1 的 sampled-verify 与 greedy token 分布不同，不能当无损。
- 未测 32K 长上下文下 spec 接受率，也未把 Lucebox 接到 OpenClaw 别名。
- 若要接 OpenClaw：要么客户端 greedy（T=0），要么服务端 `DFLASH_SAMPLED_VERIFY=1`；ctx 目前 32K，不能替代 WORK 200K。
