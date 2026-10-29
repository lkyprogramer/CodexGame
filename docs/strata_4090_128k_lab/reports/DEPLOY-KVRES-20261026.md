# 生产启用 CFG-KVRES：`--kv-resident 20480`（2026-10-26）

**后续证据入口（2026-10-27）：** 本文记录 10-26 部署与冒烟的历史事实。[补充组合实验](P3-COMBINATION-KVRES-20261027.md) 已在独立实验环境完成，生产配置未改；6 对、276 请求的性能表征中 8 个主指标 CI 均未达 4% 门，正式采用门未通过，质量非劣未建立。原正式回放失败和独立 4/4 同错保留；两臂均观测到 69625 / 102385 token 真实恢复，但各六个长检索均未通过精确答案检查；Python 全链成功率关闭 2/2、开启 1/2，样本不足以因果归因。新检索输入与本文未保存的随机错答文档不同，不能称为复现或解释了本文 T3 异常。收尾确认全部实验进程退出，GPU 1 MiB、无计算进程，生产 inactive/dead、仍 enabled，13 个保护文件 hash 不变。

**结论：生产配置已加入 `--kv-resident 20480`，冒烟验证通过，验证完按用户要求重新停机（21:41:59 EDT 起 inactive，仍 enabled）。**

- 端口 18343、模型名 `openclaw/Qwen3.8-next`、NGINX 28343、Pi 配置、引擎二进制、10-26 上午上线的四个开关都不变。
- 启动回执、进程参数和环境确认生效。
- 冒烟覆盖了停放后恢复会话。这是实验室没覆盖到的路径，日志有 `conversation cache: restored 30006 tokens (live)`，恢复后回答正确。

冒烟里有一次检索答错：随机文档的追问，采样，thinking 关，第 350 行答成 4，应为 6。在另一份固定文档上复核了 32 次（greedy 与 Pi 采样各半），全部正确。**原随机输入缺失，因此只能说在另一份文档上未复现，尚不能归因或排除 KVRES**，见 2.3 节。

**注意：** 服务仍是 enabled，机器重启会带着 KVRES 配置自动拉起。

## 1. 变更

| 项 | 变更前 | 变更后 |
|---|---|---|
| `/home/hhtele/strata-0.2.3/strata-iq3_xxs.json` 的 `args` | `--kv int8`，不传 `--kv-resident`（默认 0：K/V 全驻显存） | 在 `"--kv", "int8"` 之后加 `"--kv-resident", "20480"` |
| 备份 | — | `/home/hhtele/strata-0.2.3/backup-20261026-kvres/strata-iq3_xxs.json`，与改前文件字节一致（sha256 前缀 `cc2999f80daac50f`） |

- `diff` 只有新增的两行。改后 JSON 校验通过。
- systemd unit、NGINX、`run-iq3_xxs.sh`、服务层代码都没动。
- 依据：[P2-CFG-KVRES](P2-CFG-KVRES-20261026.md)。

## 2. 验证（2026-10-26 21:38～21:42 EDT）

### 2.1 启动与回执

| 检查 | 结果 |
|---|---|
| 服务启动 | 21:38:30 `systemctl start`；`/health` 在 30 s 内（5 s 轮询）`loaded: true`，`max_context` 131072 |
| KV 回执 | `KV streaming: 20480 of 131072 cells per QSA layer in VRAM, the K/V in 1.55 GiB of pinned RAM` |
| 专家缓存 | `expert cache 10290 slots, 16.68 GiB of VRAM`，与实验室 cfg 臂相同（之前生产为 9420 / 15.27 GiB）；`pre-filled 10290 of 10290 slots from the profile` |
| prefill | `prompt chunk auto: 16384 tokens, a 384-slot ring`；`the prompt path borrows 4390 CUDA0 cache slots (7.13 GiB)` |
| 服务层回执（`run-iq3xxs.out`） | `LAB_PR_1536 enabled=1`；`LAB_CFG_PT preserve_thinking default=0` |
| 引擎命令行 | `--kv int8 --kv-resident 20480` |
| 引擎环境 | `STRATA_PREFILL_CPU_SHARE_MAX=4096`、`STRATA_PREFILL_AUTO_MAX=16384`、`STRATA_ADAPT_OVERLAP=1` 与 EXACT6 都在位 |
| 服务进程环境 | `STRATA_REPLY_REUSE=1`、`STRATA_PRESERVE_THINKING=0` |
| `/v1/models` | `openclaw/Qwen3.8-next`，loaded |
| NGINX 28343 | 不带 Bearer 返回 401；未测带 Bearer 的请求 |
| 显存 / 内存 | 空载显存 23,598 MiB，`512 MiB of VRAM free with everything loaded`；引擎 RSS 42.4 GiB；MemAvailable 13.04 GiB |
| 错误 | 日志里没有 CUDA / 内存错误，没有 `skip parking` |

MemAvailable 与上一次部署的约 13.0 GiB 基本相同，没有出现预期的少约 1.5 GiB：
- 事实：两次都只在启动后读了一次。
- 推断：MemAvailable 里含可回收的页缓存，它随专家 arena 走文件缓存读入而波动，单次读数分辨不出 1.5 GiB。
- 停放没有受影响：本次停放了两段会话，合计 1.17 GB，没有被拒。

