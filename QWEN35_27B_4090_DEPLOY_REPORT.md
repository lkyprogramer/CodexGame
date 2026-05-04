# Qwen3.5-27B-UD-Q4_K_XL 在 4090 机器上的最终部署汇报

## 1. 文档目的

本文档用于完整说明截至 **2026-03-07**，`Qwen3.5-27B-UD-Q4_K_XL` 模型在 4090 机器上的最终部署状态、访问方式、配置文件位置、服务脚本、运维命令、接口调用方式、已验证结果与注意事项。

目标读者假设为：

- 没参与过本次部署
- 但需要接手运维或继续使用这套服务

---

## 2. 部署结论

当前已经完成：

- 使用官方最新 `llama.cpp` HEAD 构建 CUDA 版 `llama-server`
- 成功加载 `Unsloth Qwen3.5-27B UD-Q4_K_XL` GGUF 模型
- 已配置为 `systemd` 常驻服务
- 服务已监听在 **`18343`**
- 已验证 OpenAI 兼容接口可用
- 已验证 `thinking mode` 可用，并能返回 `reasoning_content`

当前最终运行策略：

- 模型：`Qwen3.5-27B-UD-Q4_K_XL.gguf`
- 推理引擎：`llama-server`
- GPU：`1 x RTX 4090 24GB`
- 上下文：`262144`
- Thinking：默认开启
- 服务端口：`18343`
- 主要用途：**Precise coding tasks**

---

## 3. 机器与访问链路

### 3.1 GCP 跳板机

- 实例名：`instance-20260222-145427`
- 区域：`us-central1-a`
- Project：`project-d4e4f88c-f262-47af-b5b`
- 登录方式：

```bash
gcloud compute ssh \
  --zone "us-central1-a" \
  "instance-20260222-145427" \
  --project "project-d4e4f88c-f262-47af-b5b" \
  --tunnel-through-iap
```

说明：

- 该跳板机通过 IAP 访问，推荐始终用实例名访问
- 外网 IP 不应作为长期稳定入口依赖

### 3.2 4090 目标机

- 主机地址：`100.107.189.100`
- 登录用户：`hhtele`
- 登录密码：`hhtele`
- 主机名：`debian`
- 系统：`Debian 12`
- GPU：`NVIDIA GeForce RTX 4090`

从跳板机进入 4090 的方式：

```bash
sshpass -p hhtele ssh -o StrictHostKeyChecking=no hhtele@100.107.189.100
```

---

## 4. 部署资源概览

### 4.1 llama.cpp

- 代码目录：`/opt/llama.cpp`
- 当前源码 commit：

```text
c5a778891ba0ddbd4cbb507c823f970595b1adc2
```

- 二进制路径：

```text
/opt/llama.cpp/build/bin/llama-server
/opt/llama.cpp/build/bin/llama-cli
/opt/llama.cpp/build/bin/llama-mtmd-cli
/opt/llama.cpp/build/bin/llama-gguf-split
```

### 4.2 模型

- 模型来源：Unsloth `Qwen3.5-27B-GGUF`
- 量化版本：`UD-Q4_K_XL`
- 本地模型路径：

```text
/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf
```

- 模型文件大小：

```text
17621125024 bytes
```

- 模型 SHA256：

```text
13cb6228344898afa50d963c02ae0d991ae25094eea8837db8d0e452e91c5888
```

### 4.3 日志

- 标准输出日志：

```text
/var/log/llama/qwen-server.log
```

- 标准错误日志：

```text
/var/log/llama/qwen-server.err.log
```

---

## 5. 最终配置文件

### 5.1 启动脚本

路径：

[`/opt/llama.cpp/run-qwen.sh`](/opt/llama.cpp/run-qwen.sh)

当前内容：

```bash
#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
exec /opt/llama.cpp/build/bin/llama-server \
  -m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --alias unsloth/Qwen3.5-27B-UD-Q4_K_XL \
  -ngl 99 \
  -c 262144 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --temp 0.6 \
  --top-p 0.95 \
  --top-k 20 \
  --min-p 0.0 \
  --chat-template-kwargs '{"enable_thinking": true}' \
  --host 0.0.0.0 \
  --port 18343
```

### 5.2 systemd 服务文件

路径：

[`/etc/systemd/system/llama-qwen.service`](/etc/systemd/system/llama-qwen.service)

当前内容：

