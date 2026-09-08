# Qwen3.8-27B NInfer · RTX 4090 部署、使用与后续优化

机器：`192.168.10.29`（hhtele）  
GPU：单卡 RTX 4090 24GB  
文档日期：2026-09-08  
范围：现网默认推理栈。llama.cpp WORK / TEXT 只作回滚，不当开机。

不要把 NGINX token、SSH 密码、sudo 口令写进 git。

对照：

- 融合验证：`output/qwen38-27b-4090-ninfer/reports/09-fusion-final.md`
- llama.cpp WORK/TEXT 旧运维：`docs/openclaw-qwen38-4090-ops.md`
- 仓库脚本副本：`output/qwen38-27b-4090-ninfer/scripts/`

---

## 1. 现网一览

| | |
|---|---|
| systemd | `openclaw-qwen38-ninfer.service` **enabled** |
| 对外 API | `http://127.0.0.1:18343/v1` |
| 公网/内网入口 | `http://192.168.10.29:28343/v1`（NGINX Bearer，配置未改） |
| 调用名 | **`openclaw/Qwen3.8-27B-WORK`**（上层不用改 model 字段） |
| 引擎 | Docker `ninfer-4090:44a2c6c`，容器 `ninfer-4090-prod`，`127.0.0.1:18030` |
| 兼容层 | `openai_compat_proxy.py` 听 `0.0.0.0:18343` |
| 制品 | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer` |
| SHA-256 | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`（18210531328 bytes，16.96 GiB） |
| HF 来源 | `neroued/Qwen3.8-27B-NInfer` rev **`3526913004b1`**（旧 MTP 制品，**不是** main 上 19G DFlash2） |
| 源码树 | `tensorninja/ninfer-4090@44a2c6c`（含 sergiuszm sm_89 + UDP E8） |
| 窗口 | `--max-context 262144 --kv-capacity 262144` |
| KV | `rk4v4-e8` |
| 投机 | MTP `--draft-tokens 3 --lm-head-draft` |
| 思考默认 | **medium**（兼容层注入；引擎自身缺省是 xhigh） |
| 并发 | `--max-concurrency 1` |
| 空载显存 | **22594 / 24564 MiB** |
| llama.cpp WORK | `openclaw-qwen38-work-64k.service` **disabled** |
| TEXT | `openclaw-qwen38-text.service` **disabled** |

一张 4090 只跑一个 27B。NInfer / WORK / TEXT / 评测容器互斥。

---

## 2. 架构

```
OpenClaw / Pi / curl
        │
        │  model = openclaw/Qwen3.8-27B-WORK
        ▼
  NGINX :28343  (Bearer，只反代，不改 JSON)
        │
        ▼
  python3 openai_compat_proxy.py    :18343  0.0.0.0
        │  改写 chat_template_kwargs
        │  默认 reasoning_effort=medium
        │  /v1/models 同时给 OpenAI data + llama.cpp models
        ▼
  ninfer-serve (docker, host network)
        127.0.0.1:18030
        权重 bind-mount 只读
        L1/L2 continuation cache
```

为什么必须有兼容层：

1. 裸 NInfer 只认顶层 `reasoning_effort` / `enable_thinking`。llama.cpp 客户端常用 `chat_template_kwargs.enable_thinking`，直接打会 **400**。
2. 客户端不带 effort 时，NInfer 模板按 **xhigh** 渲染，不是 WORK 的 medium。
3. llama.cpp 的 `/v1/models` 有 `models[].name`；NInfer 只有 OpenAI `data[].id`。兼容层两套都返回。

引擎不绑 `0.0.0.0:18030`，避免绕过兼容层。

---

## 3. 部署

### 3.1 前置

- Debian 12，驱动已升到能跑 CUDA 13.2 容器（现网 `nvidia-smi` 显示 610.x / CUDA 13 系即可）。
- Docker + NVIDIA Container Toolkit，`hhtele` 在 `docker` 组。
- 镜像 `ninfer-4090:44a2c6c` 已在本机（`Dockerfile.sm89-nobake`，`FROM nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`，不烤权重）。
- 制品已落盘且 SHA 对得上。**不要**用 HF `main` 上 19.03 GiB DFlash2 文件替换，loader 合同不同。

4090 默认不能 GitHub；构建在能拉基础镜像的环境做，再 `docker save | scp`。权重走 hf-mirror，`HF_HUB_DISABLE_XET=1`。

### 3.2 机器上的文件

