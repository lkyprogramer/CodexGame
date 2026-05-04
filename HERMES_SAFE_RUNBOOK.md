# hermes-safe 运维手册

## 1. 目标

`hermes-safe` 是当前 4090 上 Hermes CLI 的一层稳定适配层。

它的目标不是替换 Hermes，而是收口这些现网真实问题：

- Hermes 已经生成答案，但 CLI 非 0 退出
- `stdout` 被 spinner / tool trace 污染
- JSON-only 输出被 ```json fence 或解释性前缀包裹
- 真实仓库分析需要只读护栏
- 沙箱写入需要统一 workspace、验证和审计目录

当前推荐使用顺序：

- 日常调用：`hermes-safe`
- 排查 Hermes 原始行为：`hermes`

## 2. 现网落点

4090 上的实际文件：

- launcher：[hermes-safe](/home/hhtele/.local/bin/hermes-safe)
- wrapper 主脚本：[hermes_safe_wrapper.py](/home/hhtele/hermes-safe/hermes_safe_wrapper.py)
- 共享库：[hermes_guardrail_lib.py](/home/hhtele/hermes-safe/hermes_guardrail_lib.py)
- 配置目录：[.hermes-safe](/home/hhtele/.hermes-safe)
- 配置文件：[config.json](/home/hhtele/.hermes-safe/config.json)
- 运行目录：[runs](/home/hhtele/.hermes-safe/runs)
- 最近一次执行软链：[latest](/home/hhtele/.hermes-safe/latest)

当前 `config.json`：

```json
{
  "hermes_cmd": "hermes",
  "session_root": "~/.hermes/sessions",
  "run_root": "~/.hermes-safe/runs",
  "max_retries": 1,
  "default_timeout_seconds": 300
}
```

## 3. 工作模式

`hermes-safe` 当前只有一个子命令：

```bash
hermes-safe run
```

支持 4 种模式：

- `text`
  - 普通问答、分析、代码建议
  - 成功标准：能恢复非空最终答案
- `json`
  - 给脚本或上层 agent 消费
  - 成功标准：最终输出能解析为合法 JSON
- `readonly`
  - 真实仓库只读分析
  - 执行前后做 `git status --porcelain`
  - 如发现真实变更，直接失败
- `sandbox`
  - 小型 agentic coding
  - 在独立 workspace 内修改文件
  - 以验证命令是否通过为最终标准

## 4. 结果恢复逻辑

`hermes-safe` 不直接盲信 `stdout`。

最终答案优先级固定为：

1. `session.json` 中最后一个 assistant 消息
2. 清洗后的 `stdout`
3. 清洗后的 `stderr`

JSON 模式额外做两层恢复：

- 去掉 fenced JSON
- 抽取外层 JSON tail

也就是说，下面这种情况会被判为成功：

- Hermes CLI 非 0 退出
- 但 `session.json` 中已经有合法最终答案

这类成功会记成：

- `soft_success = true`

## 5. 运行目录结构

每次执行都会写到：

```text
~/.hermes-safe/runs/<run_id>/
```

至少包含：

- `request.json`
- `stdout.txt`
- `stderr.txt`
- `session.json`（如果成功定位到 session）
- `result.json`
- `workspace/`（仅 sandbox）
- `attempts/attempt-1/...`
- `attempts/attempt-2/...`（仅发生重试时）

`result.json` 的关键字段：

```json
{
  "run_id": "...",
  "mode": "json",
  "cwd": "...",
  "query_digest": "...",
  "session_id": "...",
  "soft_success": false,
  "exit_code": 0,
  "elapsed_ms": 12063.221,
  "tool_used": true,
  "contract_success": true,
  "json_parse_success": true,
  "validation_success": true,
  "failure_reason": null,
  "final_output": "...",
  "stdout_file": "...",
  "stderr_file": "...",
  "session_file": "...",
  "output_source": "session",
  "session_source": "stdout",
  "readonly_delta": [],
  "changed_files": ["app.py"],
  "validation_results": [],
  "attempt_count": 1,
  "success": true
}
```

这份结构就是后续上层 orchestrator 应该消费的稳定结果，不要再直接解析原始 `stdout`。

## 6. 实际验证结果

本次已经在 4090 上实际通过这些检查：

### 6.1 `text`

```bash
hermes-safe run --mode text --query "Reply READY only."
```

实际成功返回：

```text
READY
```

### 6.2 `json`

```bash
hermes-safe run --mode json --query 'Return strict JSON only. {"status":"ready","endpoint":"local"}'
```

实际成功返回：

```json
{"status":"ready","endpoint":"local"}
```

### 6.3 `readonly`

```bash
hermes-safe run \
  --mode readonly \
  --cwd /home/hhtele/hermes-bench-stage-run/hermes-bench-stage/repo \
  --query "Identify the runtime authority and main runtime entrypoint in this repository. Return exactly two lines: AUTHORITY: <path> and ENTRYPOINT: <path>."
