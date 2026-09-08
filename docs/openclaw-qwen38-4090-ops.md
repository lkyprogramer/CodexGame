# OpenClaw Qwen3.8-27B · RTX 4090 现网与无审核档部署运维

> **现网 NInfer 的部署 / 使用 / 优化以 [`openclaw-qwen38-ninfer.md`](openclaw-qwen38-ninfer.md) 为准。** 本文保留 llama.cpp WORK 与 TEXT 的回滚细节。

机器：`192.168.10.29`，用户 `hhtele`  
GPU：单卡 RTX 4090 24GB  
文档日期：2026-08-25（NInfer 切流 2026-09-08）  
范围：现网默认是 **NInfer**（调用名仍为 `openclaw/Qwen3.8-27B-WORK`）。llama.cpp WORK 与无审核 TEXT 仍互斥、可回滚，不能双开。

仓库内启动脚本副本：

- WORK：`output/qwen38-27b-4090-20260818/launch/`
- TEXT：`output/qwen38-27b-4090-20260820-hauhau-text/launch/`

不要把 NGINX token、SSH 密码写进 git。

---

## 1. 现状一览

| | NInfer（开机默认） | llama.cpp WORK（回滚） | TEXT（无审核，按需） |
|---|---|---|---|
| systemd | `openclaw-qwen38-ninfer.service` | `openclaw-qwen38-work-64k.service` | `openclaw-qwen38-text.service` |
| 开机 | **enabled** | **disabled** | **disabled** |
| 调用名 | `openclaw/Qwen3.8-27B-WORK` | 同左 | `openclaw/Qwen3.8-27B-TEXT` |
| 权重 | `qwen3_8_27b.ninfer` 16.96 GiB MTP | Unsloth UD-Q4_K_XL Dynamic V3 | HauhauCS Aggressive Q4_K_P |
| 窗口 | 262144 | `n_ctx=200192` | 同 WORK |
| KV | `rk4v4-e8` | q4_0 | q4_0 |
| MTP | n=3 `--lm-head-draft` | draft-mtp n=2 | 同 WORK |
| 思考默认 | medium（兼容层注入；引擎默认 thinking on） | medium，budget 4096 | 同 WORK |
| 空载显存 | ~22600 MiB | **22958 / 1259 MiB** | **23306 / 911 MiB** |
| 用途 | OpenClaw coding agent | 回滚 | 无审核闲聊；不当开机 |

本机 API：`http://127.0.0.1:18343/v1`  
对外：`http://192.168.10.29:28343/v1`（NGINX Bearer，配置 `/etc/nginx/conf.d/openclaw-28343.conf`）

二进制（两档共用，含空正文补丁）：

```text
/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
```

旧服务（不要再传这个 model 名）：

```text
openclaw-qwen36-mtp4-128k.service   inactive + disabled
openclaw/Qwen3.6-27B-MTP-Q4XL
```

unit 名字带 `64k` 是历史，**实际窗口 200K**。

---

## 2. 架构约束

1. 一张 4090 只跑一个 27B。WORK 与 TEXT 的 systemd `Conflicts=` 互斥，切档会停掉对方。
2. `-np 1`：单槽。OpenClaw 与评测抢同一 18343 会排队。
3. KV 在启动时按 200K q4 预分配。会话变长几乎不再涨显存；空闲时显存应是一条平线。
4. 思考开着时，服务端会按 `max_tokens` 给正文留余量（空正文补丁）。客户端仍应把 `max_tokens` 留足（建议 ≥ 8192）。
5. `reasoning_effort` 必须走 `chat_template_kwargs`，不要只放请求顶层。
6. DFlash2、MTP n>2、200K+q8、第二路 27B：**不当现网**。

---

## 3. 目录与文件

### 3.1 WORK

```text
启动
  /home/hhtele/qwen38-27b-4090-20260818/launch/production-18343.sh
回滚（旧 XL + 112K q8）
  /home/hhtele/qwen38-27b-4090-20260818/launch/production-18343-112k-q8.rollback.sh
systemd
  /etc/systemd/system/openclaw-qwen38-work-64k.service
模型（现网）
  /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf
模型（回滚，勿覆盖）
  /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf
  SHA256 bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372
日志
  /var/log/llama/openclaw-qwen38-work-64k.log
  /var/log/llama/openclaw-qwen38-work-64k.err.log
```

