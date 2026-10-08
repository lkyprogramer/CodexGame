# 13 · 来源、身份与引用约定

## 13.1 本包内部来源

- **R1**：[Claude 原始评审](../evidence/claude-review.original.md)，用户附件原样保留，评审日期2026-09-25。
- **R2**：[保留复现资产](../evidence/review-assets/)，bench_ftc.cpp、gen_prodshape.py、analyze_logs.py及results-29；hash在[input-provenance](../evidence/input-provenance.json)。
- **R3**：[本次资产结构审计](../evidence/review-assets-audit.json)，只解析保留记录，不是重跑节点29。
- **R4**：[本次词法模型检查](../evidence/scanner-model-checks.json)，有限纯词法模型，不能冒充真实NInferBPE/资源验证。
- **R5**：[本包自检记录](../evidence/PACK_CHECKS.md)，辅助工具结果、生成数据与ZIP校验的范围。

## 13.2 固定仓库来源

[S01–S15 完整清单](../source-lock.json)记录固定commit、symbol/purpose与blobSHA。关键读数对应：

- processor.cpp::encode_rendered_chat：完整主encode与各prefix重复encode，错误检查和hints顺序。
- tokenizer.cpp::Tokenizer::encode：循环find；validate_supported_added_token及merge后ID顺序。
- tokenizer.h：旧EncodeOptions只含parse_added_tokens，未有新master的边界接口。
- chat_template.cpp：last_real_user_query、StablePrefix、StableTurn、Rolling与generation opener。
- frontend.cpp/resources.cpp：text/media/count/prepare_tokens及资源绑定。

仓库永久定位：`https://github.com/tensorninja/ninfer-4090/tree/44a2c6c3392c9d51e76a895ed97bf1867530d252`。详细URL在source-lock；不要替换为main。新接口和新增测试target是设计要求，不在来源清单中伪装成既有实现。

## 13.3 身份尚未拿到的资料

完整prepare-detail镜像ID/digest、生产overlay完整diff、实际artifact六对象bytes、原1690JSONL、真实请求正文、review原生成语料没有随附件交付。报告给出的短ID/哈希前缀和现场描述只作R1引用，不补全猜测。

HF `Qwen/Qwen3.8-27B@1d4bf0f` 的匹配是R1报告；执行者使用完整resolvedrevision和本地文件hash再确认。无需为了本任务访问浮动HF main或下载另一份完整权重。

## 13.4 引用形式

执行报告引用`[S05: symbol, blob]`、`[R2: file, row/case]`、`[LOCAL: command, resultfileSHA]`。性能表每行必须标明CPU原型/产品CPU/HTTP/生产观测/估算。中文评审原文保持原样，其内部推断和例子错误由[16](16_ASSET_AUDIT_AND_LIMITS.md)单独说明，不偷偷编辑原附件。
