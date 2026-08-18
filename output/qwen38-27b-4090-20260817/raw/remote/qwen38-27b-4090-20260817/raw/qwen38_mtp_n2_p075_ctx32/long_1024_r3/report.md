# long_1024_r3

- status: `PASS`
- started: `2026-08-16T22:52:09-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p075_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `84`
- completion_tokens: `1024`
- prompt_ms: `196.341`
- predicted_ms: `17657.849`
- prompt_tokens_per_s: `427.82709673476245`
- decode_tokens_per_s: `57.991208328941994`
- effective_tokens_per_s: `57.33284759588294`
- draft_n: `543`
- draft_n_accepted: `488`
- draft_acceptance_rate: `0.8987108655616943`
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
- max utilization: `96.0`
- max power W: `415.91`
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
A 502 Bad Gateway error indicates that the reverse proxy or load balancer (e.g., Nginx, HAProxy, AWS ALB) received an invalid response from the upstream Java/Spring application. This is distinct from a 503 Service Unavailable, which usually implies the upstream is down or overloaded. A 502 suggests the upstream is reachable but failing to communicate correctly, crashing, or timing out.

Before executing any commands, verify that you have read-only access to the production environment. Do not restart services or modify configurations until the root cause is identified. If the service is critical and traffic is failing, consider enabling a maintenance page or draining traffic to a healthy instance if available.

2. Evidence Collection
Gather data from three distinct layers: the edge (proxy), the application (Spring/Java), and the infrastructure (OS/Container).

Edge Layer (Reverse Proxy/Load Balancer)
- Retrieve the access logs for the specific time window of the incident. Look for the upstream status code. If the log shows "upstream timed out," the issue is latency. If it shows "connection reset by peer" or "broken pipe," the Java process likely crashed or closed the socket abruptly.
- Check the error logs for specific proxy messages. Nginx often logs "upstream prematurely closed connection" or "no live upstreams."
- Verify the health check status. If the proxy is marking the backend as unhealthy, it may be routing traffic to a dead instance.

Application Layer (Spring/Java)
- Collect the application logs (stdout/stderr or log files) for the affected instance. Search for exceptions such as OutOfMemoryError, StackOverflowError, or specific Spring framework errors like "Failed to bind properties" or "BeanCreationException."
- Check for thread dumps. If the application is hanging, a thread dump will reveal if threads are blocked on I/O, database locks, or synchronized blocks.
- Review the Spring Boot Actuator health endpoint (if exposed) to see if the application reports itself as DOWN or DEGRADED.

Infrastructure Layer (OS/Container)
- Check system resource utilization. High CPU usage may indicate a busy loop or excessive garbage collection. High memory usage may indicate a memory leak leading to OOM kills.
- For containerized environments (Kubernetes/Docker), check the container status. Look for "OOMKilled" or "CrashLoopBackOff" states.
- Verify network connectivity between the proxy and the Java application. Ensure there are no firewall rules or security groups blocking the port.

3. Hypotheses
Based on the evidence, prioritize the following hypotheses:

Hypothesis A: Application Crash or Restart
The Java process terminated unexpectedly due to an unhandled exception, OOM, or a liveness probe failure. The proxy attempted to send a request to a dead process.
- Supporting Evidence: Container restarts, OOMKilled status, "connection refused" in proxy logs.

Hypothesis B: Timeout Mismatch
The reverse proxy has a shorter timeout than the Java application. The Java app is processing a slow request (e.g., complex query, external API call) and exceeds the proxy's read timeout.
- Supporting Evidence: "upstream timed out" in proxy logs, long request durations in application logs, no exceptions in Java logs.

Hypothesis C: Resource Exhaustion
The Java application is running out of memory, file descriptors, or database connections. It accepts the connection but fails to process the request, leading to a reset or hang.
- Supporting Evidence: High GC time, "Too many open files" errors, database connection pool exhaustion logs.

Hypothesis D: Configuration Drift
A recent deployment introduced a configuration error (e.g., wrong port, malformed YAML) that causes the Spring context to fail to start or bind incorrectly.
- Supporting Evidence: Application fails to start, "Port already in use" or "BindException" in logs.

4. Safe Checks
Execute these checks in order of least to most intrusive.

Step 1: Verify Process Status
- On the host or in the container, confirm the Java process is running.
- Command: ps aux | grep java
- If the process is missing, check the container logs for the reason for termination.

Step 2: Check Port Binding
- Ensure the Java application is listening on the expected port.
- Command: netstat -tlnp | grep <port> or ss -tlnp | grep <port>
- If the port is not listening, the application has not started or has crashed.

Step 3: Test Local Connectivity
- From the same host as the Java application, test connectivity to the local port.
- Command: curl -v http://localhost:<port>/act
```
