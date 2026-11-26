# v2.0 交付验证记录

**日期：2026-11-26，Asia/Shanghai。范围：文档、机器合同、来源身份与CPU辅助工具。**

目标4090、模型、Atomic构建、CUDA/Lean/Seismic及业务测试均未执行；没有服务修改。148项计划测试仍全部NOT_RUN，不能把下列文档检查计入TC/GX/AX/LX/UX/MGX资格。

## 1. 已实际执行的检查

| 项目 | 观察结果 | 证明范围 |
|---|---|---|
| 既有helper unittest | 9项通过，exit0 | 配对统计及只读调查工具的既有行为；GPU返回用fixture |
| Cache JSON Schema | 57项预期吻合：8正例、38负例、11语义边界探针 | 结构接受/拒绝；11探针被接受说明Schema未验证这些语义 |
| Kernel JSON Schema | 110项预期吻合：10正例、93负例、7语义边界探针 | 既有scoped proof/编译/执行字段的结构门；没有运行Lean或GPU |
| 原run/gate合同 | 11合成正对照有效；18历史负例及G99按预期拒绝 | 原模型身份、事实/gate分离、授权结构门未削弱 |
| v2 run扩展 | 42项预期吻合 | L/M任务枚举、唯一cache入口、PASS非空引用、旧别名拒绝 |
| 原合同保持 | gate、validation-policy、kernel Schema、两个helper及9项测试与v1.2字节一致 | 原阈值和基础工具行为没有变更 |
| 来源身份 | 新2DSD37新增文件blob核对；Magnitude49分支/58源码pin；CUDA Rust14文件delta | 静态来源身份；历史141文件审计仍绑定旧S22 |

完整具名结果见[package-checks](validation/package-checks.json)、[cache检查](validation/cache-schema-checks.json)、[kernel检查](validation/kernel-schema-checks.json)、[run/gate检查](validation/run-gate-schema-checks.json)、[新增run检查](validation/run-extension-checks.json)、[helper原始输出](validation/helper-checks.json)。合成PASS形状只在检查程序内存中用于测试Schema；它们没有成为实际run或gate。

全包静态检查结果在[document-checks](validation/document-checks.json)：任务及条件边无环、44任务/148测试引用完整、43专题、47登记来源/42源锁、JSON严格解析、Python语法、Markdown文件链接与围栏、shell片段仅做`bash -n`。精确文件/链接/围栏计数以该机器结果为准，不表示执行过shell片段中的工程命令。

## 2. 审查中修正的实质问题

1. token提交与压缩发布分开：已emit前缀不撤销；raw sealed保留到encoded发布与最后读者完成，pending和open tail同时计峰值。
2. graph metadata采用reader→update→replay事件链或独立generation；固定地址不足以证明同步。
3. 零suffix恢复明确next logits/readout与末token消费状态，避免重复forward。
4. 本地typed subrecord+目录与论文跨层TileStream格式区分，staging envelope按全部并发buffer和scratch合计。
5. request continuation绑定logical owner、resume generation及权威commit/effect水位；model-prefix不带另一请求私有状态。
6. 物理allocation、view和arena generation独立；同arena子view复用不能被旧ticket退休。
7. run唯一cache接口与必需artifact统一；L05研究组合测试按已选profile求值，L03功能恢复与L07服务soak分工。
8. 目录与record的哈希方向无环，持久状态与操作状态词汇明确，L00冻结wire而L01实现header。
9. 全包检查发现UX01–UX04的机器索引指向来源章40，而测试表在39；已修正并通过完整复验，验收要求未变。
10. Magnitude的未来回放只给miss/held对照；小Bélády gap不能单独否定预取。预取需真实stall、提前量、overlap、竞争和E2E证据。

这些是规范修订，不是已经复现或修复的推理引擎漏洞。两轮独立审查已在所审范围确认闭合；语义验证器及实际实现仍由后续任务交付。

## 3. 可立即复验

在解压目录运行：

```bash
python3 -B -m unittest discover -s tests -v
python3 tools/check_document_package.py
python3 tools/check_cache_schema.py
python3 tools/preflight.py --help
python3 tools/paired_stats.py --help
sha256sum -c PACKAGE_MANIFEST.sha256
```

`check_cache_schema.py`需要当前Python环境已有jsonschema；缺少时返回BLOCKED/exit2，不自行安装。`check_document_package.py`仅用标准库和`bash -n`，不执行示例命令。两个既有helper仍只依赖标准库。不要在此环境运行preflight后把所得机器清单当用户4090；真正清单属于现场T00。

上方复验覆盖包完整性、结构与helper。原run/kernel完整反例的具名观察已归档；本包新增cache检查器可重复生成57个合成结构案例。L01/T01/K01未来的真实artifact、事件、状态、数据来源、能力与授权语义检查尚未实现，Schema不能替代它们。

## 4. 外部证据与未来现场资格

Ghost外部CPU CI、历史CUDA Rust CPU/proof/GPU-less与Blackwell结果仍分列于原观察文件；新f35d6ccc的10条Actions success只是摘要。2DSD exact head查询0条Actions只是查询观察；不推断作者未本地测试。作者H800/H100/B200、Metal和其他显卡测量都不是目标4090结果。

后续仍需T00实机调查、选定资产构建、正式R3状态/数值/质量、DSpark拒绝取消、真实codec、SM89 kernel、长上下文与Pi/Java服务测试。单项5%、迁移10%、CI/p95/非劣、8h且200请求soak保持原合同。T12形成可审查候选；当前文档不授予G7生产切换权限。
