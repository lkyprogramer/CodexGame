# 12 · R02/R04/R05：可变循环、LoopCD与交互实验

## 1. 研究身份与事实边界

R02建立varloop oracle/结构态adapter，R04研究LoopCD，R05组合已合格的机制；均不改变固定Mini主线或保证收益。ARLoop仅是验证载体。

本章LoopCD指 **Liu等，*Decoding Looped Transformers Better for (Almost) Free*，arXiv:2610.02185v1**。[S10] `byeonghoyu/LoopCD`属于Yu等 *LoopCD: Loop-wise Contrastive Decoding for Improving Reasoning in Looped Language Models*，arXiv:2609.24196 / EMNLP main.1367，不能当作前者官方实现。指定论文的官方代码本轮未核实，R04需自行复现。

## 2. R02：varloop oracle与adapter

### 先决条件与资产

依赖03资产、05事务和任务DAG。正式Mini的 `is_varloop=false`，研究模型为true且后期训练不同，不能只改正式config冒充研究checkpoint。varloop训练覆盖1–5 passes，比例1:2:6:2:1，之后按3 passes post-train；不同R是不同目标。[S14及03官方资产]

复现2DSD使用训练target `thinkingmachines/TML-d24-varloop-research@657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2`，不替换成main；不同版本禁止复用cache。原生DSpark固定visit、只支持默认R3，不能与5层2DSD drafter互换，详03/11。[S09/S14]

### 拟新增接口与不变量

`LoopSchedule`显式映射physical_layer、execution_visit、logical_cache_slot。该架构的访问数为 `6+12*R+6`，但slot必须遵守实际引擎重排，不能假设slot等于visit。每次改变R建立新model epoch和cache arena。

`LoopStateView`包含prelude基准、active residual、completed blocks、message bank、controller及pass/phase；保留各pass KV/conv。**Inkling不是单一h反复执行core**；任意层输出不能直接当早循环预测。05的重建输入、message注入和norm边界必须保留。

`readout_at_pass(state, private_state)`运行coda时不得写入正式历史。`snapshot/fork/replay`复用05；scratch仅在证明可重算后省略，并验证后续decode。

### 试验顺序、验收、停止

1. R3、per-loop、无draft、无guidance，建立串行oracle；记录量化、kernel、模板和sampler。比较prefill与分段decode，含1023/1024/1025边界，恢复后再生成64token。
2. 输出48次visit与slot trace，确认feature语义、controller/conv状态及coda一次执行。与独立参考对齐logits/state；低精度容差和near-tie差异按13登记。
3. 同一研究checkpoint逐项R=1、2、3、4、5；每项重新分配状态、独立指纹，不复用前项cache。此阶段禁用原生DSpark的非R3组合。
4. 记录正确率、生成token数、完整任务wall time、TTFT、TPOT和峰值内存。更多loop可能改变CoT长度，tok/s不代表任务时间；R>5另列训练外推实验。

每个R独立过状态/质量门才记 `PASS`；缺参考/adapter为 `BLOCKED`，不可解释状态差异为 `FAIL`。在线逐token自适应退出尚无已核实接入。未达01收益且无容量/质量价值，记 `NO_BENEFIT`。

## 3. R04：LoopCD 的目标公式

对同一prefix，`h_R`为最终循环状态，`h_b`为较早参考；`C`表示coda，`H`表示最终norm与词表投影。论文主式使用b=1，部分实验另选参考。[S10]

**Hidden：**

`h' = (1+omega)*h_R - omega*h_b`

`z' = H(C(h'))`

固定omega只执行一次coda/head，仍有保存状态、组合和内存访问成本。**Logits：**

`z_R = H(C(h_R)); z_b = H(C(h_b))`

`z' = (1+omega)*z_R - omega*z_b`

参考分支额外运行的是 **coda加head**，不只是一次vocabulary projection。温度/截断之前，Logits形式对应 `p'(v) ∝ p_R(v)^(1+omega) / p_b(v)^omega`；非线性coda下不能把此恒等式直接套给Hidden。

adaptive系数为 `omega_max * [1-(p_R,(1)-p_R,(2))]`。论文的Hidden采用fixed；若Hidden也要先求unguided概率，再求guided输出，会多跑coda/head，失去单output-pass优势。论文覆盖Ouro、Huginn、Parcae、Looped-Qwen3，没有Inkling实验；22.5%–48.2%为forward FLOPs降幅，不是4090速度翻倍证据。[S10]

## 4. R04：接口与一步步复现

### 前提与接口

后端须暴露循环结构态、coda/head，只有最终logits不满足。GGUF/safetensors转换不得丢失controller/norm信息。

拟新增 `GuidedReadout(reference_state, final_state, guidance_contract)`，冻结论文ID、模式、b/R、omega、readout构造、norm/softcap与sampler顺序，纳入model_fingerprint。必须定义h_b/h_R的结构态对应，不能直接减两块active residual；无法定义则拒绝Hidden adapter。

guided-AR是oracle；guided表示若改变coda KV/conv，后续须沿此状态演化。参考readout持有独立state/lease，不污染最终历史。

### 操作顺序

