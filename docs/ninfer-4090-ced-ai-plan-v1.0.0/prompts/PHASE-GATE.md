# 阶段验收与独立审查提示词

只审查当前Phase的同一集成提交，不接受Task作者的口头PASS。读取该Phase文档、05统一验收、当前run_manifest、checks、raw timings、quality与restore。

检查：所有依赖Gate有效；required check都有实际case；没有SKIP/exit77被当通过；code/binary/base/predictor/config身份一致；请求长度是实际token而非max-context；Teacher没有进入真实candidate；没有偷换MTP/codec/thinking；近似状态没有被标成native；fallback成本未被排除；失败/超时未从统计中删除。

报告按templates/phase-report.md，输出PASS/FAIL/INCONCLUSIVE/BLOCKED_RESOURCE，并明确qualification scope。任一必需检查未取得证据，不得写完整PASS。数值、质量、性能、生产保护分别判定；不以其中一项代替另一项。

若当前Phase改变了上一Phase合同，指出需要重开的Gate。若只是文档修改且binary完全相同，可引用同一已核验binary证据，但不能伪造新运行时间。
