# 评分链路实施状态

实现模块：[execution/ocrbench/scoring.py](execution/ocrbench/scoring.py)。版本 `ocrbench-scoring-v1`，仅离线读取预测与GT；不导入模型，不向模型提供GT，不修改资料。

已实现严格字符编辑距离、NFC加空白规范化的辅助CER、空白分词WER、整段EM、空GT新增字符、关键equals/contains断言、文本profile逐组门、page-good-v1三态判定、固定GT全集缺预测失败、重复ID拒绝，以及各unit_kind独立汇总。失败预测按空串计GT删除，原模型部分输出仍保留在runner产物中。中文WER不作主指标。编辑距离使用线性内存精确动态规划，超长文本运行时间仍为二次复杂度。

集合micro CER按字符加权；当前macro CER为声明文字组的平均值，不能宣称已实现来源家族macro或cluster bootstrap。profile以GT预先声明为准，不从模型输出推断。只有GT标记 `GT_complete_for_required_tasks=true`、`provenance.kind=human_verified`、规则/GT/scorer版本齐全且全部适用任务可评分，才允许逐页合格；自动提取草稿仍可计算文字诊断但不会进入主good吞吐。

表格TEDS/TEDS-Struct、span位置单元格CER、文本块召回与关键块、阅读序pair/severe、公式LaTex EM诊断，以及绑定的资源/样式人工断言已经实现。依赖固定apted==1.0.3、lxml==5.4.0。公式渲染及人工结构门尚不可得时保持UNAVAILABLE；没有将LaTex字符串相同代替结构通过。结构对应关系未建立时仍UNSCORED，不能从成功预测子集反向筛GT。

## GT格式

```json
{"pages":[{"page_id":"p1","acceptance_rule_id":"page-good-v1","GT_version":"human-v1","scorer_version":"ocrbench-scoring-v1","unit_kind":"page","required_tasks":["text"],"required_text_groups":[{"id":"full","profile":"printed_chinese","text":"人工核验文字","prediction_field":"raw_text"}],"required_output_units":["raw_text"],"critical_assertions":[],"GT_complete_for_required_tasks":true,"provenance":{"kind":"human_verified"},"applicability":{"text_blocks":false,"table":false,"formula":false,"reading_order":false,"style":false,"resources":false}}]}
```

`false`适用声明只用于真实没有该任务的页/区域；不能为通过评分删除真实结构要求。文本断言支持 `field`、`operation=equals|contains`、`value`、`id`。没有图内文字、全部文字块召回GT的纯文字样本只能标作文字诊断，不能代表完整页面验收。GT完整性和human_verified目前为输入声明，仍需要独立标注流程审查其真实性。

## 执行

在execution目录：

```bash
python3 -m ocrbench.scoring --predictions predictions.json --gt gt.json --wall-seconds 100 --out scores.json
python3 -m unittest discover -s tests -p test_scoring.py -v
```

predictions为数组或 `{pages:[...]}`，每页至少page_id/status/raw_text；status仅PASS/SUCCESS/COMPLETE表示执行完成。runner如发现截断/超预算/关键错误，必须提供非成功status或相应布尔字段；artifacts_valid/identity_valid为false直接失败。GT缺预测保留失败。wall-seconds必须传整个固定提交集合包含所有失败、重试和超时的真实墙钟；评分器不从成功页时长拼造分母。无完整GT主合格吞吐为null；诊断known-good另列。不同page/long_image/crop单位不混算。可用Python `summarize(..., gpu_joules=...)`传入真实批量积分能耗，零good时J/good=null、原因NO_GOOD_PAGES。

本次已实跑8个定向测试：Unicode/编辑距离、文本成功、失败删除、缺GT/自动草稿、空白幻觉/关键断言、适用结构不可用、100页汇总不误判全部合格、CLI缺预测全集对账。全部通过。未在29执行评分，未有模型质量、性能或能耗结论。

## 结构GT及对应关系

