# Qwen3.8-next · Strata v0.1.41 IQ3_XXS · RTX 4090 部署与运维

机器：`192.168.10.29`（hhtele）  
GPU：单卡 RTX 4090 24GB  
文档日期：2026-10-10  
范围：Strata 上的 `openclaw/Qwen3.8-next`。27B 的架构和回滚仍以 [`openclaw-qwen38-ninfer.md`](openclaw-qwen38-ninfer.md) 与 [`openclaw-qwen38-ninfer-b0-b1-20260930.md`](openclaw-qwen38-ninfer-b0-b1-20260930.md) 为准。

不要把 NGINX Bearer、SSH 密码、sudo 口令、Pi 的 `apiKey` 写进 git。

> **当前状态（2026-10-26）：本文正文是 v0.1.41 时期（10-10）的记录，引擎版本、目录和参数已过时。**
> - **现网版本：** `/home/hhtele/strata-0.2.3`，A0 = v0.2.3 `5c8dd322` + EXACT6 + host 调优，加 10-26 上线的四个开关：
>   - `STRATA_REPLY_REUSE=1`
>   - `STRATA_PRESERVE_THINKING=0`
>   - `STRATA_PREFILL_CPU_SHARE_MAX=4096`
>   - `STRATA_PREFILL_AUTO_MAX=16384`
> - **服务：** `openclaw-qwen38-next.service`，active / enabled。端口 18343、NGINX 28343、模型名 `openclaw/Qwen3.8-next` 不变。
> - **变更、验证与回滚：**
>   - [strata_4090_128k_lab/reports/DEPLOY-A0-EXACT6-20261025.md](strata_4090_128k_lab/reports/DEPLOY-A0-EXACT6-20261025.md)
>   - [strata_4090_128k_lab/reports/DEPLOY-PROD-20261026.md](strata_4090_128k_lab/reports/DEPLOY-PROD-20261026.md)
> - **当前事实表：** [strata_4090_128k_lab/docs/02_ENVIRONMENT.md](strata_4090_128k_lab/docs/02_ENVIRONMENT.md)。

2026-10-10 核对时，next 在跑，unit 仍是 **disabled**。开机拉起的还是 27B，重启机器会把 GPU 交回 `openclaw-qwen38-ninfer.service`。

---

## 1. 现状一览

| | |
|---|---|
| systemd | `openclaw-qwen38-next.service`，**active + disabled** |
| 开机 | **不**开机启动。开机仍是 `openclaw-qwen38-ninfer.service` **enabled** |
| 调用名 | `openclaw/Qwen3.8-next` |
| 模型 | Qwen3.8-Flash-Next，GSQ-RCO **IQ3_XXS**（2026-10-09 起；之前是 IQ3_S） |
| 引擎 | `/home/hhtele/strata-0.1.41`，tag `v0.1.41`（`fb58e0d`），本机 CUDA 12.3 自编，`/metrics` 报 **0.1.41** |
| 窗口 | `--max-context 131072` |
| KV | `int8`，整段在显存（`kv_resident` 0） |
| 专家 | 内存专家区 40925 MiB；显存 9435 槽 / 15656 MiB |
| 投机 | `--spec 4 --spec-min-p 0.5`，MTP 在 `/data/strata-data/mtp/rt` |
| 对话缓存 | **开**：`--conversation-cache-mib 6144 --conversation-cache-slots 4` |
| 视觉 | 关（`images: false`） |
| 本机 API | `http://127.0.0.1:18343/v1`，无 API key |
| 对外 | NGINX `0.0.0.0:28343`，Bearer。公网入口 `http://47.106.205.246:1082/v1` |
| 内核参数 | `iommu=pt`（2026-10-09 加入，见第 7 节） |
| 空载显存 | 约 23.7 / 24.0 GiB；引擎报 `vram_free_mib` 512 |
| 内存 | 刚加载完 `MemAvailable` 约 12.4 GiB；4 段对话停放后约 9.3 GiB |
| 27B | unit inactive + enabled |

一张 4090、62 GiB 内存只跑一档。next 与 27B、llama.cpp WORK、TEXT、旧 qwen36 MTP 互斥。

---

## 2. 架构

```
Pi / curl
    │  model = openclaw/Qwen3.8-next
    │  公网：47.106.205.246:1082
    │  内网：192.168.10.29:28343
    ▼
NGINX :28343
    Bearer，只反代，不改 JSON，不记请求正文
    proxy_pass http://127.0.0.1:18343
    ▼
serve/server.py          127.0.0.1:18343
    配置 strata-iq3_xxs.json
    ▼
engine/strata            子进程，不单独监听
    专家在内存，热专家缓存在显存，未命中的由 CPU 算或经 PCIe 流到 GPU
```

和 27B 的差别：

