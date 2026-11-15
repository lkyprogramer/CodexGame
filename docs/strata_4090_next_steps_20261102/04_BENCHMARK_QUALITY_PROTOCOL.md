# 性能、数值与质量协议

日期：2026-11-02。状态：研究协议草案，**没有启动任何实验**。

本协议继承冻结frontier合同的约束，并区分新Q/T路线。若新路线需要不同的正式主指标、状态构造或质量取舍，必须在结果出现前单独批准，不追溯修改旧P3/P24/P05结论。[S20]

## 1. 身份先于数字

每个run保存以下实际身份，缺项标记 `null / not_observed`，不填猜测值：

| 身份类别 | 必填内容 |
|---|---|
| 源码/构建 | 仓库、commit、补丁diff/hash、binary SHA256、编译器/CUDA/驱动、架构、CMake选项、实际加载库 |
| 资产 | GGUF两分片/pack/MTP/tokenizer/template/草稿词表的hash、来源revision、实际tensor格式 |
| 启动 | 归一化argv及原始argv、env的键值/不存在状态、完整启动日志、CPU线程与亲和、profile身份 |
| 资源 | 物理GPU/显存、CPU/NUMA/内存条通道、可用RAM、PCIe实际链路、cache总预算/slots、actual resident/experts |
| 请求 | 完整脱敏请求body与hash、实际渲染token hash、模板/tools/history、sampling、thinking、输出上限、停止原因 |
| 缓存 | prime/history身份、read/reused、实际warm命中、restore/park、resident阈值与slot状态 |

资产文件太大时优先复用经核验的既有manifest，不在正式性能测量中并行hash数十GB文件。报告所载hash不是本轮现场核验；历史生产状态不是空闲授权。

原冻结B的详细设置见 [01](01_RESEARCH_SUMMARY.md) 和 [06](06_HANDOFF_TEMPLATES.md)。不能以最新v0.2.9替换B后继续沿用原成绩。若迁移后才能获得候选，先批准单独的版本桥接对照；多组件升级的结果只归于该组合，不能单独归因HC/KV/草稿。

## 2. 五层计时，不能互相代换

| 指标 | 定义 | 最常见误用 |
|---|---|---|
| 冷Prefill | 新输入真实read部分的引擎处理区间；同时记总输入/read/reused | 把容量131072当实际输入，或把缓存复用算新读 |
| TTFT-thinking | 请求开始到首thinking事件 | 与首正文/首可见答案混用 |
| Native Decode | 完整decode区间；报告committed tokens、decode_ms及ms/token | 只选最快窗口、把proposed tokens算输出、用wall−TTFT伪造native计时 |
| 完整请求wall | HTTP请求开始到完整响应/约定完成事件 | 忽略前处理、park/restore、收尾 |
| 真实任务 | 完成Java/Pi任务并通过独立验收的预算内时间与成功率 | 失败快、少思考、早EOS算作更快 |

缓存重读另列 `new_read_tokens / reused_tokens / restore_ms / first_event_ms`；0.2秒没有这些字段不能反推100K冷读吞吐。每个指标同时记录计时起终点及事件来源，避免单词“decode”掩盖不同区间。

## 3. 三种工作负载合同

### W-N：原自然warm性能探针

- 建议主场景：约100K实际渲染输入、自然prime→append、fixed2048输出；PT0与真实历史保持。
- 必须已有同B/模板/采样/场景的合格原件，证明warm状态、实际append hash和自然输出长度稳定。当前P01B输出941/576/774，不满足fixed2048；P24的5-token append也不能代替。
- **缺证据时包括A/A校准在内均不自动启动。** 不找容易不断句的新题，不忽略EOS，不重试挑出2048，不截断长答案制造一致。
- 每个prime后，在发送append前检查实际完整请求hash；不符立即停止，保留已耗预算。recipe hash不能替代实际body/token hash。

### W-C：另行批准的受控warm成本实验

- 仅当已有兼容接口能由冻结transcript或状态建立相同逻辑输入与KV/GDN/PLE/MTP前提时使用；不为本计划制造大型回放系统。
- 此合同回答固定状态下的引擎成本，不等于自然Pi历史下的收益，也不回答任务成功率。
- Q格式不同不能直接跨格式加载不兼容快照；用各自正确路径建立逻辑同输入状态，额外构造成本与是否进入主指标需预先约定。
- 必须明确固定的逻辑输入、输出生成方式、停止条件和时间分母。受控重放/teacher-forcing不能标成自然Decode tok/s。

