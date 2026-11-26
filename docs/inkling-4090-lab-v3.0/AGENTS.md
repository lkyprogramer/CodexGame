# 执行合同（工程代理必读）

## 范围

在 4090 上把 Astral fork 移植到 sm_89，跑通 Inkling-2-Mini 量化 GGUF，与 llama.cpp 参考对齐，再做循环研究。任务、依赖和验收只以 [07](docs/07_tasks.md) 为准。

## 红线（违反即停止并通知用户）

1. **不动驱动。** 不运行 apt/dpkg/dkms/modprobe/rmmod、NVIDIA 驱动安装器、`nvidia-smi -pl/-pm/-r/-ac`；不以 root 运行任何安装器；CUDA 编译工具只装在 hhtele 用户目录，版本不超过驱动支持的 CUDA 13.3。
2. **每个安装/构建步骤前后跑 `tools/driver_guard.sh check`**；退出码 3（驱动指纹变化）或任何安装器输出提到 driver / kernel module / DKMS / nouveau，立即停止后续一切操作，保留现场输出，通知用户。
3. **生产停启只用 `tools/lab_window.sh`**。只允许免密的 `systemctl start|stop|restart openclaw-qwen38-next.service`；禁止 kill/pkill 生产进程；生产忙（state 不是 idle）不进窗口。
4. 不 drop page cache、不改 power limit/时钟、不改 systemd unit、不动 `/data/strata-data` 和生产目录。

## 工作规则

- 所有源码、模型、构建、证据放在 `$HOME/inkling-lab-v3/`（下称 `$LAB`），不覆盖机器上已有的任何树。
- 上游一律锁定 commit / revision（[09](docs/09_sources.md)）；升级另立任务，不自动 pull。
- Astral fork 在分支 `inkling-4090` 上提交，每个 commit 一个可归因的改动；保留上游 Apache-2.0 头和 NOTICE，新增文件同样标注。
- 正确性先于速度：先有能失败的测试（selftest、对 llama.cpp 的 golden、贪心序列），再改实现。
- 一次只改一个变量；同一张 GPU 上的实验串行。
- 每个任务交付：输入版本、命令、原始输出、结论；原始输出不能只留摘要。

## 状态与证据

状态只用 `NOT_RUN / RUNNING / PASS / FAIL / BLOCKED / NO_BENEFIT / DEFERRED`。

- 程序能启动 ≠ PASS；作者/社区数字、其他 GPU 上的结果、mock 和合成数据不能写成 4090 结果。
- 阈值在看候选结果之前冻结（[05](docs/05_validation.md)）；不为过测放宽阈值、删除断言或换更简单的样本。
- 一项修正最多两轮有 profiler/数据支撑的尝试，仍失败就按停止规则结案并报告。

## 需要用户介入的情况

驱动风险（红线 1–2）；需要 root；需要停服超过计划窗口；要放弃 Astral 改走其他引擎；要下载未列在 [01](docs/01_model.md) 的大文件（>30 GiB）；任何对外发布（推送 fork、提 PR、上传权重）。
