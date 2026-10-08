# 证据分层、输入归档与隐私

## 1. 证据层级

E0：用户报告原文；E1：报告引用的raw结果；E2：同snapshot源码；E3：公开上游文档/源码；E4：本包CPU实际运行；E5：未来用户GPU实测。

本次主要依据E0/E2/E3，辅以附件报告12直接核对，不把未经统一复算的每份raw数据都叫独立复现。CPU工具验证属于E4，不替代E5。日志截图、模型卡headline、多个fork同表只能作为线索。

## 2. 输入保存

`input-review/`保留两份Claude报告和5份关键NInfer报告。常见credential形态经过redact；`references/input-provenance.json`记录原始与输出hash及是否变动。原ZIP和raw logs不复制到交付包。源码仅保存关键文件hash与读取位置，不把整个旧源树包装成新引擎。

`references/CLAIM_AUDIT.md`逐条列“原说法、核查、影响、如何验证”，保留被否定观点的来源，不悄悄改写Claude文字。

## 3. 真实轨迹导入

由T02从现有log_proxy的request事件导出请求body，**不包含Authorization或未来assistant答案**；已发生的历史assistant/tool消息是输入的一部分。每个独立session整体分到tune或heldout，禁止未来completion进入suffix索引。真实代码/思考不得自动发给Exa、GitHub或云训练；本机私有文件模式0600，分享的是结构摘要/哈希/统计。

数据清理改变token序列，应双方统一用同一清理版重新tokenize。不能把原日志tokens与脱敏后prompt比较得出cache错误。

## 4. 源码/量化 provenance

每次转换列源revision、实际shard哈希、converter commit、每object的hash和dtype；不信HF缓存.metadata能证明文件没被recipe覆盖。`.ninfer` inspector只是结构/目录审计，**不能证明数学格式或运行时binder兼容**。

## 5. 社区检索结论

X精确搜索未取得更强原帖，Reddit复查只得到历史镜像和重复fork表；所以本包的决策不建立在新的社交媒体速度断言上。外部主证据是上游DFlash2算法/制品合同、Suffix原项目、Sage源码以及NVIDIA文档；详见SOURCES。
