# 02 · 4090 现场与安全

## 1. 现场事实（ssh 只读，2026-11-26）

| 项 | 观察 |
|---|---|
| GPU | RTX 4090，cc 8.9，24564 MiB，UUID `GPU-381cb85f-8ebf-b33e-5076-9305e6af4be5`；生产 Strata 占 23334 MiB |
| 驱动 | KMD 610.57.04，支持到 CUDA 13.3 |
| 系统 CUDA | 只有 `/usr/local/cuda-12.3`（nvcc 12.3.107）；**低于 Astral 要求的 12.8** |
| 主机 | Xeon Silver 4216 16C/32T；内存 62.46 GiB，无 swap，生产运行时可用约 9 GiB（Strata RSS ≈44.6 GiB）；PCIe Gen3 x16（pinned H2D ≈8.1 GB/s） |
| 磁盘 | NVMe 980 1TB，根分区剩余 213 GB |
| 工具 | gcc 12.2、cmake 3.25.1、Python 3.11.2、anaconda3、aria2c、docker + nvidia-ctk；**没有 Rust、hf CLI、modelscope SDK** |
| 网络 | github.com 可达；**huggingface.co 超时**；hf-mirror.com 的 API 可用，但大文件跳到 HF CDN，0.06–1.5 MB/s；**ModelScope 可用，约 10.9 MB/s** |
| 生产 | `openclaw-qwen38-next.service`（Strata v0.2.17），端口 127.0.0.1:18343 / 0.0.0.0:28343；`/health` 的 `loaded` 约 30 s 后变为 true；`/metrics` 的 `live.state` 为 `idle` 表示空闲；监控 cron 每分钟记录 prod/lab/down |
| 权限 | hhtele 只有对该 unit 的 `systemctl start` / `stop` / `restart` 免密 sudo；其余 sudo 需要密码 |

更正 v2.1：v2.1 记为“huggingface.co 返回 200”，本次在 4090 上直连超时，以本次观察为准。

## 2. 工具链方案（全部装在用户目录）

| 组件 | 方式 | 位置 | 驱动风险 |
|---|---|---|---|
| Rust 1.100.0 | `rustup-init -y --no-modify-path --default-toolchain none`，由仓库的 `rust-toolchain.toml` 拉取 1.100.0 | `$LAB/toolchains/{rustup,cargo}`（设置 `RUSTUP_HOME` / `CARGO_HOME`） | 无 |
| CUDA 12.8 编译工具 | **conda**，`-p` 前缀环境，频道 `nvidia/label/cuda-12.8.1`，只装列出的包；先 `--dry-run --json`，用 `driver_guard.sh scan` 审查包名 | `$LAB/toolchains/cuda-12.8` | conda 包中没有内核驱动，但仍要审查，见 §3 |
| Python 工具 | `python3 -m venv $LAB/venv` + `pip install modelscope gguf numpy` | `$LAB/venv` | 无 |

所需 conda 包：`cuda-nvcc cuda-cudart-dev cuda-nvrtc-dev cuda-cccl libcublas-dev cuda-cuobjdump cuda-nvdisasm cuda-profiler-api cuda-driver-dev cuda-nvml-dev`，版本由 label 锁定为 12.8.1；conda-forge 依赖走清华镜像。Astral 只需要 nvcc 和头文件；llama.cpp 还需要 cudart、cublas、cccl、`libcuda.so` 链接 stub（`cuda-driver-dev`，**不是驱动**）和 `nvml.h`。依赖中会带入 conda-forge 的 gcc 13.4 和 binutils，它们只在该前缀里，不在 PATH 上；nvcc 实际使用系统的 gcc 12.2（CMake 输出已确认）。

**禁止的方式**：

