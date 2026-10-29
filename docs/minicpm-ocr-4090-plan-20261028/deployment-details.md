# MiniCPM OCR 安装命令与 SDK 配置

设计日期2026-10-28；2026-10-29已进入29实际实施，当前状态见[执行记录](execution-report.md)。下文保留固定版本的安装设计基准。固定起步：BF16、vLLM、16K上下文、4区域并发、0.65显存预算、CPU layout、标准解码。DSpark须在两模型标准基线和横向比较完成后进行；共同变量以[统一合同](comparison-plan.md)为准。

## 1. 固定真源和实施前提

官方仓库本次核查HEAD：`62d5e649c32be2271f2c8c66ec8307f3d7373903`（GitHub API所列提交时间2026-10-28T12:41:34Z）。下列链接均固定此revision。实施时不无声跟随main。

- [安装锁](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/pyproject.toml)：vLLM `18343393b4da41a7e8027efbc4c7e77c28301bf0`，Transformers `549e5b410733fb50e8efbbe4aa585cb89f6478ea`（5.21.0.dev0），torch2.14.0、torchvision0.29.0；SDK源码1.0.2；CPU paddle3.2.1、paddlex3.4.2。
- [安装器](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/scripts/install.sh)：入口 `sdk-cpu|sdk-gpu|transformers|vllm|sglang`，默认sdk-cpu；venv为`.venv-<profile>`，默认Python3.12，可`OCR_PYTHON=3.12`；`MAX_JOBS`默认8；vLLM构建要求gcc13/g++13。先执行对应源码准备，再改vLLM的Transformers依赖锁，最后安装源码。不是直接pip任意vllm版本。
- 隔离CUDA：安装器从pip装nvcc13.0.48、runtime13.0.96等，设置CUDA_HOME到`.venv-vllm/lib/python3.12/site-packages/nvidia/cu13`，补bin/crt和库链接。宿主CUDA12.3无须升级；gcc13/g++13不由脚本提供。不要在Debian12执行教程的Ubuntu PPA命令。
- 29已有`nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`，可作为候选基础镜像；先验证Docker NVIDIA GPU透传。镜像tag不是锁：记录`docker image inspect`的ID/RepoDigests。容器里编译用官方venv的cu13.0，不能因为基础镜像为13.2就混用nvcc/headers。

宿主目标根目录：`/data/ocr/minicpm-ocr-1.0`（实施前检查无重名内容），子目录与[主方案](README.md)一致，CPU SDK和GPU服务环境均放在专用release内。现有OCR容器/历史Qwen/ninfer目录不动。将本次SDK适配作为明确patch而不是覆盖既有源码。

## 2. 只读preflight与准备门槛

```bash
# 在 jssh 29 会话执行；只读。
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free --format=csv
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
free -h
df -h /data
docker image inspect nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04 --format '{{.Id}} {{json .RepoDigests}}'
docker info --format '{{json .Runtimes}}'
ss -ltn
```

下一条会创建临时容器，属于实施阶段检查，评估阶段不执行：

```bash
docker run --rm --gpus device=0 \
  nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04 \
  nvidia-smi --query-gpu=name,driver_version,memory.free --format=csv
```

容器用户态先准备`ca-certificates curl git build-essential gcc-13 g++-13 libdw-dev libelf-dev pkg-config libgl1 libglib2.0-0 python3 python3-venv python3-pip`，以Ubuntu24.04 apt来源提供gcc13，不加PPA。包可用性、镜像NVIDIA挂载的libcuda.so实际路径均在preflight确认。`OCR_LIBCUDA`必须指向真实文件；脚本默认`/usr/lib/x86_64-linux-gnu/libcuda.so.1`，不同Docker runtime挂载路径需要显式修正。Python/uv使用专用venv，不以root pip覆盖系统Python。

uv可固定0.10.10；29宿主已有该版本但不假设容器可见。容器内专用工具venv安装`uv==0.10.10`，之后`uv python install 3.12`。安装后记录真实Python patch版本及python可执行文件SHA。首次完整解析成功后保存`uv pip freeze`、`uv pip check`输出、容器image ID、git diff与依赖wheel/hash清单，构建可重放release镜像。仅上层版本锁无法声称所有传递依赖已完全可复现。

