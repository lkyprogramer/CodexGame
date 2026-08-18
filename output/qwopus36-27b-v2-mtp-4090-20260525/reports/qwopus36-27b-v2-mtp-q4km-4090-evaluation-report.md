# Qwopus3.6-27B-v2-MTP Q4_K_M 4090 Evaluation Report

生成时间：2026-05-25

## 结论

本轮不建议直接替换当前生产基线 `Qwen3.6-27B-UD-Q4_K_XL`，但建议把 `Qwopus3.6-27B-v2-MTP-Q4_K_M` 作为 OpenClaw 灰度候选继续验证。

关键原因：

- `Qwopus Q4_K_M + draft-mtp n=2 p-min=0.75` 在 128k 单并发全部 10 个 case 成功，strict JSON、patch、short output 通过率 100%。
- 128k 长输出 `long_generation_2048` decode 达到 `53.72 tok/s`，高于当前最佳基线 `Qwen n=4` 的 `50.67 tok/s`，提升约 `6.0%`，但未达到本轮设定的 `>=10%` 直接替换门槛。
- 128k 峰值显存更低：`Qwopus n=2` 为 `20.94 GiB`，`Qwen n=4` 为 `22.30 GiB`，节省约 `1.36 GiB`，对 24GB 4090 有实际余量价值。
- prompt cache warm 命中正常，`cache_n=65622 / prompt_tokens=65626`，冷启动约 `35.81s`，热命中约 `0.73s`。
- 人工格式分和质量分与当前基线持平：128k 平均格式分 `4.85`，平均质量分 `4.70`。

推荐灰度配置：

```bash
/home/hhtele/llama.cpp-master-qwopus-20260525/build/bin/llama-server \
  -m /data/models/qwen/qwopus/Qwopus3.6-27B-v2-MTP-Q4_K_M.gguf \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --cache-reuse 256 \
  --slot-prompt-similarity 0.10 \
  --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --spec-draft-p-min 0.75
```

## 环境与构建证据

4090 访问方式：`192.168.10.29` 直连。

模型下载：

- 源：`hf-mirror.com`
- 目标：`/data/models/qwen/qwopus/Qwopus3.6-27B-v2-MTP-Q4_K_M.gguf`
- 文件大小校验：`16810713312` bytes
- aria2c 下载结果：`OK`
- 平均下载速度：`26 MiB/s`

llama.cpp：

- 构建目录：`/home/hhtele/llama.cpp-master-qwopus-20260525`
- commit：`549b9d84330c327e6791fa812a7d60c0cf63572e`
- version：`version: 1 (549b9d8)`
- CUDA：`12.3.107`
- 架构：`CMAKE_CUDA_ARCHITECTURES=89`
- 关键参数存在：`--spec-type draft-mtp`、`--spec-draft-n-max`、`--spec-draft-p-min`、`--cache-prompt`、`--chat-template`、`--ctx-size`
- 最新 help 中 `--spec-draft-p-min` 默认值仍是 `0.00`，本轮所有 p-min 新策略测试均显式传入 `0.75`。

构建参数：

```bash
cmake -S . -B build \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_BUILD_WEBUI=OFF \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_CUDA_GRAPHS=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_BUILD_TYPE=Release
```

## Phase 0：当前 Qwen 基线健康门禁

最新 llama.cpp binary 对当前生产基线无明显 regression，两个 32k smoke lane 全部通过，因此继续进入 Qwopus 测试。

| Lane | ctx | MTP | p-min | pass | avg decode tok/s | long decode tok/s | accept | fmt | quality | peak VRAM MiB |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| qwen_udq4xl_draft_n2_p075_ctx32 | 32768 | 2 | 0.75 | yes | 61.38 | 47.76 | 0.945 | 4.86 | 4.71 | 19638 |
| qwen_udq4xl_draft_n4_p075_ctx32 | 32768 | 4 | 0.75 | yes | 63.89 | 48.35 | 0.957 | 4.86 | 4.71 | 19954 |

## Phase 1：Qwopus 32k 参数筛选