```text
/home/hhtele/ninfer-4090/launch/production-18343.sh
/home/hhtele/ninfer-4090/launch/production-stop.sh
/home/hhtele/ninfer-4090/launch/openai_compat_proxy.py
/home/hhtele/ninfer-4090/cache/          # L2 host cache
/etc/systemd/system/openclaw-qwen38-ninfer.service
/etc/systemd/system/openclaw-qwen38-work-64k.service.d/conflict-ninfer.conf
/etc/systemd/system/openclaw-qwen38-text.service.d/conflict-ninfer.conf
/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
/var/log/llama/openclaw-qwen38-ninfer.log
/var/log/llama/openclaw-qwen38-ninfer.err.log
```

仓库副本：`output/qwen38-27b-4090-ninfer/scripts/`。安装脚本：`cutover_ninfer_18343.sh`（只在 4090 上跑）。

### 3.3 引擎启动参数（现网）

`production-18343.sh` 里 docker 命令：

```bash
docker run -d --name ninfer-4090-prod --gpus all --restart=no --network host \
  -v /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer:/opt/ninfer/models/qwen3_8_27b.ninfer:ro \
  -v /home/hhtele/ninfer-4090/cache:/var/cache/ninfer \
  ninfer-4090:44a2c6c \
  /opt/ninfer/models/qwen3_8_27b.ninfer \
  --model-id openclaw/Qwen3.8-27B-WORK \
  --host 127.0.0.1 --port 18030 \
  --max-context 262144 --kv-capacity 262144 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib 6144 \
  --continuation-cache-l2-mib 8192 \
  --preserve-thinking \
  --default-max-tokens 32768 \
  --temperature 1.0 --top-p 0.95 --top-k 20 --presence-penalty 0.0
```

systemd `Type=simple`：脚本等到 `18030 /v1/models` 通了之后 `exec` 兼容层，兼容层是主进程。`TimeoutStartSec=300`。Docker `--restart=no`，重启由 systemd 管。

`Conflicts=` 会停掉 WORK / TEXT。WORK/TEXT 的 drop-in 也 Conflict 回 NInfer。

### 3.4 首次切流（已做过，留作复装）

```bash
# 在 4090 上，脚本在 /tmp/ninfer-prod/
bash /tmp/ninfer-prod/cutover_ninfer_18343.sh
```

它会：拷 launch 文件 → 装 unit → `disable --now` WORK → `enable --now` NInfer。NGINX 28343 不用动。

### 3.5 日常启停

```bash
sudo systemctl status openclaw-qwen38-ninfer.service
sudo systemctl restart openclaw-qwen38-ninfer.service   # 冷启动约 30–90s
sudo journalctl -u openclaw-qwen38-ninfer.service -n 80 --no-pager
tail -f /var/log/llama/openclaw-qwen38-ninfer.log
docker logs -f ninfer-4090-prod
```

健康检查：

```bash
curl -sS http://127.0.0.1:18343/v1/models
# data[0].id 与 models[0].name 均为 openclaw/Qwen3.8-27B-WORK
# data[0].meta.n_ctx == 262144

ss -ltn | grep -E '18343|18030|28343'
# 18343 0.0.0.0   18030 127.0.0.1   28343 nginx
pgrep -a llama-server   # 现网应为空
nvidia-smi              # 空载约 22600 MiB
```

### 3.6 回滚到 llama.cpp WORK

```bash
sudo systemctl disable --now openclaw-qwen38-ninfer.service
sudo systemctl enable --now openclaw-qwen38-work-64k.service
curl -sS http://127.0.0.1:18343/v1/models   # n_ctx 回到 200192
```

TEXT 仍按旧文档按需开，开完必须切回 **NInfer**，不要 enable TEXT。

---

## 4. 使用

### 4.1 端点

| 谁 | URL | 鉴权 |
|---|---|---|
| 本机 / 隧道 | `http://127.0.0.1:18343/v1` | 无 |
| 局域网 OpenClaw | `http://192.168.10.29:28343/v1` | `Authorization: Bearer <NGINX token>` |
| 引擎直连 | `http://127.0.0.1:18030/v1` | 无；**不要给上层用**（无 medium 注入、无 kwargs 兼容） |

`model` 填 **`openclaw/Qwen3.8-27B-WORK`**。兼容层还会把 `qwen3.8-27b` 等别名改写成这个 id。

### 4.2 思考（medium）

现网默认 **thinking on + medium**。三种等价写法：

```json
{"model":"openclaw/Qwen3.8-27B-WORK","messages":[{"role":"user","content":"..."}]}
```

```json
"reasoning_effort": "medium"
```

```json
"chat_template_kwargs": {
  "enable_thinking": true,
  "reasoning_effort": "medium",
  "preserve_thinking": false
}
```

关思考：

```json
"enable_thinking": false
```

或 `"reasoning_effort": "none"`。兼容层会把 `enable_thinking: false` 转成 `reasoning_effort=none`。

