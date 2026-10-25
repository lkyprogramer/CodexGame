# 观测、Baseline、消融与采用门槛（2026-10-21 分层范围修订）

当前先执行 [29 Baseline合同](../plans/05-baseline-29-execution.md)，优化尚未开始。本页覆盖当下B29和未来P6/Cn，不把可测指标与未来拟建指标混为一谈。完整场景/容量/任务执行与监控以该合同及 [主审查报告](../../ninfer-hyperqwen-v3-review-29-20261020.md) 为依据。

## C21：版本化计量与可追溯

B29真实日志schema20/prepare_detail，保留原始字段和单位。未来P6保留core schema24/prepare_detail，并在 `extensions.hybrid_spec_v1` 扩展。使用显式schema adapter，旧缺值null+原因；代理默认补0的reasoning_tokens不可当真实计数，不能伪造旧日志包含新round/feature字段。

新扩展至少包含request/round ID、backend、proposal fingerprint、N、logical K/valid V、physical W/B/token rows、neural/lookup proposals、accepted_drafts、committed_tokens、bonus_tokens、round_wall_ns、alignment_ns、lookup_cpu_ns、graph key/hit/miss、fallback reason、index/graph/staging bytes与epochs。allocated shape与mask有效量独立记录。

输出计数来自原引擎许可/停止策略下的token ID/completion统计，reasoning/content/tool分项注明来源；anchor不重复，拒绝后Target token/全接受bonus按实际输出计一次，stop/cancel按合同。accepted≠committed/completion，SSE frame不是token。不得重BPE最终显示文本伪造原ID计数。客户端ID、响应X-Request-Id、server_instance_id/request_id必须可联结。

每metric保存来源raw、公式、单位、起止区间、schema adapter/hash、缺失原因。记录client send/headers/first_byte/progress/first_reasoning/content/tool/last/done/complete、server queue/prepare六段/restore/prefill/decode/publish和future round spans。跨机器绝对时间不相减；异步span不简单相加。

## 指标定义

- E2E=client complete−send_start；client TTFT=首非空reasoning/content/tool payload−send_start，排除progress/空role/首HTTP字节；首正文与工具完整可执行时间另报。engine TTFT保留版本原定义。
- E2E吞吐=真实交付completion/client E2E；server decode吞吐注明decode span的首/末token边界。复制、自由生成与Agent分别报告，短2/18/26token探针只smoke。
- prefill吞吐=computed_prefill/prefill span；reused不进重算分子，热total_prompt/时间另名。总prompt、reused、computed与请求O单列。
- 客户端TPOT近似仅N>1且有可信N时用 `(last_payload-first_payload)/(N-1)`；合并flush影响明确。全token单chunk不报0TPOT/无限吞吐；无逐token时间戳只报chunk-gap，不造ITL分位。
- aggregate吞吐=测量窗口内全部交付tokens/窗口wall，不相加各请求TPS。acceptance、committed/round、整轮wall与物理W共同报告，局部kernel快不能代替业务收益。
- GPU/host采样100–200ms起步并保存allocator高水位、graph/aux/pinned/RSS、温度/时钟/功耗/节流/IO/swap/其他进程；功率积分J按整卡或batch计，不给每lane重复分配。短请求峰值可能是下界。

观测OFF/ON成对测，常规开销≤2%，超出降低采样再测；不能每层cuda同步。监控数据缺失或跨schema含义未知时BLOCKED对应资格，不填0。

## 基线、最终采样目标与范围

B29=真实E8/schema20二进制，BO=clean O重建，B6=真实P6/rk4v4/schema24，Cn=优化。B29↔BO解释部署来源，B29↔B6独立验收frontend/codec/ABI，B6↔Cn单因素，最终Cn再对B29回归。已有PROD/O/C设计不变；缺BO/P6实证不拿U填空。

生产Target sampling保持temperature1/top_p.95/top_k20/presence0/preserve-thinking/medium。greedy/deterministic只描述proposal策略，新增Lookup/mixed/DFlash/selective sampling组合在design/11及各shape资格前OFF/回旧合格sampling。`research_greedy`是Target temperature0数值诊断，不能和sampling混桶或宣称现网收益；相同seed跨普通/spec路径不保证同token，分布与路径一致性分开。

完整声明目录仍为14P×3O×4负载×cold/warm×2采样/诊断轨=672单元（P256/tool不可表示单列），不是每阶段默认执行量。现已采用 [plans/06](../plans/06-staged-evidence-budget.md)：初始174core+104专项=278请求、Pi44一次O32768、8工程一次+2repo一次；阶段相关A/B总额≤240，H5/H8对实际发布profile集中正式资格。未测声明仍未资格，不把预算或278落盘升级成性能PASS。新增17合成题/算术smoke保留可选，不再要求20×3通用下限；发布工程为8×3+2=26任务/variant。

