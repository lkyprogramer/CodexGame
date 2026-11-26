# 20 · 阶段验收、能力表与发布阻断

**目标GPU、质量、长context和服务能力初始NOT_RUN；本文不授权上线。** 包自检、短prompt或预期guard拒绝成功不提升其他能力行。

## 1. 状态与证据规则

状态沿AGENTS：`NOT_RUN / RUNNING / PASS / FAIL / BLOCKED / NO_BENEFIT / DEFERRED / SKIPPED_WITH_EVIDENCE`。未开始NOT_RUN；缺机器/资产/权限/统计证据BLOCKED+reason；违反合同FAIL。仅有证据无需实施的可选分支可跳过。

证据区分document-check、synthetic/mock、CPU-only、other-GPU、target-4090。PASS仅覆盖对应claim；schema合法不证明raw真实。05的`SUPPORTED/UNSUPPORTED/UNQUALIFIED`能力资格与任务状态分列。

release key包含模型/权重、R3或研究目标、backend/path、KV codec、context类型与P/N/capacity、spec/宽度、graph/budget、active/slot上限、state格式；关键项变更须重新资格。

## 2. G0–G7门与交付物

| Gate | 必需工作与证据 | 通过后可做什么 |
|---|---|---|
| G0 inventory+locks | T00目标机清单；代码/资产/模板/构建锁；现有服务回退快照；预算与guard矩阵 | 在已授权隔离环境构建、短测试 |
| G1 generic CUDA serial | 正式Mini R3、target-only、初始P4K实际输入；TC01–TC06/TC20相关项；16K扩展经T04/T10另记 | 建立同模型串行oracle；不授予budget/spec资格 |
| G2 state/numeric/spec | TC01–TC24按能力全覆盖；E/N/Q分类；完整state/RNG账本；greedy及sampling分别资格 | 对已合格路径做性能实验 |
| G3 E2E performance | PF01–PF03/PF05相关项；≥30独立case确认；中位数、CI及gmean分列；资源与失败计数 | 保留有证据优化；仍不是发布许可 |
| G4 longcontext | PF04/PF07；64K、C128K/P128K所承诺类型；输入实证、reserve、恢复、零截断及资源预算 | 只扩大通过的context能力行 |
| G5 quality noninferiority | QC01–QC08适用项；150独立Java任务+300工具case；2pp/1pp非劣及关键项零新增错误 | 形成质量合格候选，研究目标另记 |
| G6 service/soak/rollback drill | SV01–SV07；≥8h且≥200请求；Pi排队/恢复与实测旧服务回退 | 输出完整可审阅release候选 |
| G7 authorized rollout | SV08；核实当时明确部署授权，锁定流量范围、SLO、触发器与回退责任 | 只在授权范围按阶段灰度 |

G2按本次声明能力选择必需集合，后加spec/缓存/队列时补全，不制造阶段循环依赖。G3不授予发布许可；G4真实质量还须G5通过。必需门不能以其他高分抵消。任务完成与能力gate分开：T03/T04可完成初筛/诊断交付，而完整G5/G4仍为未通过；容量失败诊断可触发T09，不要求先让失败能力通过。

### G0最小锁集合

- 代码：底座`fb69fff02101b048a0a165a3b502712dd2ca978f`、candidate commit、patch、submodule、dirty状态、build/config摘要。
- 模型：仓库revision与全部文件hash；weight quant、K/V codec分开；config/tokenizer/template/generation config；正式Mini R3及DSpark匹配关系。
- 环境：GPU UUID摘要/显存/driver、CUDA toolkit/runtime、CPU/NUMA、RAM、OS/cgroup、SSD余量、负载下PCIe/搬运。历史记录不当现状。
- 业务：Pi版本/工具schema、JDK8/依赖镜像、任务数据与oracle、sampling、预算、SLO、现有NInfer/Strata配置和回退启动记录。

现场不升级驱动、调功耗、清cache或停生产；无独占条件则记录混杂并阻断性能结论。

## 3. 服务验收ID

