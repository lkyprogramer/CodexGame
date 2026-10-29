# 29 实施进展

> 用户已要求停止新增测试，现仅基于已有归档作最终对比；不再运行模型、预解码、单测或部署。2026-10-29 14:09:35 CST实际readback：主sequence为FAIL，9 steps均终态、steps_not_run=0；66 paired为65 PASS、1 FAIL。Mini E0为PASS，Ovis E0为FAIL，两者均已排空。 14:09:50已确认源码hash未变、两模型容器停止、GPU无compute app、旧CPU OCR同实例healthy。完整终态与未测边界见[标准执行结果](execution/reports/observed-standard-results.md).

2026-10-29，已按用户要求停止所有新增测试。原方案是设计基准，本文件保留已执行事实；已基于既有归档完成离线对比汇报，入口见下。

## 当前已观察事实

已有归档的最终离线对比已完成，见[最终对比报告](execution/reports/final-comparison-20261029.md)及[正式性能汇总CSV](execution/reports/final-performance-20261029.csv)。当前结论以该报告的完整分母、失败组限制及资源/能耗口径为准，本页保留执行历史，不重复性能大表；所有新增测试与部署仍停止。

原Q01–Q22、F01–F12与退化数量合同的实际覆盖、未测/能力缺口和G6导出readback见[覆盖矩阵](execution/reports/coverage-matrix.md)；局部执行PASS不代表完整质量或场景合同通过。

主评187输入已冻结解盲，分场景评分、完整输入验收及49/105全文、273/300区域文本CER见[公开AI质量结果](execution/reports/ai-quality-results.md)。该报告为AI_JUDGED、不是human_verified；新增[补充74专项AI结果](execution/reports/supplement-ai-results.md)分层记录controls、robustness、数学、R0结构与原生图形/G6，主187与原273数字不变。姓名同12源R0后补两模型均10/12 exact，主7/12对10/12包含整页布局损失，不能当纯识别器胜负。

2026-10-29最新快照：两模型S0标准解码全量诊断均已完成。Ovis顶层预处理参数生效后的`c0-v3`为420/420解析、93/93文档产物完成、652次completion调用、2011.351秒批次墙钟；Mini `c0-v3`为419/420解析、92/93文档产物完成、4654次completion调用、2767.172秒批次墙钟。Mini `LOCAL-GOVPDF-01-p003` 的 `block-0016` 真实截断，`finish_reason=length`、输出4096 tokens，原失败保留。双方均为cold adapter、没有同worker开发预热，主性能资格false；Ovis该批另有构建干扰，不作正式性能排名。解析完成不等于文字正确率。详细分母与元数据证据见[标准解码结果快照](execution/reports/observed-standard-results.md)。

Mini补充验证已完成：G6的29页、3个手写数学页面和6个公式输入均execution PASS；5个扩展输入故障负例按预期5 FAIL、0模型调用，故障验证PASS。外层任务265.431秒、状态PASS；这些是执行/故障证据，不能改称质量通过。Mini `cancel-r2` 原取消predicate为UNAVAILABLE：观察到请求active，队列排空PASS，没有abort计数增量；原outer exit 2保留。正式66 paired及两次E0均终态、主sequence FAIL，新增测试已停止；DSpark为`NOT_ADMITTED_QUALITY_GATE`，尚未执行GPU加速。

历史阶段记录（同日较早）：Ovis的300区域、9控制相关输入及48扰动已完成；Mini固定源码构建`install-mini-r3` PASS（7861.152秒），依赖检查通过。下列r1/v2结果是保留的历史诊断，不能替代新批。

