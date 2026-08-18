# Unlimited-OCR 29 批处理部署测试报告

测试时间：2026-06-29 23:13-23:44（29 机器本地时区）  
本地归档：`/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/remote-copy`  
远端部署目录：`/home/hhtele/unlimited-ocr-4090`

## 结论

`baidu/Unlimited-OCR` 在 29 的 RTX 4090 上可以用 Docker + Transformers fallback 跑通批处理 OCR；不升级 driver、不重启、不修改 Qwen systemd/NGINX 配置的前提成立。

但当前结果不建议直接做成常驻服务。主要原因是 4 张用户长图里有 1 张出现退化长生成，运行约 301 秒后被人工中断，未生成有效结果；其余 3 张能出结果，但存在错字、版面误判、截断和表格化异常。更合适的下一步是继续作为按需批处理验证，并补齐长图裁剪、模式选择、超时和质量回归样本后，再评估 HTTP wrapper 或官方 vLLM/SGLang 路线。

## 环境

| 项 | 结果 |
|---|---|
| 主机 | `192.168.10.29` / `debian` |
| GPU | NVIDIA GeForce RTX 4090 |
| Driver | `545.23.08` |
| VRAM | `24564 MiB` |
| Docker | `25.0.2` |
| NVIDIA runtime | 可用 |
| `/data` 空间 | 准备阶段约 `153G` 可用 |
| Qwen 服务 | `openclaw-qwen36-mtp4-128k.service` |
| Qwen 入口 | `18343` 本地，`28343` NGINX token 入口 |

## 部署内容

远端目录：

```bash
/home/hhtele/unlimited-ocr-4090
/data/models/ocr/unlimited-ocr/hf
/data/ocr/input/repo-samples
/data/ocr/input/user-testimg
/data/ocr/output/repo-samples
/data/ocr/output/user-testimg
/data/ocr/logs
```

脚本：

```bash
/home/hhtele/unlimited-ocr-4090/prepare_unlimited_ocr.sh
/home/hhtele/unlimited-ocr-4090/ocr_run_once.sh
/home/hhtele/unlimited-ocr-4090/run_ocr.py
```

容器镜像：

```text
unlimited-ocr-transformers:cu121-py312
image id: 9cd9e2cab548
size: 5.7GB
base: docker.m.daocloud.io/library/python:3.12-slim-bookworm
```

关键依赖：

```text
torch 2.5.1+cu121
torchvision 0.20.1+cu121
transformers 4.57.1
Pillow 12.1.1
PyMuPDF 1.27.2.2
accelerate 1.14.0
safetensors 0.8.0
```

说明：

- 29 直连 Docker Hub 拉 `python:3.12-slim-bookworm` 不稳定，因此实际使用 `docker.m.daocloud.io/library/python:3.12-slim-bookworm`。
- 曾尝试复用本机已有 `python:3.9.18`，但 `Pillow==12.1.1` 和新版依赖要求 Python 3.10+，已放弃该路线。
- `prepare_unlimited_ocr.sh` 的 here-doc Docker 调用已加 `-i`，否则容器内 `python -` 读不到脚本。
- `ocr_run_once.sh` 已加入默认 `OCR_TIMEOUT_SECONDS=300`，用于防止单图退化长生成长期占用 GPU；token 只读取 `$QWEN_NGINX_TOKEN`，脚本未硬编码 token。

## 模型下载

下载方式：

```bash
docker run --rm -i \
  -e HF_ENDPOINT=https://hf-mirror.com \
  -v /data/models/ocr/unlimited-ocr:/models \
  unlimited-ocr-transformers:cu121-py312 \
  python -
```

`snapshot_download("baidu/Unlimited-OCR", local_dir="/models/hf", ignore_patterns=["assets/long-horizon-ocr.gif"])`

结果：

| 项 | 结果 |
|---|---|
| 文件数 | 19 |
| 下载用时 | `22:04` |
| 主权重 | `/data/models/ocr/unlimited-ocr/hf/model-00001-of-000001.safetensors` |
| 主权重大小 | `6672547120` bytes |
| 估算整体下载速度 | 约 `4.8 MiB/s` |

