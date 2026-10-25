# 选中scope的适用断言

原373条原义和旧成绩保留；当前80条对应20任务、4门禁，31个scope（15 candidate＋15 publication＋1 research）为可选实验库。当前仅选K2-T05，不代表全量执行。

| 断言 | 节点 | 必须证明 |
|---|---|---|
| CHATPERF-K0-T01-V01 | K0-T01 | 输入身份不符则停止该候选，不把P5未评审树当P4。 |
| CHATPERF-K0-T01-V02 | K0-T01 | Baseline/P0—P4原始证据不改写、不重复执行。 |
| CHATPERF-K0-T01-V03 | K0-T01 | 调用图区分纯文本、媒体与决策分支，不把media-only move优化声称为文本收益。 |
| CHATPERF-K0-T01-V04 | K0-T01 | 新记录明确research base与完整资格/生产状态的区别。 |
| CHATPERF-K0-T02-V01 | K0-T02 | op、完整round与service wall能关联；不可观测字段为null+原因。 |
| CHATPERF-K0-T02-V02 | K0-T02 | 历史context_capacity与SSE length分别保留，不误归因物理OOM。 |
| CHATPERF-K0-T02-V03 | K0-T02 | 请求、warmup、代理上游、失败、重试及native迭代都进入同一账本。 |
| CHATPERF-K0-T02-V04 | K0-T02 | 不裁剪context或Pi输出，不重发结果未知请求。 |
| CHATPERF-K0-T04-V01 | K0-T04 | 被选实验有可达路径和总成本假设；无热点/资产时记录不选择原因。 |
| CHATPERF-K0-T04-V02 | K0-T04 | 预算是该实验总额，跨任务共享；不把各任务上限相加。 |
| CHATPERF-K0-T04-V03 | K0-T04 | 候选资格与生产发布分开，所有新模型/GPU/训练/下载成本都需其对应授权。 |
| CHATPERF-K0-T04-V04 | K0-T04 | 采用门槛预先声明，统计不足为INCONCLUSIVE；不把HTTP200或接受率当提速。 |
| CHATPERF-K1-T01-V01 | K1-T01 | verify输出、state和conv逐bit等于同编译配置raw；独立oracle未被修改迁就候选。 |
| CHATPERF-K1-T01-V02 | K1-T01 | 有效/无效suffix、count0/1/2/full与尺寸/别名错误受控，不读未写记录。 |
| CHATPERF-K1-T01-V03 | K1-T01 | 数学点积、beta舍入、FMA与更新顺序保持；额外store未改变数值路径。 |
| CHATPERF-K1-T01-V04 | K1-T01 | 实际记录与峰值显存计入成本；不把统一fold或紧凑记录算新增收益。 |
| CHATPERF-K1-T02-V01 | K1-T02 | 未许可/重复fold/错epoch或slot不修改正式状态，conv推进与原路径一致。 |
| CHATPERF-K1-T02-V02 | K1-T02 | Target sampling、processor、RNG、输出预算不变；只greedy命中不给sampling资格。 |
| CHATPERF-K1-T02-V03 | K1-T02 | 整轮计时包含verify、store、同步、fold与fallback；无完整route-hit不给新路径性能结论。 |
| CHATPERF-K1-T02-V04 | K1-T02 | 容量与headroom无倒退；双池新增空间照实记账，不因fold更快就采用。 |
| CHATPERF-K2-T01-V01 | K2-T01 | 独立数值参考与原算子比较，保持已有精度/数值合同，不为PASS放宽阈值。 |
| CHATPERF-K2-T01-V02 | K2-T01 | Graph捕获与真实route-hit一致，未资格shape保持原路径。 |
| CHATPERF-K2-T01-V03 | K2-T01 | 无端到端净收益或资源占用倒退则保留原实现，不能仅报微基准。 |
| CHATPERF-K2-T01-V04 | K2-T01 | 不新增codec/权重格式/35B目标资格，不把Ada误写为不支持FP8。 |
| CHATPERF-K2-T05-V01 | K2-T05 | 完整BF16 Q/K/V输出与conv state逐bit等于raw；复用既有FP64 oracle和阈值，保持pairs数学、FP32累加及BF16舍入。 |
| CHATPERF-K2-T05-V02 | K2-T05 | 仅ordinary Prefill C10240、T>64且<=1024及限定对齐可达候选；实际Graph节点身份、几何及copy参数见证通过，其它路由保留原路径。 |
| CHATPERF-K2-T05-V03 | K2-T05 | 卷积、state更新和raw三次提取copy完整计入段级对照；算法kernel与辅助传输次数及字节分开记账，净收益不冒充完整Prefill或Chat收益。 |
| CHATPERF-K2-T05-V04 | K2-T05 | 无信号、逐bit或资源检查失败即停止并保留原路径；完整Prefill、Chat候选资格与生产发布独立，不自动追加测试。 |
| CHATPERF-K3-T01-V01 | K3-T01 | 同live区间不alias，跨流最后consumer完成才复用。 |
| CHATPERF-K3-T01-V02 | K3-T01 | Graph视图地址与encoding/shape绑定稳定，调优后不悬挂旧view。 |
| CHATPERF-K3-T01-V03 | K3-T01 | 实际可用容量/峰值显存或分配wall有改善且Chat延迟无倒退。 |
| CHATPERF-K3-T01-V04 | K3-T01 | 无真实容量/分配瓶颈则停止，不用理论payload差额冒充实测释放。 |
| CHATPERF-K3-T02-V01 | K3-T02 | 分支无数据依赖，两个scratch及逃逸输出生命周期不重叠误用。 |
| CHATPERF-K3-T02-V02 | K3-T02 | capture/replay、cancel和后续consumer均等待正确join。 |
| CHATPERF-K3-T02-V03 | K3-T02 | 包含同步和资源争用的完整Graph/round有净收益。 |
| CHATPERF-K3-T02-V04 | K3-T02 | 不因Flare使用双流就强行启用；无独立关键路径可记录NOT_SELECTED。 |
| CHATPERF-H1-T01-V01 | H1-T01 | 索引更新、查找、搬运、verify、alignment、commit全部计入完整round。 |
| CHATPERF-H1-T01-V02 | H1-T01 | 命中来源/接受深度可核对；不命中不能给Lookup资格。 |
| CHATPERF-H1-T01-V03 | H1-T01 | 有界内存、不跨请求串用身份；cancel/restore/尾轮按原状态合同。 |
| CHATPERF-H1-T01-V04 | H1-T01 | 在相同Target采样和输出上限下服务wall净改善，工具输出合同不回退。 |
| CHATPERF-H1-T07-V01 | H1-T07 | 独立分布与负例拒绝stale logits、错processor和错RNG；单seed文本一致不是分布证明。 |
| CHATPERF-H1-T07-V02 | H1-T07 | 需要stochastic q的候选必须提供真实条件q及独立正确性证明，否则限deterministic草稿。 |
| CHATPERF-H1-T07-V03 | H1-T07 | 许可、epoch、slot、conv/state和下一轮衔接正确；bonus/anchor/显示token不与commit_columns混淆。 |
| CHATPERF-H1-T07-V04 | H1-T07 | 复用不变合同的既有测试，只为新shape/route补证；不改Target/Pi32768。 |
| CHATPERF-H2-T01-V01 | H2-T01 | draft token映射无歧义、目标支持集和概率未裁剪。 |
| CHATPERF-H2-T01-V02 | H2-T01 | route-hit与独立数值/分布及状态检查覆盖实际候选。 |
| CHATPERF-H2-T01-V03 | H2-T01 | 覆盖/接受深度的下降计入收益，不能只比较head GEMM。 |
| CHATPERF-H2-T01-V04 | H2-T01 | 无可测head瓶颈或净收益即停止，不把多个profile全量资格设为必做。 |
| CHATPERF-H3-T01-V01 | H3-T01 | 所有实际组件支持W8，没有截断context/输出或隐藏fallback。 |
| CHATPERF-H3-T01-V02 | H3-T01 | 各接受深度和尾轮remaining1/2、cancel/partial permit状态正确。 |
| CHATPERF-H3-T01-V03 | H3-T01 | 新宽度的Target分布、RNG与commit_columns映射合格。 |
| CHATPERF-H3-T01-V04 | H3-T01 | 接受tokens/s和服务wall净改善，宽度和显存增加成本完整计入。 |
| CHATPERF-H4-T01-V01 | H4-T01 | W8技术证据已完成且可复用，不为W16重复全W8验收。 |
| CHATPERF-H4-T01-V02 | H4-T01 | GDN、MTP、Attention、Graph、KV和许可/尾轮都覆盖实际W16。 |
| CHATPERF-H4-T01-V03 | H4-T01 | 没有输出/context缩减或采样近似；容量不足保留失败并停止。 |
| CHATPERF-H4-T01-V04 | H4-T01 | W16相对W8净收益超过新增成本，否则不采用。 |
| CHATPERF-H6-T01-V01 | H6-T01 | 精确27B模型/层/特征/词表绑定成立，public DFlash论文不能代替本项目DFlash2资格。 |
| CHATPERF-H6-T01-V02 | H6-T01 | 独立数值、Target分布、RNG、许可/rollback与restore覆盖实际route。 |
| CHATPERF-H6-T01-V03 | H6-T01 | 权重、feature ingress、draft KV、Graph、GPU显存和fallback成本均计入。 |
| CHATPERF-H6-T01-V04 | H6-T01 | 有实际draft命中和完整服务净收益才继续；无兼容资产则明确BLOCKED_ASSET且不耗GPU。 |
| CHATPERF-H7-T01-V01 | H7-T01 | 负例拒绝tokenizer/model/position/feature identity不符及无效旧记录。 |
| CHATPERF-H7-T01-V02 | H7-T01 | 全部来源都由最终前缀Target验证，绝不直接提交检索结果。 |
| CHATPERF-H7-T01-V03 | H7-T01 | 索引、查询、搬运、重建与verify总成本低于收益，局部Lookup对照保留。 |
| CHATPERF-H7-T01-V04 | H7-T01 | 未发现ring外有效命中或搬运成本过大即停止，不要求所有请求建立全局索引。 |
| CHATPERF-S0-T01-V01 | S0-T01 | 只能选择当前已资格route，不能由调度器绕过sampling/容量/状态门禁。 |
| CHATPERF-S0-T01-V02 | S0-T01 | CPU决策、同步、恢复和cache miss的全服务成本进入分母。 |
| CHATPERF-S0-T01-V03 | S0-T01 | cancel/公平进度与原硬边界不退化，不改变业务优先级或采样。 |
| CHATPERF-S0-T01-V04 | S0-T01 | C1收益和混合负载收益分别验证；平均acceptance更高不替代实际wall更低。 |
| CHATPERF-UP-T01-V01 | UP-T01 | 每个被选改动有当前纯Chat调用可达证据、性能假设或必要耦合依赖；提交名不能代替源码判断。 |
| CHATPERF-UP-T01-V02 | UP-T01 | 保留18处G1差异及已修复前端/增量流/并发合同；不采用P5未评审树冒充可构建候选。 |
| CHATPERF-UP-T01-V03 | UP-T01 | 对实际触及的共享状态/缓存版本、取消/故障和Chat做必要验证，完整merge不等于所有模型/协议重新全验。 |
| CHATPERF-UP-T01-V04 | UP-T01 | 完整版计入构建、内存、cache冷启动/迁移与服务wall；无净收益或更大回归则用选择性版本或P4。 |
| CHATPERF-K4-T01-V01 | K4-T01 | 微基准、完整round和Chat服务结论分开，净收益包含所有新增成本且命中真实route。 |
| CHATPERF-K4-T01-V02 | K4-T01 | 选中路径适用的独立数值/采样/许可/资源/容量与Chat合同全过，不要求未启用功能资格。 |
| CHATPERF-K4-T01-V03 | K4-T01 | 预声明收益/质量门槛达到，样本不足或不可观察项如实INCONCLUSIVE；不得宣称旧Baseline已优化通过。 |
| CHATPERF-K4-T01-V04 | K4-T01 | 完整证据及回退工件哈希可复现；C1缺口、18差异、失败/拒绝成本和未来发布未授权状态披露。 |
| CHATPERF-C0-T01-V01 | C0-T01 | 所有分段update/finish、边界与canonical content ID逐字节一致，损坏输入仍被拒绝。 |
| CHATPERF-C0-T01-V02 | C0-T01 | 原SHA-NI路线及小buffer/冷provider初始化不出现未披露回退，BO依赖和服务二进制可构建。 |
| CHATPERF-C0-T01-V03 | C0-T01 | 同构建原实现与候选的大块CPU哈希>=1.7x、缓存publication目标降低>=30%，失败与启动成本全部保留。 |
| CHATPERF-C0-T01-V04 | C0-T01 | 实际cache-constrained Chat服务收益另测；只CPU微基准通过不给推理/发布资格，不重跑历史任务。 |
