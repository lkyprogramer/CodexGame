# 04 · 唯一下一次GPU工作：限额暖态decode资格诊断

## 问题

在P6完整配置、单会话warm append、100K级起始上下文、xhigh采样长输出下，是什么真实依赖阻塞下一批target token提交？其中是否存在足以支持一次工程改造的可消除成本？

这是诊断，不是off/on候选实验，不产生加速或质量结论。不重测HC，不升级main，不扫配置，不改模型，不增加并发。

## 预算与矩阵（事前冻结）

最多1个fresh engine、3条工作请求，依次为100K级prime和两次真实warm append。每请求目标输出固定2048 token，max_output也为2048；正常EOS等短输出完整保留，并以INSUFFICIENT停止，不强迫延长、不补跑。本诊断不是任务质量PASS。

总墙钟≤3600秒，包含启动、加载、冷却、采集与收尾。每个请求deadline不超过600秒，且受全程剩余预算约束；预留至少120秒给本轮进程清理与交接。剩余时间不足下一请求登记deadline和收尾时，不再发送新请求。首个硬失败停止，不重试、不补缺样本、不延长预算。该上限不保证三请求均完成，未运行记NOT_RUN。异常阻止按时归还时，如实标BLOCKED_RESOURCE并优先清理自己的资源。

| 请求 | 条件 | 冻结输入/运行核验 | 输出与deadline |
|---|---|---|---|
| prime | 既有低开销日志，单臂 | 渲染后约100K输入；冻结原语料、模板/tokenizer、body/token hash | 目标/上限2048；≤600秒 |
| append_1 | 同一引擎和conversation | 回传prime真实历史；冻结真实Pi用户追问；观察实际新读量 | 目标/上限2048；≤600秒 |
| append_2 | 同一引擎和conversation | 回传前两次真实历史；冻结真实Pi用户追问；观察实际新读量 | 目标/上限2048；≤600秒 |

材料来自原冻结语料或经授权的Pi脱敏重放，不临时创造容易通过的新quality题。100K是层级，实际token IDs和数量用冻结tokenizer渲染登记。所有请求均须满足完整渲染输入+2048输出预算+4096安全余量≤131072。

保持reply reuse=1/PT0。每次把本引擎真实生成的正文/thinking按现存PT0合同原样回传，再渲染下一请求、保存完整body/token hash并核context预算。不能以标准答案、冻结伪历史或裁剪正文替代自己的历史。

2026-10-30，用户明确选择“保留真实追问，按实际新读量诊断”。此前约3K新读目标及允许区间提案已被该决定替代；此变更不是为了使旧合同通过而放宽验收。

append固定 `new_read_policy=observe_actual_pi_followup`，`new_read_target_tokens=null`、`new_read_allowed_range_tokens=null`。冻结真实Pi用户消息hash及来源，保持真实短追问，不填充文本凑token。`new_read_rationale`说明：实际`read_tokens`包含PT0导致的上一轮正文重读，只记录不按3K或其他新读区间设门。当前两条追问分别61/48字符；字符数不是token计数。每条先登记`append_user_tokens_upper_bound=256`的保守预算；下一请求输入上界至少为上一输入上界+2048输出+该用户token上界+64模板/BPE余量。运行时仍须用冻结tokenizer核实际完整渲染输入+2048+4096≤131072，超界即停止。

运行后保存`prompt_tokens/read/reused/completion_tokens`、真实warm链和完整历史hash，不伪造计数、不重写历史、不补请求。实际历史未生成前，完整渲染hash和实际计数保持null及`RUNTIME_PENDING`。短输出、硬失败和真实历史不符仍保留原件并停止；实际新读量偏离旧3K提案本身不构成失败。

不增加64K层、第二引擎、无采集对照或profiler请求。正式P05仍缺本轮稳定warm fixed2048原件资格；本次三请求完成也不自动解除该BLOCKED_EVIDENCE。

## 采集优先级

只使用已有低开销native窗口日志、SSE、资源采样、CPU pool trace的必要字段。不要开启会关闭真实融合/分支的`STRATA_VERIFY_PROFILE`并据此归因；旧文档已指出该开关改变执行图。如已有日志不足，先记录证据缺口；确需新增窄打点时保持真实路径，仅写预分配有界buffer、请求后导出，不每token打印或同步GPU。扰动无法分离则INSUFFICIENT，不扩大矩阵。

本轮不启动Nsight或新增profiler对照。既有工具看不到依赖边/事件就是UNKNOWN，不默认无命中，不改系统权限，也不开root采集路径。