联网依赖：GitHub clone及其子项目/CMake下载；PyPI、download.pytorch.org/cu130、PyTorch/NVIDIA wheel托管；uv的Python分发（GitHub Releases资产）；developer.download.nvidia.com上的NVCC redistribution；ModelScope模型下载及实际重定向存储域；Paddle模型URL。Github raw200、ModelScopeHEAD200、PyTorch index200只证明对应请求成功，不保证clone、wheel下载、全量权重速度及所有构建子依赖。

## 3. 模型下载与完整性

29 HF不可直达，主路径用官方ModelScope仓库。使用完整目录snapshot，不只下载safetensors。ModelScope提供的SHA256与HF主/draft权重LFS SHA一致。

- 主模型HF revision `d10038c4954c2a4f7be159165f319a0aad57c7a2`，权重SHA256 `83f4e433b044fd23f9ea7eb3acbc7d59e4fe11a1fdf3c3129b7021d0ab4f8fd4`。
- Draft HF revision `038915ad18182b759e356632b6b16b55efd29952`，权重SHA256 `3e6332e05e2539898a0691db381e3a85877728a754561f9e3d13e597e44c672b`。
- [主ModelScope metadata](https://modelscope.cn/api/v1/models/OpenBMB/MiniCPM-OCR-1.0/repo/files?Revision=master&Recursive=true)；[Draft metadata](https://modelscope.cn/api/v1/models/OpenBMB/MiniCPM-OCR-1.0-DSpark/repo/files?Revision=master&Recursive=true)。两者的`master`不是不可变锁，实施前保存响应、用每文件SHA256作为准入门槛，下载后逐文件验证；不可只记录下载时branch名。
- Layout官方tar：`https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayoutV3_infer.tar`，SHA256 `98b9bac88c80f6bc0fda7e0bfc2cae180020371c0b2edbb1eb498a70ace751b1`。[SDK内置校验真源](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/layouts/download.py)

下载语义依据[ModelScope snapshot_download源码](https://github.com/modelscope/modelscope/blob/master/modelscope/hub/snapshot_download.py)，在独立下载工具环境中执行：

```python
from modelscope import snapshot_download
snapshot_download('OpenBMB/MiniCPM-OCR-1.0', revision='master',
                  local_dir='/models/MiniCPM-OCR-1.0')
# 仅DSpark阶段下载draft；标准服务不需要它。
snapshot_download('OpenBMB/MiniCPM-OCR-1.0-DSpark', revision='master',
                  local_dir='/models/MiniCPM-OCR-1.0-DSpark')
```

`master`下载须匹配本方案已记录的文件hash。主模型必备：config.json、generation_config.json、chat_template.jinja、model.safetensors、tokenizer.json、tokenizer_config.json、preprocessor_config.json、processor_config.json；缺少任意文件不准启动。除权重外当前主模型hash：

```text
762025491b206967a3c29c3e36ff2cccd8af6a8c750360b61dc91882b573f759  config.json
7cecf81e246f8db6bcc4c14f22313dd7decf2d6a70dd1b45c4d237a2e6927405  generation_config.json
c6a5f1387c6baa0befecc39e36f293e44baba865a9c7809ac93fae1604b2c210  chat_template.jinja
7b46cf09f350fa1cd3bfd4d20fe8b8532e76dcc5d892a0052660f803c8ad532b  preprocessor_config.json
b71fbc3e22a7dbe04622e1a2641e8553375bc1434875ac438066c58a88b974b1  processor_config.json
6269eb38f25c20c0f2ba676577f2e5603f79eab3be573dfdaa727ca6eeb5522d  tokenizer.json
74f51078120066292803d9dfe5437f67b778c5ef6d16eb04dbc6a3f7a13e5826  tokenizer_config.json
```

Draft config.json hash：`ba0a9ed774ca1e5e4d7d97517379e477c7e8b6c151154e4b0556b0abd449d2e3`。模型其余非运行必需文件也保存manifest。

CPU SDK环境可调用真实函数下载layout（下载时联网，校验tar）：

```bash
.venv-sdk-cpu/bin/python - <<'PY'
from pathlib import Path
from minicpmvocr.layouts.download import ensure_layout_model
print(ensure_layout_model(Path('/models/PP-DocLayoutV3_infer')))
PY
```

它验证inference.pdiparams/inference.json/inference.yml三件套，并写`.minicpmvocr-model.json`含source与archive_sha256。完成下载后只读挂载模型、保存各文件SHA；运行时完整本地路径，不传远端repo ID。`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`配合本地模型用于验证运行期不依赖HF；Paddle layout与方向模型也必须已本地准备。

## 4. 建立隔离环境（实施命令）

在GPU可见的专用构建容器中，clone到release内固定路径`/opt/minicpm-ocr`，与最终容器内路径一致（editable installs依赖路径，不能随意挪venv）：

```bash
git clone https://github.com/OpenBMB/MiniCPM-OCR.git /opt/minicpm-ocr
cd /opt/minicpm-ocr
git checkout --detach 62d5e649c32be2271f2c8c66ec8307f3d7373903
export OCR_PYTHON=3.12 CC=gcc-13 CXX=g++-13 CUDAHOSTCXX=g++-13
export MAX_JOBS=4 NVCC_THREADS=1
# 仅构建sm89，是否对应构建器生效须检查cmake/build日志。
export TORCH_CUDA_ARCH_LIST=8.9
bash scripts/install.sh vllm
bash scripts/install.sh sdk-cpu
.venv-vllm/bin/python -c 'import torch,transformers,vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)'
.venv-sdk-cpu/bin/python -c 'import paddle,minicpmvocr; print(paddle.__version__)'
uv pip check --python .venv-vllm/bin/python
uv pip check --python .venv-sdk-cpu/bin/python
```

MAX_JOBS4是给62GiB主存的保守起点，不是已测构建峰值。若源码build下载失败、cu13 headers混用、缺GCC或libcuda挂载，停止修正该依赖，不修改宿主驱动/CUDA，不启动循环重试或接管其他服务。

## 5. 必须处理的SDK兼容与内容保真缺口

以下不是可选美化；要声称“文本完整且验证可追溯”必须处理，并单独记录patch、测试及release版本。

### 5.1 未生效采样字段

SDK [dialects.py](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/backends/dialects.py)固定发送no_repeat_ngram_size=100；锁定vLLM的[ChatCompletionRequest](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/entrypoints/openai/chat_completion/protocol.py)与[SamplingParams](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/sampling_params.py)无此字段。[OpenAIBaseModel](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/entrypoints/serve/engine/protocol.py)允许extra但只DEBUG记录ignored，因此HTTP200不代表参数生效。

准备阶段确认：

```bash
.venv-vllm/bin/python - <<'PY'
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
names = ['max_tokens','temperature','top_p','top_k','repetition_penalty',
         'no_repeat_ngram_size','mm_processor_kwargs','chat_template_kwargs']
for name in names:
    print(name, name in ChatCompletionRequest.model_fields)
PY
```

计划内最小SDK适配：从build_vllm_payload删除no_repeat_ngram_size这一payload项；直接API也不发送它。所有标准/DSpark测试均使用同一SDK patch、同一请求参数，明示没有原no-repeat约束；不凭成功返回声称相同语义。无需新增自定义logits processor。

### 5.2 截断与预算证据

[client.py](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/backends/client.py)仅将max_tokens裁为max_model_len−prompt_reserve_tokens（默认512），不计算真实视觉prompt。400且包含maximum context length时输出预算减半，其他400/500也可能重试至request_ready_timeout。每轮HTTP可能超出deadline，deadline不是严格总墙钟限制。

[blocks.py](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/pipeline/_blocks.py)不把client返回的finish_reason留到常规result_block。计划内最小适配：记录每region实际finish_reason、有效请求max_tokens、prompt/completion tokens、模型revision及失败原因；finish_reason=length不得判作成功验收。若不适配只能通过逐区域直接API留原始响应验证，现有SDK JSON不能证明无截断。

16K是输入+输出总和；表格默认输出8192、正文4096、公式2048；来自[prompts.py](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/prompts.py)。初始prompt_reserve_tokens8192为保守输出上限预算，不是真实tokenizer计数；逐样本验证输入token并留余量。超预算优先细分裁剪或单独受控扩大上下文；不静默丢尾部文字。

### 5.3 默认整页输出会遗漏的内容

- prompts.py默认Markdown忽略number/footnote/header/footer/aside_text。完整文本方案生成外部prompt_map，复制整个DEFAULT_PROMPT_MAP，再把markdown_assembly.ignore_labels设[]（不能只传部分markdown_assembly，因为外层update是浅合并，会丢格式字段）。
- [layout/base.py](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/layouts/base.py)默认跳过image/header_image/footer_image，需`layout.use_ocr_for_image_block=true`或明确skip_vlm_labels=[]才会调用TextRecognition。
- 即使启用image OCR，[Markdown组装](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/postprocess/markdown.py)对三类image仍只输出`![image]()`，不输出识别内容。必须从results_json生成包含图中文字的text.txt/结构化结果；若Markdown也需保真，最小适配image分支输出真实图片路径+图中文字，单独验证，不声称现有SDK原生完成。
- chart使用Chart to Table，seal使用Seal Recognition；image OCR仅读取图中文字，不能据此保证几何关系/地图语义正确。
- 默认后处理还会修复LaTeX、去重/截断重复内容。因此同时保存raw_content和content，以raw文本计OCR质量，以content计产品导出效果，避免把后处理删改当模型原始表现。

## 6. vLLM标准服务命令（容器内）

固定内部服务端口18499，宿主建议仅映射127.0.0.1:18499。Docker桥接容器内须监听0.0.0.0；对外隔离由宿主端口映射控制。若实际端口占用，先更改专用端口及SDK引用，不停其他服务。

```bash
cd /opt/minicpm-ocr
source .venv-vllm/bin/activate
export CC=gcc-13 CXX=g++-13
export CUDA_HOME="$(python -c 'import sysconfig; print(sysconfig.get_path("purelib") + "/nvidia/cu13")')"
export PATH="$CUDA_HOME/bin:$PATH"
export FLASHINFER_NVCC="$CUDA_HOME/bin/nvcc"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
exec vllm serve /models/MiniCPM-OCR-1.0 \
  --served-model-name minicpm-ocr \
  --host 0.0.0.0 --port 18499 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 4 \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --gpu-memory-utilization 0.65 \
  --limit-mm-per-prompt '{"image":1,"video":0}' \
  --attention-backend FLASH_ATTN \
  --mm-encoder-attn-backend FLASH_ATTN \
  --mm-processor-kwargs '{"downsample_mode":"4x","max_slice_nums":9}' \
  --trust-request-mm-kwargs \
  --default-chat-template-kwargs '{"enable_thinking":false}'
```

每个SDK区域请求只有一个image_url（dialects.py真实实现）；max_slice_nums是图内切片，不是image请求数量。用image1可约束单区域API；不把并发4误当image4。禁止开启thinking。将`vllm serve --help`实际输出与上列flags核对后才发布；未支持即停止，不静默删flag。

## 7. SDK CPU配置与两种页面调度方式

从固定源码bundled YAML复制生成`/config/baseline.yaml`（保留其余真实默认），供C0受控页面执行器使用（当前实现见execution/ocrbench）。该执行器每次只向SDK页级处理路径提供已接纳的当前页；**不能把下面的配置直接配合多页 `minicpmvocr parse` 当作C0**。设置以下真实字段：

```yaml
run:
  mode: full
input:
  limit: 0
engine:
  type: vllm
  model_name: minicpm-ocr
  server_url: http://minicpm-ocr-vllm:18499
  startup_timeout_sec: 1800
  request_timeout_sec: 120
  request_ready_timeout_sec: 240
  request_retry_interval_sec: 2
  max_model_len: 16384
  prompt_reserve_tokens: 8192
layout:
  enabled: true
  provider: ppdoclayout3_paddlex
  model_dir: /models/PP-DocLayoutV3_infer
  device: cpu
  use_chart_recognition: true
  use_seal_recognition: true
  use_ocr_for_image_block: true
pipeline:
  queue_mode: serial
  max_workers: 4
  page_workers: 1
  overlap_layout: false
  layout_workers: 1
  save_crops: true
  save_pages: true
  merge_cross_page_tables: false
mm:
  downsample_mode: 4x
  max_slice_nums: 9
  image_limit: 1
prompt:
  override_mode: legacy
  prompt_map: /config/prompts-all-text.yaml
decode:
  temperature: 0.0
  top_p: 1.0
  top_k: -1
  repetition_penalty: 1.0
upright:
  enabled: false
```

此文件是C0的greedy配置。`queue_mode=serial`让识别阶段进入检查`page_workers`的分支，`max_workers=4`仍可让同页区域并行；它本身**不会消除官方CLI的整文件预渲染/预布局**。真正的C0 D0/P0必须由下述单页执行器控制。Mini原生策略参考N0另存配置，decode为temperature0.01/top_p0.001/top_k1；不覆写或混用两个profile。`no_repeat_ngram_size`配置可留但payload适配删除且不得声称生效。此处是修改项摘录，不建议手抄为丢默认的新完整yaml。0.65是服务预算；4只约束区域执行数，不能4个SDK进程各开4当成全局4。

### 7.1 C0必须由受控页面执行器接纳

固定SDK的`queue_mode=concurrent`会忽略`page_workers=1`，把全部页区域展平到一个队列；`overlap_layout=false`的原CLI还会先完成整文件布局再推理。因此YAML值相同不等于页面接纳语义相同。[识别分支](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/pipeline/staged.py#L412)、[展平队列](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/pipeline/staged.py#L235)。

共用页面执行器现已实现为`execution/ocrbench/core.py`与`ocrbench.cli`；实现和模型实测状态见[执行记录](execution-report.md)。D0的顺序必须是：接纳当前页 → 仅渲染当前页 → 布局/裁剪 → 当前页最多4区域识别及补识别 → 验证/组装/写出终态产物 → 接纳下一页。上一页即使失败，也先写失败终态，再按共同文档deadline决定是否继续。不能调用会先物化所有页的整文档SDK入口。P0已预渲染的输入不再计渲染，但布局/识别/写出仍按同一接纳顺序。

后端连接、CPU布局实例等可在同一run中复用，冷初始化/预热单独记录；不要每页启动新SDK进程加载模型，再无说明地把该额外开销当模型差异。C0页接纳2/4时沿用同一个执行器和全局4区域派发上限，而非增加独立SDK各自的4个workers。

接纳执行器必须输出`page_admitted/raster_start/layout_start/region_start/region_end/artifacts_complete/page_terminal`事件及单调时钟、原页ID。两页大小/区域数不同的fixture中，接纳1时页2的接纳、渲染、布局和区域事件均不得早于页1的`page_terminal`；区域全局峰值≤4。页接纳2/4另验活跃页上限，deadline从执行器的接纳事件开始。SDK原生`page_started`与layout JSON读取耗时不得代替D0外部事件计时。

### 7.2 原SDK整文档staged批处理，仅作N0参考

生成prompts-all-text.yaml：

```bash
.venv-sdk-cpu/bin/python - <<'PY'
from copy import deepcopy
from pathlib import Path
import yaml
from minicpmvocr.prompts import DEFAULT_PROMPT_MAP
p = deepcopy(DEFAULT_PROMPT_MAP)
p['markdown_assembly']['ignore_labels'] = []
Path('/config/prompts-all-text.yaml').write_text(yaml.safe_dump(p, allow_unicode=True, sort_keys=False))
PY
```

以下是官方staged整文档入口，**只作N0原生批处理参考，不是C0单页接纳命令**。`/config/native-staged.yaml`从上述配置复制，并改为`queue_mode=concurrent`及N0的decode策略；该模式的`page_workers=1`不限制识别阶段活跃页，必须在manifest记录`pipeline_variant=sdk_staged_bulk`。每次使用新run-tag，避免skipped_existing缓存污染：

```bash
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
/opt/minicpm-ocr/.venv-sdk-cpu/bin/minicpmvocr parse \
  --config /config/native-staged.yaml \
  --backend vllm \
  --server-url http://minicpm-ocr-vllm:18499 \
  --model minicpm-ocr --device cpu --workers 4 \
  --set run.mode=full \
  --set input.limit=0 \
  --set engine.max_model_len=16384 \
  --set pipeline.page_workers=1 \
  --set run.run_root=/runs \
  --run-tag native-staged-case001-n0-r1 \
  --input /inputs/case001.pdf \
  --output /runs/native-staged-case001-n0-r1/document.md
```

必须传`--config`。CLI快速路径会改上下文40960、32请求并发及layout overlap，不能使用默认快速命令冒充16K配置。服务URL给根地址，不加/v1；模型名每次显式传。`run.mode=full`与`input.limit=0`保证本次staged参考不限页，但不提供C0调度保证；仅冒烟可临时limit1。N0批处理结果不得混入C0的首完整页延迟、单页deadline或串行页吞吐列。

输出包括`results_json/<image_id>.json`（image_id、image_width、image_height、source、crop_blocks、markdown、result_stage），block含label/order/bbox/crop_filename/status/content/raw_content；布局JSON还包含class_id、score、regions等。PNG保留由save_crops/save_pages启用，但不会自动将Markdown的图片占位改为有效链接。补充导出的text.txt和总manifest应明确是本次包装层产物。

## 8. 旋转纠偏增量配置

`upright.enabled=false`是官方默认，baseline先关闭。针对90/180/270度及轻度倾斜场景，另建rotation配置：upright.enabled=true、upright.device=cpu（源码支持），并固定以下3个额外本地模型：PP-LCNet_x1_0_doc_ori、PP-OCRv5_mobile_det、PP-LCNet_x1_0_textline_ori；分别配置upright.model_dir/det_model_dir/textline_model_dir。`orientation_confirm`默认true会同时用三者。准确下载URL与各模型SHA本轮尚未核实，列为旋转场景执行前prepare gate；不能在离线运行期依赖自动下载。准备后保存对应目录hash和Paddle实例可加载证据。该路径仅方向/deskew，不等于透视畸变或弯曲纸面的几何矫正保证。

## 9. API能力与最小包装层范围

- 原生区域API：POST `/v1/chat/completions`，OpenAI图像消息+Text Recognition:/Table Recognition:/Formula Recognition:/Seal Recognition:/Chart to Table:，输入图在文本前，16K总token预算。直接API示例不发送no_repeat_ngram_size。
- SDK CLI包含parse-layout/prepare/infer/run/show-config/list-backends/parse/serve-layout；`serve-layout`仅布局检测server，不提供整页PDF→Markdown HTTP。
- 用户若要整页HTTP，需本次另交付最小包装层，不能杜撰`minicpmvocr serve`。建议受限上传→单整页active job→现有SDK parse→返回job状态及Markdown/JSON/text/PNG产物；独立run-tag、固定config、本地文件路径白名单/大小页数限额、解析失败或partial_failed不标success。并发与超时设置需要真实场景值；不把vLLM区域API当整页接口。
- CLI exit0/Markdown非空不能证明没有失败或漏页；wrapper须检查pages指标num_failed_blocks、status/partial_failed、输入/输出页数以及截断字段。本方案不实施wrapper；若只交付CLI整页闭环，不需要该组件。

## 10. DSpark后续A/B

完成两模型标准服务验收与横向基线后，停止该专用vLLM容器，沿用主模型、SDK patch、16K/4/0.65/CPU layout及sampling，只新增官方原始speculative-config（model替换为本地路径）：

```json
{
  "method": "dspark",
  "model": "/models/MiniCPM-OCR-1.0-DSpark",
  "num_speculative_tokens": 15,
  "enable_adaptive_verification": false
}
```

[官方DSpark命令](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/docs/minicpmvocr_tutorial_en.md#3-start-the-service)。只启动一个GPU推理实例；未验收不同时跑标准+DSpark。校验metrics含spec_decode相关accepted/drafts计数且实际请求后增长；无证据不得写DSpark生效。不能保证逐token一致；留差异、CER与结构质量结果，性能对比时保持同图片/暖机/并发/预算，不能让其中一方no-repeat payload变体或裁剪策略不同。

## 11. 容器生命周期与回滚

构建和运行使用专用image/release标识；模型只读挂载、输入只读、runs/cache可写；CPU SDK与GPU服务分别执行，SDK可以在同一已构建image内用独立venv运行。桥接专用network，GPU服务仅宿主127.0.0.1端口映射；不使用host网络、不开放公网、不接管已有OCR容器。首轮不自动重启风暴，失败保留日志和状态。

建议仅一层生命周期管理：Docker restart策略或systemd监督容器二选一，避免两层同时重启。如果需要systemd，unit仅操作本次命名容器，明确TimeoutStopSec、日志位置、GPU就绪/模型目录检查；先manual启动与验收后再enable，创建常驻服务属于后续已授权部署动作。

新release同GPU不能与旧服务同时跑完整配置；先停止本次专用旧服务，启动新release，通过区域/整页smoke与产物检查后切换current引用。失败仅停止新容器并恢复上一image/config/SDK patch/model manifest组合，不降级或修改宿主driver/CUDA；保留失败runs及日志。第一次部署无旧OCR服务可回退时，回滚定义是停止本次容器、撤销其独立unit/端口映射，保持现有系统原状。后续删除下载模型和产物需要另行按保留策略操作，不默认清除证据。

## 12. 未验证且必须在实施时关闭的门槛

容器GPU透传/最终发布镜像digest；所有联网构建依赖实际可达；Ubuntu24.04下官方cu13.0源码完整build；vLLM启动flags与sm89 kernel；全量ModelScope下载及SHA验证；CPU Paddle模型加载；no-repeat适配和finish_reason证据保存；完整文本导出/图中文字/Markdown链接的最小适配；旋转附加模型SHA（验收该场景前）；整页HTTP包装层仅在交付该层时准入。基础CLI整页交付不以HTTP包装层作为必选门；前述基础门关闭前不能写部署/测试通过。

补充sm89构建依据：锁定vLLM的[CMakeLists](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/CMakeLists.txt#L126)在CUDA13.0分支支持`7.5;8.0;8.6;8.7;8.9;9.0;10.0;11.0;12.0`，架构提取/过滤后会打印`CUDA target architectures`与`CUDA supported target architectures`，sm89不属于未知硬件。OpenBMB install.sh全文未覆盖TORCH_CUDA_ARCH_LIST或CMAKE_CUDA_ARCHITECTURES，因此可传TORCH_CUDA_ARCH_LIST=8.9；要保存实际编译日志确认，不额外同时设冲突的CMAKE_CUDA_ARCHITECTURES。vLLM[setup.py](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/setup.py#L215)读取MAX_JOBS并记录，NVCC_THREADS会影响并行计算；建议显式MAX_JOBS=4、NVCC_THREADS=1，是保守并发上限，不是已测内存峰值或无OOM保证。sm89支持不等于MiniCPM-OCR整链所有kernel已在29验证，仍须构建和图像推理门槛。


## 13. 主机与容器路径映射及最终配置核对

使用同一份发布镜像，GPU服务与CPU SDK分别启动。模型只读，输出/cache可写，editable源码与venv在镜像内统一固定为`/opt/minicpm-ocr`。

| 宿主路径 | 容器路径 | 使用方 |
|---|---|---|
| `/data/ocr/minicpm-ocr-1.0/models/main` | `/models/MiniCPM-OCR-1.0` | GPU服务，只读 |
| `/data/ocr/minicpm-ocr-1.0/models/draft` | `/models/MiniCPM-OCR-1.0-DSpark` | DSpark阶段GPU服务，只读 |
| `/data/ocr/minicpm-ocr-1.0/models/PP-DocLayoutV3` | `/models/PP-DocLayoutV3_infer` | CPU SDK，只读 |
| `/data/ocr/minicpm-ocr-1.0/configs` | `/config` | 配置与启动脚本，只读 |
| 本次要识别的PDF/页图目录 | `/inputs` | CPU SDK，只读；Word原件先转换 |
| `/data/ocr/minicpm-ocr-1.0/runs` | `/runs` | CPU SDK，可写 |
| `/data/ocr/minicpm-ocr-1.0/cache` | `/cache` | 独立cache，可写，预热与离线测试留证 |

创建本服务专用Docker网络；GPU容器名固定`minicpm-ocr-vllm`，内部端口18499，因此SDK使用`http://minicpm-ocr-vllm:18499`。宿主仅映射`127.0.0.1:18499`。如果SDK在宿主运行，改用`http://127.0.0.1:18499`并同时调整所有本地路径；不同运行方式不能混用示例路径。

第一次执行先在GPU可见的候选构建容器内安装依赖。以下是待纳入Dockerfile的依赖准备片段，不在Debian宿主执行：

```bash
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git build-essential \
  gcc-13 g++-13 libdw-dev libelf-dev pkg-config libgl1 libglib2.0-0 \
  python3 python3-venv python3-pip
python3 -m venv /opt/ocr-tools
/opt/ocr-tools/bin/python -m pip install uv==0.10.10
export PATH="/opt/ocr-tools/bin:$PATH"
uv python install 3.12
```

安装器和SDK适配验证完再固化release镜像，记录最终digest。首次本机运行的`docker run`须包含`--gpus device=0`、专用网络、上表挂载、`-p 127.0.0.1:18499:18499`和明确的共享内存大小（建议起步`--shm-size=4g`）；启动内容保存为只读`/config/start-vllm.sh`，与第6节命令一致。不能以可变tag或一个手工改过但无构建记录的容器作为最终版本证据。

必须保存最终解析配置，而非只保存YAML。执行包按固定CLI `show-config` 的真实`--help`读取，或在调用SDK前序列化解析后的config对象。逐项断言16384、4、page1、CPU、overlap false、full mode、limit0、8192 prompt reserve、prompt map、采样、输出路径及GPU预算0.65；再单独用7.1的实际事件轨迹验证调度。配置值检查不能证明单页接纳生效，也不能在测试代码里另造一份“生效配置”。

## 14. PDF分辨率与CPU线程的真实边界

固定源码`constants.py`的`PDF_RENDER_ZOOM=2.0`意味着144 DPI，`pipeline/_inputs.py`使用PyMuPDF `Matrix(zoom,zoom)`，没有原生`input.dpi`或PDF DPI CLI参数。C0执行器用共用渲染器逐页300 DPI并送SDK页图，不进入整文件渲染；N0若采用SDK原生PDF输入，才在部署副本改为`300.0/72.0`并留diff。实际像素/坐标/crop均需核对。200/400 DPI诊断使用显式预渲染PNG，不伪装成原生参数；改zoom不能修复原CLI预渲染/预布局全部页的调度边界。

CPU layout provider创建PaddleX模型时没有透传`cpu_threads`，所以不增加无效`layout.cpu_threads`。记录实际线程数、CPU利用率和容器配额；如实测出现既有CPU OCR竞争，再按测量决定是否增加一个provider参数适配，不能提前声称4线程已生效。`upright.cpu_threads`只控制纠偏模型，不控制主布局模型。

请求超时120s、request_ready240s只是SDK配置；它原始实现不保证严格总deadline、固定最大attempt。第5节及主方案A5要求部署适配把“最多1次可恢复重试”和剩余墙钟deadline真正落实，并在文档层执行300s/页、1800s/文档边界。原始配置单独不能证明这些合同已经成立。

[PDF渲染常量](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/constants.py)、[输入与限页逻辑](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/pipeline/_inputs.py)、[CPU布局实例](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/layouts/ppdoclayout3_paddlex.py)。
