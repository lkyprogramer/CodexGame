> 历史实验规范与记录。后续探索的当前阶段见 [NEXT_ACTIONS](../plans/NEXT_ACTIONS.md)；本文原口径用于解释原报告，不覆盖 frontier 新阶段合同。

# 开发、运行、报告闭环

## 命令与状态

`init`生成本地配置；`doctor`只读盘点；`bootstrap`建立冻结base；`qualify`检查前提；`prepare`抓取PR固定head、导出diff、建立从base起步的候选worktree；`ai`调用配置的外部开发器或输出TASK路径；`build`构建；`noise/run/scenario`只在显式execute下使用GPU；`stats`重算现有结果。

正常状态流：PREPARED → NEEDS_AI_PORT → READY → BUILT → GPU_QUALIFIED → SCREENED → HOLDOUT → ADOPT_CANDIDATE。允许分支：ALREADY_UPSTREAM、NOT_APPLICABLE、NO_MECHANISM_BENEFIT、BLOCKED、REGRESSION。没有“自动合入生产”。

## 外部 AI 适配

`agent_command`是用户选定的程序argv，不是shell字符串：

```json
["/absolute/path/to/your-agent-wrapper", "--task-file", "{task_file}", "--cwd", "{worktree}"]
```

包装器如何把文件交给具体AI由用户现有工具决定；不预设某一CLI版本、API密钥或无限审批。命令继承用户凭据但不写入报告。给AI的TASK明确禁止生产修改与GPU并行。即便外部AI有更大权限，本包的文字约束不等于操作系统沙箱，建议单独低权限开发账号。

无适配器时，`auto`停在TASK，不返回假成功。可直接在现有AI终端读TASK，开发后运行build/run。

## 源码审计模板

| 原PR要点 | 冻结main对应符号 | 状态 | 最小移植方式 | 测试 |
|---|---|---|---|---|
| 功能/结构一 | 文件:函数 | absent / equivalent / partial | 保留/替换/不移植 | 失败前后证据 |

`git apply --check`只是文本适配提示；合得上不证明语义兼容。`mergeable=false`也不是无法移植。main与PR可能都修改同一函数不同职责，按行为重新实现，而非退回旧函数整体。

## READY与开关

每个PR都要求完整off/on对照和真实启动回执。#3517原PR没有全局关闭开关；#3711原`STRATA_SLOT_SHUTTLE`不能关闭park复用的全部变化，因此要加明确的实验master gate。这些是本实验新增，不应描述成官方已支持参数。

启动回执应来自实际选中路径，至少包含PR号、enabled、fallback reason、关键预算。仅环境中存在变量不能算启用。被硬件/模式guard跳过时输出NOT_APPLICABLE。

## 一次实验

1. 核实固化资产与原配置hash。
2. A0/A1/B的配置差异审查；CPU/GPU不相关开关一致。
3. A/A噪声控制；其结果是测量系统的噪声，不是优化。
4. smoke先跑，失败停止；长测与Java隔离环境准备后再full。
5. 默认5轮，每轮base-off-on或on-off-base；分别重启，保存日志与GPU/RAM遥测。
6. 固定题目和冻结历史；不要使用A生成的更短答案替换B下一轮输入。
7. 统计、专项机制核实、复核异常样本。
8. 留出真实Pi任务，不自动发布。

## 运行参数映射

`common`的配置对base/off/on均生效；例如为了某项机制测试建立小缓存profile，三态必须同预算。off/on的差异只能是该PR功能。模型、KV、context等敏感项不允许通过READY临时覆盖，必须另建明确profile并重新生成/验证题集。

DFlash2从MTP切换属于特殊算法比较，不是普通环境开关：先完成生命周期与服务协议支持，单独登记draft模型、内存和接受率，再使用同一target、相同实际expert容量的隔离对照。通用runner默认禁止通过READY替换`--mtp`，避免误用；专项任务明确要求实现受审核的drafter adapter再运行该实验。
