# long_1024_r3

- status: `PASS`
- started: `2026-08-16T22:45:02-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_no_spec_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `84`
- completion_tokens: `1024`
- prompt_ms: `178.555`
- predicted_ms: `22920.724`
- prompt_tokens_per_s: `470.4432807818319`
- decode_tokens_per_s: `44.675726648076214`
- effective_tokens_per_s: `44.31594700302167`
- draft_n: `0`
- draft_n_accepted: `0`
- draft_acceptance_rate: `None`
- cache_n: `27`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `length`

## GPU

- peak memory MiB: `17702.0`
- max utilization: `97.0`
- max power W: `384.03`
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
The Spring Boot process has crashed or is in the middle of a restart. The reverse proxy is still routing traffic to the instance, but the process is not accepting connections.
Indicators: Application logs show a fatal exception or shutdown sequence. System metrics show the process is not running. The reverse proxy log shows "connection refused."

Hypothesis B: Thread Pool Exhaustion
The Tomcat or Jetty thread pool within Spring Boot is saturated. New requests are queued or rejected, causing the reverse proxy to time out waiting for a response.
Indicators: Application logs show "RejectedExecutionException" or "Thread pool is full." System metrics show high CPU usage. The reverse proxy log shows "upstream timed out."

Hypothesis C: Memory Leak or Garbage Collection Pause
The application is experiencing long garbage collection pauses or has run out of heap memory. The JVM is in a "stop-the-world" state, causing requests to hang.
Indicators: System metrics show high memory usage and frequent GC events. Application logs show "GC overhead limit exceeded" or "Java heap space." The reverse proxy log shows "upstream timed out."

Hypothesis D: Database or Downstream Dependency Failure
The Spring application is waiting for a response from a database, cache, or external API that is unresponsive. This causes the request thread to block, eventually exhausting the thread pool.
Indicators: Application logs show database connection timeouts or "Connection pool exhausted." The reverse proxy log shows "upstream timed out." The issue may be intermittent, correlating with database load.

Hypothesis E: Reverse Proxy Configuration Error
The reverse proxy is misconfigured, pointing to the wrong port, IP address, or health check endpoint.
Indicators: The issue started immediately after a configuration change. The reverse proxy log shows "no live upstreams" or "connection refused" even though the application is running.

3. Safe Diagnostic Checks

Execute the following checks in order. Do not perform destructive actions until the root cause is identified.

Check 1: Verify Application Process Status
On the application host, run: ps -ef | grep java
Confirm that the Spring Boot process is running. If it is not, check the system logs for OOM killer events or crash dumps. If it is running, proceed to Check 2.

Check 2: Verify Port Listening
On the application host, run: netstat -tlnp | grep 8080
Confirm that the process is listening on the expected port. If it is not listening, the application may have failed to start or crashed after startup. Check the application logs for startup errors.

Check 3: Test Local Connectivity
On the application host, run: curl -v http://localhost:8080/actuator/health
If the actuator endpoint is enabled, this will return a JSON response indicating the
```