- 独立任务根：`/data/ocr/dual-ocr-20261028`。原CPU OCR容器保持运行，历史服务配置未修改。
- 两主模型完整ModelScope下载、逐文件SHA256校验通过；文件与原方案锁一致。
- Ovis原生环境已安装：Python3.12.3、vLLM0.22.1、Torch2.11.0+cu130、Transformers4.57.6。完整freeze、安装状态与耗时在29的`evidence/`。
- 历史部署：Ovis以BF16/16K/0.65/maxseq4/CPU8核/RAM32GiB加载，宿主仅127.0.0.1:18500。容器`ocr29-ovis-20261029`，基础镜像ID`sha256:09093e7be732a886ab2c8609e9b80f62e0a843e5833456f89b35a56a39cc168a`。
- Ovis真实开发拍摄页：多模态输入8686 tokens，输出687 tokens/1189字符，finish_reason=stop，tokenize与usage一致；这是接口验证，未作文字正确率验收。
- Ovis模型列表、强制length截断记失败、未知模型/超上下文4xx检查通过。取消原始predicate仍UNAVAILABLE：锁定vLLM正常客户端取消不递增abort计数；源码与实测counter共同证明强制7186-token请求在1996生成token后终止，未达到stop/length，随后稳定idle。依据与限制保留在execution/reports/ovis-cancellation-source-evidence.json。
- 初始采样显存约15.2–16.3GiB；C0后续累计5388条有效采样的NVML峰值17910MiB（约17.5GiB/卡总量73%）。0.65是引擎配置，不是NVML总占用硬上限；该历史采样时尚无两模型正式性能结论，最终结论见本页最终报告入口。首进程engine初始化226.60秒包含JIT/profile，不是每页延迟。
- 历史构建阶段（2026-10-29较早）：Mini前两次因Git/CMake远程依赖获取失败；失败日志保留。固定源码及10份CMake依赖由本机原生Git获取、校验并上传，随后在官方本地依赖覆盖变量下完成构建。主架构配置为8.9；FlashAttention官方构建还生成sm80兼容内核，不能将全部编译命令称为只生成sm89。CPU布局检测已实际成功：22个区域。
- Ovis固定420输入全量完成：416解析成功、4失败，640次模型调用，批次2040.839秒。4失败均为表格内图片被v1适配器拒绝；原始响应与失败保留，v2定向4/4成功，额外17次调用，21.527秒；这是定向修复证据，不把原始420失败或批次时长覆盖为成功。
- Ovis另完成300个R0区域（290文本、6公式/图选项、2章、2表）、8控制页+1图表页/区域。3损坏/加密故障文件全部被拒绝；故障拒绝不是质量失败分母。文字批次初次因文档不连续在模型调用前被拒，稳定按文档归组后仅重跑该组，290/290解析成功。
- Ovis全量输出抽取的53个独立公式均经实际MathJax3.2.2渲染成功；不证明原图公式全部检出或语义正确。该批是cold_adapter且有编译干扰，不具备主性能比较资格，也不是质量通过率。

## 输入与工具

93个冻结原候选均可定位且原SHA匹配。Word首次转换出现严重中文缺字，28份失败转换已隔离。修复任务私有字体后重转，当前固定输入420单元：Word306页、原PDF49页、拍摄PDF5页、图像60份；4作文完整原图。代表数学/化学/物理已实际渲染检查，但Word全量保真和人工GT仍未完成。

共同执行器、两适配器、逐页/文档导出、评分/报表与专项入口已实现。根代理本地整合168项相关测试通过（17.980秒）；随后开发页非空门禁10项定向测试通过；29 Ovis环境此前81项通过；包含真实HTTP慢头、实际PDF渲染与适配器到评分器集成，均不等于真实模型质量通过。

正式人工GT为0。新增300个唯一像素R0区域、9个合成控制和40个性能页（39源文档、25源家族），均独立于模型成绩选择；合成集不替代真实手写/拍摄/盖章。用户随后明确指定由当前助手验收打分，现按[AI裁判规则](ai-judge-plan.md)建立独立视觉参考与盲评。已核对范围可作AI质量验收和对应字符评分，仍显示参考来源与覆盖率；未核对部分不虚标通过。私有原图、转录和模型全文不进入仓库。

## 继续执行

双方S0标准解码全量诊断已完成，保留Mini取消UNAVAILABLE结论，停止所有新增测试，已完成已有质量验收和已终态正式性能/耐久归档的离线汇总，其他准备专项保留未执行；保留全部原失败。正式G4按平衡配对块、唯一像素输入与同worker开发预热执行。DSpark继续受原方案门槛约束，未满足双方标准和质量门时不提前宣称可采用。

## 跨页专项当前边界

