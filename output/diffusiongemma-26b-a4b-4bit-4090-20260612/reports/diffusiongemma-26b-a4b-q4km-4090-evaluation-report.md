# DiffusionGemma 26B-A4B Q4_K_M 4090 评测报告

测试对象：`unsloth/diffusiongemma-26B-A4B-it-GGUF` 的 `diffusiongemma-26B-A4B-it-Q4_K_M.gguf`  
测试机器：RTX 4090 24GB，`192.168.10.29`  
输出目录：`/Users/luo/Documents/github/CodexGame/output/diffusiongemma-26b-a4b-4bit-4090-20260612`

## 结论

不建议把当前这套 DiffusionGemma Q4_K_M 作为 OpenClaw 或 OpenAI API 推理基座。

它在 4090 上可以跑通短 prompt，并且 generation-only 速度有一定优势：`-n 256/512/1024/2048` 的有效生成速度中位数分别为 `108.3 / 78.3 / 66.6 / 63.1 tok/s`。但这不是严格端到端 server 吞吐：本轮使用的是 `llama-diffusion-cli` 独立进程，端到端包含模型加载后只有 `22.1 / 32.3 / 41.3 / 43.2 tok/s`。

真正阻断点有三个：

- 目前只能用 PR `#24423` 的 `llama-diffusion-cli`，不能用标准 `llama-server` 或 OpenAI API。
- CLI 裸输出会泄漏 `<|channel>thought` / `<channel|>`，不适合作为 agent JSON/patch 场景的直接后端。
- 长 prompt 不成立。默认 `-ub` 下 4k/16k prompt 要求把整个 `[prompt | canvas]` 放进一个 ubatch；按要求增大 `-ub` 后，最小 4k retry 也需要额外分配 `8280 MiB` compute buffer 并 OOM。64k/128k 级别需要 `74520 MiB` / `132480 MiB` 级别 compute buffer，24GB 4090 不可行。

最终判断：短输出 demo 可以继续观察；生产型长上下文、agent trace、OpenAI API、prompt cache 评测都不具备落地条件。本轮不能证明它相对非 diffusion 4-bit 模型有 `>=2x` 大幅优势。

## 部署与下载

只下载了 4-bit Q4_K_M，没有下载 BF16/Q5/Q6/Q8，也没有下载非 diffusion 对照模型。

模型路径：

```bash
/data/models/gemma/diffusiongemma/diffusiongemma-26B-A4B-it-Q4_K_M.gguf
```

下载命令使用 `hf-mirror.com` + `aria2c`：

```bash
aria2c -c -x 8 -s 8 -k 16M \
  -d /data/models/gemma/diffusiongemma \
  -o diffusiongemma-26B-A4B-it-Q4_K_M.gguf \
  "https://hf-mirror.com/unsloth/diffusiongemma-26B-A4B-it-GGUF/resolve/main/diffusiongemma-26B-A4B-it-Q4_K_M.gguf"
```

下载证据：

- Range 支持：`Accept-Ranges: bytes`
- `Content-Length`: `16806810336`
- `x-linked-size`: `16806810336`
- `stat` 文件大小：`16806810336`
- aria2 平均速度：`26 MiB/s`
- 下载完成时间：约 `10m17s`

原始日志：

```text
raw/remote-copy/logs/prepare.log
```

## llama.cpp 构建

远端 `git clone` GitHub 失败，错误为：

```text
GnuTLS recv error (-110): The TLS connection was non-properly terminated
```

因此改成本机下载 PR tarball 后上传到 4090。PR head SHA：

```text
10a2613aa0b2686f7d0608520c4f0ea05219df03
```

构建目录：

```bash
/home/hhtele/llama.cpp-diffusiongemma-pr24423-20260612
```

构建命令：

```bash
cmake -S . -B build \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j --target llama-diffusion-cli
```

构建结果：

- CUDA toolkit：`12.3.107`
- GPU arch：`89`
- target：`llama-diffusion-cli`
- build：成功

`llama-diffusion-cli --help` 证据已保存：

```text
raw/remote-copy/logs/llama-diffusion-cli-help.txt
```

关键参数支持：

- `-c, --ctx-size`
- `-n, --predict`
- `-ub, --ubatch-size`
- `-fa, --flash-attn`
- `-ctk, --cache-type-k`
- `-ctv, --cache-type-v`
- `-f, --file`
- `--perf`
- `-ngl, --gpu-layers`

## 测试配置

基础命令：

```bash
./build/bin/llama-diffusion-cli \
  -m /data/models/gemma/diffusiongemma/diffusiongemma-26B-A4B-it-Q4_K_M.gguf \
  -ngl 99 \
  -c 131072 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --perf \
  -n <tokens> \
  -f <prompt_file>
```

没有使用 `llama-server`，因为该模型当前需要专用 `llama-diffusion-cli`。

指标口径：

- `generation tok/s`：CLI stdout 的 `throughput: xx tok/s`，只统计 diffusion generation。
- `e2e tok/s`：实际生成 tokens / Python 子进程端到端耗时，包含模型加载、上下文初始化和生成。
- `in-step parallel tok/s`：CLI 的 diffusion 内部并行指标，不作为跨模型主对比指标。
- 有效 case 要求：退出码 0、无 `E error`、stdout 有 throughput 行、输出非空、marker 命中。

