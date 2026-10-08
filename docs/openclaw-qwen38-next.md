# Qwen3.8-next · Strata IQ3_S · RTX 4090 部署与运维

机器：`192.168.10.29`（hhtele）  
GPU：单卡 RTX 4090 24GB  
文档日期：2026-10-08  
范围：Strata 上的 `openclaw/Qwen3.8-next`。27B 的架构和回滚仍以 [`openclaw-qwen38-ninfer.md`](openclaw-qwen38-ninfer.md) 与 [`openclaw-qwen38-ninfer-b0-b1-20260930.md`](openclaw-qwen38-ninfer-b0-b1-20260930.md) 为准。

不要把 NGINX Bearer、SSH 密码、sudo 口令、Pi 的 `apiKey` 写进 git。

2026-10-08 核对时，next 进程在跑，unit 仍是 **disabled**。开机拉起的还是 27B。重启机器会把 GPU 交回 `openclaw-qwen38-ninfer.service`。

---

## 1. 现状一览

| | |
|---|---|
| systemd | `openclaw-qwen38-next.service`，当时 **active + disabled** |
| 开机 | **不**开机启动。开机仍是 `openclaw-qwen38-ninfer.service` **enabled** |
| 调用名 | `openclaw/Qwen3.8-next` |
| 模型 | Qwen3.8-Flash-Next，GSQ-RCO **IQ3_S** |
| 引擎 | 本机源码构建，`/home/hhtele/strata/engine/strata`，`/metrics` 报 **0.1.40** |
| 源码 | `Niko1221/Strata` `v0.1.40.1`，`82f46a8c8f475f001ad76d92f58f4a4f8ffb0253` |
| 窗口 | `--max-context 131072` |
| KV | `int8`，整段在显存（`kv_resident` 0） |
| 投机 | `--spec 4 --spec-min-p 0.5`，MTP 在 `/data/strata-data/mtp/rt` |
| 视觉 | 关（`images: false`） |
| 本机 API | `http://127.0.0.1:18343/v1`，无 API key |
| 对外 | NGINX `0.0.0.0:28343`，Bearer。公网入口 `http://47.106.205.246:1082/v1` |
| 空载显存 | 约 **23998 / 24564 MiB**；引擎报 `vram_free_mib` 240 |
| 加载后内存 | `MemAvailable` 约 **6.5 GiB**（MemTotal 65492932 kB） |
| 27B | unit inactive + enabled；权重仍是 18210531328 字节 |

一张 4090、62GiB 内存只跑一档。next 与 27B、llama.cpp WORK、TEXT、旧 qwen36 MTP 互斥。

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
    配置 strata-iq3_s.json
    ▼
engine/strata            子进程，不单独监听
    专家在内存，热专家缓存在显存
```

和 27B 的差别：

1. next 没有兼容层，也没有 Docker。`server.py` 直接讲 OpenAI `/v1/chat/completions`。
2. 27B 的引擎在 `127.0.0.1:18030`，兼容层占 `0.0.0.0:18343`。next 在跑时 18030 不监听，18343 只绑 `127.0.0.1`。
3. next **不校验** model 字符串。请求里写成 `openclaw/Qwen3.8-27B-WORK` 也会用 next 的权重回答，响应里的 model 仍是 `openclaw/Qwen3.8-next`。27B 那边未知 id 会 404。切档后要同时改 Pi 的当前模型。
4. 引擎不绑 `0.0.0.0`。本机没有 API key，不能改成 `--host 0.0.0.0`。

主机：Debian 12，内核 `6.1.0-17-amd64`，Xeon Silver 4216，驱动 **610.57.04**，工具链只有 `/usr/local/cuda-12.3`。引擎启动日志认定这颗 CPU 走 AVX2。

---

## 3. 目录与文件

```text
代码
  /home/hhtele/strata                          源码，含本机补丁
  /home/hhtele/strata/.venv                    Python 3.11
  /home/hhtele/strata/engine/strata            引擎，56824688 字节，sm_89，CUDA 12.3
  /home/hhtele/strata/serve/server.py
  /home/hhtele/strata/run-iq3_s.sh             systemd 入口
  /home/hhtele/strata/strata-iq3_s.json        唯一运行配置
  /home/hhtele/strata/switch-qwen.sh           next | 27b | status
  /home/hhtele/strata/data/expert-profile.bin  196632 字节
  /home/hhtele/strata/.no-sudo-bin/sudo        构建时拒绝提权