O1-16K-PRED、image=2、原max_pixels=8294400：两相邻对输入18605/18894 tokens，均FAIL_BUDGET；三页递归UNSUPPORTED。独立源图核验确认这两对都是无续表X03负例；真实X01在PDF-003-p004/p005，后续单独加入。LOWPIX使用每图4147200像素，单独profile，不覆盖原16K失败或标准C0。

## 实际预处理更正

先前Ovis嵌套images_kwargs未控制resize。CPU实际processor同图grid：nested为[1,220,156]/8580视觉token；顶层max_pixels8294400为[1,214,150]/8025；顶层4147200为[1,150,106]/3975。配置对象size字段仍显示默认值，不能拿它代替实际输出网格。此前420及LOWPIX-r1标为无效预处理预算诊断；原记录不删除，顶层参数生效后的新标准批次已完成，见本文当前状态。证据29:evidence/ovis-image-processor-kwargs-proof.json。

正确LOWPIX-r2：真实续表PDF003p4/p5输入9736 tokens，因多表绑定保护返回UNSUPPORTED；两个无续表负例输入9395/9684，正确返回无需合并并通过资源导出；3页递归仍UNSUPPORTED。该专项不是C0或原像素预算通过。

本地集成130项相关测试PASS（12.519秒）；新增资料准备与脚本另有定向验证。source-only全页审阅105页/210tile已完成：原PDF49页+Word56页，49页提供可用线性全文参考候选，复杂页明确保留公式/图内字/阅读序缺口，root仍需验收。

## G6新增公开续表源样本

