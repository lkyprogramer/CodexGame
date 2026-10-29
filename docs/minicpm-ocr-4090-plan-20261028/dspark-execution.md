# MiniCPM-OCR-1.0 DSpark 执行依据

2026-10-29。**已核实锁定源码和文件元数据；真实 GPU DSpark 尚未运行。** 本文件仅补充标准解码之后的 DSpark 实验入口。实际结果由 [执行报告](execution-report.md) 记录。没有人工金标不阻塞实验；质量使用已冻结源图及 AI 验收，不能写成人工验证结果。

## 固定版本及下载准入

- 官方 SDK/source：`62d5e649c32be2271f2c8c66ec8307f3d7373903`。
- vLLM：`18343393b4da41a7e8027efbc4c7e77c28301bf0`。
- Draft：`openbmb/MiniCPM-OCR-1.0-DSpark`，HF revision `038915ad18182b759e356632b6b16b55efd29952`。
- 完整文件清单、字节数、SHA256、下载地址及原始 metadata 响应摘要见 [DSpark source lock](dspark-source-lock.json)。原 [标准 source lock](source-lock.json) 不变。

[HF 固定 revision 元数据](https://huggingface.co/api/models/openbmb/MiniCPM-OCR-1.0-DSpark/revision/038915ad18182b759e356632b6b16b55efd29952?blobs=true) 仅含四个文件：`.gitattributes`、`README.md`、`config.json`、`model.safetensors`。运行必需的权重为 **594,599,898 bytes**，SHA256 `3e6332e05e2539898a0691db381e3a85877728a754561f9e3d13e597e44c672b`；配置为 **1,409 bytes**，SHA256 `ba0a9ed774ca1e5e4d7d97517379e477c7e8b6c151154e4b0556b0abd449d2e3`。

29 可沿用 [ModelScope 官方仓库](https://modelscope.cn/models/OpenBMB/MiniCPM-OCR-1.0-DSpark) 下载完整快照。此次取得的 [ModelScope metadata](https://modelscope.cn/api/v1/models/OpenBMB/MiniCPM-OCR-1.0-DSpark/repo/files?Revision=master&Recursive=true) 中，weights/config/README 与 HF SHA256 相同；`.gitattributes` 不同：HF 为 1,519 bytes，ModelScope 为 2,135 bytes。两套来源分别冻结，不能把这个 Git 属性文件差异判作运行权重不一致。ModelScope `master` 可变，下载后必须逐文件匹配已记录的来源清单，并保存实际 metadata 响应。

Draft [固定配置](https://huggingface.co/openbmb/MiniCPM-OCR-1.0-DSpark/blob/038915ad18182b759e356632b6b16b55efd29952/config.json) 指定 `Qwen3DSparkModel`、`block_size=15`、BF16、5 层。锁定 [SpeculativeConfig](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/config/speculative.py#L1348-L1370) 令 draft dtype 继承主模型，默认复用主模型 tokenizer，因此该 draft 仓库没有独立 tokenizer 文件不构成缺失。有效 draft 最大长度受主模型最大长度约束，本实验仍为 16K。

## 在标准命令中启用

先保存标准实例的实际 argv、版本、配置和结果，停止该任务的标准 GPU 实例。使用相同 release、主权重、SDK patch、CPU 布局模型、输入像素、裁剪和请求参数；在现有 [Mini serve 命令](execution/deploy/serve.sh) 中仅追加：

```bash
--speculative-config '{
  "method":"dspark",
  "model":"/models/MiniCPM-OCR-1.0-DSpark",
  "num_speculative_tokens":15,
  "enable_adaptive_verification":false
}'
```

这是 [锁定官方教程](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/docs/minicpmvocr_tutorial_en.md#3-start-the-service) 的 speculative 配置，仅将模型地址改为本地路径。保持 BF16、`max_model_len=16384`、`max_num_seqs=4`、`max_num_batched_tokens=8192`、`gpu_memory_utilization=0.65`、`downsample_mode=4x`、`max_slice_nums=9`、CPU layout 及标准 C0 采样、缓存策略。只启动一个 GPU 推理实例。

**DSpark 仅在 GPU Model Runner V2 实现。** 锁定源码 [默认选择逻辑](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/config/vllm.py#L714-L752) 在 Triton 和当前功能允许时选择 V2；[V1 验证](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/config/vllm.py#L3057-L3064) 明确拒绝 DSpark。检查没有遗留 `VLLM_USE_V2_MODEL_RUNNER=0`，并保存实际 runner 日志。不能仅凭配置或 READY 声称 DSpark 已生效。0.65 参数相同不保证剩余 KV 容量和 NVML 峰值相同，均须实测。

## 最小生效验证和配对比较

记录 `/metrics` 请求前后快照，再运行 processor probe、既定开发页和固定区域子集。检查 completion usage、结束原因及产物完整性，确认下列计数器增量：

```text
vllm:spec_decode_num_drafts_total
vllm:spec_decode_num_draft_tokens_total
vllm:spec_decode_num_accepted_tokens_total
vllm:spec_decode_num_accepted_tokens_per_pos_total
```

锁定 [计数器实现](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/v1/spec_decode/metrics.py#L175-L280) 在 speculative 开启时创建并在实际观测后累加这些值。要求 drafts、draft_tokens 增长；accepted 为零时如实记录。接受率使用同一测试窗口的 `Δaccepted_tokens / Δdraft_tokens`，保留各位置增量。字段存在而数值未增长不足以证明实际执行。

通用 metrics 文档中的 `1 + accepted/drafts` 带有 bonus-token 口径；本 draft 采用 [anchor-as-first-prediction](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/v1/worker/gpu/spec_decode/dspark/speculator.py#L3-L23)，不要直接把该通用值写成真实每步输出 token 数。保留原始计数和实际 completion token/耗时。

通过最小验证后，沿用统一测试的相同输入、暖机、并发、请求预算和评分器，配对比较标准与 DSpark 的结果差异、AI 质量分数、CER/结构诊断、延迟、吞吐、资源和失败率。逐 token 完全一致、4090 kernel 可用、内存余量和实际加速比均属于待验证结果；不由源码支持或模型规模代替实测结论。

## 回退

停止该任务 DSpark 实例，删除整个 `--speculative-config` 参数及 JSON，重新使用已保存的标准 serve 命令。官方教程明确该删除操作恢复无 draft 的标准解码。主权重、SDK、CPU layout 与输入不变，保留 DSpark 日志和失败产物。

任务启动脚本已预备`serve.sh mini-dspark`分支，仅给原Mini参数追加上述speculative-config；`serve.sh mini`路径仍为标准解码。此分支准备及shell语法检查不能代替GPU生效验证，实际启用须在标准横向验证之后。

内部配对入口已准备`execution/deploy/run_dspark_campaign.py`（默认plan-only），R0mixed100三对与P0fixed40六对，共18轮。三个测试容器的guard、lease、真实argv仅specflag差异、完整分母与前三个总counter增量均为硬门；per-position仅诊断，缺失不补零。Astra max独立用真实run_trial模拟外部I/O跑通18轮，另13合成tests通过；仍未执行真实DSpark GPU，不能以这些代码检查认定加速或质量通过。
