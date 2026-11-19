# 交付验证范围

日期：2026-11-15（Asia/Shanghai）。这是文档包的质量记录，**不是引擎验收回执**。

## 已实际完成的检查

- 固定7个仓库的源码/标签身份；TensorFold annotated tag已解引用，Strata app/control tag与engine build分开。
- 9个关键源码文件本地SHA256与source_lock逐一一致；这绑定源码字节，不证明其在GPU执行。
- 3个旧ZIP的SHA256与LINEAGE一致，未覆盖旧包。
- JSON可解析、无重复键；5份模板保持TEMPLATE_NOT_EXECUTABLE、批准额度0、运行测量null、默认关闭、source/deployment未绑定。
- 独立机械核验检查Markdown相对/引用式链接、固定GitHub代码SHA格式、16个Task与DAG、17个Case及预算/门槛一致性。
- 独立技术审阅检查历史重复、q/RNG、skip/catch-up、terminal input rows、H2字节/矩阵维度、样本单位和observer-off原则；发现及修订见[REVIEW_RESOLUTION](REVIEW_RESOLUTION.md)。
- 仅保Markdown、JSON与文件校验清单，不含源码clone、模型、二进制、可执行引擎工具或用户私有prompt。

## 封包完整性

`MANIFEST.sha256`记录除其自身之外所有交付文件的字节hash；它不证明来源声明真实或运行时功能正确。最终封包还检查ZIP CRC、条目路径无越界/重复以及条目字节与manifest一致。

用户可在解压后的包根验证：Linux用`sha256sum -c MANIFEST.sha256`，macOS用`shasum -a 256 -c MANIFEST.sha256`。对ZIP可用`python3 -m zipfile -t <ZIP文件路径>`；这些是完整性检查，不会运行文档里的未来CLI。

## 明确没有验证

- 未执行R0–R4未来CLI/CPU合同测试；这些工具尚未由本包实现。
- 未构建或运行YASAKANI/OSAKANA/TensorFold/NInfer/Strata；GPU/模型/服务/生成请求/远端写入均0。
- 未独立复现作者benchmark，没有本轮4090 tok/s、质量分数或性能CI。
- 未获得当前用户部署/真实轨迹/hidden，不将历史b0/P4/作者模型结果代替。
- 未运行浏览器版Markdown/Mermaid渲染，也未逐条联网重开全部固定URL；已读取的源文件与metadata身份单独在source_lock记录。

后续采纳资格仍必须按[测试协议](../docs/10_TEST_PROTOCOL_AND_GATES.md)与明确授权执行，不能引用本文件将NOT_RUN改为PASS。
