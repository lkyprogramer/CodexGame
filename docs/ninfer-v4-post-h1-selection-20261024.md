# H1收尾与下一项选择：先验证现有W6扩宽

**H1-T01正式收尾，追加预算0。下一项选择H3-T01 Stage A：复用已有C1/W6、K5 MTP执行链，与当前W4/K3做完整decode对照。** 本轮仅通过`jssh 29`核对源码、身份、现有证据并更新文档，没有实施补丁、构建、旧测试或GPU/模型/HTTP请求。新分支尚未创建，未来实机预算是提案。

## 已有结果和实时身份

H1的2个native场景逐bit通过，47/128正式候选轮选中Lookup；复制、工具、控制的完整decode每报告token成本分别增加6.98%、4.28%、8.11%。单对独立随机输出、两个正例受既有重复保护截断，不能推成普遍回退，也没有采用信号。4条原`FAIL_MODEL_BEHAVIOR`及wire `length`保留；Engine原因为`repetition_cycle`，并非2048输出上限用尽。控制也命中Lookup，no-hit成本仍缺证据。关闭该profile不代表原4项资格断言通过。

[收尾回执](../output/ninfer-v4-post-h1-selection-20261024/H1-T01-closeout.json)绑定原分析、账本、交付及原报告SHA；不修改旧raw、账本或评分。C0、K2-T01、K1-T01、K2-T05继续关闭，均不追加补测。18处G1差异、C1附件缺口、Baseline坏raw/无法恢复附件以及所有原失败和成本原样保留。

本轮2026-10-24 07:05 UTC只读回查：原`ninfer-4090-prod`为STOPPED/PID0，镜像、argv身份未变，GPU无计算进程，lease可用；H1已结束账本COMPLETE。当前H1树`9e7c0a1f19721d0ba63db362da6d10b5cda7c8e0`只用于历史证据。下一项从raw对照树`a5ba33de12d75ab1e16a153020e4068094ee1757`开始，避免叠加未采用Lookup或T1024分派。该raw工作区无未暂存差异，读取的24个源码文件与固定Git树blob逐字节一致。[实时回执](../output/ninfer-v4-post-h1-selection-20261024/remote/live-snapshot.json)、[源码见证](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses.json)、[补充见证](../output/ninfer-v4-post-h1-selection-20261024/remote/source-supplement.json)。最初猜测的`graph_plans_impl.h`不存在已记录，随后找到实际`graph_impl.h`；没有把文件名猜测当源码结论。

## 为什么先做W6

H1两个正例的raw实际每轮提交3.880/3.944 token，已接近W4上限4。在相同轨迹和整轮成本的假设下，同宽仅改善proposal接受量的节时上限约3.01%/1.39%。这只约束这两个被保护截断的简单样本，不代表真实代码负载的接受率。观察到整轮约23.2ms；因此值得先问：**扩大每轮正式产出，能否减少完整Target轮数？**

源码支持比W8更小的首步：

- 27B及共享round state最大MTP草稿数为5，已有W6 host/rope/许可和下一轮buffer；layouts接受K1..5，MTP对齐、AR循环及Graph按配置宽度工作。
- 实际Target全词表head为248320×5120，Q6路由对T6已有`r8_c6`，不是需要开发新kernel；现有优化proposal head为131072，保持原格式和支持集策略。
- GQA small-T阈值就是6，编译/launcher包含T1..6及packed-K/rotated-V分支，可覆盖当前rk4v4路径的源码资格。**这只是静态支持，不是W6实机通过。**
- 原P3通用T目录为1/2/3/4/8/12/16/24/32/33，不能把这些旧PASS冒充T6资格。数学参考和诊断工具可复用，只新增必要T6行。

