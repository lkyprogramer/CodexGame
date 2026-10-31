# Strata 4090 / 128K 实验执行入口

先读 `START_HERE_AI.md` 和 `plans/NEXT_ACTIONS.md`。后续探索合同在 `frontier/`；旧 PR 专项、旧续测和根 sources/LOCK.json 仅在追溯原实验时读取。工具、历史报告、workspace 原位保留。frontier/P00 等编号属于新命名空间。阶段范围以当前用户指令和P00/P01回执为准；P00准备不授予P01 GPU实验或部署权限。

生产目录、配置、模型与Pi设置只读；GPU上下文总和不得超过131072；不自动停止生产服务。各PR独立worktree，关闭路径与原版先通过，再测试开启路径。不要把本包CPU测试结果当作4090验证，不要把未开发的PR写成已完成。

所有模型生成的代码（Java、Python 评分题等）仅在包内受限 Docker 流程执行，绝不在宿主机直接运行。真实工具调用必须受本轮白名单约束。遇到硬件/内存/源码差量不适用，交付可核查的NOT_APPLICABLE或BLOCKED，而不是移除安全门。

29 号机（192.168.10.29）额外规则：生产是 A0 + EXACT6 + 2026-10-26 上线的五个开关（`/home/hhtele/strata-0.2.3`，18343，见 `reports/DEPLOY-PROD-20261026.md` 与 `reports/DEPLOY-KVRES-20261026.md`）；**2026-10-26 09:44 起按用户同意停机测试**（21:38～21:41 只为 KVRES 冒烟启动过一次），恢复需用户发话；以后需要 GPU 独占的实验仍须先征得用户同意再停生产；实验只用 18089。不改 systemd unit、NGINX、`production-18343.sh`、驱动、CUDA 12.3；不装内核模块、不改 initramfs/GRUB/内核参数（CFG-UNLOCK 经用户批准的维护窗口除外）；不写 `/home/hhtele/strata-0.2.3` 和回滚树 `/home/hhtele/strata-0.1.43.1`；不运行 `./update.sh` 或其他更新器；不删除旧版本目录；不停用户未授权的共存 Docker 容器。任何 arm 都不得开启 `STRATA_STAGE_PIN` 或 `STRATA_ROUTE_RESIDENT`。不把 NGINX Bearer、SSH 密码、sudo 口令、Pi 的 `apiKey` 写进任何文件或 git。当前事实见 `docs/02_ENVIRONMENT.md`。
