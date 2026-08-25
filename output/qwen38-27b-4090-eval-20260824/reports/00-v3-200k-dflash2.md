# Qwen3.8 Dynamic V3 + 200K MTP + analogalok DFlash2

日期：2026-08-24  
机器：`192.168.10.29` RTX 4090  
现网已恢复：`openclaw/Qwen3.8-27B-WORK`，`n_ctx=112128`，22664 / 1553 MiB。  
未 enable 新 unit，未覆盖旧 GGUF。

## 权重

| 文件 | SHA256 | 字节 |
|---|---|---:|
| 现网旧 `Qwen3.8-27B-UD-Q4_K_XL.gguf` | `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` | 17923394624 |
| 新 `Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf` | `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` | 17559178144 |
| analogalok `Qwen3.8-27B-DFlash2-Q2_K.gguf` | `bbbcd5b66b571f438ff2018184648e37211a1d82c492d32834af2da2c7193755` | 705431072 |

V3 SHA 与 HF 当前 `UD-Q4_K_XL.gguf` 一致。

## C：V3 + 200K + KV q4 + MTP n=2

binary：`/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server`（现网同一份）

| 项 | 值 |
|---|---|
| `n_ctx` | 200192 |
| 空载 VRAM | 22958 / 1259 MiB |
| 生成后 VRAM | 22992 / 1225 MiB |
| fib API tok/s | 78.29（141 tok / 1.80 s） |
| fib server decode | 86.74 tok/s，draft accept 0.830 |
| tools | OpenAI `tool_calls` **true** |
| tools server decode | 87.60 tok/s，draft accept 0.906 |

空载余量 1259 MiB ≥ 800。未做 200K 填窗 prefill / needle；窗口以 `n_ctx` 分配为准。

## D：analogalok DFlash2 250K

参数：`-md Q2_K --spec-type draft-dflash --spec-draft-n-max 3 -c 250000 --parallel 1 -ctk q4_0 -ctv q4_0`，主权重 V3。

**现网 20260817 binary 加载 Q2_K 失败：** `done_getting_tensors: wrong number of tensors; expected 81, got 58`。Q2 头是 81 tensors / arch `dflash`，但这份 binary 读不进去。250k/200k/170k 全挂。

**PR #27342 binary 加载成功：** `/home/hhtele/llama.cpp-qwen38-dflash2-pr27342/build/bin/llama-server`

| 项 | 值 |
|---|---|
| `n_ctx` | 250112 |
| 空载 VRAM | 23880 / **337** MiB |
| 生成后 VRAM | 24192 / **25** MiB |
| fib API tok/s | 80.32（232 tok / 2.89 s） |
| fib server decode | 96.44 tok/s，draft accept 0.821，mean len 3.46 |
| tools | OpenAI `tool_calls` **true** |
| tools server decode | **40.91** tok/s，draft accept 0.917 |

与 2026-08-19 矩阵一致：DFlash2 短码快、工具路径掉到 ~40 tok/s；MTP 工具仍 ~88。250K 空载余量低于生产门槛 800 MiB，生成时只剩 25 MiB，不能当 WORK。

## 结论

- 200K q4 + 原生 MTP n=2 + V3 **能在现网 binary 上稳定加载**，tools 正常，余量够。要切开机 WORK 需另一次明确授权。
- analogalok 250K DFlash2 Q2 **能复现，但必须用 PR27342 binary**；不当现网。
- 可选的 112K q8 V3 QCB smoke 本轮未跑（与 200K 混因拆开的 B 步）。
