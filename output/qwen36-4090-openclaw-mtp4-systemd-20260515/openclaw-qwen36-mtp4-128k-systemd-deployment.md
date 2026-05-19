# OpenClaw Qwen3.6 MTP4 128K Systemd 部署文档

部署日期：2026-05-15  
目标机器：RTX 4090，`192.168.10.29`  
服务目标：用 `Qwen3.6-27B-MTP-Q4XL` 128k 单并发 prompt-cache 配置替换 4090 上原有 `qwen35-35b-a3b-uncensored.service`。  

## 1. 当前结论

已完成部署并切换成功。

当前启用服务：

```text
openclaw-qwen36-mtp4-128k.service: active, enabled
```

旧服务状态：

```text
qwen35-35b-a3b-uncensored.service: disabled
```

对外 OpenAI-compatible 入口：

```text
http://192.168.10.29:28343/v1
Authorization: Bearer <configured-token>
```

本机后端直连：

```text
http://127.0.0.1:18343/v1
```

当前模型 alias：

```text
openclaw/Qwen3.6-27B-MTP-Q4XL
```

## 2. 部署文件

启动脚本：

```text
/opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh
```

systemd unit：

```text
/etc/systemd/system/openclaw-qwen36-mtp4-128k.service
```

日志：

```text
/var/log/llama/openclaw-qwen36-mtp4-128k.log
/var/log/llama/openclaw-qwen36-mtp4-128k.err.log
```

NGINX 鉴权反代配置保持不变：

```text
/etc/nginx/conf.d/openclaw-28343.conf
```

## 3. 启动配置

当前启动脚本内容等价于：

```bash
/home/hhtele/llama.cpp-mtp-unsloth-20260513/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-reuse 256 \
  --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --host 0.0.0.0 \
  --port 18343
```

关键配置说明：

| 参数 | 说明 |
| --- | --- |
| `-c 131072` | 128k context |
| `-np 1` | 单并发 / 单 slot |
| `--spec-type mtp` | 启用 MTP speculative decoding |
| `--spec-draft-n-max 4` | MTP=4 |
| `-rea off` | 关闭 reasoning 输出 |
| `--cache-prompt` | 启用 prompt cache |
| `--cache-reuse 256` | 允许复用长 prompt 前缀 |
| `--cache-ram 2048` | prompt cache 主存上限 2GB，避免 8GB 配置过激 |
| `--slot-prompt-similarity 0.10` | slot prompt 相似度阈值 |
| `--host 0.0.0.0 --port 18343` | 后端监听端口，供 NGINX 28343 反代 |

不要添加：

```bash
--reasoning-format none
```

之前测试显示该参数会破坏 Qwen3.6 MTP 的 thinking 标签处理路径。

## 4. Systemd 管理命令

查看状态：

```bash
sudo systemctl status openclaw-qwen36-mtp4-128k.service --no-pager -l
```

启动：

```bash
sudo systemctl start openclaw-qwen36-mtp4-128k.service
```

停止：

```bash
sudo systemctl stop openclaw-qwen36-mtp4-128k.service
```

重启：

```bash
sudo systemctl restart openclaw-qwen36-mtp4-128k.service
```

开机自启：

```bash
sudo systemctl enable openclaw-qwen36-mtp4-128k.service
```

取消自启：

```bash
sudo systemctl disable openclaw-qwen36-mtp4-128k.service
```

查看日志：

```bash
sudo journalctl -u openclaw-qwen36-mtp4-128k.service -n 200 --no-pager
tail -f /var/log/llama/openclaw-qwen36-mtp4-128k.log
tail -f /var/log/llama/openclaw-qwen36-mtp4-128k.err.log
```

## 5. 验证结果

### 5.1 后端直连

命令：

```bash
curl http://127.0.0.1:18343/v1/models
```

结果：HTTP 200，返回：

```text
openclaw/Qwen3.6-27B-MTP-Q4XL
```

### 5.2 NGINX 鉴权入口

无 token：

```text
http://192.168.10.29:28343/v1/models
```

结果：

```text
HTTP 401
```

带正确 token：

```text
http://192.168.10.29:28343/v1/models
```

结果：

```text
HTTP 200
openclaw/Qwen3.6-27B-MTP-Q4XL
```

Chat completion：

```text
POST http://192.168.10.29:28343/v1/chat/completions
```

测试 prompt：

```text
Reply with OK only.
```

结果：

```text
HTTP 200
assistant: OK
```

### 5.3 端口与显存

端口：

```text
0.0.0.0:18343 llama-server
0.0.0.0:28343 nginx
```

部署后显存：

```text
used: 21866 MiB
free: 2351 MiB
```

## 6. OpenClaw 使用方式

推荐 OpenClaw 只使用 NGINX 鉴权入口：

```text
base_url = http://192.168.10.29:28343/v1
model = openclaw/Qwen3.6-27B-MTP-Q4XL
Authorization = Bearer <configured-token>
```

示例：

```bash
curl --noproxy '*' \
  -H 'Authorization: Bearer <configured-token>' \
  -H 'Content-Type: application/json' \
  http://192.168.10.29:28343/v1/chat/completions \
  -d '{
    "model": "openclaw/Qwen3.6-27B-MTP-Q4XL",
    "messages": [
      {"role": "user", "content": "Reply with OK only."}
    ],
    "max_tokens": 8,
    "temperature": 0
  }'
```

## 7. 运行边界

已验证的长上下文结论：

```text
128k 可用：
prompt_tokens: 130406
cold latency: 105.84s
warm latency with prompt cache: 1.23s
cache_n: 130402 / 130406
```

当前不建议启用 256k：

```text
-c 262144 -np 1 在 4090 上会在长 prompt processing 中 CUDA OOM abort
```

建议 OpenClaw 输入预算：

```text
常规上限：<= 120k tokens
硬边界：131072 tokens
超过边界：llama-server 返回 HTTP 400 exceed_context_size_error
```

## 8. 回滚方案

回滚到旧 Qwen3.5 35B 服务：

```bash
sudo systemctl stop openclaw-qwen36-mtp4-128k.service
sudo systemctl disable openclaw-qwen36-mtp4-128k.service
sudo systemctl enable --now qwen35-35b-a3b-uncensored.service
```

验证：

```bash
curl http://127.0.0.1:18343/v1/models
```

如需删除新服务：

```bash
sudo rm /etc/systemd/system/openclaw-qwen36-mtp4-128k.service
sudo rm /opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh
sudo systemctl daemon-reload
```

NGINX `28343` 鉴权入口可以保留不动，因为它只代理到本机 `18343`。

