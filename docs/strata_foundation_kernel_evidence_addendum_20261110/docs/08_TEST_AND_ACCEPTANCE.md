# 08 · 测试与验收增量

状态：**PLANNED / NOT implemented**。下表是后续实现的验收要求，不是通过记录。当前仅交付文档、合成样例和 CPU 检查；实际执行结果以 `VALIDATION.md` 为准。engine starts、generation requests、GPU budget 均为 **0**。

本章追加到原底座 `docs/12_TEST_PROTOCOL.md`，不替换 O0–O6 的 27 个任务、T0–T6 分层、四类 controller artifact 或唯一 `tools/frontier/exploration_control.py`。E0–E4 的具体任务依增量计划绑定下列用例；不得另建裁判。

## 1. 必须覆盖的正反例

每组至少有完整阳例、单点损坏反例及断言；“工具没有报错”不能代替预期结果。合成通过只证明解析和拒绝规则。

| 用例 / 对应原任务 | 注入条件 | 必须得到的结果与证据 |
|---|---|---|
| K01 · O0/O1 身份 | 同 SHA、不同 dirty patch/flags；换同名二进制；缺加载 hash | 不合并 build；保留源码、编译、产物、加载/JIT、执行五层；仅源码或产物为 `candidate_only` |
| K02 · O0/O3 路径 | preset 含 89，但 cubin 无 89；PTX 有而 JIT 输出未知；dispatch 分支不匹配 | SM89/loaded path 不得推定；记录原 manifest、产物 hash、module generation、分支与 shape 引用，缺项 UNKNOWN |
| K03 · O1/O3 graph | capture 一次、replay 100 次；同名 kernel 重排；旧 generation 混入新 graph | capture 不当 execution；按 generation/replay 关联；未匹配 launch 单列，不能填零或丢弃 |
| K04 · O1/O4 扰动 | `STRATA_VERIFY_PROFILE=0`；profile 开关改变 fork/fusion/stream；observer-off 偷关既有计数器 | 环境变量存在即启用；不得判路径等价；结构改变时正常路径资格拒绝，诊断证据不得晋升 |
| K05 · O1/O5 unknown | 丢记录、provider声明的无效时间戳sentinel、跨 boot 时钟、缺依赖、无 completion sink、未知额外成本 | null 与原因保留；合法相对时钟原点0不误拒；不得把 union/无观测区间写成可移除耗时/idle；输出 `INSUFFICIENT_ATTRIBUTION`，不自动补采 |
| K06 · O5 forcing 完整性 | arm 缺/多 ID、仅交集相同；位置缺洞/越界/重复；stock 少于 2 | 外层按冻结的完整 ID 集、每例完整位置集逐一校验；任何缺失/重复均阻断，不能接受半覆盖或 warning 后继续 |
| K07 · O5 forcing MVP | 文本/token/目标位置不一致；非有限或有限正logp；倒序/重复top2；同token不同logp；伪造margin；缺实际输出收据或输出不符 | 本增量同文本 MVP 严格拒绝；合法tie/格式舍入按冻结规则；不截交集、不补值。上游支持 decoder-arm 换文本，那是另一合同，不一概判工具bug |
| K08 · O5 结论边界 | check/selftest 通过；只有目标/argmax logp 与 top-2 TSV | 不声称已保存 full logits；不据此证明 prompt/decode 等价、GDN/KV/PLE/MTP rollback/恢复全等、自然 EOS 或服务质量 |
| K09 · O3/O4 诊断 | spill 退出 77；SM86 allowance 套到 89；权限失败；replay/cache/clock 不同 | UNKNOWN/BLOCKED 或输入无效；原始退出码与适配器状态分开；不得把 counter 时间替代 observer-off wall |
| K10 · O1/O5 内存 | host 返回即覆写；capture 当完成；slot/页复用代次混淆；draft 未提交却计 committed | 必须有最后消费者完成证据；检查 ownership、alias 生命周期及有效区间；容量/payload/页/scratch 不重复计量；缺 peak 为 UNKNOWN |
| K11 · O5 小 oracle | 独立 FP64 小输入，显式 BF16 舍入；跨页/物理页置换/不同长度；错误映射/位置、NaN/Inf、tie/near-tie | 对照独立参考，报告误差与首个差异；故意错误必须失败；空集/缺 golden/未执行不 PASS。CPU 通过不外推真实量化、长上下文或状态恢复 |
| K12 · O6 闭环 | fixture 声称 live；未授权任务；失败样本被删；预算崩溃后自动重试 | 拒绝来源升级，保留失败账本；`next_gpu_task=null`；引擎/GPU/网络入口调用数为 0；不启动第二 controller |

