# 本次交付的验证记录

日期：2026-09-24。范围：**文档集合及辅助工具**，不是NInfer实现验收。

## 已执行

| 检查 | 结果 | 证据/范围 |
|---|---|---|
| 固定提交源码审阅 | 已完成相关前端范围 | source-lock固定15个来源条目；通过GitHub连接器读取指定commit，不以main代替 |
| 辅助工具单元测试 | 19 tests，0 failures | `helper-tests.txt`；配对/缺测/非法值/错误保留、链接/DAG、只读Git验证、fixture确定性 |
| Python语法检查 | 通过 | tools及tests全部用ast.parse检查 |
| 合成数据再生成 | 8/8一致 | 同seed再生成，和data/generated_sessions逐字节比较；共32条输入 |
| 对抗数据映射 | 86/86覆盖 | adversarial_cases与test-matrix的case_id集合相同 |
| 文档/JSON/依赖/链接 | 通过 | `package-validation.json`；该文件为结构检查，最终完整性用MANIFEST.sha256另验 |
| ZIP完整性 | 最终打包时验证 | ZIP CRC和解压后manifest验证；不代表任何GPU门 |

## 未执行，不能宣称通过

NInfer源码修改、原仓C++/CUDA编译、真实tokenizer golden导出、边界新算法实现验证、4090热续写基准、Pi任务回归、诊断overlay审阅、生产shadow/canary/切流与回滚。

`templates/gate-report.json`中G0–G7因此全部保留NOT_RUN。source-lock是远端固定源码依据，不证明现网prepare-detail镜像中的本地文件；用户未提供该镜像对应diff及原始1617条请求。本包辅助工具用临时本地Git仓验证版本检查逻辑，没有把这种测试冒充对用户原仓的实际验证。

源码发现是可核对的：旧encode_rendered_chat对每个语义边界重新编码整个前缀。但其在每条生产tokenize耗时中占多少，仍须T01的主编码/边界编码计数实测，不能从汇总表编造百分比。

用户报告分档合计1616而总数1617，差1条在数据与检查warning中原样保留；不擅自归入遗漏的8–32K档。
