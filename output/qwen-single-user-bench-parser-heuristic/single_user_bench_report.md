# Qwen 单人压测报告

## 1. 报告概览

- 生成时间（UTC）：`2026-03-07T17:13:19.870847+00:00`
- 目标模型：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 目标地址：`http://34.123.73.240/v1`
- 总用例数：`18`
- 成功数：`18`
- 失败数：`0`
- 成功率：`100.0%`

## 2. 结论摘要

- 当前这套配置适合**单人顺序使用**，不适合并发吞吐型服务。
- `thinking mode` 在 OpenAI 兼容接口下是可用的，并且可返回 `reasoning_content`。
- `262K` 配置下，大上下文真实请求是可执行的。
- 单人场景下，`max_tokens` 不能设得过小。
- 本轮压测里，最小稳定 `max_tokens` 为：`8`
- cache 复用的信号：
  - cache 场景 prompt_ms 平均：`2998.93`
  - 第一轮到后续轮最优下降比例：`96.23%`

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
| `context_small` | 5230 | 200 | 22535.141 | 42.12249088717205 | 3372 |
| `context_medium` | 19728 | 200 | 45174.099 | 40.273895526761905 | 4518 |
| `context_large` | 64929 | 200 | 92111.08 | 35.50888602937556 | 4329 |

### 3.4 单人连续使用

- 本轮包含顺序 soak 用例，用于模拟单人连续工作而不是多并发。
- soak 用例数：`5`
- soak 成功率：`100.0%`

## 4. 失败样本

- 无失败样本。

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

- 原始结果 CSV：`output/qwen-single-user-bench-parser-heuristic/single_user_bench_results.csv`
- 元数据 JSON：`output/qwen-single-user-bench-parser-heuristic/single_user_bench_meta.json`
- 本报告：`output/qwen-single-user-bench-parser-heuristic/single_user_bench_report.md`
