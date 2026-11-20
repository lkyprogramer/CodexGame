# 25｜文档包静态验证与交付范围

状态：**DOC_PACKAGE_STATIC_PASS / INDEPENDENT_REVIEW_PASS**。以下是本轮实际完成的文档与结构检查，不把未来实施测试标成已运行。

## 本轮的验证对象

- Markdown相对链接、引用式链接定义、代码围栏与文件清单。
- 全部JSON可解析；两份Draft2020-12 Schema自身有效；两个示例的正例与封套负例。
- 来源SHA/摘要格式、固定版本、runtime未知项、候选未取得GPU资格。
- 预算合计与授权零值、Phase顺序、旧失败保持、绝对质量与截止条件。
- 独立语义review；最终逐文件SHA256清单和ZIP内部CRC/成员一致性。

静态JSON Schema只验证其规定结构；payload字段语义、时钟关联、真实GPU状态、隐私allowlist等仍是未来P1的任务，不能用本轮检查代替。

## 本轮已完成的检查

| 项目 | 实际结果 |
|---|---|
| 文件与内部链接 | 30份Markdown、12份JSON；89个相对链接有效；引用定义和代码围栏闭合 |
| 外部来源 | 217个去重链接已编入文档；这是引用清单，不宣称逐一重新联网检查217个页面 |
| JSON / Schema | 12份JSON可解析；2份Draft2020-12 Schema自检通过；2个示例正例通过 |
| 封套负例 | 8项被拒：缺失原因、发生时间、时钟域、额外封套字段、负序号、payload超64键、非法事件名、负物理形状 |
| 来源完整性 | SHA/digest格式检查通过；研究scratch中7个固定Strata源码快照重算Git blob均匹配来源；不把这些当二进制/GPU校验 |
| 预算 | 所列P2-L0/P3可选段14引擎、45请求、14400 GPU秒合计一致；已批准/已消费均0；source-build额外等价门与P5-AA/AB分别为0预算 |
| 独立review | 数据优先、构建身份、L2对照、W09内容边界、绝对质量、在途截止、AA前置依赖等问题修订后复核通过 |

其中8项负例只检查现有封套schema，不是50个未来实施用例已执行。清单与ZIP完整性在最终打包阶段另行检查，不以schema通过代替归档校验。

## 本轮明确未执行

Strata/NInfer源码改造或构建、上游/旧Lab测试、50项实施验收、GPU正确性/性能、真实任务质量、线上部署、任何用户服务启停。本轮模型请求数、GPU实验数、生产修改数均为0。

## 校验方式

包中MANIFEST.sha256覆盖除其自身以外的全部成员；解压后可在本包根运行`sha256sum -c MANIFEST.sha256`（macOS可用`shasum -a 256 -c MANIFEST.sha256`）。这只验证文件完整性，不验证上游声明或实验结论。

实际静态结果记录在[evidence/package_validation.json](../evidence/package_validation.json)。后续实施另写IMPLEMENTATION_RECEIPT与RunEvidence，不能覆盖本轮DOC_PACKAGE记录来伪造硬件已验收。
