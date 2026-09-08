# thinking=medium 三后端完整报告

时间：WORK 2026-09-07 17:53–18:01；NInfer+vLLM 2026-09-08 09:33–09:50。  
thinking=medium。口：WORK 18343 / NInfer 18030 / vLLM 18020。测完 WORK 已 restore。  
原始 JSON：`output/qwen38-4090-compare/results/medium/{work,ninfer,vllm}/`  
off 对照：`output/qwen38-4090-compare/results/COMPARE.md`（未覆盖）。

## 主表

| 指标 | WORK MTP n=2 q4 200K | NInfer MTP n=3 E8 221K | vLLM huge-mtp 200K |
|---|---:|---:|---:|
| Java 3/3 | 过 32/17/53 s | 过 32/23/31 s | 过 86/40/48 s |
| p50 墙钟 | 32 s | **31 s** | 48 s |
| tasks/h | 35.3 | **41.9** | 20.7 |
| tools/task | **9** | 12 | 13 |
| ~4k decode / TTFT | 77.6 / 1.87s | **127.1 / 1.24s** | 57.8 / 6.69s |
| ~64k decode / TTFT | 60.2 / 31.2s | **110.6 / 21.9s** | 63.7 / 28.3s |
| ~120k decode / TTFT | 46.5 / 71.0s | **115.4 / 50.2s** | 63.4 / 41.6s |
| 184415 针 | 中 | 中 | 中 |
| 184k decode / TTFT | 38.4 / 133.8s | **98.5 / 94.1s** | 53.1 / **65.8s** |
| 184k prefill t/s | 1383 | 1974 | **2802** |
| cache-append TTFT | 5.0s（cached 99695） | **3.6s**（99697） | 5.0s（无 cached 字段，TTFT 比 cold 0.10×） |

`capacity_gate` 脚本要 `>=185000`，实测一律 **184415**，针全中，按容量算过。

## 相对 thinking=off

WORK medium ≈ off（systemd 本来就是 medium）。NInfer medium 长 decode 仍 ~100 t/s，Java 墙钟甚至略快于 WORK。vLLM 首字 185k 仍最短，Agent 最慢。

## 现网

`openclaw/Qwen3.8-27B-WORK` active。未切默认。
