# 13 · 正确性、目标分布与业务质量

本文约束G2/G5。正式主线固定 **Mini R3 + per-loop KV + 锁定权重/模板/sampler**；研究目标另建记录，不能复用主线PASS。[S01/S02/S03] 初始全部`NOT_RUN`；目标机不可用记`BLOCKED`并列缺失证据。

## 1. 三类改动对应三种证据

| 类别 | 改动范围 | 准入合同 |
|---|---|---|
| E：语义精确 | 无损搬运、状态管理、目标分布保持型投机 | 结构/状态不变量；确定性greedy与串行oracle一致；随机投机另证分布保持 |
| N：数值等价 | 同一计算但fusion、归约顺序、累加dtype变化 | teacher-forced误差、路由差异与业务非劣；不冒称bit exact |
| Q：目标/质量变化 | Q4 KV或权重、少轮、研究权重、近似历史、LoopCD | 独立目标指纹与QC报告；不并入“同模型无损加速” |

E发现差异先FAIL，不能放宽tolerance后仍叫E。资产、循环、codec或采样目标改变须重新分类。Q8 KV不支持时先建立已注明的F16基线。

## 2. 状态与数值oracle

遵循[05架构](05_architecture.md)和[07投机](07_speculation.md)。checkpoint覆盖global/SWA KV、conv环、位置/有效长度、loop消息bank/controller、DSpark特征顺序与Markov状态、grammar/stop/parser、epoch、页所有权、lease及CUDA event。DSpark实际成员由固定源码枚举；未枚举齐全时该能力BLOCKED。至少一个oracle从原始prompt独立重算，避免两份快照同时损坏却比较相等。

**撤销模型候选状态不等于回拨全部RNG。** 分别登记proposal、acceptance、residual、target随机流及消费事件；已经消费的接受/恢复随机数不能因reject重用。只有相同完整执行序列要求同seed重现；不同合法spec策略可能等分布而不同token。统计抽样不能替代接受/残差算法证明。

数值比较使用相同teacher-forced token。记录dtype/shape/layout、max-abs、relative-L2、cosine、非有限数；logits另记KL、top1/top-k和expert路由差异。先量化baseline非确定性，再冻结按算子/dtype划分的`tolerance_registry`；缺registry不得让N通过。

初始工程筛选可采用：固定有效词表、temperature=1的logit分布平均KL≤1e-4、teacher-forced top1一致率≥99.9%。这不是普遍质量保证，仍需QC。合法mask的负无穷单独检查；有效未屏蔽状态出现NaN/Inf立即FAIL。只比较有效状态，不比较未初始化padding；张量误差阈值不得事后因失败而调宽。

## 3. G2正确性矩阵

边界包括0/1、conv长度±1、1023/1024/1025、page/capacity±1；未支持组合验证拒绝，不以跳过取得能力。

| ID | 场景与最小覆盖 | 必须满足 |
|---|---|---|
| TC01 | 每build/profile核对资产、resolved配置 | 模型/草稿/模板/精度/路径指纹一致 |
| TC02 | 旧budget的model/spec、4096及ubatch32边界 | 原guard明确拒绝；不删guard冒充资格 |
| TC03 | 200条中英/Unicode/工具历史fixture | 模板、特殊token、input IDs一致 |
| TC04 | 32prompt的prefill/decode映射 | 24物理层、48visit与真实cache slot对应 |
| TC05 | 128prompt、≥4096个teacher-forced位置 | 覆盖各pass与global/SWA；符合E/N合同 |
| TC06 | per-loop支持的chunk 1/7/31/32/127/128/512/1024 | 分块与非分块目标一致；last-loop只按10的固定prefill/B1 oracle资格，B>1先证明语义 |
| TC07 | global KV扩容、量化block/page边界 | 有效区、position、scale正确 |
| TC08 | SWA满环、绕回及覆盖后reject | 数据/写指针/绝对位置恢复 |
| TC09 | conv初期与跨环，回滚前1–4位置 | 被拒候选不影响后续logits |
| TC10 | 每pass开始/结束处中断 | loop bank/controller不漏跑或重复 |
| TC11 | 每合格k的接受前缀0..k，8边界×16seed | correction/bonus正确；随后AR64tokens一致 |
| TC12 | DSpark每状态成员的fork/reset/reject | feature visit、Markov及恢复语义正确 |
| TC13 | 小词表枚举与错误residual负例 | p/q实际分布、one-hot、零概率、EOS正确 |
| TC14 | 1000序列，seed重放/交错请求 | 完整RNG账本隔离，无盲回拨或重复draw |
| TC15 | cancel/异常/预算变更时释放lease | CUDA工作/图引用完毕后才回收地址 |
| TC16 | prefix长度0/1、SWA/page边界及中途编辑 | 精确token前缀、COW隔离、正确miss |
| TC17 | 20次epoch/模板/codec/loop切换 | 不兼容缓存失效；在途请求不混epoch |
| TC18 | 100例EOS/stop/UTF-8跨token和spec块 | finish_reason正确；未commit内容不外发 |
| TC19 | queue/prefill/draft/verify/commit/stream各50次abort | 终态唯一；下个请求等于干净实例 |
| TC20 | 容量±1、超长工具结果、输出reserve边界 | 明确接受/拒绝；零静默截断 |
| TC21 | 连续100次save/restore/cancel | 续接等于完整重算，无资源持续增长 |
| TC22 | 缓存损坏、半写、旧格式、磁盘不足 | 拒绝恢复并安全重算，不用污染状态 |
| TC23 | 图形状/地址/版本变化，k7→k0等切换 | 只选已资格图；旧引用安全退役 |
| TC24 | 1主+2/3子请求，50种交错序列 | 状态隔离，active generation≤1，无持锁等child |

