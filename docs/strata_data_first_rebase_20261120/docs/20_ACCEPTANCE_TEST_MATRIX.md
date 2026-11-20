# 20｜验收测试矩阵：50个分阶段用例

状态：测试规格，**下列不是本轮已执行测试数量**。新增fixtures为未来P1/P2目标；本轮仅检验包内文档与JSON结构。CPU优先，live用例只有获预算后执行。

| ID | Phase / 模式 | 输入或故障 | 预期 |
|---|---|---|---|
| T01 | P0 CPU | tag SHA填为Linux binary build | 拒绝；分别保存release/source/build/hash |
| T02 | P0 CPU | main有README变化/engine内容相同 | 记录delta范围，不重标binary等价 |
| T03 | P0 CPU | 规划exploration_control路径不存在 | 不调用CLI；标PLANNED_NOT_IMPLEMENTED |
| T04 | P0 read-only | PID复用/engine epoch改变/只有prepared配置 | 不绑定旧请求；actual runtime UNBOUND |
| T05 | P0 CPU | 渲染输入+输出+4096超过131072 | 请求前拒绝，不截prompt自动继续 |
| T06 | P1 CPU | JSON字段缺失/0/null | 分别OBSERVED0与UNAVAILABLE，禁止补0 |
| T07 | P1 CPU | vllm preemptions硬编码0 | 标constant proxy，不得导出“无驱逐” |
| T08 | P1 CPU | KV usage=token/context | 不报VRAM allocator占用率 |
| T09 | P1 CPU | Prom ITL请求均值重复N次 | 标mean proxy，真实token P95=null |
| T10 | P1 CPU | legacy/negotiated prompt totals分母不同 | 不同metric source，不直接求差 |
| T11 | P1 CPU | 两scraper轮流调用legacy throughput | 标共享scrape窗口不可独立对照 |
| T12 | P1 CPU | telemetry401/schema不识别/只有404 | 401停；未知schema停；仅已定义404允许旧端点回退 |
| T13 | P1 CPU | request ID相同但instance/epoch不同 | 不能join |
| T14 | P1 CPU | 一HTTP含多个native leg | 一对多保留，不覆盖first leg |
| T15 | P1 CPU | slot复用与parent-child并发 | slot_epoch隔离，parent显式绑定 |
| T16 | P1 CPU | 初始历史gap、锚后event seq缺口/ring覆盖/失终点 | 建(instance,last_seq)锚；启动前gap不误判当前，required窗口内loss不授资格 |
| T17 | P1 CPU | clock domains不同/时钟回拨 | 不直接相减；wall仅日期；缺映射unknown |
| T18 | P1 CPU | source receipt新但硬件样本陈旧 | 分sample与receipt，stale显示 |
| T19 | P1 CPU | role/空SSE/usage-only/半UTF8 | 不误报首token或ITL |
| T20 | P1 CPU | reasoning先于visible/tool-only | 各首事件独立，完整tool args再计可用 |
| T21 | P1 CPU | 一个chunk含7tokens/一次commit7tokens | batch gap与count，不能造7个间隔 |
| T22 | P1 CPU | 错误/取消/timeout与成功混合 | 全保存；快失败不提高成功任务速度 |
| T23 | P1 CPU | 预算布尔true但无当轮scope | 不调用OwnedServer；BLOCKED_AUTHORITY |
| T24 | P1 CPU | 旧schema有nullable GPU字段但无原件 | 不升级成OBSERVED；报告unknown |
| T25 | P1 CPU | missing request/短位置/仅一个stock臂 | 不因force_check交集/exit0而PASS |
| T26 | P2 CPU | 串行FIFO admitted vs parallel waiting registry | 不同stage语义，不能混队列耗时 |
| T27 | P2 CPU | cancel在queue/load/decode、engine-only restart | 单terminal，资源owner与epoch正常，不丢失败 |
| T28 | P2 CPU | logical reuse与RAM restore同时发生 | 两维共存，不互斥求和/当GPU hit |
| T29 | P2 CPU | new admitted expert尚有DMA | pending不是ready_hit；需求wait单列 |
| T30 | P2 CPU | 大logical read命中page cache | 不计为等量物理NVMe/H2D bytes |
| T31 | P2 CPU | 相同session key但tool schema/history改变 | prefix identity失配有理由，不冒称缓存bug |
| T32 | P2 CPU | round N结束时做N+1 draft | explicit draft_for_round，不双计 |
| T33 | P2 CPU | EOS/cap/取消导致commit裁剪 | matched/committed/emitted分开，不强套a+1 |
| T34 | P2 CPU | graph capture1次、launch100次 | capture不是执行次数，不复制耗时 |
| T35 | P2 CPU | 固定buffer溢出/长字符串/敏感payload | bounded/drop，拒私密字段，不热路径阻塞 |
| T36 | P2 source/build | hooks关闭，PROFILE='0' vsunset | 关态无新增clock/sync/I/O；presence flags正确 |
| T37 | P2 source/build | SM100 API/INT8KV不支持/缺toolchain | N/A或BLOCKED，不伪造SM/升级CUDA |
| T38 | P2.0/P3 GPU有条件 | 同源同构建off/on三对，或release/source身份不同 | 三对SCREEN_ONLY；不套六对工具；跨构建不配对；超开销停，不自动续采 |
| T39 | P3 GPU有条件 | prime/exact-repeat/真实append | 三种cache定义与实际token可复核，绝对质量独立 |
| T40 | P3 GPU有条件 | 多stream相交/CPU与DMA重叠 | busy用并集；critical需依赖；累计不当wall |
| T41 | P3 GPU有条件 | 错PID/捕获裁剪/trace丢记录 | 拒正式归因，保留invalid原件 |
| T42 | P4 CPU | trigram4-way覆盖旧长源、有/无合法W09原件 | proposal只同会话当前前缀；事后oracle单列；缺trace不能用L1摘要猜补 |
| T43 | P4 CPU | 找回但policy不选择/non-copy开销 | 不能算额外commits收益；oracle单列 |
| T44 | P4 CPU | logical rows与issued tiles不同 | 按真实grid算有效比例；无grid则unknown |
| T45 | P4 CPU/source | padded rows大但DMA压关键路/stream-k重排 | 不将padding等同比例提速；exact不符不实现 |
| T46 | P4 CPU | headroom低于门/旧机制/上游已有/独立AA缺失 | 对应关闭；缺AA不得补0，≥4%也只许AA待定状态，不给原型/AB额度 |
| T47 | P5有条件 | 同kernel oracle正确但EOS后state错 | STOP_CORRECTNESS，不继续性能 |
| T48 | P5有条件 | 一个request很多round伪独立 | 不得用round数缩CI；按pair/trajectory |
| T49 | P5有条件 | 主指标快但质量/非主时间/资源退化，或缺gold/必测任务 | 不推广；绝对阈值与必测逐项审，不能平均掩盖 |
| T50 | P2.0/P3/P5有条件 | deadline时请求在途、owner失配、清理宽限不足/恢复未授权 | 预留清理时间；只取消实验自有工作；owner不符不杀；安全隔离不可保证则不启动 |

## 最小 fixture 设计

P1建立一套小型匿名、合成输入：单服务两epoch、两request、三native legs、一pending DMA、一RAM恢复、一个7-token commit、一个seq gap和一次取消。每个负例只改一个字段，能重现对应校验拒绝原因。JSON Schema只管结构，语义不变量要由test代码验证。

P2的fake engine/transport只检验协议与状态机，不能替代GPU数值。实际CUDA/graph/expert/state oracle留给已获授权的P3/P5，未跑明确NOT_RUN。

## Review要求

测试输出必须具体到命令/版本/exit/失败名称。不得写“测试都通过”而省略大批NOT_RUN。每个Phase报告CPU_SOURCE、CPU_FIXTURE、BUILD、GPU_CORRECTNESS、TASK_QUALITY、E2E_PERF、DEPLOYMENT七个独立状态。静态包验收只更新DOC_PACKAGE一项。