```

实际成功返回：

```text
AUTHORITY: apps/game-runtime/src/runtime/GameRuntimeServer.ts
ENTRYPOINT: apps/game-runtime/src/runtime/GameRuntimeServer.ts
```

### 6.4 `sandbox`

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /tmp/hermes-safe-sandbox-src \
  --query "Fix app.py so add(a, b) returns the correct sum. Keep the change minimal." \
  --validation-cmd 'python3 -c "from app import add; assert add(2, 3) == 5"'
```

实际成功返回 JSON，且 `result.json` 中：

- `success = true`
- `validation_success = true`
- `changed_files = ["app.py"]`

## 7. 常用命令

### 7.1 查看帮助

```bash
hermes-safe --help
hermes-safe run --help
```

### 7.2 text 模式

```bash
hermes-safe run --mode text --query "Reply READY only."
```

### 7.3 json 模式

```bash
hermes-safe run --mode json --query-file /path/to/prompt.txt
```

### 7.4 readonly 模式

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query "Use terminal tools to inspect first. Do not modify files. Return strict JSON only."
```

### 7.5 sandbox 模式

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query "Fix the bug with the smallest safe change." \
  --validation-cmd "pytest -q"
```

### 7.6 导出结果 JSON

```bash
hermes-safe run \
  --mode json \
  --query 'Return strict JSON only. {"status":"ready"}' \
  --output /tmp/hermes-safe-result.json
```

## 8. 失败语义

当前固定的 `failure_reason`：

- `contract_failure`
- `json_parse_failure`
- `timeout`
- `session_missing`
- `readonly_violation`
- `validation_failure`
- `hard_process_failure`

不要再把失败只理解成“exit code 非 0”。  
真正应该看的是：

- `success`
- `soft_success`
- `failure_reason`
- `output_source`

## 9. 故障排查

### 9.1 CLI 非 0，但怀疑答案其实出来了

先看：

- [latest/result.json](/home/hhtele/.hermes-safe/latest/result.json)
- [latest/session.json](/home/hhtele/.hermes-safe/latest/session.json)
- [latest/stderr.txt](/home/hhtele/.hermes-safe/latest/stderr.txt)

重点字段：

- `soft_success`
- `output_source`
- `session_source`

如果 `soft_success=true`，说明 Hermes CLI 虽然报错，但 wrapper 已经成功从 session 救回答案。

### 9.2 JSON 模式失败

先看：

- `failure_reason`
- `final_output`
- `stdout.txt`
- `session.json`

常见原因：

- 模型返回了 prose 而不是 JSON
- session 中有 fenced JSON，但最终仍提取失败
- 原始 query 的 JSON contract 太复杂

建议：

- 先把 schema 收窄
- 保持 `Return strict JSON only`
- 不要一次要求太多字段

### 9.3 readonly 模式失败

先看：

- `readonly_delta`

这说明运行后仓库状态有变化。  
当前策略是宁可失败，也不放过真实仓库写风险。

### 9.4 sandbox 模式失败

优先看：

- `validation_results`
- `changed_files`
- `workspace/`

判断顺序：

1. 模型有没有真的改文件
2. 验证命令为什么没过
3. 是 contract 失败，还是代码没写对

## 10. 与现有服务的关系

`hermes-safe` 不改：

- [openclaw-executor.service](/etc/systemd/system/openclaw-executor.service)
- 现有本机模型接口 `http://127.0.0.1:18343/v1`
- 现有 GCP 网关 `http://34.123.73.240/v1`

本次已经实际确认：

- 本机 `/v1/models` 正常
- GCP 网关 `/v1/models` 正常
- `openclaw-executor.service` 仍为 `active`

## 11. 回滚

如果只回滚 `hermes-safe`，不影响原始 Hermes：

删除：

- [/home/hhtele/.local/bin/hermes-safe](/home/hhtele/.local/bin/hermes-safe)
- [/home/hhtele/hermes-safe](/home/hhtele/hermes-safe)
- [/home/hhtele/.hermes-safe](/home/hhtele/.hermes-safe)

原始 Hermes 仍然可以继续用：

```bash
hermes chat -q "Reply READY only" -Q
```
