# 完整参考 Baseline 后的瓶颈、失败归因与路线评估

日期：2026-10-21。状态：**ASSESSMENT_ONLY，未授权实施优化**。本次只读取已完成证据、计算派生指标和修订方案，没有调用模型、重跑评分、连接或修改现网。这里的“完整”指278项均记账及8+2闭环评分齐备，不指278项全部有效，也不指优化资格通过。

来源：[原始最终报告](../../../output/ninfer-baseline-29-20261020/FINAL-REPORT.md)、[最终汇总](../../../output/ninfer-baseline-29-20261020/final-summary.json)、[离线复算脚本](../../../output/ninfer-baseline-29-20261020/assessment-20261021/analyze.py)、[派生数字及输入SHA](../../../output/ninfer-baseline-29-20261020/assessment-20261021/metrics.json)。原最终报告、评分、raw与分母不修改。

## 1. 可确定的瓶颈

| 本批观察集合 | n | 请求耗时合计 | prefill合计 | decode合计 | decode/请求耗时 | accepted/drafted |
|---|---:|---:|---:|---:|---:|---:|
| 生产sampling Core | 158 | 5479.52s | 4700.41s | 759.30s | 13.86% | 79.91% |
| O8192长输出 | 12 | 975.28s | 444.44s | 528.33s | 54.17% | 79.05% |
| HTTP200 Pi回放 | 39 | 1694.47s | 497.90s | 1190.62s | 70.27% | 52.19% |

这些是描述性总和，包含复用观察；不是本次运行墙钟或生产流量加权。server span可能重叠，不能把差值解释为某个kernel的精确占比。Pi39条HTTP200不等于39个任务通过。单cell一次观察，没有p95或置信区间。

O512生产sampling下，四负载的TTFT中位数如下，每格n=4：

| P | cold TTFT | 紧邻warm TTFT | warm decode中位数 |
|---:|---:|---:|---:|
| 32768 | 10.28s | 0.103s | 144.27 tok/s |
| 131072 | 57.67s | 0.217s | 123.93 tok/s |
| 196608 | 103.46s | 0.249s | 111.09 tok/s |
| 253952 | 153.03s | 0.238s | 103.21 tok/s |

结论：长上下文冷prefill主导首包；warm后仍有随P增长的decode成本。当前数据不能区分Attention、GEMM、KV解码、内存带宽、draft/verify/alignment各自的贡献。不得从decode span直接宣称某个kernel或CPU查找是主瓶颈。

66条真实闭环请求中，实际P合计1,105,680、O合计29,389、cache hit合计943,812（约85.36%的P）。这是重复请求输入计数，不是独立token或计费。五条S6 L2观察全部source=none/hit=0，包括return-A；因此本批没有证明L2复用收益，也不能据此断言整个L2实现损坏。优先核对alias、准入/发布、页上限与实际复用条件，而非默认扩缓存。

## 2. 97fc7be6：行为异常与直接终止原因分开

原记录：`pi-pi-ee064ce94fbb-97fc7be6`。P=31,421，请求O=32,768，实际O=32,767；总耗时335.82s，其中decode325.82s。reasoning字符121,620，content=0、tool call=0。原始reasoning包含反复内部Java草稿及immutable copy、锁、线程池、端口/文件锁等重复自检，未走出reasoning并交付工具动作。

**对先前“普通输出预算耗尽”的归因作补充纠正：** SSE为`length`，服务端却明确是`result.finish_reason=context_capacity`；同一请求metrics的`kv_growth_curtailed_total`增加1、forced spills增加0。故可观察的直接结束原因是KV增长被截停，不能把它简化成正常`output_limit`，更不能混同275579输入的HTTP400准入容量拒绝。

这不是孤例：Core有72/174条服务端`context_capacity`，其中40条比请求O少2、32条少1；长输出另有2条少2。上述请求的P+请求O均未超过262144。max_tokens本来是上限而非必须生成量，但这些是容量终止而非自然stop，值得优先核对。

O源码提供一个有证据的解释候选：[concurrent_executor.h](../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/runtime/engine/concurrent_executor.h)的`build_round_membership/grow_decode_headroom/curtail_request`在KV增长失败时发布ContextCapacity；[program_impl.h](../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/targets/qwen3_8/impl/runtime/program_impl.h)的`try_grow_decode_headroom`按完整draft窗口检查主/辅助页；[request_plan_impl.h](../../../output/qwen38-27b-4090-ninfer/ninfer-4090/src/targets/qwen3_8/impl/runtime/request_plan_impl.h)另有请求页ceiling。请求尾部剩余1/2 token与固定验证余量/页ceiling的交互值得优先验证。

但O源码尚非B29二进制构建认证；现场又没有末轮budget/frontier/page entitlement与allocator高水位。**不能确定是请求ceiling、页池压力、保守余量还是另一容量条件，更不能直接宣布显存OOM或off-by-one已证实。** 原报告的`output_budget_exhausted`是把output_limit/context_capacity合并的派生布尔值，本页保留两种原始reason并作语义细分。

