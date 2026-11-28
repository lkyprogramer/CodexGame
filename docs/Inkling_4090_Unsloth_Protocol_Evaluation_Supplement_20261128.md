# Inkling 4090：Unsloth 深入核查与独立补充

## 输出通道评分、思考参数兼容与两个文本通道的接入

**日期：2026-11-28（北京时间）**  
**范围：** 对 Unsloth《Fine-tuning Inkling 2 Mini Guide》及相关源码深入核查后，排除已有量化、循环、LoRA/LAMED和评估方向，只保留本次确认的具体增量。  
**状态：** 研究与待实施设计；本次没有修改引擎、实验室任务状态或原有文档，没有运行新的GPU基准。

## 1. 结论与优先级

这篇文章可以继续借鉴，但排除既有方案后，**没有足够证据再启动一个新的CUDA吞吐优化方向**。本轮值得实施的内容集中在两处：

| 本文编号 | 新增范围 | 直接价值 | 优先级 |
|---|---|---|---|
| U1 | 在已有逐位置logits/KL结果上增加冻结的角色、输出通道与逻辑turn归属，派生分组CE/KL | 识别总体均值掩盖的最终回答、工具调用局部损伤；完善后续量化/近似候选的筛选依据 | 先做CPU诊断 |
| U2 | 给现有请求处理补 `enable_thinking:false` 映射；给现有token-ID parser补两个官方文本通道 | 避免客户端请求被误解，以及指定协议序列下输出正文被忽略 | 小范围兼容修复 |

U1/U2只是本文内部标号，不创建新的正式T/K任务。U1复用T25/T46，U2复用现有API和parser。已有KV8/KV4、GQA×query复用、权重格式、LoRA恢复、动态循环、专家缓冲等仍按原计划推进。

**收益边界：** 本文没有新的tok/s、显存或任务成功率实测。U1改善退化定位；U2改善接口和输出完整性。思考强度映射可能影响输出长度与完成时间，但不会减少正式三遍模型的内部循环次数，也不保证完全不生成思考。

## 2. 本次固定基线与证据边界

### 2.1 项目已更新，不能照抄旧任务状态

本次重新查询并读取：

| 对象 | 固定版本 |
|---|---|
| `lkyprogramer/inkling-4090-engine` | `d1f4012bc1d04ff49139525f77e5fb5b9296877f` |
| `lkyprogramer/CodexGame`，`4090-report` | `15d11b564d206e5a0c13806a618a7c90e546d210`，lab v3.0.27 |
| Unsloth | `67e39f08bea65f4ac76b16f26a4c6d63188ff681` |
| unsloth-zoo | `b0fb3222cbb58730c2632c63fe4535af9e110212` |
| Transformers | `518453161921c2e908a64913949dbaaafba64e3e` |
| 官方模板/tokenizer文件版本 | `thinkingmachines/Inkling-2-Mini@1fb4134b9a74f9681054f4ef82e4bf1f458a2337` |

最新lab已登记 **T45 PASS，K12原设计NO_BENEFIT**。默认decode现已走单行verify的算术路径；`ASTRAL_DECODE_LEGACY=1`才回到旧decode。故前序文档的“K12/T45尚待完成”已经是历史状态，本补充按当前lab衔接。[S07][S10]

本次还读取了T45原始slot差异与SHA记录：48个slot的row0均记录相同，多组spec记录按prompt具有一致SHA。原始实验身份保留了旧提交加工作区改动和二进制hash，lab将结果归入d1f4012；**不能把这重写成本次对干净HEAD重新构建后的GPU实测**。[S10]

### 2.2 实际核查方式

- 读取文章、官方模板、tokenizer响应解析定义和Unsloth合并修复记录。
- 对照当前API、Rust输出parser、模型logits路径与T25/T46脚本。
- 从固定unsloth-zoo源码的AST中抽取真实response-mask函数，用原子特殊标记的合成tokenizer执行六类协议样本。
- 计算一个完整概率分布的CPU反例，验证总体KL排名可以与最终回答子集排名相反。
- 对建议的请求兼容规则进行11个正常输入、6个异常输入的CPU设计探针。
- 对既有本地报告、实验室文档及方案10/11/13、Mirage/TileLang/Basalt文档进行定向去重。

未执行真实模型训练、真实tokenizer端到端mask测试、Rust服务集成测试、CUDA编译或GPU生成。CPU探针不是这些验证的替代品。

## 3. 严格去重：哪些内容不再作为新方向