1. next 没有兼容层，也没有 Docker。`server.py` 直接讲 OpenAI `/v1/chat/completions`。
2. 27B 的引擎在 `127.0.0.1:18030`，兼容层占 `0.0.0.0:18343`。next 在跑时 18030 不监听，18343 只绑 `127.0.0.1`。
3. next **不校验** model 字符串。请求里写成 `openclaw/Qwen3.8-27B-WORK` 也会用 next 的权重回答。27B 那边未知 id 会 404。切档后要同时改 Pi 的当前模型。
4. 引擎不绑 `0.0.0.0`。本机没有 API key，不能改成 `--host 0.0.0.0`。
5. 采样：请求不带采样字段时，Strata 是 **greedy**（配置里没有 `sampling` 块）；27B 服务端默认是 `1.0 / 0.95 / 20`。Pi 侧已按思考档位补上采样参数，见 5.3。

主机：Debian 12，内核 `6.1.0-17-amd64`，Supermicro X11SPM-TF，Xeon Silver 4216（16C/32T，引擎走 AVX2），内存 2 × 32GB DDR4-2400（6 通道只插了 2 条），GPU 在 CPU1 SLOT6 Gen3 x16。驱动 **610.57.04**，工具链只有 `/usr/local/cuda-12.3`。

---

## 3. 目录与文件

```text
现行代码（v0.1.41）
  /home/hhtele/strata-0.1.41                         tag v0.1.41 浅克隆，源码无改动
  /home/hhtele/strata-0.1.41/.venv                   Python
  /home/hhtele/strata-0.1.41/engine/strata           63999072 字节，sm_89，CUDA 12.3，BUILD.json source=local
  /home/hhtele/strata-0.1.41/run-iq3_xxs.sh          systemd 入口（现行）
  /home/hhtele/strata-0.1.41/strata-iq3_xxs.json     现行运行配置
  /home/hhtele/strata-0.1.41/strata-iq3_xxs.json.bak-cache-ab-20261010   开对话缓存前的配置
  /home/hhtele/strata-0.1.41/run-iq3_s.sh            IQ3_S 回滚入口（同一引擎）
  /home/hhtele/strata-0.1.41/strata-iq3_s.json       IQ3_S 回滚配置
  /home/hhtele/strata-0.1.41/build-engine-only.sh    CUDA 12.3 重编引擎
  /home/hhtele/strata-0.1.41/data/expert-profile-iq3xxs.bin          现行加载的画像（与上游 expert-profile.bin 相同）
  /home/hhtele/strata-0.1.41/data/expert-profile-iq3xxs-learned.bin  --expert-profile-save 写出的学习画像，尚未启用

旧代码（v0.1.40.1，回滚用，不要删）
  /home/hhtele/strata                                含 3 处本机补丁
  /home/hhtele/strata/run-iq3_s.sh、strata-iq3_s.json
  /home/hhtele/strata/switch-qwen.sh                 next | 27b | status，与版本无关，现行仍用它
  /home/hhtele/strata-patches/                       check-after-upgrade.sh、旧 diff

权重与包（不要和 /data/models/qwen 混放）
  /data/strata-data/models/IQ3_XXS/
    Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf   47039860096
    Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf   28800138432
  /data/strata-data/models/IQ3_S/                    回滚用，约 78 GiB
    Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf     54817524224
    Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf     28800138432
  /data/strata-data/packs/iq3_xxs、packs/iq3_s       各约 1.5 GiB，互不覆盖
  /data/strata-data/mtp                              约 6.45 GiB，两个量化共用

systemd
  /etc/systemd/system/openclaw-qwen38-next.service
  /etc/systemd/system/openclaw-qwen38-ninfer.service.d/conflict-next.conf

日志
  /home/hhtele/strata-0.1.41/run-iq3xxs.out          stdout/stderr，多次启动往同一文件追加
  /home/hhtele/strata-0.1.41/strata-iq3_xxs.log      引擎日志：启动探测、每个请求的 prefill/decode/命中率
  /var/log/nginx/openclaw_28343_access.log           combined，无正文

测试记录（主机上）
  /home/hhtele/pcie-test-20261009/                   PCIe 带宽、iommu 对照
  /home/hhtele/strata-0.1.41/smoke-iq3s-v41*/、smoke-iq3xxs-v41/、smoke-iq3xxs-needle/
  /home/hhtele/strata-0.1.41/cache-ab-20261010/      对话缓存交替续写
  /home/hhtele/strata-0.1.41/sampling-ab-20261010/   greedy 与推荐采样的速度对照

27B（本档不要改）
  /home/hhtele/ninfer-4090/launch/production-18343.sh
  /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer

提权
  /home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
```

主机没有 rsync。笔记本上的脚本副本是旧的，不要 scp 覆盖主机上的目录。

NGINX 配置是 `/etc/nginx/conf.d/openclaw-28343.conf`，本档没有改它：`listen 28343`，`client_max_body_size 256m`，`proxy_read_timeout` / `proxy_send_timeout` 1800s，`proxy_buffering off`。`/v1`、`/v1/`、`/metrics` 都转到 `127.0.0.1:18343`。

---

## 4. 启动参数

`run-iq3_xxs.sh`：

```sh
#!/bin/sh
cd "/home/hhtele/strata-0.1.41"
exec "/home/hhtele/strata-0.1.41/.venv/bin/python" "/home/hhtele/strata-0.1.41/serve/server.py" "--engine" "strata" "--config" "/home/hhtele/strata-0.1.41/strata-iq3_xxs.json" "--port" "18343"
```

