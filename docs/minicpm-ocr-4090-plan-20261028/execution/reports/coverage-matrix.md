# 实际覆盖矩阵：Q01–Q22、F01–F12

> 用户已要求停止新增测试，现仅基于已有归档作最终对比；不再运行模型、预解码、单测或部署。2026-10-29 14:09:35 CST实际readback：主sequence为FAIL，9 steps均终态、steps_not_run=0；66 paired为65 PASS、1 FAIL。Mini E0为PASS，Ovis E0为FAIL，两者均已排空。 14:09:50已确认源码hash未变、两模型容器停止、GPU无compute app、旧CPU OCR同实例healthy。完整终态与未测边界见[标准执行结果](observed-standard-results.md).

2026-10-29快照。逐项对照[原方案第8–10节](../../README.md)，区分“实际执行了什么”和“质量/故障合同是否满足”。本表不执行远端任务，不将准备中的扩展或运行中任务提前记PASS。证据来自[标准执行结果](observed-standard-results.md)、[主AI质量结果](ai-quality-results.md)、[补充AI结果](supplement-ai-results.md)、[实施记录](../../execution-report.md)，以及root提供的最新实际readback。

状态含义：**PASS**只适用于明确已验分项；**FAIL**为已观察的不符合或原失败；**NOT_RUN**为尚无实际执行；**GAP**为样本或交付能力缺口；**UNAVAILABLE**为接口/指标不可得；**UNKNOWN**为尚不能确定。局部PASS不代表整行合同通过。AI判断不是human gold；结构GT不完整时不补造块召回、样式准确率或完整页good状态。

## 质量场景