真源：[最大草稿数](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses/src/targets/qwen3_8_27b/impl/config.h:98)、[轮状态布局](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses/src/targets/qwen3_8/export/ninfer/targets/qwen3_8/round_state.h:15)、[MTP执行链](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses/src/targets/qwen3_8/impl/runtime/mtp_impl.h)、[Q6分派](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses/src/ops/linear/q6/q6_dispatch.cpp:11)、[GQA路由](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses/src/ops/wrapper/gqa_attention.cpp:359)、[实际packed分支](../output/ninfer-v4-post-h1-selection-20261024/remote/source-witnesses/src/ops/launcher/gqa_attention_decode.cu:272)。

| 方向 | 当前判断 |
|---|---|
| 现有W6/K5完整执行链 | 选中。已有入口和kernel，工程范围较小，直接检验轮数与整轮代价。 |
| 直接实现W8/W16 | 需要突破当前MTP最大5和GQA六列边界；先用W6验证接受增长，避免先支付整链扩宽成本。 |
| 再试同宽Lookup/norm/correction/卷积 | 对应profile已收尾，不换夹具或shape继续补测；保留现有正负证据。 |
| Q4/Q5、draft-head再裁剪 | 现有small-T、split-K和优化head已存在，不能重新命名为新优化；尚无足够分项证据支持哪种新路由。 |
| Workspace、有限fork/join | 仍有理论价值，当前缺生命周期峰值和独立关键路径证据，先不扩大实现。 |
| DFlash2、全局检索、utility、选择性上游性能合入 | 保持条件研究，不成为本项前置；本轮不新增资产、索引或调度器。 |

这是基于已知实现成本和可证伪性的排序，不是W6收益已获证明。旧Baseline用于宏观边界，H1用于当前执行链观察；不把两个简单正例的接受率外推为生产加速率。

## 实施范围

profile为`MTP_EXISTING_C1_W6_K5_VS_W4_K3_V1`，拟议分支`codex/h3-w6-existing-route-20261024`。只在隔离候选显式选择已有draft数5，控制为3；产品默认分派、Target采样、greedy proposal算法、mandatory MTP对齐/下一轮、许可Fold、缓存格式、context262144及Pi medium/32768保持原合同。若配置已足够，不为了交付“补丁”发明产品改动。

工程交付限于：BO依赖闭合与可构建诊断驱动、W6精确边界合同、请求/轮级真实计量、新夹具、预算与owner控制器、定向CPU检查和集成评审。确证的接线缺陷可在隔离分支修复，但不改数学或放宽断言。原H1观测代码可选择性复用，不能把Lookup逻辑或其开关整个带入。诊断宏默认OFF，核对实际消费模型TU的编译参数；oracle不暴露为HTTP功能。

native比较采用**相同物理W6**的Target逐步参考，不要求W4和W6因不同数值路由仍全量逐bit。参考只把测试用逻辑proposal extent设0，每轮实际调用Target sampler；请求输出预算仍32768。取参考正式生成的前5个真实ID作为W6候选包，在完整Target verify前入包，必须实际观察接受5/许可6。oracle只证明状态事务，不计为真实MTP命中率或性能样本；不改Target logits/acceptance/RNG。比较对应因果列、FP32 state、conv和已许可KV；完全许可场景另比较终态清理前的下一轮MTP。若同宽比较不满足原逐bit合同，保留FAIL，不改成容差PASS。

第二场景复用同一prefix/seed的真实Target oracle，完整W6验证后只许可1个token并终态清理；仅比较共同首列和正式许可state，丢弃列及其下一轮草稿不伪造为可比状态。剩余1/2、拒绝深度0..5、cancel/reset先做定向CPU合同；完整随机分布、恢复、长时稳定性和发布仍独立验收，本pilot不声称穷尽。

## 最小新增验证与耗时

**以下预算尚未冻结为可执行窗口，本轮不启动。** 不重跑旧Baseline、H1、P3矩阵或已通过数值/Graph场景。

