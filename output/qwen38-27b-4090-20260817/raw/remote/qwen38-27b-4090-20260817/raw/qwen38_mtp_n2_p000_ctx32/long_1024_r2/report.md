# long_1024_r2

- status: `PASS`
- started: `2026-08-16T23:00:07-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p000_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `84`
- completion_tokens: `1024`
- prompt_ms: `197.563`
- predicted_ms: `13199.045`
- prompt_tokens_per_s: `425.1808283939807`
- decode_tokens_per_s: `77.58137047036358`
- effective_tokens_per_s: `75.41528429061415`
- draft_n: `886`
- draft_n_accepted: `579`
- draft_acceptance_rate: `0.6534988713318285`
- cache_n: `27`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `length`

## GPU

- peak memory MiB: `18580.0`
- max utilization: `100.0`
- max power W: `442.77`
- max temperature C: `84.0`

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
A 502 Bad Gateway error indicates that the reverse proxy or load balancer (e.g., Nginx, HAProxy, AWS ALB) received an invalid response from the upstream Java/Spring application. This is distinct from a 503 Service Unavailable, which usually implies the upstream is down or overloaded. A 502 suggests the upstream is reachable but failing to communicate correctly, crashing, or returning malformed data.

Before executing any commands, verify that you have read-only access to the production environment. Do not restart services or modify configurations until the root cause is identified. If the service is critical and traffic is failing, consider enabling a maintenance page or failover to a secondary region if available, rather than attempting a live fix.

2. Evidence Collection
Gather data from three distinct layers: the edge (proxy), the application (Spring/Java), and the infrastructure (OS/Container).

Edge Layer (Reverse Proxy/Load Balancer)
- Retrieve the access logs for the specific time window of the incident. Look for the upstream status code. If the log shows "upstream_status: 502" or "upstream_status: 000", the connection was reset or closed prematurely.
- Check error logs for specific messages such as "upstream prematurely closed connection," "no live upstreams," or "connection refused."
- Verify the health check status of the upstream instances. If the proxy marks the instance as unhealthy, it may be routing traffic to a dead node.

Application Layer (Spring/Java)
- Collect the application logs (stdout/stderr or log files) for the affected instance. Search for exceptions, stack traces, or OOM (Out of Memory) kills.
- Check the Spring Boot Actuator endpoints if exposed. Specifically, look at /actuator/health and /actuator/metrics. A "DOWN" status on the health endpoint often correlates with 502s if the proxy relies on health checks.
- Review the JVM logs for garbage collection pauses. Long GC pauses can cause the application to stop responding to keep-alive requests, leading the proxy to interpret this as a failure.

Infrastructure Layer
- Check system resource utilization: CPU, Memory, and Disk I/O. High memory pressure can cause the OS to kill the Java process (OOM Killer).
- Verify network connectivity between the proxy and the application. Use ping or traceroute if appropriate, but be aware that ICMP may be blocked.
- If running in a containerized environment (Kubernetes/Docker), check the container status. Look for "CrashLoopBackOff" or "OOMKilled" states.

3. Hypotheses
Based on the evidence, prioritize the following hypotheses:

Hypothesis A: Application Crash or Restart
The Java process has terminated unexpectedly. This is common if the application throws an unhandled exception during startup or if it is killed by the OS due to memory limits.
- Indicator: Application logs show a shutdown sequence or no logs after a certain timestamp. Container status shows "Exited" or "Restarting."

Hypothesis B: Resource Exhaustion (Memory/CPU)
The application is running but is too slow to respond within the proxy's timeout window. This can be caused by memory leaks, high CPU usage, or disk I/O bottlenecks.
- Indicator: High GC activity in JVM logs, high CPU usage, or slow response times in application metrics. The proxy logs show "upstream timed out."

Hypothesis C: Network or Configuration Mismatch
The proxy is trying to connect to the wrong port, IP, or protocol. This can happen after a deployment if the service port changes or if the application binds to a different interface.
- Indicator: Proxy logs show "connection refused" or "no route to host." The application is listening on a different port than expected.

Hypothesis D: Malformed Response
The application is returning a response that the proxy cannot parse. This is rare but can occur if the application sends invalid HTTP headers or if there is a protocol mismatch (e.g., HTTP vs. HTTPS).
- Indicator: Proxy logs show "invalid header" or "bad response." The application logs show successful request processing.

4. Safe Checks
Execute these checks in order of least to most intrusive.

Step 1: Verify Application Process Status
- On the host or container, run: ps aux | grep java
- Confirm the Java process is running. If it is not, proceed to Step 2. If it is, proceed to Step 3.

Step 2: Check for OOM Kills
- On the host, run: dmesg | grep -i "killed process"
- If you see a message indicating the Java process was killed, check the memory limits of the container or host
```