| 文章可能引出的方向 | 已有覆盖 | 本轮处理 |
|---|---|---|
| LoRA/QLoRA、量化恢复、按循环深度训练 | 先前LAMED建议、Loop/adapter研究 | 排除 |
| Message Gate/router/controller精度保护 | LAMED、混合精度与量化实施方案 | 排除；不把现有F32保护降为FP16并声称优化 |
| 只展开选中专家、bounded dequant scratch | 先前LAMED已讨论 | 排除 |
| NF4训练参考、merge、GGUF/native导出对拍 | LAMED-02/08、量化实施方案 | 排除泛化部署链 |
| 草稿器蒸馏、多深度蒸馏、KV-QAT | LAMED-04/05/06 | 排除 |
| 精确全词表KL、top-k仅筛选 | lab验证合同、T46 `--full`、量化评估 | 已有，不重新立项 |
| 大logits分块归约/保存 | 量化实施§2、lab验证§6.7 | 已有，不将fused CE换名作为新优化 |
| softcap顺序、有效词表排除padding | 量化实施§6.2、lab验证§6.1 | 已有，仅核对上游是否遵守 |
| chat template与reasoning配置入manifest | lab验证§7 | 已有，不新建模板审计平台 |
| 最终答案评分、截断/复读与自由生成检查 | 量化评估、Gemini补充、T46 gencheck | 已有；U1只增加逐位置统计的归属规则 |
| KV8/KV4、MQ读取复用、prefix保护、旋转、FP4→FP8、MXFP8、L2与pack缓存 | 本对话前序三份文档 | 全部排除 |

去重范围包括完整文档与针对性原文定位。先前LAMED只有检索到的建议任务表，未找到独立文件，因此本报告将它作为已有讨论排除，不声称读取了不存在的完整LAMED文档。不能证明所有历史对话从未出现相关句子；这里的新意限定为上述可核查范围内未展开的具体实现合同。[P01]–[P06]

## 4. 文章与上游源码真正支持什么

### 4.1 训练收益不能直接迁移成4090推理收益

文章的速度和峰值显存比较来自QLoRA训练，涉及梯度、优化器、checkpoint和训练logits；不是本引擎的decode测试。当前引擎普通decode只保存单行logits，verify保存少量行，并已有末端softcap与有效词表处理。[S01][S08]

进一步核查发现，现成Unsloth FlexAttention适配路径限制offset、Q/KV长度和单query情形；不能把其训练/prefill数据作为本引擎decode的加速证据。Fused CE源码中的softcap和padded-vocab保护值得保留为既有评分实现的检查项，但大logits分块、精确KL本身已在旧方案中。[S12][S13]

### 4.2 `response-only`不等于`final-answer-only`

文章用user/model两个角色标记调用 `train_on_responses_only`。固定源码中，默认 `last_response_only=False`；函数找response spans并复制其中的label，保留已有的`-100`排除标记。它没有按Inkling的thinking/text/tool-json通道定义“最终答案”。[S01][S02]

官方模板允许一个assistant逻辑消息展开成多个带 `message_model` 的协议段：思考一段、正文一段，多个content parts或多个工具调用也可形成多段；逻辑turn末尾另有 `content_model_end_sampling`。这使“最后一个协议段”和“完整最后一轮assistant输出”成为不同对象。[S03]

本次执行固定上游scanner得到：

| 输入结构 | 默认response-only | `last_response_only=True` |
|---|---|---|
| 思考 + 最终正文 | 两段都保留 | 最终正文 |
| 只有思考的turn | 保留思考 | 仍保留思考，不会凭空得到final |
| 同一turn有两个正文part | 两个part | 只有第二个part |
| 同一turn有两个工具调用 | 两个调用 | 只有第二个调用 |
| 合法call → assistant EOS → tool结果 → final | call与final，工具结果排除 | final |
| 手写历史省略call后的assistant EOS | 工具结果也被包含 | 最后一个response段 |

最后一行是**非规范输入负例**。官方模板正常生成EOS，本次合法工具链并未出现工具结果泄漏；不能据此声称文章已测的FineTome路径有该问题。新增结论是：导入、拼接或截断历史时，必须检查协议边界；也不能靠把 `last_response_only` 设为True来实现最终答案评分。

### 4.3 上游修复只能按当前实现差异吸收

Unsloth PR #19859修复了Inkling在effort none时的思考解析、`enable_thinking:false`被忽略，以及字面`<think>`被误切分等问题。它还披露部分后端路径的限制，不能把一个上游PR称为所有服务链的完整证明。[S06]

当前Rust引擎已按token ID解析thinking/text，不依赖effort开关，也不按字面`<think>`切文本。这里无需重新建parser。真正还存在的差异是：请求没有布尔兼容入口，以及两个官方文本通道未接入，见U2。[S08][S09]

## 5. U1：在同一冻结轨迹上分角色与输出通道评分

### 5.1 要解决的具体问题

同一条长上下文轨迹可能包含大量prompt、文档、工具结果和思考，最终回答或工具调用参数却只占很少位置。总体均值适合反映整体数值变化，却可能掩盖对实际任务更关键的小子集。

