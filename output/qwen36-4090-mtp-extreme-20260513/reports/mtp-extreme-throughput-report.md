# Qwen3.6 27B MTP 4090 极限吞吐测试报告

## 结论

本轮在已修复格式参数的前提下测试 MTP `--spec-draft-n-max=4` 的极限吞吐。结论：

1. 单流长输出是最高吞吐路径：8192 token 档平均 77.47 tok/s，最高单次 87.67 tok/s。
2. `-np 2/4` 并发总吞吐稳定在约 65 tok/s，没有超过单流长输出峰值；适合服务并发，不适合追求单卡极限 tok/s。
3. prompt cache 对长 prompt 重复请求收益极大：2000-word prompt 下，cache-on 的重复请求平均 4.93s，cache-off 平均 18.18s，约 3.7x 延迟改善。
4. 全部有效测试均无 `<think>` 泄漏，说明 `-rea off` 且不传 `--reasoning-format none` 的格式修复成立。

## 固定配置

- 机器：4090 `192.168.10.29`
- llama.cpp：`/home/hhtele/llama.cpp-mtp-unsloth-20260513`
- 模型：`/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf`
- 固定参数：

```bash
-ngl 99 -c 32768 -fa on
-ctk q4_0 -ctv q4_0
--spec-type mtp --spec-draft-n-max 4
-rea off
--temp 0 --top-p 1
```

明确未使用：

```bash
--reasoning-format none
```

## 单流长输出

Lane：`mtp_spec4_np1_single_long`

| 输出长度 | 次数 | Avg tok/s | P50 tok/s | 单次 elapsed |
| ---: | ---: | ---: | ---: | --- |
| 2048 | 2 | 62.00 | 62.00 | 34.28s, 31.88s |
| 4096 | 2 | 62.87 | 62.87 | 63.42s, 66.97s |
| 8192 | 2 | 77.47 | 77.47 | 121.79s, 93.44s |

总体：

| 指标 | 结果 |
| --- | ---: |
| 成功率 | 6/6 |
| Avg tok/s | 67.44 |
| Median tok/s | 64.41 |
| P95 elapsed | 121.79s |
| think leak | 0 |
| 平均 MTP acceptance | 0.9790 |

判断：单流 8192 token 是当前“极限 tok/s”最佳测试形态；长输出摊薄了请求固定开销和 prefill 影响。

## 并发矩阵

### `-np 2`

Lane：`mtp_spec4_np2_concurrency`

| 输出长度 | batch 次数 | Batch Avg tok/s | Batch P50 tok/s | 单请求 P50 tok/s |
| ---: | ---: | ---: | ---: | ---: |
| 2048 | 3 | 62.59 | 62.26 | 31.89 |
| 4096 | 3 | 67.16 | 67.18 | 33.79 |

总体：

| 指标 | 结果 |
| --- | ---: |
| 成功率 | 12/12 |
| Avg batch tok/s | 64.87 |
| Median batch tok/s | 65.29 |
| P95 elapsed | 121.94s |
| think leak | 0 |
| 平均 MTP acceptance | 0.9735 |

### `-np 4`

Lane：`mtp_spec4_np4_concurrency`

| 输出长度 | batch 次数 | Batch Avg tok/s | Batch P50 tok/s | 单请求 P50 tok/s |
| ---: | ---: | ---: | ---: | ---: |
| 1024 | 3 | 62.68 | 62.58 | 15.88 |
| 2048 | 3 | 67.48 | 67.59 | 17.18 |

总体：

| 指标 | 结果 |
| --- | ---: |
| 成功率 | 24/24 |
| Avg batch tok/s | 65.08 |
| Median batch tok/s | 64.56 |
| P95 elapsed | 124.93s |
| think leak | 0 |
| 平均 MTP acceptance | 0.9670 |

并发判断：

- `-np 2` 和 `-np 4` 的总吞吐都在约 65 tok/s。
- `-np 4` 没有带来更高总吞吐，单请求延迟明显变差。
- 如果目标是在线服务吞吐/多用户公平性，可用 `-np 2`。
- 如果目标是单卡极限 benchmark 数字，优先 `-np 1` 长输出。

## Prompt Cache

### 失败边界

`prompt_words=5000` 生成约 `60051` prompt tokens，超过 `32768` context，cache on/off 都返回 400：

```text
request (60051 tokens) exceeds the available context size (32768 tokens)
```

这条记录保留为上下文边界证据，不计入 cache 性能结论。

### 有效对照：2000 words

| 模式 | shared rep1 | shared rep2-5 avg | unique avg | 成功率 | think leak |
| --- | ---: | ---: | ---: | ---: | ---: |
| cache on | 18.97s | 4.93s | 5.12s | 10/10 | 0 |
| cache off | 19.02s | 18.18s | 18.02s | 10/10 | 0 |

吞吐摘要：

| Lane | Avg tok/s | Median tok/s |
| --- | ---: | ---: |
| `mtp_spec4_np1_prompt_cache_on_2000w` | 42.60 | 44.61 |
| `mtp_spec4_np1_prompt_cache_off_2000w` | 12.67 | 13.24 |

判断：

- cache-on 首次 shared prompt 与 cache-off 接近，说明首次 prefill 成本真实存在。
- cache-on 后续 shared prompt 从约 18s 降到约 5s，重复长 prompt 场景收益非常明显。
- unique prompt 在 cache-on 下也较快，日志显示 prompt cache 有 LCP 相似度命中；但该 prompt 构造有大量共享前缀，不能代表完全随机长 prompt。

## 极限推荐

### 追求最高 tok/s

```bash
./build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias qwen36-mtp-udq4xl \
  -ngl 99 -c 32768 -np 1 -fa on \
  -ctk q4_0 -ctv q4_0 \
  --spec-type mtp --spec-draft-n-max 4 \
  -rea off \
  --temp 0 --top-p 1 \
  --host 0.0.0.0 --port 18801
```

测试形态：4096/8192 token 长输出。

### 追求在线并发

```bash
-np 2
```

不要默认上 `-np 4`，除非目标是同时服务 4 个长请求且能接受单请求延迟翻倍。

### 追求长 prompt 重复请求

保留默认 prompt cache，不要加：

```bash
--no-cache-prompt
```

适用场景：固定系统 prompt、固定长文档、多轮围绕同一上下文提问。

## 已知限制

- 本轮没有测试 `-np 8`：4090 24GB 下 slot context 会进一步变小，且 `-np 4` 已未提升总吞吐。
- 本轮没有测试 16K 输出：单次耗时过长，且 8192 已能看出长输出吞吐趋势。
- prompt cache 的 unique 组仍有大量共享结构，不能视为完全随机 prompt。

## 记录位置

- Raw：`output/qwen36-4090-mtp-extreme-20260513/raw/`
- Logs：`output/qwen36-4090-mtp-extreme-20260513/logs/`
- Script：`scripts/qwen4090_mtp_extreme_eval.py`

## 恢复状态

- 实验进程：已停止。
- systemd：`qwen35-35b-a3b-uncensored.service` 已恢复为 `active`。
- 端口：`http://127.0.0.1:18343/v1/models` 返回原模型。
- GPU：恢复后约 `21870 MiB used / 2347 MiB free`。
