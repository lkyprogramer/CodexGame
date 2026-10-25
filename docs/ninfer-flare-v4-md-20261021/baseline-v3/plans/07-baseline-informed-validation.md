# Baseline完成后的验证顺序与预算提案

状态：PROPOSAL_ONLY，2026-10-21。当前授权仅为[完成后的评估](../research/04-completed-baseline-assessment.md)和文档修订；没有启动本页实验。P0—P6、H0—H8及原采用门槛保持有效。本页细化下一轮最小试验，不新增自动执行入口，不恢复已完成Baseline或旧监控。

## S0：先锁证据与正确性风险

1. 保留278参考/8+2评分、原4项row gap、5条Pi输入拒绝、两条Responses拒绝、旧3坏raw及53+8缺失附件。旧分母和RE003-v1 FAIL不改。公开汇总不包含私有prompt或隐藏测试正文。
2. 将RE003-v1标为模型归因不合格，未来另冻RE003-v2合同与baseline；Gson逐selector原结果unknown，不猜两项失败，不重新评分补历史。未来新run把CLI/raw/patch/identity/每selector结果先写持久根并哈希，完成/中止都不能只留总分。
3. 核查B29源码/二进制与BO/B6来源。针对97及Core72条`context_capacity`，先区分input容量、effective output预算、末轮remaining、main/aux页entitlement/ceiling、pool free/retained页和try-grow拒绝原因。前者HTTP400、运行中容量截停和正常output_limit必须分开。
4. 在隔离候选环境加入低开销round/commit/headroom理由和高水位计量；ON/OFF计量开销按原≤2%合同验证。不要以每层cuda同步改变被测路径。B29不能提供的字段保留null。

预算1/2、尾轮K不足、页边界、logical capacity附近、cold/warm/restore以及C1隔离都需独立数值/状态测试。O源码只是定位线索，未认证同构前不能把try-grow失败直接认定物理OOM或已证实的off-by-one。发现正确性缺陷先单独修复/验收，不把修bug收益并进Lookup单因素。

时间：0.5–1工程日，环境/源码不能复现时明确BLOCKED并重估，不偷偷改现网测试。

## S1：delta proposal的Target sampling共同资格

依design/11与H1-T07复用现有sampler，不另造接受器。tiny精确枚举先验证条件joint分布、fractional接受/残差、p(d)=0/1与bonus。随后比较ordinary/verify最终prefix的Target数值、processor顺序/count overlay、RNG purpose、eager/graph和最终commit；不是只对Target-greedy输出相同。

保持temperature1、top_p.95、top_k20、presence0、medium/preserve-thinking及原支持的其他参数。greedy只用于proposal，不能将top_k1或Target温度0的测试算生产sampling通过。accepted、licensed、committed、stop裁剪分开记。源/shape/route未实际覆盖或fallback冒充命中均不得过门。

S0/S1加最小Lookup原型合计规划2–4工程日，前提是隔离构建/GPU与P0—P6已齐；这不是CPU测试本身要运行数天。

## S2：同宽Lookup，先小试点

首个候选只C1、原已资格W4/K≤3，按design/01有界request-local索引及保守fusion；MTP/Target状态及mandatory alignment照原合同。**首轮不启H4 proposal-skip**，同宽主要检验接受提升能否覆盖索引/融合成本。普通自由生成与无命中路径必须同行对照。

统一在候选对应的合格基础B6上比较A/B，必要时另做B29回归；B29不能冒充A0/B6。同一试验只改Lookup/fusion，不能顺便改codec、采样、reasoning或输出预算。

试点最多64个实际HTTP模型请求，包含所有准备和哨兵：

