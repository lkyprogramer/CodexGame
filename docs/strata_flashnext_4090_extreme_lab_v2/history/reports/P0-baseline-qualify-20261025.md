# Phase 0 报告：基线、资格与源码准备（2026-10-25）

**结论：** Phase 0 中 P0-T1～T4 已完成。A0（v0.2.3，`5c8dd322`）用 29 现有工具链编译成功，MIG 不会因为工具链被判 BLOCKED。11 个 PR 都已生成隔离 worktree 和源码差量；qualify 只拦下 #2964（它不支持生产在用的 adaptive overlap），按规则判 NOT_APPLICABLE。为执行 MIG，给实验包加了只读的 P arm 和 `mig` 命令（见第 5 节）。P0-T5（DIAG 构建）、P0-T6（配置对照）和 P0-T7 排在 MIG 之后。

实验目录：29 上的 `/home/hhtele/strata-lab-4090`（原始输出在其 `workspace/` 下，不进 git）。

## 1. P0-T1：29 的实测状态（doctor，2026-10-25 00:17 EDT）

| 项 | 实测 |
|---|---|
| 系统 | Debian 12，内核 6.1.0-17-amd64，glibc 2.36，Python 3.11.2 |
| CPU / RAM | Xeon Silver 4216（16C/32T，有 avx512_vnni，无 VBMI），MemAvailable 58.8 GB（Strata 停止时） |
| GPU | RTX 4090，驱动 610.57.04，空闲（1 MiB 占用，无计算进程），42 °C |
| 工具链 | git 2.39.2；系统 cmake 3.25.1（不能用，见第 3 节）；部署树 venv 内 cmake 4.4.3 + ninja；nvcc 不在 PATH，用 `/usr/local/cuda-12.3/bin/nvcc` |
| 磁盘 | 根分区剩余约 170 GiB |
| 生产服务 | `openclaw-qwen38-next.service` inactive；本轮未启动、未修改 |

与文档（`docs/02_ENVIRONMENT.md`）一致，没有发现需要更正的事实。

## 2. P0-T2：冻结 P（生产 0.1.43.1）身份

| 项 | 值 |
|---|---|
| 部署树 | `/home/hhtele/strata-0.1.43.1`，HEAD `a0116b2782a5b82622358c04a06496485d12b2d6`（tag v0.1.43.1），**浅克隆** |
| 已跟踪文件改动 | 0（10 项改动全是未跟踪文件：`.no-sudo-bin/`、`ab/`、构建脚本、profile、smoke 目录、配置备份） |
| `engine/strata` | sha256 `d245b0f2a2ee1ef1ea697aa5b0fc536eafd2ff589f74e763603af9dfd2508247`（65,659,536 字节，10-13 编译） |
| 生产配置 | `strata-iq3_xxs.json` sha256 `72936fb619d7ce19445ecd4cfe755a31b5159fd97ef99ffe3c99c793774969fb` |
| chat template | sha256 `12827f24b742ea4e80cdc12dbcf9622227056b9f797252a3149263d4f9aaadce` |
| 资产快照 | `./run.sh assets`：16 个文件，共 78.2 GB，全部完成哈希（结果在 `workspace/assets.json`），每次 campaign 前后自动复核 |

生产启动参数：`--expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp /data/strata-data/mtp/rt --max-context 131072 --kv int8 --vram-reserve-mib 974 --conversation-cache-mib 6144 --conversation-cache-slots 4`，以及 `--expert-profile`（只读）和 `--expert-profile-save`（实验中由 runner 删除，不写生产 profile）。env：`STRATA_DECODE_TIMING=1`、`STRATA_PREFILL_TIMING=1`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、`STRATA_ADAPT_OVERLAP=1`。A0 和 P 的源码里这 4 个 env 名都存在。

## 3. A0 构建（v0.2.3）

- 源码：`5c8dd322528cc84f68f461ad54a506b9da8fa8d4`；llama.cpp/ggml 用 v0.2.3 指定的 `3cf03257`（取自 29 上已有的 `~/strata/third_party/llama.cpp-3cf0325.zip`，解压到实验目录）。
- cmake 参数与生产 0.1.43.1 的 `CMakeCache.txt` 对齐：Ninja、`CMAKE_CUDA_ARCHITECTURES=89`、Release、nvcc 12.3、`STRATA_MMQ_KQUANTS=OFF`、`STRATA_Q6K_EXPERTS=OFF`；另开 `STRATA_BUILD_TESTS=ON`，供后续 `mmvq_il_parity`、`b6_mmvq_bench` 使用。
- 结果：00:38:36 → 00:42:25 编译成功。`build-lab/strata` sha256 `819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d`。

遇到的问题和处理：