### 3.2 TEXT

```text
启动
  /home/hhtele/qwen38-hauhau-text-20260820/launch/production-text-18343.sh
回滚（170K、思考关、0.7/0.80/presence 1.5）
  /home/hhtele/qwen38-hauhau-text-20260820/launch/production-text-18343-170k.rollback.sh
systemd
  /etc/systemd/system/openclaw-qwen38-text.service
模型
  /data/models/qwen/qwen38-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf
日志
  /var/log/llama/openclaw-qwen38-text.log
  /var/log/llama/openclaw-qwen38-text.err.log
```

### 3.3 共用

```text
llama-server
  /home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
空正文补丁
  output/qwen38-27b-4090-20260818/patches/llama-cpp-reserve-content-tokens.diff
  源码备份
    .../tools/server/server-schema.cpp.bak-20260818
    .../tools/server/server-context.cpp.bak-20260818
NGINX
  /etc/nginx/conf.d/openclaw-28343.conf
日志目录
  /var/log/llama/   需 hhtele 可写
```

---

## 4. 现网 WORK 启动参数

```bash
/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server \
  -m /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf \
  --alias openclaw/Qwen3.8-27B-WORK \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c 200000 -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --spec-default --spec-type draft-mtp --spec-draft-n-max 2 \
  --spec-draft-type-k q4_0 --spec-draft-type-v q4_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message 'Stop thinking. State the answer or the next smallest action now.' \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768 --no-mmproj
```

systemd：

```ini
[Unit]
Description=OpenClaw Qwen3.8 27B WORK Dynamic V3 200K q4 MTP n=2 (primary)
After=network-online.target
Wants=network-online.target
Conflicts=openclaw-qwen36-mtp4-128k.service openclaw-qwen38-text.service

[Service]
Type=simple
User=hhtele
WorkingDirectory=/home/hhtele/qwen38-27b-4090-20260818
ExecStart=/home/hhtele/qwen38-27b-4090-20260818/launch/production-18343.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/openclaw-qwen38-work-64k.log
StandardError=append:/var/log/llama/openclaw-qwen38-work-64k.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

---

## 5. 无审核 TEXT 启动参数

与 WORK **同一套运行参数**，只换权重和 alias。

```bash
/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server \
  -m /data/models/qwen/qwen38-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf \
  --alias openclaw/Qwen3.8-27B-TEXT \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c 200000 -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --spec-default --spec-type draft-mtp --spec-draft-n-max 2 \
  --spec-draft-type-k q4_0 --spec-draft-type-v q4_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message 'Stop thinking. State the answer or the next smallest action now.' \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768 --no-mmproj
```

systemd：

```ini
[Unit]
Description=OpenClaw Qwen3.8 27B TEXT HauhauCS Aggressive 200K q4 MTP n=2 (switchable)
After=network-online.target
Wants=network-online.target
Conflicts=openclaw-qwen38-work-64k.service openclaw-qwen36-mtp4-128k.service

[Service]
Type=simple
User=hhtele
WorkingDirectory=/home/hhtele/qwen38-hauhau-text-20260820
ExecStart=/home/hhtele/qwen38-hauhau-text-20260820/launch/production-text-18343.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/openclaw-qwen38-text.log
StandardError=append:/var/log/llama/openclaw-qwen38-text.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

**不要 `systemctl enable` TEXT。** 开机必须是 NInfer（`openclaw-qwen38-ninfer.service`）。

回滚 llama.cpp WORK：

```bash
sudo systemctl disable --now openclaw-qwen38-ninfer.service
sudo systemctl enable --now openclaw-qwen38-work-64k.service
```

NInfer 对外仍是 18343 / 28343。引擎在 `127.0.0.1:18030`，`openai_compat_proxy.py` 把 llama.cpp 的 `chat_template_kwargs` 转成 NInfer 字段并默认 `reasoning_effort=medium`。

---

## 6. 首次部署（机器已有 CUDA / llama.cpp 时）

下面假设 4090、CUDA、`hhtele`、`/data` 已可用。二进制用现成的 `llama.cpp-qwen38-20260817`。

### 6.1 模型

```bash
# WORK V3（不要覆盖旧 XL）
ls -lh /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf
sha256sum /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf
# 期望 3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e

# 旧 XL 回滚件必须还在
sha256sum /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf
# 期望 bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372

# TEXT
sha256sum /data/models/qwen/qwen38-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf
# 期望 ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d
```

