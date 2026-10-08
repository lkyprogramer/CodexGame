# 16 · 复现资产二次审计与限制

## 16.1 实际读取的材料

原始review资产原样放在`evidence/review-assets/`，由input-provenance逐文件SHA256保护。包内有bench_ftc.cpp、gen_prodshape.py、analyze_logs.py和results-29的JSONL。不存在生产1690行原始日志、原始会话正文、现网artifact六资源、overlaydiff或原raw语料目录。

本次对材料做静态阅读与JSONL解析，不声称在节点29跑过GCC/CPU/GPU。`review-assets-audit.json`是附件结构审计，字段scope=`ATTACHMENT_AUDIT_NOT_RERUN`。

## 16.2 保留行统计

| 项 | 结果 |
|---|---:|
|session行|28|
|raw语料行|4|
|直接legacy对照行|20|
|间接B1参照行|8|
|含B2测量行|21|
|保留B0专门行|0|
|session中tokens>262144|12|

所有保留的对应equality标志为true，仅说明这些原型输入/路径的记录。不能从没有errors字段推导所有error合同已覆盖。

第一条prodshape：render903482bytes、768messages、273012tokens、H22、boundary_queries25、mainold4.450s、完整legacy101.564s、B1 4.480s、B0+B1 .442769s、localbytes212。这条是最清晰的算法工作量证据，但只能CPU测试。

## 16.3 原型代码与产品不同处

- review legacy clone没有实际processor里的uint32overflow分支；它不能测试该项旧错误合同。
- optional B0路径对prefix算长度，未完整执行nonempty/full/exactness/hintorder/error检查；时间是原型估计，产品B0应让旧processor原样执行。
- B2计时在LCP与guard后；没有线程安全共享缓存、预算、pin、eviction、publication或资源隔离的成本。
- include旧tokenizer.cpp的方式便于内部探针，但测试产品链接/ODR/ABI还需正式target。

因此T02重建完整独立oracle，不复制原型然后赋予它产品authority。

## 16.4 真正prefix冲突示例

字符串`<tts_text_bos>`末尾是`>`，较长拼写在相应位置是`_`，并非same-start短长完整匹配。这不否认字典选择规则重要；相反测试应使用能真的触发错误的合成冲突，如`ab`/`abc`和`<x>`/`<x>tail`。两组都覆盖较小ID对应短/长的不同情况。

## 16.5 逻辑扫描跨度不等于硬件流量

review的42GB/0.96TB来自每个find查询输入区间的逻辑扫描估计。std::string_view::find的实现会用优化搜索，CPUcache也可能复用；不得称已经用硬件计数器测到这些DRAM字节。B0结构门改为真实外层位置计数与candidatechecks，必要时另用CPUprofile证实指令/带宽。

## 16.6 生成器与token预算

review的prodshape generator引用raw目录但附件没有raw文件。即使参数769/20/0.78相同，也无法在无原语料时重建完全相同bytes。v2使用自写确定性corpora，明确新inputhash。旧190k文件实际296832tokens，prodshape272K/273K也超窗；所有HTTP输入均通过校准表选择，不复用标签判断。

## 16.7 日志分析代码的界限

review分析器可帮助探索，但若done时间为请求结束，span应由最早请求start和最晚end计算。使用`last_end-first_end+last_total`会错把最后耗时补到开头。本包新分析器按每条`[done-total,done]`重建interval，另给duration_sum与union。

“tool_count2/12 + gap<=600”是形态线索，不是客户端身份鉴定；“>600 +发布容量计数”支持idle假说，不是完整serializedbytes测量。不要由元数据自动把每个reset归因为某种机制。rawlogs缺失，本次不能重算评审84.2min/57.8min。

## 16.8 对用户可报告的结论

可以说：源码确认双重复，保留CPU原型支持B0+B1显著提升，因此v2改变优先级。不能说：已在你的4090上线修复，真实245K首字已1s。产品门与附件可信度分别记录，最终报告保留这一界限。
