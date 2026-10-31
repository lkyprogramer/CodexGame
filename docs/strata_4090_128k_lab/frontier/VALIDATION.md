> 原作者交付记录，保留原验证时间与计数。合并后验证另见实验主目录 `reports/DOC-MERGE-20261030.md`；原始69文件身份见 `history/IMPORT_MANIFEST.sha256`。

> 2026-10-31生产随后按用户要求恢复：12:49 health HTTP200/loaded=true；12:50:44 active/running/enabled、NRestarts0，GPU由生产占用。回执在父目录reports/PRODUCTION-RESTORE-20261031.md；此前停机回执保留原时间，零候选收口不变，未追加推理或GPU实验。

> 2026-10-31最新收口：[Astra复核回执](reports/ASTRA_REASSESSMENT_20261031.md)。root离线复算一致，当前零合格候选，F02保持DEFERRED_NEW_EVIDENCE。文档、清单与历史保留检查见父目录workspace/frontier/astra-reassessment-20261031/PACKAGE_CHECKS.json及主包VALIDATION；无新增native/CPU/GPU测试或推理。下文原作者验证计数与NOT_RUN保持原时间范围。

> 2026-10-31 F03 CPU审计：[回执](reports/F03_TEST.md)。原cache4834、基线/原型各2068 host checks PASS；CPU性能筛查未过，NO_QUALIFIED_CANDIDATE关闭，GPU追加0。以下历史批次状态不倒写。

> 2026-10-31追加的实际P01B执行见[P01B测试回执](reports/P01B_TEST.md)和父目录主报告 `reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md`：三请求COMPLETE、候选资格INSUFFICIENT。下文GPU NOT_RUN仅描述原作者当时的交付验证。

# 交付验证

**验证范围：本次交付的文档、来源身份声明、离线Python工具与ZIP文件完整性。GPU/模型/目标机验证均为NOT_RUN。**

## 已执行的检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `python3 -B -m unittest discover -s tests -v` | 8个测试方法全部通过，exit0 | 离线区间/统计/拒绝分支/JSON/清单/文档政策行为 |
| `python3 -B tools/validate.py --root .` | PACKAGE_VALID，exit0；11个JSON、32个Task、12张方向卡 | 固定政策、完整SHA格式、相对链接、DAG无环且依赖存在 |
| `./run.sh validate`、`./run.sh help` | exit0 | 离线入口实际可调用，不包含live/deploy命令 |
| `headroom.py --input fixtures/headroom_synthetic.json` | RESEARCH_RESULT_ONLY，exit0；区间并集350ms，条件模型改善15.5% | 仅合成区间算术，绝非本机收益 |
| `paired_stats.py --input fixtures/p24_rounded_synthetic.json` | 预期exit1，PERFORMANCE_GATE_NOT_MET | 舍入合成数据中TTFT比约0.991756，decode比约1.044275、CI上界约1.068783；拒绝方向正确 |
| `verify_manifest.py --root . --manifest MANIFEST.sha256` | MANIFEST_VALID，69个文件 | 清单覆盖除自身外全部文件，无缺失/额外文件，逐项SHA256一致 |
| ZIP封装检查 | 成员集合、路径、CRC及成员字节与最终文件夹逐一比对 | 70个文件含清单本身；不含外部workspace/raw/密钥 |

最后两步在封装阶段顺序执行；任何内容修改均重新生成清单，并再次验证后封装。ZIP本身的hash不写入其内部文件，避免自引用。

## 测试的主要反例

- 重叠区间求并集，未知依赖或UNKNOWN区间不能晋级。
- 六对exact paired log bootstrap枚举46656次，配对/引擎/输入hash/实际输出数必须完整。
- 缺对、重复引擎、失败、非正/非有限时间、布尔冒充数字、非法JSON均拒绝。
- decode主指标快20%而TTFT慢10%的合成例必须拒绝，不能只检查decode与wall。
- 修改4%/2%门、固定顺序、context/温度/内存等政策值，及新增120秒清理预留、decode主指标、最多3对AA校准，都被负例覆盖。
- 缺失SHA、相对链接逃逸、任务循环/缺依赖、输出覆写、清单篡改/多文件/路径穿越必须拒绝。

测试包含多个subcase；8是测试方法数，不是硬件请求数。工具会验证格式与声明，不能证明调用者提供的预登记、hash、因果或fresh-engine声明真实。

## 内容审阅

三条独立审阅线分别检查历史证据/统计、Maya/Edge0、内核/KV/SM89；修正及范围见[作者审阅记录](reports/AUTHOR_REVIEW.md)。64个旧编号和原标题与冻结atlas一致。全部74条公开代码/官方文档来源记录与93个已取读用户仓库文件的身份见[sources](sources/EVIDENCE_INDEX.md)。公开源码为定点审查，不称整仓穷尽审计。

最终目录含51份Markdown、11份JSON、6个Python文件及1个shell入口；再加MANIFEST共70个文件。阶段执行和候选状态仍为PLAN_ONLY/无硬件资格。

## 没有验证的事项

- 未恢复用户目标机上的原始模型、P6 port/构建原件、完整P24 raw数据或13项保护文件。
- 未编译或运行Strata候选，未执行CUDA、GPU、CPU推理、memcheck或热测试。
- 未建立新性能收益、质量非劣、六项长检索通过、稳定warm fixed2048探针或全天热稳定。
- 未改生产、未升级引擎、未推送GitHub、未部署；生产inactive等信息仅是用户/仓库历史报告。
- `tools/frontier/*`live适配器属于P00/P01的计划任务，当前包只提供接口与复用合同，不存在假返回PASS的一键实现。

P24示例采用报告舍入数和合成绝对量，仅检查方向/门控，不能冒充原始数据独立重算。本次离线验证成功不改变这些限制。
