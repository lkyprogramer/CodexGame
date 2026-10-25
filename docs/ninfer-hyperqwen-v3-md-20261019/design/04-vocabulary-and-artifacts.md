# 草稿词表：优先优化数据，不先增加推测层数

## 现状及不能照搬的假设

V2固定NInfer `Variant::draft_head_rows=131072`。HyperQwen报告40K head和新数据覆盖优势，但HQ06同时说明旧列表CJK极少，注释还出现与HQ01不同的语料规模/覆盖率。不能直接拿97.5%作为中文/Java保证，更不能把ID类别占比当实际输出频次覆盖。[HQ01/HQ06；V2 N02]

## C19：候选profile与数据划分

候选行数固定为 `{40960,65536,98304,131072}`，对应40K/64K/96K/128K标称。以实际有效ID和tensor描述为准，Target输出域和padding行不混淆。

使用真实模型**输出token ID**为主校准：中文说明、Java源码、测试日志解释、工具调用JSON、英文推理/文档分别分桶。train/calibration/locked-test以完整项目或会话划分，不能将同文件相邻4KB块分到训练和测试；原始工具日志/私有源码不写入本包或公共仓库。锁定测试不得回灌词表选择。

统计：每桶token频次覆盖、每个draft位置的准确率、连续3/5/7位置全部在词表内的比例、首次miss位置、端到端roundwall。单个覆盖率p的p^K只作独立性假设的解释，不作为真实链接受率预测。

必须从实际raw token IDs统计：byte-BPE的部分UTF8字节token可在后续token拼成合法字符串，不因单token解码失败而丢弃。必选special/control token按实际tokenizer契约确定，合法不代表全部无成本加入；其行数记预算。

## C20：独立只读proposal artifact

新增离线工具 `tools/convert/qwen3_8_27b/build_proposal_head.py`，输入原Target `.ninfer`、合法ID列表、校准manifest；输出 `proposal-head.ninfer`，不修改原Target文件，不经文本GGUF重新量化Target。

manifest必须包含：schema版本、target artifact指纹、tokenizer指纹、合法token域、row→token映射、row-count、量化/layout标识、tensor checksums、校准集ID、生成工具版本。写tmp→校验tensor/映射→原子rename；索引/manifest最后发布。重复ID、paddingID、负ID、非法rank/shape、缺scale、截断文件均拒绝。

NInfer侧在 `src/targets/qwen3_8_27b/impl/load/proposal_head_bindings.*` 建typed只读view；只允许上述closed profiles，启动一次绑定，旧head保留可回退。不能对每请求搬动head行或在graph中分配。复用已有低位proposal算子；如果格式需要额外repack，只能离线转换，不能在请求路径发生。

## 容量与选择

只算4-bit codes：131072→65536行减少65536×5120/2=160MiB；131072→40960减少220MiB。scale、descriptor、映射、对齐和同时保留旧head会改变实际净节省，必须live账本确认；不能把理论节省直接当DFlash2可用空间。

默认profile采用规则：locked-test各关键桶覆盖不低于原profile **0.5个百分点**，Java/中文/工具调用质量通过，整轮每committed-token成本至少改善5%，且所有上下文档位无>3%退化。以上是建议采用阈值，不是测量结果。失败则保留131072；词表实验完整但无收益允许明确NO_ADOPTION，不重复造一个运行时动态词表系统。

## Target sampling资格

小词表只影响确定性proposal，实际q=delta而非head softmax；Target full-domain/processor/p保持原样。每个拟启用profile同时检查Target-greedy诊断及生产sampling支持/residual/状态合同，稀有目标token不在草稿表仍可由Target输出。校准以实际目标业务输出为依据，不通过切Target为greedy伪造覆盖/性能；相关筛选与最终holdout按plans/06，不将每profile自动扩成全部发布p95。
