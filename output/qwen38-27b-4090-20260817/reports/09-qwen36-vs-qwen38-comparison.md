# Case 09: Qwen3.6 与 Qwen3.8 对比

## 对比表

| workload/reference | decode tok/s | JSON/tool | patch | VRAM | note |
|---|---:|---|---|---:|---|
| Qwen3.6 production JSON tool | 79.29 | PASS | n/a | production | old binary `46` draft timing |
| Qwen3.6 production patch review | 57.30 | n/a | fence (FAIL strict JSON) | production | reference only |
| Qwen3.8 no-spec 1024 | 44.69 | strict JSON PASS | patch fence | 17702 MiB | same Q38 matrix |
| Qwen3.8 MTP n=4 p=.75 2048 | 75.75 | strict JSON PASS | patch fence | 18886 MiB | balanced candidate |
| Qwen3.8 MTP n=2 p=0 2048 | 85.40 | strict JSON PASS | patch fence | 18580 MiB | fastest but lower acceptance |
| Qwen3.8 agent trace n=2 p=.75 | 61.53 | tool + JSON PASS | patch JSON PASS | 20600 MiB | real multi-turn trace |

Qwen3.6 baseline 使用现有生产服务、旧 binary/启动参数和不同请求集合，只作为 OpenClaw 参考，不把不同 workload 的 tok/s 宣称为严格 A/B。Qwen3.8 matrix 使用同一模型和同一批请求，因此 matrix 内 lane 对比是可比的。

## 质量

- Qwen3.8 smoke strict JSON、agent trace 工具调用/JSON/patch 均通过。
- matrix patch review 仍偶发 markdown fence，与 Qwen3.6 baseline 的 patch review 也存在同类问题；生产客户端必须启用 schema/grammar 或严格后处理。
- Qwen3.8 默认关闭 thinking 后短请求稳定；reasoning profile 独立验证通过。

证据：`raw/remote/qwen38-27b-4090-20260817/raw` 下 `baseline-production-qwen36-*` 与 `qwen38_*` lane。