缺 V3 时用 `HF_ENDPOINT=https://hf-mirror.com` 下 Unsloth `Qwen3.8-27B-UD-Q4_K_XL.gguf` 到 **`-dv3.gguf` 文件名**，禁止覆盖旧 XL。

### 6.2 日志目录与脚本

```bash
sudo mkdir -p /var/log/llama
sudo chown hhtele:hhtele /var/log/llama

# 从本仓库同步启动脚本
install -d /home/hhtele/qwen38-27b-4090-20260818/launch
install -d /home/hhtele/qwen38-hauhau-text-20260820/launch
install -m 700 output/qwen38-27b-4090-20260818/launch/production-18343.sh \
  /home/hhtele/qwen38-27b-4090-20260818/launch/
install -m 700 output/qwen38-27b-4090-20260818/launch/production-18343-112k-q8.rollback.sh \
  /home/hhtele/qwen38-27b-4090-20260818/launch/
install -m 700 output/qwen38-27b-4090-20260820-hauhau-text/launch/production-text-18343.sh \
  /home/hhtele/qwen38-hauhau-text-20260820/launch/
install -m 700 output/qwen38-27b-4090-20260820-hauhau-text/launch/production-text-18343-170k.rollback.sh \
  /home/hhtele/qwen38-hauhau-text-20260820/launch/
```

### 6.3 安装 unit

```bash
sudo cp output/qwen38-27b-4090-20260818/launch/openclaw-qwen38-work-64k.service \
  /etc/systemd/system/
sudo cp output/qwen38-27b-4090-20260820-hauhau-text/launch/openclaw-qwen38-text.service \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable openclaw-qwen38-work-64k.service
sudo systemctl disable openclaw-qwen38-text.service
sudo systemctl disable openclaw-qwen36-mtp4-128k.service   # 若还在
sudo systemctl start openclaw-qwen38-work-64k.service
```

### 6.4 验收 WORK

加载约 10–20s。

```bash
systemctl is-enabled openclaw-qwen38-work-64k.service   # enabled
systemctl is-active  openclaw-qwen38-work-64k.service   # active
curl -sS http://127.0.0.1:18343/v1/models
# id = openclaw/Qwen3.8-27B-WORK
# n_ctx = 200192
# size  = 17548181504

nvidia-smi --query-gpu=memory.used,memory.free --format=csv
# 约 22958 / 1259 MiB，空载余量应 ≥ 800
```

工具协议：

```bash
curl -sS http://127.0.0.1:18343/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openclaw/Qwen3.8-27B-WORK",
    "messages": [{"role":"user","content":"Call get_time with timezone UTC."}],
    "tools": [{"type":"function","function":{"name":"get_time",
      "description":"t","parameters":{"type":"object",
      "properties":{"timezone":{"type":"string"}},"required":["timezone"]}}}],
    "max_tokens": 128,
    "chat_template_kwargs": {"enable_thinking": true, "reasoning_effort": "low"}
  }'
# 期望 message.tool_calls 非空
```

对外 28343：无 Bearer → 401；有 Bearer → 200，且 `id` 仍是 WORK。

---

## 7. 切换 WORK ↔ TEXT

同一 `18343` / `28343`。切换约 10–20s（卸载 + 加载 17GB）。

```bash
# → TEXT
sudo systemctl stop openclaw-qwen38-work-64k.service
sudo systemctl start openclaw-qwen38-text.service
curl -sS http://127.0.0.1:18343/v1/models
# id = openclaw/Qwen3.8-27B-TEXT ，n_ctx = 200192
nvidia-smi --query-gpu=memory.used,memory.free --format=csv
# 约 23306 / 911 MiB

# → WORK（用完必须切回）
sudo systemctl stop openclaw-qwen38-text.service
sudo systemctl start openclaw-qwen38-work-64k.service
curl -sS http://127.0.0.1:18343/v1/models
# id = openclaw/Qwen3.8-27B-WORK ，n_ctx = 200192
```

客户端 `model` 字段必须改成当前 alias，否则 404。

TEXT 短验：