| Lane | MTP | p-min | pass | avg decode tok/s | long decode tok/s | accept | fmt | quality | peak VRAM MiB | 结论 |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| no_spec | none | N/A | yes | 52.30 | 46.81 | N/A | 4.86 | 4.71 | 17224 | 作为无 MTP 参考 |
| draft_n1_p075 | 1 | 0.75 | yes | 57.86 | 49.49 | 0.984 | 4.86 | 4.71 | 18438 | 晋级 128k |
| draft_n2_p075 | 2 | 0.75 | yes | 61.87 | 48.59 | 0.969 | 4.86 | 4.71 | 18596 | 晋级 128k |
| draft_n3_p075 | 3 | 0.75 | yes | 63.28 | 47.46 | 0.961 | 4.86 | 4.71 | 18752 | 平均快但长输出不如 n1/n2 |
| draft_n4_p075 | 4 | 0.75 | yes | 62.55 | 46.93 | 0.932 | 4.86 | 4.71 | 18908 | 不优于 n2 |
| draft_n6_p075 | 6 | 0.75 | yes | 56.82 | 44.19 | 0.901 | 4.86 | 4.71 | 19220 | 退化，淘汰 |
| draft_n4_p000 | 4 | 0.00 | yes | 74.84 | 66.36 | 0.620 | 4.86 | 4.71 | 18908 | 速度最高但 acceptance 低于 0.65 门槛，淘汰 |

观察：

- `p-min=0.0` 复现了旧行为，短测吞吐最高，但 draft acceptance 只有 `0.620`，低于本轮进入 128k 的 `0.65` 门槛；不作为 OpenClaw 稳定基座候选。
- `n=6 p-min=0.75` 在本机 4090 上没有收益，平均 decode、长输出 decode 都低于 `n=2/n3/n4`，且显存更高。
- 按长输出表现、质量和 acceptance 综合筛选，进入 128k 的配置为 `n=1 p-min=0.75` 与 `n=2 p-min=0.75`。

## Phase 2：128k OpenClaw 候选验证

所有 128k lane 均为单并发 `-np 1`，开启 `--cache-prompt --cache-ram 2048 --cache-reuse 256 --slot-prompt-similarity 0.10`。

| Lane | Model | MTP | pass | avg decode tok/s | long 2048 decode tok/s | accept | fmt | quality | peak VRAM MiB | max power W |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| qwen_udq4xl_draft_n2_p075_ctx128 | Qwen UD-Q4_K_XL | 2 | yes | 61.08 | 49.55 | 0.959 | 4.85 | 4.70 | 21984 | 439.87 |
| qwen_udq4xl_draft_n4_p075_ctx128 | Qwen UD-Q4_K_XL | 4 | yes | 67.17 | 50.67 | 0.962 | 4.85 | 4.70 | 22304 | 442.15 |
| qwopus_q4km_draft_n1_p075_ctx128 | Qwopus Q4_K_M | 1 | yes | 56.66 | 51.03 | 0.988 | 4.85 | 4.70 | 20782 | 444.60 |
| qwopus_q4km_draft_n2_p075_ctx128 | Qwopus Q4_K_M | 2 | yes | 61.05 | 53.72 | 0.956 | 4.85 | 4.70 | 20940 | 438.14 |

128k prompt cache 对比：

| Lane | prompt tokens | cold elapsed s | cold prompt ms | warm elapsed s | warm prompt ms | warm cache_n | speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen n2 | 65626 | 35.06 | 34292 | 0.767 | 120 | 65622 | 45.72x |
| Qwen n4 | 65626 | 35.29 | 34695 | 0.674 | 121 | 65622 | 52.36x |
| Qwopus n1 | 65626 | 35.60 | 34790 | 0.752 | 111 | 65622 | 47.33x |
| Qwopus n2 | 65626 | 35.81 | 35017 | 0.732 | 111 | 65622 | 48.90x |

128k 结论：

- Qwopus n2 的长输出 `2048` decode 是本轮最高：`53.72 tok/s`。
- 与当前最佳 Qwen n4 相比，Qwopus n2 长输出提升约 `6.0%`，峰值显存降低约 `1364 MiB`。
- prompt cache warm 命中质量正常，`cache_n` 与 prompt tokens 基本一致。
- Qwopus n2 的平均 decode 低于 Qwen n4，说明收益集中在长输出场景，不是全场景吞吐替代。