| ID | 可执行场景 | 验收要点 |
|---|---|---|
| SV01 | Pi文本/工具SSE、usage、断连与错误码replay | reasoning/visible/tool内容正确；未commit/半tool call不可执行 |
| SV02 | 1主+2/3子agent，50到达/取消/timeout序列 | active generation=1；队列有界/可观察；parent等child时不持GPU slot |
| SV03 | session续接、模型/codec/模板epoch切换 | 请求不混epoch；cache失效或完整重算；新旧状态不串扰 |
| SV04 | abort、OOM、GPU错误、超时、重试及半响应 | 终态唯一、资源回收、错误显式；副作用有稳定call ID/去重记录 |
| SV05 | ≥8h且≥200请求，包含所承诺64K/128K各≥10次 | 无泄漏、持续swap、OOM或SLO违规；固定同一候选与资源轨迹 |
| SV06 | 实际切回保留的NInfer/Strata适用profile | 启动/健康/3个代表请求通过；恢复时间与积压变化有实测 |
| SV07 | 独立端口replay/shadow与业务fixture | 禁止重复真实工具副作用；单卡不够双驻留则隔离时段顺序replay |
| SV08 | 明确授权后的分阶段灰度与回退演练 | 会话固定版本；记录授权、阶段、样本、SLO、停止与回退执行 |

SV04/SV06在获准隔离环境演练，不自行切生产。OOM仍使该profile不合格，恢复能力另记。工具完成状态不明时查执行记录，不盲目重做。

## 4. 一页发布能力矩阵（初始状态）

各行绑定raw run与决策；不手改PASS。C128K/P128K沿09，N取实际配置。

| 能力行 | 目标/路径 | 最小相关证据 | 当前状态 |
|---|---|---|---|
| 源/环境可重现 | 目标4090 + 全部锁 | G0、TC01/TC02 | NOT_RUN |
| 短context串行 | 正式Mini R3，generic CUDA，4K/16K | G1/G2、PF01 | NOT_RUN |
| Q8 KV主线 | 同权重/R3；不支持则注明F16基线 | TC05–TC09、TC20、PF07 | NOT_RUN |
| 原生DSpark greedy | 合格CUDA path、固定k | TC10–TC19/TC23、PF03 | NOT_RUN |
| 原生DSpark sampling | 同目标，完整RNG/分布合同 | TC13/TC14及其他spec项 | NOT_RUN |
| 64K主线 | 实际P/N/capacity明确 | G4、QC04、PF04/PF07 | NOT_RUN |
| C128K服务 | 总容量131072，输入/生成均计入 | G4/G5、TC20/TC21 | NOT_RUN |
| P128K输入 | 实际P=131072，另有N/reserve | G4/G5、PF04 | NOT_RUN |
| 200000/262144输入 | 独立扩展profile | 同类完整长context门 | NOT_RUN |
| 新离散budget Inkling | 容量证据触发的新资格路径 | guard保留、G1–G6相关项 | NOT_RUN |
| Q4/last-loop/varloop/LoopCD | 分开的研究目标及资产 | QC06/QC07与对应TC/PF | NOT_RUN |
| Inkling完整2DSD集成 | S44公开实验runner；固定研究target/drafter及Atomic/SM89资格待测 | R03、UX01–UX03及QC07 | NOT_RUN |
| Pi子任务排队 | GPU active=1，2–3逻辑子agent | TC24、SV01–SV05、PF06 | NOT_RUN |
| 真实GPU并发2/3 | 单独容量/隔离/尾延迟资格 | 不由排队能力推导 | NOT_RUN |
| 服务候选与旧服务回退 | NInfer/Strata保留适用范围 | G5/G6、SV06/SV07 | NOT_RUN |
| 生产主力流量 | 当时明确授权范围 | G7、SV08 | NOT_RUN |

## 5. 发布判定与硬阻断

按01，单项请求中位数改善≥5%、CI支持正收益、关键层p95退化≤5%；主力迁移任务中位数改善≥10%且CI支持正收益。中位数/gmean/成功率/tail/资源分列；`paired_stats.py`不能出PASS。

质量按13：150/300不保证CI足够；重大工具错误或关键约束回归即FAIL。零回归上界只适用冻结任务分布，不证明全面等价。容量功能未达速度目标须明确产品取舍。