| 新增范围 | 上限 | 用途 |
|---|---:|---|
| CPU合同 | 16场景 | K5/layout/headroom/许可深度、诊断隔离及夹具保护检查 |
| T6数值/Graph | 8场景、10 direct Op、8 capture、16 replay（含warmup） | 新Q5残差2项、Q4 SwiGLU、Attention/GDN输入投影、Q6全Target head、rk4v4 GQA、raw GDN Record/Fold链；前7项各1 Op，末项3 Op |
| native状态 | 2场景、4次请求；计划9次、上限16次decode/verify | 同宽Target参考6＋候选1，terminal partial参考1＋候选1；全部使用真实模型 |
| Chat | 3对＝6请求＋2 warmup | W4/W6各1次新代码、新具名工具JSON、新低重复控制 |
| wire/模型提交 | 10 wire＝8模型HTTP＋2 health；共12次模型工作提交＝native4＋HTTP8 | 不把native调用次数混成模型请求，不自动重试 |
| GPU窗口 | 预计5–10分钟；硬20分钟，第17分钟清理 | 拟1个native进程＋W4/W6两个HTTP进程，最多3次模型加载 |

数值8 capture/16 replay是新增独立Op套件预算；**模型startup/Graph capture/replay、算法kernel、copy/memset及字节上限尚待新驱动逐路径枚举并冻结**，不能把上述8/16当全窗口资源总量。当前`GPU_resource_envelope=null`明确阻止执行，不是无限预算。BO/旧依赖构建与FP64参考复用，Q6/GQA未覆盖的独立参考应在新驱动内补齐，不能拿待测kernel自比冒充数值真源。资源不足保持262144，停止并记缺口，不降context或输出。

夹具必须是新任务：代码每行和工具每条记录使用唯一ID，避免原H1相同短串循环；在CPU用真实tokenizer检查期望输出通过原RepetitionGuard，不改保护阈值、不重跑原H1。实际回答仍可能触发保护，应保存Engine finish reason、raw和不完整工具证据，不能把HTTP200或期望输出静态检查当实机质量PASS。Chat沿用新夹具2048输出上限，Pi预算32768不动。

预计CPU/BO/驱动/夹具/账本与评审合计**8–16工程小时，约1–2工程日**；GPU另5–10分钟，结果审计0.5–1小时。依赖缓存若命中则倾向下界；出现真实接口缺陷会单列剩余范围，不追加同类补测掩盖失败。

## 收益判据与停止条件

**预期收益数值为null。** 首筛采用信号：两个有效正例的完整decode wall/实际committed token下降≥10%，控制回退≤5%；服务wall、TTFT、接受深度0..5、正式token/轮和整轮成本同时报告。10%/5%是新profile的取舍阈值，不是放宽旧H1门槛，也不是速度承诺；一对样本不能给出p95、置信区间或生产资格。

设R为完整轮成本、G为实际正式提交token/轮：成本比为`(R6/G6)/(R4/G4)`。若W6每轮贵20%，W4每轮产出3.9，则W6需超过4.68才盈亏平衡；节时10%需至少5.2。六列相对四列只增加理论产出上限50%，**不等于实测1.5倍加速**。多出的2次MTP AR、全量verify、Graph/workspace/许可成本均计入R6；接受后两列不足时可能变慢。

没有真实W6 route、状态失败、保护截断导致正例无效、OOM或未达净收益时，就保留原W4并关闭该profile；不自动扩W8、加样本、缩context、改采样或重放已结束请求。W8原具名断言/候选及发布scope继续PENDING，W6 pilot不通过其中任一门禁；候选资格与生产发布分离。本轮只给出下一项，不实施优化。原GPU服务保持停止，`p95=null`、`optimization_qualification=false`。

[机器化范围与预算](../output/ninfer-v4-post-h1-selection-20261024/selection.json) · [证据与推断边界](../output/ninfer-v4-post-h1-selection-20261024/evidence-assessment.json) · [文档检查](../output/ninfer-v4-post-h1-selection-20261024/document-validation.json)。