- NVIDIA runfile 安装器：它内含驱动，参数一错就会尝试替换 610 驱动。
- apt 的 `cuda`、`cuda-drivers`、`cuda-toolkit-*` 和 `nvidia-*` 包。
- 任何 `sudo` 安装。
- 把 `$CUDA/lib/stubs` 放进 `LD_LIBRARY_PATH`：stub 版 `libcuda` 会遮蔽真实驱动，运行时报 "stub library"。这虽然不改驱动，但会造成误判。

版本约束：toolkit 12.8 ≤ 驱动支持的 13.3，生成的 cubin 由 610 驱动加载，不需要 PTX JIT。12.8 支持 gcc 12.2 作为 host 编译器。

## 3. 驱动守卫

`tools/driver_guard.sh` 的三个子命令：

- `snapshot <file>`：记录 `/proc/driver/nvidia/version`、`nvidia-smi` 报告的驱动版本、`modinfo -F version nvidia`、`uname -r`、`dpkg-query` 列出的 nvidia / libcuda / cuda-drivers 包、`libcuda.so.1` 实际路径及其 SHA256、`/lib/modules/$(uname -r)` 下的 nvidia 模块文件及其 mtime。
- `check <baseline>`：重新采样并与基线比较；有任何差异退出码为 3，并打印差异。
- `scan <file>`：在安装日志或 dry-run 输出里查找驱动相关字样，命中退出码为 3。

使用规则：

1. T00 生成基线 `$LAB/evidence/driver-baseline.txt`，之后不再改动；基线文件的 SHA256 写入每次运行的指纹。
2. 每个安装或构建步骤前后都跑 `check`；每个窗口进入和退出时，`lab_window.sh` 自动跑 `check`。
3. 退出码 3：停止全部后续步骤，不要尝试“修复”，保留输出，立即通知用户。

**已识别、与驱动相邻的风险（需用户决定，代理不得自行处理）**：

| 风险 | 说明 | 本包的处理 |
|---|---|---|
| 性能计数器权限 | Nsight Compute 读取 GPU 计数器，默认需要 root 或驱动模块参数 `NVreg_RestrictProfilingToAdminUsers=0`。修改该参数属于改驱动配置 | **不做**。用 CUDA event 计时、`kbench`、Nsight Systems 的 CUDA trace（不需要计数器）；确实需要 ncu 时请用户决定 |
| 时钟与功耗 | `nvidia-smi -lgc/-pl/-pm` 改变 GPU 状态 | 禁止；只读取并记录时钟 |
| GPU 故障恢复 | Xid 或卡死后的 `nvidia-smi -r` / 模块重载 | 禁止；停止实验，记录 `dmesg` 中可读的部分（若无权限则记“无法读取”），通知用户 |
| 容器 | tqllm 的 Docker 镜像使用宿主驱动，镜像内的 CUDA 12.8+ 用户态库要求驱动 ≥ 570 | 610 满足要求，不改驱动；但只有在用户同意后才运行 |

## 4. 生产窗口

只通过 `tools/lab_window.sh <分钟数> <命令…>` 进入。脚本依次：

1. 检查生产是否空闲（`live.state == idle`），并做驱动 `check`。
2. 免密 `systemctl stop`，记录停止后的显存。
3. 带 `timeout` 运行负载。
4. 无论成败，由 EXIT trap 结束 `$LAB` 下的实验进程，再 `systemctl start` 生产，最多等 300 s 直到 `loaded`。
5. 最后再做一次驱动 `check`。

监控 cron 会把窗口期记为 lab/down，这是预期内的。

单个窗口不超过 90 分钟；更长的窗口要先征得用户同意。窗口时间写入 `$LAB/evidence/windows.log`。

## 5. 主机资源

生产运行时构建：`CARGO_BUILD_JOBS=6`、`nice -n 10`；构建前要求 `MemAvailable` ≥ 4 GiB，否则等待。nvcc 编译 `gemv.cu`（114 KB 模板代码）是内存峰值点，按单文件串行编译（Astral 的 `build.rs` 本来就逐文件编译）。llama.cpp 用 `-j 8`。不在本地开发机（2C/1G）上构建或运行任何东西。
