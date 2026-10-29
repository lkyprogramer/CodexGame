# 29 双模型执行记录

> 用户已要求停止新增测试，现仅基于已有归档作最终对比；不再运行模型、预解码、单测或部署。2026-10-29 14:09:35 CST实际readback：主sequence为FAIL，9 steps均终态、steps_not_run=0；66 paired为65 PASS、1 FAIL。Mini E0为PASS，Ovis E0为FAIL，两者均已排空。 14:09:50已确认源码hash未变、两模型容器停止、GPU无compute app、旧CPU OCR同实例healthy。完整终态与未测边界见[标准执行结果](execution/reports/observed-standard-results.md).

2026-10-28。用户已明确授权按统一方案在29部署、验证与对比。本文记录执行进度；设计合同与实际结果分别保存，未测项不变成通过。

## 目标与顺序

1. 重新检查29、记录现有服务与GPU，创建本任务独立目录。
2. 固定模型及运行栈并校验下载，建立CPU SDK及两个隔离GPU环境。
3. 实现并验证共同逐页执行器、预算/原始响应留存、两个模型适配器、资料准备及严格评分。
4. 两模型依次标准解码，执行开发冒烟、完整页面/正确区域、故障与负载测试，冻结输入并记录参考来源及未核对范围。
5. 通过双方标准门后才执行DSpark；原始失败保留，未满足门槛则明确阻塞原因。
6. 汇总真实质量、效率、速度、资源、能力与缺口，复核后归还GPU。

## 分工与共享接口

- root：29部署、环境/模型安装、集成和串行GPU实测；独占远程变更。
- executor：`execution/ocrbench/{__init__,core,client,cli}.py`及对应测试，统一调度与HTTP预算。
- mini：`execution/ocrbench/mini.py`及对应测试，CPU布局/区域识别/完整导出。
- ovis：`execution/ocrbench/ovis.py`及对应测试，结构化/图内字/模式/专项输出。
- corpus：`execution/prepare_corpus.py`及资料清单；私有图像和映射不进Git。
- scorer：`execution/ocrbench/scoring.py`及对应测试，page-good-v1与明确UNSCORED。

共同Python3.12、尽量标准库；Pillow/PyMuPDF供输入处理，requests供HTTP。适配器接口 `process_page(image_path: Path, context: PageContext) -> dict`；结果含 ordered_blocks、text、raw_text、status、errors、requests。PageContext提供 `call(image_paths, prompt, task_limit, task_name)`、`emit(event, **fields)`、`remaining_seconds()`、`output_dir`、`page_id`；call保存每次请求/响应，使用服务真实/tokenize输入计数；如版本不支持多模态计数则门失败，禁止假计数。call返回 `content, finish_reason, usage, request_id, status, error`。全局区域并发最多4，外层逐页接纳初始1；可配置1/2/4。模块之间由root整合，不覆盖他人文件。

## 边界和验证

- 原有CPU OCR和历史Qwen/ninfer/Strata服务配置不改，模型轮流占卡，不升级宿主CUDA/驱动。
- 原始私有资料只放本地临时目录和29专用任务目录；仓库仅匿名元数据、代码和摘要。
- 模块定向测试、真实/tokenize与图像请求、输入像素/产物对账、模型/软件hash、资源/失败留存构成证据。
- 用户已授权root AI担任裁判：以原图先验转录与独立验收建立明确来源的AI参考，可给AI裁判分数、通过/拒绝结论及限定材料范围的模型比较，不因缺人工金标阻塞已授权验收。原图不可确定的内容保留UNKNOWN；AI参考不是人工gold，不以PDF文字层或候选模型自评替代原图核验。严格结构GT或必需指标不足的good-unit/s等仍保留UNSCORED，不能由AI均分硬换算。具体口径见[AI裁判规则](ai-judge-plan.md)及[已交付质量结果](execution/reports/ai-quality-results.md)。
- 不提交/推送Git，不创建PR。部署及测试属于本次明确授权。

## 当前状态

初始检查记录为GPU1MiB、CPU OCR healthy、磁盘161GiB，不代表当前空闲状态。2026-10-29最新快照：两模型S0标准解码全量诊断均已完成，Ovis 420/420，Mini 419/420；Mini的GOV p003 block-0016发生真实输出截断，失败保留。Mini补充输入执行及扩展输入故障验证完成；cancel-r2终态原predicate为UNAVAILABLE（observed active、queue drain PASS、无abort增量，原outer exit2保留）。正式66 paired及两次E0已全终态，master sequence FAIL（66中65 PASS/1 FAIL；Mini E0 PASS、Ovis E0 FAIL），全部新增测试按用户要求停止，仅离线汇总。 DSpark仍为NOT_ADMITTED_QUALITY_GATE。已执行事实与边界见[执行记录](execution-report.md)及[标准解码结果快照](execution/reports/observed-standard-results.md)。

## E0耐久测试

`execution/deploy/run_endurance.py`使用单次持久worker池，P0三份完整PDF共49图、开发预热4图、页接纳上限4/区域全局4。在预热完成后开启3600秒接纳窗，截止停止新接纳，再按原300/1800/120秒deadline排空已接纳前缀并组装；候选池未接纳项另存，不计失败或提交。池提前耗尽、完成不足300、已接纳执行失败或未排空均不通过。重复不增加独立质量样本数，E0始终不具备固定主性能资格。入口已完成独立代码复验；实际已结束：Mini437/437 PASS，Ovis1523终态中1521 PASS/2 FAIL，均排空；主序列FAIL，资源稳定性与能耗待本次已有归档离线分析，不再新增测试。
