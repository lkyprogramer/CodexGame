# Case 03a: 默认 reasoning 短输出失败复现

## 状态

`FAILED_EXPECTATION`。服务进程和 HTTP 请求本身成功，但短输出协议失败：`short_ok` 的 `content` 为空、`reasoning_content` 非空、`finish_reason=length`，因此不能作为 OpenClaw 默认配置。

## 证据

- lane：`raw/remote/qwen38-27b-4090-20260817/raw/qwen38_smoke_n2_ctx32_reasoning_on_failure`
- console：`raw/remote/qwen38-27b-4090-20260817/logs/case03-initial-reasoning-failure-console.log`
- content：`''`
- reasoning_content：`'The user is asking me to reply with "OK" only. This is a'`
- completion tokens：`16`
- format score：`1/5`
- quality score：`1/5`

## 修复后的门禁

随后正式 smoke 使用 `enable_thinking=false` 重跑，短输出和 strict JSON 均通过；该失败样例保留用于防止未来启动参数回归。
