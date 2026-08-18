# long_1024_r2

- status: `PASS`
- started: `2026-08-16T22:49:00-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n1_p075_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `84`
- completion_tokens: `1024`
- prompt_ms: `194.933`
- predicted_ms: `18840.143`
- prompt_tokens_per_s: `430.91728953024887`
- decode_tokens_per_s: `54.352029068993794`
- effective_tokens_per_s: `53.29257336252151`
- draft_n: `420`
- draft_n_accepted: `400`
- draft_acceptance_rate: `0.9523809523809523`
- cache_n: `27`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `length`

## GPU

- peak memory MiB: `18424.0`
- max utilization: `96.0`
- max power W: `383.41`
- max temperature C: `78.0`

## Manual review

- format score (1-5): `4`
- quality score (1-5): `4`
- reviewer notes: `请求成功且内容可读，格式未命中更强的自动断言。`

## Raw evidence

- `request.json`
- `response.json`
- `result.json`
- `server.stdout.log`
- `server.stderr.log`
- `gpu.csv`
- `trace.json` (when this is a multi-turn trace)

## Output

```text
Operational Runbook: Diagnosing Java/Spring HTTP 502 Errors

1. Immediate Evidence Collection

Before attempting remediation, establish a baseline of the current failure state. A 502 Bad Gateway indicates that the reverse proxy (such as Nginx, HAProxy, or AWS ALB) received an invalid response from the upstream Spring Boot application. This is distinct from a 503 Service Unavailable, which usually implies the upstream is down or overloaded.

Gather the following artifacts immediately:

Reverse Proxy Logs: Extract the last 500 lines of the error log from the load balancer. Look for specific upstream errors such as "upstream prematurely closed connection," "connection reset by peer," or "no live upstreams." Note the exact timestamp of the first occurrence.

Application Logs: Retrieve the Spring Boot application logs from the affected instance. Focus on the ERROR and WARN levels. Look for OutOfMemoryError, StackOverflowError, or specific exception traces related to request processing. If the application is unresponsive, check if the log file is still being written to.

System Metrics: Capture CPU, memory, and disk I/O utilization for the host running the Spring application. High CPU usage may indicate a busy loop or excessive garbage collection. High memory usage may indicate a memory leak.

Network Connectivity: Verify that the reverse proxy can reach the Spring application on the expected port (default 8080). Use telnet or nc from the proxy host to the application host and port. If the connection times out, the issue is network-level or the application is not listening.

Request Context: If possible, identify the specific URL or API endpoint triggering the 502. Is it a single endpoint or all endpoints? Is it a specific user or all users? This helps determine if the issue is localized to a specific code path or systemic.

2. Hypothesis Formulation

Based on the evidence, prioritize the following hypotheses. Do not assume the first hypothesis is correct; validate each one systematically.

Hypothesis A: Application Crash or Restart
The Spring Boot application process has terminated or is in the middle of a restart. The reverse proxy is still routing traffic to the instance, but the process is not accepting connections.
Indicators: Application logs show a shutdown sequence or a fatal exception. System metrics show a drop in process count. The application port is not listening.

Hypothesis B: Thread Pool Exhaustion
The Tomcat or Jetty thread pool within Spring Boot is saturated. New requests are queued or rejected, causing the reverse proxy to time out and return a 502.
Indicators: High CPU usage. Application logs show "RejectedExecutionException" or "Thread pool is full." Response times for successful requests are increasing before the 502s begin.

Hypothesis C: Memory Leak or Garbage Collection Pressure
The Java heap is exhausted, causing long Full GC pauses. During these pauses, the application cannot respond to requests, leading to timeouts at the proxy level.
Indicators: High memory usage trending upward. Long GC pauses visible in GC logs. Application logs may show "GC overhead limit exceeded" or "Java heap space."

Hypothesis D: Downstream Dependency Failure
The Spring application is waiting for a downstream service (database, external API, message queue) that is unresponsive. This blocks request threads, leading to thread pool exhaustion (Hypothesis B).
Indicators: Application logs show timeouts or connection errors to the database or external services. Database metrics show high latency or connection pool exhaustion.

Hypothesis E: Reverse Proxy Configuration Error
The reverse proxy is misconfigured, pointing to the wrong port, IP address, or health check endpoint.
Indicators: The issue started immediately after a configuration change. The application is healthy and responding to direct requests, but the proxy cannot reach it.

3. Safe Diagnostic Checks

Execute these checks in order. Do not perform destructive actions until the root cause is identified.

Check 1: Verify Application Process Status
On the application host, run: ps -ef | grep java
Confirm that the Spring Boot process is running. If it is not running, check the system logs (journalctl -u spring-app or /var/log/syslog) for OOM killer messages or crash dumps.

Check 2: Verify Port Listening
On the application host, run: netstat -tlnp | grep 8080 (or the configured port)
Confirm that the process is listening on the expected interface and port. If it is not listening, the application may be stuck in startup or has crashed.

Check 3: Test Direct Application Connectivity
From the reverse proxy host, run: curl -v http://<app-ip>:8080/actuator/health
If the application exposes Spring Boot Actuator, this endpoint provides a quick health check. If it returns 200 OK, the application is alive
```
