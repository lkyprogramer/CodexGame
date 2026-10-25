# Strata 4090 / 128K 实验执行入口

先读 `START_HERE_AI.md`，再读 `README.md`、`sources/LOCK.json` 和当前PR专项文档。

生产目录、配置、模型与Pi设置只读；GPU上下文总和不得超过131072；不自动停止生产服务。各PR独立worktree，关闭路径与原版先通过，再测试开启路径。不要把本包CPU测试结果当作4090验证，不要把未开发的PR写成已完成。

所有模型生成的Java仅在包内受限Docker流程执行，绝不在宿主机直接运行。真实工具调用必须受本轮白名单约束。遇到硬件/内存/源码差量不适用，交付可核查的NOT_APPLICABLE或BLOCKED，而不是移除安全门。

29 号机（192.168.10.29）额外规则：生产 Strata 当前已停止，机器在跑其他实验，**未经用户明确允许不得启动任何 Strata 进程或占用 GPU**。不改 systemd unit、NGINX、`production-18343.sh`、驱动、CUDA 12.3；不装内核模块、不改 initramfs/GRUB/内核参数（CFG-UNLOCK 经用户批准的维护窗口除外）；不写 `/home/hhtele/strata-0.1.43.1`；不占 18343；不运行 `./update.sh` 或其他更新器；不删除旧版本目录；不停共存 Docker 容器。任何 arm 都不得开启 `STRATA_STAGE_PIN` 或 `STRATA_ROUTE_RESIDENT`。不把 NGINX Bearer、SSH 密码、sudo 口令、Pi 的 `apiKey` 写进任何文件或 git。当前事实见 `docs/02_ENVIRONMENT.md`。