当前代码中，`t25_judge.py`按位置截取的是整个`generated_region_recorded`，其中可能混有消息头、thinking、final和tool call；其mean/max不能直接命名为final指标。`t46.py::gencheck`检查EOS、预算和复读，没有按输出通道判断最终答案是否完成。U1补的是这组行归属，不替换已有数值指标或任务判定。[S11]

一个已执行的CPU例子：1000个评分位置中，990个为上下文，10个为final；teacher在每行的两类概率都是`[0.8,0.2]`。候选A在上下文上完全相同，在final上交换为`[0.2,0.8]`；候选B在上下文上为`[0.7,0.3]`，final完全相同。

所有位置的冻结目标token均取第一类。因此表中NLL为`−ln Q(第一类)`；KL则对teacher的完整两类分布求期望。这两个统计的目标定义不同。

| 指标，单位nats/token | 候选A | 候选B |
|---|---:|---:|
| 全体KL | **0.008318** | 0.025475 |
| final KL | **0.831777** | 0 |
| 全体NLL | **0.237006** | 0.355340 |
| final NLL | **1.609438** | 0.223144 |
| final top-1是否与teacher一致 | 否 | 是 |

只看全体KL/NLL会偏好A，但它在final子集更差。这证明一种统计失真可能发生，**不证明当前某个量化候选已经发生这种退化**。U1的目标是在既有实验中判断这种集中损伤是否存在。

### 5.2 不改变条件分布，只改变统计哪些行

固定一条token序列 `x[0..N)`。以零基索引，长度L的前缀 `x[0:L]` 对应预测 `x[L]`；等价地，输入位置`L-1`的logits预测目标位置L。

mask必须附着于**被预测目标token的位置L**。不能直接沿用输入末位置`L-1`的角色。Transformers的causal loss也采用shifted labels。[S05]

所有对照必须保持同一token序列、同一teacher-forced前缀和同一已冻结的评分位置。不能删除user/tool内容后重新拼接assistant片段；那会改变条件分布。也不能根据候选自己的生成结果临时挑选评分位置。

### 5.3 最小标签模型

给每个目标位置记录三个维度，不用一个模糊的“response”布尔值包办：

| 字段 | 含义 |
|---|---|
| `role` | system/user/tool/assistant |
| `channel` | text/thinking/invoke_tool_json/tool_error/invoke_tool_text/xml/protocol |
| `message_id`、`logical_turn_id`、`segment_id` | message_id覆盖所有源消息和模板注入消息；assistant的logical_turn_id区分逻辑turn，其他role可为null；segment_id标识协议段 |
| `origin` | dataset/template_tools/template_effort等，区分原数据与模板注入 |
| `is_final_answer` | 从冻结final-span标注得到的true/false；缺标注时为null，不能仅凭content_text推断 |
| `eligible` | 该目标位置是否属于本次已冻结评分范围 |

正文不总是最终答案：它可能是工具调用前的说明、多个part之一，或工具错误文本。因此保留通用 `assistant_text`，另以标注定义 `final_answer`子集。`content_tool_error`与`content_invoke_tool_text`即使对外进入content，也保留其独立channel，避免与正常终答混淆。

协议标记、EOS和边界位置单独统计。角色总集与子集可以重叠展示，但互斥基础分类必须满足覆盖关系；不得将assistant总集与reasoning/final子集再次相加。

当前renderer会为非空tools自动注入`system → tool_declare → content_xml → JSON schema`，也会注入Thinking effort系统消息。必须为这两类生成稳定message_id/segment_id，分别记录`origin=template_tools/template_effort`，role=system，logical_turn_id=null；工具声明payload的channel=xml。源developer消息按当前renderer归system，同时保留source_role=developer。它们都不是assistant输出，也不能因没有原始messages索引而判INVALID。[S09]

### 5.4 如何生成可靠的span

1. 从原始结构化`messages + tools + effective_effort`、固定模板和tokenizer生成完整序列及逻辑消息归属，包括模板自动注入段。
2. 以真实特殊token ID确认协议边界。ID从当前tokenizer读取，不硬编码示例数字。
3. 对模板展开的多个段建立 `logical_turn_id → segment_id → token span` 映射。不能把分别tokenize各文本段再拼接的结果当成完整tokenize结果；必须与最终完整IDs逐项一致。
4. 工具结果的role来自结构化事件；用assistant EOS检查turn结束。检测到手写历史缺结束边界、角色冲突或无法唯一分类时，标为INVALID，不猜测补齐。
5. 对payload中的字面`<think>`或类似文本保持原样；只处理协议token及可信结构标注。若输入含特殊token字面注入导致归属歧义，拒绝该fixture进入正式统计，不能误归为模型思考。
6. 在运行候选前冻结span文件、token IDs、目标位置与schema版本的hash。每次聚合检查这些身份一致。

首轮只覆盖当前引擎支持的文本/工具消息。图片或其他未支持输入不因这份补充自动纳入。

