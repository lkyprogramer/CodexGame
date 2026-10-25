# 2026-10-21 分层范围与Target sampling合同修订验证

以下首节保留先前分层修订的验证记录；完成Baseline后的新增评估验证见末节。

本次只写当前文档包；previous-v2/inputs原件字节不变。授权范围为方案/采集工具与B29 baseline，本文档worker未修改scripts/引擎或执行远端。实际runner切换/请求进度由ROOT run证据记录。

本次新增plans/06测量预算、design/11 delta-q与Target sampling合同、H1-T07八组硬断言；不新增phase，不另造sampler。初始278请求、工程8+2、阶段≤240、发布26任务variant只是已采纳安排，不是性能/GPU资格或完成证明。旧672未测保持未资格，旧manifest/raw/损坏记录保留。

已执行`python3 /tmp/check_ninfer_docs.py`：286份Markdown、本地链接检查、唯一registry解析及三个scope无缺依赖/无环、264个唯一断言、53个H任务的interface/步骤/断言与矩阵镜像一致；192份previous-v2/inputs历史payload对原快照SHA-256全部不变。完整104节点=88task+16gate；e1_w6为68=57+11；e1_w8为75=63+12。

已按当前文件重建INDEX与MANIFEST；清单覆盖除自身外285份Markdown，逐文件字节数/SHA-256核对。检查范围仅文档结构与合同一致性；未运行NInfer构建/GPU/p95资格或远端操作，未运行与文档变更无关的全仓测试。所有优化/集成task/gate仍PENDING、P6 qualified commit仍null，新组合sampling默认OFF；现有seam/source阅读不当作完整B29或B6资格。

## 完成Baseline后的只读评估验证

新增research/04与plans/07；同步design/11、plans/06、README/INDEX/CHANGELOG。离线执行`python3 output/ninfer-baseline-29-20261020/assessment-20261021/analyze.py`，从冻结reference/raw/summary复算Core/Pi耗时、容量截停、条件加速和48/1680运行预算。输出带输入SHA，脚本没有HTTP或模型入口。独立只读复核确认20.7742小时正式请求外推、64⊆240预算及72条Core容量终止分布。

本次检查包括：新/改文档的本地链接、全部288份MD目录/287份清单、历史payload哈希、原69项Baseline交付哈希、派生输入SHA、输出数字与空白差异。结果记录在包外`output/ninfer-baseline-29-20261020/assessment-20261021/validation.json`。历史报告/评分不改，RE003-v1 FAIL未改PASS；Gson两selector未知、97的SSE/server终止语义与KV增长计数分别保留。

本轮未运行模型、grader、NInfer构建、CPU/GPU sampling资格或全仓产品检查，未执行SSH/现网操作、未重启监控。分布/状态/性能资格仍未取得；文档和离线算术检查不能当这些测试PASS。本次没有重新封包ZIP。
