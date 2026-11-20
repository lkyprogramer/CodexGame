# 21｜执行 Runbook 与 AI 交接

## 1. 当前可以直接做什么

本轮交付后首先做**离线审阅与P0来源/复用盘点**。用户若随后让AI“按包执行”，先说明当轮范围：P0/P1代码与CPU测试、P2.0现成L0证据资格、必要才做的P2 hooks、P3有限现场采集分别交接。P2.0没有有效原件时也可能需要GPU请求，不能藏在“只做基础能力”里。不要把模板里的许可字段当用户许可。

建议交给执行AI的首条任务：

> 读取本包AGENTS、README、00、01–06和19。先核4090-report最新tree与用户未提交改动，完成P0；在既有授权内做P1适配/CPU测试，P2.0先审有效L0原件与决策缺口。未获live范围授权不启动GPU；没有缺口证据不先写全部hooks。复用Lab runner/http/P01B，逐Phase独立review，交付必要字段与最小有限采集计划。旧失败保持原结论，不启更新器、不触碰生产。

## 2. 已存在工具的安全入口

以下是经固定源码核过的接口；**本包没有运行这些项目测试，且正确工作目录/配置/依赖必须先绑定**：

~~~bash
# 在已审计的 CodexGame/docs/strata_4090_128k_lab 根
python3 -B -m lab.cli verify
~~~

这是旧Lab离线自检，不是运行新collector。以该仓README确认依赖和test discovery；不为了调用它绕过用户worktree或改全局环境。

~~~bash
# 已授权只读盘点，私有配置已核；该工具会读系统/进程/资产
./run.sh --config <已核私有配置> doctor
~~~

身份工具 `python3 -B -m tools.frontier.identity --config <旧P6配置>` 虽是实际接口，但绑定旧P6依赖/产物且可能全量hash大文件；新基线需先适配，不能复制示例直接用。详见 [03](03_EXISTING_ASSETS_AND_REBASE.md)。

已有 `frontier/tools/headroom.py --input …`、`paired_stats.py --input …`、`tools/quality_gate.py --input …` 只接受其确切schema；先复用对应fixture确认输入，不把本包新模板直接喂入。

## 3. 新版只读监控入口

在已配置且确实运行的研究实例中，优先现有 `strata monitor --once --json`、`strata logs --follow --output jsonl`，以及配置授权的 `GET /v1/telemetry` / `GET /metrics`。具体flags及响应schema见 [04](04_STRATA_METRICS_AUDIT.md)。

- 本包不提供包含token的curl命令。使用已有credential配置，不在shell历史、日志、ZIP保存Bearer/API key。
- `POST /v1/vram` 是控制接口，会改变资源，不作为监控探针。
- `/api/requests` 配合api-monitor会涉及正文，默认不用。
- 实例未运行则UNAVAILABLE；不自动launch，不把只读collect失败变成部署动作。
- 多个legacy `/metrics/prometheus` scraper会扰动共享rate窗口，指定一个采集者或只读累计值自己差分。

## 4. 下面都还不是可执行CLI

`telemetry_adapter.py`、`evidence_join.py`、`event_contracts.py`、`shape_census.py`、`suffix_counterfactual.py`、`evidence_report.py`及规划中的 `exploration_control.py`。本包没有实现，也没有假造 `collect --execute` 之类命令。

实施者按19创建后，必须把真实 `--help`、入口参数、输入schema和测试命令回写到IMPLEMENTATION_RECEIPT；在此之前所有运行示意都只是设计。

## 5. 任一live阶段（含P2.0）前必须现场回答的清单

1. 实际机器现在是否空闲、谁拥有GPU/端口/容器？旧inactive记录不是当前权限。
2. 哪一个engine/binary/source/build、哪份模型分片/量化、哪个KV/template/draft实际生效？
3. 新binary/toolchain是否可在不改受保护驱动/CUDA的条件运行？否则明确BLOCKED。
4. 本次只测哪一种负载、哪些request/position、上限多少？warmup/失败有没有计费？
5. observer与无observer是否相同路径，哪些private数据被允许本地留存？
6. 谁清理本次拥有的进程？单调deadline与预留cleanup grace是多少，watchdog如何验证owner并取消在途任务？用户已有服务不属于清理对象；恢复生产是否另获授权？
7. 哪些必要字段在当前接口不可得，是否只需L1而无需L2？
8. 所有旧negative、禁止变量、context/温度/内存保护是否落入有效合同？
9. 是否锁定required cases/gold/真实工具回执/绝对阈值？若只做诊断，哪些质量项明确NOT_PROVEN？
10. L1所用source-build stock/off/on是否真同源同toolchain？若L0来自发布制品且build未知，不得直接继承等价性。

## 6. 产物交接与后续维护

每Phase更新 `IMPLEMENTATION_RECEIPT.md`（未来生成）、RunEvidence与BudgetLedger，附：

| 项目 | 内容 |
|---|---|
| 实际改动 | 完整文件列表、base/new SHA与dirty差量 |
| 测试 | 命令/环境/exit/result级别，NOT_RUN明列 |
| 数据 | 原件定位/hash、派生器版本、隐私分级、覆盖与loss |
| 结论 | 什么被证明/什么未证明；不写模糊“总体通过” |
| 资源 | 新开引擎数、请求数、GPU时长、残留PID/文件 |
| 下一动作 | 唯一允许的下一步或终止理由 |

不要把大模型、完整论文/上游源树、私密tokens或带credential配置放入交付ZIP。原始trace按用户仓库既有workspace策略保存；公开repo只存脱敏摘要、hash和复算说明。

上游再更新时只刷新source-delta、parser兼容与需要的字段；不自动重测所有候选。若无新证据，保持NO_GAIN/DEFERRED有效。