**final标注的输入合同：** 在suite数据旁新增冻结的`final_spans.jsonl`。每条以`sequence_id + token_ids_sha256`定位，记录`annotation_schema`、`annotation_origin`（如task_gold或reviewed_reference）、`annotation_status`及零基半开区间`[target_start,target_end)`；区间与message_id/part_index对应，明确只包含该任务认定的最终答案payload。标注在运行候选前完成，保存文件hash。它独立于既有T46数值结果，不能由候选分数推导。

- `annotation_status=complete`且spans非空：可确定每行true/false。
- `annotation_status=complete`且spans为空：参考确实被标注为没有final，报告`no_final_in_reference`。
- 无该case标注或状态为missing：各行`is_final_answer=null`，final统计报告`final_annotation_missing`；已有role/channel统计仍可继续。

旧材料可先保留role/channel统计，逐步补final标注；不能把缺标注默认为false，也不需要因此废弃所有历史数据。

### 5.5 与现有T46行结果连接

保留现有T46 `cache/kl/--full/gencheck`。新增sidecar把既有row key映射到目标位置，解析旧文件名得到的L仍须与原导出器语义核对；不同dump格式不能直接套一个正则。

字段示意，所有hash在真正运行时填写，以下不是已经生成的实验结果：

```json
{
  "schema": "inkling-score-spans-v1",
  "sequence_id": "dialogue_001",
  "token_ids_sha256": "<actual hash>",
  "template_sha256": "<actual hash>",
  "tokenizer_sha256": "<actual hash>",
  "span_sha256": "<actual hash>",
  "final_annotation_sha256": "<actual hash>",
  "final_annotation_status": "complete",
  "expected_positions_sha256": "<actual hash>",
  "positions": [
    {
      "row_key": "<existing T46 row key>",
      "prefix_length": 4096,
      "target_position": 4096,
      "target_token_id": 1234,
      "role": "assistant",
      "channel": "text",
      "message_id": "dataset_message_7",
      "origin": "dataset",
      "logical_turn_id": 3,
      "segment_id": 5,
      "is_final_answer": true,
      "eligible": true
    }
  ]
}
```

首次实现可以只消费已存在的逐位置logits与T46行结果，不改GPU热路径。若旧dump未包含所需final/tool-call位置，补导出明确目标位置；**没有覆盖的行不能被默认为零损伤**。T25的chunk选择或`ASTRAL_DUMP_FIRST`也不能自动保证完整覆盖。

上述`positions`是预先冻结的**预期评分位置集合**，不能从实际读到的候选row key反推。分别报告：请求行覆盖率（读到的预期行/预期行）、final请求行覆盖率（读到的预期final行/预期final行），以及final内容采样比例（预期final行/全部已标注final位置）。已标注final但没有选入评分范围是`not_scored`；已选入却缺logits是`incomplete`并使该次统计失败。三者不与`final_annotation_missing`混用。

### 5.6 统计定义与空集处理

对某个冻结目标集合S：

\[
\mathrm{CE}_S=\frac{1}{|S|}\sum_{L\in S}-\log Q_L(x_L),\qquad
\mathrm{KL}_S=\frac{1}{|S|}\sum_{L\in S}\sum_{v\in V}P_L(v)\log\frac{P_L(v)}{Q_L(v)}.
\]

沿用现有有效词表、softcap和float64离线参考，不改变KL方向和每行支持集。`top-k+tail`仍只作筛选，不能从压缩tail重建精确fullKL。

当前CLI的`cmd_score`提供argmax、top2 margin和目标logit，**目标logit不是NLL**。新增CE应由已有完整候选logits计算稳定的`log_softmax`后取目标项，或读取经过验证的log-normalizer；缺少归一化信息时不能把负目标logit当作CE。[S08][S14]

每组至少输出：`n_tokens`、`n_cases`、覆盖率、token加权均值、case宏平均、p90/max，以及A/A重复的噪声。长回答不能只因token更多而完全决定所有任务的宏平均。

`n=0`输出`null`和原因，例如`no_final_in_reference`、`not_scored`、`truncated`。不得写0分或PASS。冻结参考中没有final时，数值指标只能说明已有部分；候选自由生成缺final、超预算或工具调用失败，继续由原任务/生成检查判定。

CE依赖具体目标token，低CE不保证答案正确；KL与teacher一致也不证明teacher正确。U1用于定位损伤，保留已有自由任务质量门。

### 5.7 最小改动与交付物

以下是拟新增文件，不是当前可运行命令：

| 位置 | 改动 |
|---|---|
| lab `tools/t46/score_spans.py` | 读取冻结IDs、完整渲染输入、final_spans标注及sidecar；校验目标位置与归属；输出按组统计 |
| suite数据旁 `final_spans.jsonl` | 冻结最终答案的目标token范围、标注来源/状态与版本；不从候选输出自动回填 |
| lab `tools/t46/t46.py` | 复用现有每行KL，提供可被sidecar连接的行结果；已有输出若足够则无需修改 |
| lab `tests/test_t46_score_spans.py` | next-token边界、逻辑turn、多part、多工具、空集、缺行和重复行负例 |
| lab `docs/05_validation.md` | 附加诊断字段、覆盖率及数据身份；不改写历史判定 |