1. 先在论文覆盖的小模型上复现Logits数学与readout，再对R02 Inkling adapter移植；小模型结果只证明实现载体。
2. omega=0与原目标对齐token/logits/state；构造小词表手算Logits公式，以及非线性coda使Hidden/Logits不等价的负例。
3. 固定原深度，先fixed omega；设计初始网格可取0.1/0.2/0.3/0.5，参考b单独扫。它们是试验参数，不是Inkling论文推荐值；在holdout前冻结选择方法。
4. Logits的fixed与adaptive分开；Hidden先验证结构态映射和fixed。记录reference coda、head、状态保存的真实时间和内存，而非仅统计FLOPs。
5. 测Java/Pi质量、工具协议、重复/终止行为和完整任务时间，再研究减少R；改变R与guidance不能在同一首次实验同时引入。
6. 单独合格后才进入R05与speculation组合，重新评估真实proposal、接受率、资源和质量。

### 验收与停止

omega=0等价、guided-AR状态自洽、sampler固定、13质量及01性能/质量取舍通过，才认可能力行；不宣称相对unguided分布无损。

无结构态定义/官方复现依赖为 `BLOCKED`；reference污染cache、NaN、重复失控、工具协议退化为 `FAIL`；多跑coda/head或特征保存抵消收益为 `NO_BENEFIT`。最多两轮profiler驱动修正；不得用“理论半loop”继续承诺倍速。

## 5. R05：组合实验只验证交互

按DAG取得各单项能力行后，每次只加一个变量，使用相同paired workload和输出预算。

| 组合 | final目标与额外门槛 |
|---|---|
| 2DSD + LoopCD | verifier使用 `p=SamplerPolicy(z_guided)`；实际q另存；guided-AR是reference |
| last-loop / lagged sharing + 2DSD | 两种缓存协议分别命名；在途KV、W边界、multi-token语义与conv恢复重新证明 |
| varloop R=4/5 + draft | 原生DSpark禁用；研究drafter须匹配真实feature、target与R；S44已有公开runner，但对应Atomic/SM89多loop能力仍待独立资格 |
| LoopCD +少loops | 新目标的质量/时延点；不是正式Mini无损加速 |

proposal不必等于guided p，但接受比与拒绝residual必须相对于guided p，并包含真实温度/top-p/grammar等处理。审核后的main、frozen和fork须使用11规定的实际proposal；不能为了提升接受率改用另一个p却仍贴LoopCD标签。

事务覆盖loop/controller、coda、KV/conv、draft Markov/feature、grammar和lease。RNG遵守05，拒绝不重用acceptance/residual事件。不同算法无需同seed同输出；统计不能替代分布证明。

对比AR、原生DSpark、单项最佳与组合；TPOT用wall time/最终emit，不相加重叠CUDA时长。投机收益重叠、少loops改变draft占比、KV可能只省容量，**不得乘各项倍率**。未优于单项最佳则 `NO_BENEFIT`并保留单项。

## 6. 附录：ARLoop作为低成本验证载体

ARLoop-0.6B为18物理层、3passes、54有效层、上下文4096，可验证attention-residual snapshot/fork/replay；它是独立模型，不是Inkling drafter。[S17]

固定代码 `16c8eaa6e841a6203a068c23394e0dbe69b08c55`，0.6B HF revision `5cd28f3dbf0d46a7f82f9d34b62aca42ac0ab039`。审查remote code后跑官方greedy64token，再测prefill/decode与事务；初始不改R、不加guidance。

其论文没有证明超过训练最大循环数后继续变强。源码MIT与HF权重Apache-2.0分别归档；未确认依赖、超上下文或误当chat模型时停止。载体 `PASS` 不增加正式Mini能力等级。

## 7. 固定来源与许可证边界

- **S10**：[指定论文v1全文](https://arxiv.org/html/2610.02185v1)、[PDF](https://arxiv.org/pdf/2610.02185v1)。本轮读取HTML公式及实验边界；论文许可不能当作未核实代码的许可。[另一同名论文](https://aclanthology.org/2026.emnlp-main.1367/)仅用于消歧。
- **S09/S14**：[固定drafter config](https://huggingface.co/minseo25/2dsd-inkling-2-mini-varloop-dspark-drafter/blob/fe3e545788b84e879f3eb8b8f426aaceb5fb44c5/config.json)、[2026-11-20 vLLM说明](https://vllm-project.github.io/2026/11/20/inkling2-mini.html)。后者说明能力边界，不替代具体engine commit和硬件资格。
- **S17**：[ARLoop论文v1](https://arxiv.org/html/2611.05234v1)、[固定源码](https://github.com/OSU-NLP-Group/ARLoop/tree/16c8eaa6e841a6203a068c23394e0dbe69b08c55)、[固定0.6B资产](https://huggingface.co/osunlp/ARLoop-0.6B/tree/5cd28f3dbf0d46a7f82f9d34b62aca42ac0ab039)。所有转换、复制和依赖许可按19登记。

## 7. 研究对照的原生DSpark适用范围

原生DSpark对照仅在当前target checkpoint/revision、默认R3、feature/head契约均有匹配且已验证资产时加入。R4/R5没有该原生对照；不能用正式Mini替代varloop的同目标基线。guided研究首先以guided-AR为oracle；草稿器无需为每个omega重新训练，但必须具有合法输入/feature接口、真实proposal q与正确guided final verifier，并重新测接受率和净收益。否则只报告同目标AR与已经合格的研究方法，缺失的native对照明确标记。
