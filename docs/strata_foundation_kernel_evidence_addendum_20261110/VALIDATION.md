# 本轮实际验证记录

日期：2026-11-10（北京时间）。这是交付物与CPU合成测试记录，不是Strata性能报告。

## 已实际完成

| 检查 | 实际结果 | 能证明的范围 |
|---|---|---|
| 原基础ZIP大小/hash | 162748 bytes；SHA256与来源锁一致 | 本次确实基于指定原件，不是凭记忆重建 |
| 上游force_check文件 | Git blob与SHA256锁定；SHA256再次核对一致 | probe作用于准确版本，不外推其他版本 |
| Python单测 | `python3 -B -m unittest discover -s tests -v`，最终50项通过，exit0 | 缩小JSON合同、包文件/链接/hash工具的已覆盖分支 |
| 上游离线反例 | `tools/probe_upstream_force_check.py --source <已审计文件>`，三项复现，exit0 | check输入前提缺口；未执行Engine/gen/score |
| 独立文档审阅 | 见[REVIEW.md](REVIEW.md) | 合同、边界、来源与计划的静态复核；非运行时资格 |
| 独立CPU复验 | 50项exit0；另验原4类恶意输入均被正确拒绝 | 只证明离线工具已覆盖边界，非产品parser集成 |

最终单测输出：[validation/unit_tests_final.txt](validation/unit_tests_final.txt)。初次45项输出保留在[validation/unit_tests.txt](validation/unit_tests.txt)。原始probe JSON：[validation/upstream_probe.json](validation/upstream_probe.json)。

开发时先运行测试，观察到预期的缺实现ImportError；基础实现后针对审阅新增顺序/分数/收据边界，7个新负例先失败，再补逻辑后45项全部通过。没有通过删除失败用例或放宽断言来获得绿色结果。

独立tester随后另以恶意输入发现4类遗漏：极大整数score抛OverflowError、float token与int token被列表相等混同、空/布尔预算被当零、1e999被JSON解析为Inf。新增5个回归先得到4 FAIL+1 ERROR，再分别修复并跑各自最小测试，最终完整50项通过；没有把这些离线helper缺陷称为Strata产品缺陷。

## 三项反例的确切含义

| case | 输入 | 上游输出 |
|---|---|---|
| missing_request | stock各r1/r2、candidate仅r1，每例8行 | PASS、requests=1、candidate=8、stock=[8,8] |
| short_coverage | stock各例8行、candidate各例2行 | PASS、requests=2、candidate=4、stock=[16,16] |
| one_stock_arm | 仅1份stock、每例8行 | PASS、requests=2、candidate=16、stock=[16] |

这里全部是人工`mismatch=False`行，只用100次bootstrap检查边界；不能与原6对正式收益统计混淆。CLI的单stock warning在源码中另行核查，probe调用的是纯check函数而非CLI。

probe只从精确hash源码的AST提取ceil8/binom_tail_ge/check三函数，未import上游完整module。脚本拒绝其他hash，且包内不分发上游完整源码。

## 本包工具实际覆盖与未覆盖

- 50项单测包括：覆盖/重复/重排、stock数与身份、路径/文本/scorer合同、缺emitted数组/错误token类型、非有限/有限非法分数/不可表示大数、tie与格式舍入、严格JSON/指数溢出、预算字段完整性与严格整数类型、局部链接/manifest负例、未锁定source拒绝。
- `contract_examples.py`没有真实TSV/meta parser，没有认证receipt/process/module，也没有graph、内存oracle或NCU importer；其成功名称带FIXTURE_ONLY。
- `validate_addendum.py`只验证本地结构、内部链接文件存在、JSON、固定锁和manifest，不联网验证外部URL、不核对每项技术事实，也不检查Markdown锚点语义。
- `MANIFEST.sha256`覆盖交付文件，不包含自身。打包后的ZIP CRC和逐文件hash在交付前另行复核；可用本包`--require-manifest`重复校验解压内容。

## 明确未执行

| 范围 | 状态 |
|---|---|
| Strata产品模块E0–E4开发 | NOT_IMPLEMENTED；本包是后续实施说明 |
| 真实TSV/meta、实际receipt集成 | NOT_EVALUATED |
| 独立小算子数值reference实现 | PLANNED；本包没有把toy JSON guard叫算子oracle |
| CUDA编译、PTX/SASS生成、NCU/Nsight/CUPTI采集 | NOT_RUN |
| 模型下载、加载、generation、微基准 | NOT_RUN |
| 4090端到端提升或新候选 | NOT_EVALUATED |
| 用户仓库/上游写入、生产部署、旧闭项重开 | 未执行 |

计数：engine starts=0、generation requests=0、GPU runs=0。所有旧FAIL/BLOCKED/CLOSED与零预算保留。不能用本文件声称foundation已经部署或监控已经合格。