### W-T：真实采样任务

- 两臂任务、初始仓库状态、工具、预算和采样策略一致；允许生成轨迹与输出长度不同，不强求逐token相同。
- 主评价是任务成功率与预算封顶完成时间；保留全部thinking/正文tokens及ms/token作为解释指标。
- 单任务预算为B：成功时 `t*=min(t_success,B)`；未在B内成功（包括断言失败或模型预算耗尽）记B。基础设施失效属于实验无资格，不从幸存任务凑采用结论。
- 若现有适配器不能正确实施该规则，状态是 `BLOCKED_HARNESS`；不要假装通用工具已实现。最小适配器也须另授权、测试、审查。

Q/T路线引起自然prime输出不同，并不允许篡改W-N历史。可预先另选W-C或W-T；它们是新合同，不算“修复了原P05资格”。

## 4. 性能统计与预算

### 4.1 门槛

对批准的主时间指标：

`AA_noise = median(abs(r_AA − 1))`

其中A/A来自事前登记的独立配对、同一基线、同一工作负载、同一主指标。已有合格A/A可复用；一次off/on不能估噪声。

`m = max(0.04, 2 × AA_noise)`

主时间比的95% CI上界须 `≤ 1−m`；非目标时间指标CI上界须 `≤ 1.02`。噪声、主指标与非目标指标先冻结，不能看候选结果后挑选。

原frontier warm指标是完整 `decode_ms`，同时守住wall/TTFT；本包不将它悄悄改名为“最高tok/s”。若Q/T研究更关心完整请求wall或任务封顶时间，应另立合同，将其明确列为主指标，decode只作辅证。主指标通过仍不自动通过质量或部署。

### 4.2 六对固定探针

配对顺序：`AC / CA / CA / AC / AC / CA`。每臂fresh engine，先prime再append；主场景12引擎/24工作请求。A是统计标签，不是生产A0。

第i对：`r_i = C_i/A_i`、`l_i = ln(r_i)`，点比 `exp(mean(l_i))`。六对用完整 `6^6=46656` 整对bootstrap，双侧95%百分位区间。一个引擎里的token、窗口、层不是新的独立样本。

| 阶段 | 预注册上限示例 | 边界 |
|---|---:|---|
| 主场景6对 | 12引擎 /24请求 | 资格与授权齐全后才可运行 |
| 主门通过后4K、120K各2对 | 增8引擎 /16请求 | 描述性支持/异常筛查，不建立正式2%非劣 |
| 主+支持合计 | 20引擎 /40请求 | 不是自动全跑预算 |
| 若事前另批3对A/A | 再增6引擎 /12请求 | 总计26/52；不得候选出结果后再追加 |

这些数不含最小语义测试、质量留出集、热稳定测试；所有阶段必须有独立上限和总上限。当前本包的硬件执行预算是 **0**。120K场景实际输入至多122880，输出和4096安全余量仍要逐请求核算。

若CI太宽，结论 `INSUFFICIENT`；不看到接近显著就继续加样本。后续扩大必须新预注册，原轮完整保留，不无条件合并两轮。

### 4.3 统计工具的边界

既有 `tools/paired_stats.py` 适用于固定探针完整性/时间门；不得把变长真实任务强塞进要求同输出长度的工具。工具exit0不证明输入真实、绝对质量合格或可生产采用。所有适配都复用已审工具、增加最小必要校验，不另造大型benchmark平台。

## 5. 数值与采样语义

### E0：表示变化但数学/分派/规约不变

采用 `B → A1关闭 → C开启` 两次桥接，A0不参与跨版本bitwise对照。先证明同一有效快照的B重复执行可逐bit复现，再比较B/A1及A1/C。

有效比较域为canonical的层、逻辑token、head/expert、row/column、K/V或状态角色；检查logits、有效KV/GDN/PLE/draft状态、scale、位置和提交点。layout变化不能直接比物理slot整块；padding未初始化区不比，但独立验证映射、valid/causal mask、ownership、row/scatter顺序。

负控制至少包括：错误input/route/layout/state身份被拒绝、故意一字节差异可检出。只哈希相同不足以完成内容与语义证明。