以下任一项阻断受影响release：资产/feature不匹配；unknown codec或未资格路径；状态/RNG/lease错误；跨请求污染；静默截断；把synthetic当真实任务；持续swap/OOM/headroom违规；任一必需case缺raw证据；质量CI不足；尚无实测回退；没有生产切换授权。

NO_BENEFIT研究可以关闭并保留主线。旧CPU pool/launch overlap或DFlash只有新trace、机制假设和对照计划才重开。

## 6. 可审阅release记录与授权边界

发布记录必须含：候选二进制/模型/配置hash、完整能力key、通过/阻塞case ID、原始run索引、独立样本数、统计方法与CI、任务失败集、资源worksheet、启动/健康/停止/回退步骤、回退资产及恢复耗时、计划流量范围、SLO、立即停止条件和当时授权证据。

先完成准备和隔离演练。部署授权依据当时会话，不能从本包推定；未获授权保持BLOCKED/`DEPLOYMENT_AUTHORIZATION_REQUIRED`，不改生产。获准后建议内部session→5%新session→25%→全量，按冻结观察量/SLO推进。

回退停止新分派，安全结束/取消在途请求，恢复旧profile并新epoch重算；不直接移植KV或重放工具副作用。显存不够双驻留则安排维护/顺序切换，不承诺未演练的零停机。

`tools/inkling-lab/lab.py`由T01创建，调用标 **PLANNED_AFTER_T01**。保存真实argv、stdout/stderr、退出码与hash；包自检不升级GPU资格。

## 7. Ghost增量验收（v1.1）

新增GX01–GX20全部NOT_RUN，详见[26](26_ghost_validation_runbook.md)。启用某G任务机制后，T12必须绑定其实际profile、对应GX与原TC/QC/PF/SV证据；未启用任务不成为全局发布障碍。G04初始DEFERRED，仅新的Inkling profiler证据与DECISION可启动。所有原正确性、150 Java/300工具用例、P128K、性能统计、G6 soak和G7实际会话授权继续有效。

上游CPU CI的84 passed/6 ignored不能勾选本包GPU/模型测试。本地9项辅助工具测试也不能授引擎资格。源码中识别的relay错误传播和提前终止状态风险须用GX12/GX17验证；本次未在GPU复现，不能写成已修复故障。

## 8. CUDA Rust与自动内核增量验收（v1.2）

- [ ] 仅为实际启用的provider/op/shape/profile完成K00–K06所需产物及AX相关测试；未选新前端可保持NOT_RUN，不阻塞原主线。
- [ ] 固定source、toolchain、ABI、layout、binary、driver/JIT、graph与registry身份；源码支持与现场资格分开。
- [ ] 若声明verified，实际非空属性、假设/TCB、MIR/checker链与同候选产物绑定；零sorryAx不等于完整数值/编译证明。
- [ ] actual RTX4090执行、launch、完成event、输出oracle、sanitizer覆盖可查；static PTX/skip/外部CI不得授目标PASS。
- [ ] R3逐loop状态、route/quant数值、回滚/取消/续接、资源峰值及错误context退役正确；原TC/GX/QC/PF/SV受影响范围重跑。
- [ ] 探索与确认分离，唯一冻结候选达到原5%/10%、CI、p95/绝对SLO、质量、容量与soak要求。
- [ ] unsupported预提交fallback与已提交sticky故障分别演练；候选失效可恢复旧已资格generation，不污染在途请求。
- [ ] K07仍DEFERRED或有真实新证据与独立DECISION；不自动切换完整backend或生产G7。

这张清单是未来执行合同，不是本次勾选结果。任务/计划测试总数见当前机器DAG与test-catalog；R03已因公开实验分支改NOT_RUN，G04/K07仍DEFERRED。

## v2缓存与资源协同验收

新增LX/UX/MX按39/40/42执行；保留原96测试与所有G0–G7阈值。发布profile若启用Tier须完整StateInventory、record/码本身份、next-logit游标、恢复峰值和故障事务通过；若启用Pool须另有全Attention参数与所选spec资格、bounded overflow及graph内容同步。所有容量收益以实际allocated峰值比较，不套论文平均ratio。各机制单独PASS不等于组合PASS。