TC11只测试模型/实现允许且已有资格的k；主线按07从AR、k1、k3到k7推进，不为凑表启用未知宽度。TC13先做有限状态枚举/手算审查，再以20种小词表分布各≥100000抽样找bug；抽样检验的方法、误差与多重比较规则预登记，不能以“未拒绝零假设”证明精确。

## 4. G5业务质量矩阵

| ID | 数据与要求 |
|---|---|
| QC01 | ≥150个独立Java8真实任务，配对A/B，固定仓库/隐藏测试/预算 |
| QC02 | ≥300个独立工具场景：选择、参数、历史回填、错误恢复、流式边界 |
| QC03 | Java8编译/API/依赖约束及禁止改动的关键fixture全部通过 |
| QC04 | 64K、C128K、P128K按实际承诺分层；早期约束、跨文件关系、干扰位置 |
| QC05 | 超时、工具失败、重试、自纠错；失败保留并计入完成率/惩罚耗时 |
| QC06 | Q4相对同权重/同R3的Q8 KV（或已注明F16）独立非劣实验 |
| QC07 | varloop/last-loop/LoopCD/2DSD按各自目标；质量和成本分别报告 |
| QC08 | 主力迁移相对现有Strata/NInfer的适用任务评估；不扩大scanner范围 |

150任务建议分层：缺陷修复40、跨文件重构30、单测20、构建/日志20、长上下文约束25、工具恢复15。固定task ID、repo commit、JDK8构建、依赖镜像、输入、工具权限、隐藏oracle、wall/token/turn上限。成功以产物和验收结果为准，不用模型自述“完成”。30个代表任务追加3seed仅作稳健性诊断，不新增90个独立样本。

### 非劣判定（本项目工程策略）

任务完成率`Δ=p候选−p基线`的单侧95%下界≥−2pp；工具正确完成率下界≥−1pp。采用已验证的配对比例score或profile-likelihood CI，按独立任务聚类；工具case同样保持配对。**观察到任何重大错误工具动作、重复副作用、跨会话污染或关键约束回归即FAIL**，不能用总体得分抵消。

若配对CI实现尚未验证，可使用保守充分条件：事件“基线成功且候选失败”的概率单侧95% Clopper–Pearson上界≤margin；因为`Δ≥−P(新回归)`。零新回归时上界为`1−0.05^(1/n)`，n=150约1.98%，n=300约0.994%。这只界定**当前冻结任务总体与抽样假设下的新回归风险**，不证明所有业务全面质量等价；有回归时必须算真实区间，多seed不能充独立n。

长context样本不足时，相应质量行保持BLOCKED并写`INSUFFICIENT_EVIDENCE`；不能借150个整体任务通过来宣称每个context都通过。新增质量变化、研究目标与生产模型替换分别报告，保留失败案例。只过perplexity、needle或短问答，不能替代QC01/QC02。

## 5. 证据与执行边界

每case保存输入hash、代码/资产锁、硬件、采样/状态事件、raw输出、oracle、最小复现、资源轨迹。缺权限/硬件记BLOCKED；实现错误记FAIL。G2不授权部署。

`tools/inkling-lab/lab.py`由T01创建；调用一律标 **PLANNED_AFTER_T01**，不得假造现成flag。发布聚合见[20验收](20_acceptance.md)。

## v2新增正确性层级

原E/N/Q和业务非劣门保持。LX01–LX32及UX01–UX04由39/40定义，Magnitude MX由42定义。特别区分Codec逐bit、完整状态恢复、候选Attention数值和最终模型质量。Schema/源代码/外部CI不能替代任一模型gate。新Codec的特殊位型往返不得用浮点近似误差替代；Pool算术也不得靠bitwise Codec冒充整体E。
