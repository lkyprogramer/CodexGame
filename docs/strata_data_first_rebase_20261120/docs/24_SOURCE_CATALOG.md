# 24｜来源目录与证据等级

快照日期：2026-11-20（Asia/Shanghai）。本包研究时固定的具体SHA见[evidence/source_lock.json](../evidence/source_lock.json)。后续上游改变不追溯修改本轮结论：先做source delta，再判断是否影响数据合同或已关闭路线。

## 1. 核心来源

| 来源 | 已读内容与固定对象 | 用途 |
|---|---|---|
| [CodexGame 4090-report](https://github.com/lkyprogramer/CodexGame/tree/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b) | 当前提交/父提交、AGENTS、Lab计划/源码/报告/禁重记录；11/18多会话归档；两个指定旧包 | 实际执行和文档计划分开、历史资产与失败不能改写 |
| [Strata v0.2.16](https://github.com/Niko1221/Strata/releases/tag/v0.2.16) | 官方releases、matching refs、annotated tag解引用、release feed与制品digest；固定tag`64524fb9`和main`58ee3227`差量 | App/Terminal与Control/Engine分版；构建来源不能猜 |
| [Strata server](https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py) / [Prometheus](https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/prometheus.py) | metrics/telemetry/status/API监控、admission、DONE/BSTAT、counter/histogram构造 | 入口语义、真实ITL缺口、代理KV、硬编码preemption |
| [Terminal字段](https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/docs/TERMINAL_TELEMETRY_FIELDS.md) | client fallback、bounded snapshots、activity seq与instance、日志/监控CLI | 复用现有服务面而不是再建平台 |
| [Strata native generate](https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/program/generate.cpp) | request/leg、cache选择/恢复、loan/refill、verify/commit/next draft；相邻prefill/verify/expert/pool实现 | 可挂点边界，不把host计时当GPU或critical |
| [QuixiInfer ce25391](https://github.com/QuixiAI/QuixiInfer/tree/ce25391bff43ac9bb101e8d1f62e3705f8972494) | 模型/架构范围、CPU/DMA预算、cache反例、长位置协议与性能日志 | 资源共享与ready-hit分母 |
| [Kinetic f3723b1](https://github.com/Veloresearch/kinetic/tree/f3723b1e046cc7e1d013de160402f58d819ab423) | multi-source spec/tree默认配置、测试、Flywheel与idle settle、不同任务bench | 复制任务与普通任务分离，树与命中不能凭命名认定 |
| [Speedy 7d500de](https://github.com/DevDock-AI/Speedy/tree/7d500de0067f8fb31a9da1fbef16a303f790dacc) | suffix代码及fixture、patch ledger、bench、默认defer近似、许可、v0.4.12边界 | C01离线索引差量；排除已上游吸收和改变数学者 |
| [FlashInfer稳定9aa9206](https://github.com/flashinfer-ai/flashinfer/tree/9aa920602276537b27e017a762a71e3437fc7f0d) / [main6fd1320](https://github.com/flashinfer-ai/flashinfer/tree/6fd1320260a8224b8a0d69c8cca8235aed65b3b2) | fi_trace、autotune与bucket回退修复、QSA新旧API/SM/KV、GDN能力 | shape/tactic/coverage证据；不把新API当即插即用 |
| [Blink v1全文](https://arxiv.org/html/2604.07609v1) | 设计、同engine消融、硬件与对照、正/负结果、当前不支持功能；公开代码定向检索 | 论文级证据；作者公开源码commit未核实 |
| [PolyStrata 3e164216](https://github.com/simplexai-labs/PolyStrata/tree/3e1642161198c50ff1abed4046f4e4f476099dbb) | 两engine归属、row-class/gfx1010与NVIDIA分叉、prefill arena、PIN/state存储 | C02仅census；等价与资源反例 |
| [NVIDIA CUPTI](https://docs.nvidia.com/cupti/main/main.html#hardware-event-system-hes) / [CUDA PDL](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html) | 官方能力限制 | HES不适用于Ada，PDL≥cc9；device graphs另论 |

具体函数/行号/PR/固定文件链接在04、06、12–17章，表中目录链接不是对“所有源码已逐行审完”的声明。Release、README、作者benchmark、测试fixture和真正执行源分别核对，不以stars或宣传标题判创新。

## 2. 证据等级

| 等级 | 可以支持 | 不能支持 |
|---|---|---|
| 本机raw+合同+复算+身份 | 该工作负载下可重复的行为/性能 | 任意新版本/模型外推 |
| 用户repo执行报告 | 历史结论、配置和失败教训；注明raw是否可得 | 缺raw时声称本轮独立复算 |
| 固定源码/fixture | 实现存在、分支条件与测试覆盖范围 | 实际部署命中或性能 |
| 作者硬件benchmark | 对应条件中的作者报告 | 本机4090可复制、无质量影响 |
| 论文全文 | 作者设计、实验口径与限制 | 未公开实现已检查、可直接移植 |
| 当前建议/反事实 | 新假说、最小数据和停止门 | 实测或已批准的下一步 |

## 3. 明确保留的未知

- 当前4090主机进程、安装binary hash、Linux release的实际engine build/source，未现场核。
- 部分历史raw只在用户本机workspace；本文保留“报告级”或“用户摘要待绑定”，不补造。
- C01真实碰撞率/成本与C02真实padding关键路径空间：未采新数据。
- 旧addendum中新增控制器/collector是否后来在未公开工作区实现：P0再次盘点，不凭目录名认定。
- Blink作者实现未获得可固定commit；本轮未下载权重或运行任何供体引擎。

## 4. 使用与版权

本包是独立研究、最小设计和来源链接，不打包上游代码树、完整论文或作者原文。移植前逐文件核许可证，尤其Speedy独立代码与继承MIT部分不能混用授权。公开汇报只导出聚合/哈希；原始token/模型输出与工具内容受单独数据授权约束。

