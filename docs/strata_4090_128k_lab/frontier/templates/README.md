# 运行证据模板

本目录是未来执行的填写合同，不包含目标机结果。JSON中的null表示未取得证据；不能以0、空字符串或随意构造hash替代。模板不得直接传入live执行器；先在包外新建campaign目录，填实际身份并经P00/P01验收。

| 文件 | 用途 |
|---|---|
| [PREREGISTRATION.json](PREREGISTRATION.json) | 限额诊断、矩阵、停止条件与实际授权引用 |
| [IDENTITY.json](IDENTITY.json) | 原始基线、二进制、配置、资产、保护读取时间 |
| [DATA_CONTRACT.md](DATA_CONTRACT.md) | REQUESTS/WINDOWS/DEPENDENCIES/MEMORY/RAW_MANIFEST字段 |
| [QUALIFICATION.md](QUALIFICATION.md) | 机制差量、因果、可省上界与候选选择 |
| [PHASE_RECEIPT.md](PHASE_RECEIPT.md) | Task/Phase独立review/test与前置门 |
| [FINAL_REPORT.md](FINAL_REPORT.md) | 结论、全量指标、失败、质量与限制 |
| [HAND_BACK.md](HAND_BACK.md) | 仅本轮资源清理、保护复核与归还 |

本包工具输入示例在[fixtures](../tools/README.md)，全部synthetic。这里的运行证据模板更宽，尚需未来adapter把经过审计的原件转换到离线计算器的严格schema，不能直接重命名文件冒充转换完成。

授权引用只记录已存在的用户指令/交接证据，不创造授权；把某布尔值改成true不允许启动目标机、部署或改生产。已有授权在同一会话持续有效，执行者无需机械反复询问。