`strata-iq3_xxs.json` 的 `args` 是权威：

```text
--pack /data/strata-data/packs/iq3_xxs
--native /data/strata-data/models/IQ3_XXS/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf
--ple-gguf /data/strata-data/models/IQ3_XXS/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf
--expert-profile /home/hhtele/strata-0.1.41/data/expert-profile-iq3xxs.bin
--expert-cache auto
--prefill auto
--spec 4
--spec-min-p 0.5
--mtp /data/strata-data/mtp/rt
--max-context 131072
--kv int8
--vram-reserve-mib 974
--conversation-cache-mib 6144
--conversation-cache-slots 4
--expert-profile-save /home/hhtele/strata-0.1.41/data/expert-profile-iq3xxs-learned.bin
```

配置其余字段：`tokenizer=/data/strata-data/packs/iq3_xxs/tokenizer`、`host=127.0.0.1`、`port=18343`、`model_name=openclaw/Qwen3.8-next`、`lib_dirs` 指向 CUDA 12.3、`open_browser=false`。没有 `env` 块、`sampling` 块、`api_key`、`fit_max_tokens`、`reasoning_budget_tokens`、`parallel`、`--kv-resident`、`--vision`。

几个参数的来历：

| 参数 | 为什么 |
|---|---|
| `--vram-reserve-mib 974` | 不加时引擎日志报 `240 MiB of VRAM free ... LOW: requests may stall; add --vram-reserve-mib 974`。加了以后槽数 9597 → 9435，空闲 512 MiB，capture 后最低约 408 MiB。数值取自引擎日志，换版本或改上下文后以新日志为准 |
| `--conversation-cache-*` | 多段对话交替时停放 KV 到内存，切回来不重读。见 6.3 |
| `--expert-profile-save` | 把运行中 adaptive tier 学到的专家热度写成画像。进程正常退出或请求间隔满 10 分钟时写出。**只写不读**，现行加载的仍是上游画像。见 6.4 |
| CPU share（无参数） | v0.1.41 默认对 <1024 token 的 prompt chunk 开启。本机实测有益，保持默认。见 8.3 |

加载后 `/metrics` 的容量字段（2026-10-10）：

| 字段 | 值 | 含义 |
|---|---|---|
| `max_context` / `kv` | 131072 / int8 | 与参数一致 |
| `expert_slots` / `expert_cache_mib` | 9435 / 15656 | 显存里的热专家 |
| `arena_mib` | 40925 | 内存里的专家区 |
| `kv_resident` | 0 | KV 不从内存流式读取 |
| `conversation_cache_mib` | 6144 | 对话缓存上限 |
| `pool_workers` | 15 | 引擎按 16 核自己选的 |
| `pcie_frac` | 0.34 | 启动探测 12.3 GB/s 自动算出；`iommu=pt` 之前是 0.22 |
| `vram_free_mib` | 512 | 缓存划完后的剩余，不是可再加的预算 |
| `spec` / `mtp_max` | 6 / 4 | 运行时自报。启动参数仍是 `--spec 4`，不要改成 6 |

unit（2026-10-09 改过 Description、WorkingDirectory、ExecStart 和输出文件，没有备份文件）：

