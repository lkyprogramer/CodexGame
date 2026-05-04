# OpenClaw Executor 运维手册

## 1. 文档目的

本文档用于完整说明截至 **2026-03-09**，4090 机器上新的 `openclaw-executor` 服务配置、访问方式、文件位置、运维命令、请求示例、切换原因与回滚方式。

目标读者假设为：

- 没参与过本次模型切换；
- 但需要继续使用、排障或回滚这套服务。

---

## 2. 当前结论

当前 4090 线上默认模型已经切换为：

- 模型：`Qwen3.5-27B-UD-Q4_K_XL`
- 别名：`openclaw/Qwen3.5-27B-UD-Q4_K_XL`
- 端口：`18343`
- Host：`0.0.0.0`
- 服务名：`openclaw-executor.service`

这次切换的目标不是提升通用问答表现，而是针对 `openclaw` 这类 **agentic coding / JSON-only / 自动执行** 场景做专门优化。

当前配置重点：

- 使用 `UD-Q4_K_XL` 作为 executor 主力模型；
- 上下文收敛到 `64K`；
- 关闭 `thinking`；
- 使用更保守的采样参数；
- 保持原有对外入口不变。

---

## 3. 机器与访问链路

### 3.1 GCP 跳板机

- 实例名：`instance-20260222-145427`
- Zone：`us-central1-a`
- Project：`project-d4e4f88c-f262-47af-b5b`

登录方式：

```bash
gcloud compute ssh \
  --zone "us-central1-a" \
  "instance-20260222-145427" \
  --project "project-d4e4f88c-f262-47af-b5b" \
  --tunnel-through-iap
```

### 3.2 4090 目标机

- 地址：`100.107.189.100`
- 用户：`hhtele`
- 密码：`hhtele`
- 系统：`Debian 12`
- GPU：`NVIDIA GeForce RTX 4090 24GB`

从跳板机进入 4090：

```bash
sshpass -p hhtele ssh -o StrictHostKeyChecking=no hhtele@100.107.189.100
```

### 3.3 GCP 网关入口

当前对外入口不变：

- 基地址：`http://34.123.73.240/v1`
- 健康检查：`http://34.123.73.240/healthz`

鉴权仍走 GCP 网关 Bearer token。明文 token 不写入仓库文档；查看方法见 [GCP_QWEN_OPENAI_GATEWAY_RUNBOOK.md](/Users/luo/Documents/github/CodexGame/GCP_QWEN_OPENAI_GATEWAY_RUNBOOK.md)。

---

## 4. 当前部署状态

### 4.1 当前在线服务

- 当前 systemd 服务：`openclaw-executor.service`
- 当前模型别名：`openclaw/Qwen3.5-27B-UD-Q4_K_XL`
- 当前端口：`18343`
- 当前接口：OpenAI 兼容 `/v1/*`

### 4.2 已停用但保留的旧服务

旧服务没有删除，只是停用：

- 旧服务文件：`/etc/systemd/system/llama-qwen.service`
- 旧脚本文件：`/opt/llama.cpp/run-qwen.sh`
- 当前状态：
  - `llama-qwen`: `disabled`
  - `llama-qwen`: `inactive`

这意味着：

- 当前服务已不是蒸馏模型；
- 但如果后续要回滚，不需要重新写旧文件，只需重新启用旧服务即可。

---

## 5. 关键文件位置

### 5.1 启动脚本

当前生效脚本：

[`/opt/llama.cpp/run-openclaw-executor.sh`](/opt/llama.cpp/run-openclaw-executor.sh)

当前内容：

```bash
#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
exec /opt/llama.cpp/build/bin/llama-server \
  -m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.5-27B-UD-Q4_K_XL \
  -ngl 99 \
  -c 65536 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --temp 0.2 \
  --top-p 0.90 \
  --top-k 20 \
  --min-p 0.0 \
  --reasoning-format none \
  --chat-template-kwargs '{"enable_thinking": false}' \
  --host 0.0.0.0 \
  --port 18343
```

### 5.2 systemd 服务文件

当前生效服务：

[`/etc/systemd/system/openclaw-executor.service`](/etc/systemd/system/openclaw-executor.service)

当前内容：

