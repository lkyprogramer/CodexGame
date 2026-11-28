# Inkling-2-Mini × RTX 4090 自有引擎实验室 v3.0

**版本：3.0.27 · 2026-11-28（Asia/Shanghai）。本包是设计与执行输入；P0 与 T07–T14 已在 4090 上执行，结果见 [07](docs/07_tasks.md) 的执行记录。v3.0.7 按用户的研究评审核实后修订了验证口径、任务与研究设计；v3.0.14 并入方案 10（新增 T22–T25、R11–R13）；v3.0.17 并入方案 11（新增 T26–T31，评估 GSQ-RCO 资产后不替换 A1）；v3.0.19 核实并编排方案 12（新增 T32–T36、R14）；v3.0.20 完成 T27、T26、T25 长上下文、T28、T32；v3.0.21 并入方案 13、MTB 方案与 TensorFold 等外部调研（新增 T37–T47、K12–K17、R15，T33 暂缓）；v3.0.22 起按新顺序执行（T41、T42、T43、T45、T46 PASS；DFlash2 + DSpark 按长度切换，T21 混合负载 257.6 tok/s；decode ≡ verify，投机输出与无草稿逐 token 相同），见 [CHANGELOG](CHANGELOG.md)。**

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
4. 按需：[01 模型](docs/01_model.md) · [02 现场与安全](docs/02_site_and_safety.md) · [03 引擎调研](docs/03_engine_landscape.md) · [04 Astral 移植](docs/04_astral_fork.md) · [05 验证方法](docs/05_validation.md) · [06 循环研究](docs/06_loop_research.md) · [09 来源](docs/09_sources.md)。v3.0.21 的四份外部调研报告在 `research/20261128/`（子代理撰写，关键源码位置已抽查；收益数字多为推断）。

## 包内工具

| 工具 | 用途 |
|---|---|
| `tools/driver_guard.sh` | 驱动指纹快照与比对；有变化即退出码 3，必须停下通知用户 |
| `tools/ms_fetch.py` | 从 ModelScope 列文件、按 SHA256 预检、生成 aria2c 输入；下载后逐个校验并写 lock |
| `tools/lab_window.sh` | 停生产→跑实验→自动恢复生产并等 health；前后都做驱动比对 |
| `tools/preflight.py` | 只读硬件清单（沿用 v2） |
| `tools/paired_stats.py` | 配对延迟统计，case 等权 bootstrap（沿用 v2） |
| `tools/check_package.py` | 本包结构自检：链接、代码块、shell 语法、任务/来源 ID 引用 |
| `tools/make_manifest.sh` | 按 git 可见的文件（跟踪的与未忽略的新文件）重新生成 `PACKAGE_MANIFEST.sha256` 并自检 |

`python3 -B -m unittest discover -s tests -v` 运行工具测试，`python3 -B tools/check_package.py` 做结构自检，`sha256sum -c PACKAGE_MANIFEST.sha256` 校验包完整性；本次结果见 [VALIDATION](VALIDATION.md)。v2.x 文档包（`docs/atomic-inkling-4090-plan-v2.0`）保留为历史，不再执行。

## Astral fork 仓库

fork 已拆成独立的公开项目 **[lkyprogramer/inkling-4090-engine](https://github.com/lkyprogramer/inkling-4090-engine)**（GitHub fork，基线为上游 `49a0a2b`），4090 上的 `$LAB/src/astral` 跟踪其 `main`（远端名 `fork`）。原先放在本包 `patches/astral/` 里的补丁已删除，代码以该仓库为准：

| 提交 | 内容 |
|---|---|
| `c240d53` | `ArchProfile::Sm89`；修正 `mxfp4_block` 测试的期望值（T11） |
| `d17a519` | 同步上传 / 清零之后先等 legacy stream 完成（修复 T07 的 MXFP4 失败） |
| `d3b402e` | `astral dump-logits` 和 `cmp-prefill` 的诊断输出（T12） |
| `6b78ffc` | `bench/llamacpp_compare/`：从本包 `tools/w1`、`tools/w2`、`tools/t14` 迁过去的通用分析脚本 |
| `8189c6f`、`e484873` | 4090 移植文档、基准文档、README / NOTICE / CHANGELOG、GitHub 模板与 CI |
| `a8ca269`、`f8c976e` | 同口径 logits 比较（`dump-final-logits`、`final_logits.cpp`、`logit_compare.py` 的 num-2 / num-3）（T19） |
| `35de94a` | prefill split-K 改为固定顺序归约，prefill 运行间逐位可复现（T19） |
| `18bf3e3` | decode 路径与 DSpark verify 行的 logits 导出（T20） |
| `2c2f424` | `astral trace` 只读探针（T15） |
| `02259e1` | `ASTRAL_PASSES` 遍数覆盖、varloop 原生加载（T18） |
| `744e32a` | `Gemv::quantize` 写 FP16 平面，selftest 的 GEMM 用例检查输入（T22） |
| `9593eb4` | SWA 环形缓冲，上下文到 128K + 1024（T17） |
| `3f5a49d` | sm_89 的 decode 投影改走 dp4a（T16 第 1 轮；因 T20 B 组 decode FAIL 已在 `aa837c7` 撤回） |
| `aa837c7` | sm_89 上 DSpark 的小批改走 dp4a，decode 回到 tensor core；DSpark 206.3 tok/s（T16 第 2 轮） |
| `7108b78` | 草稿 sliding-window K/V 改为 ring（逐位相同）、可选 FP16、`ASTRAL_SPEC_LOG`；DSpark 最大容量 73728 → 106496（T21） |

本包只保留实验室专用内容：驱动守卫、停服窗口、ModelScope 下载、执行记录和调用这些分析脚本的 shell 脚本。