```ini
[Unit]
Description=llama.cpp Qwen3.5 27B server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hhtele
WorkingDirectory=/opt/llama.cpp
ExecStart=/opt/llama.cpp/run-qwen.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/qwen-server.log
StandardError=append:/var/log/llama/qwen-server.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

---

## 6. 最终推荐参数与作用说明

本次最终配置综合了两类来源：

- Unsloth 对 Qwen3.5 的最佳实践
- 你提供的单卡 3090 / 24GB 长上下文配置经验

### 6.1 核心配置

```bash
-ngl 99
-c 262144
-np 1
-fa on
-ctk q4_0
-ctv q4_0
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--chat-template-kwargs '{"enable_thinking": true}'
--port 18343
```

### 6.2 每个参数的实际作用

- `-m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf`
  - 指定模型文件路径。
  - 当前服务使用的是本地 GGUF 文件，不依赖运行时从 Hugging Face 或 ModelScope 动态拉取。

- `--alias unsloth/Qwen3.5-27B-UD-Q4_K_XL`
  - 给 API 暴露一个稳定模型名。
  - 客户端不需要直接使用本地文件名。

- `-ngl 99`
  - 尽可能把模型层全部卸载到 GPU。
  - 对 4090 单卡部署，这是默认推荐值。

- `-c 262144`
  - 把上下文窗口设置到模型原生最大值 `262K`。
  - 当前这台 4090 机器已实测可以正常拉起。

- `-np 1`
  - `llama-server` 的并行 slot 数设为 1。
  - 这对“单用户、高精度编码任务”更合理。
  - 比默认自动 slot 更节省显存与上下文相关资源，也减少多 slot 带来的噪音与抢占。

- `-fa on`
  - 强制启用 Flash Attention。
  - 在长上下文下非常重要，直接影响吞吐、显存与延迟。

- `-ctk q4_0`
  - 将 KV cache 的 K 量化为 `q4_0`。
  - 长上下文下显著减少 KV 占用。

- `-ctv q4_0`
  - 将 KV cache 的 V 量化为 `q4_0`。
  - 和 `-ctk q4_0` 配套，单卡 24GB 跑 `262K` 的关键参数之一。

- `--temp 0.6`
  - 降低采样随机性。
  - 对 precise coding tasks 更稳，减少“答非所问”或风格漂移。

- `--top-p 0.95`
  - 保留累计概率较高的候选 token。
  - 平衡稳定性与表达能力。

- `--top-k 20`
  - 限制每步采样的候选集合规模。
  - 对代码类任务有利于减少低质量 token。

- `--min-p 0.0`
  - 关闭额外 min-p 裁剪。
  - 避免对某些低概率但必要的代码 token 过早裁切。

- `--chat-template-kwargs '{"enable_thinking": true}'`
  - 显式开启 Qwen3.5 的 thinking / reasoning 模式。
  - 当前服务已验证返回 `reasoning_content`。

- `--host 0.0.0.0`
  - 允许在本机回环地址之外访问。
  - 便于内网、跳板转发、代理等后续接入。

- `--port 18343`
  - 当前服务对外监听端口。

---

## 7. 为什么最终采用这套配置

### 7.1 与你给的 3090 配置保持一致的部分

以下核心结论被保留：

- `27B dense` 在单卡高质量推理中更适合深度编码任务
- `262K native context` 值得作为主线配置
- `-ngl 99`
- `-fa on`
- `cache-type-k/v = q4_0`

这些点在 4090 24GB 上同样成立。

### 7.2 结合 Unsloth 的补充

Unsloth 对 Qwen3.5 的关键补充是：

- `thinking mode` 需要通过 `--chat-template-kwargs` 显式控制
- 对这类模型，OpenAI 兼容接口是可行路径

### 7.3 我做的本机化调整

最终额外加上的两点是：

- `-np 1`
  - 适配单用户 coding 场景

- 一组偏稳定的采样参数
  - `--temp 0.6`
  - `--top-p 0.95`
  - `--top-k 20`
  - `--min-p 0.0`

原因是：

- 你的主用途不是创意写作
- 而是 **Precise coding tasks**

---

## 8. 当前实际验证结果

### 8.1 服务状态

已验证：

- `systemctl is-enabled llama-qwen` 返回 `enabled`
- `systemctl is-active llama-qwen` 返回 `active`
- 端口 `18343` 已监听

### 8.2 模型加载

已验证：

- `llama-server` 成功加载本地模型
- `n_ctx = 262144`
- `flash_attn = enabled`
- `thinking = 1`

### 8.3 OpenAI 兼容接口

已验证：

- `GET /v1/models` 正常
- `POST /v1/chat/completions` 正常
- 返回中包含：
  - `message.content`
  - `message.reasoning_content`

### 8.4 实测性能片段

在简单请求上实测看到的生成速度大约在：

- `~42 tokens/s`

这与单卡 24GB、Q4 量化、Flash Attention 开启的预期一致。

---

## 9. OpenAI 兼容调用方式

### 9.1 基础地址

在 4090 机器本机上使用：

```text
http://127.0.0.1:18343/v1
```

如果从能直达该机器的内网地址使用：

```text
http://100.107.189.100:18343/v1
```

### 9.2 Python 示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:18343/v1",
    api_key="sk-no-key-required",
)

rsp = client.chat.completions.create(
    model="unsloth/Qwen3.5-27B-UD-Q4_K_XL",
    messages=[{"role": "user", "content": "Create a Snake game."}],
    max_tokens=1024,
)

print(rsp.choices[0].message.content)
print(rsp.choices[0].message.reasoning_content)
```

