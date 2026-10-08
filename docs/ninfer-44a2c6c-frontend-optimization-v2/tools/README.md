# 辅助工具使用

在解压包根目录运行。Python3标准库，无第三方Python依赖，不需要GPU。`self_check.sh`只检查文档包，绝不改生产。shell脚本须有bash。

```bash
bash tools/self_check.sh
python tools/scan_semantics.py --seed 20260925 --iterations 20000 --output /tmp/scan-check.json
python tools/audit_review_assets.py --output /tmp/review-audit.json
python tools/generate_sessions.py --out-dir /tmp/ninfer-v2-synthetic
python tools/check_source_pin.py --repo /path/to/your/ninfer-checkout --output /tmp/source-check.json
python tools/resource_fingerprint.py /path/to/extracted/resources --output /tmp/resources.json
```

最后两个路径需替换为真实本地目录；工具不会去下载或猜资源。

严格配对输入输出格式见[14](../docs/14_FIXTURE_FORMAT_AND_HELPERS.md)，性能schema见[benchmark schema](../schemas/benchmark-row.schema.json)。`calibrate_fixtures.py`对有request的输入重算payloadhash，同时拒绝同batch混合资源；CPU_STRESS/CPU_ONLY即使长度符合也不开放HTTP。没有request正文的输入只能验证providedhash一致，不能宣称正文已核验。

review-assets里的原始gen_prodshape.py依赖未提供raw语料，不是v2默认生成器。build_review_bench.sh编译调查原型而非产品；成功不能替代G1/G4。原型的B0支路省略部分assert，需谨慎解释。

所有工具以非零退出报告输入格式/身份错误，缺失值不补0；日志摘要只提供ANALYSIS_ONLY。报告保存到本包目录外，可保持MANIFEST校验不变。
