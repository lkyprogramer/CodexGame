# P12 — 留出、组合、可复现与最终采用

**目标：**把有机制依据的候选变成可审阅的用户机器证据；不替代用户已有部署权限边界。

## P12-01 先冻结少量候选

64项是搜索空间，不同时跑64场显著性竞赛。先按P00测量与catalog资格，筛出最多一个CPU、一个缓存/调度、一个GPU/spec候选进入正式对照；每个都有base/off/on、source和config diff、实际activation、单元/数值/机制测试。已有NO_GAIN只有在新trace证明条件变化时才能复活。

固定任务预算、seed规则、独立block数、停止规则、置信方法、主要metric和流量权重。holdout任务不用于调参。每个结果含全部失败，不挑最好轮。

## P12-02 质量与性能联合门

1. E轨道逐位/状态与功能合同；变化不能伪装E。N/Q走12文档teacher-forced、长state和任务非劣。
2. 使用已交付quality_gate离线计算paired四格；独立任务证据不足时工具返回NONINFERIORITY_NOT_ESTABLISHED、退出1；总体实验据此归INSUFFICIENT。输入只能由真实任务oracle形成，示例全成功数据不代表模型。
3. 相对NI之外必须满足预登记的绝对功能质量门：关键确定性状态/工具/JSON契约无新增错误，真实Java任务达到在解盲前冻结的最低成功率，全部新引入失败有逐项审查。quality_gate输出absolute_quality_gate=NOT_EVALUATED，不能仅靠两臂同样失败的NI结果通过。若没有事先定义绝对目标，则此门BLOCKED，不事后挑门槛。
4. 正式性能使用P00实现的restricted time-to-success分析器，主时间ratio CI上界≤1−m，关键非目标≤1.03；正确性修复例外见14。现`lab.cli stats`只做严格smoke筛选。
5. 资源有峰值和最小余量；无新增OOM/crash/状态污染。p99少于1000请求只报探索性，不能补一个漂亮百分位当通过。

## P12-03 组合与相互作用

优先测试相互可能干扰的2×2：pool×spec、resident policy×prefill scratch、RAM trim×snapshot reuse、lookup graphs×expert budget、KV压缩×tiny-queryattention。若候选A/B单独有效，组合仍必须对最新base重测；收益不相加。

观察interaction=`log(time_AB/base)-log(time_A/base)-log(time_B/base)`作为诊断，区间按同一paired单位。负值仅表示该口径下协同，不能证明普遍。组合回归cover8/32/64/122K、greedy/sampled-thinking、append/edit、A/B/Crestore、cancel、serverrestart与压力恢复。

若组合失效，保留更简单且对真实目标更好的一个；不通过堆开关维持结果。production最终方案中每个flag必须有证据和fallback。

## P12-04 对历史生产的最终收益

最新baseline资格与增量改造均通过后，将final_candidate与历史生产A0+EXACT6在同一当前机器、资产和固定工作负载重测。历史5.3%/2.2%不能与新收益相加，因为版本、计时和任务可能不同。报告三列：historical_production、latest_base、final_candidate；迁移收益与新改造收益分开。

## P12-05 交付可审阅的发布候选

生成`RELEASE_CANDIDATE.json`，包含source/base/donor commits、完整patch、dirty为空证明、GGML/compiler/flags、exe SHA、asset/dataset/host hashes、activation/config、资源账、quality/perf/组合/holdout证据、已知失败、fallback、停止条件。推荐状态只能是READY_FOR_REVIEW，不以脚本退出0代替人工检查。

可执行文件与配置在隔离目录中准备；校验路径和所有权。已有明确生产部署授权可继续履行；本次研究请求本身不自动给后来执行AI停现网、改driver或修改systemd的权限。若需要批准，先完成上述具体候选和rollback，使最后批准对象是可审阅成果而不是抽象计划。

## P12-06 回滚与事后观察

备份准确的旧binary/config/依赖身份，不只记tag。明确新binary停机/旧binary恢复方式、cache格式是否兼容；不兼容cache不能给旧binary读取。部署后先运行最短受信健康与toolstateprobe，再在预定观察窗看错误/恢复/尾延迟/内存。发现数值异常、cache污染、OOM、超预算或质量退化即回退已知好版本，保留失败现场。

原始用户代码、工具结果、密钥不进入公开报告；提供脱敏统计与可验证hash。任何没运行的测试都明确NOT_RUN，任何跳过都说明资格影响。

## 结案文档

每方向给ADOPTED/NO_GAIN/NOT_APPLICABLE/QUALITY_REGRESSION/BLOCKED/INSUFFICIENT，附主要证据、限制、未来重开条件。优化完成不等于机器理论极限已被证明；它表示已把当前可测瓶颈逐项验证并保留最优受信配置。
