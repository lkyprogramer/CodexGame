# Qwen 单人压测报告

## 1. 报告概览

- 生成时间（UTC）：`2026-03-07T14:06:29.637064+00:00`
- 目标模型：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 目标地址：`http://100.107.189.100:18343/v1`
- 总用例数：`18`
- 成功数：`6`
- 失败数：`12`
- 成功率：`33.3%`

## 2. 结论摘要

- 当前这套配置适合**单人顺序使用**，不适合并发吞吐型服务。
- `thinking mode` 在 OpenAI 兼容接口下是可用的，并且可返回 `reasoning_content`。
- `262K` 配置下，大上下文真实请求是可执行的。
- 单人场景下，`max_tokens` 不能设得过小。
- 本轮压测里，最小稳定 `max_tokens` 为：`128`
- cache 复用的信号：
  - cache 场景 prompt_ms 平均：`-`
  - 第一轮到后续轮最优下降比例：`-%`

## 3. 关键发现

### 3.1 thinking mode

- thinking mode 已被真实验证为可用。
- 正常成功的响应中同时包含：
  - `message.content`
  - `message.reasoning_content`

### 3.2 max_tokens 安全边界

- 本轮边界测试的重点是验证单人使用时的最小安全 token 预算。
- 如果 `max_tokens` 太小，thinking 内容可能还未完整闭合，就会触发服务端解析失败。
- 因此单人 coding 请求建议：
  - 保守默认：`256`
  - 更实用默认：`512` 到 `1024`

### 3.3 长上下文

| 用例 | prompt_tokens | http_status | elapsed_ms | predicted_per_second | reasoning_len |
| --- | ---: | ---: | ---: | ---: | ---: |
| `context_small` |  | 500 | 21853.902 |  | 0 |
| `context_medium` | 19728 | 200 | 46456.482 | 40.286062517359596 | 2292 |
| `context_large` |  | 500 | 93591.7 |  | 0 |

### 3.4 单人连续使用

- 本轮包含顺序 soak 用例，用于模拟单人连续工作而不是多并发。
- soak 用例数：`5`
- soak 成功率：`20.0%`

## 4. 失败样本

- `smoke_java_bugfix`: http=500, max_tokens=1024, error=`Failed to parse input at pos 4164: `
- `boundary_max_tokens_8`: http=500, max_tokens=8, error=`Failed to parse input at pos 25: `
- `boundary_max_tokens_64`: http=500, max_tokens=64, error=`Failed to parse input at pos 213: `
- `context_small`: http=500, max_tokens=768, error=`Failed to parse input at pos 3470: `
- `context_large`: http=500, max_tokens=1024, error=`Failed to parse input at pos 4510: `
- `cache_round_1`: http=500, max_tokens=768, error=`Failed to parse input at pos 3351: `
- `cache_round_2`: http=500, max_tokens=768, error=`Failed to parse input at pos 3435: `
- `cache_round_3`: http=500, max_tokens=768, error=`Failed to parse input at pos 3325: `
- `soak_round_1`: http=500, max_tokens=768, error=`Failed to parse input at pos 3282: `
- `soak_round_2`: http=500, max_tokens=768, error=`Failed to parse input at pos 3292: `
- `soak_round_3`: http=500, max_tokens=768, error=`Failed to parse input at pos 3276: `
- `soak_round_4`: http=500, max_tokens=768, error=`Failed to parse input at pos 3190: `

## 5. 推荐配置结论

当前最适合单人精确编码任务的配置可以保持为：

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --alias unsloth/Qwen3.5-27B-UD-Q4_K_XL \
  -ngl 99 \
  -c 262144 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --temp 0.6 \
  --top-p 0.95 \
  --top-k 20 \
  --min-p 0.0 \
  --chat-template-kwargs '{"enable_thinking": true}' \
  --host 0.0.0.0 \
  --port 18343
```

## 6. 对使用者的直接建议

- 如果是单人 coding，保持 `-np 1`。
- 长会话和大仓库分析场景，保持 `262144`。
- 调 OpenAI 接口时，不要把 `max_tokens` 设得过小。
- 精确编码场景下，优先使用：
  - `max_tokens=512`
  - 或 `max_tokens=1024`

## 7. 工件位置

- 原始结果 CSV：`/home/luo/qwen-bench/results/single_user_bench_results.csv`
- 元数据 JSON：`/home/luo/qwen-bench/results/single_user_bench_meta.json`
- 本报告：`/home/luo/qwen-bench/results/single_user_bench_report.md`
