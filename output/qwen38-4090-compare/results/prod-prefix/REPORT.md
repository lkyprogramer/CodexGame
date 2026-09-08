# Production NInfer prefix via Pi + HTTP

## metrics delta

| 区间 | requests | prefix_hit_tokens | cont_hits | cont_misses | stable_prefix_restores |
|---|---:|---:|---:|---:|---:|
| HTTP探针 | 5.0 | 86.0 | 0.0 | 8.0 | 1.0 |
| Pi Java三题 | 24.0 | 154961.0 | 0.0 | 25.0 | 20.0 |
| 全程 | 29.0 | 155047.0 | 0.0 | 33.0 | 21.0 |

## HTTP 对照

| tag | prompt | cached | hit | ttft_s |
|---|---:|---:|---:|---:|
| A-cold | 88 | None | 0.0 | 0.867 |
| A-append | 173 | 86 | 0.497 | 0.814 |
| B-cold | 88 | None | 0.0 | 0.775 |
| B-rewrite-last-user-root | 190 | None | 0.0 | 1.081 |
| B-rewrite-newest-user-only | 182 | None | 0.0 | 1.018 |

## Pi Java

case,pi_exit,verify_exit,protected_ok,source_changed,elapsed_s,tool_calls,turns,prompt_tokens_sum,completion_tokens_sum
java-agent-1-idempotency,0,0,true,true,25,13,11,,
java-agent-2-retry-contract,0,0,true,true,13,5,6,,
java-agent-3-reconnect-loop,0,0,true,true,19,8,7,,