生成行为的触发原因同样未定位：无可信证据证明prompt冲突、采样器错误或token级无限循环。f89c5dcc本次O298、tool_calls终止、KV截停增量0，说明历史截断现象未在所有优先请求上复现。两条都只是冻结历史派生请求的单次重放。

97的accepted/drafted为51.92%；三位置条件接受率约69.42%/71.44%/74.08%。这些不是Target熵或Lookup收益测量。保分布的加速不会系统性提高走出reasoning的概率；同seed跨路线变化也不能当作“治好了循环”。若仅decode快30%，本次335.82s条件估算约260.6s，仍可能得到同类失败。处理reasoning行为需另立质量实验，不能改本次medium、采样或O32768来伪造提速。

## 3. Gson与RE003的失败归因

### RE003：原FAIL不改，模型质量归因不合格

[题面](../../qwen38-coding-benchmark-4090-v1.0.0/tasks/RE003/prompt.md)要求更新与事件写入同一事务，未要求trim；[Account](../../qwen38-coding-benchmark-4090-v1.0.0/tasks/RE003/workspace/src/Account.java)是裸record。隐藏测试第7行传`" New "`却先要求结果为`"New"`，然后才检查其余合同。派生候选`AccountService.java`已把save/append放入同一事务，并保留原始新名称。

定位依据：[隐藏断言](/Users/luo/Documents/github/CodexGame/docs/qwen38-coding-benchmark-4090-v1.0.0/tasks/RE003/hidden_tests/TestMain.java:7)、[wire派生候选](/Users/luo/.codex/task-evidence/ninfer-baseline-29-20261020/recovered-derived-20261021/derived-not-original/qcb-RE003/repeat-1/ordinal-5/candidate-files/src/AccountService.java:7)。后者不是恢复出的原CLI文件。

因此可定位的失败是题意与隐藏断言不一致。参考答案包含trim不等于公开题面包含该要求。保留v1原始FAIL/verify_exit1和原10题分母，标注`UNQUALIFIED_FIXTURE_FOR_MODEL_ATTRIBUTION`，不把它改成PASS，也不拿它证明事务能力失败；后续事务断言是否全部通过仍未实测。原verify.log缺失，不能声称已恢复原异常栈。

未来先冻结RE003-v2：明确trim合同，或让隐藏测试遵守原始payload合同，并建立独立的v2对照。该变更不回写v1成绩；本轮不修改题目/隐藏测试，不重跑。

### Gson：完整8/10失败与两项细因unknown并存

题目以`toJson(1.5, byte.class)`为例，要求数字适配器执行目标类型转换。r2与r3候选对六个primitive适配器增加byte/short/int/long/float/double的XXXValue转换，方向确实对应题目。r2精确恢复patch SHA为`5ee028ec…a2d18c`；r3同内容属于wire派生材料，不能冒充原patch物理找回。

定位依据：[r2相同字节patch](/Users/luo/.codex/task-evidence/ninfer-baseline-29-20261020/recovered-derived-20261021/original-exactbytes-sha-match/gson-r2/pi-business/runs/google__gson-2158/repeat-1/candidate.patch:10)、[r3完整评分汇总](../../../output/ninfer-baseline-29-20261020/slim-transition-20261021/r3-execution-verified.json)的`external_scores`。

r2因复杂bash被旧策略全局abort，8/10只是中止后部分补丁评分；r3普通拒绝后改走`bash verify.sh`并正常stop，完整评分仍为FAIL8/10。故不能说r3失败仍由白名单中止造成。公开verify主要证明编译，不证明隐藏行为。

可指出的代码解释偏差：`null : value.byteValue()`之类条件表达式会装箱，不能据此声称已切换到primitive JsonWriter overload并消除Number路径开销；这也**不是**两项失败的已证实原因。

冻结评分共六个新缺陷selector、四个既有行为selector，empty/gold对照齐备；但r2/r3逐selector实际结果、原hidden verify.log已丢失。目前不能区分“遗漏缺陷边界”与“引入既有行为回归”，更不能猜两项就是float/double。下一次已授权的新候选实验应持久保存selector→原错误→补丁→干净重评分链；本轮不重新评分来补造历史。

## 4. 对greedy proposal + Target sampling路线的更新

B29实测已启用MTP3和生产sampling。固定O源码也已有`speculative_accept_greedy_drafts`及delta接受/残差/bonus路径。因此“改为greedy proposal”本身不是一个尚未拥有的加速来源，O实现存在也不等于新增mixed/W8/W16已取得B29/P6资格。

首轮应复用现有Target sampler/processor/RNG/commit链，仅增加有界Lookup与同宽确定性融合，先W4/K≤3、C1。首轮主要检验提案匹配提升是否覆盖新增成本，不提前启用H4 proposal-skip；没有命中就回既有MTP。完整索引初建/增量更新、查找、传输、mandatory alignment、残差、verify与commit全部计成本。第一轮不做DFlash2、第二套sampler、随机draft full-q或全局selective。