```ini
[Unit]
Description=OpenClaw Qwen3.8-next Strata IQ3_XXS 128K
After=network-online.target
Wants=network-online.target
Conflicts=openclaw-qwen38-ninfer.service openclaw-qwen38-work-64k.service openclaw-qwen38-text.service openclaw-qwen36-mtp4-128k.service

[Service]
Type=simple
User=hhtele
Group=hhtele
WorkingDirectory=/home/hhtele/strata-0.1.41
ExecStart=/home/hhtele/strata-0.1.41/run-iq3_xxs.sh
Restart=on-failure
RestartSec=5
TimeoutStartSec=180
TimeoutStopSec=180
StandardOutput=append:/home/hhtele/strata-0.1.41/run-iq3xxs.out
StandardError=append:/home/hhtele/strata-0.1.41/run-iq3xxs.out
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

`Type=simple`：`systemctl start` 返回只说明进程起来了，不说明权重加载完，用 `/health` 判断。`Restart=on-failure` 会在加载失败时每 5 秒重拉；连续失败先看 `run-iq3xxs.out` 末尾。

27B 的 drop-in 只有一行 `Conflicts=openclaw-qwen38-next.service`。27B unit 是 `Restart=always`，被 Conflicts 停掉后还会自己起来，所以切换必须走 `switch-qwen.sh`。

---

## 5. 使用

### 5.1 谁在听

| 地址 | 谁 | 认证 |
|---|---|---|
| `127.0.0.1:18343` | next 的 `server.py`，或 27B 的兼容层 | 本机无 key。只在主机上 curl |
| `192.168.10.29:28343` | NGINX | Bearer |
| `47.106.205.246:1082` | 跳板转到 28343 | 同一个 Bearer |
| `8080`、`18030` | next 在跑时都不应监听 | — |

无 Bearer 打 28343 应是 401。不要把 18343 改到 `0.0.0.0`。

### 5.2 请求

```bash
curl -sS http://127.0.0.1:18343/health
curl -sS http://127.0.0.1:18343/v1/models
```

健康体应包含 `"model":"openclaw/Qwen3.8-next"`、`"max_context":131072`、`"loaded":true`、`"api_key":false`。

对话走 `POST /v1/chat/completions`。`reasoning_effort` 可以放在 JSON 顶层，也可以放在 `chat_template_kwargs`：

| 客户端给的值 | 实际 |
|---|---|
| `none` / `off` / `minimal` / `disabled` / `false` | `enable_thinking=false` |
| `low`、`medium` | 原样 |
| `high` / `xhigh` / `max` / `maximum` | 模板里的 `xhigh` |
| 其他 | HTTP 400 |

`prompt + max_tokens + 8` 必须 ≤ 131072，否则 HTTP 400，不会截断。思考过程占的也是 `max_tokens`；思考打满上限时 `finish_reason=length`，这是预算用完，不是服务挂了。

采样字段（`temperature`、`top_p`、`top_k`、`min_p`、`presence_penalty` 等）按请求生效；不带时是 greedy。`top_k` 在引擎里最多 64。惩罚类字段默认只统计最近 64 个 token（`penalty_last_n`），和 vLLM 统计整段输出不同，并会让投机解码慢 1–11%。

### 5.3 笔记本 Pi

文件：`~/.pi/agent/models.json`、`~/.pi/agent/settings.json`。默认模型仍是 `openclaw/Qwen3.8-27B-WORK`。next 是旁边的一条，不会因为引擎切了就自动选中。

| 字段 | next |
|---|---|
| provider | `openclaw`，`baseUrl` `http://47.106.205.246:1082/v1`，`api` `openai-completions` |
| id | `openclaw/Qwen3.8-next` |
| 显示名 | `Qwen3.8 Next (128k)` |
| `contextWindow` / `maxTokens` | 131072 / 32768 |
| `thinkingLevelMap` | off→none，minimal→low，low→low，medium→medium，high→xhigh |
| compat | `supportsDeveloperRole: false`，`supportsReasoningEffort: true`，`maxTokensField: max_tokens` |
| `samplingParams` | `temperature 1.0`、`top_p 0.95`、`top_k 20`（2026-10-10 加） |
| `samplingParamsByThinkingLevel.off` | `temperature 0.7`、`top_p 0.8`、`top_k 20`（2026-10-10 加） |

采样参数来自 Qwen3.8-Flash-Next 模型卡：思考 `1.0 / 0.95 / 20 / presence 0`，非思考 `0.7 / 0.8 / 20 / presence 1.5`。非思考档**故意没加** `presence_penalty 1.5`：Pi 的输出多是工具调用 JSON 和代码，标点和缩进本来就反复出现，加上去有格式风险；出现重复再从 0.5 往上试。加之前 Pi 不发任何采样字段，next 实际在跑 greedy。改前的文件是 `~/.pi/agent/models.json.bak-20261010-sampling`。改完要重开 Pi 才稳妥生效。

Pi 发请求前会留 4096 token 安全垫，再把 `max_tokens` 夹到剩余空间。压缩在 `contextWindow - 16384`（114688）时触发，保留最近 20000 token。Pi 的 token 估算可能偏小：2026-10-08 出现过一次 `prompt (146576 tokens) + max tokens (1)` 的 400。这是 Pi 估算问题，不是窗口不够；再出现时考虑把 Pi 的 `contextWindow` 调小（例如 120000）让压缩更早触发，而不是把引擎改成 200K。

两档不能同时真的在服务。Pi 选 next、引擎却是 27B 时，27B 会 404。引擎是 next、Pi 仍选 27B 时，Strata 会用 next 的权重回答。

### 5.4 前缀复用与并发

两层复用：

1. **当前对话**：`--prompt-cache` 默认 6 个 checkpoint。同一条 Pi 会话续写时，只读新增的尾巴。
2. **对话缓存**：切到另一段对话时，把当前对话的 KV、状态和 checkpoint 停放到内存；切回来按 token 前缀精确匹配后恢复，不用重读。不需要客户端传 session id。系统提示或工具列表一变，复用停在最后一个共同前缀。

不要开 `parallel`。单客户端开 `parallel: 2` 会把专家缓存让给第二个槽，同机型社区测量 decode 约掉 28%。这台机器只服务一路 Pi。

---

## 6. 运维

### 6.1 切换与重启

日常只用 `switch-qwen.sh`。它停掉另一档，等到 18343 关掉且显存低于 4000 MiB，再启动目标，并等到对应的 HTTP 正文出现。端口或显存 180 秒内不干净、或者 HTTP 360 秒内不对，脚本以非 0 退出。

```bash
/home/hhtele/strata/switch-qwen.sh status
/home/hhtele/strata/switch-qwen.sh next
/home/hhtele/strata/switch-qwen.sh 27b
```

切换或重启前看有没有活连接，脚本不会等它们结束：

