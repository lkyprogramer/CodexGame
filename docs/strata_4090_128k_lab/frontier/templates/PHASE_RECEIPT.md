# Phase / Task回执

标识、时间、实现者、独立Reviewer、独立Validator：待填。

| 项 | 证据及状态 |
|---|---|
| 前置门与有效旧证据 | NOT_EVALUATED |
| 实际变更文件、diff、build/config身份 | NOT_RUN |
| 最小测试命令、退出码、原件 | NOT_RUN |
| 负控制是否真正失败 | NOT_RUN |
| GPU启动/请求/墙钟消耗 | NOT_RUN，不填0表示测过 |
| 资源、数值、性能、质量各门 | 分项填写 |
| 原始失败、未执行、偏离与未知 | 不得省略 |
| 审阅问题及修正证据 | 待填 |
| 状态及唯一下一动作 | 待填 |

Phase成功才沿DAG成功路径前进；任何终态直接P07清理，不把跳过Phase改成通过。Reviewer审逻辑/边界，Validator核原件/运行必要测试；两人重复同一摘要不算独立验证。
