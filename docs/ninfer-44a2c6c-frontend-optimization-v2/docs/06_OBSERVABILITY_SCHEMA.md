# 06 · 诊断字段与统计合同

## 6.1 保留诊断overlay的真实语义

报告说overlay改11文件并将schema20 prepare截止移动到engine_submit后；本包未持有diff。T00必须保存实际diff/image，T01确认每个timer边界。不能重新实现一套看似相同的timer后对比旧数据。

沿用`prepare_detail.tokenize`表示整个`encode_rendered_chat`；不要改成只计主E而不改名字。`template_render`保留完整render。`rendered_chars/content_chars`继续供旧消费者使用，但文档明确为UTF-8字节，可新增同值`rendered_bytes/content_bytes`别名，不静默改成codepoints。

## 6.2 新增字段建议

在现有`prepare_detail`下增加`tokenize_work`，字段名在T01与reader共同冻结。示例数值仅格式，不是运行结果：

```json
{
  "tokenize_impl": "b0-b1",
  "tokenize_work": {
    "main_encode_calls": 1,
    "main_input_bytes": 900000,
    "checkpoint_hints": 22,
    "boundary_queries": 25,
    "boundary_unique_offsets": 24,
    "local_encode_calls": 24,
    "local_input_bytes": 212,
    "local_max_bytes": 10,
    "memo_hits": 1,
    "main_scan_positions": 845000,
    "main_candidate_checks": 18000,
    "main_added_matches": 3800,
    "ordinary_input_bytes": 840000,
    "ordinary_segments": 3801
  }
}
```

**此示例非内部算术的测试oracle。** 真实统计取路径计数，不从长度推估扫描数。不在产品热循环中对每个标记打时间戳/NVTX或写日志；只做局部整型计数，调用结束聚合一次。

若schema20的既有reader拒绝未知字段，升级schema21并明确变更，运行时和分析工具同时接受有文档的版本。不允许号称保留20却改原字段含义。现有本包analyze_logs只按schema20处理；升级时需执行者补适配测试后使用。

## 6.3 两类工作量

主统计：B、A、H、Q、主扫描位置、候选比较、普通分段字节、local总字节与最大字节。

legacy只在离线benchmark统计`logical_encode_bytes=B+Σb_j`及`find_span_estimate`。后者是逻辑待搜索区间估算，不是CPU memory controller读数。`scan_positions<=main_input_bytes`只适用于一次B0主扫描，不可把local扫描累计也拿来与B比较。

## 6.4 阶段时间的计算

`tokenize_total = main_encode + local_boundaries + resolver_overhead`应来自同一request嵌套timer的约定。新增计时要区分inclusive/exclusive；不将percentile相减。归因时先对每条计算residual，再取分位。

TTFT指第一个有意义model reasoning/content/tool delta的时间，不能把role-only SSE当首字。server自己的模型首token与client首delta可能不同，HTTP测试两者都记录。队列、restore、prefill可能已有嵌套关系，按真实源码核对，不生硬要求所有字段相加必等TTFT。

## 6.5 日志数据治理

日志只含数值、固定枚举、image/commit/资源hash、匿名request关联，不打印prompt、tokens、tool arguments、paths或原始异常中可能含用户文本。差分错误在受控本地输出完整语义用于分析，公开报告只输出case_id、hash和第一个不同字段路径。

任何真实请求正文采集须明确授权。现有1690条metadata无法还原prompt，不得要求AI从这些日志“回放1000条golden”。

## 6.6 统计口径

按schema、server_instance_id、时间窗口、source/client、prompt_tokens、rendered_bytes、H、Q、path、cached_fraction分层。冷热至少同时给出定义：`prefix_cache_hit_tokens==0`，以及另一个`cache_fraction<0.1`；不要混成同一个cold计数。分档边界使用脚本固定值并写报告。

总和用逐条原始timer求sum；p50×n只能做探索估算，不能作为发布收益结算。sum(request_total)是请求服务时间之和，不是独立CPU/GPU忙碌时长；存在重叠时另报区间union。done时间戳若是结束时间，first_start=first_end-first_total，不能加最后一条total来修补首尾跨度。

## 6.7 验收观察量

B0+B1完成后看tokenize p50/p90/p99、H/B结构、<8K回归、maincalls是否1、localbytes是否符合输入形态、request_error是否新增。观察highcache且tokenize慢的request，同时保留full_reset和publish失败单独看板，不能用全局中位数掩盖两类问题。