首版定位为 `diagnostic_only`。若真实候选出现“总体通过、final/tool-call集中退化”，用冻结发现集与独立留出集校准是否增加新子集门；不能事后根据某个候选分数设阈值，也不能不经校准直接复用全体KL阈值。

### 5.8 验收与停止条件

- 原T46全体结果在未开启分组时保持一致；分组使用同一行值。
- mask偏移一行、重复row key、目标token不匹配、丢失final行、空集当0等负例必须被识别。
- reasoning-only、多正文part、多个tool calls、合法工具结果、缺EOS历史均有明确预期。
- 非空tools的自动system/xml声明、自动effort系统消息和developer→system映射均有归属与覆盖fixture。
- final未标注、已标注为空、已标注但未选入、已选入却缺logits分别有不同预期，禁止默认互换。
- 人工仅扰动final分布时，final统计必须暴露变化；不得被长prompt分母稀释。
- 首轮复用一组既有A/A与A/B材料。若缺乏结构化历史或评分位置，先只补有限样本，避免为本补充重跑全套长上下文矩阵。
- 若真实诊断没有额外解释力，保留为轻量可选报告，不继续建设复杂评估系统。

## 6. U2：补请求映射和两个官方文本通道

### 6.1 当前已经支持的能力

当前 `crates/api/src/lib.rs::prompt_ids` 从顶层或 `chat_template_kwargs`读取 `reasoning_effort`；`chat.rs::effort_text`支持named levels和数值，默认0.9。`/tokenize`与生成共用 `prompt_ids`。因此不能说引擎不支持reasoning none或没有统一模板入口。[S08][S09]

官方含义：none=0，minimal=0.1，low=0.2，medium=0.7，high=0.9，xhigh/max=0.99；写入system提示。它与内部loop pass数不是同一参数。[S03]

### 6.2 新增布尔兼容映射

实际缺口：当前没有读取 `enable_thinking`。只发送 `enable_thinking:false` 的客户端仍会得到默认effort 0.9。现有服务文档没有承诺这个别名，因此这里称为**兼容补齐**，而不是已文档化接口违约。[S08]

建议在共享 `prompt_ids`之前或其内部增加一个小的规范化函数，保留原始请求与有效值的诊断信息，规则如下：

1. 按当前规则先选择effort：顶层key存在则优先，否则使用kwargs。被选值非null时，以显式effort为准；非法值仍报400，不因false别名而吞掉错误。
2. 仅当选中的effort缺省/null时，读取 `enable_thinking`；顶层key存在优先于kwargs。
3. 被选flag为false时，传入现有renderer的`none`；true、缺省或null保持默认0.9。
4. 仅在flag参与解析时要求其为bool或null；字符串`"false"`不能当布尔false。
5. 不顺手修改当前effort的key优先级。例如顶层effort=null仍覆盖kwargs中的effort；需要改变这条历史行为时应作为另一个接口变更处理。

显式effort优先与上游修复思路一致；顶层/kwargs/null的具体处理是本补充为保持当前API行为作出的设计选择，不声称所有服务均采用它。[S06]

| 请求要点 | 建议有效effort |
|---|---:|
| 均未提供 | 0.9 |
| 顶层或kwargs仅有`enable_thinking:false` | 0 |
| 仅有`enable_thinking:true` | 0.9 |
| effort=high，同时false | 0.9，显式effort优先 |
| effort=none，同时true | 0 |
| effort=0.35 | 0.35 |
| 顶层effort=null，同时false | 0 |
| 顶层effort=null，kwargs effort=low，无flag | 0.9，保持当前key优先级 |
| 顶层flag=true，kwargs flag=false，无effort | 0.9 |
| 非法effort；被选flag为字符串false | 400 |

**none仍可能产生思考。** 不得因此关闭输出通道解析、丢弃reasoning、改变EOS、减少模型循环，或把`max_tokens`解释成只计正文。有效effort只改变输入提示语义。[S03][S06]

### 6.3 两个官方文本通道存在具体接入缺口

官方 `tokenizer_config.json::response_template`把以下三类都映射到对外`content`：

| 协议通道 | 官方响应字段 | 当前Rust parser |
|---|---|---|
| `content_text` | content | 已支持 |
| `content_tool_error` | content | 未显式识别 |
| `content_invoke_tool_text` | content | 未显式识别 |
| `content_thinking` | reasoning_content | 已支持 |
| `content_invoke_tool_json` | tool_calls | 已支持 |

固定官方文件中，两个遗漏标记的ID分别为200022和200057，均是special token。实现应查询tokenizer映射，**不能把这些示例ID写死**。[S04]

