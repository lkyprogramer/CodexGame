# Qwen3.5-27B-UD-Q4_K_XL 单人压测详细报告

## 1. 压测目标

本轮压测仅针对 **单人顺序使用** 场景，不测试并发吞吐。  
目标是验证以下问题：

- thinking mode 是否可用
- OpenAI 兼容接口在真实单人 coding 使用下是否稳定
- `262K` 上下文是否能承载真实长文本请求
- `max_tokens` 的安全边界
- prompt cache 在单人多轮使用中是否工作
- 长时间顺序使用是否稳定

测试入口：

- 服务地址：`http://100.107.189.100:18343/v1`
- 模型名：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 运行配置：

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

---

## 2. 最终结论

### 2.1 可以确认成立的结论

- `thinking mode` 在当前服务上**可用**。
- OpenAI 兼容接口在部分请求上**正常返回**：
  - `message.content`
  - `message.reasoning_content`
- `262K` 上下文配置本身**能正常拉起**，而且能处理较长 prompt。
- 单人场景下，`max_tokens` 的最小安全值至少应为 **`128`**。
- prompt cache **确实在工作**，并且日志里能看到明显命中。

### 2.2 当前真正的问题

当前最大问题不是显存，也不是 `262K` 本身，而是：

- **在 thinking mode 下，只要 prompt 更像真实 coding / review / patch 任务，`llama-server` 很容易在最终返回 OpenAI chat 响应时抛 `500`。**

错误形态高度一致：

```text
Failed to parse input at pos XXXX:
```

重要的是：

- 从服务日志看，模型并不是没跑
- 它实际上已经完成了 prompt 处理和大量生成
- 然后才在响应整理阶段报错

所以本轮压测的核心发现是：

> 当前这套 `latest llama.cpp + Unsloth Qwen3.5-27B-UD-Q4_K_XL + thinking=true + OpenAI chat` 组合，对“简单问题”稳定，对“真实 coding 任务”不够稳定。

---

## 3. 结果概览

总用例数：`18`

- 成功：`6`
- 失败：`12`
- 成功率：`33.3%`

### 按类型拆分

- `smoke`：3 个里成功 2 个
- `boundary`：4 个里成功 2 个
- `context`：3 个里成功 1 个
- `cache`：3 个里成功 0 个
- `soak`：5 个里成功 1 个

---

## 4. 关键测试结果

### 4.1 基础 smoke

| 用例 | 结果 | prompt_tokens | 总耗时 |
| --- | --- | ---: | ---: |
| `smoke_math` | 200 | 17 | 3861 ms |
| `smoke_python_lru` | 200 | 27 | 17816 ms |
| `smoke_java_bugfix` | 500 | - | 24613 ms |

结论：

- 简单问题与简短 coding 请求可以成功。
- 一旦进入更像“真实工程问题”的表达方式，即使 prompt 很短，也可能触发 `500`。

---

### 4.2 `max_tokens` 安全边界

| 用例 | max_tokens | 结果 |
| --- | ---: | --- |
| `boundary_max_tokens_8` | 8 | 500 |
| `boundary_max_tokens_64` | 64 | 500 |
| `boundary_max_tokens_128` | 128 | 200 |
| `boundary_max_tokens_256` | 256 | 200 |

结论：

- thinking mode 下，`8` 和 `64` 都不安全。
- 当前最小稳定值是 **`128`**。
- 对 coding 场景，建议不要低于：
  - 保守值：`256`
  - 实用值：`512` 或 `1024`

---

### 4.3 长上下文能力

| 用例 | 结果 | prompt_tokens | 总耗时 | 生成速度 |
| --- | --- | ---: | ---: | ---: |
| `context_small` | 500 | - | 21854 ms | - |
| `context_medium` | 200 | 19728 | 46456 ms | 40.29 tok/s |
| `context_large` | 500 | - | 93592 ms | - |

结论：

- 中等规模长上下文已经被真实验证成功：
  - `prompt_tokens ≈ 19.7K`
  - thinking mode 正常
  - 返回成功
- 更大场景下，不是模型直接 OOM，也不是服务起不来，而是最终响应解析失败。

这说明：

- **容量不是当前第一瓶颈**
- **OpenAI chat 响应稳定性才是当前第一瓶颈**

---

## 5. GPU / 资源使用情况

采样总数：`523`

### 显存

- 最低显存占用：`22496 MiB`
- 最高显存占用：`22752 MiB`
- 平均显存占用：`22679.32 MiB`

这说明：

- 当前配置下，服务长期工作在 **22.5GB 左右显存占用**
- 基本贴近 24GB 卡上限，但没有出现显存爆炸
- 单人顺序场景下，这个占用是可工作的

