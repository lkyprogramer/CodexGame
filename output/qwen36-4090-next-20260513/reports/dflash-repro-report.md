# DFlash 32K no-compression 复现报告

## 结论

本轮没有复现上一轮的 HTTP 500，但复现了 DFlash no-compression 在 32K 长上下文下的质量失败：请求返回 200，但只输出 `!`，未命中 `NEEDLE_CODE_4090_MTP_DFLASH`。因此 DFlash 标准路径仍不能作为长上下文方案。

## 测试配置

- Lucebox：`/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash`
- 端口：`18680`
- 模型：`/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- draft：`/data/models/qwen/dflash-draft/model.safetensors`
- 参数：`--budget 26 --max-ctx 32768 --ctk tq3_0 --ctv tq3_0 --fa-window 2048 --prefix-cache-slots 0 --prefill-cache-slots 0`
- PFlash：off

## 结果

| Case | HTTP | 输出 | expected_found | elapsed | 评分 |
| --- | --- | --- | --- | ---: | ---: |
| dflash_niah_1200_words | 200 | `!` | false | 31.50s | 1/5 |

日志证据：

```text
prompt_tokens=31250
compression_fired=false
raw_tokens=1
visible_tokens=1
raw_first_token_ids=[0]
read_eof=true
```

## 记录位置

- Raw：`output/qwen36-4090-next-20260513/raw/dflash_no_compression_32k_repro.*`
- Log：`output/qwen36-4090-next-20260513/logs/dflash_no_compression_32k_repro.log`

## 最终判断

DFlash no-compression 的问题从“HTTP 500”收敛为“长上下文生成退化为单 token `!`”。下一步应从 `read_eof=true`、token id `[0]`、32K prompt 下 daemon 生成提前 EOF 三个点定位。
