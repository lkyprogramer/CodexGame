# 数值输入完整性报告

- 合同：fixed-text-decode/v1
- expected set/model/tokenizer/scorer hash：
- expected request数量/ID digest：
- stock独立运行数量及实例引用：
- candidate引用：
- 每臂request集合完整性：
- 每请求位置范围与覆盖digest：
- 重复/缺失/未知位置、target错配数量：
- actual emitted-token receipt引用/hash、request/engine映射、完整结束标记；缺收据为FORCED_OUTPUT_UNPROVEN：
- forced输出一致性（不可由meta的期望ids自证）：
- TSV/meta schema与slice边界：
- logp域/top2排序与不同ID/同token同分数/margin定义/finite检查；预注册格式ε及推导：
- collector完整性及退出状态：
- guard状态/reason codes：
- 原checker版本、参数和原始结果（仅guard通过后）：
- 原状态/oracle/quality门结果引用：
- 限制与未支持的文本合同：

INPUT_ADMISSIBLE不是MODEL_CORRECT；原checker PASS不是整体采用PASS。失败不得删样或补样。