```ini
[Unit]
Description=openclaw executor on llama.cpp Qwen3.5 27B UD-Q4_K_XL
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hhtele
WorkingDirectory=/opt/llama.cpp
ExecStart=/opt/llama.cpp/run-openclaw-executor.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/openclaw-executor.log
StandardError=append:/var/log/llama/openclaw-executor.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

### 5.3 模型文件

当前服务使用模型：

[`/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf`](/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf)

旧蒸馏模型仍保留在：

[`/data/models/qwen/Qwen3.5-27B.Q4_K_M.gguf`](/data/models/qwen/Qwen3.5-27B.Q4_K_M.gguf)

### 5.4 日志文件

新服务日志：

- 标准输出：[`/var/log/llama/openclaw-executor.log`](/var/log/llama/openclaw-executor.log)
- 标准错误：[`/var/log/llama/openclaw-executor.err.log`](/var/log/llama/openclaw-executor.err.log)

旧服务日志仍保留：

- [`/var/log/llama/qwen-server.log`](/var/log/llama/qwen-server.log)
- [`/var/log/llama/qwen-server.err.log`](/var/log/llama/qwen-server.err.log)

---

## 6. 参数设计与实际作用

这套配置和之前的通用蒸馏服务不同，它是为 `openclaw` 场景专门收敛过的 executor profile。

### 6.1 关键差异

相对旧线上配置，当前这套变更了 5 个核心点：

- 模型从蒸馏 `Q4_K_M` 切到 `UD-Q4_K_XL`
- 上下文从 `262144` 收敛到 `65536`
- `thinking` 从默认开启改为关闭
- 增加 `--reasoning-format none`
- 采样从 `temp=0.6 / top-p=0.95` 收紧到 `temp=0.2 / top-p=0.90`

### 6.2 每个参数的作用

- `-m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf`
  - 指定当前 executor 使用的本地 GGUF 模型文件。
  - 这里选基线 `UD-Q4_K_XL`，不是蒸馏版。

- `--alias openclaw/Qwen3.5-27B-UD-Q4_K_XL`
  - 对外暴露稳定模型名。
  - `openclaw` 调用时不再依赖本地文件名。

- `-ngl 99`
  - 尽可能把模型层全部放到 GPU。
  - 对 4090 单卡来说应保持不变。

- `-c 65536`
  - 把上下文窗口收敛到 `64K`。
  - 这是 executor 配置的关键差异之一。
  - 原因不是模型不能跑 `262K`，而是 agent loop 更看重吞吐、首 token 延迟和 step 频率。

- `-np 1`
  - 保持单槽。
  - 避免 agent step 之间互相抢上下文资源。

- `-fa on`
  - 开启 Flash Attention。
  - 64K 下仍应保留。

- `-ctk q4_0`
  - 将 KV cache 的 K 压成 `q4_0`。
  - 继续节省显存。

- `-ctv q4_0`
  - 将 KV cache 的 V 压成 `q4_0`。
  - 和 `-ctk` 配套。

- `--temp 0.2`
  - 降低随机性。
  - 对结构化输出、最小修复和协议服从更有利。

- `--top-p 0.90`
  - 收紧采样分布。
  - 减少格式漂移和无关扩写。

- `--top-k 20`
  - 保守采样。
  - 适合 patch / script / JSON 交付。

- `--min-p 0.0`
  - 不做额外裁剪。
  - 保持代码 token 生成稳定。

- `--reasoning-format none`
  - 禁止服务端试图从回答中拆 `reasoning_content`。
  - 这有助于减少 agent 场景下的格式分裂。

- `--chat-template-kwargs '{"enable_thinking": false}'`
  - 显式关闭 thinking。
  - 原因不是 thinking 没价值，而是 `openclaw` 更怕前置分析污染机器可解析输出。

- `--host 0.0.0.0`
  - 保持原线上入口不变。
  - GCP 网关与调用方不需要跟着改 host。

- `--port 18343`
  - 保持原线上入口不变。
  - GCP 网关也无需改端口。

---

## 7. 为什么选择这套配置

结论来自两类评测结果：

- 通用 coding / 长上下文对比：
  - [final_three_round_report.md](/Users/luo/Documents/github/CodexGame/output/model-compare-v2/20260308-130031/summary/final_three_round_report.md)
- agentic coding 严格 JSON 交付对比：
  - [agentic_compare_detailed_report.md](/Users/luo/Documents/github/CodexGame/output/model-compare-agentic/20260308-232041/summary/agentic_compare_detailed_report.md)

核心判断：

- 蒸馏模型更适合 reviewer / planner / long-context analyst
- `UD-Q4_K_XL` 更适合严格 JSON-only 的 executor

因此当前线上把“默认主力模型”改成了更偏 agent 的基线配置。

---

## 8. 服务运维命令

### 8.1 查看服务状态

```bash
systemctl status openclaw-executor --no-pager
```

### 8.2 查看实时日志

```bash
journalctl -u openclaw-executor -f
```

### 8.3 重启服务

```bash
sudo systemctl restart openclaw-executor
```

### 8.4 停止服务

```bash
sudo systemctl stop openclaw-executor
```

### 8.5 开机自启状态

```bash
systemctl is-enabled openclaw-executor
```

### 8.6 检查进程参数

```bash
ps -ef | grep llama-server | grep openclaw
```

---

## 9. 接口与请求示例

### 9.1 获取模型列表

```bash
curl -s http://34.123.73.240/v1/models \
  -H 'Authorization: Bearer <gateway-api-key>'