当前 `OutputParser`初始为Header，遇到`message_model`或`end_message`也回到Header。未知通道不会切换Part，随后Header分支直接返回。因此对规范序列：

```text
message_model → content_tool_error → 普通文本payload → end_message
message_model → content_invoke_tool_text → 普通文本payload → end_message
```

按当前分支，正文会被忽略。JSON和SSE共用此parser，均受同一语义缺口影响。这是源码推导和固定协议fixture，不是已经观察到真实模型输出这些标记的线上故障；实际出现频率仍未知。[S09]

最小修复：在 `Specials`中读取两个token ID，在现有 `OutputParser::push`的Content分支加入它们。保留已有增量UTF-8解码、reasoning与JSON工具调用逻辑。当前官方Inkling profile应验证这两个ID存在；其他profile按其声明处理，不以任意未知special token自动替代Content。

`content_invoke_tool_text`依照官方response_template归普通content，**不把它提升为可执行工具调用**。只有原来明确的JSON工具通道继续走tool_calls。

### 6.4 不应照搬的解析改造

Unsloth中effort none时的解析开关和字面think标签问题，当前Rust token-ID状态机已经避开。保留以下回归fixture即可：

- effort none仍输出thinking marker：进入reasoning_content。
- 正文包含字面`<think>.*?</think>`：原样留在content。
- 多个reasoning/text段：按照真实标记累加，不用文本正则重切。
- 中文、emoji在增量解码边界处分段：SSE拼接结果与非流式结果一致。

无需引入Unsloth服务层、Python训练依赖或另一套文本parser。

### 6.5 最小文件改动与验收

| 现有文件 | 待实施改动 |
|---|---|
| `crates/api/src/lib.rs` | 在共享prompt构建入口规范化effort/flag，供tokenize与generate复用 |
| `crates/api/src/chat.rs` | 增加两项Content通道ID；保留原状态机与JSON工具逻辑 |
| `docs/serving/openai_compatible_server.md` | 说明别名、显式effort优先、none语义与支持的通道 |
| API相关测试位置 | 请求矩阵、tokenize/生成prompt同一性、协议token fixture、SSE与JSON对齐 |

验收分为三层：

1. **无需GPU的渲染测试：** 同messages下，false别名与显式none的完整prompt IDs必须相同；默认和显式high保持相同；非法输入400。
2. **无需GPU的parser测试：** 两个新增通道的payload分别进入content；JSON工具调用数量/参数不变；literal tags和thinking通道不回退。使用真实tokenizer文件，而不仅是本次合成token探针。
3. **有限服务集成：** A1固定配置下，比较false别名与显式none，先核prompt hash，再核greedy token IDs与完整响应；SSE/JSON均覆盖。无需要求none与high生成相同答案。

若没有客户端使用布尔入口，它的业务优先级可以较低；两项文本通道仍可作为小型协议完整性修复。收益报告写“兼容/输出完整性”，不得写成kernel性能提升。

## 7. 本轮额外发现：T45后旧负控需重新确认有效

这是检查最新代码时发现的验收维护问题，不是Unsloth文章提出的新优化。

当前 `tools/t25/t25_e.sh`仍用单独的 `ASTRAL_DECODE_DP4A=1`作为旧dp4a故障负控。T45后的默认decode先走 `decode_mt() && multi_t_ok` 分支，再考虑受旧decode选择影响的路径。因此在满足新分派条件的A1矩阵上，仅设置旧开关不能证明已经重新启用旧故障路径。[S08][S11]

正确处理：

- 先记录实际选中的kernel/分派与数值差异，验证负控确实产生了预期扰动。
- 若用legacy+dp4a，必须显式设置并核查两项环境变量及实际分派；旧wrapper如何解析多变量也要检查，不能将含空格字符串当成一个合法assignment。
- 也可以给U1使用受控的离线final-logit扰动，只验证聚合器是否识别集中损伤；这不等于重新证明旧GPU故障。
- `below_resolution`不应掩盖一个已经没有效果的负控；无实际扰动应标为负控无效/INCONCLUSIVE。
- 不改写T25历史E结论，新的执行身份另记。

这项检查服务于U1的负例可信度，不重开K12，也不推翻已登记T45结果。

## 8. 建议的执行顺序与交付标准

### 阶段A：全部在CPU侧准备

1. 固定上述代码与模型模板身份，完成U1 sidecar schema与6类以上协议fixture。
2. 使用已有T46材料生成分组报告；完成偏移、缺行、重复和final-only扰动负例。
3. 完成U2请求映射与两个通道的小改动，使用真实tokenizer做渲染/parser单测。

此阶段不下载26B全量权重，不安装训练栈，不抢占4090主线实验。

### 阶段B：接已有实验材料，做有限集成

