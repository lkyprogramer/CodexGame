# 执行AI协作合同

本文件约束使用本包的后续工作，不将文档中的提案伪装成已实现接口。

- 必须先读START_HERE_AI、source lock和对应plan。生产资产/目录只读；原附件历史不覆盖。
- 当前基线4b9e05a2…；41cf05a0…是已深审引用点，差异审查见02。更新上游需新baseline资格，不能静默改LOCK后复用旧结果。
- 实际型别/路径优先于模型包名。AVX512-VNNI不等于VBMI或AVX-VNNI；禁止删CPUID门控。
- 所有新引擎优化默认关闭，正向activation证明，base/off/on分别测。每个提交只承担一个可归因机制。
- 能影响数值/状态/同步的改造先写真正会失败的测试，再实现；纯文字修订不滥加测试。参数/日志观察不可改变真实运行图后又当生产速度。
- 多agent可并行读代码、设计、CPU单测；任何GPU性能运行串行且独占，CPU编译/微bench不得干扰。只停止本次拥有的进程。
- 失败要保留；配置/资产漂移、缺项、OOM、错误回滚按协议处理。SSE事件不是token，cache slots不是并发，spec-min-p不是sampling min_p。
- 真实任务主指标restricted time-to-success及完成率；源代码行数、GPU利用率、接受率和microbench单独不是成功。
- 暂缓历史NO_GAIN；若重开，先记录改变了什么前提。E/N/Q/X分轨道，不把语义近似纳入等价加速。
- 不自动修改driver、引导、systemd、host频率或生产配置；复用用户已有授权，超出授权才在具体方案就绪后澄清。
- 文档中的源许可/数据身份是实施前条件；EAGLE-4不是普通OSI开源donor，不能直接copy其受限核心代码。
- 每次交付列what/why/tests/limits/rollback，保存raw证据、patch、hash、config/dataset/host。NOT_RUN、SKIPPED、INSUFFICIENT不能改写成PASS。

若下游AI环境没有计划中提到的命名技能，按本包的分任务、先失败测试、独立复核与证据规则执行等价流程；技能名不是本包Python工具的运行依赖。