NInfer 支持的 effort：`none` / `low` / `medium` / `xhigh`。**不支持** llama.cpp 的 `high` / `minimal` / `max`（会 400）。

思考文本在 `choices[0].message.reasoning_content`。`--preserve-thinking` 已开：后续 turn 会保留已结束的 reasoning，除非请求里显式 `preserve_thinking: false`。

`max_tokens` 建议 ≥ 8192。服务端默认 32768。思考开着时预算会分给 reasoning + 正文。

### 4.3 采样

服务端默认对齐旧 WORK：`temperature 1.0`、`top_p 0.95`、`top_k 20`、`presence_penalty 0`。请求字段覆盖服务端。

### 4.4 流式

`stream: true`。`stream_options` 只保留 `include_usage`，其它键会被兼容层丢掉（否则 NInfer 400）。

### 4.5 工具 / Agent

OpenAI `tools` / `tool_choice` 可用。`--prefix-checkpoint-policy rolling-tool`：工具历史前进后检查点跟着走，适合 Pi / OpenClaw 多轮 tool。

`--max-concurrency 1`：深 prefill 会堵住队列。`--pending-timeout-ms 600000`。不要拿这张卡当多用户网关。

### 4.6 前缀缓存

同进程内 **完全相同** 的 prompt 前缀会命中（实测 100k exact TTFT ~0.6s，cached ≈ 99697）。追加 tool 结果走 append，约 3.3s。

L1 6GiB GPU / L2 8GiB host。不是通用 HTTP 结果缓存，是 NInfer continuation / compatible-prefix。客户端改写最近一条 user（把 reminder 拼进去）时，复用可能变成 0——这是已知 Agent 痛点，见第 7 节。

### 4.7 curl 例子

```bash
# 列表
curl -sS http://127.0.0.1:18343/v1/models | python3 -m json.tool

# 本机，默认 medium
curl -sS http://127.0.0.1:18343/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openclaw/Qwen3.8-27B-WORK",
    "messages": [{"role":"user","content":"用一句话说明 prefill 和 decode 的区别。"}],
    "max_tokens": 1024
  }'

# OpenClaw 风格 kwargs
curl -sS http://127.0.0.1:18343/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openclaw/Qwen3.8-27B-WORK",
    "messages": [{"role":"user","content":"PONG"}],
    "max_tokens": 256,
    "chat_template_kwargs": {
      "enable_thinking": true,
      "reasoning_effort": "medium",
      "preserve_thinking": false
    }
  }'
```

对外 28343 加上 `Authorization: Bearer …`，token 只在 `/etc/nginx/conf.d/openclaw-28343.conf`。

### 4.8 和旧 WORK 的差异（上层能感知的）

| | 旧 llama.cpp WORK | 现网 NInfer |
|---|---|---|
| model 字符串 | `openclaw/Qwen3.8-27B-WORK` | 同左 |
| `/v1/models` | `models` + `data` | 兼容层对齐 |
| `n_ctx` | 200192 | **262144** |
| `chat_template_kwargs` | 原生 | 兼容层翻译 |
| `reasoning_effort` | 也接受 kwargs | 顶层或 kwargs；不要发 `high`/`max` |
| 思考输出 | `reasoning_content` | 同左 |
| 184k decode（off 阶梯） | ~38 t/s | ~87 t/s |
| Java 三题 p50 | ~32s | ~26–31s |
| 权重格式 | GGUF | `.ninfer`，不能混用 |

---

## 5. 运维约束

1. **评测会停现网。** `4090_ninfer_start.sh` 会 `systemctl stop openclaw-qwen38-ninfer`，另起容器 `ninfer-4090` 占 GPU。结束后必须 `4090_ninfer_stop_restore.sh`，它会重新拉生产 unit。
2. 实验容器不要和 `ninfer-4090-prod` 抢 `18030`。
3. 空闲显存应是平线（KV 启动时按 262k 预分配）。空闲掉到接近 0 再涨，多半是别的进程。
4. 镜像 tag 钉死 `44a2c6c`。不要 `docker pull` 浮动 latest。
5. 制品 SHA 钉死。HF `main` 已变成 19G DFlash2，直接替换会加载失败或静默错模型。
6. 驱动/CUDA 工具链：容器内 CUDA 13.2；宿主机 toolkit 保持 12.3 也可以跑该镜像，但不要在宿主机乱升 nvcc 来“重编 llama”。

---

## 6. 已验证数字（本机 4090）

thinking=off HTTP 阶梯，针全中。Java 为 Pi 三题。