1. 选择已有基线及一个已经有数据的候选，按同一冻结轨迹复算U1统计。未覆盖的位置明确报告，不补零。
2. 做U2 false/none的tokenize与生成一致性检查。
3. 校验被选负控在当前分派下确实生效；无效则不使用它判断新诊断的灵敏度。

### 阶段C：根据实际价值决定是否进入正式合同

- U1若揭示总体指标遗漏的集中退化，再提出一个带冻结阈值和留出验证的新诊断门；否则只保留可选分组输出。
- U2以协议fixture和服务一致性通过作为完成标准。真实稀有通道出现频率可以继续观测，但无需编造频率或吞吐收益。
- 新文档不修改当前T44/K15等主线顺序，不启动新的LoRA训练或CUDA内核项目。

建议交付物仅为：一个冻结sidecar格式、一个轻量分组脚本、API小补丁、针对性fixture和一份结果说明。无需新增平台或独立训练仓库。

## 9. 本次验证结果与尚未完成项

| 项目 | 本次状态 | 能支持的结论 |
|---|---|---|
| 上游response scanner，6类样本 | CPU执行通过 | response-only/last-response语义和EOS边界行为 |
| 已有`-100` mask保留 | CPU断言通过 | 被排除label没有被重新激活 |
| 全体与final排名反转例子 | CPU计算通过 | 聚合分母可能掩盖局部损伤 |
| 建议effort规则11正常+6异常输入 | CPU设计探针通过 | 建议规则内部一致；不是Rust改造已完成 |
| 两文本通道缺口 | 官方配置、源码分支提取与CPU静态fixture一致 | Header态会忽略给定协议序列的payload；未执行真实Rust parser |
| T45原始记录 | 已读取 | lab已登记完成；本次没有重跑GPU |
| 真实tokenizer、Rust服务、SSE/JSON集成 | 待执行 | 不宣称通过 |
| 真实量化候选的分组收益 | 待执行 | 不宣称已发现某个候选退化或质量提高 |

### CPU聚合反例的最小复现

```python
import math

def kl(p, q):
    return sum(x * math.log(x / y) for x, y in zip(p, q))

p = [0.8, 0.2]
candidates = {
    "A": (p, [0.2, 0.8]),
    "B": ([0.7, 0.3], p),
}
for name, (prompt_q, final_q) in candidates.items():
    full = (990 * kl(p, prompt_q) + 10 * kl(p, final_q)) / 1000
    print(name, "all_KL", full, "final_KL", kl(p, final_q))
# A all_KL 0.008317766166719342 final_KL 0.8317766166719343
# B all_KL 0.025474771553205502 final_KL 0.0
```

上游mask实验使用[S02]固定源码的真实scanner函数与合成tokenizer；复现时需保持默认marker、EOS及`last_response_only`设置，按§4.2六类样本核对保留内容。生产验收必须换成当前资产的真实tokenizer再执行一遍，不能把合成token探针当作完整集成证据。

## 10. 采用建议

优先做U1的轻量诊断与U2的小范围协议修复。它们能帮助确认后续量化/近似方案到底伤在什么输出位置，并减少调用配置和响应解析带来的误判。

本篇不新增吞吐和上下文容量目标，也不把训练速度换算成推理速度。对于这篇文章，其余直接优化方向已被前序文档覆盖，继续重复扩写没有新增工程价值。

## 来源索引

### 当前文章、上游源码与项目基线