权重与包（不要和 /data/models/qwen 混放）
  /data/strata-data/models/IQ3_S/
    Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf   54817524224
    Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf   28800138432
  /data/strata-data/packs/iq3_s                约 1.44 GiB
  /data/strata-data/mtp                        约 6.45 GiB

systemd
  /etc/systemd/system/openclaw-qwen38-next.service
  /etc/systemd/system/openclaw-qwen38-ninfer.service.d/conflict-next.conf

日志
  /home/hhtele/strata/run-iq3s.out             stdout/stderr，多次启动往同一文件追加
  /home/hhtele/strata/strata-iq3_s.log         引擎计时
  /var/log/nginx/openclaw_28343_access.log     combined，无正文
  /var/log/nginx/openclaw_28343_error.log

27B（本档不要改）
  /home/hhtele/ninfer-4090/launch/production-18343.sh
  /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer

提权
  /home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
```

主机没有 rsync。笔记本上的脚本副本是旧的，不要 scp 覆盖 `/home/hhtele/strata`。

NGINX 配置是 `/etc/nginx/conf.d/openclaw-28343.conf`，本档没有改它。有效指令：`listen 28343`，`client_max_body_size 256m`，`proxy_read_timeout` / `proxy_send_timeout` 1800s，`proxy_buffering off`。`/v1`、`/v1/`、`/metrics` 都转到 `127.0.0.1:18343`。访问日志是默认 combined，没有 `$request_body`。

---

## 4. 启动参数

`run-iq3_s.sh`：

```sh
#!/bin/sh
cd "/home/hhtele/strata"
exec "/home/hhtele/strata/.venv/bin/python" \
  "/home/hhtele/strata/serve/server.py" \
  "--engine" "strata" \
  "--config" "/home/hhtele/strata/strata-iq3_s.json" \
  "--port" "18343"
```

`strata-iq3_s.json` 的 `args` 是权威，不要为了追速度改这一列：

```text
--pack /data/strata-data/packs/iq3_s
--native /data/strata-data/models/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf
--ple-gguf /data/strata-data/models/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf
--expert-profile /home/hhtele/strata/data/expert-profile.bin
--expert-cache auto
--prefill auto
--spec 4
--spec-min-p 0.5
--mtp /data/strata-data/mtp/rt
--max-context 131072
--kv int8
```

配置里同时有 `host=127.0.0.1`、`port=18343`、`model_name=openclaw/Qwen3.8-next`、`open_browser=false`。没有 `api_key`、`fit_max_tokens`、`reasoning_budget_tokens`、`parallel`、`--kv-resident`、`--vision`。

加载后 `/metrics` 里和容量有关的字段（2026-10-08）：

| 字段 | 值 | 含义 |
|---|---|---|
| `max_context` / `kv` | 131072 / int8 | 与参数一致 |
| `expert_slots` / `expert_cache_mib` | 8004 / 15537 | 显存里的热专家 |
| `arena_mib` | 47962 | 内存里的专家区 |
| `kv_resident` | 0 | KV 不从内存流式读取 |
| `conversation_cache_mib` | 0 | 多会话停放缓存关着 |
| `pool_workers` | 15 | 引擎按 16 核自己选的 |
| `pcie_frac` | 0.22 | 未命中专家里交给 GPU 的比例 |
| `vram_free_mib` | 240 | 缓存划完后的剩余，不是空闲可再加的预算 |
| `spec` / `mtp_max` | 6 / 4 | 运行时自报。启动参数仍是 `--spec 4`，不要改成 6 |

unit：

```ini
[Unit]
Description=OpenClaw Qwen3.8-next Strata IQ3_S 128K
After=network-online.target
Wants=network-online.target
Conflicts=openclaw-qwen38-ninfer.service openclaw-qwen38-work-64k.service openclaw-qwen38-text.service openclaw-qwen36-mtp4-128k.service