| 原编号 / 要求 | 当前实际执行覆盖 | 质量结论与剩余边界 |
|---|---|---|
| Q01 中文印刷 | S0含试卷和中文PDF；主评73试卷页及相关技术/接口材料；全文105中49份有AI文本参考 | 已测局部；有错字、漏块与关键内容错误，非全中文印刷PASS。古文/繁简/生僻字/拼音及标点各子类未形成完整独立金标结果，UNKNOWN |
| Q02 英文印刷 | 原技术PDF及双栏材料已解析并AI验收 | 已测局部；技术文档存在遗漏、顺序风险。英文印刷子集独立CER/WER与所有规定子场景尚不齐，不以技术混排均分代替PASS |
| Q03 中英技术混排 | 原PDF49页已执行；主评技术41页、接口8页，partial排除完整均值 | 已见图内字/字段遗漏及截断；冻结所有关键token exact门尚未证明，非质量PASS |
| Q04 数字与近形字符 | 控制9页、章码、姓名及数学样本已检查 | 已测局部且有真实错误；近形字源图有歧义者UNKNOWN，不靠归一化消除错误，未达关键token全对 |
| Q05 数学公式 | 旧R0六份：Mini冻结AI内容接受5/6、旧formula可渲染3/6、交集2/6、扣已知格式失败后附加1/6；Ovis分别0/6、6/6、0/6、0/6。Mini v2离线5raw/19片段MathJax19/19 | 冻结内容判断非render-qualified product PASS；三Mini已接受旧产物实际parse FAIL，另正文/选项包$$格式失败。附加资格不是新识别正确率或浏览器布局PASS；旧4raw/18片段保留，0新GPU。fresh v2原6ROI语义/renderer将另核，原数不变；完整公式GT未齐 |
| Q06 理化公式 | R0理化题干/选项与完整试卷已执行、部分AI核对 | 已有状态符号、选项/正文遗漏及错误内容；渲染合法不等于忠实转写，专项关键结构仍FAIL/UNKNOWN |
| Q07 表格 | 整页解析及2个R0表后补诊断；2表双方39/39 cells，TEDS约0.820043、结构0.822967 | 2表局部指标可得；th/td差异非漏格。其他材料存在rowspan错，完整合并格/复杂表GT不足，不能宣称全表格PASS |
| Q08 跨页表格 | G6补充21边界对、3chain；Ovis默认21预算FAIL、3链UNSUPPORTED；LOWPIX另profile有17对正确完成 | LOWPIX条件内7TP/10TN，但4正例预算缺失，正覆盖7/11、固定对17/21；全链文字CER/TEDS未齐。Mini无等价native合并为GAP/UNSUPPORTED，不评分0；导出readback见后文 |
| Q09 复杂版式 | 原PDF、试卷和双栏控制已执行；主187按场景评分 | 已测且有块/选项遗漏；双栏顺序双方仍AI_REVIEW_REQUIRED，完整偏序GT不足，不报99%顺序通过 |
| Q10 全部可见文字 | 主187含头行/题号等检查；4作文完整输入与正文另评 | 存在头行、整行、图内字及水印遗漏，完整性FAIL保留。正文CER不能抵消关键漏块；无全量分标签召回GT |
| Q11 图中文字 | 整页图内字路径、R0带图文字crop与原生图形extra已执行 | 存在漏图中文字；R0公式文字任务不要求曲线几何。保留图片不等于文字已识别，图形语义另判，不整体PASS |
| Q12 图表转表 | 控制图表及原生figure10项（其中5图表）已执行 | 控制图所有关键标签/值正确但漏冗余yticks，实用接受90分、all_visible_text_complete=false；原生caption有趋势/系列反转。原要求至少10个清晰图表转表块尚未证明齐备，GAP |
| Q13 手写与涂改 | 中文长段4、姓名30、英文真实手写3、stylus数学3页+6crop已执行 | 中文纸面手写数学与多作者仍GAP；stylus非纸拍/非中文数学。writer身份和足够书写者分组不足，不宣称真实手写泛化PASS |
| Q14 空白与负例20输入 | 旧controls实际只有blank、grid两项负例；其余控制不能冒充负例数 | **GAP：2/20已测，原20未齐。** 空白控制Ovis无源解释为已见FAIL；扩展20negative已source-approved、尚未GPU执行，暂无新模型终态 |
| Q15 方向与横版 | 旧扰动只有90度及+5度倾斜覆盖 | **NOT_RUN：180/270/EXIF**；真实横版/混合方向的完整核对不足。扩展18orientation已source-approved但未GPU，不把90度结果推给所有方向 |
| Q16 低质采集 | 真实照片/表单/盖章材料、6源×8扰动48份已执行并分unit评分 | 有真实漏字/错误；合成派生不代替真实采集，眩光/曲面等分层最低样本与GT尚未齐，局部验收不等于类别PASS |
| Q17 多页与混合PDF | 原生PDF49页、拍摄图像PDF及转换文件已走页面流程 | **NOT_RUN：原生+扫描混合PDF、隐藏文字与像素冲突**；不同页尺寸/混合方向完整合同未证明。扩展5mixed/hidden已source-approved但未GPU，不写PASS |
| Q18 文档资源 | 逐页/文档产物与部分公式、Mermaid实际渲染；G6派生34MD实际readback | 已测局部。Mermaid8/9且语法FAIL保留；公式serialization合法不证明识别正确。G6有3个预期空白页，下游兼容未测，不能称全部资源非空/全渲染PASS |
| Q19 字段抽取（可选） | 目前是OCR正文或R0姓名识别，没有独立字段抽取接口交付 | **OPTIONAL_NOT_DELIVERED**。姓名R0 exact不能冒充姓名/日期/金额等字段接口PASS |
| Q20 题面语义样式20区域 | 已核3真实文档/7页/20范围的既有S0产品；Mini文字19/20、样式exact1/20，Ovis文字20/20、样式exact11/20 | **部分能力＋失败变体**。单线Ovis11/11、Mini1/11；4波浪线与4上点双方0exact。style_marks字段UNAVAILABLE不等于产品无样式；无render PASS，删除线/圈点真实样本仍GAP。详见补充报告 |
| Q21 长段作文/长竖图 | 4原长图全纳入；正文1645字，含头行的完整输入单列 | Ovis正文CER1.9453%、完整输入4/4接受；Mini4.3769%、4/4拒绝（3头行+1整行遗漏）。AI小样结论，不外推独立作者泛化；涂改样式仍UNAVAILABLE |
| Q22 印章与章压正文 | 主评5盖章合同、2独立章crop及扰动8章crop已执行 | 有章码错误及遮挡未知；2章仅1份双方完整可评分，弧形/压字完整GT与原检测框覆盖未证明齐备，部分FAIL/UNKNOWN保留 |

