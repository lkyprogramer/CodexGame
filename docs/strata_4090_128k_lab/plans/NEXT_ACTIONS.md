# 当前结束点 · Astra复核后零候选收口

[Astra复核与收口报告](../reports/FRONTIER-CLOSURE-ASTRA-20261031.md)：2026-10-31独立复核已完成，root采纳结论，停止当前冻结合同下的性能探索。当前NO_QUALIFIED_CANDIDATE；撤回“优先推进F02”的建议，取消原拟追加的四小时离线审计。

**当前生产已恢复运行。** 用户在文档收口后明确要求恢复既有服务；[恢复回执](../reports/PRODUCTION-RESTORE-20261031.md)记录12:49健康接口loaded=true、12:50:44 active/running/enabled、NRestarts0。生产GPU已占用，旧停机回执不能用于判断当前实验资源。

F02保持DEFERRED_NEW_EVIDENCE。旧P11 trace按实际PID与首末输出区间重算，GU-SwiGLU全家族并集占6.8911%/6.5884%，但合同限定一个格式、一个内核；最大TG21仅2.2188%/2.1287%，且尚无已证load/layout新机制。这是旧profile条件成本，不是当前真实暖态暴露成本或严格上界，不能外推全局NO_GAIN。

## 当前行动

- 文档、入口与清单已收口；不进入P02/P03候选开发，不追加GPU，不换另一方向续测。
- P01原短输出停止、P01B执行COMPLETE/资格INSUFFICIENT、F03 NO_QUALIFIED_CANDIDATE及旧关闭结论保留；六FAIL不变，P05仍BLOCKED_EVIDENCE。
- 6144MiB/4slots、PT0和生产配置保持。生产恢复动作仅启动既有服务，没有改配置或追加GPU实验。未来停生产或占用GPU须明确对应执行范围；本次恢复不解除实验前置门。

## 未来重开条件

先提供独立新源码机制、当前真实暖态命中与可闭合依赖证据、可信局部方案和新增成本账，支持完整请求净省时≥4%；说明旧否决证据为何不覆盖新机制，并明确资源/质量前提、新编号和限额合同。缺证据保持DEFERRED_NEW_EVIDENCE/BLOCKED_EVIDENCE，不自动补采样。后续实施或GPU实验须由用户明确给出对应范围；本次收口不产生实验授权。

## 已关闭的F03 CPU审计

[F03实际报告](../reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md)：2026-10-31按用户授权完成会话快照复制/生命周期审计及必要CPU验证，结论NO_QUALIFIED_CANDIDATE，本轮关闭。

没有证明泄漏或可删除的已结束快照。现有take/retain、dirty边界、superseded、guard、容量回收和off-path move已覆盖对应语义。唯一新差量“同步KV保存避免先零填”在独立CPU目录验证：cache4834 checks、基线/原型各2068 host checks PASS，但固定三对完整CPU成本均慢6.08%–7.74%，不保留候选、不追加样本。

GPU启动0、推理0，无engine重建；生产停机，13保护hash、原P6和配置未变，6144MiB/4slots/PT0保持。无新优化采用，不进入P02/P03或GPU。六FAIL及P05 BLOCKED_EVIDENCE继续保留。重开须有独立新机制与当前暴露成本证据，不能重测同一零填、旧async/pool或trim/MMAP开关。

## 已关闭的P01B

[P01B实际报告](../reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)：2026-10-31按用户授权补齐host有界采集并验证，单引擎三请求全部完成，无重试。prime/append_1/append_2输出941/576/774，最后一次追问read291/reused89207。执行COMPLETE，候选资格INSUFFICIENT。

939个完整窗口、2291个原始token IDs已核对。两条warm请求的verify返回→commit进入全部host间隙仅占0.1340%/0.1224%，该窄方向没有4%空间。GPU内部和其他未知依赖保持UNKNOWN，不外推全局无优化空间。首个append大规模重读与PT0上下文相关渲染吻合，第二次已高复用；没有据此认定新的持续缓存缺陷。

生产保持停机，最终13保护SHA、原P6及配置未变，GPU1MiB、端口空闲、所属PID退出。本批次关闭，不追加GPU、不进入P02/P03、不遍历候选。新方向须先有明确机制差量和可闭合依赖证据；六FAIL和P05 BLOCKED_EVIDENCE保持。

## 上一批次保留

[P01实际报告](../reports/P01-PI-WARM-DIAGNOSTIC-20261030.md)：单引擎/1prime，103183输入、941自然EOS。按2048输出门停止，两次append NOT_RUN，阶段INSUFFICIENT。P00身份锁定仍有效；本轮无新候选资格、未部署，生产停机。

采集适配已实现并交付，但实际warm链、2048长输出、逐window依赖与原token IDs均没有得到证据。P05保持BLOCKED_EVIDENCE，原六FAIL不变。

P01原run保持关闭。其后由用户明确授权的新P01B自然EOS合同另行执行，未倒写P01原验收门或失败原件。
