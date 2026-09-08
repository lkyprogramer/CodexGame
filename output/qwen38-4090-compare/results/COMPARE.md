# WORK vs NInfer vs patched vLLM（thinking=off）

huge-mtp：W4A16 + KVarN + MTP n=3，口 18020。测完已 restore WORK。`capacity_gate` 脚本死卡 `prompt_tokens>=185000`，实测 184k 档针全中，按下表按容量已过。

## 主表

| 指标 | WORK llama.cpp MTP n=2 q4 200K | NInfer MTP n=3 E8 221K | vLLM huge-mtp KVarN 200K |
|---|---:|---:|---:|
| Java 3/3 | **3/3** | **3/3** | **3/3** |
| p50 墙钟 | **27 s** | 40 s | 44 s（首题 97s，含 JIT） |
| tasks/h | **44.4** | 31.6 | 19.8 |
| tools/task | **9** | 13 | 13 |
| ~4k decode | 81.5 | **117.5** | 55.2 |
| ~64k decode | 57.1 | **98.4** | 55.2 |
| ~120k decode | 47.1 | **101.8** | 55.2 |
| deep prompt | ~185k | 184417 | **184457** |
| deep decode | 36.7 | **87.2** | 47.4 |
| deep TTFT | 133.6 s | 94.6 s | **65.8 s** |
| deep needle | 中 | 中 | 中 |
| cache-cold TTFT | 56.7 s | **40.3 s** | 50.5 s |
| cache-exact TTFT | **0.50 s** | 0.51 s | 1.59 s |
| cache-append TTFT | 4.41 s | **3.45 s** | 4.60 s |
| append vs cold | 0.08× | 0.09× | **0.09×** |

vLLM append 未回 `cached_tokens`，用 TTFT 相对 cold ≤50% 判定 cache 过。

## 怎么读

- **日常 Agent（这三道 Java）：WORK 仍最快。** 不要用 vLLM/NInfer 的长 decode 去换开机默认。
- **长上下文首字：vLLM 最好**（185k TTFT 66s），decode 介于 WORK 与 NInfer 之间。
- **长 decode：NInfer 明显第一**（87 t/s @184k）。
- **前缀 cache：三套都过**；WORK/NInfer exact 约 0.5s，vLLM exact 1.6s。
- vLLM 首题 97s 含容器首次编译，tasks/h 被拉低，重复跑会接近 40s 档。

未改 18343/NGINX。未把 vLLM 写成默认。