| 问题 | 原因 | 处理 |
|---|---|---|
| selftest 1 个错误（UnicodeDecodeError） | 从 macOS 打包时带上了 126 个 `._*` 元数据文件，`prs/*PR3453.md` 的 glob 匹配到了它 | 删除 `._*`，之后改用 `COPYFILE_DISABLE=1 tar --no-xattrs` 同步；31/31 通过 |
| 第一次 configure 失败 | 系统 cmake 3.25.1 不认 `CUDA20` 方言 | 改用生产当初编译用的 venv cmake 4.4.3（只读调用） |
| bootstrap 拉取基线失败 | 29 访问 GitHub 不稳定：一次 TLS 中断，一次连接超时 | 本机拉取完整历史和 11 个锁定 PR head（SHA 全部与 LOCK.json 一致），打成 git bundle（约 80 MB）传到 29。因为部署树是浅克隆，增量 bundle 缺前置提交，改用完整 bundle |

## 4. P0-T3 / T4：prepare 与 qualify

| PR | 上游文件数 | 提交数 | `git apply --check` 到 A0 | qualify |
|---|---|---|---|---|
| #2253 | 6 | 5 | 冲突（与文档一致：需语义移植） | 通过 |
| #3453 | 3 | 1 | 可直接应用 | 通过 |
| #1536 | 5 | 1 | 冲突 | 通过 |
| #3307 | 7 | 3 | 冲突 | 通过 |
| #3584 | 23 | 36 | 冲突 | 通过 |
| #3281 | 9 | 5 | 冲突 | 通过 |
| #3517 | 5 | 1 | 可直接应用 | 通过 |
| #3711 | 5 | 1 | 可直接应用 | 通过 |
| #2822 | 51 | 11 | 可直接应用 | 通过 |
| #3322 | 722 | 65 | 冲突（分支混入大量旧主线，需按符号移植） | 通过 |
| #2964 | 9 | 1 | 冲突 | **拦下：原 PR 拒绝 adaptive overlap** → NOT_APPLICABLE（生产依赖 `STRATA_ADAPT_OVERLAP=1`，关掉会损失约 12% decode） |

“可直接应用”只说明文本补丁不冲突，不等于语义正确；每个 PR 的源码差量审计（PORT_AUDIT）放到各自的 Phase 里做。每个 PR 的 `TASK.md`、`upstream.patch`、`upstream-files.txt` 在 `workspace/state/pr-<N>/`。

## 5. 对实验包的改动（为执行 MIG）

文档的 MIG 一节写明“runner 没有 P arm”。按其中方案 1 实现：

- `lab/runner.py`：
  - `make_run_config` 在 arm `p` 时运行部署树里的二进制（其余 arm 仍是 `build-lab/strata`）；写入类参数（`--expert-profile-save` 等）照旧删除，日志写到 run 目录。
  - 所有 arm 设 `PYTHONDONTWRITEBYTECODE=1`，P 从部署树导入 `serve/` 时不会生成 `.pyc`。
  - `campaign(..., mig=True)`：每轮 P/A0 交替先后；启动 P 前核对二进制 sha256 没变；campaign 开始和结束各做一次部署树文件清单（大小 + mtime），有任何新增、删除或改动就判 BLOCKED，并写出 `deployed-tree-diff.json`。
- `lab/cli.py`：新增 `mig --execute --corpus <冻结题集> [--groups ...]`。
- MIG 烟测（1 轮，quality 组）暴露并修复了 3 个跑测脚本缺陷：
  1. `init` 和 `load_config` 都对 Python 路径做了 `resolve()`，把 venv 的 `bin/python` 符号链接解析成系统 `/usr/bin/python3.11`，导致丢掉 venv（`No module named 'jinja2'`）。改为只取绝对路径、不跟随符号链接。
  2. 两个 arm 之间只等 2 秒，P 退出后端口 18089 还没释放，下一个 arm 拒绝启动。改为 `wait_released()`：等端口能绑定且 GPU 上没有计算进程，最多 120 秒。
  3. 第 1、2 次失败时部署树清单比对均为 0 改动，确认失败路径也没写生产树。
- `tests/test_mig.py`：5 个单测，覆盖 P arm 用部署二进制且删除写入参数、A0 arm 不受影响、清单比对能发现写入、venv 符号链接不被解析、`wait_released` 会等端口和 GPU。29 上 selftest 36/36 通过；`MANIFEST.sha256` 已重建（100 个文件）。
- 烟测结果（`results/pr-0-20261025-005232`）：P 与 A0 的 8 道 quality 题全部通过；部署树 0 改动。两边启动日志一致：adaptive overlap 开启，专家缓存 9434 对 9420 个槽，满载后空闲显存 516 对 514 MiB。

## 6. 下一步

1. MIG 烟测：已完成并通过（见第 5 节）。
2. MIG 正式运行（2026-10-25 00:57 启动）：5 轮，P/A0 交替，题集 `mig-523966959432`（39 题：quality/tool/protocol、短 decode、4K～120K 冷 prefill、长检索，以及 8 题 Pi 采样参数副本）。
3. 根据 MIG 结论（PASS / REGRESS / BLOCKED）进入 P0-T5 DIAG 和 P0-T6 配置对照。

未覆盖：Java 组需要本地 Docker JDK 镜像，29 没有，所以 Java 题为 NOT_RUN；park/restore 多轮场景实验包没有内置，放到 #2253 的 Phase 里补。
