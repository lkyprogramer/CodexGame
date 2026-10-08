# 14 · 数据集与辅助工具合同

## 14.1 附带数据类型

| 路径 | 类型 | 用法 |
|---|---|---|
|`data/adversarial_cases.jsonl`|固定语义场景清单|C++adapter按kind构造输入，真实legacy计算oracle |
|`data/test-matrix.json`|case→task/gate/断言映射|不得漏掉case或用B2代替active覆盖 |
|`data/session_recipes.json`|生产形态配方|显式messages/recent rounds/tools/bytes/seed |
|`data/generated_sessions/*.jsonl`|32条新合成请求|默认UNMEASURED，须真实tokenizer校准后HTTP |
|`data/corpora/*.txt`|自写重复文本|可重复语料，不是review原raw，不是生产正文 |
|`deferred/b2_adversarial_cases.jsonl`|旧跨请求case|首期不实现，不计active覆盖 |

旧v1保留60个activecase，并新增v2针对scanner/trace/error的case。部分case是变换规范而非完成的API请求；C++adapter必须生成可执行输入和实际hash。input hash不能只hashcase_id。

## 14.2 case kind 映射

`raw-boundaries`：text转UTF8，以byte_cuts对每个prefix调用独立reference和candidate。`invalid-utf8`：按hex bytes构造string，绝不decode替换。`synthetic-added-priority`：合成完整byte-vocab并加载给定added字典。`synthetic-merge`：构造最小BPEmerge资源确保cut改变merge。`rendered-contract`：直接构造RenderedChat含offsets/hints验证processor；`chat-transform`：由固定basechat应用指定变换，比较完整PreparedPrompt。v2新增`scanner-contract`、`trace-lifecycle`、`boundary-contract`分别对应真实C++scanner、复制/并发、错误优先级。

合成资源的普通byte-vocab使用0–255域；v2具体added用例ID已分配到300以上，避免与byte symbols冲突。证明中的ID1/2仅表示抽象优先顺序。

不支持kind时adapter必须非零退出，不能跳过。没有真实资源时`real-or-synthetic`可先做synthetic，但真实resource那一栏仍BLOCKED。

## 14.3 生成与冻结

```bash
python tools/generate_sessions.py --recipes data/session_recipes.json \
  --out-dir "$NEW_FIXTURES"
```

生成器按request JSON的保序紧凑序列化计算SHA256，附`provenance=SYNTHETIC_NOT_PRODUCTION`、recentassistant逻辑计数。该计数不是renderer的H，需离线测量实际H/Q。不能因为fixture名`prod_h20`就断言实际hint=20。

`data/corpora/cpp_code.txt`沿用语料类别名，但文本是Java示例；目的为用户Java工作形态，不是C++编译测试。rawmetadata记录语言，避免报告错误归类。

## 14.4 归一化前端结果

```json
{
  "case_id": "CASE-ID",
  "input_sha256": "64位小写SHA256",
  "resources_sha256": "64位小写SHA256",
  "kind": "rendered",
  "status": "OK",
  "semantic": {
    "token_ids": [],
    "stable_prefix_boundary": null,
    "turn_rewrite_boundary": null,
    "user_turn_boundary": null,
    "checkpoint_hints": []
  }
}
```

此处空tokens只是schema示意，不是合法boundary案例。ERROR用`error:{phase,class,message}`，不要输出semantic占位。prepared类型还要求token_types/positions/rope_delta/identity/starts_in_reasoning/rendered_sha256；count类型要求count。两个可执行来源记录放外部manifest，不把不同binaryhash混入semantic比较。

运行`python tools/compare_frontend_results.py "$ORACLE" "$CANDIDATE" --output "$DIFF"`。helper拒绝缺字段、input/resource不同、重复case、缺失配对；只输出首差字段路径。它只比较提供的结果，不验证这些JSONL确实来自产品，G0/T02负责来源。

## 14.5 各工具的边界

| 工具 | 会做 | 不会做 |
|---|---|---|
|check_source_pin.py|本地git完整pin/subject/blob/range核验|不会fetch/reset/certify部署overlay |
|resource_fingerprint.py|六本地资源fullSHA与组合identity|不提取artifact，不用旧official allowlist |
|scan_semantics.py|有限earliest-ID词法模型/随机cut验证|不做真实NFC/BPE/Qwen模型推理 |
|generate_sessions.py|确定性合成请求/manifest|不校准tokens，不伪装生产 |
|calibrate_fixtures.py|验证提供的测量身份及P+budget|不实际编码、不提交HTTP |
|compare_frontend_results.py|归一化结果精确比较|不替代独立oracle来源审计 |
|summarize_bench.py|严格配对性能输出|不自动批准G4或部署 |
|analyze_logs.py|schema20元数据统计/时间union|不从工具数自动判客户端因果 |
|audit_review_assets.py|解析附件保留行/哈希/证据缺口|不重跑节点29 |
|validate_pack.py/self_check.sh|文档链接/JSON/任务DAG/manifest与helpertest|不证明产品实现 |

## 14.6 benchmark 结果

[schema](../schemas/benchmark-row.schema.json)规定mode取legacy/b0/b1/b0-b1，schema_version=2，metrics严格finite。`oracle_match`缺省或null时不能进入发布性能结论。输入、资源、编译lane、sampling/cohort/cache_kind应固定。CPU微基准cache_kind用none；此处cache不是GPU L1命中率。严格归一化row不能直接塞work计数或run_id：bench同时生成`OUT.work.jsonl`（按pair_id关联B/A/H/Q/局部工作）与`OUT.run.json`（编译器、采样、二进制身份）。raw/sidecar都必须保留。

## 14.7 新数据测量与权限

生成JSON不包含生产secrets；测真实数据前先取得授权，存受限本地目录，公开报告只留hash/shape。rawinput和oracle结果可包含用户内容，不能作为常规request_done日志增加字段。未授权无法完成真请求回放时，清楚写synthetic验证，不补造1000条真实golden。