### 原8.1退化数量缺口

旧实际是**6个源×8条件=48派生输入**，其中32 page、8 long_image、8 seal crop。原要求24个已金标基页、约120–180变体、规定操作至少8不同基页，尚未满足。不能把48派生图当48独立来源，或把其中非page单元算成48基页。24基页164变体扩展已source-approved但未GPU，且仅15/24基页有全文参考；本快照尚无该扩展模型终态，原48结果保留，不补造未运行DPI/EXIF/复合退化曲线。

## 故障、恢复与生命周期

| 原编号 / 要求 | 已观察执行与状态 | 尚未证明或不支持部分 |
|---|---|---|
| F01 损坏/截断/伪扩展/无效图 | 原损坏/加密负例明确拒绝；扩展5输入按预期FAIL且0模型调用，验证PASS；PDF伪装检查有本地真实fixture | 局部拒绝PASS，不将输入非法的FAIL当模型质量失败；未声称所有损坏格式均覆盖 |
| F02 加密PDF密码路径 | 已验证无密码拒绝 | CLI不接密码，正确/错误密码受控接口不支持；记能力GAP，不写三密码路径PASS |
| F03 字节/页数/像素边界 | 已验证PDF渲染前像素阈值、巨大画布拒绝及正常RGB保持，扩展负例实际拒绝 | 仅像素边界已测；不扩称字节上限、页数上限或全部解压炸弹隔离通过，其他NOT_RUN/UNAVAILABLE |
| F04 空PDF/空白/纯图/混方向尺寸 | blank/grid控制已执行，空白Ovis无源解释FAIL；原PDF/多页已执行 | 空PDF、纯图、混合方向及不同尺寸完整组合覆盖未齐，不能因页级终态就合同PASS |
| F05 输出/上下文预算 | 人为length拒绝、真实Mini GOV区域length截断、跨页16K预算FAIL均保留；API超上下文4xx已测 | 检测与失败留存分项通过不等于完整恢复；原截断不能因其他块成功洗掉，完整超长表格分块恢复未证明 |
| F06 超时/断连/5xx/4xx | r2已在29真实loopback、synthetic responses、无GPU验证PASS：21tests＋9scenarios（3轮）；disconnect按一次transient retry共2次尝试，最终FAIL raw保留 | 这是传输/有限重试/截止证据，不是GPU模型故障注入。r1误期待1次而FAIL的历史保留，不覆盖为成功 |
| F07 页/区域/组装/资源失败 | 真实Mini420中1页FAIL传递为92/93文档PASS；本地fixture覆盖组装及失败产物保留，F10原子写另证 | 不把本地fixture称为真实GPU每类故障均已注入；图片写失败/所有中途组装组合仍需逐项证据 |
| F08 服务/布局进程中断恢复 | ops-r2两模型断网冷启、进程停止/重启恢复、标准容器dev4实际PASS | 中途正式任务/布局子进程的完整失败传播不由空闲生命周期证明；ops-r3追加4次加原2次、每模型3次fault→restart→dev4已实际PASS；这不等于布局子进程和所有中途任务场景均已覆盖 |
| F09 取消/断连/重复提交 | Mini cancel-r2观察到active且queue drain PASS；原取消predicate UNAVAILABLE、无abort增量、outer exit2保留。Ovis取消counter限制另有源/实际证据 | 取消排队/运行、重复同文件隔离与状态合同未全部真实闭合；F06 synthetic断连不能替代GPU取消，UNKNOWN/UNAVAILABLE分别保留 |
| F10 只读目录/空间不足 | 29任务私有、CPU-only、network-none容器实际只读bind/64KiB tmpfs拒绝与ENOSPC；原完整JSON字节/hash保留，0.074秒PASS | 证明atomic_json层，不是填宿主盘，也不是GPU整页HTTP写故障验收 |
| F11 禁网首次/再次启动 | ops-r2两模型实际断网冷启动、停止及重启恢复，标准dev4均PASS | 仅对已冻结依赖和被测环境成立，不替代全新宿主离线重建或所有字体/样本覆盖 |
| F12 容器/包装层恢复 | ops-r2标准容器恢复及dev4分项PASS | ops-r3各模型累计3次故障/重启/dev4已PASS；F06 r2 HTTP suite真实loopback synthetic/noGPU已PASS；可选任务包装持久化合同不由此自动通过 |

