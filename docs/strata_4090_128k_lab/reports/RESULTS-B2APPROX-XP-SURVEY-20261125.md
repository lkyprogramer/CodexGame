# B2 近似路由、ECAP/DEFER、Survey S/K/M 实测结果（2026-11-25）

预登记：[B2_APPROX_20261124](../plans/B2_APPROX_20261124.md)、[XP_ECAP_DEFER_20261125](../plans/XP_ECAP_DEFER_20261125.prereg.json)、[SURVEY_20261125](../plans/SURVEY_20261125.prereg.json)。来源调研见 [MEGAKERNEL-SQUID5090-SURVEY](MEGAKERNEL-SQUID5090-SURVEY-20261125.md)。原件在 4090 的 `/data/strata-data/upgrade-gate/`，目录分别为 `b2-approx-20261124/`、`xp-ecap-defer-20261125/`、`survey-20261125/`，日志在 `logs/` 和 `chain*.out`。生产配置没有改动；19:21 UTC 复核 health 200、active。

## 结论

| 项 | 预登记判定 | 说明 |
|---|---|---|
| B2 `TAIL_SKIP=5`（TS5） | 第二阶段 CONTENDED（OCR ≥1 核）；补充判定 STAGE3；305 题门 NONINFERIORITY_ESTABLISHED | 长上下文 +5.05%，门题集 +4.2%。唯一过完两层门的候选。补充判定是偏离，要上生产需用户确认 |
| B2 `TAIL_SKIP=6`（TS6） | NO_PASS（补充判定） | +3.25%，低于 4% 门线 |
| DEFER `=1`（D01） | NO_GAIN | +5.1%，门线被对照噪声抬到 6.65% |
| ECAP 24（E24） | NO_GAIN | +6.3%，同上 |
| DEFER BELOW=1、ECAP 16 | KL 筛除 | KL 0.101 / 0.179 > 0.10 |
| S1 COUPLED、S2 COUPLED+GUMBEL | NO_PASS | 两次平均 +0.2% / +0.5% |
| S3 PROB+top | NO_GAIN_SCREEN | −7.3% |
| L2_PF | INVALID（预登记）；按补充规则有效，筛选 +1.1% | 远低于门线，结论不变 |
| FUSE_WAIT=2、QIL | NO_GAIN_SCREEN | −1.4% / −3.9% |
| GRAPH_PRIO | NO_PASS | 第一次 +2.9%，确认轮 141.9（低于对照） |
| QFUSE、VERIFY_DEVICE_PLAN | NOT_BITWISE | KL 对 B2 0.019 / 0.012：文档称无损，实测不逐位一致 |

## 生产变更（2026-11-26）

用户确认后，把 `/home/hhtele/strata-0.2.17/strata-iq3_xxs.json` 的 `STRATA_ROUTE_TAIL_SKIP` 从 7 改为 5（diff 只有这一行），config sha `d7ee52b0…` → `7fb50fba…`，`IDENTITY.json` 同步更新并加了 changes 记录；备份为 `*.pre-ts5-20261126`。重启前生产已空闲 6 小时以上。`sudo -n systemctl restart` 约 50 秒后 health 200；引擎进程的 env 为 `STRATA_ROUTE_TAIL_SKIP=5`，启动日志打印 "STRATA_ROUTE_TAIL_SKIP=5 is ON"；冒烟请求返回正常。回滚：把备份拷回后重启。

## B2 近似路由

第二阶段（≥32K 的 decode tok/s）：C0a 138.7、C0b 138.3（重跑）；TS5 145.5、TS6 143.0。对照噪声 0.29%，门线 4%。TS5 和 TS6 运行时同机负载为 2.33 / 1.57 核，按预登记（≥1 核即 CONTENDED）不可判；补充判定把阈值放到 4.5 核（OCR 容器已硬限 4 核），记于 `DEVIATION-20261125.json` 和 `VERDICT-SUPPLEMENTARY-20261125.json`。

第三阶段（305 题，对存档的精确路由 ts0，margin 5%）：

| 臂 | pass@1 | pass@2 | decode tok/s |
|---|---|---|---|
| ts0（精确） | 260 | 292 | 115.7 |
| b2（生产） | 257 | 296 | 134.7 |
| TS5 | 262 | 292 | 140.3 |

推断：TS5 质量与精确路由相当，比生产 B2 再快约 4–5%。限制：第二阶段只靠补充判定成立；门题都 <32K 且单轮；pass@2 比 B2 少 4 题，在噪声范围内但方向不利。

## ECAP / DEFER（v0.2.17-xp 树）

