# 22｜报告与监控面板最小规范

目标是让用户能判断“数据够不够、值不值得改”，不是新建监控产品。优先扩展现有Terminal/Lab离线报告；无需Kafka/时序库/Grafana部署。以下均为设计，不是已新增页面。

## 1. 五块视图

| 视图 | 必须显示 | 不能暗示 |
|---|---|---|
| 运行身份 | product/engine/build/source、binary与模型hash缩写、实际route、采集等级、时间/版本绑定状态 | 最新tag等于本机运行 |
| 任务与请求 | success/structured/complete answer、外层等待、server queue、prepare/read/generate、首思考/visible/tool、E2E | HTTP200等于任务成功，失败快等于优化 |
| 会话/cache | logical match、实际read、live/slot/RAM/SSD来源、restore字节/耗时、parent保留/evict原因 | reused越高就绝对零搬运，preemptions0就无eviction |
| 资源与工作量 | expert ready/new/pending/CPU/stage、物理传输、RAM/VRAM水位、fault、actual/padded rows | GPUutil或hit rate单项解释根因 |
| 证据资格 | schema/clock/ID覆盖、drops/stale、AA/observer开销、candidate状态/预算 | 缺字段显示0或绿色 |

## 2. 每个图表的必要注释

展示单位、source endpoint/schema、聚合范围、时间窗口/样本数、是否proxy、是否有丢失和derived算法版本。

特别标注：

- `vllm:kv_cache_usage_perc`：token/context代理，不是物理KV占用。
- `vllm:num_preemptions_total`：当前hardcoded0，不具有“未驱逐”的证据意义。
- `vllm:inter_token_latency_seconds`：请求均值型分布，不是真逐token延迟。
- legacy rate：单scraper共享窗口；不能与另一端点按名字混画。
- NVML/systemIO：背景进程也参与，不能说某个expert/请求耗了这些bytes。
- graph capture count：与graph launch count分开。

完整字段核实见 [04](04_STRATA_METRICS_AUDIT.md)。

## 3. 数据粒度

公开metrics只用低基数 `phase/outcome/route_bucket/codec` 等bounded标签。request_id、session、parent、expert_id、path、tokenhash不做Prometheus label；在受限离线附件联结。

live面板保留原上游rings，足够运营；正式实验记录必须有完整journal。若只有live polling，首页直接显示“有限采样，不具备完整请求归因”。

## 4. 候选页应是一张证据卡

每个候选只需显示：原旧路线、此次独立source delta、实际dispatch、生效次数、completion-path上界、新成本、数值/任务门、当前结论、下一步和预算。

当padding高但在overlap内、接受率高但draft成本更高、减少GB但E2E更慢时，显示这些负例。不得按“局部百分比最大”自动排第一。

## 5. 最小告警

- 身份/重启epoch漂移；
- 采样stale或required event丢失；
- 任务失败/结构错误/取消异常增加；
- 内存/温度/预算达到已有保护线；
- 同schema含义不明或权限失败；
- collector自身阻塞/开销超门。

不为每次短utilization波动报警，不从proxy阈值自动调整KV/reserve/draft。控制动作仍由既有合同与人工决定。

