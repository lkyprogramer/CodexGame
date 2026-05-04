# GCP Qwen OpenAI Gateway 运维手册

## 1. 文档目的

本文档用于完整说明截至 **2026-03-07**，部署在 GCP 跳板机上的 OpenAI 兼容转发网关的现状、配置、访问方式、运维命令、验收结果与故障排查方法。

目标读者假设为：

- 没参与过本次部署；
- 但需要接手运维、排障或继续扩展这套网关。

---

## 2. 系统概览

当前网关的职责很简单：

- 对外提供一个公网 HTTP OpenAI 兼容入口；
- 在 GCP 上做 Bearer token 鉴权；
- 将 `/v1/*` 请求透明转发到 4090 机器上的 `llama-server`；
- 不做请求改写、不做模型切换、不做响应包装。

当前链路：

```text
Client
  -> http://34.123.73.240/v1/*
  -> GCP nginx gateway
  -> http://100.107.189.100:18343/v1/*
  -> Qwen3.5-27B-UD-Q4_K_XL on RTX 4090
```

设计重点：

- 目标是“稳定转发”，不是“高并发网关”；
- 上游 4090 当前是单 slot 模型服务；
- 网关只负责入口、鉴权与长连接透传。

---

## 3. 当前部署状态

### 3.1 GCP 网关机器

- GCP 实例名：`instance-20260222-145427`
- Zone：`us-central1-a`
- Project：`project-d4e4f88c-f262-47af-b5b`
- 状态：`RUNNING`
- 公网 IP：`34.123.73.240`
- 内网 IP：`10.128.0.2`
- Service Account：`996591526083-compute@developer.gserviceaccount.com`
- Scope：`cloud-platform`
- 网络标签：
  - `http-server`
  - `https-server`

### 3.2 4090 上游服务

- 上游地址：`100.107.189.100:18343`
- 上游接口：`http://100.107.189.100:18343/v1`
- 模型别名：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 当前 serving 方式：
  - `thinking=true`
  - `--reasoning-format none`

这意味着：

- 模型仍然会进行 thinking；
- 但客户端不能依赖 `message.reasoning_content` 独立字段；
- thinking 内容会直接出现在 `message.content` 中。

### 3.3 当前对外入口

- 基地址：`http://34.123.73.240/v1`
- 健康检查：`http://34.123.73.240/healthz`

---

## 4. 当前文件与配置位置

### 4.1 Nginx 站点配置

- 主配置：
  - `/etc/nginx/sites-available/qwen-openai-gateway`
- 启用链接：
  - `/etc/nginx/sites-enabled/qwen-openai-gateway`
- 默认站点：
  - 已禁用 `/etc/nginx/sites-enabled/default`

### 4.2 鉴权配置

- Bearer token 校验片段：
  - `/etc/nginx/snippets/qwen-openai-gateway-auth.conf`

### 4.3 日志格式配置

- 日志格式：
  - `/etc/nginx/conf.d/qwen-openai-log-format.conf`

### 4.4 日志文件

- Access log：
  - `/var/log/nginx/qwen-openai-access.log`
- Error log：
  - `/var/log/nginx/qwen-openai-error.log`

---

## 5. 当前生效配置

### 5.1 站点配置

当前站点配置如下：

```nginx
upstream qwen_backend {
    server 100.107.189.100:18343;
    keepalive 16;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 64m;

    access_log /var/log/nginx/qwen-openai-access.log qwen_openai;
    error_log /var/log/nginx/qwen-openai-error.log warn;

    location = /healthz {
        access_log off;
        default_type text/plain;
        return 200 "ok\n";
    }

    location /v1/ {
        include /etc/nginx/snippets/qwen-openai-gateway-auth.conf;

        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_request_buffering off;
        chunked_transfer_encoding on;
        proxy_connect_timeout 5s;
        proxy_send_timeout 900s;
        proxy_read_timeout 900s;

        proxy_set_header Host $host;
        proxy_set_header Authorization "";
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://qwen_backend;
    }

    location / {
        return 404;
    }
}
```

### 5.2 鉴权片段

仓库文档中不写入 Bearer token 明文。当前配置逻辑如下：

```nginx
if ($http_authorization != "Bearer <REDACTED>") {
    add_header WWW-Authenticate 'Bearer realm="qwen-openai-gateway"' always;
    return 401;
}
```

### 5.3 日志格式