```

预期模型名：

```text
openclaw/Qwen3.5-27B-UD-Q4_K_XL
```

### 9.2 Python 调用示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://34.123.73.240/v1",
    api_key="<gateway-api-key>",
)

resp = client.chat.completions.create(
    model="openclaw/Qwen3.5-27B-UD-Q4_K_XL",
    messages=[
        {
            "role": "system",
            "content": "Return strict JSON only."
        },
        {
            "role": "user",
            "content": "Write a bash script that counts ERROR signatures in a log file."
        }
    ],
    max_tokens=1024,
    stream=False,
)

print(resp.choices[0].message.content)
```

### 9.3 curl 调用示例

```bash
curl -s http://34.123.73.240/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <gateway-api-key>' \
  -d '{
    "model": "openclaw/Qwen3.5-27B-UD-Q4_K_XL",
    "messages": [
      {
        "role": "system",
        "content": "Return strict JSON only."
      },
      {
        "role": "user",
        "content": "What is 2+2?"
      }
    ],
    "max_tokens": 64,
    "stream": false
  }'
```

### 9.4 请求约定

对 `openclaw` 这套 executor，推荐遵循这些约定：

- 用 `system + user`
- 不用 `developer`
- 默认 `stream=false`
- 明确要求 JSON-only 或 schema-constrained output
- `max_tokens` 不要太小，实际任务建议至少 `512` 或 `1024`

---

## 10. 故障排查

### 10.1 `/v1/models` 返回的模型名不对

先检查：

```bash
systemctl status openclaw-executor --no-pager
```

再看脚本内容：

```bash
sed -n '1,220p' /opt/llama.cpp/run-openclaw-executor.sh
```

### 10.2 GCP 网关返回 502 / 504

先检查 4090 上服务：

```bash
systemctl status openclaw-executor --no-pager
```

再检查网关日志：

```bash
sudo tail -n 200 /var/log/nginx/qwen-openai-error.log
```

### 10.3 服务起不来

检查 stderr：

```bash
tail -n 200 /var/log/llama/openclaw-executor.err.log
```

再检查 journal：

```bash
journalctl -u openclaw-executor --no-pager -n 200
```

### 10.4 显存异常升高

查看 GPU：

```bash
nvidia-smi
```

如果发现与当前配置不一致，优先检查是否误改了：

- `-c`
- `-np`
- `-ctk`
- `-ctv`

---

## 11. 回滚方式

如果要回到旧的蒸馏服务：

### 11.1 停掉当前服务

```bash
sudo systemctl disable --now openclaw-executor
```

### 11.2 重新启用旧服务

```bash
sudo systemctl enable --now llama-qwen
```

### 11.3 验证

```bash
systemctl status llama-qwen --no-pager
curl -s http://34.123.73.240/v1/models -H 'Authorization: Bearer <gateway-api-key>'
```

旧服务恢复后，模型名应回到：

```text
jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Q4_K_M
```

---

## 12. 当前状态摘要

截至本文档生成时：

- 当前默认服务：`openclaw-executor.service`
- 当前默认模型：`openclaw/Qwen3.5-27B-UD-Q4_K_XL`
- 当前端口：`18343`
- 当前入口：`http://34.123.73.240/v1`
- 当前用途：`openclaw` 风格的 agentic coding executor

旧蒸馏服务仍保留在机器上，随时可回滚。