### 9.3 curl 示例

```bash
curl http://127.0.0.1:18343/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "unsloth/Qwen3.5-27B-UD-Q4_K_XL",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ],
    "max_tokens": 256
  }'
```

---

## 10. 运维命令

### 10.1 查看状态

```bash
systemctl status llama-qwen
```

### 10.2 启动服务

```bash
sudo systemctl start llama-qwen
```

### 10.3 停止服务

```bash
sudo systemctl stop llama-qwen
```

### 10.4 重启服务

```bash
sudo systemctl restart llama-qwen
```

### 10.5 查看实时日志

```bash
journalctl -u llama-qwen -f
```

或：

```bash
tail -f /var/log/llama/qwen-server.log
tail -f /var/log/llama/qwen-server.err.log
```

### 10.6 查看监听端口

```bash
ss -ltnp | grep 18343
```

---

## 11. 关键文件清单

- 启动脚本：
  - [`/opt/llama.cpp/run-qwen.sh`](/opt/llama.cpp/run-qwen.sh)

- systemd 单元：
  - [`/etc/systemd/system/llama-qwen.service`](/etc/systemd/system/llama-qwen.service)

- llama.cpp 代码目录：
  - [`/opt/llama.cpp`](/opt/llama.cpp)

- 服务二进制：
  - [`/opt/llama.cpp/build/bin/llama-server`](/opt/llama.cpp/build/bin/llama-server)

- 模型文件：
  - [`/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf`](/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf)

- 输出日志：
  - [`/var/log/llama/qwen-server.log`](/var/log/llama/qwen-server.log)

- 错误日志：
  - [`/var/log/llama/qwen-server.err.log`](/var/log/llama/qwen-server.err.log)

---

## 12. 部署过程中涉及的外部来源

- 官方源码：
  - [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)

- Unsloth 文档：
  - [Qwen3.5 docs](https://unsloth.ai/docs/models/qwen3.5#qwen3.5-27b)

- ModelScope 仓库：
  - [wuniansky/Qwen3.5-27B-UD-Q4_K_XL](https://modelscope.cn/models/wuniansky/Qwen3.5-27B-UD-Q4_K_XL)

---

## 13. 当前已知注意事项

### 13.1 thinking mode 下不要把 `max_tokens` 设得过小

已实测：

- `max_tokens = 8` 时，`/v1/chat/completions` 可能返回 `500`
- 不带 `max_tokens` 时正常
- `max_tokens = 256` 时正常

这说明：

- thinking 模式下，模型先输出思考链，再输出答案
- 如果给的生成上限太小，当前 `llama-server` 的结果整理过程可能失败

建议：

- coding 任务默认至少给 `256`
- 更常用的是 `512`、`1024` 或更高

### 13.2 当前配置优先单用户精确编码，不追求多并发

因为当前设置了：

- `-np 1`

所以：

- 更适合单用户长对话 / 精确编码
- 不适合当成多用户并发推理网关使用

### 13.3 262K 虽然已验证可起，但请求越大，延迟越高

这不是故障，而是长上下文的正常特性。

---

## 14. 如果要改配置，应该改哪里

优先修改这里：

- [`/opt/llama.cpp/run-qwen.sh`](/opt/llama.cpp/run-qwen.sh)

修改后执行：

```bash
sudo systemctl restart llama-qwen
```

不要直接改二进制路径，不要在 `systemd` 里硬塞复杂 JSON 参数。  
复杂参数优先放在启动脚本里维护。

---

## 15. 一句话总结

截至 **2026-03-07**，`Qwen3.5-27B-UD-Q4_K_XL` 已经在 `100.107.189.100` 这台 4090 机器上，以 **最新 `llama.cpp` HEAD + 262K 上下文 + thinking mode + OpenAI 兼容接口 + systemd 常驻服务** 的形式稳定运行，服务地址为：

```text
http://127.0.0.1:18343/v1
```