```bash
ss -H -tn state established '( sport = :18343 or sport = :28343 )'
curl -fsS http://127.0.0.1:18343/metrics | python3 -c 'import json,sys; print(json.load(sys.stdin)["live"]["state"])'   # 应为 idle
```

手动看状态用 sudo-wrap，不要把口令写进命令行：

```bash
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
"$WRAP" systemctl status openclaw-qwen38-next.service
"$WRAP" systemctl is-enabled openclaw-qwen38-next.service openclaw-qwen38-ninfer.service
```

next 单独重启（确认 27B 已是 inactive）：

```bash
"$WRAP" systemctl restart openclaw-qwen38-next.service
curl -fsS --max-time 3 http://127.0.0.1:18343/health
```

从停到 `/health` 的 `loaded` 为 true 约 30 秒（专家约 40 GiB 进内存）。重启会清空对话缓存和 `/metrics` 计数。

### 6.2 验收

全部在主机上做：

```bash
curl -fsS http://127.0.0.1:18343/health
ss -lnt | awk '/:18343|:28343|:18030|:8080/'
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
grep -E 'PCIe probe|expert cache [0-9]+ slots|VRAM free' /home/hhtele/strata-0.1.41/strata-iq3_xxs.log | tail -3
cat /proc/cmdline
```

next 就绪时应看到：

- health 的 model 是 `openclaw/Qwen3.8-next`，`loaded` 为 true；
- 18343 只在 `127.0.0.1`，28343 在 `0.0.0.0`，18030 和 8080 没有监听；
- 引擎日志最新一次启动：`PCIe probe: 12.3 GB/s ... pcie_frac 0.34`，`expert cache 9435 slots` 左右，`512 MiB of VRAM free` 左右，且**没有** `LOW` 那一行；
- `/proc/cmdline` 含 `iommu=pt`；
- `openclaw-qwen38-ninfer` 是 inactive，且仍是 enabled。

PCIe 探测若回到 7.9 GB/s、`pcie_frac 0.22`，说明 `iommu=pt` 丢了（见第 7 节），prefill 会慢约三分之一。

### 6.3 指标

```bash
curl -fsS 'http://127.0.0.1:18343/metrics?requests=all'
```

- `requests`：最近最多 500 条完成的请求，**新的在前**。每条有 `prompt_tokens`、`reused`、`prompt_ms`、`decode_ms`、`decode_tok_s`、`drafts_offered` / `drafts_accepted`、`hit_rate`、`pcie_share`、`finish`。不记录采样参数。
- `totals`：进程启动以来的合计。
- `conversation_cache`：`parked`、`bytes`、`parks`、`restores`、`evictions`、`requests_reused`、`reused_tokens`。`restores` 持续为 0 而 Pi 在多段对话间切换，说明复用断了（常见原因是系统提示或工具列表变化）。`evictions` 增长快说明 4 个槽或 6 GiB 不够。

引擎日志 `strata-iq3_xxs.log` 每个请求一行 `prompt N tokens = R reused + M read in X ms ...`，下一行是 decode 命中率。`run-iq3xxs.out` 里的 `[strata] done` 不拆 prefill / decode。

内存要盯 `MemAvailable`。对话缓存在分配前和抓取后都会检查，低于 `--conversation-cache-min-free-mib`（默认 2560）就跳过停放、退回普通读取。主机 swap 只有 976 MiB，2026-10-09 下载核对时有脚本把整个分片读进内存触发过 OOM，引擎被 systemd 拉起过一次。**在这台机器上做大文件校验要流式读，不要整文件进内存。**

NGINX 日志属主是 `www-data:adm`，用 sudo-wrap 跑只读脚本。日志里没有提示词原文。

### 6.4 学习画像（待验证，未启用）

`data/expert-profile-iq3xxs-learned.bin` 在 2026-10-09 23:43 写出过一次，md5 与上游画像不同。要启用：

1. 等真实 Pi 流量跑过至少一两天，让它反映实际负载；
2. 先 `cp` 一份带日期的副本，`--expert-profile` 指向副本（`--expert-profile-save` 继续写原文件，不要让读写同一个文件）；
3. 重启后对照每个请求开头的命中率（`strata-iq3_xxs.log` 的 `decode expert cache hit rate`）和 decode 中位数；不好就把 `--expert-profile` 指回 `expert-profile-iq3xxs.bin`。

### 6.5 回滚

| 要回到 | 怎么做 | 状态 |
|---|---|---|
| 27B | `switch-qwen.sh 27b` | 常规操作 |
| 关掉对话缓存或学习画像写出 | `cp strata-iq3_xxs.json.bak-cache-ab-20261010 strata-iq3_xxs.json`，重启 next | 备份是开缓存前的现行配置 |
| v0.1.41 + IQ3_S | sudo-wrap 编辑 unit 的 `WorkingDirectory` 不变、`ExecStart` 改成 `/home/hhtele/strata-0.1.41/run-iq3_s.sh`，`daemon-reload` 后重启 next | 未演练。`strata-iq3_s.json` 2026-10-09 跑过 smoke，但没有 `--vram-reserve-mib`，会报 LOW；回滚前按引擎日志补上 reserve。**不要**在 IQ3_S 上开对话缓存，加载后只剩约 6.4 GiB |
| v0.1.40.1 + IQ3_S | unit 的 `WorkingDirectory` 改回 `/home/hhtele/strata`、`ExecStart` 改回 `/home/hhtele/strata/run-iq3_s.sh` | 未演练。旧树与旧引擎没动过 |
| Pi 采样 | `cp ~/.pi/agent/models.json.bak-20261010-sampling ~/.pi/agent/models.json` | — |
| `iommu=pt` | 见第 7 节 | — |