[Service]
Type=simple
User=hhtele
Group=hhtele
WorkingDirectory=/home/hhtele/strata
ExecStart=/home/hhtele/strata/run-iq3_s.sh
Restart=on-failure
RestartSec=5
TimeoutStartSec=180
TimeoutStopSec=180
StandardOutput=append:/home/hhtele/strata/run-iq3s.out
StandardError=append:/home/hhtele/strata/run-iq3s.out
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

`Type=simple`：`systemctl start` 返回只说明进程起来了，不说明权重加载完。用 `/health` 判断。`Restart=on-failure` 会在加载失败时每 5 秒重拉；连续失败先看 `run-iq3s.out` 末尾，不要一直 restart。

27B 的 drop-in 只有一行 `Conflicts=openclaw-qwen38-next.service`。只靠 Conflicts 停 27B 不够：27B unit 是 `Restart=always`，被 Conflicts 停掉后还会自己起来。所以切换必须走 `switch-qwen.sh`，它先 `systemctl stop` 对方。

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

健康体应包含 `"model":"openclaw/Qwen3.8-next"`、`"max_context":131072`、`"loaded":true`、`"api_key":false`。`/v1/models` 的 `meta.n_ctx` 是 131072，`input_modalities` 只有 `text`。

对话走 `POST /v1/chat/completions`。`reasoning_effort` 可以放在 JSON 顶层，也可以放在 `chat_template_kwargs`。服务端映射：

| 客户端给的值 | 实际 |
|---|---|
| `none` / `off` / `minimal` / `disabled` / `false` | `enable_thinking=false` |
| `low`、`medium` | 原样 |
| `high` / `xhigh` / `max` / `maximum` | 模板里的 `xhigh` |
| 其他 | HTTP 400 |

模板只认 `xhigh`、`medium`、`low`。没有单独的 `high` 档。

`prompt + max_tokens + 8` 必须 ≤ 131072，否则 HTTP 400，正文大意是请求不会被截断。没有 `fit_max_tokens`，超窗不会悄悄改短。思考过程占的也是 `max_tokens`。配置里没有 `reasoning_budget_tokens`；思考打满上限时 `finish_reason=length`，这是预算用完，不是服务挂了。不要自行加上思考封顶。

### 5.3 笔记本 Pi

文件：`~/.pi/agent/models.json`、`~/.pi/agent/settings.json`。默认模型仍是 `openclaw/Qwen3.8-27B-WORK`。next 是旁边的一条，不会因为引擎切了就自动选中。

| 字段 | next |
|---|---|
| provider | `openclaw`，`baseUrl` `http://47.106.205.246:1082/v1` |
| id | `openclaw/Qwen3.8-next` |
| 显示名 | `Qwen3.8 Next (128k)` |
| `contextWindow` / `maxTokens` | 131072 / 32768 |
| `thinkingLevelMap` | off→none，minimal→low，low→low，medium→medium，high→xhigh |
| compat | `supportsDeveloperRole: false`，`supportsReasoningEffort: true`，`maxTokensField: max_tokens` |

Pi 发请求前会留 4096 token 安全垫，再把 `max_tokens` 夹到剩余空间。压缩在 `contextWindow - 16384` 时触发，保留最近 20000 token。估算已经顶满窗口时，Pi 仍会送 `max_tokens=1`；真实 token 若超过 131072，Strata 回 400。2026-10-08 上午出现过一次：`prompt (146576 tokens) + max tokens (1)`。这是超过硬窗口，不是把 8 token 余量配错。

