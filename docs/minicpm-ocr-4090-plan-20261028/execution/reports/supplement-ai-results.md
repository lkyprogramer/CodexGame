# 补充AI结果：控制、扰动、数学与区域结构

2026-10-29冻结补充版，`AI_JUDGED`、`human_verified=false`。本版74输入分成controls9、robust48、math9和R0结构8，分别在判断冻结后解盲；不跨case平均原A/B字母，不以任意权重合成整体winner。它们不改写[主评187及原273区域文本结果](ai-quality-results.md)。姓名R0同12源的布局/识别公平性更正亦见主报告的姓名章节。

分数为AI实用性评分，满分100；渲染前冻结的AI内容判断与分数分开，不等于渲染合格的产品验收。partial不进入完整输入均分，未知保留；可确定的致命错误即使源图有其他未知字仍记拒绝。源图文字、姓名、私有路径、输入映射与seed均不公开。

## 控制输入：9页

| 模型 | 完整配对评分 | 样本均分 | 接受 / 拒绝 / 待复核 |
|---|---:|---:|---:|
| Mini | 9/9 | 97.56 | 8 / 0 / 1 |
| Ovis | 9/9 | 91.44 | 7 / 1 / 1 |

空白页控制中Ovis臆造了“图像模糊”的解释，属于无源支持内容；不能把它当正确转录。双栏阅读顺序两者均待复核。图表控制中所有标签和值都正确，仅遗漏冗余y轴刻度，两者均90分并按实用性接受，但`all_visible_text_complete=false`，不得写成所有文字完整。这与主评图表的同类验收口径一致；可解释的Month/Value表头不当作无源编造。

## 扰动：6份源输入 × 8种条件

48份派生输入来自6个源，不是48个独立样本、作者或家族。按unit拆分，不把32页、8长图和8章裁剪混算总分，也不据重复派生输入计算跨来源泛化CI。

| unit / 数量 | Mini均分 | Ovis均分 | Mini接受 / 拒绝 / 待复核 | Ovis接受 / 拒绝 / 待复核 |
|---|---:|---:|---:|---:|
| page / 32 | 94.71875 | 98.50 | 29 / 3 / 0 | 31 / 1 / 0 |
| long_image / 8 | 90.00 | 95.375 | 1 / 7 / 0 | 6 / 1 / 1 |
| seal crop / 8 | 98.875 | 100.00 | 7 / 1 / 0 | 8 / 0 / 0 |

## 数学：3个整页与6个裁剪

这些来源是stylus数字手写，不是纸面拍摄或中文手写数学泛化材料。3个page只有1个双方完整可评分，不能拿该单例67/67作整页均分排名；完整输入实际0/3接受：Mini3拒绝，Ovis2拒绝、1未知。该范围只能证明已见的遗漏、变量/关系符替换等局限。原始源审先后偏差及其说明保留，不伪称无偏标准benchmark。

6个crop仅5个可完整配对评分，其均分Mini95.80、Ovis82.20；验收仍按全部6个计：Mini3接受、1拒绝、1待复核、1未知；Ovis1接受、5拒绝。O/0存在源图歧义的项保留partial，不将选字差异记错；独立于此歧义的整行遗漏、错误函数结构、根号分母、态符号或近似关系丢失仍是已知缺陷。公式图片的文字可读和最终产品可渲染是不同验收项。

Mini mathadapter v2的serialization修复已通过15项测试、真实SDK验证与Astra独立review。v11代码已实际部署，`source-v11-install.json` 为PASS；部署适配器SHA256为 `135321e34ca69592c2d43e778f3b0811f713b892b552516b598065de92280933`。另用5份保留原始响应离线重放，经适配器导出19个片段，MathJax实际渲染19/19合法；该重放只验证序列化，0次新模型调用，不证明修复后的新GPU识别质量。4份旧bad-wrapper产物保留，不用代码修复覆盖为成功；主187与原273均未包含这4份，原主数字不变。旧single-field渲染统计Mini69/73、Ovis80/80包含mixed mathdoc，既不是纯公式识别正确率，也不能作为最终公式排名；本次19片段重放是修正后的序列化验证，仍不能替代重新推理后的完整公式识别验收。

## R0结构：6个公式/整题/带图crop与2个table

