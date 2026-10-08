# 12 · 后续路线与停止条件

## 12.1 本轮排序

首先完成B0+B1及精确/CPU/HTTP验证。这既改变原v1“B1→B2”的顺序，也修正更早“约3000token/s的BPE所以必须跨请求缓存”的推断。新增证据表明有效吞吐被两层重复工作拖慢，而普通BPE本体并未被证明只有3000token/s。

首期达标后，**完成并关闭此项目**；不以“缓存越多越好”为理由继续加入FrontEndContinuation。再比较真实任务remaining wall组成，决定后续工作。

## 12.2 B2 重新开启条件

同时满足以下条件才形成新设计/任务，而不是自动实施：

- B0+B1真实产品已发布且G0–G7闭环；至少两个匹配形态观测窗口中，120K+热续写tokenize p90仍>1s，样本不少于50或明确样本不足。
- 该时间确实是普通编码/局部边界而非诊断、锁、CPU干扰或full_reset；对总requestwall有可测的重要占比。
- trace与局部memo无实现缺陷；已有B1可优化边界重复/allocator不是更低风险选择。
- 在固定请求语料上，计算包含LCP、资源identity、pin、容量、publication和锁的完整B2成本；收益超过团队设定的工程成本阈值，独立review批准。

阈值是重评触发器不是B2准入PASS。附件0.001s未计全部成本，不能直接用于这一判断。

## 12.3 tokenizer 内部后续优化

若普通BPE本体仍大且冷请求居多，可独立profile merge表、分段、临时分配、NFC；每项保持相同错误/token合同，单独PR。不得以新HFtokenizers输出作“更正确”基准替代历史资源语义。执行前重做ROI，不把以前偏低的有效吞吐当当前纯BPE性能。

## 12.4 full_reset 是并列独立工程

评审报告长full_reset prefill合计57.8分钟，规模接近append tokenize64.7分钟。tokenizer修复后，这条尾部成本会更显眼。以[17](17_FULL_RESET_SEPARATE_PROJECT.md)只读证据工作启动；若路由/TTL/容量因果验证成立，形成单独配置/引擎修复包。不要在同一性能表混入两项改动。

## 12.5 MTP、Suffix、DFlash2与模型版本

当前热decode约100token/s，tokenize几十秒优先级明显更高。首期稳定后若decode成为主要服务时间，才能回到proposal head/suffix/DFlash2。在所有实验中保留262K、真实采样、同输入和cache状态。Bonsai/EXL3等不同制品不属于本包；变更权重会同时改变前端资源和输出分布，不能与纯前端性能补丁混跑。

## 12.6 成功定义

成功不是“上线更多功能”，而是：两个重复算法消失，语义不变，真实形态CPU≤1s，短请求无退化，HTTP热首字按实际数据降低，没有新增复杂共享状态。如果B0+B1已经满足这一目标，B2保持DEFERRED是合理结束，不是未完成项。
