# 最终包只读审阅：入口、接口与统计门

审阅对象：`output/strata_flashnext_4090_extreme_lab_v2`，2026-10-25。只读核对文档、CLI及相关源码；未修改包内文件，未重跑测试、启动服务或执行引擎。FRESHNESS/VALIDATION等正在生成的文件未计为缺陷。

## 优先修复

1. **P1 — schema2计划缺请求hash仍可能获得候选结论。** `lab/statistics.py:85–90`只检查case ID；`:132`在`case.get('request_sha256')`为真时才核对请求身份。若descriptor缺此字段，而两臂record具有相同非空hash，后续检查仍能成立，单层五轮三臂可能进入`CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION`。这违反`HARNESS_UPGRADE.md:92`和docs14的预登记缺项拒绝合同。正常runner会写此字段，但离线stats接受外部结果，不能依赖正常producer。应强制schema2每个case包含合法非空SHA256，并补“descriptor缺hash、两臂row有相同hash仍拒绝”的回归测试；本轮为静态审查发现，未执行复现。

2. **P2 — 统计估计对象的文字与实现不同。** `docs/13_BENCHMARK_PROTOCOL.md:23`说“按case求paired log ratio，再按round聚合”。实际`lab/statistics.py:155–156`先按同层/同round/同arm求case时间总和，再对paired轮总时间求log ratio/bootstrap；`HARNESS_UPGRADE.md:106`描述正确。两种算法对长短任务的权重不同，应该改协议文字而非静默改算法。

3. **P2 — 可复制报告样例残留旧base。** `plans/P05_CUDA_PREFILL.md:219`的JSON `base_sha`仍是`41cf05a0…`；本包执行锁、registry与READY均是`4b9e05a2a806a3fe24f7b2560d98626c37dade35`。建议该样例改新锁或要求从LOCK读取。文献源码链接保留41cf正确，无须批量改引用。

4. **P2 — 质量工具返回状态名写错。** `README.md:36`和`plans/P12_HOLDOUT_AND_RELEASE.md:14`称返回`INSUFFICIENT`。真实helper为`NONINFERIORITY_NOT_ESTABLISHED`、退出1（`tools/quality_gate.py:166,226`）；`tools/QUALITY_GATE_README.md`正确。可以将项目decision映射成INSUFFICIENT，但要明确这是上层映射，不能说CLI直接返回此字符串。

5. **P2 — 自动监控覆盖表述超出实现。** `docs/13_BENCHMARK_PROTOCOL.md:36`称monitor持续检查swap与资源释放。当前`OwnedServer._monitor`覆盖GPU身份、温度、MemAvailable，未采集swap；资源释放由退出时`wait_released`检查。建议注明swap等为P00待补观测，不将协议要求写成已实现功能。

## 已核对一致的关键边界

- README、AGENTS、LOCK、实验registry与READY模板的最终执行SHA均为4b9；41cf明确作为深入审计引用点，旧5c8+EXACT6保留历史身份。
- 入口展示的`init/doctor/assets/bootstrap/build/prepare/qualify/run/corpus/mig/stats/validate-plan`命令名称与参数成立；全局`--config`位置正确。`run`示例未错误传`--corpus`。新registry各PR有对应`prs/PR<N>.md`。
- MIG的`p`使用部署binary及serve树，但两臂均用归一化实验配置：local覆盖cache预算，parallel=1、移除batch、固定测试端口等；**不是原样生产运行的复刻**。P00已明确cache-off资格范围；建议补上这一句完整语义。
- `cfg --env`仅STRATA变量、MALLOC适配未实现，文档已说明。`cfg --tree`需要build receipt。dry-run仍要求可读local配置，但不检查GPU、READY、构建或完整运行时限制，不能作为资格PASS；现入口没有此类虚假PASS承诺。
- park/restore只有离线schema检查；正式restricted-time性能分析器、真实任务适配器、window trace明确为后续实施。docs12–14没有把这些写成现成CLI。正式NI和smoke统计分开，模型失败/任务预算与基础设施错误区分正确，质量门退出0未被写成发布批准。
- 131072作为完整输入加输出的总预算、普通测试4096余量、专门negative边界测另行隔离，表述一致。quality gate的b/c四格、Bonferroni CP界、30题不足及184题示例与实际helper一致。

## 非阻断清理

`HARNESS_UPGRADE.md:155`仍说“这个工作副本中的旧START/prs/sources”，最终包已完成整合；`:160`声称早期red日志和`final-tests.txt`随包保留，但当前evidence目录仅见最终with-quality两文件。建议删工作副本说明、明确这里只携带最终日志，或者补对应历史证据；不影响已有最终日志的有效性。

本审阅没有提供新的测试通过或目标机性能证明。根代理应从最终包执行其计划的完整离线验证，并在最终manifest冻结前处理上述接口/合同问题。
