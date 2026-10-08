# 06｜诊断字段与测量合同

## 6.1 不覆盖未知schema20

44a2c6c是schema19。现网prepare-detail是用户本地schema20，补丁正文未提供。T00先归档实际diff与真实一行request_start/request_done的键名。不能用本包字段名覆盖既有tokenize/prepare含义。

推荐保留现网字段并增加`frontend_tokenization`对象，内含`schema_version:1`。若原仓全局schema必须升级，执行者选择未占用版本并同步reader/dashboard/tests，不能盲写21。辅助分析工具只读本包的规范化row，不自动猜schema20字段。

## 6.2 最少诊断

```json
{
  "frontend_tokenization": {
    "schema_version": 1,
    "mode": "single-pass",
    "selected_path": "single-pass",
    "render_bytes": 810000,
    "boundary_queries": 0,
    "unique_boundary_offsets": 0,
    "legacy_requested_encode_bytes": 0,
    "main_input_bytes": 0,
    "local_prefix_input_bytes": 0,
    "ordinary_bpe_input_bytes": 0,
    "full_encode_calls": 0,
    "reused_prefix_bytes": 0,
    "reused_prefix_tokens": 0,
    "suffix_input_bytes": 0,
    "cache_lookup_seconds": 0.0,
    "main_encode_seconds": 0.0,
    "boundary_resolve_seconds": 0.0,
    "shadow_seconds": null,
    "shadow_match": null,
    "fallback_reason": "none"
  }
}
```

上例为字段形状，不是真实测量。0只能代表已测为0，缺测用null并标记not_measured。

定义：legacy_requested_encode_bytes按旧调用列表计`B+Σb_i`，重复offset保留，用于工作放大对照；main_input_bytes是本次真正交给主encoder的bytes；local_prefix_input_bytes是resolver局部prefix的累计bytes；ordinary_bpe_input_bytes在append_bpe_ids入口累计，含所有实际重复，不用logical新token数替代。

`full_encode_calls`计实际完整R编码次数，single-pass应为1，incremental命中应为0；局部prefix调用不算完整R，但要计入work。对于未命中incremental，主编码=1。

`reused_prefix_tokens`是CPU复用，不是GPUcached_tokens；后者维持原值。不得把CPU复用数回填OpenAI cached_tokens。

## 6.3 精细定位重复开销

legacy诊断可加入`main_encode_seconds`与`boundary_prefix_encode_seconds`、`boundary_validation_seconds`。有需要时加added-token scanning/NFC/BPE计时，但不要为每个token查询时钟，避免测量改变性能。T01至少能回答：80.6s中主编码多少、重复边界编码多少。

## 6.4 时间闭合

针对**每一请求**记录prepare、ttft、queue、restore、prefill、first_visible_delta。先核对本地计时作用域是否重叠；不默认`prepare+queue+restore+prefill`都互斥。仅在确认互斥后计算残差，负值超容差视为测量错误，不clip成0掩盖。

p50(a+b)不等于p50(a)+p50(b)。不能用52−44.4得出固定7.6s剩余。性能报告须在逐行归因后再聚合。

旧NVML board energy主要计GPU，不覆盖CPU tokenization耗电。不能把GPU J/token下降解释为整机节电。CPU前端改动的第一指标是wall与CPU time；能源没有墙上电表时保留局限。[S00提交说明]

## 6.5 汇总必须分层

至少按：模式、cold/warm、prompt深度、消息数、boundary_queries、GPU reuse_path、front-cache hit/miss、真实Agent/合成压测、session_id。统计request_done之外的request_error/cancelled/rejected，不把完成子集当总成功率。

短请求1417条不能稀释长请求74条的退化；主图是120K+warm续写。重试要归回原任务，stop_token只说明终止原因。

## 6.6 日志与私密数据

常驻日志只有计数、资源fingerprint、不可逆会话标识、时间、索引与错误code。原始bytes/token IDs/goldens只在受控replay目录，默认不上传GitHub、不写公网共享报告。统计采样需固定规则并记录总体分母。
