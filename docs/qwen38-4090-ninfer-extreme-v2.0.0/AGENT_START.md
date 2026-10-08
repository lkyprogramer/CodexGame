# 执行AI入口

## 首要决策

本轮不执行旧Kern PoC，不从零重写引擎；冻结NInfer44a生产（262144、rk4v4-e8、MTP3、medium）作为基线与回滚点。候选profile的目标是**受保护200192 + medium + Java/Pi长期会话**上的实际收益，不是最短复制题峰值。200192是用户2026-09-09的明确决定（`docs/22 §1.1`），不是可以再往下让的软目标；生产本身不改。

## 阅读顺序

`docs/00` → **`docs/22`（实机复核事实与决策，冲突时以它为准）** → `references/CLAIM_AUDIT.md` → `docs/01`/`04` → `docs/03`/`05` → `docs/11`/`12` → `configs/tasks.json`。分支实现必须再读对应专题和task卡。原报告12含关键混杂解释，不能跳过。

## 第一次会话要完成的事

- 运行stdlib self-check（`bash scripts/self_check.sh`，74项），不装numpy/cargo。
- 读取Mac的Pi/Node/JDK路径（Pi在`~/.nvm/versions/node/v22.19.0/bin/pi` v0.85.1，不是`~/.pi/bin`）；GPU host只读preflight（不要把Mac事实当4090）。
- SHA核对生产artifact与源；新worktree，不改生产目录。把`docs/22 §2`逐项与preflight结果对照，差异即重新锁定。
- 权限已就位（`docs/22 §1.2`）：`sudo -n systemctl stop|start openclaw-qwen38-ninfer.service`免密、hhtele在`systemd-journal`与`docker`组、`~/qwen38-vllm/models`可读。**不要再申请任何权限扩大**（不改`RmProfilingAdminOnly`、不改`perf_event_paranoid`、不加NOPASSWD:ALL）。
- 明确授权：实验GPU会暂停现网，控制AI必须在外部服务。T01的真实维护演练要用户给时间窗口；没有批准先只做CPU准备。
- 创建`results/tasks-state.json`（初始空对象），从T00开始记录。不要修改configs/tasks.json原计划。

## 自主执行规则

按DAG推进，CPU独立任务可并行，共享runtime/采样变更单owner合并，GPU串行lease。每task先失败测试/负对照、最小实现、复核、commit、测该commit。新CLI case未实现返回77/NOT_IMPLEMENTED；CTest SKIP不得算PASS。不要为了“打勾”写只输出成功JSON的adapter。

T03只用数据决定投资分支：Suffix链延长v1（零bridge、W≤6）较小先做；DFlash2链的**第一道门是T07**（W8路径在184K的每轮额外耗时），T09/T10不得在T07性能数据出来前启动；DFlash2需要companion binder/精确q/完整状态事务/**会话持久化（44a对DFlash后端显式抛错，是新功能）**一起实现；prefill需d256适配；A4默认disabled。rk8@200192与DFlash2争同一块显存，T03输出的是二选一决策。任何选择记录decision.json的假设、证据、预计成本、停止门。

## 已发生过的误执行（2026-09-09，`output/qwen38-4090-compare/extreme_v2`）——不要重复

- 用未改动的44a二进制跑`--draft-tokens 5` 当作"Suffix v1"、用`--spec dflash`启动MTP制品当作"T07 W8"。两者都没有可测对象；正确状态是`BLOCKED: 未实现/未构建`，不是`否决`/`未过门`（细则见`tasks/T06 §什么不是v1`、`tasks/T07 §什么不是T07`）。
- 5 token输出、`reasoning_effort=none`、`temperature 0.2`、748/752 token缓存命中的HTTP探针被当作decode吞吐与A/A噪声样本。有效样本定义只有一处：`docs/12 §2`。
- 越过`tools/remote_guard.py`：用喂密码的`sudo-wrap.sh`、`pkill -f "ssh .*18030"`、容器名`ninfer-4090`占生产原生端口18030且无`qwen38.lab.run` label。sudoers已免密（`docs/22 §1.2`），候选走18041+label，guard才能接管清理。
- 在没有T00 `runtime-lock.json`/`memory-ledger.json`、T01演练、T02每轮遥测的情况下直接进入T03/T06/T07测量。没有AL分解的吞吐数字不能进任何门。

## 禁止事项

不覆盖旧模型、不merge上游master、不把W8说成原有small-T路径、不将rootcodec优化套给rk4、不把Sage>128错误绕过为两个softmax、不吞掉unsupported采样参数、不用未来completion生成lookup、不用不匹配的旧Java结果、不把用户凭据写入日志、不通过缩窗口（<200192）/去thinking/改题使性能门变绿、不把rk8与DFlash2同时塞进200192预算、不把exact rejection sampling和`/metrics`请求计数当成待建功能重写。

## 提交最终报告

报告必须包含实际实现的分支、未做分支、source/artifact/image锁、具体通过/失败项、每case真实计数、cold/hot/round/task四种时延、恢复smoke和状态、配对数与A/A噪声底。只有得到用户最终许可才改生产；当前旧NInfer仍是回滚点。
