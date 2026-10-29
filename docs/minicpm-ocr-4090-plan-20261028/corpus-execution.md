# 实际语料准备结果

2026-10-29。已执行匿名打包、冻结源文件SHA校验、Word转换和清单核对。未执行本文件对应的模型OCR或人工金标验收。

私有包位于 `/private/tmp/ocr-corpus-execution-20261028`。其中 `inputs/`、`manifest.json`、`region-manifest.json`、`annotations-draft/`、`region-gt-draft.json` 可用于29的本次封闭测试；`private-source-map.json` 保留本地，不需传到29或仓库。整个目录权限按umask077创建，文件0600；原件未改。

| 内容 | 实际结果 |
|---|---|
| 冻结候选 | 93个全部找到，全部匹配既有SHA256，无完全重复源文件 |
| Word | 28 DOCX通过现有LibreOfficeDev26.8转换为230个PDF页面；字体/公式/分页视觉QA待验，只作诊断输入 |
| 三份原PDF | 49页全部保留；仍用原PDF逐页D0渲染，不预先把文字层返回模型 |
| 本地增补 | 56候选形成59输入单元；其中2照片PDF共5页，作文4张保留完整1550×6664原图 |
| 公开增补 | 原临时文件已丢失，按冻结来源重新获取6图，逐文件SHA仍匹配；条款/转录待复核 |
| 端到端输入总数 | 344单元：284个PDF页和60张图像，75个保守源家族 |
| 区域诊断 | ICDAR2015原10个test图标签获得37个非###文字crop，单独R0清单，不增加原件/作者数量 |
| 私有包大小 | 64,523,429字节（最后一次summary统计；后续运行产物不在此数） |
| 完整人工GT | 0；正式good-page/s与质量胜负仍不可判定 |

`manifest.json` 的path相对于包根目录。图像expected_pixel_hash为EXIF归一后RGB.tobytes的SHA256。DOCX同一学科答案/新旧试卷保持同source_family_id和同split，不按页随机拆分；近重复仍只按保守家族归并，75不是独立作者/物理文档族的已验证统计。姓名crop、章crop、长竖作文有unit_kind，不冒充真实A4页。

`annotations-draft/` 的PDF文字层仅供后续人工审阅；公开镜像转录、ICDAR原标签保留其来源身份。`region-gt-draft.json` 使用评分器schema，但GT_complete_for_required_tasks=false、provenance.kind=draft。矩形crop可能含相邻文字，不把数据集标签未经复核当本轮完整crop金标。全部文字与结构GT需要独立审阅；AI看图复核也不等于人工双盲标注。

执行命令：

```bash
python3 docs/minicpm-ocr-4090-plan-20261028/execution/prepare_corpus.py --out /private/tmp/ocr-corpus-execution-20261028 --convert-word
python3 -m py_compile docs/minicpm-ocr-4090-plan-20261028/execution/prepare_corpus.py
```

实际验证通过：344输入路径存在、三PDF49页、作文4张、93源hash一致、家族不跨split、37区域路径存在、Python语法检查。两次完整打包得到相同原件数和页数；第二次复用已生成PDF，避免重复转换。未做Word视觉保真、全量人工GT、完整结构/关键字段/跨页关系标注。公开条款、中文长手写GT、>=30真实手写页/10已知作者、真实照片页>=10及专项跨页原始链仍是GAP。

## 补充：盲审与实际执行入口

已补`gt-draft.json`：344输入完整schema，284页PDF文字层草稿，其余空模板；所有GT_complete_for_required_tasks=false，provenance.kind=draft。没有将人工金标缺口改为通过。

- `development-manifest.json`：4个既有development家族的代表输入，保留冻结split，用于实施调试；不宣称覆盖全部场景。
- `smoke-manifest.json`：16输入固定参数诊断，含英文双栏/表格、中文技术/接口、数学答案页、姓名、5类增补代表及4作文全图。保留原split，不能用其中evaluation_diagnostic反馈逐样本调参；固定配置后才执行这些页。数学Word页的公式可见性仍受转换QA门约束。
- `blind-review/`：4份作文原图、28张重叠导航区图和4份空白标注模板，使用WRITING匿名编号；不含模型结果。重叠区域用于定位，不能重复抄写计分；审阅人需在原图上核对全文、标点、涂改、不可读字和空格区域。`essay-review-key-private.json`留本地。
- `scene-coverage-map.json`：Q01–Q22候选页映射、输入/原件计数、NOT_RUN及GAP状态。来源tag只用于寻找候选，不能作为场景实测PASS；跨页对、化学/物理结构、具体样式区域仍需标注验证。Q14/Q15尚无冻结负例/方向派生。

