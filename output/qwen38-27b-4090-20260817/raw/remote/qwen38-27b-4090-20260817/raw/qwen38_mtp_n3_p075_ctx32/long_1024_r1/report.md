# long_1024_r1

- status: `PASS`
- started: `2026-08-16T22:54:51-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n3_p075_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `84`
- completion_tokens: `1024`
- prompt_ms: `197.422`
- predicted_ms: `16730.919`
- prompt_tokens_per_s: `425.48449514238536`
- decode_tokens_per_s: `61.20404981937932`
- effective_tokens_per_s: `59.861802463542254`
- draft_n: `652`
- draft_n_accepted: `541`
- draft_acceptance_rate: `0.8297546012269938`
- cache_n: `27`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `length`

## GPU

- peak memory MiB: `18732.0`
- max utilization: `96.0`
- max power W: `410.94`
- max temperature C: `80.0`

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

1. Immediate Context and Safety
A 502 Bad Gateway error indicates that the reverse proxy or load balancer (e.g., Nginx, HAProxy, AWS ALB) received an invalid response from the upstream Java/Spring application. This is distinct from a 503 Service Unavailable, which usually implies the upstream is down or overloaded. A 502 suggests the upstream process is running but failing to communicate correctly, crashing mid-request, or returning malformed data.

Before executing any commands, verify that you have read-only access to the production environment. Do not restart services or modify configurations until the root cause is isolated. If the error rate is above 5 percent, immediately trigger the rollback procedure in Section 5.

2. Evidence Collection
Gather data from three distinct layers: the edge (proxy), the application (Spring Boot), and the infrastructure (OS/Container).

Edge Layer (Reverse Proxy)
Check the access logs and error logs of the load balancer. Look for specific error strings.
- Connection refused: The Spring app is not listening on the expected port.
- Connection reset by peer: The Spring app accepted the connection but closed it abruptly.
- Upstream timed out: The Spring app is taking longer than the proxy timeout allows.
- Invalid header field value: The Spring app is returning malformed HTTP headers.

Application Layer (Spring Boot)
Retrieve the application logs from the last 15 minutes. Focus on the following patterns:
- OutOfMemoryError: Indicates heap exhaustion.
- StackOverflowError: Indicates infinite recursion.
- Connection pool exhaustion: Look for "Cannot get a connection, pool error" or HikariCP timeout messages.
- Unhandled exceptions: Look for 500 status codes in the application logs that correlate with the 502s at the edge.

Infrastructure Layer
Check system resources on the host or container.
- CPU usage: Sustained 100 percent CPU may indicate a busy loop or GC thrashing.
- Memory usage: Check for OOM killer events in dmesg or system logs.
- Disk I/O: High I/O wait can cause request timeouts.
- Network: Check for dropped packets or connection limits (netstat -s).

3. Hypotheses
Based on the evidence, prioritize the following hypotheses:

Hypothesis A: Application Crash or Restart
The Spring Boot process is crashing and restarting. During the restart window, the proxy cannot connect.
- Evidence: Application logs show a shutdown sequence followed by a startup sequence. System logs show process termination.
- Likelihood: High if errors are intermittent and clustered.

Hypothesis B: Thread Pool Exhaustion
The Tomcat or Jetty thread pool is full. New requests are queued or rejected.
- Evidence: Application logs show "RejectedExecutionException" or high thread count. Metrics show high active thread count.
- Likelihood: Medium if errors correlate with traffic spikes.

Hypothesis C: Database or Downstream Timeout
The Spring app is waiting for a slow database query or external API call, exceeding the proxy timeout.
- Evidence: Application logs show long execution times for specific endpoints. Database logs show slow queries.
- Likelihood: High if errors are consistent for specific endpoints.

Hypothesis D: Malformed Response
The Spring app is returning a response that the proxy cannot parse (e.g., invalid header, missing Content-Length).
- Evidence: Proxy error logs show "invalid header" or "bad response". Application logs show successful 200 responses.
- Likelihood: Low, but possible after a recent code change involving custom headers or filters.

Hypothesis E: Resource Exhaustion
The JVM is out of memory or the host is out of file descriptors.
- Evidence: JVM logs show frequent Full GCs. System logs show "Too many open files".
- Likelihood: Medium if errors are persistent.

4. Safe Checks
Execute these checks in order. Do not modify any configuration.

Check 1: Verify Process Status
- Command: ps aux | grep java
- Expected: The Java process is running.
- Action: If not running, check the container orchestrator (Kubernetes, Docker) for crash loops.

Check 2: Verify Port Listening
- Command: netstat -tlnp | grep <port>
- Expected: The Java process is listening on the expected port.
- Action: If not listening, check the application configuration for server.port.

Check 3: Check JVM Health
- Command: jps -lvm
- Expected: The JVM is running with reasonable memory usage.
- Action: If memory usage is near the max heap, take a heap dump (if safe) or check GC logs.

Check 4: Check Thread Count

```
