# 生产更新：#1536 + PT=0 + CPUSHARE 4096 + AUTOMAX 16384（2026-10-26）

**结论：生产已更新并恢复运行（09:24 EDT 起 active / enabled）。** 端口 18343、模型名 `openclaw/Qwen3.8-next`、NGINX 28343 链路、Pi 配置、引擎二进制（A0 `819ff262…`）都不变。

上线了四个开关：两个服务层 Python 改动，两个引擎 env。启动回执、进程环境和冒烟请求都确认生效。

## 1. 变更清单

| 项 | 变更前 | 变更后 | 依据 |
|---|---|---|---|
| 服务状态 | 10-25 起按用户授权停机测试 | **active / enabled** | 用户 10-26 要求更新生产 |
| 服务层代码（7 个文件） | A0 `5c8dd322` 原样 | 打上 `lab/prod-20261026`（`dcd67870` #1536 + `f615cc8d` CFG-PT）相对 A0 的补丁 | [P1-SESSION](P1-SESSION-1536-PT-20261025.md) |
| `STRATA_REPLY_REUSE` | 无 | `1`（#1536：下一轮复用回复自己的 token id） | 同上 |
| `STRATA_PRESERVE_THINKING` | 无（模板默认保留历史 thinking） | `0`（历史轮不渲染 thinking；请求里的 `chat_template_kwargs.preserve_thinking` 优先） | 同上 |
| `STRATA_PREFILL_CPU_SHARE_MAX` | `3072` | `4096` | [P2-CFG-CPUSHARE-S](P2-CFG-CPUSHARE-S-20261026.md) |
| `STRATA_PREFILL_AUTO_MAX` | 无（auto 上限 8192） | `16384` | [P2-PR3307](P2-PR3307-20261026.md) |

**改动的 7 个文件：**
- `serve/server.py`
- `serve/frontend.py`
- `tools/strata_tokenizer.py`
- `serve/test_server.py`
- `serve/test_prompt_encoder.py`
- `serve/test_frontend.py`
- `docs/DETAILS.md`

打补丁前逐个核对过，这 7 个文件都与 A0 一致，没有本地漂移。补丁后的内容与分支逐个一致。

**两个服务层开关放在启动脚本里，不在配置的 `env` 里：**
- 配置的 `env` 只传给引擎子进程（`serve/server.py:3480` 拼引擎环境），服务进程自己读不到。
- 所以 `STRATA_REPLY_REUSE`、`STRATA_PRESERVE_THINKING` 写在 `run-iq3_xxs.sh` 里，在 `exec` 之前 export，带注释。
- 两个引擎 env 放在 `strata-iq3_xxs.json` 的 `env`。
- 配置里除这两个 key 外没有其他差异。systemd unit、NGINX 都没动。

**合并说明：**
- 两个改动都在 `serve/server.py` 的 `main()` 同一处加了启动回执，cherry-pick 时冲突。手工合并，两行都保留。
- 其余部分不重叠。

**备份：** `/home/hhtele/strata-0.2.3/backup-20261026/`，内容如下：
- 7 个原文件（保持原目录结构）
- 原 `strata-iq3_xxs.json`
- 原 `run-iq3_xxs.sh`
- `prod-20261026.patch`
- `SOURCE_COMMIT`

## 2. 验证

| 检查 | 结果 |
|---|---|
| 单测（合并分支，生产 venv，`python -m unittest serve.test_frontend serve.test_prompt_encoder serve.test_server`） | **已运行并通过**：396 项，OK |
| 服务启动 | `systemctl start` 后 34 s `/health` 为 `loaded: true`；`max_context` 131072，`model` `openclaw/Qwen3.8-next` |
| `/v1/models` | `openclaw/Qwen3.8-next`，loaded |
| NGINX 28343 | 不带 Bearer 返回 401，与之前一致；未测带 Bearer 的请求 |
| 启动回执 | `[strata] LAB_PR_1536 enabled=1 (... + remember_reply)`；`[strata] LAB_CFG_PT preserve_thinking default=0` |
| 进程环境 | 服务进程有 `STRATA_REPLY_REUSE=1`、`STRATA_PRESERVE_THINKING=0`；引擎进程另外有 `STRATA_PREFILL_CPU_SHARE_MAX=4096`、`STRATA_PREFILL_AUTO_MAX=16384` |
| 引擎回执 | `prompt chunk auto: 16384 tokens, a 384-slot ring`；`expert cache 9420 slots, 15.27 GiB`（与之前相同）；PCIe probe 12.3 GB/s |
| 显存 / 内存 | 空载 23.7 GB；MemAvailable 约 13.0 GiB |
| PT=0 | 同一组带历史 thinking 的消息（thinking 开）：默认 157 prompt token；显式 `preserve_thinking=false` 157；显式 `true` 284。默认值生效，请求覆盖也生效 |
| 短问答（thinking low，Pi 采样） | 正常回答；223 token，decode 114.9 tok/s |
| 长读入（27,155 token，新前缀，thinking 关） | 7.57 s 读完（3,588 tok/s），TTFT 7.62 s；答案正确（`v699`） |

**未验证：**

- **#1536 在生产上的实际复用：** 只看了启动回执。PT=0 下 Pi 的默认请求本来用不到它（见 P1 报告 5.4 节）；请求显式要 `preserve_thinking=true` 时才生效。实验室已验证：重读 4/14 → 0/16。
- **CPUSHARE 4096 与 AUTOMAX 16384 的组合：** 没做 A/B，只有上面的冒烟。两者作用区间不重叠（[06_COMBINATIONS](../docs/06_COMBINATIONS_ROLLBACK.md)）。
- **真实 Pi 长会话：**
  - PT=0 的难题质量，实验室只在编码链上验证过，有天花板效应。
  - 真实流量下 TTFT 和 decode 的统计，需要攒一批请求后对比。
- **发热：** AUTOMAX 下连续长冷读会到 84～85 °C（卡的目标温度 84 °C）。头几天留意 `nvidia-smi` 的温度和 `clocks_event_reasons`。

## 3. 回滚

每项都可以单独回滚，改完都要重启服务：
```
sudo systemctl restart openclaw-qwen38-next
```
冷加载约 30 s。

| 回滚对象 | 做法 |
|---|---|
| AUTOMAX | 删掉 `strata-iq3_xxs.json` 里 `env` 的 `STRATA_PREFILL_AUTO_MAX` |
| CPUSHARE | 把 `STRATA_PREFILL_CPU_SHARE_MAX` 改回 `3072` |
| 两个引擎 env 一起 | `cp backup-20261026/strata-iq3_xxs.json .` |
| PT=0 或 #1536 | 删掉 `run-iq3_xxs.sh` 里对应的 `export` 行。代码留着也不生效：两个开关不设时，行为与 A0 相同 |
| 服务层代码整体 | `cp -a backup-20261026/{docs,serve,tools} .` 和 `cp backup-20261026/run-iq3_xxs.sh .` |
| 整个版本回到 0.1.43.1 | 见 [DEPLOY-A0-EXACT6](DEPLOY-A0-EXACT6-20261025.md) 第 4 节。`/home/hhtele/strata-0.1.43.1` 未动 |

以上路径都相对 `/home/hhtele/strata-0.2.3`。

## 4. 对实验的影响

- 生产恢复后占用 GPU。实验端口 18089 的 GPU campaign 必须先停生产，需要用户同意。
- 实验包的公共基线仍是 A0 + EXACT6 原样。生产多了这四个开关，此后的实验结论如果要套到生产上，需要在这个配置上复核。