P由最终模板/控制token计数并与server核对，容量按P>C拒绝、O_eff=min(O,C−P+1)、文本ceiling=P+max(O_eff−1,0)，末token不入KV、初始4096窗口/动态growth、MTP clamp另账；P+O≤C只是保守预算，不强加固定R。正式core原argv、actual cache分类：cold须reused0/computed=P，预期cold实际hit保留gap，不启no-prefix-reuse顶替，不按nonce/key/slot erase猜冷。B29只有进程内L1/L2；复杂Pi跨协议count不保证同wire，必须server复核，缺IDs/metric记null。

B29 C1服务的多客户端排队与候选activeC2/C3/C4资格分开；共享KV/物理W/B/资源预算不按每lane一份262K。COPY/W16首版C1限制保留，但不把“greedy proposal”误写成Target必须T0。

Pi A层固定请求与B层真实闭环分开。44派生wire保留原O32768、medium、compaction/context_edit和两异常；固定历史toolResult不执行，不当任务成功。8工程/2repo按独立测试与干净patch评分，失败/耗尽成本保留；合成性能length请求不算完成任务wall。

消融A0=B6原MTP3；A1同采样合格MTP3/4/5；A2同宽Lookup；A3词表；A4W8；A5动态W16；A6proposal-skip；A7DFlash2ring；A8selective。当前B29不是A0，新合同/文档不是这些未来实现的性能结果。

## 统计统一、有限预算与fail-closed

初始T0是全P薄覆盖/工程参考，只回答能跑、实际深度/状态/粗略成本，不承诺p95或优化收益。T1每阶段只做预登记相关合同+≤240相关A/B请求，候选6P/2负载/cold-warm/每版5次是最大筛选形状，至少3时间block；前置/warmup/重试/哨兵调用计实际预算，必要时减少格数，不能隐形扩张。硬数值/状态断言仍全部按实际影响验证。

正式T2在H5/H8针对实际发布profile：关键case≥10有效配对、至少5独立run block、3warmup不进样本；每个预登记p95桶/variant≥100请求。metric、桶组成/权重、比较对象/允许变化、样本与一次追加预算先冻结。混合负载100不能冒称各负载/每P都有100；跨O/cache/Target sampling比例不测后拼桶。100只是最低可估条件，CI不够窄仍INCONCLUSIVE。

单卡A/A先漂移验证，候选A/B/A或ABBA，bootstrap建议10000次/95%CI按case/会话聚类与配对block重采样；相关turn/token不算独立请求。报告绝对/相对差、分位/CI/样本及全部attempt可靠性。环境排除只按预登记规则整block保留重跑；自身OOM/超时/慢样本不能删除，timeout是censored/deadline不记0。

明显错误/无收益先停止；一次预登记追加仍不确定就INCONCLUSIVE/不采用，不无限加样本直到显著。发布示例1680请求只支持已登记O512请求级回归，不替代完整copy补丁/工程任务wall或所有profile尾延迟；后者另有预算和质量门。时间/次数耗尽不免除阈值，缩声明必须记录未资格项。

历史merge_tools仅识别p50/p90/p10，p95-only会静默忽略；原件不改，当前门禁必须未知rule/quantile/metric/单位/非finite值拒绝、空有效断言拒绝、缺/重复配对与错hash/schema/skip/0tests拒绝。A1/B100+p95_relative=.05必须失败；p95/CI未实现或不足不能PASS。分布验收按design/11的独立概率/processor/RNG合同，不能以几条seed重复或top_k1测试代替。

## 采用门槛（未来候选测量前冻结）

| Gate | 规则 |
|---|---|
| 身份/覆盖 | binary/config/data/hash一致；actual P、route计数、required案例/指标齐全；GPU必测无skip |
| 数值/状态 | 同codec/同prefill state的精确或独立oracle合同；stop/bonus/rollback/cancel正确 |
| 可靠性/质量 | 无新增必测失败/OOM/状态污染/schema回归；任务/工具/编译成功率观察不下降并报告CI |
| 原业务guardrail | TTFT p50≤+5%/p90≤+10%，decode p50≥−3%/p10≥−5%，prepare同TTFT；小分母绝对预算TTFT5ms、prepare0.5ms |
| 长context | 131072/196608/253952普通负载decode比率CI下界≥.97；warm TTFT p95比率CI上界≤1.05 |
| H5采用 | copy/edit wall改善≥15%；自由Java/中文/tools p50退化≤3%、p95≤5%；真实Agent总wall改善≥5% |
| H6/H7采用 | 预登记目标桶committed吞吐改善≥15%、E2E改善≥5%，无质量/资源/其他场景回退 |

推荐95%CI边界达标才采用，跨线INCONCLUSIVE；旧/V3同时适用取事前明确的更严格规则。仅copy获益仅发布显式copy profile，不能写通用提速。撤回20Java×3通用下限；工程初始8+2、发布8×3+2仍只是回归集，概率非劣margin/功效/样本数需独立预登记。本轮baseline没有候选，因此不产出优化收益PASS或promotion。