## G6真实导出文件补证

已完成实际只读导出readback：LOWPIX的17个执行PASS边界任务共34份derived Markdown全部存在，hash、UTF-8内容、embedded rewritten结果及非表块保留一致；其中**31份非空、3份Arabic第二页按表格移到前页后的合同预期空白**，不能写34份全非空。10负例的20份MD与原Stage1一致，1个图像资源存在、非空且hash匹配；3个空白页的下游消费兼容尚未测。

两模型58份Stage1 result与默认/LOWPIX共48份Stage2 result的冻结hash均未变。Stage1独立MD历史hash清单未提供，其不变性由冻结JSON内容与result hash支持。默认21预算失败及3UNSUPPORTED、LOWPIX4预算失败及3链UNSUPPORTED均保留。此readback补的是落盘与非表内容保持证据，不新增语义验收或全链CER/TEDS，也不把AI源审升级为人工金标。

## 本快照不能宣称的完成项

Q14负例数量、Q15完整方向/EXIF、8.1基页与变体规模、Q17混合/隐藏层冲突仍有明确缺口；扩展准备不算终态。Q13中文纸面数学/独立多作者为GAP；Q20已有部分产品样式能力与失败变体，删除线/圈点缺真实样本，不能按字段UNAVAILABLE抹掉已见能力。Q19独立字段接口未交付。正式66 paired及两次E0已全终态，master sequence FAIL（66中65 PASS/1 FAIL；Mini E0 PASS、Ovis E0 FAIL），全部新增测试按用户要求停止，仅离线汇总。 F06 r2 HTTP suite已有29实际21 tests、9 scenarios/3轮PASS证据，不因ops-r3恢复而混记为GPU或任务包装验收；DSpark仍为NOT_ADMITTED_QUALITY_GATE。不存在“execution全部PASS所以全场景质量PASS”的结论。

宏CER家族聚合P2已在Mac本地repo整合已审补丁（scoring.py SHA `a5364f96df8a96113212c34eee2bd046da0d187b3e44725856daa13b12d268f1`），实际repo 31项测试PASS（0.698秒、exit0）；证据见[实施记录的本地评分整合说明](../../execution-report.md#正式序列启动与补充状态)。29仍冻结v11旧评分源 `42153baccdc43a017d0d937e36b455073cd3277cfba6a149272950efe017eed2`，用户要求停止后不再部署到29；本地修复不改变远端22文件冻结，原GT/结果未覆盖、micro不变，不能称远端已修或全部关闭。

停止边界补充：43 controls、24基页164 variants、chart10、pure6、P05、新F07 OS component及F09 SSE均仅准备未执行，按用户要求不再补跑。实际两次E0均已终态，Mini437全PASS；Ovis1523中1521PASS、2截断FAIL，均排空，master FAIL。资源和正式速度只待已有归档离线汇总。
