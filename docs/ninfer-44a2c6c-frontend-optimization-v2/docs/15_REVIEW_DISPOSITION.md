# 15 · Claude Review 逐项处置

## 15.1 决策

需要修订，且不是增加一层功能，而是**缩小首期范围、补齐第二个算法根因**。接受B0+B1、B2延期、取消生产shadow、生产形态输入、绝对性能门与full_reset独立立项。对测试证明、现场因果和原型代码加限定，不把评审当产品完成报告。

## 15.2 F1–F8映射

| Review | 处置 | v2落点 | 验证责任 |
|---|---|---|---|
|F1 added扫描二次项|接受P0；不可再写成P3常数优化|03/04；T03|真实C++ B0 differential+扫描结构|
|F2 B2收益小|接受延期；p90>1s为重评条件不是自动触发|12/deferred|发布后匹配样本窗口 |
|F3 H驱动与合成偏差|接受；H实际测量，不把+2当普遍公式|06/09/recipes；T07|render H/Q+真实bytes |
|F4流程过重|接受删shadow/四模式/1000realgate；保留独立oracle+一次HTTP|08/10；T06/T11–13|有限差分不是全域穷尽 |
|F5共享vision/count|接受共享源码；不声称visionGPU已测|05；T09|expandedCPU+真实frontendintegration |
|F6资源身份不一致|接受artifact-first；前缀hash不当fullidentity|18；T00/T02|实际提取六对象fullSHA |
|F7 overlay已审计|接受为review现场证据；本包未拿到diff|00/18；T00|现场捕获对应builddiff/完整image |
|F8时间/字节/范围/分桶|接受修正文档与计数口径|01/06/16/source-lock|逐条统计、symbols/blob |

## 15.3 额外审计结果对计划的影响

1. **保留结果与报告声明分开。** 28session中20直接legacy；B0 10.01无保留raw。仍充分支持优先级调整，但正式G1/G4须产出自己结果。
2. **真正重叠标记用合成词表。** `<tts_text_bos>`与`<tts_text_bos_single>`不是字面前缀，加入真前缀/反向ID反例，不更改ID优先规则。
3. **oracle完整性。** review clone缺uint32，B0 optional路径省断言；新增T02来源隔离与T05错误顺序测试。
4. **窗口校准。** 12条保留session超262K；新HTTPfixture不得按文件名猜长度。
5. **B2计时。** .001s在LCP/guard后开始，不能等同完整共享缓存TTFT。延期决定更合理，不因此承诺B2“只有1毫秒”。
6. **复现材料并非全量。** 缺资源/rawtexts/inputs/logs/overlay；包中给出可重建新synthetic，但不叫“完全重跑相同29报告”。
7. **日志因果/忙碌口径。** reset归类依时间gap/tools形态，需另外证明；requestdurationsum不能自动成为硬件busytime。
8. **CPU基准干扰。** cpuset/nice降低影响不消除L3/内存竞争，发布计划不能写绝对不影响生产。

## 15.4 保留的v1价值

固定commit、原错误合同、added优先级、局部prefix分解、GPU token状态不可提前用作开关、完整render、源治理、任务化执行、精确差分都保留。删除的是没有当前ROI的跨请求状态与高代价发布流程，不是降低正确性标准。

## 15.5 不能从评审推出的结论

不能保证每个真实245K请求都0.44秒；不能保证HTTP恰好1秒；不能证明8GiB L2拒绝全由容量且调16GiB必修复；不能证明两个工具集合就是确定两个特定客户端；不能宣称“全possibleinput已穷尽”。这些留在限制与后续实验中。
