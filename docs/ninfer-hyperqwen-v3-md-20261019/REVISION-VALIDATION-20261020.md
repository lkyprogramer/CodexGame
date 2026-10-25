# 2026-10-20 方案修订验证

> 本页仅记录其原日期的历史检查；2026-10-21当前文件/任务/断言数量以[最新修订验证](REVISION-VALIDATION-20261021.md)为准。

对象：本目录现行Markdown方案，不是NInfer产品二进制。修订依据是主审查报告，当前执行范围BASELINE_ONLY；实际baseline推进由run证据记录。此页不将原2026-10-19 ZIP校验沿用为新目录验证。

## 验证范围

核对现行内部链接、registry唯一JSON围栏、full/e1_w6/e1_w8依赖闭合无环、任务与具名断言镜像、全文件MANIFEST字节/SHA以及previous-v2/inputs修订前后原字节。所有优化/集成任务保持PENDING，P6合格commit保持null，未把baseline写成phasegate。

本次实际执行 `python3 /tmp/check_ninfer_docs.py` 及独立的MANIFEST/INDEX逐文件校验；临时检查脚本仅在本地验证方案，没有执行产品代码或历史围栏脚本。

| 检查 | 实际结果 |
|---|---|
| Markdown目录 | 282份，新增baseline合同与本修订验证；INDEX逐文件列全 |
| 内部链接 | 去除代码围栏后1450处本地链接均存在 |
| 历史原件 | 修订前后192份previous-v2/inputs文件SHA256完全相同，未改历史原件 |
| full DAG | 103节点=87task+16gate，闭合/无环 |
| e1_w6 DAG | 67节点=56task+11gate，闭合/无环 |
| e1_w8 DAG | 74节点=62task+12gate，闭合/无环 |
| 任务/断言镜像 | 52个H任务的interface/implementation/tests与registry一致；256条唯一ID与矩阵一致 |
| 状态/范围 | 全部task/gate保持PENDING；qualified_p6_commit=null；BASELINE_ONLY且optimization_implementation_authorized=false |
| MANIFEST | 除自身外281份Markdown的实际bytes/SHA256逐项匹配；目录/清单无遗漏 |

当前DAG未解除P6→H0、H5→H6生产gate。本次B29测量前置独立于H0优化实施，不改变原依赖或伪造scope/gate资格。上述PASS只属于文档一致性与原件保全，不是CUDA/模型或完整baseline通过。

## 未验证

本文修订未执行远端操作、NInfer构建/CUDA测试、BO/P6重建、完整baseline矩阵或Pi回放、优化实现/发布。与其他worker并行执行的实际baseline由ROOT汇总，本文不冒认它们的结果。

## 同日runtime补正的最小复核

再次执行现行链接/registry/task-matrix/DAG及MANIFEST检查。容量、计数与cold控制已按plans/05的源码依据修正；正式core明确original argv、actual-cache/gaps，不启no-prefix-reuse。previous-v2/inputs仍保留全部原字节。此补正也不代表已运行精确容量边界、正式cold矩阵或20真实Java闭环。
