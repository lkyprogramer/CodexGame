# AI测试与证据契约

## Task与Phase职责

Task只跑本任务最小RED/GREEN和定向回归，不要求每个worker都跑长上下文全套。每Phase由Integrator将任务合到同一commit，Reviewer审查组合diff，再跑本阶段受影响数值/状态/功能/GPU硬合同与plans/06相关小集（≤240相关A/B请求）；H5/H8才集中正式发布业务/尾延迟资格，不逐阶段重跑全部672。一个GPU队列串行安排硬件测试；CPU开发可并行。缺subagent时可串行实施，但不能冒充独立review。

每个现行H任务至少3条具名断言；新增H1-T07有8条sampling断言，完整目录在 [断言矩阵](../plans/03-acceptance-matrix.md)。测试目标均为拟建，先注册CMake/实际构建再运行；测试文件存在不表示已执行。最小assertion应覆盖正常、负例、状态/资源边界，不只跑--help。

## 证据schema（Markdown记录中的JSON围栏）

```json
{
  "schema": "ninfer.hybrid.gate.v1",
  "phase": "H1",
  "source_commit": "actual-commit-required",
  "build_fingerprint": "actual-build-required",
  "target_fingerprint": "actual-target-required",
  "configuration_hash": "actual-policy-required",
  "assertions": [{"id":"H1-T01-A1","status":"NOT_RUN","evidence":[]}],
  "review": {"reviewer":"unassigned","commit":"unassigned","verdict":"NOT_RUN"},
  "research_status":"NOT_RUN",
  "gpu_status":"NOT_RUN",
  "promotion_status":"OFF"
}
```

占位字符串只出现在模板；运行门禁对这些值必须拒绝。证据路径必须存在、hash对应，声明包含GPU时需gpu_uuid/driver/cuda及实际longprompt计数。`PASS`、`FAIL`、`SKIPPED`、`BLOCKED`、`NOT_RUN`分开；CTest返回0但必测skip77，不算GPU通过。

## 恢复/预算矩阵

强制覆盖：0/部分/全接受+bonus；accepted≠committed；stop/EOS/budget1/2/K/K+1；roundfault/cancel；lane复用和重复epoch；L1/L2/L3热Target而aux cold；历史工具输出改写；tokenizer/adapter改变；同W不同B与异W混batch；NaN scratch/guard越界；CUDAGraph capture/replay及未命中fallback；负的scale/invalidID/byte-fragment token；copy高命中到低命中转折；late DMA。

## 已有行为与RED

新增测试先在未实现版本看到预期FAIL。若继承行为已经通过，记录BASE_PASS并用原缺陷/边界/受控mutation证明测试有效；不为制造RED破坏生产。基线审计类任务不要求“故意审计失败”，但必须测试证据缺失、假SHA、缺bucket、skip被误判的负例。

## 阶段分支和停止

所有phase串行：P6→H0→…→H8。内部依赖见 [DAG](../plans/02-task-registry.md)。默认每phase的所有任务都要完成相应验证。没有收益的优化可关闭/移除实现并由review签署NO_ADOPTION；不能把缺测试或数值失败写成PASS。

H3-W8不合格时H4-W16不能执行资格。执行者可按[发布范围契约](10-release-scope.md)请求关闭宽块范围：使用预定义的`e1_w6`或`e1_w8`派生DAG，明确替换H5-T01的前置为最后真实合格gate。宽块任务仍保留FAIL/BLOCKED/NOT_RUN，不伪造H3/H4-GATE为PASS；取消决定本身也不是GPU资格。H5在派生范围内重新审查同一个发布commit及全部保留路径，方可发布。

H6缺资产时H7仍阻断；不宣称H8完整融合，只能交付H5已合格范围。恢复被关闭的研究前，必须恢复相应依赖和补齐资格。默认完整DAG不做任何隐式跳过。

## 机器消费但不额外带JSON文件

[任务注册表](../plans/02-task-registry.md)有唯一JSON代码围栏，可由Agent在包外解析；不存在独立`.json`附件。执行者可产出本地JSON/JUnit/二进制证据，但它们不是本次MD文档交付物。原V2工具通过support恢复，V3 `tools/bench/check_hybrid_evidence.py`由H0-T06实现，不能在实现之前声称该命令已通过。

## 2026-10-20 baseline与统计纠正（现行规则）

当前 [BASELINE_ONLY](../plans/05-baseline-29-execution.md) 是B29二进制P0测量前置，不等于P0/P6/H0-GATE。P6→H0、H5→H6的完整DAG未拆分，缺原生产资格继续BLOCKED，不隐式绕过。新优化任务全部PENDING；baseline完成也不意味着优化已实现。

样本按plans/06分层：初始278参考+8工程/2repo；阶段≤240相关A/B/至少3block只筛选；H5/H8正式关键case≥10配对/至少5block，p95桶/variant≥100且CI满足，探索不可升级为正式通过。20×3通用下限已撤回。checker必须fail-closed处理未知规则/quantile、空metrics、缺字段、样本不足、重复/缺配对、错hash/schema/commit、required skip/0tests。p95-only且A1/B100的负例应失败；原归档helper不满足此合同。

B29 schema20 adapter不伪造schema24；缺round/tokenID/reasoning分项写null+原因，必需metric缺失阻断相应gate。记录采集、统计、源码重建、数值、资源、生产各自状态，不将COLLECTED当QUALIFIED。Pi固定轨迹与真实闭环、cached/recomputed、logicalV/physicalW独立记录。baseline长任务先验证runner/monitor/heartbeat/checkpoint与恢复，再定时唤醒，禁止用频繁主动poll代替脚本监督。

## B29 runtime补充纠正

现行plans/05已将通用P+O+R说明修正为源码推导O_eff=min(O,C−P+1)、末token不入KV及动态页预留；实际B29仍按生成日志/边界验证，不能从clean源码推断已完成产品资格。核心baseline保持原argv，expected/observed cache分别记录，未达到cold reused=0条件的attempt保留gap，不允许偷偷启no-prefix-reuse或按“第二次”推断warm。count_tokens不提交KV；复杂Pi跨协议转换计数差异不得冒充精确P。

## 2026-10-21授权范围与sampling门

[plans/06](../plans/06-staged-evidence-budget.md)是已采用测量安排，预算不是性能资格；旧672/Pi×5/20×3执行展开不再是默认。原full/e1 feature范围与门禁仍有效；新增H1-T07在同一H1内完成delta-q/最终mixed prefix/processor/residual/bonus/stop/cancel/RNG/legacy fallback具名硬合同，H1-T06依赖它。后续各W/head/backend/aux组合独立复验Target sampling，不能用Target-greedy诊断替代，未资格保持新路径OFF/回原合格sampling。生产Target参数维持原值，greedy只描述提案。

正式checker需按`measurement_scope_id`核对选定expected-cases、stage/release预算和具体claim的metric/bucket/CI，不把278当672全覆盖或将阶段预算达到当p95通过。旧raw/manifest不重写；排除与复用选择不得依赖观察结果好坏。新增sampling合同只修订计划，不授权或证明引擎已实现。