自然CPU/GPU分派变化可能破坏整机bitwise，不能强制关CPUshare制造“无损”。局部固定路径E0与自然路径分级分别报告。[S20]

### E1/Q：数值或目标精度改变

事前冻结允许误差的测量定义、质量损害预算、关键失败零容忍项；本包不代填任意KL容差。出现NaN/Inf、状态丢失、漏专家等属于错误，不是可接受数值漂移。Q1/Q2不得仅用“top1大多相同”豁免任务质量。

### 草稿特殊要求

greedy对齐不足以证明temperature=1的采样分布。先审实际算法：若用p/q拒绝采样，证明接受 `min(1,p/q)` 与拒绝残差；若用exact-match/耦合链，证明该链保持target采样及随机数语义。不得假设不同引擎/PR共享同一种算法。

检查拒绝后KV/GDN/PLE/position/草稿状态与commit完整回滚；全拒绝、首个接受后拒绝、全接受、EOS、取消、下一请求分别覆盖。冻结原target tail-skip行为，不用“同GGUF”偷换成全专家target。

## 6. 质量：相对非劣与绝对成功分开

| 层次 | 作用 | 不能宣称 |
|---|---|---|
| teacher-forcing / KL / top1 | 定位数值变化，检查明显异常 | 等同真实长Agent质量 |
| 少量开发/哨兵任务 | 发现复制、代码、工具、长文风险，供早停 | 30对全一致就有2pp非劣 |
| 独立留出任务 | 估计真实成功率差及预算内时间 | 把同题多seed/token当新任务 |
| 固定六项长检索 | 保留既有绝对失败并逐项诊断 | 两臂都错就代表质量已经过关 |

任务四格中，b=基线成功/候选失败，c=基线失败/候选成功，n为独立任务对总数。沿用保守门：

`CP_upper(b,n,0.025) − CP_lower(c,n,0.025) ≤ 0.02`

全一致时按此公式至少183对才越过2pp边界：`1−0.025^(1/183)≈0.019956`。**183不是通用样本量推荐**；任务分层、实际不一致率、独立性和代表性决定是否还需更多证据，不能为凑数量换轻题。

开发集与留出集先冻结；多候选反复看同一留出集不再独立。本包默认一次仅一个候选。相对门通过但原六FAIL未解决，最终最多 `RESEARCH_RESULT_ONLY / BLOCKED_QUALITY`，不能写READY或建议上线。若未来要改变绝对质量合同，必须由用户明确接受业务取舍，不在本包中默许。

## 7. 资源与执行安全

- 目标：4090 SM89 / Xeon4216 /约64GB RAM；历史编译CUDA12.3，禁止为比较自动更换驱动/工具链。
- 85°C、MemAvailable<4096 MiB、外来GPU进程、OOM、错资产、预算越界均停止；不得杀外来进程或降低门槛继续。
- 实验端口只可在另行批准且确认空闲后使用127.0.0.1:18089；不碰生产18343、unit、NGINX、旧回滚树。若生产占GPU，报告阻塞，不能先停服务再问。
- `STRATA_STAGE_PIN`、`STRATA_ROUTE_RESIDENT`不进入旧合同。诊断中的managed/oracle/profiler配置单独命名，不能混入正式性能。
- 正式臂删除presence-sensitive profiler环境键，不能设为0；参数、采样、资源采样开销两臂一致。
- 温度起点/冷却政策事前冻结；保留major faults、swap、时钟、温度、实际auto slots，不事后剔除慢样本或按时钟归一化挽救。
- 不在正式测量同时压缩/上传trace或hash模型。小样本不能给可靠p99或全天稳定承诺。
- 任何热/质量/功能测试都计入独立预算；本包没有“为了验证可无限运行”的隐含权限。

## 8. 状态必须可拆解

每个结果至少有：`mechanism_status`、`numeric_status`、`performance_status`、`relative_quality_status`、`absolute_quality_status`、`thermal_status`、`production_state_changed`。未知填 `NOT_RUN / NOT_OBSERVED`，缺证填 `BLOCKED_*`；不得用单个PASS掩盖其他未过门项。

`production_state_changed=false`只描述实验/文档是否改动过生产，不代表服务当前running。本轮状态为文档交付、硬件 `NOT_RUN`，而不是新的benchmark结果。