```bash
curl -sS http://127.0.0.1:18343/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openclaw/Qwen3.8-27B-TEXT",
    "messages": [{"role":"user","content":"Reply with exactly the word PONG."}],
    "max_tokens": 64,
    "chat_template_kwargs": {"enable_thinking": true, "reasoning_effort": "low"}
  }'
```

TEXT 余量只有约 0.9GB，长生成比 WORK 更靠近墙。不要长时间占着 18343 不切回。

---

## 8. 日常运维

```bash
# 谁在跑
systemctl is-active openclaw-qwen38-work-64k.service
systemctl is-active openclaw-qwen38-text.service
curl -sS http://127.0.0.1:18343/v1/models
nvidia-smi

# WORK 日志
journalctl -u openclaw-qwen38-work-64k.service -f
tail -f /var/log/llama/openclaw-qwen38-work-64k.err.log

# TEXT 日志
journalctl -u openclaw-qwen38-text.service -f
tail -f /var/log/llama/openclaw-qwen38-text.err.log

# 改脚本后
sudo systemctl daemon-reload
sudo systemctl restart openclaw-qwen38-work-64k.service   # 或 text
```

健康（开机默认）：

| 检查 | 期望 |
|---|---|
| `is-enabled` WORK | enabled |
| `is-enabled` TEXT | disabled |
| `is-active` WORK | active |
| `/v1/models` | `openclaw/Qwen3.8-27B-WORK`，`n_ctx=200192` |
| 空载显存 | ~22958 / ~1259 MiB，不随空闲时间爬升 |
| 28343 无 token | 401 |
| 28343 有 token | 200 |

显存空闲时持续往 24GB 爬：重启当前 unit。正常是平线。

进程被杀：`Restart=always`，5s 后会自己起来。若 18343 被其它 llama-server 占用，unit 会起不来，先查 `ss -ltn \| grep 18343`。

---

## 9. 调用约定

### 9.1 本机

```bash
curl -sS http://127.0.0.1:18343/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openclaw/Qwen3.8-27B-WORK",
    "messages": [{"role":"user","content":"Reply with OK only."}],
    "max_tokens": 64,
    "chat_template_kwargs": {
      "enable_thinking": false,
      "preserve_thinking": false
    }
  }'
```

### 9.2 对外

```text
POST http://192.168.10.29:28343/v1/chat/completions
Authorization: Bearer <见 nginx 配置>
```

### 9.3 OpenClaw

| 项 | 值 |
|---|---|
| model | `openclaw/Qwen3.8-27B-WORK`（切 TEXT 时改 alias） |
| base URL | `http://192.168.10.29:28343/v1` 或内网 `http://127.0.0.1:18343/v1` |
| 思考任务 `max_tokens` | ≥ 8192 |
| `reasoning_effort` | 放进 `chat_template_kwargs` |
| 默认思考 | medium；短 JSON / 只要工具名可 `enable_thinking: false` |
| 项目问题 | 先读仓库文件，不要闭卷问约定 |
| 会话 | 历史接近 180K 就摘要或新开；窗口是 200K 不是无限 |
| 并发 | 不要对这张卡再拉一路 27B |

思考开：`temperature=1.0, top_p=0.95, top_k=20`（服务端已默认）。关思考可在请求里改 `0.7 / 0.8 / 20`。

---

## 10. 回滚

### 10.1 WORK → 旧 XL 112K q8

```bash
cp /home/hhtele/qwen38-27b-4090-20260818/launch/production-18343-112k-q8.rollback.sh \
   /home/hhtele/qwen38-27b-4090-20260818/launch/production-18343.sh
sudo systemctl restart openclaw-qwen38-work-64k.service
curl -sS http://127.0.0.1:18343/v1/models
# id=WORK ，n_ctx≈112128 ，size=17912397824
```

### 10.2 TEXT → 旧 170K（思考关）

```bash
cp /home/hhtele/qwen38-hauhau-text-20260820/launch/production-text-18343-170k.rollback.sh \
   /home/hhtele/qwen38-hauhau-text-20260820/launch/production-text-18343.sh
# 若 TEXT 正在跑：
sudo systemctl restart openclaw-qwen38-text.service
```

### 10.3 切回 Qwen3.6（不推荐）

两套不能同时占卡。

```bash
sudo systemctl disable --now openclaw-qwen38-work-64k.service
sudo systemctl enable --now openclaw-qwen36-mtp4-128k.service
curl -sS http://127.0.0.1:18343/v1/models
# openclaw/Qwen3.6-27B-MTP-Q4XL
```

