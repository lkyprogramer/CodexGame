# OpenClaw Qwen3.8-27B RTX 4090 部署与使用

机器：`192.168.10.29`（用户 `hhtele`）  
GPU：单卡 RTX 4090 24GB  
文档日期：2026-08-18  
状态：**现网主力**。Qwen3.6 已停用。

评测与补丁细节在 `output/qwen38-27b-4090-20260818/`。本文只保留运维需要的事实。

---

## 1. 现在在跑什么

| 项 | 值 |
|---|---|
| systemd | `openclaw-qwen38-work-64k.service`（名字带 64k，**实际窗口 112K**） |
| 状态 | `active` + `enabled` |
| 模型文件 | `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf` |
| 调用名 | **`openclaw/Qwen3.8-27B-WORK`** |
| 本机 API | `http://127.0.0.1:18343/v1` |
| 对外 API | `http://192.168.10.29:28343/v1`（NGINX Bearer） |
| 上下文 | `n_ctx = 112128`（`-c 112000`） |
| 并发 | `-np 1`（单人单槽） |
| 空载显存 | 约 **22664–22694 MiB**，剩余约 **1.5GB** |
| 主机 RSS | 约 **3.4GB / 62GB** |

旧服务：

```text
openclaw-qwen36-mtp4-128k.service   inactive + disabled
模型名 openclaw/Qwen3.6-27B-MTP-Q4XL   不要再传
```

---

## 2. 文件位置

```text
启动脚本
  /home/hhtele/qwen38-27b-4090-20260818/launch/production-18343.sh

systemd
  /etc/systemd/system/openclaw-qwen38-work-64k.service

llama-server（含空正文补丁）
  /home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
  源码备份
    tools/server/server-schema.cpp.bak-20260818
    tools/server/server-context.cpp.bak-20260818
  补丁副本
    output/qwen38-27b-4090-20260818/patches/llama-cpp-reserve-content-tokens.diff

模型
  /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf
  SHA256 bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372

日志
  /var/log/llama/openclaw-qwen38-work-64k.log
  /var/log/llama/openclaw-qwen38-work-64k.err.log

NGINX（未改）
  /etc/nginx/conf.d/openclaw-28343.conf
```

仓库内对应副本：`output/qwen38-27b-4090-20260818/launch/`。

---

## 3. 启动参数（当前）

```bash
/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server \
  -m /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.8-27B-WORK \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c 112000 -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --spec-default --spec-type draft-mtp --spec-draft-n-max 2 \
  --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message 'Stop thinking. State the answer or the next smallest action now.' \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 --cache-reuse 256 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768
```

要点：

- MTP **n=2**，不要改回 3.6 的 n=4。
- KV **q8**，不要为了再加窗口改回 q4。
- 思考默认 **medium**，预算 4096；服务端会按 `max_tokens` 再钳一刀，给正文留余量。
- `--cache-reuse` 在该 binary 上会被拒绝并自动关掉，不影响启动。
- 单卡只能跑这一个大模型。

---

## 4. 怎么调用

模型字段必须是：

```text
openclaw/Qwen3.8-27B-WORK
```

本机：

```bash
curl -sS http://127.0.0.1:18343/v1/models

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

对外（NGINX）：

```text
POST http://192.168.10.29:28343/v1/chat/completions
Authorization: Bearer <NGINX 配置的 token>
```

无 token 应为 **401**，有 token 应为 **200**。Token 在 `/etc/nginx/conf.d/openclaw-28343.conf`，不要写进 git。

### OpenClaw 建议

| 项 | 建议 |
|---|---|
| model | `openclaw/Qwen3.8-27B-WORK` |
| base URL | `http://192.168.10.29:28343/v1`（或内网直连 18343） |
| 思考任务 `max_tokens` | ≥ 8192（2048 也有补丁兜底，但客户端仍应留足） |
| `reasoning_effort` | 走 `chat_template_kwargs`，不要只放顶层 |
| 默认思考 | medium；短 JSON / 工具名可 `enable_thinking: false` |
| 项目问题 | 先 `read_file`，不要闭卷问仓库约定 |
| 会话长度 | 历史接近 80–90K 就摘要或新开 session |
| 并发 | 不要对这张卡开第二路大模型 |

思考开着时官方采样是 `temperature=1.0, top_p=0.95, top_k=20`。关思考可用 `0.7 / 0.8 / 20`。