```nginx
log_format qwen_openai '$remote_addr - $remote_user [$time_local] '
                      '"$request" $status $body_bytes_sent '
                      'rt=$request_time urt=$upstream_response_time '
                      'ua="$http_user_agent"';
```

---

## 6. 对外接口定义

### 6.1 健康检查

无鉴权：

```http
GET /healthz
```

返回：

```text
ok
```

语义说明：

- 只表示 GCP 网关本身还活着；
- 不代表 4090 上游一定可用。

### 6.2 OpenAI 兼容接口

需要 Bearer token：

- `GET /v1/models`
- `POST /v1/chat/completions`
- 其他 `llama-server` 当前已提供的 `/v1/*`

行为约束：

- 透明转发；
- 不改请求体；
- 不改响应体；
- 支持普通 JSON；
- 支持 `stream=true`；
- 不做模型别名重写。

---

## 7. 鉴权与密钥管理

### 7.1 当前鉴权方式

当前采用单 Bearer token 方案：

```http
Authorization: Bearer <gateway-api-key>
```

### 7.2 为什么文档不写明文 token

原因很直接：

- token 是现网可用凭证；
- 将其明文写进仓库文档属于不必要的扩大暴露面；
- 运维文档应描述“如何获取、如何轮换”，而不是把 secret 固化到 repo。

### 7.3 查看当前 token

在 GCP 机上查看：

```bash
sudo cat /etc/nginx/snippets/qwen-openai-gateway-auth.conf
```

### 7.4 轮换 token

编辑鉴权片段：

```bash
sudo vi /etc/nginx/snippets/qwen-openai-gateway-auth.conf
```

将 Bearer token 改为新的值后执行：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

轮换后需要同步更新所有客户端的 `api_key`。

---

## 8. 客户端接入示例

### 8.1 Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://34.123.73.240/v1",
    api_key="YOUR_GATEWAY_API_KEY",
)

resp = client.chat.completions.create(
    model="unsloth/Qwen3.5-27B-UD-Q4_K_XL",
    messages=[{"role": "user", "content": "Write a Java null-safe config loader method."}],
    max_tokens=512,
)

print(resp.choices[0].message.content)
```

### 8.2 Curl

```bash
curl -H "Authorization: Bearer YOUR_GATEWAY_API_KEY" \
  http://34.123.73.240/v1/models
```

```bash
curl -H "Authorization: Bearer YOUR_GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  http://34.123.73.240/v1/chat/completions \
  -d '{
    "model": "unsloth/Qwen3.5-27B-UD-Q4_K_XL",
    "messages": [{"role": "user", "content": "Explain Optional vs null in Java."}],
    "max_tokens": 512
  }'
```

---

## 9. 常用运维命令

### 9.1 Nginx 状态与重载

```bash
sudo nginx -t
sudo systemctl status nginx
sudo systemctl reload nginx
sudo systemctl restart nginx
journalctl -u nginx
```

### 9.2 日志查看

```bash
sudo tail -f /var/log/nginx/qwen-openai-access.log
sudo tail -f /var/log/nginx/qwen-openai-error.log
```

### 9.3 监听端口检查

```bash
ss -ltnp | grep ':80 '
```

### 9.4 GCP 到 4090 上游连通性

```bash
curl http://100.107.189.100:18343/v1/models
```

如果要从 GCP 跳板机验证 4090 的服务状态：

```bash
sshpass -p hhtele ssh -o StrictHostKeyChecking=no hhtele@100.107.189.100 \
  "systemctl status llama-qwen --no-pager"