两档不能同时真的在服务。Pi 选 next、引擎却是 27B 时，27B 会 404。引擎是 next、Pi 仍选 27B 时，Strata 会用 next 的权重回答。

### 5.4 前缀复用

同一条 Pi 会话会把变长的历史整段重发。命中的是**当前这一个槽**的前缀，不是多会话停放缓存。`conversation_cache_mib` 是 0。加载后只剩约 6.5 GiB，不要开对话缓存，也不要开 `parallel`。

单客户端开 `parallel: 2` 会把专家缓存让给第二个槽。同机型的社区测量里，单客户端 decode 大约掉 28%。这台机器只服务一路 Pi。

---

## 6. 运维

日常只使用 `switch-qwen.sh`。它会停掉另一档，等到 18343 关掉且显存低于 4000 MiB，再启动目标，并等到对应的 HTTP 正文出现。端口或显存 180 秒内不干净、或者 HTTP 360 秒内不对，脚本以非 0 退出。

```bash
/home/hhtele/strata/switch-qwen.sh status
/home/hhtele/strata/switch-qwen.sh next
/home/hhtele/strata/switch-qwen.sh 27b
```

切换前看有没有活连接。脚本不会等这些连接自己结束：

```bash
ss -H -tn state established '( sport = :18343 )'
```

手动看状态时用 sudo-wrap，不要把口令写进命令行：

```bash
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
"$WRAP" systemctl status openclaw-qwen38-next.service
"$WRAP" systemctl is-enabled openclaw-qwen38-next.service
"$WRAP" systemctl is-enabled openclaw-qwen38-ninfer.service
```

next 单独重启（确认 27B 已经是 inactive）：

```bash
"$WRAP" systemctl restart openclaw-qwen38-next.service
curl -fsS --max-time 3 http://127.0.0.1:18343/health
```

冷加载大约几十秒：46.84 GiB 专家进内存，之后 `/health` 的 `loaded` 才是 true。`systemctl restart` 返回早于这个时刻。

验收，全部在主机上做：

```bash
curl -fsS http://127.0.0.1:18343/health
curl -fsS http://127.0.0.1:18343/v1/models
ss -lnt | awk '/:18343|:28343|:18030|:8080/'
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
```

next 就绪时应看到：health 的 model 是 `openclaw/Qwen3.8-next`；18343 只在 `127.0.0.1`；28343 在 `0.0.0.0`；18030 和 8080 没有监听；显存大约 24GB 用到 23GB 以上；`openclaw-qwen38-ninfer` 是 inactive，且仍是 enabled。

指标：

```bash
curl -fsS 'http://127.0.0.1:18343/metrics?requests=all'
```

`requests` 最多保留最近 500 条完成的请求。每条有 `prompt_tokens`、`reused`、`prompt_ms`、`decode_ms`、`decode_tok_s`、`hit_rate`、`pcie_share`、`finish`。这是 prefill / decode 的来源。`run-iq3s.out` 里的 `[strata] done` 不拆这两段时间。进度行里的 thinking、bash、write、edit、read 是心跳，不是工具调用次数。

NGINX 日志属主是 `www-data:adm`，hhtele 直接读会权限不足。用 sudo-wrap 跑只读脚本。日志里没有提示词原文；`/var/lib/nginx/body` 里的临时文件是反代缓冲，请求结束后就没了。

回到 27B 的完成标准：`/v1/models` 出现 `openclaw/Qwen3.8-27B-WORK`，18030 和 18343 都在听，容器镜像仍是 `ninfer-4090:frontend-b0-b1-1dacb0f`。不要改 `production-18343.sh`。

---

## 7. 权重、构建与本机补丁

