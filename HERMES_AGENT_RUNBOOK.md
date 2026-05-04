# Hermes Agent 4090 安装与运维手册

## 1. 目标

本文档说明如何在 `100.107.189.100` 这台 4090 机器上使用本地安装的 Hermes Agent，并让它默认连接已经在线的 `openclaw-executor` 模型服务。

当前接入关系：

- Hermes CLI
  - 调用本机 OpenAI-compatible endpoint：`http://127.0.0.1:18343/v1`
- 模型服务
  - systemd 服务：`openclaw-executor.service`
  - 模型别名：`openclaw/Qwen3.5-27B-UD-Q4_K_XL`

本次范围固定为：

- CLI First
- 本机 terminal backend
- 不安装 Hermes gateway
- 不配置 Telegram / Discord / WhatsApp / Slack
- 不修改现有 `openclaw-executor` 服务参数

## 2. 部署位置

Hermes 在 4090 上的实际落点如下：

- 源码目录：[hermes-agent](/home/hhtele/hermes-agent)
- Python 虚拟环境：[.venv](/home/hhtele/hermes-agent/.venv)
- 配置目录：[.hermes](/home/hhtele/.hermes)
- 主配置文件：[config.yaml](/home/hhtele/.hermes/config.yaml)
- 环境变量文件：[.env](/home/hhtele/.hermes/.env)
- 命令入口：
  - `/home/hhtele/.local/bin/hermes`
  - `/home/hhtele/.local/bin/hermes-agent`

## 3. 当前配置

当前 Hermes 主配置：

文件：[config.yaml](/home/hhtele/.hermes/config.yaml)

```yaml
model: openclaw/Qwen3.5-27B-UD-Q4_K_XL
toolsets:
  - hermes-cli
terminal:
  backend: local
```

当前环境变量：

文件：[.env](/home/hhtele/.hermes/.env)

```env
OPENAI_API_KEY=sk-no-key-required
OPENAI_BASE_URL=http://127.0.0.1:18343/v1
TERMINAL_ENV=local
```

关键约束：

- `model` 使用字符串，而不是 dict
- 不显式设置 `model.provider=openrouter`
- 通过 `OPENAI_BASE_URL` 指向本机 `llama.cpp`

原因：

- Hermes 当前部分工具链对 dict 型 `model` 配置兼容不完整
- 如果显式走 `openrouter`，会偏离本地自建 endpoint

## 4. 安装方式

采用源码安装，而不是官方一键脚本。

核心步骤如下：

```bash
git clone https://github.com/NousResearch/hermes-agent.git ~/hermes-agent
cd ~/hermes-agent
git submodule update --init mini-swe-agent
python3 -m pip install --user --break-system-packages uv
~/.local/bin/uv venv .venv --python 3.11
~/.local/bin/uv pip install --python .venv/bin/python -e ".[cli,pty]"
~/.local/bin/uv pip install --python .venv/bin/python -e ./mini-swe-agent
```

补充依赖：

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip ripgrep
```

## 5. 本次额外补丁

为了让 Hermes 能稳定接 OpenAI-compatible `llama.cpp` 服务并使用 tool path，本次在 4090 本地 Hermes 源码上补了两个兼容性修复。

### 5.1 auxiliary model 配置兼容修复

文件：[auxiliary_client.py](/home/hhtele/hermes-agent/agent/auxiliary_client.py)

修复内容：

- 原逻辑默认假设 `auxiliary.model` 是字符串
- 当配置是 dict 或其他结构时，会触发 `.strip()` 崩溃
- 现已兼容：
  - string
  - dict
  - 其他对象降级为 `None`

### 5.2 tool call arguments 兼容修复

文件：[run_agent.py](/home/hhtele/hermes-agent/run_agent.py)

修复内容：

- 原逻辑默认假设 `tc.function.arguments` 是字符串
- 当 `llama.cpp` 返回 dict/list 结构时：
  - 调试日志切片崩溃
  - JSON 参数校验也会崩溃
- 现已兼容：
  - string
  - dict
  - list
  - 其他 JSON-serializable 对象

这两个补丁只影响 Hermes 自身的工具调用链，不影响现有 `openclaw-executor` 服务。

## 6. 验证结果

本次已经实际通过以下检查：

### 6.1 基础环境

```bash
hermes --version
hermes --help
hermes doctor
hermes status
```

结果：

- `hermes` 命令正常可用
- `hermes doctor` 可完整跑完
- `hermes status` 显示：
  - `Model: openclaw/Qwen3.5-27B-UD-Q4_K_XL`
  - `Provider: Custom endpoint`
  - `Backend: local`

### 6.2 模型连通性

```bash
curl http://127.0.0.1:18343/v1/models
hermes chat -q "Reply READY only" -Q
```

结果：

- 本机模型列表正常返回
- Hermes 已成功通过本机 endpoint 返回 `READY`

### 6.3 terminal backend

实际验证命令：

```bash
hermes chat -q "Use the terminal tool to run pwd in the current directory. Return exactly one line in the form PWD: <absolute-path>. Do not do anything else and do not modify files." -Q --yolo
```

实际成功返回：

```text
PWD: /home/hhtele/hermes-agent
```

这说明：

- Hermes 不只是纯聊天
- 它已经可以通过本地 terminal backend 调用真实 shell

### 6.4 现有服务未受影响

检查项：

```bash
systemctl is-active openclaw-executor.service
curl http://127.0.0.1:18343/v1/models
```

以及 GCP 网关检查：

```bash
curl http://34.123.73.240/v1/models \
  -H 'Authorization: Bearer <gateway-token>'