```

---

## 10. 当前验收结果

以下项目已经实测通过：

### 10.1 网关基础连通性

- `GET /healthz` 返回 `200`
- 未带 token 访问 `/v1/models` 返回 `401`
- 带 token 访问 `/v1/models` 返回 `200`

### 10.2 与上游一致性

实测对比过：

- 模型 ID 一致
- alias 一致
- `n_ctx_train` 一致

也就是说，网关没有篡改模型元信息。

### 10.3 非流式请求

OpenAI SDK 非流式 `chat.completions.create(...)` 已返回 `200`。

### 10.4 流式请求

`stream=true` 已验证正常逐段返回：

- SSE 没被 `nginx` 缓冲吞掉；
- 首个内容 chunk 实测约 `2270ms`。

### 10.5 长请求

已实测一条长 prompt 透传：

- `prompt_tokens = 81659`
- 总耗时约 `94.5s`
- 正常返回，没有被网关读超时截断

### 10.6 并发透传

已实测 3 个并发请求全部成功。

说明：

- 网关本身不崩；
- 也不主动拒绝；
- 实际延迟由 4090 单 slot 上游决定。

### 10.7 上游异常语义

临时停止 `llama-qwen` 后，网关访问 `/v1/models` 返回：

- `502 Bad Gateway`

恢复上游后，重新返回：

- `200`

这符合预期。

---

## 11. 故障排查手册

### 11.1 `/healthz` 不通

优先排查：

1. `nginx` 是否存活
2. 80 端口是否监听
3. GCP 防火墙是否仍允许 `tcp:80`

命令：

```bash
sudo systemctl status nginx
ss -ltnp | grep ':80 '
```

### 11.2 `/v1/models` 返回 `401`

说明鉴权失败，常见原因：

- 没带 `Authorization`
- Bearer token 错了
- token 轮换后客户端没更新

先核对：

```bash
sudo cat /etc/nginx/snippets/qwen-openai-gateway-auth.conf
```

### 11.3 `/v1/models` 返回 `502`

说明 GCP 网关活着，但上游 4090 不可达或上游服务没起来。

优先排查：

```bash
curl http://100.107.189.100:18343/v1/models
```

如果这里失败，再去 4090 上看：

```bash
sshpass -p hhtele ssh -o StrictHostKeyChecking=no hhtele@100.107.189.100 \
  "systemctl status llama-qwen --no-pager"
```

### 11.4 流式输出卡住

优先检查：

- `proxy_buffering off` 是否还在
- 上游是否本身卡住
- access log / error log 是否有超时信息

### 11.5 长请求中途断开

优先检查：

- `proxy_read_timeout`
- `proxy_send_timeout`
- 上游 `llama-qwen` 是否被重启
- 客户端自身 timeout 是否太小

当前网关值为：

- `proxy_connect_timeout 5s`
- `proxy_send_timeout 900s`
- `proxy_read_timeout 900s`

---

## 12. 当前限制与已知 trade-off

### 12.1 这是临时 HTTP 方案

当前对外是：

- 公网 IP
- 明文 HTTP
- Bearer token 明文传输

这意味着：

- 不适合长期暴露在不可信公网；
- 适合临时接入和内测；
- 正式使用应尽快切 HTTPS。

### 12.2 网关不做并发治理

当前策略是“直接透传”：

- 不排队；
- 不限流；
- 不做请求重试。

这意味着：

- 并发请求会直接堆到 4090 上游；
- 网关稳定，但整体延迟与吞吐完全由上游单 slot 决定。

### 12.3 上游 reasoning 字段 trade-off

4090 当前使用：

```bash
--chat-template-kwargs '{"enable_thinking": true}'
--reasoning-format none
```

这意味着：

- thinking 仍然存在；
- 但客户端不能依赖 `reasoning_content`；
- thinking 文本直接合并到 `message.content`。

这是为了绕过 `llama-server` 对 Qwen3.5 reasoning 输出的 parser 问题。

---

## 13. 后续升级到 HTTPS 的路径

正式升级建议如下：

1. 准备域名或子域名，例如：
   - `qwen-api.example.com`
2. 把 A 记录指向：
   - `34.123.73.240`
3. 在当前 `nginx` 站点上增加：
   - `server_name qwen-api.example.com;`
4. 安装 `certbot`
5. 执行：

```bash
sudo certbot --nginx -d qwen-api.example.com
```

6. 客户端把：

```text
http://34.123.73.240/v1
```

改为：

```text
https://qwen-api.example.com/v1
```

升级时不需要改：

- 上游地址；
- Bearer token 鉴权模型；
- `/v1/*` 路由；
- 客户端请求体格式。

---

## 14. 最小交接清单

如果需要把这套网关交给别人维护，最少需要交接这几项：

- GCP 项目与实例信息
- 公网 IP：`34.123.73.240`
- `nginx` 配置文件位置
- Bearer token 获取与轮换方法
- 上游 4090 地址：`100.107.189.100:18343`
- 4090 的 `llama-qwen` 服务检查命令
- 当前这是临时 HTTP 方案，不是正式 HTTPS 方案
- 当前上游 `reasoning_content` 不独立返回

以上信息足够让新的维护者完成：

- 健康检查
- 认证排障
- 上游排障
- token 轮换
- 配置重载
- HTTPS 升级