---

## 5. 日常运维

```bash
# 状态
systemctl status openclaw-qwen38-work-64k.service
curl -sS http://127.0.0.1:18343/v1/models
nvidia-smi

# 日志
journalctl -u openclaw-qwen38-work-64k.service -f
tail -f /var/log/llama/openclaw-qwen38-work-64k.err.log

# 重启（约 10s 内恢复 18343）
sudo systemctl restart openclaw-qwen38-work-64k.service

# 改启动参数后
sudo systemctl daemon-reload
sudo systemctl restart openclaw-qwen38-work-64k.service
```

健康检查：

```text
systemctl is-active openclaw-qwen38-work-64k.service     # active
18343 /v1/models                                         # 200，id = openclaw/Qwen3.8-27B-WORK，n_ctx ≈ 112128
28343 /v1/models 无 token                                # 401
28343 /v1/models 有 token                                # 200
nvidia-smi memory.used                                   # 约 22600–22800 MiB
```

显存若在空闲时持续往 24GB 爬，再重启一次。正常情况是一条平线，不随对话变长而涨。

---

## 6. 内存会不会溢出

**长时间挂着当主力，一般不会因为“用得久”而 OOM。** 112K KV 启动时已经占满，会话变长几乎不再涨显存。

会出问题的是：

1. 同一张卡再起一个 27B / 把 `-np` 改成 2。
2. 历史已经 90K，单次还要生成接近 32K（`--predict 32768`），会超窗口，表现为截断或报错，不一定是 GPU OOM。
3. 把窗口改回 128K（q8）。上次只剩约 665MiB，不要这么干。

主机内存：进程 RSS 约 3.4GB，整机 62GB，不是瓶颈。

想更稳：`-c 98304`（96K）能多留约 1.5GB。当前 112K 是单人长上下文的上限甜点。

---

## 7. 回滚到 Qwen3.6

两套不能同时占卡。

```bash
sudo systemctl disable --now openclaw-qwen38-work-64k.service
sudo systemctl enable --now openclaw-qwen36-mtp4-128k.service
# 确认
curl -sS http://127.0.0.1:18343/v1/models
# 此时模型名变回 openclaw/Qwen3.6-27B-MTP-Q4XL
```

3.6 启动脚本仍在 `/opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh`。

再切回 3.8：把上面两条对调。

---

## 8. 改窗口 / 重编译

改上下文：编辑 `production-18343.sh` 的 `-c`，然后 `daemon-reload` + `restart`。建议值：

| `-c` | 用途 |
|---|---|
| 65536 | 最稳，会话短 |
| 98304 | 100K 质量悬崖前 |
| **112000** | **当前** |
| 131072 | 禁止默认 |

空正文补丁在 `llama.cpp-qwen38-20260817` 的 `server-schema.cpp` / `server-context.cpp`。升级 llama.cpp 后必须重打：

```bash
cd /home/hhtele/llama.cpp-qwen38-20260817
# 重新 apply output/qwen38-27b-4090-20260818/patches/llama-cpp-reserve-content-tokens.diff
cmake --build build --config Release -j"$(nproc)" --target llama-server
sudo systemctl restart openclaw-qwen38-work-64k.service
```

没有这份补丁时，客户端 `max_tokens=2048` 且开思考，可能得到空 `content`。

---

## 9. 不要做的事

- 不要 `enable` 3.6 和 3.8 两个单元一起开机。
- 不要在测试端口 19343 再拉一份同样的 27B。
- 不要为了速度把 MTP 改成 n=4。
- 不要默认 xhigh。
- 不要假设模型闭卷记得 CodexGame 约定，必须读文件。
- 不要把 NGINX token 或 ssh 密码写进仓库。

---

## 10. 相关报告

| 文档 | 内容 |
|---|---|
| `output/qwen38-27b-4090-20260818/11-capability-eval-plan.md` | 能力深测方案 |
| `output/qwen38-27b-4090-20260818/reports/11-capability-portrait.md` | Full 能力画像 |
| `output/qwen38-27b-4090-20260818/reports/10-iteration-primary-deploy.md` | 切主力 + 空正文补丁 |
| `output/qwen38-27b-4090-20260818/reports/12-ctx-112k.md` | 64K → 112K |
| `output/qwen38-27b-4090-20260818/01-deployment-and-eval-plan.md` | 第一轮部署方案 |