GPU smoke：

```text
torch 2.5.1+cu121
cuda_available True
device NVIDIA GeForce RTX 4090
capability (8, 9)
```

## 测试配置

单图默认使用 `auto`，图片优先 `gundam`：

```python
prompt = "<image>document parsing."
base_size = 1024
image_size = 640
crop_mode = True
max_length = 32768
no_repeat_ngram_size = 35
ngram_window = 128
save_results = True
```

低字符输出 fallback 到 `base`：

```python
base_size = 1024
image_size = 1024
crop_mode = False
ngram_window = 128
```

每次 OCR 运行流程：

1. 记录 Qwen 服务和 GPU 状态。
2. 停止 `openclaw-qwen36-mtp4-128k.service`。
3. 等待显存释放后运行 OCR Docker。
4. 结束或中断后恢复 Qwen 服务。
5. 验证 `18343/28343` 和 OCR 残留进程。

## repo-samples

| Case | 输入 | 尺寸 | 结果 | 耗时 | 输出字符 | 峰值显存 | GPU util 峰值 | 功耗峰值 | 温度峰值 | fallback | 人工质量分 |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| `baidu.png` | `/data/ocr/input/repo-samples/baidu.png` | `440x133` | 成功 | `6.96s` | 16 | `7564 MiB` | `54%` | `80.95W` | `47C` | 是 | 5 |

输出：

- 远端：`/data/ocr/output/repo-samples/baidu_png`
- 本地：`/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/remote-copy/output/repo-samples/baidu_png`
- 主要结果：`result.md`，内容为 `Baidu 百度`

说明：样例图内容简单，识别正确。因为字符数低于默认阈值，触发了一次 `base` fallback，fallback 输出一致。

## user-testimg

| Case | 输入 | 尺寸 | 结果 | 耗时 | 输出字符 | 峰值显存 | GPU util 峰值 | 功耗峰值 | 温度峰值 | fallback | 人工质量分 |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| `11.png` | `/data/ocr/input/user-testimg/11.png` | `1550x6664` | 成功 | `19.91s` | 723 | `10572 MiB` | `54%` | `114.12W` | `51C` | 否 | 4 |
| `2.png` | `/data/ocr/input/user-testimg/2.png` | `1550x6664` | 成功 | `14.00s` | 455 | `10576 MiB` | `65%` | `127.20W` | `52C` | 否 | 3 |
| `3.png` | `/data/ocr/input/user-testimg/3.png` | `1550x6664` | 中断 | `301s wrapper / 286.93s runner` | N/A | `10576 MiB` | `54%` | `126.94W` | `57C` | N/A | 1 |
| `4.png` | `/data/ocr/input/user-testimg/4.png` | `1550x6664` | 成功 | `15.23s` | 451 | `10576 MiB` | `100%` | `128.52W` | `52C` | 否 | 4 |

输出目录：

| Case | 远端输出 | 本地归档 |
|---|---|---|
| `11.png` | `/data/ocr/output/user-testimg/11_png` | `/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/remote-copy/output/user-testimg/11_png` |
| `2.png` | `/data/ocr/output/user-testimg/2_png` | `/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/remote-copy/output/user-testimg/2_png` |
| `3.png` | `/data/ocr/output/user-testimg/3_png` | `/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/remote-copy/output/user-testimg/3_png` |
| `4.png` | `/data/ocr/output/user-testimg/4_png` | `/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/remote-copy/output/user-testimg/4_png` |

质量观察：

- `11.png`：主体段落基本可读，能识别老旧小区改造、四级联动治理、志愿服务、文化活动等核心内容；存在错字和重复，如“回奏初心、初心”“一楼林”“治思网络”等。
- `2.png`：主体可读但版面误判为 table，结构有明显干扰；存在“因满”“回顿换新颜”“隔生感”等错字，部分内容缺失。
- `3.png`：开头被识别为巨大 table，出现大量拆字和空单元格，日志停在局部输出后继续占用 GPU；约 5 分钟后人工中断。该样例暴露了当前 `gundam + max_length=32768` 对某些长图存在退化长生成风险。
- `4.png`：主体可读，能识别文化活动、社区活动中心等内容；存在“H社E”“推动3邻里间”等错字，末尾有截断迹象。