新增包体积约93.1MB，包含重复展示原图和28导航图；未增加原始质量样本数。检查确认16个诊断输入、4个开发输入、28展示区、全部GT标为待审，且冻结家族split未改。

## 转换缺陷修复（2026-10-29，优先于上述首轮计数）

root实际渲染发现首轮Word页面大量中文不可见、数学向量方框；因此首轮230页转换证据全部判为`REJECT_RENDER_QA`，不得用于质量或吞吐正式比较。此前“转换成功”仅证明LO返回PDF，不证明像素正确。这一问题已修正：使用任务私有FONTCONFIG_FILE，提供本机Songti、ArialUnicode、STIX及已安装Word的DFonts字体目录可见性，不改系统字体或全局LO配置，不将字体复制到仓库或29。原始DOCX不变。

首次只加中文字体恢复中文但数学向量仍为方框；加入本机Word字体后，数学箭头、中文、化学反应上下标/箭头、物理核反应/图例可见。实际查看数学2、化学2、物理2首页。任务证据在 `/private/tmp/ocr-word-font-repair-20261029/test/{math2,chemistry,physics}.png`；私有font-manifest记录267个可见字体的路径/hash。初轮错误PDF保留在包内 `rejected-word-render-fonts-v1/`，此目录只作失败证据，**不可作为输入**。

修复命令：

```bash
python3 docs/minicpm-ocr-4090-plan-20261028/execution/prepare_corpus.py --out /private/tmp/ocr-corpus-execution-20261028 --convert-word --rerender-word --word-fontconfig /private/tmp/ocr-word-font-repair-20261029/fonts.conf
```

三代表恢复可见性不代表28份全量保真通过。字体替代、旧Equation对象与分页仍需逐份视觉验收，修复后Word保持`CONVERTED_VISUAL_FONT_FORMULA_QA_PENDING`与非正式诊断身份。旧渲染分页不可复用，新manifest、PDFhash和文字层草稿为当前真实版本；未重新审阅的Word不进正式质量分母。

修复后实际重建：28Word共306页，端到端清单420输入（360PDF页+60图），93源SHA仍一致。`word-render-v2-lock.json`保存28个新PDFhash。所有GT/开发/smoke页身份与新manifest对账通过；旧Word230页不可复用。首轮包大小已经过时，失败证据/重建文件使包增大。

## 单元类型校正

已逐项显式标注unit_kind并同步主清单、开发、smoke、GT草稿与R0。420主输入为374个page、4个long_image、32个crop（30姓名+2章）、10个scene_image（ICDAR街景）；R0另37个crop不计新增来源。PDF逻辑页和纸面整图使用page，仅表示输入单元，不能推导真实A4物理页；4作文边界未知，固定为long_image。GNHK纸面手写与DocUNet完整纸面照片为page输入，作者身份未知，不增加已验证作者数。`unit-coverage.json`给出可上传匿名计数与语义。所有清单和GT unit_kind一致性、28Word像素来源PDFhash未变检查通过。本次仅修元数据，不改开发4页内容或任何原件。

## 独立R0区域集300

`execution/prepare_region_suite.py`实际生成 `/private/tmp/ocr-ai-judge-20261029/r0-300`，300个唯一crop、输入PNG共11,293,371字节：116作文行、30姓名、2章、37ICDAR、6公式/图表选项ROI、2表、107原PDF文字行。所有unit_kind=crop；51保守source_family，93原case（包含原PDF逻辑页身份），不增加作者/原件数。6公式ROI沿独立已审结构参考边界，其中物理速度图与选项是图文结构诊断，不冒称单条LaTeX公式。

未读取两模型OCR结果、未访问29。4作文approx行范围对齐原网格水平线；001-L35水平线较弱，实际查看该段后显式定位。实际看过26张全量联系图；PDF原字体行bbox带入邻行碎笔后进行了像素边界收紧，再看8张印刷联系图。原手写越格/重描墨迹保留，不能涂改图像清除。所有图片byte/pixel hash、bbox回映射及唯一性校验通过。

49原PDF页不都有普通正文：接口封面、目录或代码密集页达不到普通行条件时保留GAP，缺额按冻结候选序列均匀补在其他原页，仍为107个不同普通/技术文本行，未重复samecrop凑数。`gaps.json`记录5个页级不足，不把它们假报全覆盖。

`references-draft.json`保留独立AI参考、原存疑行、root已决字段及原图来源，非human_verified；已决占位按root裁决替换，剩余literal〔候选〕标记为0。印刷文字层仅为draft参考，NFKC只规范参考ligature，不改源图像。300记录仍需root最终批准，正式人工GT未建立。`freeze-sha256.json`锁定清单/参考/摘要/缺口。
