# NInfer-4090 资格实测（tensorninja @ 44a2c6c）

时间：2026-09-06/07。Pi 未跑 Java 三题（本轮先过容量/协议/针）。测完已 restore WORK。

## 环境

| 项 | 结果 |
|---|---|
| OS | Debian 12（不能用 Ubuntu 驱动脚本） |
| 驱动 | **610.57.04**（`cuda-drivers-580` 实际带上 610；nvidia-smi UMD CUDA **13.3**） |
| 宿主 nvcc | **仍 12.3**，`cuda-toolkit-12-3` hold |
| WORK 回归 | reboot 后 unit active，18343 有回复 |
| 代码 | `tensorninja/ninfer-4090` `44a2c6c`，本机 clone 后 tar 到 4090 |
| 制品 | `neroued/Qwen3.8-27B-NInfer` **rev `3526913004b1`**（不是 main 19G DFlash2） |
| SHA | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` **通过** |
| 镜像 | `ninfer-4090:44a2c6c` 3.55G，CUDA 13.2 经 **daocloud** |
| 服务 | `127.0.0.1:18030`，`--max-concurrency 1`，ctx/kv **221184**，rk4v4-e8，MTP n=3 |
| 启动显存 | 21870 / 2241 MiB；日志 KV 221184、weights 后剩余 6.48 GiB |

`main` 上的 19.03G 包已故意不用。Docker Hub 不通，`docker.m.daocloud.io/nvidia/cuda:13.2.0-cudnn-*-ubuntu24.04` 可用。

## 实测

| 项 | prompt | 墙钟 | prefill | decode | 结果 |
|---|---:|---:|---:|---:|---|
| 短 CAS | 22 | 0.93s | — | **113.8 t/s** | 正常英文 |
| 热追问（同 `prompt_cache_key`） | 64 | **0.20s** | — | 88 t/s | `AtomicInteger`；日志 `cache_source=l1` `reuse=restore_turn_checkpoint` `cache_tokens=18` |
| 28k 针 | **28032** | 8.39s | **3428 t/s** | **145 t/s** | tick=1847 |
| 64k 针 | **64032** | 21.96s | 2965 t/s | 115 t/s | tick=1847 |
| **185k 针** | **185032** | 93.05s | 2006 t/s | **110 t/s** | tick=1847，无 OOM |

MTP 长针接受率约 92–100%。185k decode **远高于** ≥20 t/s 门槛。无 CUDA fault。

未跑：Pi Java 三 fixtures、会话 A/B/A、tools schema 完整环。`usage.cached_tokens` HTTP 字段为 null，命中看服务端日志。

## 现网

WORK 已 restore：`openclaw/Qwen3.8-27B-WORK`。NInfer 容器已删。未改 NGINX、未切默认。

## 相对 WORK / Lucebox（同卡、不同权重）

- 185k 冷 prefill ~93s / ~2000 t/s，优于此前 Lucebox 180k ~164s / ~1100 t/s。
- 短 decode ~114 t/s，长 185k 仍 ~110 t/s（E8 KV 下 decode 几乎不掉）。WORK/Lucebox 在 160–180k 掉到 ~50。
- 权重是 groupwise `.ninfer`，**不是** UD-Q4_K_XL；质量不能用 tok/s 代替 Pi Java。

## 下一步

1. Pi 隧道打 18030，跑 `docs/qwen38-4090-vllm-extreme-v1.0/fixtures/java-agent-*`（不改 verify.sh）。
2. 同一驱动上再开 vLLM extreme Docker（18020），分时占卡。
3. 不要把 NInfer 写进 18343 systemd，除非 Pi Java 过门禁。