### GPU 利用率

- 平均 GPU 利用率：`58.94%`
- 峰值 GPU 利用率：`100%`

### 显存带宽利用率

- 平均显存利用率：`52.33%`
- 峰值显存利用率：`97%`

### 功耗

- 平均功耗：`250.43 W`
- 峰值功耗：`435.99 W`

结论：

- 这是一套**高负载但可工作的单卡极限配置**
- 单人场景下没看到显存层面的直接失稳证据

---

## 6. cache 是否真的生效

从自动汇总 CSV 看，cache 轮都返回了 500，所以单看 HTTP 成败会误判为“cache 没用”。

但服务日志显示 cache 明确生效了：

```text
srv  get_availabl: updating prompt cache
srv   prompt_save:  - saving prompt with length 20487, total state size = 510.140 MiB
srv          load:  - found better prompt with f_keep = 0.949, sim = 0.999
srv        update:    - prompt ... 65952 tokens, checkpoints: 8, 2507.206 MiB
```

并且后续请求的耗时也出现下降：

- `cache_round_1`: `48916 ms`
- `cache_round_2`: `29272 ms`
- `cache_round_3`: `23813 ms`

所以更准确的结论是：

- **cache 在工作**
- **cache 提升了 prompt 处理效率**
- 但最终响应仍可能因为 server 解析问题返回 `500`

---

## 7. 500 的真实含义

本轮最容易被误解的一点是：

- `500` 并不等于模型没推理
- 也不等于显存不足
- 更不等于 thinking mode 完全不可用

日志里可以看到失败请求其实已经走完了大量步骤：

```text
prompt eval time = 283.42 ms / 499 tokens
eval time = 19065.02 ms / 768 tokens
total time = 19348.44 ms / 1267 tokens
slot release ...
srv operator(): got exception: {"error":{"code":500,"message":"Failed to parse input at pos 3282: ","type":"server_error"}}
```

这说明：

1. prompt 已处理
2. 模型已经生成了内容
3. 失败发生在更后面的响应整理/模板解析阶段

所以当前问题更像：

- **server 对 Qwen3.5 thinking 输出的结构化解析不稳定**

而不是：

- 模型质量问题
- 显存问题
- CUDA 问题

---

## 8. 单人场景是否适合继续使用

### 8.1 适合的情况

这套配置适合：

- 单人顺序使用
- 大上下文阅读
- 研究 thinking mode
- 简单问题、分析类问题
- 对 `reasoning_content` 有明确需求

### 8.2 不适合直接作为稳定 coding API 的情况

这套配置当前**不适合**直接作为“稳定生产级 precise coding API”的原因是：

- 很多真实 coding / review prompt 会返回 `500`
- 即使模型实际上已经做了推理

如果你的目标是：

- 高成功率
- 稳定的 OpenAI chat 接口
- 长时间连续 coding 不中断

那当前线上默认配置不够稳。

---

## 9. 对当前配置的判断

### 当前配置的优点

- 最新 `llama.cpp`
- 262K 上下文
- 单 slot，适合单人
- q4_0 KV，显存控制合理
- thinking mode 已经被证明确实可用

### 当前配置的缺点

- OpenAI chat 接口对真实 coding 请求不够稳
- `reasoning=true` 下更容易触发 server 解析失败

---

## 10. 最终建议

### 方案 A：继续保留当前配置，作为“研究型 / 分析型单人服务”

保留当前线上：

- `262K`
- `thinking=true`
- `np=1`

适合：

- 长文档分析
- 代码阅读
- reasoning 展示

但需要接受：

- 某些 coding 请求会 500

### 方案 B：如果目标是“稳定 coding”，建议切回 non-thinking

如果你优先要：

- API 稳定
- coding 成功率
- 少折腾客户端重试

那更稳的是：

- 保持其它参数不变
- 只把：

```bash
--chat-template-kwargs '{"enable_thinking": false}'
```

加回去

这会牺牲显式 reasoning 输出，但更接近稳定工作模式。

---

## 11. 工件位置

### 原始结果

- [`single_user_bench_results.csv`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/single_user_bench_results.csv)
- [`single_user_bench_results.json`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/single_user_bench_results.json)
- [`single_user_bench_meta.json`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/single_user_bench_meta.json)

### 采样结果

- [`gpu_samples.csv`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/gpu_samples.csv)
- [`vmstat.log`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/vmstat.log)

### 自动汇总

- [`single_user_bench_report.md`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/single_user_bench_report.md)

### 本详细报告

- [`single_user_bench_detailed_report.md`](/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench/single_user_bench_detailed_report.md)