## 必要数据合同

| 对象 | 必要字段 |
|---|---|
| 运行身份 | run/engine/PID、source/binary/asset/config/patch/hash、线程映射、实际env |
| 请求 | body/token/template hash、cold/warm、read/reused、输入/输出、SSE完成、stop原因 |
| 窗口 | window_id、context、draft长度、committed tokens、完整开始/结束时间、normal/continuation标志 |
| CPU | 实际expert IDs/格式/nt分布；任务完成至join；唤醒/park/排队分开；不默认旧nt分布 |
| GPU | QSA索引/选页/resolve/attention，GDN，resident/miss专家，target/head/commit的依赖区间 |
| 内存 | native RSS/PSS/Swap、major/minor fault差值、VmLck/VmPin、系统swap/PSI可用字段、可用RAM |
| 资源 | 槽数、KV页/epoch、scratch高水位、分配次数、GPU频率/温度/功耗、GPU进程 |

系统swap只能当背景，不能归因给该引擎；`VmSwap>0`是容量，不是本窗口发生swap的充分证据。统计请求前后delta并尽量关联native地址空间/实际等待。只有相关性时报告相关性。

## 关键路径重建

1. 以每个完整verify/commit窗口为闭合区间，统一时钟与PID；SSE事件不是token计数。
2. 根据CPU完成标记、CUDA event/stream依赖、graph launch/节点关系建立DAG。已知分支内只计有效时间，未知边保留。
3. 求实际阻塞join/commit的分支；其内部候选区间取并集，不能重复计CPU等待与GPU同一等待。
4. 给暴露份额范围与证据：已证明部分、未知部分、理论删光上界、可信局部方案下的净界。`tools/headroom.py`只帮算并集和公式，不会从trace自动证明因果。
5. 采集改变了槽数、shape、分派或融合时，原样保留记录并降级为诊断线索；不能外推无插桩的严格上界。

## 需要区分的五种结果

| 结果 | 下一步 |
|---|---|
| 主要是实际CPU专家工作，已近当时内存瓶颈，未见可省路径 | 关闭host调度/泛VNNI/graph重做，记录剩余未知 |
| 主线程可运行但长时间未调度，或同步供给确实让GPU空转 | 先与NP3已测项比差量；没有新机制则不立项 |
| host KV必要页copy/resolve确实阻塞 | 先确认现有4cell去重/CLOCK是否生效；tqLLM名字本身不构成新机制 |
| native活跃页反复fault且与阻塞吻合 | 只针对可证明冗余内存生命周期/重复驻留设计；不直接改swappiness/MMAP |
| QSA选择、某新dtype/shape、scratch等新暴露范围足够大 | 建一张资格回执；需同基线源码差量和具体算法，再选唯一候选 |

## 本阶段输出

`PREREGISTRATION.json`、`IDENTITY.json`、`REQUESTS.jsonl`、`WINDOWS.jsonl`、`DEPENDENCIES.json`、`MEMORY.jsonl`、`QUALIFICATION.json`、`RAW_MANIFEST.json`、`HAND_BACK.json`，以及易读`REPORT.md`。模板见[模板入口](../templates/README.md)。缺字段用null+reason，不伪造0。

允许的终态：`NO_QUALIFIED_CANDIDATE`、`INSUFFICIENT`、`BLOCKED_*`或`ONE_CANDIDATE_PROPOSED`。最后一项仍须P02独立审阅，不能自动进入性能/部署。

## 采样轨迹与采集扰动的限制

每个prime保存实际生成token IDs/hash、stop原因与RNG seed（可得则加RNG状态身份）；append保存完整渲染历史的token/hash，不能只存追加文本的body hash。每窗实际commit/acceptance/dispatch轨迹分别记录。同seed不保证跨引擎轨迹相同。

本轮为单臂资格观察，没有off/on因果对照。日志支持的暴露成本和删光模型只属于当前观察条件，不能称为无插桩严格上界或实际因果加速。prime→append轨迹本来会变化，逐窗记录真实commit/acceptance/dispatch。若依赖不完整或新增打点的扰动无法分离，结果为INSUFFICIENT；不自动增加对照补证据。

必须真正删除`STRATA_VERIFY_PROFILE`环境键并核实际PID。P6用`getenv(...) != nullptr`判断，该键设为0仍改变branch、fusion、shared fork等路径。此限制不能通过“诊断就可以有开销”的说法豁免。