| 项目 | 计算 | 请求上限 |
|---|---|---:|
| 性能配对 | P32768/131072×copy/tool JSON×cold/warm×A/B×3时间block | 48 |
| Pi诊断哨兵 | f89c5dcc、97fc7be6×A/B，每条原medium/O32768 | 4 |
| 自由Java对照及准备预留 | 至少4条为P32768/free_java/cold-warm×A/B；其余最多8条准备/漂移/暖状态，未用不补跑 | 12 |
| 总计 | 包含准备，不是48之外再无限加warmup | **64** |

冻结block内交错顺序及cold/warm准备，按实际hit检查条件，不能把跨variant缓存污染当warm收益。记录真实命中/无命中、source、index初建/append/查找/传输、draft/verify/alignment/commit成本、最终committed与E2E；不得拿a+1或accepted/drafted直接当业务速度。

48个主请求以本批相同8个cell×3×2外推，约989.22s；两个Pi的A/B约691.26s。另含4条自由Java对照，Lookup实际无命中须按route计数单列，不能预先假定；未观察到无命中则相应guard仍未资格，不能隐藏扩预算。计入准备、漂移、观测开销和审计，规划1–2 GPU小时。它只能筛选方向，不能给p95或总体质量提升结论。

明显退化、没有实际命中或更宽/更大内存才能勉强获益时，先停并说明。通过才在本阶段**总额度≤240**内扩展非copy、196608/253952和长输出；64包含在240内。深筛规划3–6 GPU小时，所有模型重试/前置/哨兵均入总额度，硬数值测试另记。不得无限加样本直到显著。

## S3：按成本证据决定扩宽

先测真实α_i与整轮成本，再决定W8；W16、COPY-skip依H4后置。理想K3→K7的许可量增益不足以覆盖verify/align/资源增长时，不尝试更宽。97类低接受reasoning不能拿高copy命中率代替其资格。任何new width必须重做对应数值、sampling、预算/页边界、Graph/restore资格，不继承W4 PASS。

不把DFlash2/full-q/TokenTree/global selective纳入首轮收益或时间承诺；这些仍按各原阶段和资产条件另估。

## S4：正式采纳验证

仍按plans/06和design/07事前冻结profile、桶、CI、追加预算及质量/资源/容量规则；每个实际p95桶/variant≥100、至少5独立block及关键case≥10有效配对，功效不足仍INCONCLUSIVE。

原示例P32768/131072/196608/253952×3非copy×35 warm/variant，配cold后两variant共1680请求。按本批对应24个cold/warm cell×35×2，纯请求外推**20.77小时**；加52工程运行、少量预登记Pi holdout、构建/评分和审计，规划24–36小时，异常可超过48小时。候选比B29快多少尚未知；BO/B6先决资格、第三比较轴、额外profile/长输出p95都单列，不隐入此估计。

每repo仍Pi1800s、可信评分外层450s/容器420s、父进程2400s，24turn/60tool/O32768不变。52×父进程40min=34h40是工程任务极端上限，并非期望；Pi哨兵每请求40min上限也不代表都只需数秒。

RE003合同修正会形成新版本回归集，不能将v2分数与v1不一致oracle直接配对。现在已分析过的Gson/RE003及两Pi只作为诊断哨兵，不能又叫未参与调参的holdout。正式发布另外冻结未用于调参的案例/seed；保留全部中止、耗尽和失败成本，不能用pass@3覆盖逐seed失败。

采纳需copy/edit wall≥15%改善、真实Agent wall≥5%改善及原普通负载、长context、尾延迟、质量、可靠性、资源guardrail满足。仅copy收益只开放明确copy profile；无收益NO_ADOPTION、CI不足INCONCLUSIVE。保持p95=null直到真正取得所需证据。

## 当前决定

建议批准下一次工作时先做S0/S1与同宽小试点；本页只是建议，不是实施许可。本轮已经完成离线评估，不重跑旧任务，不修改现网或重新创建监控。最小可评估原型在前置齐备下约3–5工程日；实测和正式验收分别另留上述GPU时间。首次结果不支持直接承诺2×、更长Pi任务成功率提高或普遍首包加速。
