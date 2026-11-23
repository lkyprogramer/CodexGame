# 新版本一键过门（upgrade_gate.py）

上游 Strata 发布新版本后，在 4090 上判断它能否替换生产。脚本把 v0.2.17 迁移时手工做过的步骤串成一条命令：取源码、打 PT0/#1536 补丁、编译、组装新树、KL 门、任务级门。**不会自动切换生产**；切换要另外执行 `switch`，并加 `--yes`。

只用 Python 标准库，在 4090 上用 `/home/hhtele/anaconda3/bin/python` 运行。部署位置是 `/data/strata-data/upgrade-gate/`，放三样东西：

- 本脚本；
- 通用补丁 `pt0-reply-reuse.patch`，即本仓库的 [`patches/v0217-pt0-reply-reuse.patch`](../../patches/v0217-pt0-reply-reuse.patch)；
- 某个版本需要手工移植时，放 `pt0-reply-reuse.<tag>.patch`，存在时优先使用。例如 v0.2.19 用的是 [`patches/v0219-pt0-reply-reuse.patch`](../../patches/v0219-pt0-reply-reuse.patch)，其中还含一处 CUDA 12.3 编译修复。

## 用法

```bash
cd /data/strata-data/upgrade-gate
setsid nohup /home/hhtele/anaconda3/bin/python -B upgrade_gate.py all v0.2.18 > v0.2.18.log 2>&1 < /dev/null &
# 结束后
/home/hhtele/anaconda3/bin/python -B upgrade_gate.py report v0.2.18
# 决定切换时
/home/hhtele/anaconda3/bin/python -B upgrade_gate.py switch v0.2.18 --yes
```

各阶段也可以单独运行：`prepare`、`kl`、`gate`、`report`、`switch`。

- **`gate --env K=V`**（可重复）：给这一臂加额外的引擎 env，臂名会带上开关名。
- **`gate --limit N --env …`**：只跑前 N 题，给出同一批题上的端到端速度对比，不作质量判定。前 40 题的比值与整臂 305 题相差约 1.5%。
- **已完整跑完的臂**：再次执行 `gate` 时只做判定，不再停生产。阶段结果写在 `/data/strata-data/upgrade-gate/<tag>/` 下的 `PREPARE.json`、`KL.json`、`GATE.json`、`REPORT.json` 和 `SWITCH.json`。退出码 0 表示阶段完成，2 表示按规则停止，原因写在对应 JSON 的 `stop` 字段。

## 阶段

| 阶段 | 做什么 | 生产 | 用时 | 停止条件 |
|---|---|---|---|---|
| `prepare` | 浅取 tag 到私有裸仓库，与 GitHub API 核对 tag 对象；`git archive` 导出 engine/terminal；补丁 `-F0` 先 dry-run 再应用，并重新生成本版补丁；用当前生产 python 跑 `serve.test_prompt_encoder serve.test_frontend serve.test_server`（约 2.5 分钟）；按 B1/B2 的 CMake 选项编译（nice、默认 `-j 8`，v0.2.19 起生产在线时要用 `-j 4`；MemAvailable 低于 3 GiB 即中止）；组装新树 `/home/hhtele/strata-<版本>`，python、专家 profile、配置和 run 脚本取自当前生产树，路径改写；检查 serve `--help` 能启动 | 不停 | 约 10 分钟 | 树已存在、tag 不一致、布局变化、补丁冲突（需手工移植）、单测失败、编译失败、配置引用不存在的文件 |
| `kl` | 用新树的 `quant_quality.py` 跑 rank 7、`--gpu-experts auto`，ids 与 v0.2.17 KL 实验相同；分别对比 v0.2.17 的 rank 7 和精确路由两次存档 | 停约 2 分钟 | 约 2 分钟 | 运行失败；全部 KL > 0.060 或 agent 段 > 0.170（KL_REGRESSION），不进入任务门 |
| `gate` | 写附加预登记 `PREREG-<arm>.json`，然后用未改动的 `gate17.py`（sha 与原预登记一致）只跑新版本一臂；配对的基线是已存档的 b2 臂；`quality_gate.py` 判定，prodlog 给出 decode 速度 | 停约 2 小时 | 约 2 小时 | KL 不是 PROCEED（可用 `--force` 越过）；臂不完整 |
| `switch` | 备份 `strata-0.2.3/run-iq3_xxs.sh`，改为 exec 新树；重启服务；600 秒内 health 不通过则自动回滚 | 重启 | 约 1 分钟 | 门未通过（可用 `--force` 越过）；没有 `--yes` |

