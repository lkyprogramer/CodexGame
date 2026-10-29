# 数值与任务质量门

## 1. 三个参考层

- R-production：附件最后已知A0+EXACT6，仅用于最终用户收益对照。
- R-latest：最新源码、相同模型资产、公共配置、已资格验证的基线；所有候选的主要参考。
- R-quality：对明确会改变精度/语义的分支，建立质量优先参考（关闭相应近似或使用更高精度可运行配置）。它不能与速度基线混名。

已有量化/路由策略可能本来就近似。所谓“无损”必须说明相对于哪个参考，不得把相对量化基线不变写成相对BF16原模型无损。

## 2. 数值测试顺序

1. 类型与内存：所有实际dtype、非整tile、nt1..8（lookup长窗另测9..16）、空expert、最大expert数、对齐/尾部、stride。
2. 单kernel：同一输入与布局，E轨道逐位；N轨道记录max_abs/RMSE/relative分位及参考A/A，不能只用一个宽松max误差。
3. 算子链：GU→SwiGLU→ActQ→down→combine，验证中间量化/求和顺序。
4. teacher-forced：同一token轨迹，候选维护自身KV/GDN/MTP状态，让误差累积；记录full logits或可审计压缩量、KL均值/p95/p99/max、top1翻转和margin。
5. 状态寿命：prefill分块、decode、spec reject/accept0/1/all、park/restore、取消恢复、编辑前缀；与从相同tokens重新计算的参考比较。
6. 自由生成：greedy与真实采样thinking分别测；输出不同不自动等于错误，也不自动通过。
7. 任务oracle：代码编译/测试、严格JSON类型、完整tool_calls、长上下文跨文件任务与真实Pi循环。

Kern的top20+other均值KL是筛查方法，不能直接抄一个1e-3阈值宣告128K安全。全词表尾部压缩与平均值会隐藏局部问题；特别保留失败位置及其上下文。

## 3. 质量集合

保留原`fixtures/questions.json`、8项Java oracle及生成的长ledger，用修复评分器重新生成新dataset ID。新增集合由P00任务实施，禁止把旧缺失14题复建后冠以旧ID。

| 集合 | 最低覆盖 | 判断 |
|---|---|---|
| Q-JSON | bool/int/null、重复key、NaN/Infinity、嵌套、空/Unicode | 固定exact oracle严格区分类型；通用schema需单独validator |
| Q-TOOL | 单工具、多工具、分片参数、空参数、错误修复、tool结果续接 | 首段参数到达不等于可执行；最终完整schema正确 |
| Q-JAVA | 现有8题；新增并发幂等、事务边界、分页、缓存失效、钱币、时区、重试、资源关闭等至少24任务 | 隐藏断言；JDK8语法和行为；编译失败计失败 |
| Q-LONG | 8/32/64K、122K附近；首/中/尾证据，矛盾版本，多文件依赖，编辑历史 | 不只needle；答案和引用位置有oracle |
| Q-STATE | A→B→A、A→B→C→A、cancel、spec reject、cache不同精度或模板 | 必须状态身份正确，无跨会话污染 |
| Q-PI | 至少30个独立真实Java任务，冻结工具结果/时间规则与采样profile | 完成率、测试通过、修复轮数、总wall、总token |

单元测试用于测试实验工具，不代表模型通过质量门。8个Java小题也不代表大型Java仓库能力。

## 4. 非劣原则

项目建议的验收政策（不是已测结论）：E轨道不能新增确定性功能错误；N/Q轨道至少30个独立任务做筛查，正式非劣不默认30题足够。

冻结 `delta = p(candidate_success) - p(base_success)`，容忍边界2个百分点。四格定义：a=两者成功，b=仅基线成功（harm），c=仅候选成功（gain），d=两者失败，n=a+b+c+d。正式工具使用保守的paired二项边际界：`U_harm = CP_upper(b,n,alpha=0.025) - CP_lower(c,n,alpha=0.025)`；Bonferroni保证至少95%的联合覆盖，等价delta下界=`-U_harm`。只有U_harm≤0.02才通过本项非劣门；区间宽则INSUFFICIENT。它是保守策略，不能替换为30题全同后退化为[0,0]的朴素bootstrap。

在0个discordant任务的例子中，n=30的harm上界约11.57%，不能认证2pp；n=184时约1.98%。这只是该方法的样本量例子，不保证184题代表真实任务分布。相同任务的多seed必须按预登记方法聚合为一个独立任务结果，不增加n。

用包内 `tools/quality_gate.py` 和 `tools/QUALITY_GATE_README.md`执行该离线计算；它不会运行模型，也不能单独给总体发布PASS。真实模型失败仍是有效观测，不删除：`run_valid`表示实验有效性，`task_success`表示答案质量，`failure_kind`区分model_oracle、task_budget_exhausted、infrastructure_timeout、oom、crash等。引擎OOM/crash是硬拒绝，基础设施失效使比较不完整；模型达到预定任务预算仍为有效失败。

现有 `lab.cli stats` 是严格smoke筛选器：任何oracle失败会阻止其候选输出。它没有实现上述任务级非劣，也没有实现restricted time-to-success。正式任务适配器与性能分析由P00/P12实施；不能把smoke退出0当作正式质量门。Q轨道单独列速度—质量Pareto，不自动进入默认部署。

## 5. 128K预算

普通长测满足`template + system + tools + history + new_input + max_new_tokens + 4096 <= 131072`。预算来自与服务完全匹配的tokenizer及模板；usage缺失或计数漂移超约定误差应停止该长测。

专门的边界测试可取消安全余量但保留总上限，测试131071/131072/131073附近的完整渲染请求。超限应由测试客户端在发送前拒绝；不得用自动截断让测试通过。需要强行探测服务端错误语义时用单独negative测试，明确不属于正常性能样本。
