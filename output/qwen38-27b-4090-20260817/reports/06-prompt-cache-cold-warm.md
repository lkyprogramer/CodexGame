# Case 06: Prompt cache 冷热、增量与相似度

## 指标

| phase | cache_n | prompt tokens | prompt ms | TTFT wall s | decode tok/s | JSON |
|---|---:|---:|---:|---:|---:|---|
| `cold` | 0 | 5639 | 2356.44 | 3.04 | 81.72 | False |
| `warm_exact` | 5635 | 5639 | 116.04 | 0.77 | 85.61 | False |
| `incremental` | 27 | 5650 | 2334.24 | 3.36 | 86.18 | False |
| `similarity` | 5134 | 5640 | 363.38 | 1.13 | 75.35 | False |
| `repeat_1` | 5134 | 5639 | 362.90 | 1.02 | 85.54 | False |
| `repeat_2` | 5635 | 5639 | 115.80 | 0.77 | 85.69 | False |
| `repeat_3` | 5635 | 5639 | 115.30 | 0.77 | 85.75 | False |
| `repeat_4` | 5635 | 5639 | 113.62 | 0.77 | 85.73 | False |
| `repeat_5` | 5635 | 5639 | 113.31 | 0.77 | 85.61 | False |

## 结论

- exact warm `cache_n=5635`，prompt 总量约 5639；cold `cache_n=0`。
- prompt 处理时间从约 2356ms 降至约 116ms，约 `20.31x`；连续重复 5 次稳定在 113-116ms。
- incremental 只复用约 27 tokens，追加消息会重新计算主要前缀；similarity 修改最后一条消息仍复用约 5134 tokens，说明 prefix matching/LRU 行为符合预期。
- cache case 输出带 markdown JSON fence，内容字段正确但不能视为严格 JSON；这是格式层问题，不是 cache 污染。未观察到上一轮答案污染当前 marker。

## 证据

- raw lane：`raw/remote/qwen38-27b-4090-20260817/raw/qwen38_cache_n2_ctx64`
- console：`raw/remote/qwen38-27b-4090-20260817/logs/case06-cache-console.log`
