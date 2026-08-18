# S6 Prompt cache

同一 64K work-balanced 进程。

| phase | prompt tokens | cache_n | prompt_ms | 说明 |
|---|---:|---:|---:|---|
| cold | 6874 | 28 | 2819.7 | 冷启动 |
| warm_exact | 6874 | 6870 | 120.1 | exact 前缀，约 **23.5x** |
| incremental | 6886 | 6870 | 208.2 | 追加一句，前缀命中 |
| similar | 6877 | 28 | 2806.1 | 改了最后一句，未误命中 |
| think_off_short | 45 | 28 | 191.7 | 开关 thinking 后短请求仍可用 |

结论：`--cache-prompt` 可用；相似但不相同的 prompt 不会错误复用。thinking 开关变化没有把短请求打挂。
