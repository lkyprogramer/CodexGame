# 测试矩阵：一小时筛选与分阶段发布门

## 1. 时间范围

“一小时”仅指**候选已经编译、模型已准备、adapter已实现后的单轮筛选**。不包括开发、下载、编译、首次kernel JIT和完整质量benchmark。超时生成`INCOMPLETE/BLOCKED`，不删测试凑PASS。一个阶段不通过即可退出并恢复生产。GPU角色串行，绝不可同时加载baseline+candidate。

## 2. 筛选计划：一轮一个长度桶（2026-09-09按现网实测重排）

按现网数字（`22 §4.6`）：184K样本≈105s；8个ABBA配对=16次≈28min；baseline/candidate不能同驻，每次切换重启≈40s×16≈11min。原表"15分钟做4K/64K/184K三桶各5配对"算不出来，会让执行AI按做不到的数字排程。改为三种run类型，每次GPU维护窗口跑其中一种：

| Run类型 | 预算 | 工作 |
|---|---:|---|
| **R-protocol**（身份/协议/生命周期/质量） | ≈55min | 5min hash/flags、tools/stream smoke、真实sampler；**10min A/A噪声底**（同harness同桶，baseline对baseline，得`aa_noise_abs`）；10min prefix/lifecycle（L1–L4）；15min原3题fresh + 30语义题；10min容量L5（≈196K+2048，OOM/截断）；5min回到生产smoke与汇总 |
| **R-perf-184K** | ≈45min | 184K桶，实际输出≥1024，**8配对ABBA跨两次启动**（≈40min）；汇总5min。这是产品主桶，单独一轮 |
| **R-perf-short** | ≈35min | 4K与64K各8配对（4K≈2min/对、64K≈6min/对含切换）；汇总5min |

**有效decode样本的最低条件**（同时满足，否则该样本不计入任何门，也不计入A/A噪声底）：实际`completion_tokens ≥ 1024`；`reasoning_effort=medium`且引擎默认采样（T=1.0/top-p 0.95/top-k 20，不在客户端覆盖temperature）；prompt落在声明的桶（4K/64K/184K）内；请求日志能对应到每轮`draft_n/draft_n_accepted`（T02遥测）。`timings.predicted_per_second`在5–32 token输出下量的是一两轮的固定开销，不是吞吐；2026-09-09一次误执行正是拿这类样本得出"219 t/s"与"慢18.5%"（`AGENT_START §已发生过的误执行`）。

R-protocol必须先于任何R-perf跑过且A/A噪声≤3%；否则R-perf结果只能标INCOMPLETE。预算不是机器运行时间承诺；超预算的项标`INCOMPLETE/BLOCKED`，不把计划悄悄降成一两个prompt。默认一轮聚焦一个补丁，不同时扫所有算法。

## 3. 核心case定义

**L1 append**：构造60K多message Java会话，run0结束后严格带回assistant原文，再append1K tool result。验证reused/TTFT，单纯exactrepeat不替代append。带GDN的引擎若只保留endpoint，exactrepeat miss可以是策略，不能算算法坏。

**L2 newest-user rewrite**：为A和B各独立建立相同前置状态，再只改最新user reminder。不得像报告12-B那样先扩展另一分支再回到旧prefix，却标记为“相同测试”。

**L3 branch rewind**：明确先A0→A1，再A0→B1；这个压力项单独记录，不与L2混合。只有production真实需要才决定是否投资额外anchors。

**L4 cancel/stop**：取消在proposal后/verify后/提交前后；stop串跨token、EOS在块内、max_tokens1/2/K±1。后续fresh请求不得受残留影响。检查exact state frontier，不只看服务器没有崩。

**L5 capacity**：构造不重复单句的大量代码/文档片段；调用tokenizer/engine实际计数到约196000；放5个随机值于5/25/50/75/95%并要求检索+代码细节。reserved总tokens必须≤200192（docs/02 §3），完成至少2048再统计持续decode。质量probe短答可单独执行，不用强制垃圾重复填满2048。

## 4. 数值门分级

N0 schema/codec/索引：要求bit-exact（包括既有半陪集近似，不擅自变更）。
N1同target算术优化：输出/状态按预登记oracle，先跑baseline-vs-baseline量噪声；不能临时扩大tolerance。
N2 proposal：p/q解析式与toy exhaustive测试；GPU采样固定条件大量抽样，控制多重检验，报告TV/置信区间；统计不显著≠数学证明。
N3 target低精度：额外holdout/既有Hard/公开质量集，并记录误差分布、失败任务与回退。

## 5. 判定

- `BLOCKED`：缺权限、模型hash、adapter、engine字段或未完成必要测试；主桶配对数<8；A/A噪声底>3%。
- `NO_GO`：质量/状态/采样/OOM失败。
- `TRADEOFF_ONLY`：容量降到200192以下或其他受保护能力改变，即使快。200192本身通过容量门（用户决策，docs/02 §1）。
- `NO_MEASURABLE_PRODUCT_GAIN`：正确但配对收益不足或任务wall回退。
- `CANDIDATE_PASS_NOT_RELEASED`：筛选通过，尚未完成soak、恢复签收和用户批准。

最终生产资格需至少三次独立测试会话、不同seed的真实Java/Pi回归、2小时以上定向soak以及恢复检查。任务时间受用户预算约束时可以只做到筛选，不冒充长期稳定性验证。
