# Ornith-1.5-35B-A3B 4090 试验部署 + QCB smoke

日期：2026-08-25  
现网已切回 `openclaw/Qwen3.8-27B-WORK`，200192，22958 / 1259 MiB。Ornith **未 enable**。

## 权重

- 仓库：`AtomicChat/Ornith-1.5-35B-A3B-GGUF`
- 文件：`/data/models/qwen/ornith/Ornith-1.5-35B-A3B-AD-Q4_K-IQ4_XS.gguf`
- 大小：20125923520
- SHA256：`6def24b4ef1436f080403b8c0fa9ca3b593abc080c74e64ef7c72d3d6a7322f1`（与 HF LFS oid 一致）

社区依据：AtomicChat 官方 24GB「留上下文」档就是 AD-Q4_K-IQ4_XS（20.1GB）；@danirebollo 3090 同量化 + q4 KV + 196k；@analogalok 4090 用 Q4_K_M + q8 KV 250k。本轮取 **AtomicChat 量化 + 200k q4 KV**，与现网窗口对齐，且空载余量 3.1GB。未加载 mmproj，未上独立 MTP 草稿。

## 加载

| 项 | 值 |
|---|---|
| binary | `llama.cpp-qwen38-20260817`（含 `qwen35moe`） |
| alias | `openclaw/Ornith-1.5-35B-EVAL` |
| `n_ctx` | 200192 |
| 空载 VRAM | 21040 / **3177** MiB |
| 采样 | 0.6 / 0.95 / 20，thinking on |

## 协议 smoke

| 题 | server decode | 备注 |
|---|---:|---|
| fib | **154.9** tok/s | thinking 有 |
| tools | **149.2** tok/s | OpenAI `tool_calls` **true**，prefill 2052 t/s |
| think 512 | **156.0** tok/s | |

远快于现网 V3 MTP ~80 tok/s（3B active MoE）。

## QCB smoke 12×seed42

Hard **5/12 = 41.7%**（与 V3 200K smoke 同档，高于冻结 WORK 3/12）。n=12 只作初筛。

| 题 | 结果 |
|---|---|
| SF001 / SF002 / BF001 / BF004 | PASS |
| AT002 | PASS（exhausted 但 hidden 过） |
| AT001 / RE* / LC001 / CR* | FAIL（invalid_output / patch_failed 偏多） |

invalid 率 41.7%、valid tool-call 85.2%（WORK/V3 ~96%）。仓库和 review 仍全灭。decode 中位 **148** tok/s。

不当现网：协议能用、速度快，但工具合法率和 invalid 比 V3 WORK 差；未跑 core。