| 档 | 4k / 64k / 120k / 184k decode | 184k TTFT | Java |
|---|---|---:|---|
| llama.cpp WORK 200k n=2 | 78 / 60 / 47 / **38** t/s（medium 套件） | 134s | 3/3 p50 32s |
| **现网 262k rk4 n=3** | 112 / 111 / 110 / **87** | 94s | **3/3** 38/24/26s |
| draft n=5 | … / **76** | 95s | — |
| rk2v4-e8 | 109 / 98 / 92 / 88 | **110s** | **2/3** |

社区 greedy 代码 148 t/s、MTP7 greedy 230 t/s **不能**当 Agent 目标。采样 + 长上下文是另一回事。

切流当日 smoke：kwargs 请求 200，有 `reasoning_content`；省略 effort 也有 reasoning。

---

## 7. 后续可优化（按优先级）

不要再长第四棵 fork。基线保持 `tensorninja@44a2c6c`。

### P0 — 现网行为，不改内核

| 项 | 说明 | 风险 |
|---|---|---|
| 真实 OpenClaw 会话观察 | **Pi Java 三题已在现网 18343 跑过**（见 `reports/10-pi-prefix-prod.md`）：24 请求，prefix 命中约 **85%**，`stable_prefix_restores +20`。L1/L2 continuation lookup 仍为 0。 | 无 |
| `auto-long-anchors` 取证 | Pi **追加历史** 已经命中。HTTP 探针里把 reminder 拼进**根 user** 则 cache=0。还缺的是 OpenClaw 自己那种改写形状，不是再跑 Java 三题 | 中：要改 frontend，不是配置 |
| L3 disk cache | 合成 dump 重建后 **不命中**。若要做，必须用真实多轮 session 重启测 TTFT | 磁盘磨损；先不要开 |
| 兼容层补 `high`→`xhigh` 映射 | 若某客户端仍发 llama.cpp `high`/`max` | 低 |

### P1 — 配置旁路，不当默认

| 项 | 已测 | 建议 |
|---|---|---|
| `--draft-tokens 4` | 184k 94 vs 87；短档更慢 | 不改默认 |
| `--draft-tokens 5` | 184k **76** | 禁止 |
| `rk2v4-e8` | 容量更好，184k TTFT +17s，Java 题3 未过 | 不当默认；若只做超长检索可另开 unit |
| ctx > 262144 / YaRN | 未测，模型 native 262k | 不做 |

### P2 — 源码补丁，单独镜像 tag

| 来源 | 内容 | 可行性 |
|---|---|---|
| UDP `e8_root_codec` bfi/redux | 只加速 **rk2** 编码 | 补丁小；rk4 现网无感 |
| UDP T=1 draft-head Ada MMA | 可能 1–3% decode | 同类 Q4/Q5 优化在这张卡 Linux 上回退过，必须 HTTP 阶梯，掉 >3% 丢弃 |
| sergiuszm `--auto-long-anchors` | Agent 改写历史时 TTFT 16s→0.6s（作者数） | **最值得**的下一工程；不能整树 merge 09-04 上游（会拆 INT8 prefill，且曾导致 E8 decode 垃圾 logits） |
| 把兼容层逻辑做进 ninfer | 去掉 Python 代理 | 要重建镜像；现在代理已经够用 |

明确不做：UDP DirectStorage/D3D12（`_WIN32`）；19G DFlash2 制品；并发 4；把 18030 暴露给上层。

### P3 — 工程卫生

- 兼容层改成 chunked 之外的更稳 SSE（当前已是 chunked 流式，长生成不要再缓冲整包）。
- systemd `ExecStartPre` 清残留容器，避免 `ninfer-4090` 实验名冲突。
- `/metrics` 接到既有监控，看 draft accept 和 cache_tier。
- 评测脚本默认 restore **NInfer**（已改 `4090_ninfer_stop_restore.sh` / `4090_vllm_ctl.sh`），不要再 start WORK。

---

## 8. 故障速查

| 现象 | 先查 |
|---|---|
| 18343 通、思考像“特别能想” | 请求没带 effort 且绕过了 18343 打到 18030（xhigh） |
| 400 `chat_template_kwargs.enable_thinking is not supported` | 打到了 18030，或兼容层没起来 |
| 400 `unknown parameter` / `stream_options` | 多出来的 OpenAI 字段；兼容层只白名单 `include_usage` |
| 404 `model not found` | model 字符串不在别名表且不是 WORK id |
| 18343 无进程、GPU 空 | `systemctl status openclaw-qwen38-ninfer`；看 err.log / `docker logs ninfer-4090-prod` |
| GPU 被占但 18343 失败 | 评测容器 `ninfer-4090` 还在；`docker rm -f` 后 `systemctl start` 生产 |
| OOM / 容器 Exited | 不要加 L1、不要开 vision、不要把 ctx 和 L3 一起加；先回当前参数 |
| 28343 401 | NGINX Bearer，与 NInfer 无关 |

回滚命令见 §3.6。