3.6 脚本：`/opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh`。切回 3.8 把上面 enable/disable 对调。

---

## 11. 显存与故障

长时间挂着当主力，**不会因为“用得久”而 OOM**。200K q4 启动时已经占满。

会出问题：

1. 同一张卡再起一个 27B，或把 `-np` 改成 2。
2. 上下文已经接近 200K，还要生成接近 32K（`--predict 32768`）→ 截断或报错，不一定是 GPU OOM。
3. 200K 配 q8 KV → OOM。q8 只用于 112K 回滚档。
4. TEXT 空载只剩 ~911 MiB，比 WORK 紧；长生成更危险。
5. analogalok DFlash2 250K 生成后只剩约 25 MiB，**不当现网**。

主机内存：llama-server RSS 约数 GB，整机 62GB，不是瓶颈。

空闲显存持续爬升：重启 unit。  
18343 起不来：`ss -ltn | grep 18343`，停掉占端口的进程后再 start。  
空 `content`：确认仍是 `llama.cpp-qwen38-20260817` 且打过空正文补丁；客户端 `max_tokens` 过小叠加思考也会挤掉正文。  
工具不出 `tool_calls`：查 `--jinja`、chat template、是否打到了 TEXT 档。

升级 llama.cpp 后必须重打补丁再切流：

```bash
cd /home/hhtele/llama.cpp-qwen38-20260817
# apply output/qwen38-27b-4090-20260818/patches/llama-cpp-reserve-content-tokens.diff
cmake --build build --config Release -j"$(nproc)" --target llama-server
sudo systemctl restart openclaw-qwen38-work-64k.service
```

---

## 12. 质量基线（运维需要知道的数）

同一套 QCB-4090 v1.0.0 core，32×3=96，seeds 11/29/47：

| | 冻结旧 WORK（112K q8，旧 XL） | 现网 V3 200K q4 |
|---|---:|---:|
| Hard | 46.9%（45/96） | 46.9%（45/96） |
| CBI | 46.7% | 48.3% |
| exhausted | 16 | 13 |
| agent_tool | 58% | 83% |
| bug_fix | 67% | 50% |
| code_review | 0/12 | 0/12 |
| decode tok/s | 76.7 | 77.4 |

McNemar 16 vs 16，p=1。**不是智力升级，也不该为此回滚 112K。** 200K 窗口和 AT003 收工是留下 V3 200K 的理由。

QCB 的 long_context 设计带宽只有 8K–52K，**没有证明 200K 填窗无损**。q4 KV 换窗口在这张卡上成立；「q4 与 q8 质量相同」没有单因子实验。

TEXT 没有跑 QCB。MTP n 扫描：tools 短样本 n=3 更快，思考长输出 n=2 更稳，现网保持 n=2。DFlash2 工具路径 ~40 tok/s，不当 WORK。

详细：`output/qwen38-qcb-4090-v3-eval/reports/00-v3-core-vs-work.md`。

---

## 13. 不要做的事

- 不要 `enable` TEXT 或 3.6 与 WORK 一起开机。
- 不要在 19343 / 第二张卡以外再拉一份同样的 27B 占这张 4090。
- 不要为了速度把 MTP 改成 n=4/n=6，也不要把 DFlash2 设成开机。
- 不要默认 `xhigh`。
- 不要覆盖旧 XL `Qwen3.8-27B-UD-Q4_K_XL.gguf`（回滚和冻结 QCB 基线）。
- 不要把 200K 改回 q8。
- 不要假设模型闭卷记得仓库约定。
- 不要把 NGINX token 或 ssh 密码提交进仓库。

---

## 14. 相关材料

| 路径 | 内容 |
|---|---|
| `output/qwen38-27b-4090-20260818/launch/` | WORK 脚本与 unit |
| `output/qwen38-27b-4090-20260820-hauhau-text/launch/` | TEXT 脚本与 unit |
| `output/qwen38-27b-4090-20260818/patches/` | 空正文补丁 |
| `output/qwen38-qcb-4090-baseline/reports/` | 冻结 WORK QCB |
| `output/qwen38-qcb-4090-v3-eval/reports/` | V3 200K smoke/core |
| `docs/qwen38-coding-benchmark-4090-v1.0.0/` | QCB 题集与 runner |
