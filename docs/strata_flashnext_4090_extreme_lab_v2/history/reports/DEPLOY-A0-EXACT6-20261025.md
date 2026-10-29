# 生产升级：A0（v0.2.3）+ EXACT6 + CFG-CSTATE（2026-10-25）

**结论：生产已切到 `/home/hhtele/strata-0.2.3`（A0 + EXACT6），端口 18343、模型名 `openclaw/Qwen3.8-next`、NGINX 28343 链路和 Pi 配置都不变。CFG-CSTATE 在线 A/B 为 +2.2%（配对中位，18 对），已保留并持久化。perf 已安装。**

## 1. 变更清单

| 项 | 变更前 | 变更后 |
|---|---|---|
| 服务 `openclaw-qwen38-next` | inactive / disabled，指向 0.1.43.1 | **active / enabled**，指向 `/home/hhtele/strata-0.2.3` |
| 服务 `openclaw-qwen38-ninfer` | active / enabled（18343 上的代理，后端 docker 未运行） | **inactive / disabled** |
| docker `onnxocr-ppocrv6-small-cpu-compat` | Up（6013，约 8 GB RAM） | **stopped**（restart 策略为 unless-stopped，重启后不会自动拉起） |
| 引擎 | 0.1.43.1 | A0 `5c8dd322`，`engine/strata` sha256 `819ff262…de3d` |
| env | ADAPT_OVERLAP=1、PREFILL_CPU_SHARE_MAX=3072、两个 TIMING | 原有 env + EXACT6：`SIDE_MIXER=2 ATTN_DAILY=1 GR_UP75=1 GU_SWIGLU=1 QSA_ROWS=1 B6_MMVQ_ROWS=1` |
| CPU 调频 | 32 × `schedutil`（intel_cpufreq） | 32 × `performance` |
| C-state | C6（退出延迟 133 µs）全开 | C6 全部 disable；POLL / C1 / C1E 不变 |
| `kernel.perf_event_paranoid` | 3 | 1 |
| perf | 无 | `linux-perf` 6.1.190（顺带把 linux-libc-dev / linux-kbuild / linux-compiler-gcc 从 6.1.69 升到 6.1.190；运行内核 6.1.0-17、驱动、CUDA 都没动） |

新增文件：

- `/etc/systemd/system/strata-host-tuning.service`：oneshot，开机设置 performance 调频并关闭 C6；在 next 服务之前启动。
- `/etc/sysctl.d/99-perf.conf`：设置 paranoid=1。
- unit 备份：`/etc/systemd/system/openclaw-qwen38-next.service.bak-v0431-20261025`。
- 原始值记录：`workspace/reports/deploy/host-before-20261025.txt`。

没有动 NGINX、驱动 / CUDA、内核参数 / GRUB / initramfs，也没有写 `/home/hhtele/strata-0.1.43.1`。

## 2. 验证

| 检查 | 结果 |
|---|---|
| `127.0.0.1:18343/health` | 200，`model=openclaw/Qwen3.8-next`，`max_context=131072`；从启动到健康约 25 s |
| `/v1/models` | `openclaw/Qwen3.8-next`，loaded |
| 引擎进程 env | 上表 10 个 `STRATA_*` 全部存在 |
| 专家缓存 | 9420 experts / 15.27 GiB；GPU 显存占用 23.6 GB |
| NGINX 28343 | 不带 Bearer 返回 401（与之前一致）；带 Bearer 的 `/v1/models` 和 chat 正常 |
| 冒烟请求（短 Java 问题，512 tok） | 118 tok/s，命中率 92.6% |

## 3. CFG-CSTATE 在线 A/B

方法：在生产服务上（服务不重启），交替切换 host 设置。

- arm off = `schedutil` + C6 开；arm on = `performance` + C6 关。
- 6 轮，轮间交换顺序；每轮每个 arm 发 3 个固定提示（Java LRU / InnoDB MVCC / Spring 异常处理）。
- 每个提示 512 tok，`temperature=0`，关闭 thinking。
- 读取引擎 `done:` 行的 tok/s。
- 数据：`workspace/reports/deploy/cstate-ab-20261025.tsv`。

| arm | n | 中位 tok/s | 均值 |
|---|---|---|---|
| off | 18 | 156.9 | 155.8 |
| on | 18 | 160.2 | 159.3 |

配对 on/off：中位 **1.022**，范围 0.917～1.150。

解读：

- 中位和均值都是 +2.2%，与 NP-0 的“CPU 在关键路径上”方向一致。
- 幅度和组级噪声（约 ±2%）相当。所以这是**小幅正收益，不是确定的大收益**。
- 只测了短上下文 decode，长上下文和 prefill 没测。

代价：CPU 空闲功耗上升（不再进入 C6，并固定在高频）。

## 4. 回滚

- **引擎回滚到 0.1.43.1**：
  ```
  cp openclaw-qwen38-next.service.bak-v0431-20261025 openclaw-qwen38-next.service
  systemctl daemon-reload
  systemctl restart openclaw-qwen38-next
  ```
  0.1.43.1 目录完好。
- **恢复 NInfer**：
  ```
  systemctl disable --now openclaw-qwen38-next
  systemctl enable --now openclaw-qwen38-ninfer
  ```
  两个服务互相 Conflicts。
- **恢复 OCR**：`docker start onnxocr-ppocrv6-small-cpu-compat`。
- **撤销 CSTATE**：
  ```
  systemctl disable --now strata-host-tuning
  ```
  ExecStop 会恢复 `schedutil` 并重新开启 C6。
- **撤销 paranoid**：删除 `/etc/sysctl.d/99-perf.conf`，然后执行 `sysctl -w kernel.perf_event_paranoid=3`。

## 5. 剩余风险

- **受控回放 / 冒烟 ≠ 真实 Pi 流量。** 建议攒一批真实请求后，按之前的口径与 0.1.43.1 时期的统计对比。
- **NInfer 已 disable。** 如果有依赖 `openclaw/Qwen3.8-27B-WORK` 的客户端，它们会拿到 404（模型不存在）；18343 现在只提供 `openclaw/Qwen3.8-next`。
- **服务一直使用 `.venv`。** `strata-0.2.3/.venv` 是从 0.1.43.1 复制的；serve 已能正常 import 并对外服务。