K06/K07 是外层完整性护栏，不重写上游评分算法。`force_check.py gen/score` 会启动引擎，不属于离线检查；prompt scorer 与 decode scorer 的配置不同，不能跨域互证。具体输入合同见本包数值护栏章节；内存参考见 [07](07_MEMORY_AND_ORACLE.md)。

## 2. 原统计与质量门槛原封保留

正式候选仍为 **6 对 fresh-engine**，顺序 `AC/CA/CA/AC/AC/CA`；以整对引擎序列为单位做 paired log-ratio 的 `6^6=46,656` 次 exact bootstrap，95% CI，不按 token/window 伪扩样本。预注册 `m=max(0.04, 2*AA_noise)`；冻结主指标须满足 `U95(C/A) ≤ 1−m`，非目标 TTFT/wall 的上界 ≤1.02。不得补第七对、挑最好结果或排除失败交集。

原 oracle/golden、heldout、自然 EOS、完整任务成功率和失败惩罚保持不变；质量阻断不可用性能补偿。2% 非劣界不是允许删除 2% 失败。任务时间裁判未实现时仍为 `TASK_TIME_NOT_ESTABLISHED`；retrieval 六项 FAIL、P05 阻断不变。

Observer 单独按原 O4 验收：A 原版/B 新版观测关闭/C semantic/D 短诊断分组，不与候选收益混算。完整且有效时 U≤1.01 才可 `QUALIFIED_SEMANTIC`；1.01<U≤1.03 为 `DIAGNOSTIC_ONLY`；U>1.03 且 L≤1.03 为 `INCONCLUSIVE`；L>1.03 或硬性路径/正确性失败为 `REJECTED`。缺证据不自动取得低开销资格。

证据的diagnostic角色不覆盖observer资格：graph CHANGED即使U=0.99仍REJECTED；graph UNKNOWN即使U=1.00仍不能QUALIFIED。图等价和完整性先于开销区间。

## 3. 每项任务的验收包

每项 E 子任务须列出对应 O 任务、K 用例及未覆盖项，至少提交：

1. 输入白名单、源码/补丁/配置/fixture hash；原 artifact 引用，不另起身份体系。
2. 正反例、预期状态、实际状态、原始 stdout/stderr、退出码与执行时间；未知字段及原因。
3. 修改范围、最小测试、外部入口零调用证明；仅文档任务不得伪造运行记录。
4. 五轴结论：完整性/来源、观测/路径、数值/状态/服务、完成收益/任务质量、授权/预算；未测明确 `NOT_EVALUATED`。
5. 独立 review 与独立 test 的问题单/裁决，以及唯一下一项离线任务或 null。阶段验收不能只引用实现者的 PASS。

以下是验收材料落点，不是新增任务编号：

| 原任务 | 本增量须附的材料 |
|---|---|
| O0 | 固定来源锁、已建/待适配/阻断/关闭复用矩阵；源码与部署身份差异、缺失加载证据清单 |
| O1/O2 | 既有 scope/时钟/事件合同的字段映射、K01–K05 合成证据；不假装原生 collector 已接入 |
| O3 | 产物与 SM89 目标材料、capture/replay 对应关系、定向诊断配置及原始失败；没有设备资格就明确未测 |
| O4 | 各组的二进制、配置、工作量、路径与资格判定；保留原置信区间和异常，不用平均值代替上界 |
| O5 | 完整输入集合和位置审计、stock 重复数量、数值与状态独立结论；同文本 MVP 的适用范围声明 |
| O6 | 全部用例覆盖表、失败账本、独立复核意见和交付 hash；质量阻断及历史关闭项的回归检查 |

原 O2 仍承担原生采集实现；本增量不为它另造旁路。必须检查观测代码没有新增设备/流/事件同步，没有移动原语义所需的同步或原子操作，没有把文件写入、锁或分配放进热路径。源码检查通过不等于这项运行时资格已通过。

本包 CPU 检查绿灯只允许“离线交付通过”，不允许宣布 foundation 已部署、GPU 资格通过、候选可采纳或历史闭项重新开放。