| 任务范围 | 输入 / 可完整配对 | Mini均分 | Ovis均分 | Mini冻结AI内容接受 / 拒绝 | Ovis冻结AI内容接受 / 拒绝 |
|---|---:|---:|---:|---:|---:|
| 公式、完整题干选项及带图文字crop | 6 / 6 | 94.6667 | 51.3333 | 5 / 1 | 0 / 6 |
| table crop | 2 / 2 | 99.00 | 99.00 | 2 / 0 | 2 / 0 |

前6项不是纯公式benchmark，包含选项、题干和图中文字。公式识别模式不要求重建图形折线；可见轴、tick及全部选项正确保留即可在文字任务接受，几何/图形理解由X04另测，不能额外强加该模式未要求的曲线重建。反之，漏完整选项或题干仍是可确定缺陷。

Astra独立核对源图、冻结判断、解盲后的实际result SHA与MathJax证据后，对这6份**旧产物**另列后验附加资格；原冻结分数和AI内容接受数不改写：

| 同6份旧R0产物 | Mini | Ovis |
|---|---:|---:|
| 冻结AI内容接受 | 5/6 | 0/6 |
| 旧formula字段实际可渲染 | 3/6 | 6/6 |
| 内容接受与可渲染的交集 | 2/6 | 0/6 |
| 再排除已知格式失败后的旧产物附加资格 | 1/6 | 0/6 |

Mini原AI内容接受中，匿名R0结构case-0002、case-0004、case-0005实际parse FAIL；另case-0006把外部正文/选项整体包在`$$`内，是已知格式失败。排除该格式错误不等于追加曲线重建要求。不能拿5/6称render-qualified product PASS；附加1/6、0/6也不是新识别正确率或完整浏览器布局验收。

最新v2离线重放为5份保留raw、19片段MathJax19/19；更早4份/18片段证据保留，不与新v2混记，全部为0新GPU调用。修复不覆盖旧parse/format FAIL，也不证明新推理质量。正式R0的fresh v2输出将另核原6个ROI的语义与renderer，不更新本次冻结原数。

两份table后补量化均为AI源审诊断，不改变原273：两模型均39/39单元格对齐、2/2 HTML合法，macro TEDS=0.820043、TEDS-struct=0.822967、micro cell CER=0.208333%。差异包含th/td语义标签，不能把树结构分下降叫成漏格；唯一字符差异为空格。该结果不证明完整页、复杂合并单元格或跨页表GT已齐备。

## 冻结与证据边界

四批均在冻结判断后解盲，冻结证书SHA256如下，公开报告不包含私有身份映射：

- controls9（9输入）：`e96ff18b5c7f16cde1c78038ea2697a537240cc8f8f280a4b2d8435da04d3f15`。
- robust48（48输入）：`d22b12add393b8d10eb8d83d053ebc7ecfc90c0f6aeb3e74d2fafa6b9a10454f`。
- math9（9输入）：`0bae9e2e288955fceec8f58aad1fdf7e09ced3f9b73166aef71783889940c744`。
- r0-structure8（8输入）：`136c4a1883cd9c0eb3ab118f2276fd0a27934c880c88ae252242ea82ba7066c8`。

主187、主R0文本273和本74专项分别保留分母，不把补充诊断重新包装为预先冻结的主测试。ops-r1因Env顺序导致的false fail已保留证据；root已在29实际完成ops-r2，两模型的断网冷启动、进程停止、重启恢复，以及恢复标准容器后的dev4均PASS。ops-r3-repeats已由root实际readback PASS：4次追加故障事件加ops-r2原2次，合计每模型3次fault→restart→dev4恢复，Mini使用v11 mathadapter v2。ops-r3收尾时GPU idle、旧CPU服务healthy、旧summary hash不变；这是随后正式序列启动之前的状态，不代表正式运行期间GPU空闲。 F06 r2 HTTP suite已由root在29实际PASS：21 tests、9 scenarios分3轮，synthetic responses、无GPU；该传输证据与ops恢复证据分开，不替代真实模型或任务包装持久化验收。正式66 trials＋2次E0的串行序列 `sequence-g3g4-e0-r1` 已实际RUNNING（durable PID `1745300`）；这是序列运行状态，不代表各子任务均已开始或完成，不发布单trial赢家。 DSpark按README第11节标记`NOT_ADMITTED_QUALITY_GATE`，质量门尚未PASS，下载、权重验证与脚本准备不等于GPU加速运行。