注意：原始 `summary.json` 的 `ok_count` 对长 prompt 不可靠，因为 PR runner 在部分错误场景会返回 0 并把错误写到 stdout。本报告使用二次解析后的 `valid` 口径。

## Smoke

Smoke 命令跑通：

```bash
-n 256 -f smoke_n256.txt
```

结果：

- 退出码：`0`
- 输出非空：是
- marker 命中：是
- generation speed：`108.3 tok/s` 量级
- 峰值显存：`20618 MiB`
- 未出现 CUDA OOM

但 stdout 中出现 raw thinking channel：

```text
<|channel>thought
...
<channel|>
```

这与 Hugging Face 讨论区用户观察一致：当前 bare CLI 会泄漏 raw channel token。

## 输出长度速度

短 prompt，1 次 warmup + 3 次正式测量；下表只统计正式测量。

| `-n` | valid/total | median generated tokens | median generation tok/s | median e2e generated tok/s | median elapsed s | max VRAM MiB | max power W | max temp C |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3/3 | 256 | 108.3 | 22.06 | 11.60 | 20618 | 186.82 | 58 |
| 512 | 3/3 | 512 | 78.3 | 32.30 | 15.85 | 20986 | 191.24 | 60 |
| 1024 | 3/3 | 1024 | 66.6 | 41.26 | 24.82 | 21728 | 188.14 | 61 |
| 2048 | 3/3 | 1280 | 63.1 | 43.23 | 29.61 | 22916 | 190.41 | 63 |
| 4096 | 0/3 | - | - | - | - | - | - | - |

关键观察：

- `-n 2048` 并没有实际生成 2048 tokens，中位数只有 `1280`，stdout 显示 entropy-bound 提前停止。
- `-n 4096` 三次正式测量全部失败，退出码 `-6`，stderr 显示在 diffusion init / CUDA 分配阶段失败。
- 有效输出的峰值显存最高到 `22916 MiB`，已经非常接近 24GB 4090 的生产安全边界。

## Prompt 长度速度

固定 `-n 1024`。第一轮默认/自动 `ubatch` 后，4k/16k 提示需要更大 `-ub`，64k/128k 因合成 prompt tokenizer 后超过 `131072` context。随后做了 focused retry：按错误日志估算真实 token 膨胀比例，降低 prompt 构造目标，并显式设置 `-ub`。

第一轮有效结果：

| target prompt | cold valid | warm valid | cold generation tok/s | warm generation tok/s | cold e2e tok/s | warm e2e tok/s | max VRAM MiB | failure |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | yes | yes | 54.3 | 54.9 | 36.57 | 36.34 | 21726 | - |
| 1024 | yes | yes | 21.6 | 21.5 | 17.03 | 16.94 | 22548 | - |
| 4096 | no | no | - | - | - | - | 20922 | needs larger `-ub` |
| 16384 | no | no | - | - | - | - | 17816 | needs larger `-ub` |
| 65536 | no | no | - | - | - | - | 17816 | input too long |
| 131072 | no | no | - | - | - | - | 20922 | input too long |

补测结果：

| target | retry `-ub` | result | stderr 关键点 |
|---:|---:|---|---|
| 4k | 8192 | OOM | allocating `8280.00 MiB` compute buffer failed |
| 16k | 32768 | OOM | allocating `33120.00 MiB` compute buffer failed |
| 64k | 73728 | OOM | allocating `74520.00 MiB` compute buffer failed |
| 128k | 131072 | OOM | allocating `132480.00 MiB` compute buffer failed |

结论：当前 PR runner 对 DiffusionGemma 需要全 prompt + canvas 在一个 ubatch 中处理，长 prompt 的 compute buffer 随 `-ub` 近似线性膨胀。24GB 4090 上可用的有效 prompt 长度只有 1k 级别，不能支撑 16k/64k/128k 长上下文测试。

## 组合矩阵

| prompt target | `-n` | valid/total | median generated tokens | median generation tok/s | median e2e tok/s | max VRAM MiB | failure |
|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 256 | 2/2 | 256 | 97.4 | 21.76 | 20620 | - |
| 128 | 1024 | 2/2 | 1024 | 59.3 | 38.71 | 21730 | - |
| 4096 | 1024 | 0/2 | - | - | - | - | needs larger `-ub`; retry OOM |
| 16384 | 1024 | 0/2 | - | - | - | - | needs larger `-ub`; retry OOM |
| 65536 | 1024 | 0/2 | - | - | - | - | input too long; retry OOM |
| 65536 | 2048 | 0/2 | - | - | - | - | input too long; retry OOM |
| 131072 | 1024 | 0/2 | - | - | - | - | input too long; retry OOM |

## Prompt Cache / Diffusion KV Cache

没有观察到可用的 cold/warm prompt cache 收益：

