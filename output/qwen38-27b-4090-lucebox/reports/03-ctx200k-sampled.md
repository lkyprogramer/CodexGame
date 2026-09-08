# Lucebox Qwen3.8 4090 — 200K + 采样验收（sampled verify）

时间：2026-09-04 02:46–02:53 EDT  
结论：**CTX200K_OK（q4 KV）**。`DFLASH_SAMPLED_VERIFY=1` + T=1.0 在 **max_ctx=200000** 上全程 `[spec-decode]`，无 `[ar-decode]`。28k/64k/128k/180k 三针全中，工具命中。**q8 KV 的 200K 不能推理**。测完 trap 已 restore WORK。

## 配方

| 项 | 值 |
|---|---|
| 端口 | 18343（临时占） |
| target | IQ4_XS 14G |
| draft | DFlash2 Q8 2.0G，block 16 |
| 采样 | T=1.0 top_p=0.95 top_k=20，`enable_thinking:false` |
| 加速 | `DFLASH_SAMPLED_VERIFY=1` |
| 成功档 | **`--max-ctx 200000` + KV q4_0/q4_0**（C200Q4） |

## 失败档：q8 200K

C200Q8 空载 **22468 / 1749 MiB**，`max_ctx=200000` 写进日志。  
每条请求都 `cudaMalloc 2489.25 MiB failed`，completion=0、wall≈0.01s。空载能起来 ≠ 能推理。

## 成功档：q4 200K

空载 **19342 / 4875 MiB**。180k 针时峰值 **22736 / 1481 MiB**。无 OOM。

| 项 | pt | 针 | decode tok/s | accept | wall |
|---|---:|---|---:|---|---:|
| probe / S_short | 24–30 | — | 228 / 234 / 140 | 80% / 77% / 42% | 0.3–1.1s |
| L_28k | 27842 | **全中** | 115.6 | 87.5% | 18.0s |
| L_64k | 63772 | **全中** | 69.1 | 58.9% | 45.3s |
| L_128k | 127642 | **全中** | 61.3 | 70.0% | 104.7s |
| L_180k | **179542** | **全中** | 51.5 | 70.0% | 163.7s |
| A_tools | 263 | `read_file Agents.md` | 131.0 | 40.6% | 0.39s |

针内容：`tick=1847` / `protocol=delta-net-ok` / `replay=seed-42`。预览即 JSON。  
180k 的 wall 主要是 prefill（~1100 t/s 量级）；decode 仍走 spec，只是长上下文变慢。

相对 32K q8 的 S1（短代码 ~187 t/s）：200K q4 短代码仍约 **140–234 t/s**；到 180k 上下文 decode 掉到 **~52 t/s**，仍不是 AR fallback。

## 现网（测后）

- 18343 id：`openclaw/Qwen3.8-27B-WORK`
- unit **active**，GPU 22958 MiB / 0%
- 未改 NGINX、未切默认、未 enable TEXT

## 限制

- 200K 只能配 **q4 KV**；继续用 Lucebox 默认 q8 KV 会在首包 OOM。
- 针测关 thinking、短生成（28–33 tok）。不是 OpenClaw 长 thinking / 多轮工具评测。
- 长上下文 decode 51 t/s 已接近此前 32K AR 的量级；加速优势主要在短上下文。
- 未把 Lucebox 接到 OpenClaw 别名。

## 产物

远程：`/home/hhtele/lucebox-qwen38-4090/{logs/ctx200k-sampled.out,logs/C200Q4.stderr.log,logs/ctx200k-sampled.q8fail.out,results/ctx200k-sampled/summary.json}`  
本地：`output/qwen38-27b-4090-lucebox/reports/03-ctx200k-sampled.md`
