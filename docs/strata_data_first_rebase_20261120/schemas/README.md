# Schema 使用边界

本目录的两个 JSON Schema 为 Draft 2020-12，属于**拟新增的证据附件**，不是上游 API schema，也不是已有四合同的替代品。

| 文件 | 已约束内容 | 仍需 P1 代码/夹具约束 |
|---|---|---|
| `measurement_event.schema.json` | 封套字段、枚举、生产者序号、有界名字、可用性及缺失原因；occurred 必须有单调时间/时钟域 | 每类 event 的 payload allowlist/单位/scope/字段个数之外的字节上限，敏感内容，ID ownership、seq 连续、epoch、clock 映射、丢失区间 |
| `workload_signature.schema.json` | 模型/量化/KV/route 的可空结构、形状数值类型、覆盖状态 | 量化/布局与 kernel 的实际兼容性、issued rows 分母、route 原件、未知原因完整性、runtime identity 真实存在 |

结构通过不等于事实正确、隐私安全或 GPU 可用。不能把任意键值塞进 payload 后以 schema PASS 作为入库许可。P1 在外部输入/持久化边界实现逐事件字段登记表；内部已成立的契约不再堆重复检查。

## 两个例子的含义

- [measurement_event.synthetic.json](../templates/measurement_event.synthetic.json)：人工构造的7-token commit，用于说明一次commit不等于7个独立token时间戳；`evidence_class=SYNTHETIC`。内部 `availability.status=OBSERVED` 仅表示“该夹具中给定此值”，绝不能导入真实测量集。
- [workload_signature.proposed.json](../templates/workload_signature.proposed.json)：尚未绑定的设计卡，所有实际模型与route均为空。不是默认Flash-Next已命中某kernel的证明。

真实证据应同时要求数据来源、runtime绑定、观测权限、完整性与语义门；参见[05 数据模型](../docs/05_DATA_MODEL_AND_MEASUREMENT.md)、[19 P1](../docs/19_PHASE_TASK_PLAN.md)、[20 负例](../docs/20_ACCEPTANCE_TEST_MATRIX.md)。

## 静态检查与运行验证分开

本轮做了schema自检、例子正例和几项封套负例，具体回执见[25](../docs/25_PACKAGE_VERIFICATION.md)。它们不覆盖未来50个实施测试用例。未来生产者若新增event，要更新登记表、对应fixture、adapter版本及兼容迁移，不能只放宽`additionalProperties`。

不为执行本包而自动安装依赖；有现成`jsonschema`可用时用Draft202012Validator检查，缺依赖先报告或按当轮开发授权在隔离环境补齐。不要对上游API响应直接套本附件schema。