对确定候选d，q=delta，接受概率为处理后的p(d)，拒绝后排除d并归一化其余p；全接受再抽bonus。Target按最终mixed前缀计算每列p，不能复用旧前缀logits或以神经softmax充当确定proposal的q。分布保证依据[Leviathan等人的Algorithm1及证明](https://proceedings.mlr.press/v202/leviathan23a/leviathan23a.pdf)，本次仅采用其算法结论，不迁移论文性能数字。

在恒定条件接受概率α的理想模型中，K个draft的期望许可量为`E_K=1+α+…+α^K`。α=.7时K3→K7只增加约24%，且尚未扣宽verify/对齐成本；因此97类reasoning不应先盲上W16。α=.9时K3→K7理论上约66%增量，复制负载更值得后续试验；这仍不是实测吞吐预测，许可量也不等于经过stop/budget/cancel后的committed量。

W8只在同宽净收益成立、Target数值与状态资格完成且宽度成本实测后尝试。W16/COPY-skip再后置；所有未资格组合默认OFF。P0—P6和既有release DAG不绕过，B29↔BO↔B6身份/codec变化独立解释。

## 5. 收益：给目标和条件情景，不给未测承诺

首个同宽候选以**decode吞吐1.10–1.30×**作为研究目标，仍可能无收益或退化。若decode耗时按该比率缩短、其余耗时完全不变，`S=1/((1-f)+f/R)`给出本批观察混合的条件结果：

| 集合 | decode快10%时总加速 | decode快30%时总加速 |
|---|---:|---:|
| 生产Core | 1.013× | 1.033× |
| O8192长输出 | 1.052× | 1.143× |
| Pi39条 | 1.068× | 1.194× |

这是Amdahl情景，不是已取得或可保证的收益，也不是生产流量预测。热缓存复制负载有更大的可优化份额，冷253K首包不会因proposal优化从153s变成几秒。真实Agent还含工具/构建/评分时间，上表不能直接套成任务wall改善。比率是speedup，不等于相同百分比的耗时下降。

继续使用既有采用门槛：copy/edit wall改善≥15%、真实Agent wall改善≥5%，普通负载不退化并满足既定CI/长context/容量/质量规则。达不到则NO_ADOPTION或INCONCLUSIVE，不以“跑完”替代性能PASS。prefill与L2生命周期问题另设单因素路线，不把其收益算给greedy proposal。

## 6. 验证顺序与预计耗时

详见[冻结前的下一轮验证计划](../plans/07-baseline-informed-validation.md)。先补证据/容量终止/fixture合同，再证明Target分布和commit，再同宽单因素试点，最后才扩宽和正式统计。当前仅批准本评估；下列实施和模型调用均未执行。

| 下一步 | 工作量/运行估计 | 前提与停止规则 |
|---|---|---|
| 证据、B29/BO/B6身份与容量终止审计 | 0.5–1工程日 | 不调采样/预算；未认证源码不冒充B29根因 |
| 数学/processor/RNG/预算1/2/页边界资格及最小同宽Lookup | 2–4工程日 | 可复现隔离构建/GPU与P0—P6前置已满足；缺失则另估 |
| 64请求首轮试点（含预留/2Pi哨兵×2variant） | 约1–2 GPU小时 | 基础48请求按B29估16.49min；4Pi约11.52min，其余含4条自由Java对照及最多8条准备余量 |
| 有收益再扩展，单阶段总量≤240 | 约3–6 GPU小时 | 64包含在240内，所有prep/重试/哨兵均占额度 |
| 正式两variant的1680 O512参考请求 | 纯请求约20.77h | 依原24个cold/warm cell×35×2估算；不能承诺几小时 |
| 上项加52个工程任务、少量预登记Pi、构建/评分与审计 | 规划24–36h，异常可超过48h | 不是deadline保证；52×40min父进程硬上限本身为34h40，不能用上限当期望值 |

因此，在隔离构建与GPU等前置齐备时，**首个可评估同宽原型约3–5工程日；首轮实测1–2小时；正式验收另留1–2天**。W8/W16、DFlash2和全局检索不在此首轮承诺内；额外B29↔BO/B6资格或第三比较轴单独计预算。原精简Baseline从优先阶段启动到结束约7小时14分，含修复、等待、准备、评分，不能当纯推理时间，也不应照搬成下一轮ETA。

## 7. 当前交付边界

本次新增的是评估、离线派生数字和拟验证方案。没有修现网容量逻辑，没有改模型/引擎/codec/采样，没有降低Pi输出预算，没有修改RE003或Gson题目/评分，也没有重启监控、重跑已完成任务或重新声称优化PASS。无法恢复的评分明细与CLI附件继续作为证据缺口。