构建：v0.2.17 + PT0 + ecap + defer + lab-delay，零 fuzz。两处移植修正已写入 [PORT_NOTES](../patches/v0217-defer-cpu.PORT_NOTES.md)：去掉只改 docs 的 hunk；`kVerifyMaxT` 加命名空间。`ecap_parity` 2520 例通过。

KL（vs B2）：off 0（IDENTITY）、lab 0、dchk 0.017、d01 0.046、e24 0.059 通过；d1 0.101、e16 0.179 筛除。dchk 不为 0：推断是同层加回改变了浮点加法顺序，不是错误。

回放：C0a 146.7、C0b 141.9（重跑）；D01 151.7（ms/窗口 −3.7%，tok/窗口 +1.2%）；E24 153.4（ms/窗口 −1.8%，tok/窗口 +4.3%，重跑）。噪声 3.3%，门线 6.65%，判 NO_GAIN。

## Survey

对照 C1–C5：141.8、141.2、143.8、145.1、146.1（单调上升），噪声 3.41%，门线 6.82%。运行期间同机负载均为 0.013 核：OCR 从约 12:15 UTC 起空闲，0.013 是容器底噪。

| 臂 | 第一次 | 确认轮 | 筛选增益 |
|---|---|---|---|
| S1 | 143.0 | 144.8 | +1.06% |
| S2 | 143.2 | 145.4 | +0.49% |
| S3 | 131.2 | — | −7.28% |
| KL2 | 143.0（INVALID） | — | — |
| KFW | 139.5 | — | −1.41% |
| KQI | 136.9 | — | −3.93% |
| KGP | 146.7 | 141.9 | +2.95% |

S 组所有运行 finish=length 和重复提示均为 0。

M 组（以 C3、C4 均值 18.381 ms/窗口为基准）：

- MD8（8 个空节点/层）：18.137 ms，即每个空节点约 −0.0006 ms。空节点成本低于测量分辨率（对照 ms/窗口波动约 0.25 ms，对应约 0.6 µs/节点），图节点数不是瓶颈。
- MLP（门铃前每层 +20 µs）：18.921 ms，斜率约 0.56。门铃前的路径大约一半在关键路径上；对照波动使斜率误差约 ±0.25。
- MLH（resident 专家后每层 +20 µs）：18.329 ms，斜率约 −0.05，即这段被 CPU 等待完全掩盖。推断：GPU 侧在 hit 之后还有余量，CPU 行才是关键路径，这与调研里"GPU 侧裁剪上限约 1.7–2.3 ms"的判断一致。
- MPF（profile + commit timing）：138.3，仅留作结构记录。

## 偏离与无效运行

1. OCR 实测 2–4 核（用户说已空闲），B2 第二阶段因此 CONTENDED，改用补充判定（4.5 核），并据此跑了 TS5 第三阶段。
2. 树标签由 `xp0217` 改为 `v0.2.17-xp`（prepare 要求 tag-后缀形式），在冻结前改，远端冻结版与本地一致。
3. 8 次运行因"引擎请求 121 个、未对齐"无效（每个运行最多重跑一次，失败件都保留为 `*.failed*`）。其中 6 次可完全解释为思考达到 12288 预算后服务端续写回答（一次 HTTP 请求在引擎日志里记成两条）；B2 C0b 第一次、KL2.failed1、TS5.failed3 是别的原因。检查结果在 `logs/split-check-20261125.json`。预登记判定照原规则；补充规则只影响 KL2，不改变任何结论。
4. 测试链 chain5d 因 `pgrep -f` 匹配到等待命令自身而空等约 1 小时 23 分，对数据无影响。

## 解读与下一步建议

- 本次会话的对照噪声为 3.3–3.4%，是 11-23 ABBA（0.6%）的 5 倍以上，主要来自 tok/窗口，也就是采样文本不同导致的接受长度差异。两个对照分辨不出 3–6% 的收益。D01 和 E24 的 ms/窗口都下降了，方向一致，但证据不够。若要复测，建议 ABBA×2 以上，并按 ms/窗口和 tok/窗口分别预登记门线；本轮没有运行。
- 本轮 TS5 是唯一的上线候选：生产 env 从 `STRATA_ROUTE_TAIL_SKIP=7` 改为 `5`。这需要用户确认；回滚就是改回 7 再重启。
- K 组（无损开关）和 S 组（采样投机）在 4090 上都没有收益，这条线可以关闭。QFUSE、VERIFY_DEVICE_PLAN 不逐位一致，以后若有人认为它们无损，以本次 KL 为准。