私有补充集已从公开GitHub测试fixture选定5份PDF、29物理页、5源家族；独立源图检查确认11个真续表边界、10个不应合并边界和3条不同逻辑表链（5/5/4页）。10个negative中4个是table-table边界，6个是一侧非表，分层报告。1条positive链是Arabic RTL，只评价续表结构身份，不能算中文准确率。原420主清单及性能选择未变。历史源图核验阶段尚未执行GPU专项；其后两模型均完成这29页的Stage1解析。Ovis默认16K的21对全部FAIL_BUDGET、3链UNSUPPORTED；LOWPIX另profile完成17/21对正确结果（正覆盖7/11，另4正例预算失败），3链仍UNSUPPORTED。实际34份派生MD已完成hash/content及非表保留readback（31非空、3预期空白）；详见[补充结果](execution/reports/supplement-ai-results.md)与[导出覆盖证据](execution/reports/coverage-matrix.md#g6真实导出文件补证)。这些执行/导出证据不等于全链文字CER/TEDS或完整质量门通过，原失败保留。PDF第三方许可未单独声明，保留源仓库/commit和许可边界，仅私有测试，不将repo MIT解释为PDF重许可。

## 输入与原子写出层补充验证

真实PDF大画布与PNG伪装PDF的输入边界已修复：PDF在300DPI分配前复用Pillow现有像素error阈值，并核实际PDF格式；正常旋转/crop RGB保持一致。32项executor测试通过；Astra max另以4个真实PDF fixture独立复验。历史执行安排（2026-10-29较早）：当时活跃Mini标准批次保持原已加载代码，新增guard等待该批结束后部署再冻结。最新状态：该S0批次已完成，v8包已部署并确认core f2版本；5个扩展输入故障负例已按预期拒绝、0模型调用，验证PASS。

F10已在29真实独占CPU-only、network-none容器执行：只读bind与64KiB tmpfs分别触发写拒绝/ENOSPC，原完整JSON字节与hash不变，最终JSON仍可解析；job iofault-r1 PASS/0，0.074秒。故障仅作用于新建任务夹与临时文件系统，没有填宿主盘；这是共同atomic_json层证明，不是GPU质量或整页HTTP验收。详细errno与空间证据在29私有evidence/f10-atomic-io-r1.json。

## 正式阶段前部署与guard修复

2026-10-29，真实Docker前置检查因 `docker top ... -eo args` 缺PID列而报错，原guard在stop前拒绝继续。候选检查改为 `pid,args`，构建检查改为 `pid,comm` 并保留编译进程识别。PID补丁后，root以 `PYTHONPATH=execution` 运行campaign全21项测试PASS（0.450秒）；实现owner此前另有4项定向测试PASS，二者不混记。29真实 `docker top ... -eo pid,args` 与新guard均已readback PASS，不只是本地mock。

v8 tar已实际部署，SHA256 `e7d228530e62fe8f006c5bd4eea1f55c3de25ae3ce2ecadd87ad271faa8fa8cd`；已确认远端core完整SHA `f2b707796feabd80c7f5a446a8f519b29a426b7859da7a68a6c3f1eac67d3e89`。这证明包部署与前置guard可执行，不证明后续66 trials、E0或DSpark通过。

DSpark仅完成下载与权重验证，46.907秒、PASS；按README第11节质量门尚未PASS，阶段状态`NOT_ADMITTED_QUALITY_GATE`。脚本准备不代表已获准进入GPU加速阶段，不与标准解码性能混比。

## v11与补充验证更新

root已实际部署v11，`source-v11-install.json` 为PASS；Mini适配器SHA256 `135321e34ca69592c2d43e778f3b0811f713b892b552516b598065de92280933`。mathadapter v2另以5份保留原始响应重放、19片段MathJax渲染19/19验证序列化，0次新模型调用；不改写旧输出或主187/原273分数，也不证明新推理质量。

Mermaid已完成真实Chrome渲染8/9，与parser同一份未选中额外图语法失败；5份选中流程源拓扑已核，其他4份额外图没有语义验收结论。两项细节见[补充AI结果](execution/reports/supplement-ai-results.md)。

root在29完成ops-r2：两模型实际断网冷启动、进程停止、重启恢复与标准容器恢复后的dev4均PASS，运行终态证据为`evidence/ops-r2/state.json`。ops-r1的Env顺序false fail保留；ops-r3后续重复恢复结果见下；F06 r2 HTTP suite已有29实际21 tests、9 scenarios/3轮synthetic、无GPU的PASS证据，与ops恢复分开，不扩称任务包装持久化验收。正式66 paired及两次E0均有终态、主sequence FAIL，终态不等于全项通过；运维此分项通过不等于完整运营、性能或耐久验收通过。

## 正式序列启动与补充状态

ops-r3-repeats已由root实际readback PASS：4次追加故障事件加ops-r2原2次，合计每模型3次fault→restart→dev4恢复，Mini使用v11 mathadapter v2。ops-r3收尾时GPU idle、旧CPU服务healthy、旧summary hash不变；这是随后正式序列启动之前的状态，不代表正式运行期间GPU空闲。

正式66 paired及两次E0已全终态，master sequence FAIL（66中65 PASS/1 FAIL；Mini E0 PASS、Ovis E0 FAIL），全部新增测试按用户要求停止，仅离线汇总。 DSpark仍为NOT_ADMITTED_QUALITY_GATE。

样式20目标既有产物诊断显示Mini文字19/20、样式exact1/20；Ovis文字20/20、样式exact11/20。UNAVAILABLE字段不代表产品全无样式，source-first范围及2项真实source addendum、失败变体见[补充结果](execution/reports/supplement-ai-results.md)，无新GPU推理、无render PASS、主187不变。扩展43输入与24基页164扰动均source-approved但未GPU；robust仅15/24有全文参考。

Astra max终review核对5份冻结证书与261输入的hash通过；另发现scorer宏CER家族聚合P2。Astra已review通过的补丁现已整合到Mac本地repo的scoring.py，并新增test_scoring_macro.py；源码SHA256 `a5364f96df8a96113212c34eee2bd046da0d187b3e44725856daa13b12d268f1`。root在实际repo execution目录运行 `python -m unittest discover -s tests -p 'test_scoring*.py' -v`，31项PASS、0.698秒、exit0。本地评分工具已修复；29仍保持冻结v11评分源码 `42153baccdc43a017d0d937e36b455073cd3277cfba6a149272950efe017eed2`，用户要求停止后不再部署到29，不能称远端已修或全部关闭。正式冻结22个文件（16份源码、6份清单）均在远端任务目录，Mac独立副本的整合不会改变该实验；原GT与冻结结果没有覆盖，micro CER不变。该缺陷是CER聚合实现问题，不把既有AI评分的family macro重新解释成字符CER。

新增pure6和chart10源已由root批准但未GPU；P05 same/unique30仅完成selection批准，少量补覆盖未执行并按用户要求停止，不修改正式66 trials。