- 128 prompt：cold `54.3 tok/s`，warm `54.9 tok/s`
- 1k prompt：cold `21.6 tok/s`，warm `21.5 tok/s`
- 4k 以上：无有效生成结果

原因限制：

- 本轮是独立 CLI 进程，不是常驻 server slot；不能等价验证 OpenAI server 的 prompt cache。
- 当前 CLI 没有标准 OpenAI API，也没有 `llama-server` 的 slot/LRU 复用语义。
- 长 prompt 无法有效进入生成阶段，因此无法测试 64k/128k warm cache。

## 质量与格式

短 prompt 输出内容可读，但格式不适合 agent：

- 泄漏 raw thinking channel：`<|channel>thought`、`<channel|>`。
- 输出中包含先验分析/自检段，不是干净 assistant response。
- 对 JSON tool、patch review、OpenClaw trace 这类严格格式场景不合格。

人工质量结论：

| 维度 | 分数 | 说明 |
|---|---:|---|
| 短回答可读性 | 3.5 / 5 | 能解释主题，但包含思考泄漏 |
| Agent 格式稳定性 | 1.0 / 5 | 不适合 JSON-only / patch-only |
| 长上下文可用性 | 0.0 / 5 | 4k 以上无有效结果 |
| 部署成熟度 | 1.0 / 5 | CLI-only，无标准 server/API |

## Online 4-bit Baseline 对比

没有找到严格满足“RTX 4090 + Gemma 4 26B-A4B + Q4/GGUF + llama.cpp + 相同 prompt/output”的公开非 diffusion baseline。因此不做严格倍数结论。

可参考资料：

- Google 官方介绍称 DiffusionGemma 在专用 GPU 上最高可到 `4x`，并给出 H100 `1000+ tok/s`、RTX 5090 `700+ tok/s` 的说法；这不是 4090 Q4_K_M 条件。
- Unsloth 模型页明确：该 GGUF 当前需要 DiffusionGemma PR `#24423` 和 `llama-diffusion-cli`，标准 `llama-cli` / `llama-server` 不能生成；Q4_K_M 是 16GB 量级、适合单 24GB GPU。
- Hugging Face discussion 有用户记录：Q4_K_M fits one 4090，但 CLI-only 且裸 CLI 会泄漏 raw channel token。
- Reddit 上 `gemma-3-27b-it-Q4_K_M.gguf` 的 4090 tuned baseline 是 TG `54.38 t/s`，但这是 Gemma 3 27B，不是 Gemma 4 26B-A4B，也不是同 prompt。
- Ollama 社区模型卡对 Gemma 4 26B Q4_K_M 4090 tag 写到 Ada 上约 `150 tok/s class`，但它是模型卡描述，不是可复现实测报告。

本机历史 AR 参考：

- `Qwopus3.6-27B-v2-MTP Q4_K_M` 128k long 2048 decode：`53.72 tok/s`
- 当前 Qwen baseline 128k long 2048 decode：`50.67 tok/s`

与这些参考相比，本轮 DiffusionGemma 的 generation-only `63.1 tok/s` 有小幅优势，但：

- `-n 2048` 实际只生成 `1280 tokens`
- 端到端 CLI 吞吐约 `43.2 tok/s`
- 不能长上下文
- 不能 OpenAI server
- 有格式泄漏

因此不能称为“大幅提升”。

## 生产恢复验证

两轮测试都临时停止了：

```text
openclaw-qwen36-mtp4-128k.service
```

测试结束后恢复验证：

- `systemctl is-active openclaw-qwen36-mtp4-128k.service`: `active`
- `systemctl is-enabled openclaw-qwen36-mtp4-128k.service`: `enabled`
- `curl http://127.0.0.1:18343/v1/models`: `200`，返回 `openclaw/Qwen3.6-27B-MTP-Q4XL`
- `curl -H "Authorization: Bearer $QWEN_NGINX_TOKEN" http://127.0.0.1:28343/v1/models`: `200`
- 无 token 访问 `28343`: `401`
- `llama-diffusion-cli` / `llama-server.*19343` 残留进程：`0`

恢复日志：

```text
raw/remote-copy/logs/restore-status.log
raw/remote-copy/logs/retry-restore-status.log
```

## 外部资料

- Unsloth GGUF model page: https://huggingface.co/unsloth/diffusiongemma-26B-A4B-it-GGUF
- llama.cpp PR #24423: https://github.com/ggml-org/llama.cpp/pull/24423
- Google DiffusionGemma announcement: https://blog.google/innovation-and-ai/technology/developers-tools/diffusion-gemma-faster-text-generation/
- llama.cpp diffusion README: https://github.com/ggml-org/llama.cpp/blob/master/examples/diffusion/README.md
- HF discussion, 2x4090 notes: https://huggingface.co/unsloth/diffusiongemma-26B-A4B-it-GGUF/discussions/2
- Gemma 3 27B Q4_K_M 4090 public baseline reference: https://www.reddit.com/r/LocalLLaMA/comments/1lgcbyh/performance_comparison_on_gemma327bitq4_k_m_on/
- Gemma 4 26B Ollama community card reference: https://ollama.com/odytrice/gemma4-26b%3A5090