## 失败与修复记录

| 问题 | 处理 |
|---|---|
| Docker Hub 拉 `python:3.12-slim-bookworm` 不稳定 | 改用 `docker.m.daocloud.io/library/python:3.12-slim-bookworm` |
| 复用 `python:3.9.18` 时依赖不满足 | 放弃 Python 3.9，恢复 Python 3.12 |
| `docker run ... python - <<'PY'` 没有执行 here-doc | 为 GPU smoke 和模型下载 Docker 命令补 `-i` |
| `3.png` 退化长生成 | 人工中断，wrapper 已加入默认 `OCR_TIMEOUT_SECONDS=300` |

模型加载 warning：

```text
Some weights of UnlimitedOCRForCausalLM were not initialized from the model checkpoint at /models/unlimited-ocr and are newly initialized: ['model.vision_model.embeddings.position_ids']
```

该 warning 未阻止推理，但正式服务化前需要确认这是位置编码 buffer 的非致命 warning，还是 Transformers fallback 与官方 recipe 的兼容差异。

## Qwen 服务恢复验证

每个 case 的 `restore.log` 均记录：

```text
systemctl is-active openclaw-qwen36-mtp4-128k.service => active
systemctl is-enabled openclaw-qwen36-mtp4-128k.service => enabled
curl http://127.0.0.1:18343/v1/models => 200
curl -H "Authorization: Bearer $QWEN_NGINX_TOKEN" http://127.0.0.1:28343/v1/models => 200
curl without token http://127.0.0.1:28343/v1/models => 401
OCR residual container/process => none
```

最终人工复核结果：

```text
active=active
enabled=enabled
models18343=200
models28343_auth=200
models28343_noauth=401
ocr_residual=
python_residual=
gpu=21866 MiB used after Qwen restored
```

## 复跑命令

准备阶段：

```bash
/home/hhtele/unlimited-ocr-4090/prepare_unlimited_ocr.sh
```

单图 OCR：

```bash
QWEN_NGINX_TOKEN="$QWEN_NGINX_TOKEN" \
/home/hhtele/unlimited-ocr-4090/ocr_run_once.sh \
  --group user-testimg \
  --input /data/ocr/input/user-testimg/11.png
```

可调整单图超时：

```bash
OCR_TIMEOUT_SECONDS=600 \
QWEN_NGINX_TOKEN="$QWEN_NGINX_TOKEN" \
/home/hhtele/unlimited-ocr-4090/ocr_run_once.sh \
  --group user-testimg \
  --input /data/ocr/input/user-testimg/3.png
```

## 最终判断

当前 29 适合继续做 Unlimited-OCR 的按需批处理测试，不适合立即做常驻服务。

原因：

- 可用性：容器 GPU、模型加载、3/4 用户长图 OCR 成功，说明最小改动路线可行。
- 资源：OCR 峰值约 `10.6GB`，单独运行时 4090 显存足够；但无法与当前 Qwen 128k 服务共存，必须停 Qwen。
- 质量：长图结果有可读性，但错字和版面误判明显，`3.png` 出现不可接受的退化长生成。
- 运维：当前仍是停止 Qwen 后单次运行，不适合直接暴露服务；如要服务化，至少需要图片预处理/裁剪、模式路由、超时、失败重试和质量回归集。

建议下一轮：

1. 对 `3.png` 单独做 `base` 模式和更短 `max_length=8192/16384` 对比，确认是否是 `gundam` crop 模式引起的 table 退化。
2. 对 1550x6664 长图先做纵向切片，再合并 OCR 结果，降低单次生成长度和版面误判。
3. 如果要服务化，优先做本地 HTTP wrapper + 队列 + 单 worker，不要直接并发；Qwen 共存需要另设机器或强制互斥调度。