## 原生图形专项（独立任务）

Ovis原生figure实际验收10项AI均分90.5，5流程图均分95.6、5图表均分85.4；所选5份流程Mermaid与源拓扑23节点/19边匹配。caption仍有最高系列判断、红蓝趋势和hatch方向反转等真实风险，不能因拓扑匹配而覆盖语义错误。root实际parser检查9份code为8 PASS、1 FAIL；随后真实Chrome/Mermaid浏览器渲染亦为8/9，与parser失败的是同一份未选中额外图的语法错误。所选5份流程的源拓扑已验收，另外4份额外图不能因parser或浏览器可渲染就宣称语义正确。该任务不混入主OCR/CER分；Mini没有等价官方原生任务，标UNSUPPORTED，不评分0。

## G6原生跨页表专项（独立任务）

Ovis默认像素预算/16K下21对全部FAIL_BUDGET，3条chain均UNSUPPORTED。LOWPIX是另一profile：可完成条件内7 TP、10 TN、0 FP、0 FN，但另4个正例因预算未完成；全正例覆盖7/11，固定21对整体可正确完成17/21，不能声称全覆盖100%，3条chain仍UNSUPPORTED。cell split核对24/41正确，未完成全链文字CER/TEDS；局部合并/数值点查不代表全链质量通过。Mini无等价原生自动合并能力，UNSUPPORTED不能当0分比较。源身份仅AI核验，全部结果与主OCR分分开。

## 真实题面样式20目标：能力诊断补证

3份真实文档、7页、20个目标范围按source-first固定；这是对已有S0产物的`UNBLINDED_CAPABILITY_DIAGNOSTIC`，不是新盲测，不新增GPU推理或模型调用，不改主187评分。原v1的2个本地RGB不匹配保留；root只读29实际admitted source PNG、批准addendum后补齐2个目标，v2全部20目标输入身份已核对。页内多个范围不当独立文档或writer。

| 指标（同20目标） | Mini | Ovis |
|---|---:|---:|
| 目标文字exact | 19/20 | 20/20 |
| 目标样式＋文字exact | 1/20 | 11/20 |
| 样式缺失 | 19 | 7 |
| 样式种类错误 | 0 | 1（双线变单线） |
| 样式位置错误 | 0 | 1（上点变下点） |
| 11个单下划线exact | 1/11 | 11/11 |
| 4个波浪线exact | 0/4 | 0/4 |
| 4个上方着重号exact | 0/4 | 0/4 |

Mini一项目标文字发生日→曰错误。两adapter的`style_marks=UNAVAILABLE`只是统一字段不可得，不能据此断言最终block/text/Markdown完全没有样式；Ovis的单下划线已在产品内容明确编码，Mini也有1个正确保留。当前结论是**部分样式能力已见、其余变体存在失败**，不是整项能力全无。显式编码不等于浏览器render PASS，具体范围边界亦不证明整段全范围正确；删除线/圈点仍缺真实样本，保持GAP。

## 最新冻结与执行状态


Astra max终review核对5份冻结证书与261输入的hash通过；另发现scorer宏CER家族聚合P2。Astra已review通过的补丁现已整合到Mac本地repo的scoring.py，并新增test_scoring_macro.py；源码SHA256 `a5364f96df8a96113212c34eee2bd046da0d187b3e44725856daa13b12d268f1`。root在实际repo execution目录运行 `python -m unittest discover -s tests -p 'test_scoring*.py' -v`，31项PASS、0.698秒、exit0。本地评分工具已修复；29仍保持冻结v11评分源码 `42153baccdc43a017d0d937e36b455073cd3277cfba6a149272950efe017eed2`，待全部GPU测量结束后才部署，不能称远端已修或全部关闭。当前正式冻结22个文件均在远端任务目录，Mac独立副本的整合不会改变该实验；原GT与冻结结果没有覆盖，micro CER不变。该缺陷是CER聚合实现问题，不把既有AI评分的family macro重新解释成字符CER。

扩展43输入（20negative＋18orientation＋5mixed/hidden）与24基页164份robust变体已source-approved，尚未运行GPU；robust只有15/24基页有全文参考，不能写24页全GT或扩展质量PASS。

新增pure6和chart10源已由root批准但未GPU；P05 same/unique30仅完成selection批准，少量补覆盖后续另列，不修改正式66 trials。
