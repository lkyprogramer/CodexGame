# 10 · 复用原工具，而不是再造实验平台

唯一执行根目录是 `docs/strata_4090_128k_lab`，本包位于其 `frontier/`。本节未来适配器的 `tools/frontier/*`、测试和 workspace 路径均相对执行根目录；不要在 frontier/tools 再建一套 live runner。运行时显式绑定执行根目录，核对原有资源身份。

## 已存在且可以复用的入口

| 原路径 | 复用内容 | 不能假定 |
|---|---|---|
| `lab/runner.py`、`lab/workspace.py` | 原资源护栏、隔离构建/运行、PID所有权 | 本包已自动调用或已完成warm adapter |
| `lab/cli.py` | `verify`、`doctor`、`assets`、`cfg`、`stats`真实命令 | `stats`已实现本包正式采用门 |
| `tools/session/session_bench.py`、`chain_bench.py` | 单会话请求/受限评分 | HTTP重放等于真实Pi |
| `tools/np3/trace_patch.py`、`trace_summary.py` | CPU任务级字段和既有采集经验 | 旧patch适用于任意新源码 |
| `tools/v027/trace_ada.py`、`analyze_ada.py` | PID/SSE区间、归类/并集/不确定性处理 | 所有GPU wait都是可删成本 |
| `tools/oracle_replay/compare_session.py` | 匹配分派raw比对与负控制基础 | 只比hash足以证明有效区域一致 |
| `tools/hc_scratch/perf.py` | 六对顺序、计时变量删除、原件计数、统计纪律 | 可直接用于任何warm链或重新开HC |
| `tools/quality_gate.py` | 独立任务binary相对非劣 | 绝对质量、受限完成时间、生产许可 |
| `tools/combination/run_chain.py` | 已有失败记2400s的专用任务做法 | 通用任务适配器全部存在 |

原源码：[工具树](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/tools)、[lab目录](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/lab)。

## 原命令的安全用法

在原包目录内：

```bash
python3 -B -m lab.cli verify
python3 -B -m lab.cli --config config/local.json doctor
```

`doctor`是目标机只读核查，执行前仍需确认配置指向隔离路径；本次作者没有执行。`cfg --execute`、`run --execute`、`auto --execute`不是本包诊断入口，不应直接拿旧默认corpus开跑。

## 适配器状态（P00后）

本轮已实现根tools/frontier/identity.py、pi_history.py、warm_plan.py和contracts.py及对应定向测试。identity.py为只读收集，warm_plan为纯离线校验；P01现已实现warm_run.py和critical_path.py，handoff直接复用原生命周期及最终回读，不新增单次抽象：

- `tools/frontier/identity.py::collect_identity(config_path: Path) -> dict`：读取旧config并脱敏，核全SHA、实际服务/GPU/port、资产清单；不停止服务。
- `tools/frontier/warm_plan.py::validate_warm_plan(plan: dict, policy: dict) -> dict`：检查1引擎/3请求、上下文、授权与身份、freeze hash和墙钟上限；不发网络。
- `tools/frontier/warm_run.py::run_diagnostic(plan_path: Path, identity_path: Path, output_dir: Path) -> Path`：复用旧runner的锁/PID/guard，执行唯一诊断矩阵；输出逐请求与窗口引用。仅在任务被授权后实现/调用，命令help必须明确live行为。
- `tools/frontier/critical_path.py::summarize_windows(trace_paths: list[Path], identity: dict) -> dict`：保留UNKNOWN边；不把kernel总和自动转成critical path；输出可人工复核的区间与证据。

identity/warm_plan/warm_run/critical_path已实现；资源交还逻辑复用并内联于warm_run，不另建handoff模块。实际本轮以短输出停止，后续本地修复只有CPU验证。路径/签名让独立Task能衔接；不得用空实现返回PASS。若现有旧工具已等价覆盖，写调用适配与验证即可，不重新复制一个runner。

2026-10-31的独立P01B合同新增根`tools/frontier/p01b_run.py`，通过显式adapter复用warm_run原锁/PID/预算/历史与清理；旧P01默认语义保持。`p01b_patch.py`和`lab_p01b_trace.hpp`只在独立native研究树插入有界host采集，`p01b_analysis.py`验证完整窗口/原始IDs及窄依赖边，GPU内部未知保留。P01B已完成1引擎3请求；实际报告与执行源码单独冻结，候选资格INSUFFICIENT，不将自然EOS合同用于P05固定输出性能。

## 数据接口

`IDENTITY`包含`source_sha/binary_sha256/asset_manifest_sha256/config_sha256/patch_manifest_sha256`和机器读取时间；`REQUESTS`每行包含`run_id/engine_id/request_id/request_sha256/token_ids_sha256/prime_or_append/prompt_tokens/read_tokens/reused_tokens/completion_tokens/valid/failure_kind`；`WINDOWS`以`engine_id/request_id/window_id`联合主键。

trace区间需带clock domain和来源；未经校准不能跨时钟直接相减。每个输出文件写入RAW_MANIFEST，manifest不包含自身。所有输出新建，原P3/P24证据只读。

## 计算器与真实验收的接口边界

`paired_stats.py` 不读取真实warm链、P6资产、A/A原件或温度，输入声明必须先按 templates/DATA_CONTRACT.md 核验；当前主指标是 decode_ms。`headroom.py` 的 dependency_verified 和局部加速比也由有来源的证据支持，exit0只表示条件模型可计算。两个工具均不能签发硬件资格、质量通过或部署许可。
