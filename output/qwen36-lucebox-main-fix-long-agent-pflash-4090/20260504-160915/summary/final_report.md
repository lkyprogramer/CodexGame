# Lucebox Qwen3.6 Long/Agent + PFlash 修复验证报告

## 结论

- GGUF draft restore bad header: 未复现
- PFlash NIAH: 2/3 命中
- TQ3 128K long decode: visible_tokens=128, stop_token_hit=False, thinking_leakage=False
- Server/cache agent loop: 5/5 可用
- Server cache hit: prefix=0, full=0, snapshot_oom=True
- no-thinking: 通过

## 判定

- long/agent 生成链路可以进入下一轮质量评测；这不是上线结论。
- server/cache 不能判为 cache winner：本轮 prefix/full cache hit 为 0，需继续解决 snapshot OOM 或降低 cache slots/context。
- PFlash loader 问题已修复，命中样例可作为候选配置继续扩大样本。

## 关键指标

### PFlash NIAH

| case | keep | compressed | ratio | score_s | gen_s | hit | bad_header |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 32k | 0.1 | 3466 | 10.1 | 4.6 | 2.9 | True | False |
| 64k | 0.05 | 3473 | 20.1 | 6.2 | 2.8 | True | False |
| 128k | 0.02 | 2755 | 50.8 | 11.0 | 2.5 | False | False |

### Long Decode

| case | prompt | visible | raw | stop | elapsed_s | leak |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| tq3_32k | 31977 | 128 | 128 | False | 37.6 | False |
| tq3_64k | 64762 | 128 | 128 | False | 80.9 | False |
| tq3_128k | 130249 | 128 | 128 | False | 222.5 | False |
| q4_32k | 31977 | 128 | 128 | False | 31.2 | False |

### Server/cache

- short non-stream: len=230, leak=False
- short stream: len=230, leak=False
- diag entries: 7
- cache stats: prefix_hits=0, full_hits=0, compression_fired=5, snapshot_oom=True

| turn | len | completion_tokens | elapsed_s | leak | marker |
| ---: | ---: | ---: | ---: | --- | --- |
| 1 | 602 | 128 | 12.9 | False | True |
| 2 | 586 | 128 | 12.7 | False | True |
| 3 | 584 | 128 | 12.7 | False | True |
| 4 | 563 | 128 | 12.6 | False | True |
| 5 | 599 | 128 | 12.6 | False | True |

## 服务恢复

```json
{
  "qwen35-35b-a3b-uncensored": "active",
  "openclaw-executor": "inactive",
  "models": {
    "models": [
      {
        "name": "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M",
        "model": "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M",
        "modified_at": "",
        "size": "",
        "digest": "",
        "type": "model",
        "description": "",
        "tags": [
          ""
        ],
        "capabilities": [
          "completion"
        ],
        "parameters": "",
        "details": {
          "parent_model": "",
          "format": "gguf",
          "family": "",
          "families": [
            ""
          ],
          "parameter_size": "",
          "quantization_level": ""
        }
      }
    ],
    "object": "list",
    "data": [
      {
        "id": "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M",
        "aliases": [
          "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"
        ],
        "tags": [],
        "object": "model",
        "created": 1777882833,
        "owned_by": "llamacpp",
        "meta": {
          "vocab_type": 2,
          "n_vocab": 248320,
          "n_ctx_train": 262144,
          "n_embd": 2048,
          "n_params": 34660610688,
          "size": 21158128128
        }
      }
    ]
  }
}
```
