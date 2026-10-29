# OCR 公开样本补充核查

2026-10-28。仅查源、下载六张小候选图和目视核实，未运行 OCR。镜像与数据部署均未执行。原始样本和镜像注释保存在权限0700的临时目录，未写入仓库。

## 可用证据与方案决策

1. **真实英文手写有具体候选**。官方 [GoodNotes/GNHK-dataset](https://github.com/GoodNotes/GNHK-dataset/blob/5be3842f4231d2b469198600c2b9b0a3745e4d34/README.md)明确整个数据集按 CC-BY-4.0 免费下载，类型为非受控相机拍摄英文手写。官方旧下载页现在跳转产品首页，GitHub本身只有README/许可/论文，不能写官方完整集已可直接下载。本次通过[第三方HF镜像](https://huggingface.co/datasets/bhavya777/GNHK-dataset)公开 rows API 取得前三张原尺寸图片和镜像文本注释，三张均已实际看图，确为纸面英文手写相片：稀疏编号清单、连笔笔记与印刷背景叠加、低对比度整页笔记。合计约1.16MB。镜像的原始文件ID/作者ID/词框不齐，转写有特殊占位token，**不可直接作已审GT**；正式计分前确认镜像来源并双人复核。没有作者ID时不把三页推断成三位作者。该数据补英文，不能替代中文学生长答。
2. **中文整页手写的SCUT-HCCDoc不按免费开放集入选**。官方 [HCIILAB仓库](https://github.com/HCIILAB/SCUT-HCCDoc_Dataset_Release)确有学生笔记/试卷等真实相机中文手写，GitHub也有展示样本，但完整集受非商业研究协议、机构签章申请和访问审核约束，且说明2022年后公司免费申请不再接受。本次未下载受限样本、未申请、未联系作者。它仅保留为后续来源候选，不能因图在GitHub上就视为企业可自由使用集。
3. **拍摄数据已有三个补充候选，现不需继续拉整库**。从官方 [DewarpNet](https://github.com/cvlab-stonybrook/DewarpNet/tree/5f9e216535f048d98ca44bbfb5f6ea55f8cdfe13/eval/inp)取得两张DocUNet真实拍摄示例，从官方 [DocTr](https://github.com/fh2019ustc/DocTr/tree/044648919b6b28f2cb1b288db6d8fd97749db537/distorted)取得一张：弯曲说明书、折叠彩色杂志、含表格/图表/公式的折叠双栏论文。均已看图，约6.27MB。真实DocUNet benchmark与合成Doc3D训练集必须区分；[官方DocUNet页](https://www3.cs.stonybrook.edu/~cvl/docunet.html)明确benchmark含原始相片、居中裁剪、平板扫描参照。DewarpNet `tess_gt.json`提供25文档OCR参照，其中document1有对应文本，但不是所有下载图都有GT，且要按实际可见裁剪复核。代码MIT不等于已证明底层文档图像无额外条款，DocTr README还明确商业用途联系作者。鉴于本地已找到真实拍摄文档，这些只作为候选，不必在条款/GT未确定时纳入正式评分。
4. **本地1597章图上游可确认，mask不能当文字GT**。[DocDiff官方README](https://github.com/Royalvice/DocDiff/blob/f422a3af10657eeabeca90f2e862d88c72725845/README.md#印章数据集)写明1597个中文红章及二值mask，大部分原图来自ICDAR2023 ReST，少部分内部图；章是从原文档提取，背景图不提供，另有marker代码生成合成盖章页。它是“真实来源章crop”，不是1597份真实盖章整页，也没有对应OCR转写GT。用户本地已存在，未重复下载。[ReST官方论文](https://arxiv.org/abs/2304.11966)称10000真实印章并标文字polygon和内容；官网本次直接获取502，下载/条款未核实。DocDiff MIT代码许可不自动替上游数据条款。现有本地govSeal整页与章crop分别测，合成叠章仍标synthetic。
5. [WarpDoc官方页](https://sg-vilab.github.io/event/warpdoc/)确认1020真实相机文档，下载是GoogleDrive整包，当前不需要拉取；其数字参照用于恢复图像质量，不自动等于逐字OCR GT。保留为备用来源即可。

## 本次实际取得

- `/private/tmp/minicpm-ocr-public-source-manifest-20261028.json`：六张候选的来源commit/path、SHA-256、字节数、尺寸、场景、许可/GT状态；附上游来源决策。
- `/private/tmp/minicpm-ocr-public-samples-20261028/`：六张原图，三份镜像注释，DewarpNet文本参照。总图像7,421,892字节。
- 所有六图已目视核查，无OCR结果、质量成绩或样本量通过结论。

## 执行计划应保留的缺口

三张英文手写图不足以达到30页/10名已知作者；没有作者元数据不能靠页数补成作者数。中文姓名crop只能证明姓名短词场景，不能证明中文长答/涂改/整页手写。公开benchmark可能进入模型预训练，成绩宜称固定回归效果，不作严格未见分布泛化保证。优先完成本地语料与真实govSeal整页的人工GT，再按需要扩展英文手写；用户后续提供的本地作文目录已确认4份长段中文手写输入，详见主方案；它们解决“无长文样本”，但作者元数据、独立物理页数、人工GT和更大统计规模仍需补齐。