- [S01] [Unsloth：Fine-tuning Inkling 2 Mini Guide](https://unsloth.ai/docs/models/inkling-2-mini/fine-tuning)，访问2026-11-28。
- [S02] [unsloth-zoo dataset_utils.py：response mask](https://github.com/unslothai/unsloth-zoo/blob/b0fb3222cbb58730c2632c63fe4535af9e110212/unsloth_zoo/dataset_utils.py)，重点`train_on_responses_only`、response spans与last_response_only。
- [S03] [官方chat_template.jinja，固定文件版本](https://huggingface.co/thinkingmachines/Inkling-2-Mini/blob/1fb4134b9a74f9681054f4ef82e4bf1f458a2337/chat_template.jinja)。
- [S04] [官方tokenizer_config.json：response_template与特殊token](https://huggingface.co/thinkingmachines/Inkling-2-Mini/blob/1fb4134b9a74f9681054f4ef82e4bf1f458a2337/tokenizer_config.json)。
- [S05] [Transformers causal loss：shifted labels](https://github.com/huggingface/transformers/blob/518453161921c2e908a64913949dbaaafba64e3e/src/transformers/loss/loss_utils.py)。
- [S06] [Unsloth PR #19859](https://github.com/unslothai/unsloth/pull/19859)，[合并提交2be207a](https://github.com/unslothai/unsloth/commit/2be207ad683de2b909ab2d4258fb34d422f93ef0)。
- [S07] [Engine固定提交d1f4012](https://github.com/lkyprogramer/inkling-4090-engine/commit/d1f4012bc1d04ff49139525f77e5fb5b9296877f)。
- [S08] [API入口lib.rs](https://github.com/lkyprogramer/inkling-4090-engine/blob/d1f4012bc1d04ff49139525f77e5fb5b9296877f/crates/api/src/lib.rs)；[模型执行与logits](https://github.com/lkyprogramer/inkling-4090-engine/blob/d1f4012bc1d04ff49139525f77e5fb5b9296877f/crates/model/src/inkling.rs)。
- [S09] [Rust chat renderer与OutputParser](https://github.com/lkyprogramer/inkling-4090-engine/blob/d1f4012bc1d04ff49139525f77e5fb5b9296877f/crates/api/src/chat.rs)；[服务接口说明](https://github.com/lkyprogramer/inkling-4090-engine/blob/d1f4012bc1d04ff49139525f77e5fb5b9296877f/docs/serving/openai_compatible_server.md)。
- [S10] [lab v3.0.27任务记录](https://github.com/lkyprogramer/CodexGame/blob/15d11b564d206e5a0c13806a618a7c90e546d210/docs/inkling-4090-lab-v3.0/docs/07_tasks.md)；[T45原始结果目录](https://github.com/lkyprogramer/CodexGame/tree/15d11b564d206e5a0c13806a618a7c90e546d210/docs/inkling-4090-lab-v3.0/tools/t45/results)。
- [S11] [T25 E负控脚本](https://github.com/lkyprogramer/CodexGame/blob/15d11b564d206e5a0c13806a618a7c90e546d210/docs/inkling-4090-lab-v3.0/tools/t25/t25_e.sh)；[T46现有实现](https://github.com/lkyprogramer/CodexGame/blob/15d11b564d206e5a0c13806a618a7c90e546d210/docs/inkling-4090-lab-v3.0/tools/t46/t46.py)；[既有验证合同](https://github.com/lkyprogramer/CodexGame/blob/15d11b564d206e5a0c13806a618a7c90e546d210/docs/inkling-4090-lab-v3.0/docs/05_validation.md)。
- [S12] [Unsloth Inkling FlexAttention适配](https://github.com/unslothai/unsloth/blob/67e39f08bea65f4ac76b16f26a4c6d63188ff681/unsloth/models/inkling2_flex.py)。
- [S13] [fused softcap CE测试](https://github.com/unslothai/unsloth-zoo/blob/b0fb3222cbb58730c2632c63fe4535af9e110212/tests/test_inkling2_fused_softcap_ce.py)；[compiler中的相关重写](https://github.com/unslothai/unsloth-zoo/blob/b0fb3222cbb58730c2632c63fe4535af9e110212/unsloth_zoo/compiler.py)。
- [S14] [CLI score与logits导出](https://github.com/lkyprogramer/inkling-4090-engine/blob/d1f4012bc1d04ff49139525f77e5fb5b9296877f/crates/cli/src/main.rs)；[T25位置与生成区域判定](https://github.com/lkyprogramer/CodexGame/blob/15d11b564d206e5a0c13806a618a7c90e546d210/docs/inkling-4090-lab-v3.0/tools/t25/t25_judge.py)。

### 去重依据

- [P01] [Inkling_4090_Quantization_Context_Assessment_20261128.md](https://chatgpt.com/library?file_id=libfile_fde3_f-d2064a9e627481919313efc11718e4be_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)，尤其§9。
- [P02] [Inkling_4090_Quantization_Context_Implementation_Plan_20261128.md](https://chatgpt.com/library?file_id=libfile_fde3_f-644a029ed0388191a091277d61143569_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)，尤其§2、§6.2、§9、§10–11。
- [P03] [Inkling_4090_Gemini_KV_Supplement_20261128.md](https://chatgpt.com/library?file_id=libfile_fde3_f-bbc75dbe6df48191ac7f3469402b3b47_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)，尤其§7–13。
- [P04] [10_molt_loomformer_inkling4090_plan.md](https://chatgpt.com/library?file_id=libfile_fde3_f-db4d9995cea881919fc3b1b211af62a4_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)；[11_inkling4090_new_optimization_plan_20261127.md](https://chatgpt.com/library?file_id=libfile_fde3_f-0570cb348dc08191b75300fd74cb24ab_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)。
- [P05] [13_inkling_loop_model_extreme_research_plan_20261128.md](https://chatgpt.com/library?file_id=libfile_fde3_f-cc27ac1ffda88191b5535e3d9ae7f5ab_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)；[Inkling_4090_Mirage_TileLang_Basalt_Exploration_Plan_20261128.md](https://chatgpt.com/library?file_id=libfile_fde3_f-9978da946558819189840b17c8e77e2e_9f3d81f9d8588191b3e92b92598ea89e&account_id=personal)。
- [P06] 此前LAMED讨论中的00–08建议任务表；仅作为已讨论方向的排除依据，不宣称存在独立文件。