表格算法按[PubTabNet TEDS定义](https://github.com/ibm-aur-nlp/PubTabNet/blob/master/src/metric.py)：树节点insert/delete成本1；标签/span不同时rename成本1，cell内容为标签token加字符序列的归一化Levenshtein。分母为两表最大后代节点数。实现保留th为独立cell标签；不是无条件声称原官方数字完全一致。表格入口按HTML5严格fragment解析（html5lib1.1，单个table，可有thead/tbody/tfoot）；接受合法未引号属性和可省略的td/tr结束标签，拒绝真正截断/非法表格，非法预测HTML_valid=false、TEDS=0。cellCER按原始行列起点和rowspan/colspan定位，对缺格删除、额外格插入；span错误不靠串接全表文字获得零CER。此定位指标与TEDS分别报告。

`structure_GT`按任务列出完整GT对象；`text_blocks:[{id,critical}]`、`reading_order:[{before,after,severe}]`、`table:[{id,html,critical_assertions:[]}]`、`formula:[{id,latex}]`。关键表格断言为匹配block上的field/value exact。文本块召回这里指独立人工确认的块对应存在，字符质量另由CER判定；未对应GT块在分母中计遗漏。reading_order每条GT偏序都入分母，漏端点判错。

`assessment`是模型输出后独立人工核对的**对应关系**，不是用来改写GT；必须 `kind=human_verified_correspondence` 和 `prediction_sha256=prediction_digest(prediction)`，以及 `matches:{GT_block_id: predicted_ordered_blocks_index|null}`。对应关系必须一对一，索引无效/重复直接抛出ValueError拒绝评分。错误digest使结构UNAVAILABLE。此离线字段禁止传入模型；没有由预测自报的GT身份。多模型分别需要自己的对应关系。

resources/style的GT列出{id,...}，assessment提供`resources_assertions`/`style_assertions:[{id,passes:bool,...evidence}]`；要求ID集合与GT完全一致并绑定输出digest，否则UNAVAILABLE。这是人工完整资源/样式检查的承载与计分接口，不声称自动完成路径、原页身份或样式视觉验证。公式LaTex EM按匹配ID计算，render/结构门仍UNAVAILABLE，符号关键断言可用顶层equals/contains字段明确核验。

表格依赖安装示例（Python3.12）：`pip install apted==1.0.3 lxml==5.4.0 html5lib==1.1 six==1.17.0 webencodings==0.6.1`。无依赖时纯文字评分可运行，但表格明确UNAVAILABLE。

结构扩展后的最终验证：使用独立Python3.12.12环境 `/private/tmp/ocr-scoring-py312-20261029`、apted1.0.3、lxml5.4.0，运行 `python -m unittest discover -s docs/minicpm-ocr-4090-plan-20261028/execution/tests -p test_scoring.py -v`，12项全部通过。新增span拆分、rowspan/th、文字变化但结构相同、非法HTML、GT表缺失、额外预测表、漏块/严重错序、对应digest失配、重复匹配拒绝、资源断言完整性。额外预测表会保留索引并使表格页门失败，不从匹配GT子集里静默排除。

初次系统Python3.14测试因尚未装依赖失败；随后uv默认缓存目录受沙箱限制未安装成功。改用Python3.12独立环境及 `/private/tmp/ocr-scoring-uv-cache` 后固定依赖安装与最终12项验证通过。没有删断言或将缺依赖测试跳过。

增量修复独立review发现的两个真实缺陷：GT_version/规则/scorer版本必须为非空字符串，不能只有键且值null；主合格吞吐使用整个固定工作负载GT完整性门，而不是按unit分组后隔离无GT的UNKNOWN输入。加入回归后13项评分测试通过，额外无GT项现在会使所有unit主good吞吐null，已知子集仅诊断。

## AI裁判验收路径（2026-10-29用户明确授权）

AI参考使用独立规则 `page-good-ai-v1`，原 `page-good-v1` / `provenance.kind=human_verified` 路径不变。AI规则复用全部文本/结构门槛，不把100分rubric换算CER、不自动通过未核对任务。AI结果标 `reference_kind=AI_JUDGED`，汇总保留 `reference_kinds`。

参考GT须填：

```json
{"acceptance_rule_id":"page-good-ai-v1","reference_provenance":{"kind":"ai_verified","judge_id":"root-blind-review","source_image_sha256":"64位裁判所看图文件sha256","input_pixel_hash":"64位实际RGB像素sha256","source_sha256":"64位原始输入文件sha256","review_status":"accepted","review_evidence":[{"path":"private/review.json","sha256":"64位review证据sha256"}]},"uncertainties":[]}
```

judge_id须非空；source_image_sha256及证据sha256须为小写64位hex；证据path须非空，accepted才准入。路径/hash只是可追溯引用校验，评分函数不冒称已重新读取每个证据文件；root须保存这些真实证据。input_pixel_hash为AI路径必填并核对预测的实际RGB哈希；source_sha256若填入则核对原始文件哈希；**不把渲染图文件hash与原PDF文件hash比较**。裁判看到的图、实际输入像素与原源文件的映射由review证据保留。AI与human标签冲突拒绝评分。

`uncertainties:[{resolved:false,affects_required_tasks:true,...}]` 表示必需任务尚未核清，结果UNSCORED/GT_complete=false；只有已核清的完整范围或独立crop才可声明GT完整。已清楚但超CER门照常FAIL，不用AI身份放宽门槛。结构对应可使用 `assessment.kind=ai_verified_correspondence`，仍要求judge/source-image/review/evidence及完整prediction_sha256绑定；不取代实际表格/顺序评分，公式render门仍须真实验证。

reporting遇AI参考明确标 `AI_JUDGED_REFERENCE_METRICS_SEPARATE_FROM_HUMAN`；全固定工作负载完整性门仍保留。通过 `--gt-draft`导入的通道维持诊断标识，不自动宣布主质量赢家。

### 独立blind rubric汇总

`reporting.rubric_summary(document)` 或CLI `--rubric rubric.json`读取root已审裁的成绩：

```json
{"rubric_version":"root-rubric-v1","reviews":[{"page_id":"p1","blind_candidate_id":"candidate-X","judge_id":"root","source_image_sha256":"64位hex","review_status":"accepted","review_evidence":[{"path":"private/review.json","sha256":"64位hex"}],"score_100":85,"criteria":{"fidelity":{"earned":35,"possible":40}},"critical_errors":[]}]}
```

这里只校验评审身份、证据字段、唯一page/candidate和0–100有限分数，按匿名候选给已审数量及均分；criteria原样保留供root核对权重。接口不声称验证了root评分算术、不自动转CER/page-good、不生成赢家。这样AI评分与客观指标保持并列、可追溯。

本次增量验证：16项scoring和7项reporting测试全部通过。覆盖有效AI参考、缺证据、必需存疑未解决、像素身份错误、原PDF与裁判图文件hash不同仍按正确映射核验、human旧路径、AI rubric不转换CER及超界分拒绝。


AI增量review修复：AI参考必须提供有效input_pixel_hash并与预测实际RGB哈希相等，不能仅以任意格式正确的source_image_sha256获得通过；human规则同时携带ai_verified标签时也拒绝冲突。`text_reference_verified`将文字参考核准状态与整页结构可评分状态分开：未决必需文字参考只保留单页/`unverified_text_diagnostics`诊断，不进入正式micro/macro CER；公式渲染不可得不会抹掉另已核准的文字CER。汇总明确已核准units/characters及覆盖率。

HUMAN_VERIFIED与AI_JUDGED在`reference_strata`分列，每列仍使用原始整批墙钟及全固定GT门。相同unit若混合参考来源，顶层unit不输出合并CER/主good吞吐，仅保留来源计数并要求读取分层列；不以“SEPARATE”标签掩盖实际混算。新增回归后19项scoring、7项reporting测试通过。

## table-score-view-v1（2026-10-29真实嵌图表格发现展示层偏差后）

同样正确单元格文字在产品HTML里加入 `<br/>`、`<span data-ocr-supplement>` 后，旧raw HTML TEDS会惩罚展示token，不能公平比较。现在 `table_metrics` 对**GT与两模型产品HTML使用同一评价视图规则**：只在td/th内部移除span/b/strong/i/em/font/small/big展示wrapper并完整保留文字；br变为换行分隔，修剪cell外缘展示空白；img不以路径或文件名充当文字。table/tr/thead/tbody/tfoot、rowspan/colspan、sup/sub、MathML等语义结构保留，不把不同列/span或公式扁平成同样文本。既有.95/.97/1%门保持不变。

三通道分开：模型原始响应在request证据；确定性产品HTML保存在适配器产物；评分只派生 `reference_score_view` / `prediction_score_view`，不覆盖原始或产品HTML。主`TEDS`/`TEDS_struct`/`cell_CER`来自共同视图；原始产品HTML的`raw_HTML_TEDS`、`raw_HTML_TEDS_struct`、`raw_cell_CER`、raw计数独立保留诊断。版本固定`score_view_version=table-score-view-v1`。

图片数量与 `resource_validation_required` 保留。任一表格含图片，整体页门要求明确资源GT与相应核验，不能用未适用资源声明自动通过。纯文字表预测只给img、以文件名放GT文字而不输出可见文字，cellCER仍按删除失败；插图另须正确来源资源门。正文样式准确性仍是独立适用style门，不由展示wrapper移除证明样式正确。

新增3项定向回归（总22项scoring PASS）：展示wrapper/嵌图补字对称等分、漏字加图仍失败、span/sup/MathML语义不抹平、br保持词间分隔、嵌图必须资源门。首次资源门回归失败暴露接线遗漏，已修真实structural_scores接线后全通过；未改GT或降低门槛。


HTML输入兼容增量：真实 `PAPER012-p006`输出使用合法 `<table border=1>`，旧XML入口误判。评分入口现统一采用 [html5lib HTMLParser严格模式](https://html5lib.readthedocs.io/en/latest/html5lib.html#html5lib.html5parser.HTMLParser) 的HTML5 fragment语义，冻结 `html_parser_version=html5lib-1.1-strict-fragment-v1`。合法未引号属性、optional td/tr结束及void img/br按标准树解释；缺外层table闭合或真正解析错误仍失败，不通过容错吞掉截断。隐含tbody由标准解析器对称建立，不改模型原文、GT或门槛。

MathML保留HTML5 foreign-content命名空间。评价视图使用HTML5 serializer往返，而不把带ns0前缀的XML串误当新HTML重读；回归确认msup/mi/mn和span语义仍在。仅忽略不渲染的HTML注释并保留后续文本。

新增包锁：html5lib==1.1，实际解析依赖six==1.17.0、webencodings==0.6.1；现有apted1.0.3、lxml5.4.0不变。没有修改共享pyproject，由部署owner接线。Python3.12专用环境已装以上依赖，24项scoring测试全部通过（含真实unquoted-border、optional-cell、外层table截断、MathML/colspan往返及原展示公平门）。
