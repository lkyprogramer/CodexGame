# Pi + Java Agent Benchmark

## Pi provider isolation

The benchmark does not overwrite the user's normal `~/.pi` configuration. It creates an isolated HOME under `.state/pi-home` and writes a local `models.json` pointing at the vLLM endpoint.

Pi supports custom OpenAI-compatible providers through `models.json`, including `baseUrl`, `openai-completions`, context-window metadata and compatibility flags. The harness runs Pi in JSON event-stream mode so tool calls and provider usage can be counted.

## Default Pi settings

```text
provider          local-vllm
model             qwen3.8-27b-local
thinking          medium
allowed tools     read,bash,edit,write,grep,find,ls
session           ephemeral per case
version check     disabled
telemetry         disabled for test process
```

If your installed Pi/version maps reasoning differently and returns HTTP 400, set:

```bash
PI_THINKING=off
```

and rerun. Record that deviation in the report; do not silently change it during a comparison.

## Why these Java tasks

The fixtures deliberately avoid Maven/Gradle dependencies so test time measures the Agent and inference stack, not network/download behavior. They still mirror common Java backend work:

- idempotency and concurrency;
- retry/error-handling semantics;
- stateful reconnect/runtime logic;
- log/source correlation;
- cross-file fixes;
- compile/test/retry tool loops.

The third case contains a long operational/design document so the Agent has to maintain context while moving between logs and several source files.

## Scoring

A case passes only when:

1. Pi exits before timeout;
2. `verify.sh` passes;
3. protected test hashes are unchanged;
4. the source tree contains an actual production-code change.

The parser records:

- elapsed seconds;
- tool-call count;
- input/output/cache usage when present in Pi JSON;
- Pi exit code;
- validator result.

## Real-work interpretation

Three passing micro-repositories do not prove an Agent can work for eight hours. They are a compact proxy for the failure modes that matter in a long session: tool use, remembering constraints, iterative compilation, cross-file reasoning and context growth. The HTTP prefix-cache stage separately tests the runtime property that becomes dominant as the session reaches tens or hundreds of thousands of tokens.