IQ3_S 两个分片来自 ModelScope `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`，字节数与 Hugging Face revision `ed59f92082b1e93c0e96d60a8b11aab089b52f09` 的 IQ3_S 一致。当时 ModelScope 显示的 revision 是 `master`，没有做整文件 SHA-256 对照。不要重新走 hf-mirror / `hfd.sh`，大文件会跳到不稳定的 Xet。

MTP 来自 ModelScope `Qwen/Qwen3.8-Flash-Next` 的 `master`（`2741eec155d03a8ce151b993ccce1a7b1e398d6b`）。上游钉死的 Hugging Face 提交在这台机器上返回过 500。

源码相对 `v0.1.40.1` 有三处未提交改动。它们挡住 `git pull --ff-only`，但 **v0.1.40.3 已经包含等价实现，升级后不要把旧 diff 打回去**。对照和缺了才补的写法在 [`strata-patches/README.md`](strata-patches/README.md)。主机上的副本是 `/home/hhtele/strata-patches/`，里面的 `worktree-v0.1.40.1.diff` 是升级前的原文。

| 本机改动 | v0.1.40.3 里对应的什么 |
|---|---|
| `src/core/vmm.cpp`：CUDA 12.3 改走 `cudaGetDriverEntryPoint` | `b4182a8`（#1071）同一分支，并清除失败查询的 sticky error |
| `include/strata/core/vmm.hpp`：`std::size_t` | 上游同一行已经是 `std::size_t` |
| `tools/mtp_fetch.py`：`STRATA_MTP_VERIFY_PINNED=1` | `STRATA_SOURCE=modelscope` 把 `REPO` 和 `PINNED` 设成同一个 URL，哈希照查 |

升级时只丢掉这 3 个文件的本地 diff。不要 `git reset --hard`，不要 `git clean`，不要 `stash pop`。`checkout` 之后立刻 pull，中间不要重编、不要重启服务。pull 完跑：

```bash
/home/hhtele/strata-patches/check-after-upgrade.sh /home/hhtele/strata
```

退出码 0 才算 CUDA 12.3 回退还在。非 0 时按 README 里的上游片段补缺的那一处。

`./update.sh` 还会给 sm_89 下 CUDA 13.0 的现成引擎，运行库走 pip 轮子。驱动 610.57.04 高于它要求的 580。`/usr/local/cuda-12.3` 不用改，也不要被现成包替换掉。继续用 12.3 自编时才加 `--build`，并且上面的检查必须先通过。这次没有执行升级。

必须重编时才用 `/home/hhtele/strata/build-engine-only.sh`。它会清掉代理和 `HF_ENDPOINT`，把 `nvcc` 钉在 CUDA 12.3，并用 `.no-sudo-bin` 挡住脚本里的 sudo。`third_party/llama.cpp` 已经在时，脚本不会重新下载。llama.cpp 提交是 `3cf03257f219afbe7334045ff7c6a06ac68c627d`。脚本里的 `codeload.github.com` 地址曾经 404；需要重新下载时用 `https://github.com/ggml-org/llama.cpp/archive/3cf03257f219afbe7334045ff7c6a06ac68c627d.zip`。不要 apt 安装 NVIDIA、CUDA 或 Docker，不要改驱动。

---

## 8. 已验证数字

冷读 smoke，2026-10-07，`reasoning_effort=none`，每档新生成 256 token，`reused=0`，`finish=length`。结果在 `/home/hhtele/strata/smoke-20261007/summary.json`。

| 目标 prompt | Prefill tok/s | Decode tok/s |
|---:|---:|---:|
| 1024 | 277 | 68.7 |
| 4096 | 804 | 94.0 |
| 32768 | 1624 | 90.6 |
| 65536 | 1651 | 95.7 |
| 128000 | 1625 | 86.3 |

128K 冷读的首 token 大约 79 秒。这是整段新 prompt，不是 Pi 续写。

