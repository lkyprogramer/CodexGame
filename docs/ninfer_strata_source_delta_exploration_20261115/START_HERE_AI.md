# AI 执行入口：先淘汰，再实现

> 当前是执行规格，不是执行许可。开始前读根 [AGENTS](AGENTS.md)。所有命令都在未来获准的隔离工作区运行；本包不含引擎补丁。

## 最短路径

1. 读 [历史台账](docs/01_HISTORY_AND_NO_REPEAT.md)，将本轮主张逐一标为“已实现 / 已测关闭 / 已规划 / 新机制 / 未绑定”。
2. 按 [R0](phases/R0_BINDING.md) 填 `templates/ExperimentSpec.json` 的副本。锁当前实际树、二进制、模型与会话合同；缺任何关键身份即停。
3. 从已有授权且脱敏的真实 token 轨迹判断 D1 是否有用。不要先搭 OSAKANA，也不要先跑更宽窗口。
4. H2 先核 head-only 关键路径和 sidecar 预算；不要用 P14 的 9.5% 当当前可全部优化比例。
5. K-PAIR 仅查 P3/当前分派；M0 仅核上游修复/当前部署，不当新性能实验。
6. R1 结束，最多选择 D1 或 H2 中的一个进入实现。两者均无机会时，以 `NO_QUALIFIED_CANDIDATE` 交接；这是成功收口，不是任务失败。

## 文档约定

路径基准 `LAB_ROOT = docs/strata_4090_128k_lab`，`NINFER_ROOT` 和 `STRATA_ROOT` 是 R0 中绑定的隔离源码目录，不是环境默认值。后续工具路径相对于 LAB_ROOT，未实现的新接口均明确标出；不能把本文命令当现成可用脚本。

计划新增的窄工具目录为 `tools/frontier/donor_delta_20261115/`，只做读取、归一化、离线比对与合同检查；由原控制器调用，不能自行开引擎。既有等价工具优先复用，记录 `reused_from`，不要新建同功能脚本。

## 当前不可自动填的输入

| 输入 | 为什么必需 | 缺失时动作 |
|---|---|---|
| 当前服务 build / engine SHA / binary hash | 公开 b0 不是当前生产证明 | `BLOCKED_IDENTITY` |
| P3/P4 最终源码及部署状态 | small-T、codec、export 修复可能已覆盖候选 | K-PAIR 保持源码缺口 |
| 同 tokenizer/model 的真实编辑 token trace | 文本相似或合成重复不能代表实际机会 | D1 停在机制规格 |
| 当前真实 draft hidden / head 分项成本 | 换合同的 P14、随机向量不可代替 | H2 停在资产可行性 |
| 完整采样 / continuation 合同 | proposal 与恢复正确性需要 | 默认仅 greedy 或退原路 |
| 用户批准的硬件窗口与预算 | 文档包不授予 GPU 权限 | `BLOCKED_AUTHORITY` |

## 每次交接必须回答

- 这次实际改了什么，旧路线中哪一部分保持关闭？
- 什么已验证，什么只是源码存在，什么仍是 null？
- 全部失败和停止原因在哪里？是否仍有未结授权/身份缺口？
- 当前生产保持何种 baseline？默认开关是否仍关？
- 接手者执行哪个 Task、读哪份证据，哪些动作不得做？

完整执行顺序见 [DAG](docs/11_PHASES_TASKS_DAG.md)；独立审阅模板见 [PHASE_REVIEW](templates/PHASE_REVIEW.md)。