每个停生产的阶段都在 finally 中恢复进入时的状态，SIGTERM 也会走到这一步。同一时间只能运行一个实例（文件锁）。脚本不写生产树、`strata-0.1.43.1`、驱动或 CUDA，只结束自己启动的进程组。

## 判定规则（在看到任何新版本之前定下）

- **KL 门**：阈值是 v0.2.17 rank 7 相对精确路由的已接受水平（全部 0.047，agent 段 0.136）的 1.25 倍。另外记录对 v0.2.17 rank 7 的漂移：为 0 表示数值完全没变。
- **任务门**：复用 [任务级配对质量门](../../reports/V0217-AGENT-GATE-20261120.md) 的 305 道题、seed、提示、判分镜像和 margin 5%。基线不重跑，直接用存档的 b2 臂，理由如下：
  - 原来的两臂也是先后分开跑的；
  - 同一 seed 本来就不能复现输出（见下方自检），重跑基线只是换一次随机抽样，不会让配对更紧。
- **建议**：只有 prepare 为 READY、KL 为 PROCEED、任务门为 NONINFERIORITY_ESTABLISHED 时，`report` 才给出 SWITCH_CANDIDATE。是否切换，还要结合速度和 release notes 由人决定。

## 自检（2026-11-21，用 v0.2.17 自身）

证据：[evidence/v0217-upgrade-gate-selftest-20261121/](../../evidence/v0217-upgrade-gate-selftest-20261121/)。

- **prepare：READY。**
  - tag 对象 `028e6826b`、commit `12d491da4`，与 API 和原迁移记录一致。
  - 补丁无偏移地应用到 6 个文件，其中 3 个运行文件的 sha 与生产树 IDENTITY 相同；新建树的 `terminal/` 与生产树逐文件相同（`diff -rq` 为空）。
  - 配置和 run 脚本除路径外都相同。
  - 编译 361 秒，生产在线，MemAvailable 最低约 6 GiB。
- **编译不可复现**：同一源码、同一目录编译两次，引擎 sha 分别为 `868a1155…` 和 `afcab6ca…`，生产版是 `df2d006b…`。所以新版本的数值是否变化以 KL 为准，不看二进制 hash。
- **kl：PROCEED。**
  - 对 v0.2.17 rank 7 存档：KL 0、top-1 100%，重新编译的引擎在数值上完全相同。
  - 对精确路由：KL 0.0474、agent 段 0.1361，与原报告一致。
  - 生产停了 87 秒。
- **gate `--limit 3`（只验证流程，不作判定）**：新树服务 40 秒就绪，3 题均无错误。affine-cipher 和 book-store 的结果与 b2 存档不同，beer-song 相同。同一版本、同一 seed，逐题结果仍会变化，所以只能看 305 题的统计。
- 自检结束后生产 health ok，GPU 占用 23.3 GB；临时树、build 和 src 已删除。

## 实际使用记录

- **2026-11-22 v0.2.19**（[报告](../../reports/V0219-UPGRADE-GATE-20261122.md)）：
  - 补丁手工移植，并加了 CUDA 12.3 编译修复。
  - 生产在线时 `-j 8` 会触发内存守卫，要用 `-j 4`。
  - 判定：KL 为 PROCEED，任务门非劣，但 decode 慢 13%，结论是不升级。

## 已知局限

- **补丁冲突需要人工**：上游改了 `frontend.py` / `server.py` / `strata_tokenizer.py` 的上下文时，dry-run 会失败，需要手工移植补丁，再更新 `pt0-reply-reuse.patch`。
- **flag 检查只给警告**：引擎 `--help` 本来就不列 `--vram-reserve-mib` 和 `--conversation-spill-mib`。新版本如果删掉了某个 flag，要到 `kl` 阶段引擎启动失败时才会暴露。
- **KL 门只覆盖一种配置**：生产配置下的 rank 7 加 auto 放置。新版本的变化如果只出现在长上下文、prefill 或会话缓存路径上，KL 门看不到；任务门也只覆盖 32K 以内的单题会话。必要时补一次 [Pi 式负载模拟](../../reports/V0217-PISIM-20261120.md)。
- **python 不随版本更新**：新树的 python 是从当前生产树复制的。新版本如果新增 Python 依赖，prepare 的 serve `--help` 检查会把它拦下。