## 人工评分与失败样例

评分规则：

- 格式分：JSON、patch、无 markdown fence 泄漏、无空输出、无 slash 重复、无 think leak。
- 质量分：回答是否满足任务语义，代码审查是否指出关键问题，长输出是否连贯。

结果：

- 本轮无空输出、无 `/` 重复、无 think leak、无 markdown fence 泄漏。
- strict JSON、patch、short output 在 Phase 0/1/2 均通过。
- 长输出任务统一给 `4.0` 质量分，主要原因是内容可用但细节密度一般；Qwen 与 Qwopus 没有拉开质量差距。
- 未发现足以否决 Qwopus 的格式失败样例。

## Acceptance Criteria 对照

| 条件 | 结果 |
|---|---|
| 128k 单并发所有 case 请求成功 | 通过，Qwopus n1/n2 均 10/10 |
| strict JSON、patch、short output 通过率 100% | 通过 |
| 平均质量分不低于当前 Qwen baseline 0.1 分以上差距 | 通过，均为 4.70 |
| long_generation_1024/2048 decode 比当前 baseline 高至少 10%，或质量相等时 wall time 明显更低 | 未完全通过；Qwopus n2 对 Qwen n4 的 long 2048 提升约 6%，未达 10% |
| 128k prompt cache warm cache_n 接近 prompt tokens | 通过，65622/65626 |
| 128k warm speedup 不低于当前 baseline 的 80% | 通过，Qwopus n2 为 48.90x，Qwen n4 为 52.36x |
| 峰值显存不高于当前 Qwen baseline；若更高必须有明确质量收益 | 通过，Qwopus n2 低约 1.36GB |
| 测试结束后生产服务完整恢复 | 通过 |

## 生产恢复验证

测试 wrapper 在退出时恢复了生产服务，随后又做了一次独立复核：

- `systemctl is-active openclaw-qwen36-mtp4-128k.service`：`active`
- `systemctl is-enabled openclaw-qwen36-mtp4-128k.service`：`enabled`
- `curl http://127.0.0.1:18343/v1/models`：返回当前生产模型 `openclaw/Qwen3.6-27B-MTP-Q4XL`
- `curl -H "Authorization: Bearer <token>" http://127.0.0.1:28343/v1/models`：HTTP `200`
- 无 token 访问 `28343`：HTTP `401`
- `llama-server.*19343` 残留进程：`0`

## 文件与原始记录

本地输出目录：

```text
/Users/luo/Documents/github/CodexGame/output/qwopus36-27b-v2-mtp-4090-20260525
```

关键文件：

- 测试报告：`reports/qwopus36-27b-v2-mtp-q4km-4090-evaluation-report.md`
- 远端准备脚本：`remote/prepare_qwopus_llamacpp.sh`
- 远端评测脚本：`remote/qwopus4090_eval.py`
- 远端 wrapper：`remote/run_qwopus4090_eval_wrapper.sh`
- 汇总结果：`raw/remote-copy/results/summary.json`
- 门禁结果：`raw/remote-copy/results/gate.json`
- 构建与下载日志：`raw/remote-copy/logs/prepare.log`
- 恢复日志：`raw/remote-copy/logs/restore-status.log`

## 后续建议

1. 保留当前生产 `Qwen UD-Q4_K_XL n=4 p-min=0.75`，不要直接替换。
2. 新增一个非生产灰度服务端口运行 `Qwopus Q4_K_M n=2 p-min=0.75`，只接 OpenClaw 长输出/长上下文压测流量。
3. 下一轮重点测试真实 OpenClaw agent trace：多轮 JSON tool、patch review、长历史增量缓存、重复相似 prompt 的 cache reuse 稳定性。
4. 如果要追求极限吞吐，可单独把 `n=4 p-min=0.0` 作为实验 lane 跑更长质量集；它速度最高，但本轮 acceptance 未达稳定门槛，不应直接进生产。
