# R4 — 六对正式实验与独立交接

前置：R3门、正式独立预算、被冻结的任务集合与统计实现。当前NOT_RUN。没有可信AAnoise或足够额度时不开始。

## R4-T1 正式执行

- [ ] 再核A/C source/binary/model/config hashes与唯一处理变量；禁止夹带M0升级或H2+D1组合。
- [ ] 冻结N个任务、权重、context/cache顺序、max_new、EOS/timeout/失败计入与scorer。
- [ ] 以 `AC / CA / CA / AC / AC / CA` 执行6pair；每个A/C各fresh owned engine，不能同GPU并行。
- [ ] observer-off，仅保合格低扰动统计；每请求完整raw与exit/stop reason保留。
- [ ] 任一身份/正确性/权限硬失败停止；预算不足标INCOMPLETE，不用成功交集作正式汇总。
- [ ] 完成后封存manifest，不再替换输入、输出或scorer。

## R4-T2 独立重算

Reviewer读diff、spec与质量失败，不改golden。Verifier从封存raw重算paired主耗时比、AAnoise门、6^6精确bootstrap及分层守护指标。

- [ ] 样本单位是pair/run block，不是token。
- [ ] 自然任务wall、质量、输出长度齐报；固定replay仅诊断。
- [ ] D1若定义copy-only，只可对该范围下结论，非copy guard必须守住。
- [ ] H2head加速但接受率下降/全任务无净益，按整任务判拒绝。
- [ ] p95样本不足/CI过宽显式INCONCLUSIVE，不补第七对、不改显著性门。
- [ ] 与历史/作者数字分栏，不与不同模型或硬件拼成排行榜。

统计命令由R0锁定现有冻结stats工具；不得在R4临时换bootstrap库/分位定义。独立重算需要工具变更时先说明旧结果不能比较，另审新合同，而不是“修到过门”。

## R4-T3 收口

产物：`decision.json`、`EFFECT.md`、`HANDOFF.md`、raw manifest、review与verification。

结论只能是：

- `KEEP_EXPERIMENTAL`：适用范围内有完整证据，尚非生产采用。
- `REJECTED`：保留失败范围与机制，默认关闭。
- `INCONCLUSIVE / INCOMPLETE`：不给收益声明，剩余缺口明确，不自动续费。
- `NO_QUALIFIED_CANDIDATE`：若前阶段已结束，不应伪造R4产物。

最后确认生产未变；后续若用户要求灰度，另给精确部署/rollback窗口。写入旧台账的新增记录必须链接本轮合同，不能覆盖原H1/H3/K1或StrataDF2结论。

## Phase gate

独立Reviewer与Verifier均签名/时间/输入manifest，Controller核已用预算与权限范围。最终状态的每一项有原件引用；“文档完成”与“优化成功”严格分开。
