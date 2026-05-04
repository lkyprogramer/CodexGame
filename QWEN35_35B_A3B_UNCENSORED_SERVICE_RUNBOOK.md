# Qwen3.5-35B-A3B Uncensored 服务运维手册

## 1. 当前结论

当前 4090 默认公网服务已经切换为：

- 模型：`Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M`
- 对外别名：`hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`
- 服务名：`qwen35-35b-a3b-uncensored.service`
- 监听地址：`0.0.0.0:18343`
- 公网入口：`http://34.123.73.240/v1`

这套服务的定位是：

- 通用聊天
- 创作 / 角色 / 风格化写作
- 更开放、少约束的回答风格

它**不是** `openclaw` executor，也不再适合作为旧的 Hermes / openclaw 默认上游。

## 2. 实际生效配置

### 2.1 模型文件

- [`/data/models/qwen/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`](/data/models/qwen/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf)

### 2.2 启动脚本

- [`/opt/llama.cpp/run-qwen35-35b-a3b-uncensored.sh`](/opt/llama.cpp/run-qwen35-35b-a3b-uncensored.sh)

当前内容：

```bash
#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
exec /opt/llama.cpp/build/bin/llama-server \
  -m /data/models/qwen/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf \
  --alias hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --temp 0.8 \
  --top-p 0.95 \
  --top-k 40 \
  --min-p 0.0 \
  --chat-template-kwargs '{"enable_thinking": false}' \
  --host 0.0.0.0 \
  --port 18343
```

### 2.3 systemd 服务

- [`/etc/systemd/system/qwen35-35b-a3b-uncensored.service`](/etc/systemd/system/qwen35-35b-a3b-uncensored.service)

当前内容：

```ini
[Unit]
Description=Qwen3.5 35B A3B Uncensored HauhauCS Aggressive on llama.cpp
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hhtele
WorkingDirectory=/opt/llama.cpp
ExecStart=/opt/llama.cpp/run-qwen35-35b-a3b-uncensored.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/qwen35-35b-a3b-uncensored.log
StandardError=append:/var/log/llama/qwen35-35b-a3b-uncensored.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

### 2.4 日志

- 标准输出：[`/var/log/llama/qwen35-35b-a3b-uncensored.log`](/var/log/llama/qwen35-35b-a3b-uncensored.log)
- 标准错误：[`/var/log/llama/qwen35-35b-a3b-uncensored.err.log`](/var/log/llama/qwen35-35b-a3b-uncensored.err.log)

## 3. 为什么最终是 `thinking=false`

原方案最初是：

- `128K`
- `thinking=true`

但实测发现这个模型在当前 `llama.cpp` 路径下，`thinking=true` 时会稳定出现一个对外可用性问题：

- 请求本身 `200`
- `reasoning_content` 很长
- 但 `message.content` 持续为空

这个问题在：

- 普通短聊天
- 流式输出
- `max_tokens=2048`

下都能复现，所以我最终把配置收敛为：

- 保留 `128K`
- 保留当前采样参数
- 关闭 `thinking`

这样做后的实测结果是：

- 非流式回答恢复正常正文输出
- 流式输出恢复正文 chunk
- `90032` prompt token 的长上下文请求可正常完成
- 没有出现 `500`、OOM 或重复重启

## 4. 对外访问

### 4.1 GCP 网关

- 基地址：`http://34.123.73.240/v1`
- 健康检查：`http://34.123.73.240/healthz`

Bearer token 沿用现有 GCP 网关配置，不在仓库文档中写明。

### 4.2 本机 / 内网

- 本机：`http://127.0.0.1:18343/v1`
- 4090 内网：`http://100.107.189.100:18343/v1`

### 4.3 当前模型名

调用时必须显式使用：

```text
hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M
```

旧的：

```text
openclaw/Qwen3.5-27B-UD-Q4_K_XL
```

已经不是当前默认服务。

## 5. 请求示例

### 5.1 Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://34.123.73.240/v1",
    api_key="<gateway-api-key>",
)

resp = client.chat.completions.create(
    model="hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M",
    messages=[
        {"role": "user", "content": "Write exactly one vivid sentence about a stormy cyberpunk alley."}
    ],
    max_tokens=256,
)

print(resp.choices[0].message.content)
```

### 5.2 curl

```bash
curl -s http://34.123.73.240/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <gateway-api-key>' \
  -d '{
    "model": "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M",
    "messages": [
      {"role": "user", "content": "Write exactly one vivid sentence about a stormy cyberpunk alley."}
    ],
    "max_tokens": 256,
    "stream": false
  }'
```

## 6. 运维命令

```bash
systemctl status qwen35-35b-a3b-uncensored --no-pager
journalctl -u qwen35-35b-a3b-uncensored -f
sudo systemctl restart qwen35-35b-a3b-uncensored
sudo systemctl stop qwen35-35b-a3b-uncensored
tail -n 200 /var/log/llama/qwen35-35b-a3b-uncensored.err.log
curl -s http://127.0.0.1:18343/v1/models
```

GPU 观察：

```bash
nvidia-smi
watch -n 1 nvidia-smi
```

## 7. 验收结果

当前已经实际验证通过：

- `GET /v1/models` 本机正常
- `GET /v1/models` 经公网网关正常
- 非流式聊天正常返回正文
- 流式输出正常返回正文 chunk
- 长上下文成功打进约 `90032` prompt tokens
- 无 `500`
- 无 OOM
- 无 systemd 重启抖动

## 8. 当前限制

这套服务的主要限制有三点：

1. 它不是 executor profile  
   不适合继续作为 `openclaw` / `Hermes` 默认后端。

2. `thinking=true` 当前不可用  
   不是服务崩，而是正文长期为空，已经被实际关闭。

3. `128K` 是当前生产默认，不是极限长上下文服务  
   如果后续要冲 `262K`，应单独做压测，不应直接在线上改。

## 9. 回滚

如果需要回滚到旧的 executor：

```bash
sudo systemctl disable --now qwen35-35b-a3b-uncensored
sudo systemctl enable --now openclaw-executor
```

回滚后应立即验证：

```bash
curl -s http://127.0.0.1:18343/v1/models
curl -s http://34.123.73.240/v1/models -H 'Authorization: Bearer <gateway-api-key>'
```

预期恢复为：

```text
openclaw/Qwen3.5-27B-UD-Q4_K_XL
```
