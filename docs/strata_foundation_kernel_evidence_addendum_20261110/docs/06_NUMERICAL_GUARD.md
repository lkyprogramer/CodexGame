# 06 · 数值证据：先验证输入完整，再调用现有checker

状态：**PLANNED外层守卫**。复用上游Token Forcing与原lab正确性裁判，不移植samir整个模型，不创建另一个SpecPilot控制器。

## 1. 上游已经做了什么

固定SHA的 [tools/force_check.py](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/tools/force_check.py) 包含gen、score、check、selftest。gen/score会启动真实engine，不能在当前零预算下运行；未来也不能绕过原OwnedServer、资源预算、进程身份和失败保留机制。

- score `--path decode` 使用STRATA_FOLLOW与STRATA_FOLLOW_LOGPOS，在实际decode/verify窗口沿指定token续写，保留drafter/spec配置（并显式关闭prompt cache）。
- score `--path prompt` 用prompt/read路径，过滤部分drafter参数，不能代替decode路径资格。
- 内部评分会计算完整FP32 vocabulary head并拷回，但保存的TSV只是forced/argmax概率与top2摘要，不是完整logits回放档案。评分运行不能作为真实吞吐基线。
- check是CPU统计器，不是CPU上的独立模型oracle；当前大margin事件规则也不包含论文的完整stock self-path复现审计。

脚本里+0.5个百分点的统计规则不是允许模型错误增加0.5%的通用合同，更不能覆盖原golden、状态、长期检索或质量门。

## 2. 本次离线实际复现的边界

对精确源码hash，以人工构造的全无mismatch输入调用check，得到：

| 输入缺陷 | 上游返回 | 本增补要求 |
|---|---|---|
| candidate缺一个request | PASS；只统计交集中的1个request | INPUT_SET_MISMATCH |
| candidate每request只留2行，stock有8行 | PASS；candidate4 tokens vs每stock16 | POSITION_COVERAGE_MISMATCH |
| 仅一个stock arm | PASS；CLI另外只打印warning | INSUFFICIENT_STOCK_ARMS |

这证明“输入完整性需要外层保证”，不证明真实Strata模型发生了错误。复现脚本只允许审计过的源码SHA256，见[验证记录](../VALIDATION.md)。它不调用gen/score，不访问GPU。

其他静态发现：cmd_score的forced输出不一致只打印WARNING；行数检查不是精确位置覆盖；load_arm会校验已出现行的target，但不自动证明所有期望位置恰好出现一次。

## 3. 本轮只支持固定文本比较合同

MVP合同名 `fixed-text-decode/v1`：两份以上独立stock运行和candidate，对同一完整set、相同prompt与continuation评分；配置、模型、tokenizer、有效域及允许变化单独冻结。

stock与candidate的scorer/build hash可以不同（这正是scorer改造的比较目标），但必须分别匹配预注册的每臂身份；禁止强制所有臂binary hash相同，也禁止未声明的漂移。

**不是声称上游所有不同continuation都是bug。** 上游也允许“改变decoder后生成各自文本再由stock评分”的方法。那属于不同统计合同；本增补先返回 `UNSUPPORTED_TEXT_CONTRACT`，未来另行预注册其配对/曝光量/路径审计规则。不得悄悄按固定文本方法比较。

## 4. 外层严格检查顺序