---

## 7. 主机：IOMMU 与 PCIe

2026-10-09 起内核参数是 `quiet iommu=pt`。

- 原因：默认的 IOMMU DMA 翻译（DMA-FQ）把 GPU 的 H2D 限在约 7.8 GB/s。`iommu=pt` 后，pinned H2D 7.77–7.87 → **12.14–12.28 GB/s**，D2H 8.64–8.66 → 13.08–13.17 GB/s（`/home/hhtele/pcie-test-20261009/` 的 `bw-*.txt`）。加 CPU 负载、拉满 uncore 都没用；运行时改 iommu group 类型会 I/O error，只能改内核参数重启。
- 效果：引擎探测 7.9 → 12.3 GB/s，`pcie_frac` 自动 0.22 → 0.34；IQ3_S 冷 prefill 约 +50%，decode +5–11%（8.1）。
- 代价：主机设备驱动的 DMA 不再经过 IOMMU 地址隔离。这台是单租户推理机，没有 VFIO 直通。
- 文件：`/etc/default/grub` 的 `GRUB_CMDLINE_LINUX_DEFAULT="quiet iommu=pt"`，原文件 `/etc/default/grub.bak-20261009-iommu`。
- 回滚：把备份拷回 `/etc/default/grub`，`update-grub`，重启。重启会回到 27B。

---

## 8. 已验证数字

### 8.1 128K 冷读的演进

`reasoning_effort=none`，新生成 256 token，`reused=0`，每档 1 次。

| 阶段 | 改了什么 | prefill tok/s | decode tok/s | 128K 首 token |
|---|---|---:|---:|---:|
| 2026-10-07 | v0.1.40.1，IQ3_S | 1625 | 86.3 | 约 79 s |
| 2026-10-09 | + `iommu=pt` | 2440 | 91.6 | 52.5 s |
| 2026-10-09 | + v0.1.41（仍 IQ3_S） | 2448 | 93.9 | 52.4 s |
| 2026-10-09 | + IQ3_XXS | **2986** | **127.2** | **43.0 s** |

prefill 的大头来自 PCIe 修复，decode 的大头来自 IQ3_XXS（显存多放约 18% 的专家，未命中的每个也便宜约 15%）。v0.1.41 的 IQ3_S 基线没加 `--vram-reserve-mib`（8003 槽），对 IQ3_XXS 是不利条件。

### 8.2 v0.1.41 smoke：IQ3_S 与 IQ3_XXS

prefill / decode，tok/s。结果在 `smoke-iq3s-v41/` 和 `smoke-iq3xxs-v41/`。

| 目标 token | IQ3_S | IQ3_XXS |
|---|---:|---:|
| 512 | 372.6 / 78.9 | 520.9 / 93.9 |
| 1024 | 658.0 / 92.0 | 792.7 / 124.5 |
| 4096 | 1202.8 / 96.5 | 1488.6 / 137.6 |
| 32768 | 2444.4 / 99.6 | 2987.2 / 120.4 |
| 65536 | 2489.0 / 95.9 | 3032.8 / 136.8 |
| 128000 | 2448.4 / 93.9 | 2986.4 / 127.2 |

每档 1 次，decode 的单次数字波动可达 10–20%。Needle：32K 和 128K 各 3 个深度（约 10% / 50% / 90%），6 条全部引用到唯一字符串，`finish=stop`（`smoke-iq3xxs-needle/`）。

### 8.3 CPU share（v0.1.41 默认开）

IQ3_S，同一天，冷读，每档 1 次：

| prompt | 开（默认） | `STRATA_PREFILL_CPU_SHARE=0` |
|---:|---:|---:|
| 511 | **372.6** / 78.9 | 245.6 / 77.7 |
| 1023 | **658.0** / 92.0 | 423.5 / 88.7 |
| 4096 | 1202.8 / 96.5 | 1206.0 / 97.6 |

<1024 的 chunk prefill +52–55%，decode 不降。上游 Issue #1729（Windows、i9-14900KF 混合核心、RTX 5090 D）报告开着时 decode 46 对 110 tok/s，本机没有这个现象，保持默认。没测过的：IQ3_XXS 上关掉后 32K 以上和 decode 的对照。`STRATA_PREFILL_CPU_SHARE_MAX=3072`（把分担扩到 3K 以内的 chunk）是待做的 A/B。

### 8.4 对话缓存

2026-10-10，两条真实续写交替：A 约 14K、B 约 28K，每轮先 A 后 B，6 轮 12 次，每次生成 1 token。结果在 `cache-ab-20261010/results.json`。