2026-10-08 09:33–10:58 CST 的 Pi 流量，进程内 132 条业务请求：prompt 复用 97.9%，decode 中位 75.1 tok/s（p90 85.0，范围 49.9–95.4），专家命中中位 0.83，PCIe 份额中位 0.022，没有排队。64K–98K 这档 decode 中位约 75；98K 以上约 71。冷的 4 万 token prefill 大约 25–30 秒、1460 tok/s 左右。这些数是这一档配置健康时的样子。

官方 5070 12GB 上的 IQ3_S，128K 输出大约 46 tok/s。这台 24GB 卡的冷 prefill 和那一档同级，decode 更高，因为专家缓存有 15 GiB。社区里 110 tok/s 的 4090 帖用的是 128GB DDR5，或者 48GB 显存、或者 IQ2_XS。不是这台机器漏了开关。

---

## 9. 不要改的东西

1. 不要 `enable` next，除非明确要求改变开机档。重启后应回到 27B。
2. 不要两档一起跑，不要 `docker rm` 27B 的容器，不要动 `/data/models/qwen` 和 `/home/hhtele/ninfer-4090`。
3. 不要改 NGINX、`production-18343.sh`、驱动、CUDA 12.3。
4. 不要把上下文加到 200K / 262K。IQ3_S 的内存账在这台 62GiB 上只够 128K，KV 留在显存。IQ3_XXS 也没把 200K 变成安全默认。
5. 不要开 `--kv-resident`、对话缓存、`parallel`、视觉、`fit_max_tokens`、`reasoning_budget_tokens`。
6. 不要把量化换成 IQ2_XS 或 Coder 来换速度。24GB 上社区建议的质量档仍是 GSQ-RCO IQ3_S。
7. `--kv-grow` 的前提这台机器满足（单卡、有画像、KV 在显存、专家在内存），但没测过。按今天的上下文中位，大约只能多出零点几 GiB 缓存。要试必须停业务做对照，不写进启动参数。

---

## 10. 故障速查

| 现象 | 先看 |
|---|---|
| 开机后模型突然变成 27B | 预期。next 是 disabled。需要 next 时再 `switch-qwen.sh next` |
| `switch-qwen.sh` 说端口或 GPU 没清掉 | 90 次 × 2 秒仍有 18343，或显存仍 ≥ 4000 MiB。看是谁占着，不要并行再起一个 |
| 18343 进程在，`/health` 还没有 loaded | 专家还在进内存。看 `run-iq3s.out` 是否出现 ready。不要在这个窗口再 start 27B |
| HTTP 400，prompt + max tokens 超过 131072 | 硬窗口。不是把服务改成截断。缩短会话或让 Pi 压缩 |
| `finish=length`，日志写还在思考 | `max_tokens` 用完。不要加 `reasoning_budget_tokens` |
| 思考档不对，或 400 unknown effort | 客户端发了模板不认的值。Pi 的 high 已经映射成 xhigh |
| 回答 model 是 next，但 Pi 选的是 27B | next 不校验 model 名。先切引擎，再改 Pi 当前模型 |
| 28343 返回 401 | Bearer。与引擎无关 |
| 28343 返回 502 / 超时 | 18343 没起来，或还在加载。本机 `curl /health` |
| 显存接近 24GB、`MemAvailable` 只剩数 GiB | next 的正常空载。不要再开 27B、对话缓存或第二个模型 |
| 加载失败后每 5 秒重拉 | `Restart=on-failure`。先停 unit，看 `run-iq3s.out` 末尾 |
| 升级后 CUDA 12.3 编不过，或有人把旧 diff 打了回去 | 先跑 `check-after-upgrade.sh`。旧的 3 文件 diff 和 v0.1.40.3 冲突，不要 `git apply`。步骤在第 7 节 |
| NGINX 日志里找不到提示词 | 正常。combined 只记请求行和状态 |

回滚就是 `switch-qwen.sh 27b`。27B 的镜像和参数回滚见 B0+B1 记录，不在本文范围。
