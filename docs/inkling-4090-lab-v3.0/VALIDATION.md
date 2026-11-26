# v3.0 交付验证记录

> **历史记录（v3.0 初版交付时）。** 本文件只描述 v3.0 文档包交付当时的检查，当时 4090 上什么都没运行。之后的真实执行结果（T00–T14 已执行，G1–G3 通过，V7 待 T19 复核）以 [07](docs/07_tasks.md) 的状态表和执行记录为准；下文的 “NOT_RUN” 不再反映现状。

**日期：2026-11-26（Asia/Shanghai）。范围：文档、工具和来源身份。4090 上没有安装、构建或运行任何东西，生产没有停过。**

## 1. 已执行的检查（在本地开发机上，只用标准库）

| 项目 | 结果 | 证明范围 |
|---|---|---|
| `python3 -B -m unittest discover -s tests -v` | 17 项通过：沿用的 9 项（paired_stats、preflight）+ 新增 8 项（driver_guard 的 compare/scan/snapshot，lab_window 的参数拒绝，ms_fetch 的 plan/verify） | 工具逻辑；lab_window 只测了在调用 systemctl 之前就退出的路径 |
| `python3 -B tools/check_package.py` | PASS：10 篇专题；任务、研究、来源、资产 ID 一致；Markdown 链接有效；shell 脚本和 shell 代码块通过 `bash -n` | 结构；**不代表**示例命令在 4090 上能运行 |
| `sha256sum -c PACKAGE_MANIFEST.sha256` | 全部 OK | 包完整性 |

## 2. 只读现场与来源核对

| 项目 | 方法 | 观察 |
|---|---|---|
| 4090 下载渠道 | ssh 上 curl | HF 直连超时；hf-mirror 大文件 0.06–1.5 MB/s（经 HF CDN）；ModelScope 10.9 MB/s。static.rust-lang.org、crates.io、conda nvidia 频道、PyPI 清华镜像、GitHub 均可达 |
| ModelScope 镜像身份 | ModelScope 文件列表的 Sha256 对 HF LFS oid | A1–A6 全部一致 |
| Astral 结论 | 在 49a0a2b 上通过 GitHub API 逐文件读取并 grep | [04](docs/04_astral_fork.md) §2 的每一行都对应具体文件与行号；“4090 上可能无需改代码即可上卡”是推断，未运行 |
| 其他 pin | GitHub / HF API | [09](docs/09_sources.md) 所列 commit 和 revision |

## 3. 未执行

T00–T18、R1–R7 全部 `NOT_RUN`。driver_guard 的 `snapshot` / `check` 读取真实系统的部分，lab_window 的停启路径，ms_fetch 的在线列表，[08](docs/08_runbooks.md) 中的全部命令：都没有在 4090 上执行过。