```

结果：

- `openclaw-executor.service` 仍然 `active`
- 本机 `18343` 正常
- GCP 网关仍然正常

## 7. 常用命令

### 7.1 进入环境

```bash
export PATH=$HOME/.local/bin:$PATH
cd ~/hermes-agent
```

### 7.2 基础检查

```bash
hermes status
hermes doctor
```

### 7.3 最小聊天

```bash
hermes chat -q "Reply READY only" -Q
```

### 7.4 只读 terminal 测试

```bash
hermes chat -q "Use the terminal tool to run pwd in the current directory. Return exactly one line in the form PWD: <absolute-path>. Do not do anything else and do not modify files." -Q --yolo
```

### 7.5 查看当前模型服务

```bash
curl -s http://127.0.0.1:18343/v1/models
```

## 8. 常见问题

### 8.1 `Provider` 显示成 OpenRouter

原因：

- 配置误设了 `model.provider=openrouter`
- 或者没有设置 `OPENAI_BASE_URL`

修复：

- 保持 [config.yaml](/home/hhtele/.hermes/config.yaml) 中 `model` 为字符串
- 在 [.env](/home/hhtele/.hermes/.env) 中设置：

```env
OPENAI_BASE_URL=http://127.0.0.1:18343/v1
OPENAI_API_KEY=sk-no-key-required
```

### 8.2 `'dict' object has no attribute 'strip'`

原因：

- Hermes 上游当前某些路径默认把模型配置或 tool arguments 当成字符串

当前机器已修复的两处：

- [auxiliary_client.py](/home/hhtele/hermes-agent/agent/auxiliary_client.py)
- [run_agent.py](/home/hhtele/hermes-agent/run_agent.py)

如果后续升级 Hermes 源码，可能需要重新核对这两个补丁是否仍在。

### 8.3 `unhashable type: 'slice'`

原因：

- tool call arguments 返回 dict/list 时，旧逻辑直接切片

当前机器已在 [run_agent.py](/home/hhtele/hermes-agent/run_agent.py) 修复。

### 8.4 `hermes doctor` 仍有可选告警

这不是当前目标失败。

本次目标只要求：

- CLI 可用
- 本机模型可用
- terminal backend 可用

以下告警目前可忽略：

- 没登录 Nous Portal
- 没登录 OpenAI Codex
- 没配 messaging / web / image_gen / honcho
- 没有 `SOUL.md`

## 9. 升级建议

如果后续要升级 Hermes：

1. 先备份：

```bash
cp ~/hermes-agent/agent/auxiliary_client.py ~/hermes-agent/agent/auxiliary_client.py.pre-upgrade
cp ~/hermes-agent/run_agent.py ~/hermes-agent/run_agent.py.pre-upgrade
```

2. 更新源码后重新验证：

```bash
hermes doctor
hermes status
hermes chat -q "Reply READY only" -Q
hermes chat -q "Use the terminal tool to run pwd in the current directory. Return exactly one line in the form PWD: <absolute-path>. Do not do anything else and do not modify files." -Q --yolo
```

3. 如果工具链又出现上面的兼容问题，再重新合并本次两处补丁。

## 10. 回滚

本次没有动现有模型服务，所以 Hermes 回滚非常直接。

删除 Hermes：

```bash
rm -rf /home/hhtele/hermes-agent
rm -rf /home/hhtele/.hermes
rm -f /home/hhtele/.local/bin/hermes
rm -f /home/hhtele/.local/bin/hermes-agent
```

这不会影响：

- `openclaw-executor.service`
- `http://127.0.0.1:18343/v1`
- GCP 网关 `http://34.123.73.240/v1`

