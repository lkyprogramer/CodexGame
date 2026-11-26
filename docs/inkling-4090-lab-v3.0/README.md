# Inkling-2-Mini × RTX 4090 自有引擎实验室 v3.0

**版本：3.0 · 2026-11-26（Asia/Shanghai）。本包是设计与执行输入；截至发布，4090 上尚未构建或运行任何引擎。**

## 目标

在单张 RTX 4090 上，用一个**自己掌控的 Rust + CUDA 单模型引擎**跑通 Inkling-2-Mini（固定 3 遍循环的 MoE），先做到与参考实现数值一致，再在此基础上研究“自循环”模型本身：每一遍循环在做什么、遍数能否调、各遍之间的 KV 和专家怎样复用。速度是第二目标，生产替换不在本包范围。

## 已确认的决策（用户，2026-11-26）

| 决策 | 内容 |
|---|---|
| 自有引擎 | fork **Astral**（Rust 主机侧 + 手写 CUDA，Apache-2.0），在 4090（sm_89）上移植和扩展 |
| 编译工具 | 在 hhtele 用户目录安装新版 CUDA 编译工具（12.8），不用系统的 12.3 |
| 模型 | 先用量化 GGUF（unsloth `Mainline_Support/UD-Q4_K_XL`），原生 checkpoint 只取分词器和 DSpark 草稿器 |
| 驱动 | **绝对不动驱动**；任何可能触及驱动的步骤先停下通知用户，见 [02](docs/02_site_and_safety.md) |
| 底座 | 放弃 v2 的 Atomic 路线；上游 llama.cpp 只作数值参考 |

## 四层分工

| 层 | 实现 | 作用 |
|---|---|---|
| 自有引擎 | Astral fork（分支 `inkling-4090`） | 主力：移植、观测、循环实验 |
| 参考 | llama.cpp mainline b12751（同一 GGUF）；HF transformers `inkling2_loop`（语义） | 判定数值对错 |
| 速度参照（可选） | tqllm 精确模式（Docker）、Xolotl、atlas-ingine | 只看 4090 上能做到多快，不维护 |
| 业务对照（可选） | 生产 Strata 新版 + SQ-20 包 | 与现 Qwen3.8 在同一套 Pi 任务上比较 |

## 阅读顺序

1. [AGENTS](AGENTS.md)：执行合同与红线。
2. [00 总计划](docs/00_plan.md)：第一性原理、阶段、门槛、停止规则。
3. [07 任务](docs/07_tasks.md)：唯一的任务清单与依赖；[08 手册](docs/08_runbooks.md)：命令。
4. 按需：[01 模型](docs/01_model.md) · [02 现场与安全](docs/02_site_and_safety.md) · [03 引擎调研](docs/03_engine_landscape.md) · [04 Astral 移植](docs/04_astral_fork.md) · [05 验证方法](docs/05_validation.md) · [06 循环研究](docs/06_loop_research.md) · [09 来源](docs/09_sources.md)。

## 包内工具

| 工具 | 用途 |
|---|---|
| `tools/driver_guard.sh` | 驱动指纹快照与比对；有变化即退出码 3，必须停下通知用户 |
| `tools/ms_fetch.py` | 从 ModelScope 列文件、按 SHA256 预检、生成 aria2c 输入；下载后逐个校验并写 lock |
| `tools/lab_window.sh` | 停生产→跑实验→自动恢复生产并等 health；前后都做驱动比对 |
| `tools/preflight.py` | 只读硬件清单（沿用 v2） |
| `tools/paired_stats.py` | 配对延迟统计，case 等权 bootstrap（沿用 v2） |
| `tools/check_package.py` | 本包结构自检：链接、代码块、shell 语法、任务/来源 ID 引用 |

`python3 -B -m unittest discover -s tests -v` 运行工具测试，`python3 -B tools/check_package.py` 做结构自检，`sha256sum -c PACKAGE_MANIFEST.sha256` 校验包完整性；本次结果见 [VALIDATION](VALIDATION.md)。v2.x 文档包（`docs/atomic-inkling-4090-plan-v2.0`）保留为历史，不再执行。
