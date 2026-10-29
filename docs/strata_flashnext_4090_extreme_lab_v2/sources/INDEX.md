# 证据与来源索引

- [LOCK.json](LOCK.json)：执行4b9、审计41cf、历史A0、release与12个PR head；commit固定，不随main漂移。
- [FRESHNESS_DELTA.md](FRESHNESS_DELTA.md) / [blob身份](freshness_blob_identity.json)：最终上游刷新差异；关键目录同tree object。
- [PR状态](pr_status.json)、[PR3871刷新](pr3871_fresh_status.json)：状态只代表取证时点。合并状态不等于机制完全缺失。
- [REFERENCES.json](REFERENCES.json)：当前研究正文引用的URL及反向文档列表；不是“全部读过论文数”或“实测引擎数”。
- [CATALOG_ALIASES.json](CATALOG_ALIASES.json)：64方向的source短ID解析；DONOR_Dnn/Qnn对应07文档同名节。
- [donor研究](../docs/07_DONOR_RESEARCH.md)：18组深入机制来源、85条固定/官方来源定义及许可边界；另见[通用引擎官方文档对照](../docs/11_GENERAL_ENGINES_AND_EXCLUSIONS.md)。
- [内核审计](../docs/08_KERNEL_SOURCE_AUDIT.md)：真实调用链、36条低层候选及固定行号；不要将数量与64方向直接相加，两者有映射重叠。
- [history/reports](../history/reports/DEPLOY-A0-EXACT6-20261025.md)：用户附件七份原始报告；无原始trace，结论标H而非新实测。
- [本地测试](../evidence/final-package-tests.txt)：只验证本包工具，不验证Strata性能。

pr-diffs中保留已审PR文件差分，供离线阅读；实施时从固定head取完整原diff并对最新执行基线语义移植。不要自动apply缓存的patch。README/官方网页声明和作者跑分都不能单独证明本机收益。

## 证据等级

H=附件历史目标机报告；S=固定源码；P=官方论文/文档/作者实验；L=本轮本地工具测试；I=有前提的工程推断。数字必须说明属于哪级。不同硬件/权重/采样/上下文不可直接换算。
