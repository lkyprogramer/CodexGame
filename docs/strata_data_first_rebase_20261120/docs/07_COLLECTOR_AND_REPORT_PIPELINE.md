# 07｜采集与分析管线：复用现有 Lab，补 sidecar 而非重建平台

状态：实施规格，未实现。新文件名仅为后续 Task 目标，不是当前可执行 CLI。

## 1. 选择的最小架构

~~~mermaid
flowchart TD
    A["Harness 与 SSE 既有记录"] --> D["Lab 版本适配与关联"]
    B["Strata metrics / telemetry"] --> D
    C["Native 有界事件附件"] --> D
    D --> E["身份 完整性 语义验证"]
    E --> F["REQUESTS / WINDOWS / DEPENDENCIES"]
    E --> G["新事件与 shape/cache 附件"]
    F --> H["分层报告与候选资格"]
    G --> H
    H --> I["既定 Decision / BudgetLedger"]
~~~

不新增数据库、队列服务或Grafana强依赖。沿用现有文件证据目录与Python分析；若用户已有Prometheus只加低基数投影。原始数据不可被后续汇总覆盖。

## 2. 目录与责任

以 `docs/strata_4090_128k_lab/` 为代码根：

| 文件 | 状态与责任 |
|---|---|
| `lab/http.py` | EXISTS：SSE/usage/time，保留 `token_itl_ms=None` 的诚实语义 |
| `lab/runner.py` | EXISTS：OwnedServer/resource/cleanup/审计入口，继续拥有进程生命周期 |
| `tools/frontier/contracts.py` | EXISTS：旧记录格式；新增附件引用，不重写旧档 |
| `tools/frontier/identity.py` | EXISTS但旧P6绑定：增加新版适配，不绕过原有效性检查 |
| `tools/frontier/p01b_run.py / p01b_analysis.py` | EXISTS：旧host event/ID抽象；只抽取可复用组件，不重跑旧P01B合同 |
| `tools/frontier/telemetry_adapter.py` | PROPOSED：产品snapshot→规范化L0 summary，版本表、明确缺值 |
| `tools/frontier/evidence_join.py` | PROPOSED：request/leg/slot/epoch/clock关联，拒绝歧义 |
| `tools/frontier/event_contracts.py` | PROPOSED：本包 sidecar payload、complete/loss validator |
| `tools/frontier/shape_census.py` | PROPOSED：有实际grid的rows/route统计、coverage |
| `tools/frontier/evidence_report.py` | PROPOSED：读取有效附件，产“可回答/未知/失败/下一步”报告 |
| `tools/frontier/exploration_control.py` | 既有规划但未见实现：若填补只做预算/前置决策入口，调用现有runner；不能顺带做自动调参器 |

建议测试放 `tests/test_frontier_telemetry_adapter.py` 等统一现有 test discovery；最终路径在 P0 读当前tree后绑定，禁止创建同职责第二模块。

## 3. 一次采集的产物

建议在原 Lab 工作区的新run目录持有以下附件：

- `run_identity.json`：prepared与observed分开，实际二进制/模型/配置与进程。
- `requests.jsonl` / `events.jsonl`：关联后的规范记录。
- `snapshots.jsonl`：原上游JSON响应及receipt时间，私密字段白名单投影后才入归档。
- `native_events.bin` 或结构化导出：固定buffer，request后导出，不在线逐kernel文本打印。
- `coverage.json`：预登记request/round/position覆盖、loss/overflow、schema支持情况。
- `shape_census.json` / `cache_ledger.json`：派生结果，带source hash与算法版本。
- `SUMMARY.md` / `decision.json`：分别区分完整性、正确性、性能、可部署性。

字段名是建议，不替换旧格式文件名。允许同run以manifest关联原有SSE和WINDOWS，不复制数百MB重复raw。

## 4. L0：先不改引擎

1. 从固定服务版本获取 `/v1/telemetry`、`/metrics` JSON；确认认证、schema与最近记录窗口。
2. 在既有SSE收集请求完成时进行一次snapshot补抓；只需系统趋势时低频轮询（建议1Hz作为待测起点，不是保证开销）。
3. 上游live ring被覆盖或记录缺失时记DROPPED；绝不以poll平均代替每请求事实。
4. 只请求readonly endpoint，不让采集器触发模型加载或新的generation。服务未启动时记UNAVAILABLE，不自动启动。
5. 收集器默认observer_level=L0，不打开verify profiler、tensor dumps或 `--api-monitor`。
6. model/file hash与toolchain只在identity阶段校验，正式窗口中不得扫大文件或全 `/proc/*/smaps`。

L0产物应已能区分质量失败、queue/load、真实append重读与宏观CPU/GPU/内存。先看这些是否已解释问题。

## 5. L1：只为当前未知补结构事件

按 [06](06_MINIMAL_INSTRUMENTATION.md)补lineage、cache原因、spec工作量、实际shape。热路径只做固定record与计数，不分配、不加同步、不写JSON。以确定性request/round采样，事先冻结采样ID列表；不是事后挑最慢或最快轮。

增量必须可完全关闭。若“=0”仍触发 `getenv` 分支，baseline应unset，并记录有效环境；关闭态和原版必须先等价。事件导出移到结尾或已存在checkpoint线程；导出占用与后续请求排队不能隐去。

## 6. L2：被问题驱动的限定时序

仅当L0/L1显示潜在净空间且时间依赖仍未知时，选择一个已登记窗口捕获Nsight/CUPTI/CUDA events。能力失败记NOT_SUPPORTED/permission，不降格填零；不改驱动权限、不偷偷sudo。

原始timestamp先保留clock domain；校准误差大于要解释的gap时不连接因果边。CUPTI correlation能连接launch与activity，NVTX只给范围而非GPU完成。graph capture节点不等同replay执行。

## 7. 汇总的七条不变量

1. expected请求集合与observed集合**相等**，不只取交集。
2. 每request恰有一个terminal状态，cancel/error同样保留；重复重试有独立attempt。
3. native正式提交数、SSE usage、client可见token能解释差异（隐藏thinking/协议过滤/截断），不能要求本来不相同的数强相等。
4. 所有duration同clock且非负，活动区间与重启边界不能混拼。
5. memory/byte统计不混单位、不同存储层不重复相加；无需sum-to-100%的量明确说明。
6. 只有 OBSERVED/有引用的 DERIVED 可用于正式门；ESTIMATED只做筛选，缺失不是好结果。
7. 查询失败或schema变更时保留raw/error并停止该项比较，不“fallback到旧版正确-looking字段”。

## 8. 最小可用报告

一份报告必须能回答“这次哪层慢、证据多完整、是否值得下一步”，而不是堆一页 counters。首页至少列：

- actual runtime 与参考source是否对应；
- 任务成功/结构成功/完整答案、失败和未执行；
- 外层等待、服务queue、prepare/restore/read/decode、client-visible gaps；
- true append / exact repeat / A→B→A 分栏；
- 真实reuse原因与expert/shape的已知/未知；
- observer overhead、样本完整性、当前candidate资格及预算余额。

面板映射见 [22](22_MONITOR_DASHBOARD_SPEC.md)。业务结论和证据不足状态应当一起显示，不以绿色健康灯代表性能优化通过。