- 第 1 轮各自冷读：A 6.1 s，B 11.2 s。
- 第 2–6 轮全部命中，`reused` 等于该对话上一轮的完整 prompt；`prompt_ms` 0.49–0.80 s，其中快照恢复进显存 57–105 ms，其余是把另一段对话停放到内存的时间。
- 后 10 次若重读约 86.5 s，实际 6.6 s。park 11、restore 10、evict 0。可用内存 12.4 → 10.5 GiB；同一对话每多一轮快照约涨 100–200 MiB。

背景：IQ3_S 时期 278 个真实请求里，>10K 且 `reused=0` 的冷读合计 355 s，占 prefill 的 36%，主要是两段对话（14K / 28K）来回切、每次整段重读。

### 8.5 采样参数对速度的影响

2026-10-10，直连 18343，写代码类任务，输出跑满 `max_tokens`，每组 3 次交错。结果在 `sampling-ab-20261010/`。

| 场景 | greedy decode 中位 | 推荐采样 decode 中位 | 草稿接受率 |
|---|---:|---:|---|
| 非思考，短 prompt，768 token，`0.7/0.8/20` | 118.1 | 137.0 | 0.86 → 0.85–0.90 |
| 思考 low，短 prompt，1536 token，`1.0/0.95/20` | 128.6 | 124.1（−3.5%） | 0.85 → 0.77–0.82 |
| 非思考，约 8K 上下文，768 token，`0.7/0.8/20` | 137.2 | 147.2 | 0.88–0.90 → 0.88–0.98 |

结论：推荐采样不会明显变慢，思考档的 −3.5% 在 greedy 自身的波动范围内。

### 8.6 历史：IQ3_S 时期的 Pi 流量

2026-10-08 09:33–10:58 CST，v0.1.40.1 IQ3_S，`iommu=pt` 之前，132 条业务请求：prompt 复用 97.9%，decode 中位 75.1 tok/s（p90 85.0），专家命中中位 0.83，PCIe 份额中位 0.022。新增 token 中位约 313；约 70% 的请求新增不到 1024 token，所以短 chunk 的 prefill（CPU share 管的那段）对体感影响大。IQ3_XXS 上线后还没有足量真实流量数据。

---

## 9. 升级、构建与本机补丁

### 9.1 升级方式：新目录，不原地升级

v0.1.41 是装在新目录 `/home/hhtele/strata-0.1.41` 里的，旧的 `/home/hhtele/strata`（v0.1.40.1）原样保留做回滚。下一次升级照此办理：

1. 浅克隆新 tag 到 `/home/hhtele/strata-<版本>`，建 `.venv`，拷 `build-engine-only.sh` / `.py` 和 `.no-sudo-bin/`；
2. 跑 `/home/hhtele/strata-patches/check-after-upgrade.sh <新目录>`，退出码 0 才继续（v0.1.41 是 0，源码无需补丁）；
3. 用 `build-engine-only.sh` 以 CUDA 12.3 编引擎；
4. 权重、pack、MTP 都在 `/data/strata-data`，直接复用；新建配置和 `run-*.sh`，路径全部指向新目录；
5. 停服务窗口内改 unit 的 `WorkingDirectory`、`ExecStart`、输出文件，`daemon-reload`，重启，按 6.2 验收，跑 smoke 和 needle；
6. 新引擎日志若给出新的 `--vram-reserve-mib` 建议，写回配置再重启一次。

不要用 `./update.sh`。它在原目录 pull，再跑 `setup.sh --update`：有现成引擎就下，没有就本机编译。**v0.1.40 到 v0.1.41 的 Release 都没有 Linux 现成引擎**，本机 `engine/BUILD.json` 也是 `source: local`，所以实际会走编译，用的是 `setup.py` 自己挑的 nvcc，没有 `build-engine-only.sh` 的那几条约束，还会动正在服务的目录。旧文档里「`update.sh` 会下 CUDA 13 现成引擎」的说法是错的。不要 apt 安装 NVIDIA、CUDA 或 Docker，不要改驱动。

上游打开的 opt-in 里，`STRATA_STAGE_PIN` 会损坏 IQ3_S、`STRATA_ROUTE_RESIDENT` 会改变答案，不要开。

### 9.2 构建

`build-engine-only.sh` 会清掉代理和 `HF_ENDPOINT`，把 `nvcc` 钉在 CUDA 12.3，用 `.no-sudo-bin` 挡住脚本里的 sudo。`third_party/llama.cpp` 已在时不会重新下载；钉的提交是 `3cf03257f219afbe7334045ff7c6a06ac68c627d`（v0.1.41 未变）。需要重新下载时用 `https://github.com/ggml-org/llama.cpp/archive/3cf03257f219afbe7334045ff7c6a06ac68c627d.zip`，脚本里的 `codeload.github.com` 地址曾经 404。

### 9.3 权重来源

两个量化都来自 ModelScope `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`。shard 2 在 IQ3_S 和 IQ3_XXS 里内容相同（ModelScope 给的 SHA256 都是 `316b46f3…`），目前两边各存一份（不是硬链接），磁盘紧张时可以硬链接省约 27 GiB。IQ3_XXS 的 shard 1 用 aria2 下载，结果 OK。不要走 hf-mirror / `hfd.sh`，大文件会跳到不稳定的 Xet。

