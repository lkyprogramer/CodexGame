> V4继承材料：原始当前V3保留在源目录；本副本按V4根执行合同使用。历史“先跑Baseline”、旧发布依赖和旧scope不能独立调度。请先读[V4唯一执行入口](../AI_EXECUTION_PROMPT.md)；原文事实、旧实验记录和未改写的历史状态不等同本轮授权。

# 给开发Agent的唯一入口

你正在执行NInfer V3计划，不是在部署HyperQwen，也不是把tqLLM整体merge进NInfer。先读research/01、design/00、plans/00和plans/01；执行注册表的有效范围是P0—P6与H0—H8，旧P7—P12只参考。

## 当前先执行 BASELINE_ONLY

本轮先读 [29 Baseline合同](plans/05-baseline-29-execution.md)、[分层范围](plans/06-staged-evidence-budget.md) 与 [sampling合同](design/11-sampling-acceptance-and-proposal.md)：只修订文档/采集工具并跑B29。初始278请求+8工程一次/2repo一次，Pi44一次O32768；阶段≤240相关A/B请求，H5/H8才做正式发布资格，不再先展开全部672。暂不实施引擎优化。B29二进制测量不依赖尚未取得的P6，但不能据此填P0/P6/H0完成。准备不可变run manifest、raw、heartbeat/status、可恢复checkpoint与定时唤醒；确认脚本和监控推进后让出回合，不主动频繁轮询。

区分B29(E8/schema20/实际sampling)、BO(clean O重建)与B6(真实P6/rk4v4/schema24)。当前先兑现原P0的PROD测量，保留缺失构建/迁移资格。固定Pi轨迹不执行历史工具；闭环另在隔离工作区执行。统计、缓存、token/ID与逻辑/物理宽度纠正以当前design/07、design/09及baseline合同为准。

以下是未来解除baseline-only范围后才可执行的优化循环。

## 开始前

核实实际分支/dirty overlay/生产镜像与P6-GATE。没有真实P6资格则从原P0—P6未完成处继续，不能从“文档已经写完”推断已经实现。使用独立worktree；不reset生产树、不下载/切换Target、不强推仓库。

## 执行循环

先读当前Task的相关设计、源文件和接口；依赖与文件锁满足才启动。Task写最小失败测试→实现→定向GREEN→自审提交。CPU独立文件可并行，公共头/CMake/Program只能Integrator串行写。单4090测试排队；不并行驻留两套27B。缺subagent时按同依赖串行，不虚构独立Reviewer。

每Phase统一合入同一个commit，独立review组合diff，执行该阶段实际变更的数值/功能/资源/GPU合同与预登记相关小集；不要逐阶段展开全声明/发布重复。H5/H8才集中实际发布profile的正式业务/尾延迟资格，预算耗尽仍缺证据就INCONCLUSIVE。通过Task不自动通过Phase，通过Phase不自动production promotion。缺权重/GPU、CTest skip77、0test、证据错commit一律不能PASS。

## 必守产品约束

唯一完整TargetVerify/ReplaySSM/输出/continuation权威；保留B0/B1、prepare_detail、工具协议和合格rk4v4/262K能力。新功能默认OFF，先base/text；greedy/deterministic仅描述proposal，Target生产采样维持T1/.95/k20/presence0/preserve-thinking/medium。新增sampling组合资格前回既有合格sampling；媒体/adapter仍原资格路线。Target-greedy单列数值诊断，不当生产收益。不要把Lookup加成新模型backend，不把MTPmax5改15来代替外部W16。

Lookup候选仅当前有效token历史。接长尾需要前序候选一致，禁止无条件7+8。skip-proposal仍做必要MTPalignment。TargetKV不等于DraftKV；ProjectedG archive独立身份。hostfeedback必须event完成、epoch匹配且round只消费一次；捕获图不能冻结未来host策略。

## 收益与停止

以committed token/整轮wall和真实Java任务walltime为标准；accepted/proposed/SSEframe不能替代。保持同Target模型质量与context；预算不足或无收益不强行推广。W8/W16无法合格则明确取消宽块范围并保留较窄合格路线，不能称其通过。H6缺资产则H7阻断，H5可单独发布，完整H8不得虚报完成。

不要重复研究已被来源锁确认的表层事实；实施前只重定位P6后的实际代码变化。新asset的未知shape/version不能猜，取得真实manifest后继续。真实生产操作按P0冻结host/窗口/服务名与design/08实施，不从历史文字臆造授权范围。

## 每次交付

写明task/phase、实际commit、最小测试与完整gate的分别状态、GPU实测/未跑、资源、采用/拒绝理由及回滚。先结论与证据，不把上游作者自测、旧63helpertests或本次文档检查写作当前产品验证。

## 窄范围发布前置

本页依赖是默认完整方案；W8/W16退出时仅可依据[发布范围契约](design/10-release-scope.md)的`e1_w6/e1_w8`派生DAG进入H5。范围外任务保留真实状态，不能伪造H3/H4-GATE通过。

## 不能混淆的采样与范围

H1-T07要求deterministic delta-q、最终mixed prefix下的Target p/processor、fractional accept/residual/support边界、bonus/stop/cancel/commit、RNG分布vs路径一致性八组具名证明。优先重定位并复用`speculative_accept_greedy_drafts`；其名称不是Target只能greedy。已有CPU参考缺min_p/tie/CDF/RNG全语义时补独立测试，不能把旧top_k1用例当fractional资格。未来随机draft没有general-q合同不启用，不另造sampler绕过原state。

工程集改为旧3题+QCB BF009/RE003/RE007/AT005/LC003；初始各1次，发布3seed；真实repo2题各1次、环境未知NOT_RUN。撤回20×3通用下限，保持合成/框架/真实repo资格边界。旧记录按最早有效raw/hash/case/cache匹配复用，不按成绩挑选；旧manifest不改写。