### 2.2 冒烟请求（`workspace/o09/kvres_smoke.py`，21:40:01～21:40:13）

用 Pi 的采样参数（T 1.0 / top_p 0.95 / top_k 20），直连 127.0.0.1:18343。长文档是 700 行带随机种子的代码，每行末尾常数为 `行号 × 7 mod 13`。

| # | 请求 | prompt / 生成 | TTFT | 结果 |
|---|---|---|---:|---|
| T1 | 短问答，thinking low | 56 / 205 | 0.67 s | 正常回答；decode 119.9 tok/s（86 窗口，平均 T 3.24，19.88 ms / 窗口） |
| T2 | 新前缀长读入，thinking 关 | 29,955 / 5 | 8.18 s | 读入 8.11 s（3,692 tok/s）；`v699`，正确 |
| T3 | 同会话追问第 3、350 行的常数 | 30,002（复用 29,959，读 43）/ 5 | 0.33 s | `8, 4`，**错**，应为 `8,6` |
| T4 | 无关短会话，使上一会话被停放 | 23 / 2 | 0.74 s | `2`，正确；日志 `conversation cache: parked 30006 tokens in 507.6 ms` |
| T5 | 回到 T2/T3 会话，问第 648 行 | 30,037（复用 30,006，读 31）/ 3 | 0.50 s | `12`，正确；日志 `conversation cache: restored 30006 tokens (live) in 116.6 ms` |

KV 流式统计（引擎日志）：
- 30K 冷读：`91.30% of 382056 block reads hit VRAM, 133.8 MiB read from RAM`；
- 恢复后的追问：`86.87% of 215664 block reads hit VRAM, 114.1 MiB read from RAM`。

T1、T2 和上一次部署冒烟的数字不可直接比较：都是单次请求，长度也不同（上次长读入为 27,155 token，3,588 tok/s）。

### 2.3 T3 错答的复核（`workspace/o09/kvres_retr.py`，21:41:12～21:41:33）

做法：
- 固定种子的同类文档（约 30K token），读一次，答 `v699`，正确。
- 13 个位置各追问一次 greedy、一次 Pi 采样：第 3 / 50 / 120 / 200 / 280 / 346 / 350 / 359 / 420 / 500 / 580 / 648 / 690 行。346 与 359 的常数都是 4，即 T3 错答的值。
- 再把 T3 的原题“第 3 行和第 350 行”各问 3 次 greedy、3 次采样。

| 检查 | 结果 |
|---|---|
| 单位置 greedy | 13/13 |
| 单位置 Pi 采样 | 13/13 |
| 原题 greedy | 3/3（`8, 6`） |
| 原题 Pi 采样 | 3/3（`8, 6`） |

判断：
- 事实：另一份固定文档的同类检索任务在 KVRES 下 32 问全对；实验室质量补测里 4K～123K 检索两臂都是 25/25。
- 推断：T3 是 T 1.0 + thinking 关下的单次采样错答，取到了相邻行的常数（第 346 行的 4）。
- 未排除：T3 那份随机文档的种子没有记录，无法在两臂上重放它。若真实使用中再出现中段检索错答，需要按同一文档在 `--kv-resident 0` 上对照。

### 2.4 停机

- 21:41:59 EDT `systemctl stop`（经 sudo 包装）。
- 停后 `inactive`、仍 `enabled`；GPU 显存 1 MiB，没有 `strata-host` 进程，温度 47 °C。

## 3. 未验证

以下为本次 10-26 部署窗口的未覆盖项。10-27 的补充验证范围与结果以 [组合验证报告](P3-COMBINATION-KVRES-20261027.md) 为准；本轮只补充了所列恢复与负载观察，不代表完整 128K 或长期热稳定性验证。

- **真实 Pi 长会话里的净收益：** decode +2.8%～+4.4% 与冷读 / 追问读入代价都来自实验室配对，生产上只做了冒烟。
- **64K 以上会话的停放与恢复：** 本次只恢复了 30K 的会话。
- **发热：** KVRES 与 AUTOMAX 叠加后的长时间温度没有测；冷读多了 `kv stage`，GPU 负载时间略长。
- **历史实验室基线与生产不同：** 10-26 实验室 `deployed_config` 指向 0.1.43.1 的配置，base 是 K/V 全驻显存（9420 槽）。这些历史 campaign 的数字相对旧 base；10-27 组合验证另行冻结当前完整配置，两臂仅 KVRES 不同，不能混用基线。

## 4. 回滚

```
cp /home/hhtele/strata-0.2.3/backup-20261026-kvres/strata-iq3_xxs.json /home/hhtele/strata-0.2.3/strata-iq3_xxs.json
sudo systemctl restart openclaw-qwen38-next   # 若当时是停机状态，则只拷配置，不启动
```

- 冷加载约 30 s。
- 再往前回到 10-26 上午之前的状态，用 `backup-20261026/`，见 [DEPLOY-PROD-20261026](DEPLOY-PROD-20261026.md) 第 3 节。

## 5. 数据

- 29：`/home/hhtele/strata-0.2.3/strata-iq3_xxs.log`（引擎，21:38:31 起）、`run-iq3xxs.out`（服务层回执）。
- 脚本：`workspace/o09/kvres_smoke.py`、`workspace/o09/kvres_retr.py`。