MTP 来自 ModelScope `Qwen/Qwen3.8-Flash-Next` 的 `master`（`2741eec155d03a8ce151b993ccce1a7b1e398d6b`）。重新下载用 `STRATA_SOURCE=modelscope`。

IQ3_XXS 相对 IQ3_S 不只压了专家：专家 3.33 → 2.84 bpw，attention 5.89 → 5.23，SSM 6.49 → 5.80，输出头 Q6_K → Q5_K，embedding IQ4_XS → IQ3_S（`tools/quantscope.py` 读文件头）。官方评测 Task avg 93.26 → 92.57（GPQA-D −1.52，LCB −0.57，AIME25 持平），差距在评测误差内；长上下文推理、中文和工具调用没有评测覆盖，靠线上观察。

### 9.4 旧树的本机补丁

`/home/hhtele/strata`（v0.1.40.1）有 3 处补丁，v0.1.40.3 起上游都有等价实现，细节见 [`strata-patches/README.md`](strata-patches/README.md)。不要把旧 diff 打到新版本上。

---

## 10. 不要改的东西

1. 不要 `enable` next，除非明确要求改变开机档。
2. 不要两档一起跑，不要 `docker rm` 27B 的容器，不要动 `/data/models/qwen` 和 `/home/hhtele/ninfer-4090`。
3. 不要改 NGINX、`production-18343.sh`、驱动、CUDA 12.3。
4. 不要把上下文加到 200K。真实 prompt 最大约 115K，正好压在 Pi 的压缩阈值下，窗口没有成为瓶颈；200K 要多占约 0.9 GiB 显存（少约 550 个专家槽，所有请求的 decode 都受影响），一段 200K 对话的停放快照 3 GiB 以上，128K 以上又是量化后最没把握的区间。
5. 不要开 `--kv-resident`、`parallel`、视觉、`fit_max_tokens`、`reasoning_budget_tokens`、`STRATA_STAGE_PIN`、`STRATA_ROUTE_RESIDENT`。
6. 不要把量化换成 IQ2_XS 或 Coder 来换速度。IQ2_XS 的 Task avg 89.16，掉了一档。
7. 不要把对话缓存加到 8 GiB 以上。加载后可用约 12.4 GiB，下限 2.56 GiB，swap 不到 1 GiB。
8. 不要删 `/data/strata-data/models/IQ3_S`、`packs/iq3_s` 和 `/home/hhtele/strata`，它们是回滚路径。

---

## 11. 故障速查

| 现象 | 先看 |
|---|---|
| 开机后模型变成 27B | 预期。next 是 disabled。需要时 `switch-qwen.sh next` |
| `switch-qwen.sh` 说端口或 GPU 没清掉 | 90 次 × 2 秒仍有 18343，或显存仍 ≥ 4000 MiB。看是谁占着，不要并行再起一个 |
| 18343 进程在，`/health` 还没有 loaded | 专家还在进内存，约 30 秒。不要在这个窗口再 start 27B |
| 引擎日志 PCIe probe 7.9 GB/s、`pcie_frac 0.22` | `iommu=pt` 丢了。`cat /proc/cmdline`，查 `/etc/default/grub`，见第 7 节 |
| 引擎日志出现 `VRAM free ... LOW` | 按日志给的数改 `--vram-reserve-mib` 后重启 |
| 切回另一段 Pi 会话又整段重读 | `/metrics` 的 `conversation_cache`：`restores` 不涨看系统提示 / 工具列表是否变了；`evictions` 涨快看槽数和预算；日志有 physical RAM admission 说明内存不够 |
| `MemAvailable` 掉到 3 GiB 以下 | 有别的进程吃内存，或停放快照太多。先查别的进程，不要再加缓存预算 |
| HTTP 400，prompt + max tokens 超过 131072 | 硬窗口，不会截断。缩短会话或让 Pi 压缩；反复出现考虑调小 Pi 的 `contextWindow` |
| `finish=length`，日志写还在思考 | `max_tokens` 用完 |
| 输出循环、同一段反复 | 先确认 Pi 已带采样参数（5.3）；greedy 下更容易循环 |
| 思考档不对，或 400 unknown effort | 客户端发了模板不认的值。Pi 的 high 已映射成 xhigh |
| 回答 model 是 next，但 Pi 选的是 27B | next 不校验 model 名。先切引擎，再改 Pi 当前模型 |
| 28343 返回 401 | Bearer，与引擎无关 |
| 28343 返回 502 / 超时 | 18343 没起来或还在加载。本机 `curl /health` |
| 加载失败后每 5 秒重拉 | `Restart=on-failure`。先停 unit，看 `run-iq3xxs.out` 末尾 |
| 进程被 OOM 杀掉后 systemd 拉起 | `journalctl -k` 找 oom-killer。2026-10-09 是下载校验脚本整文件读入内存造成的 |
| NGINX 日志里找不到提示词 | 正常。combined 只记请求行和状态 |