1. **身份**：expected set hash、模型/tokenizer/模板hash、scorer build hash、source/build/engine实例、路径decode、采样及有效精度合同必须存在。stock至少2个独立运行；复制同一arm元数据不算第二次。
2. **集合**：expected、每个stock、candidate的request ID集合严格相等；拒绝重复ID、未知ID、空集合。禁止先求交集再评分。
3. **元数据边界**：TSV切片不越界、不重复占用、与请求映射一致。若prompt路径存在额外行，其分区规则必须先冻结；不能用“看起来属于prompt”随意过滤缺陷。本MVP只接decode。
4. **逐位置覆盖与顺序**：prompt长度P≥1、continuation长度K>0时，期望预测位置为P−1至P+K−2，共K项；每项恰好一次，按位置配对而不是按行号。每请求原TSV切片必须按位置严格递增，重排即POSITION_ORDER_MISMATCH；因为原load_arm保留行序，check按列表的first departure取margin，乱序会改变delta。不得暗中排序；如未来明确支持规范化，须另存带hash和raw映射的派生文件并预注册。BOS/特殊模型若例外，先定义版本化position mapping，不能临时挪一格。
5. **target与强制输出**：每行target等于指定continuation对应token；实际forced输出完全相同，包括自然EOS/边界。必须引用现有runner封存的emitted-token receipt（实际T输出、request/engine映射、hash、完整结束标记）；原meta只记录期望ids，不能单独证明实际输出。没有收据返回FORCED_OUTPUT_UNPROVEN/BLOCKED，不把“没看到WARNING”当证明，不为补证据自动重跑。EOS/取消另有原状态场景，不拿截短当数值通过。
6. **分数域与一致性**：这里是log probability，不是任意logit或线性概率；必需字段有限且logp≤0（仅允许预注册格式舍入ε）。argmax logp不小于forced/top2 logp；top1/top2 token不同；forced=argmax时两份logp一致；forced=top2时也须一致。margin由对应logp之差计算，若附件保存margin，须与定义一致；token ID在冻结词表内。tie按scorer既定规则，near-tie不擅自要求同一argmax。ε只能来自锁定TSV输出精度的误差界并在见结果前固定，不因失败放宽。NaN/Inf/截断/重复行阻断，摘要缺失不能按0解释。**不要求top2概率和为1，也不声称验证了全词表归一化。**
7. **运行与collector完整性**：异常退出、丢失日志、无法证明完整flush、身份不一致、配置漂移先阻断。只凭exit0不足以证明数据完整。
8. **才调用原check**：存原始输出、原脚本hash与参数，透传REJECT/INCONCLUSIVE；PASS只代表这份数值统计通过，不发最终采用决定。

Guard的成功状态叫 `INPUT_ADMISSIBLE`，不是 `MODEL_CORRECT`。包内缩小版合成守卫叫 `INPUT_ADMISSIBLE_FIXTURE_ONLY`，更加不具备真实产品资格。

## 5. 三层正确性必须同时保留

| 层 | 验证对象 | 不可替代 |
|---|---|---|
| 小算子独立oracle | dequant/layout/index/mask/页映射等，边界与有效域明确 | 不能证明全模型/长上下文 |
| 固定文本数值统计与状态验证 | logits摘要、真实decode路径、KV/GDN/PLE/rollback等原状态合同 | 不证明真实任务质量、速度 |
| 原任务golden/holdout/长期检索 | 用户关注的有效回答、检索恢复、自然结束等 | 不被新checker PASS覆盖 |

若需要比较完整logits误差，必须另有受控raw附件与校准好的精度容忍规则；不能从top2 TSV重建全vocab L∞误差。训练数值习惯或H200 FP8案例不能直接降低4090量化推理的正确性门。

## 6. 最小实现边界

建议在已有lab代码内增加 `lab/observability/numerical_guard.py`，复用原manifest解析器/失败记录；输入为只读set/meta/TSV、实际emitted-token receipt及已有运行身份，输出一个完整性报告附件。不可新建launcher，不改上游统计算法，不自动加样、不补跑、也不为PASS改delta。

最小测试至少覆盖：缺request、重复ID、缺/重复位置、错target、forced输出不同/收据缺失、单stock、同一stock重复、文本合同不同、错scorer、prompt冒充decode、NaN、越界slice、日志截断，以及完整输入允许进入下一层。再分别注入有限正logp、倒序top2、重复top2 ID、同token不同logp、伪造margin，合法tie/格式舍入不得误拒。真实parser需测试原TSV和meta格式；包内示例只测试缩小合同，不冒充parser集成验收。

本改动能减少误判，但不会创造新GPU预算，也不重新打开DFlash2或旧F02。对于已有closure，新数值工具的存在本身不是premise_delta。
