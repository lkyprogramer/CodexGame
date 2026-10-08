# Qwen3.8-27B NInfer · B0+B1 上线记录

机器：`192.168.10.29`（hhtele）  
GPU：单卡 RTX 4090  
记录日期：2026-09-30  
状态：已切到候选镜像。本次没有重建镜像，也没有改 NGINX、权重、采样和上下文。

不要把 NGINX token、SSH 密码、sudo 口令写进 git。

这是 2026-09-30 这次切换的部署记录。架构、兼容层和 llama.cpp 回滚仍以 [`openclaw-qwen38-ninfer.md`](openclaw-qwen38-ninfer.md) 为准；该文 2026-09-08 的镜像表已经过期。构建和门禁的原计划在 `docs/ninfer-44a2c6c-frontend-optimization-v2/docs/10_BUILD_DEPLOY_ROLLBACK.md`，不代替本文的现网身份。

---

## 1. 现在在跑什么

| | |
|---|---|
| systemd | `openclaw-qwen38-ninfer.service`，`Type=simple`，`TimeoutStartSec=300` |
| 启动脚本 | `/home/hhtele/ninfer-4090/launch/production-18343.sh` |
| 脚本镜像行 | `IMAGE=ninfer-4090:frontend-b0-b1-1dacb0f` |
| 容器 | `ninfer-4090-prod` |
| 运行镜像 | `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3` |
| 回滚标签 | `ninfer-4090:prepare-detail` 仍是 `sha256:9c2dec8b9ff087d178f72b68251ff7ff18c77330833eaade5b40bf4c49eb312b` |
| 脚本备份 | `/home/hhtele/ninfer-4090/launch/production-18343.sh.bak-20260930-cutover` |
| 切换时间 | 2026-09-30 02:31:53 -04:00 |
| 模型 ID | `openclaw/Qwen3.8-27B-WORK` |
| 对外 | 兼容层 `0.0.0.0:18343`；引擎 `127.0.0.1:18030`；NGINX `28343` 未改 |
| 权重 | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`，容器内只读挂到 `/opt/ninfer/models/qwen3_8_27b.ninfer` |
| 请求日志 | `/home/hhtele/ninfer-4090/logs/ninfer-request.jsonl` |

主机上的启动脚本是权威。笔记本里的 `output/qwen38-27b-4090-ninfer/scripts/` 副本是旧的，不要 scp 覆盖主机脚本。

一张 4090 只跑一个约 22GB 的服务。这个 unit 与 WORK、TEXT 互斥。`ninfer-g1-devel` 没有 GPU，不要为这次上线删掉它。

---

## 2. 这次相对旧镜像改了什么

旧镜像是 `ninfer-4090:prepare-detail`。它从 `44a2c6c` 加上当时未推送的本地补丁做成，已经写 schema 20。热的续写请求里，`prepare_detail.tokenize` 几乎是整段重新分词。

新镜像在这之上换了前端，服务行为有两处变化：

- B0：added token 按 ID 分桶后单调向前扫描。命中规则是最早起点，同一起点取最小 ID。不再整段反复 `text.find`。
- B1：聊天边界从已选中的 token 重启校验。前缀的 token id、type、position 都对上时走 `append_frontier`；否则用最深的 turn checkpoint。不再为了校验边界把整段前缀重新编码。

schema 20 的字段含义没有改：

- `prepare_detail.tokenize` 仍包住整段 `encode_rendered_chat`。
- `rendered_chars` 仍是渲染结果的 UTF-8 字节数。
- JSONL 不写 `tokenize_impl`，也不写 B1 的内部计数。

`request_done.prepare_detail` 的六段是 `serve_convert`、`frontend_convert`、`template_render`、`tokenize`、`positions_identity`、`engine_submit`。

没有改的部分：模型 ID、端口、NGINX、权重、`--max-context 262144`、`--kv-capacity 262144`、`rk4v4-e8`、MTP `--draft-tokens 3 --lm-head-draft`、L1 6144 / L2 8192、`--prefix-checkpoint-policy rolling-tool`、`--preserve-thinking`、采样 `temperature 1.0 --top-p 0.95 --top-k 20 --presence-penalty 0.0`、`--max-concurrency 1`。请求自己的 `temperature` 仍覆盖命令行，范围 `[0, 2]`。

兼容层行为不变。`enable_thinking: false` 由代理写成 `reasoning_effort=none`。客户端不要直接送 `reasoning_effort=none`，引擎会回 HTTP 400。省略 `enable_thinking` 时代理仍默认 medium。

冷启动的 TTFT 几乎不变，时间在 prefill。这次上线缩短的是续写时的 tokenize，不是 240K 第一次 prefill。

---

## 3. 源码和镜像各自是什么

产品仓库在 `output/qwen38-27b-4090-ninfer/ninfer-4090`，分支 `b0-scanner`。`lkyprogramer` 对 `tensorninja/ninfer-4090` 只有读权限，分支推到了 fork：

`https://github.com/lkyprogramer/ninfer-4090` `b0-scanner`  
`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`

从 `44a2c6c` 往后，和线上行为有关的提交是：

| 提交 | 内容 | 是否在运行镜像里 |
|---|---|---|
| `6b4286d` | B0 单调扫描 | 在 |
| `e924cc2` | 请求内 tokenizer work 计数 | 在。计数不进 JSONL |
| `1d05441` | 选中 token 的重启轨迹 | 在 |
| `a5128f0` | B1 从重启点校验聊天边界 | 在 |
| `f3b231d` | schema-20 `prepare_detail` 计时 | 源码与镜像内 overlay 一致。镜像构建时这 11 个文件还没提交 |
| `1dacb0f` | CPU 对照 harness | 不在。`BUILD_TESTING=OFF` |
| `46320bd` | `Dockerfile.sm89-nobake` | 构建配方，不是容器里的一层业务代码 |
| `7c9d959` | linear swiglu 把无 CUDA 的 skip 77 传出 main | 不在 |
| `e0b05f7` | G1 差分驱动 | 不在 |
| `d5d2e17` `c782577` | 基线身份和 44a2c6c oracle | 不在 |

运行镜像是切换前已经打好的 `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`。2026-09-30 没有用 `e0b05f7` 重建，也没有把 `prepare-detail` 标签改到新 digest 上。因此 G0 不能算通过：资源指纹当时自标 `LOCAL_BYTES_MEASURED_NOT_PRODUCTION_CERTIFIED`。六个前端资源文件合计 SHA-256 `c8afe487da2dd305125cd7421a668bd55cadd632b13b0999956a7300d3917a51`。

构建时的身份：

| 对象 | SHA-256 |
|---|---|
| schema-20 overlay（11 个文件，与 `f3b231d` 的 diff 一致） | `579c0853f2ea690fd779861766f2530f213af2c990db023c3dfaeb2d01df01eb` |
| `Dockerfile.sm89-nobake` | `3f1fd17dbb4599a135958e166101cde3fdc03a369b0e7b25ab087d8a210e7cdc` |
| 权重文件（沿用旧制品，只读挂载，不用 HF `main`） | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` |

---

## 4. 启动命令

脚本只允许改 `IMAGE=`。下面是主机脚本里的启动参数，切换前后比对过：命令、入口、网络、runtime、GPU 请求和三个挂载都相同。Docker 不保证 `HostConfig.Binds` 的顺序，顺序不同不是参数变化。

```bash
IMAGE=ninfer-4090:frontend-b0-b1-1dacb0f
docker run -d --name ninfer-4090-prod --gpus all --restart=no --network host \
  -v /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer:/opt/ninfer/models/qwen3_8_27b.ninfer:ro \
  -v /home/hhtele/ninfer-4090/cache:/var/cache/ninfer \
  -v /home/hhtele/ninfer-4090/logs:/var/log/ninfer \
  "$IMAGE" \
  /opt/ninfer/models/qwen3_8_27b.ninfer \
  --model-id openclaw/Qwen3.8-27B-WORK \
  --host 127.0.0.1 --port 18030 \
  --max-context 262144 --kv-capacity 262144 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib 6144 \
  --continuation-cache-l2-mib 8192 \
  --request-log-jsonl /var/log/ninfer/ninfer-request.jsonl \
  --preserve-thinking \
  --default-max-tokens 32768 \
  --temperature 1.0 --top-p 0.95 --top-k 20 --presence-penalty 0.0
```

脚本在 `18030 /v1/models` 可用后 `exec` 兼容层。日志文件的日期不是当天时，脚本会按天转走 `ninfer-request.jsonl`。`systemctl restart` 对 `Type=simple` 只表示进程已拉起，不表示模型已就绪。用两个 `/v1/models` 判断。

重启用：

```bash
/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh \
  systemctl restart openclaw-qwen38-ninfer.service
```

重启前看 `ss -H -tn state established '( sport = :18343 )'`。已有连接时不要停 unit。

---

## 5. 回滚

回滚目标是 `sha256:9c2dec8b9ff087d178f72b68251ff7ff18c77330833eaade5b40bf4c49eb312b`。不要把 `prepare-detail` 标签改到新镜像上，也不要同时留下两个模型进程。

```bash
cp -a /home/hhtele/ninfer-4090/launch/production-18343.sh.bak-20260930-cutover \
  /home/hhtele/ninfer-4090/launch/production-18343.sh
# 确认第 6 行是 IMAGE=ninfer-4090:prepare-detail
/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh \
  systemctl restart openclaw-qwen38-ninfer.service
```

就绪后再查三件事：容器镜像是上面的旧 digest，`18343` 和 `18030` 的 `/v1/models` 都是 `openclaw/Qwen3.8-27B-WORK`，再打一条小的 medium 工具请求。只看进程在不能算回滚完成。

出现 token 或 hint 对不上、新的 `request_error`、或短请求稳定变慢时，按上面退回。冷启动 prefill 变长不是这次优化的回退。

---

## 6. 上线前已经做完的检查

证据在 `output/qwen38-27b-4090-ninfer/b0-evidence/`。

- G1：固定用例、不超过 256 字节的全切、每个 profile 20000 条 mutation，种子 `20260925`，对照隔离的 `44a2c6c` oracle。差分通过，token 不一致为空。
- 镜像内 CPU ctest 重新分类后是 31 通过、71 个资源跳过（退出码 77）、0 失败。GPU 数值用例没有跑，跳过不是通过。
- 32K / 128K / 192K / 240K HTTP 对照跑完后已退回旧镜像。56 个 POST 都是 HTTP 200，`token_mismatch` 为空，没有 `request_error`。
- T13 独立审查结论是 `APPROVE_FOR_AUTHORIZED_RELEASE`。审查同时写明 G0 不是 PASS，G6 当时没执行。记录在 `b0-evidence/ladder/t13-review.md`。

续写 tokenize 按档位看，不合成一条中位数。下面是 `verdict.json` 里 `index>0` 的 6 条 sample，`prepare_detail.tokenize` 中位数，旧镜像到新镜像：

| 档 | 冷 prompt tokens | 旧 tokenize | 新 tokenize | 新/旧 |
|---|---:|---:|---:|---:|
| 32K | 32933 | 0.914s | 0.039s | 4.3% |
| 128K | 131006 | 2.826s | 0.172s | 6.1% |
| 192K | 196806 | 4.052s | 0.250s | 6.2% |
| 240K | 245974 | 5.064s | 0.305s | 6.0% |

240K 冷 TTFT 是 149.877s 到 149.109s，prefill 分别是 145.228s 和 148.420s。冷请求的时间在 prefill。

唯一的路径差异是 temperature 0、240K、index 1–6：旧镜像 `full_reset` 且 hit 为 0，新镜像 `restore_turn_checkpoint`。temperature 1.0 四档的路径一致。这不是 token 不一致，所以上线没有改 cache 参数。

更早一次短样本里，index 4 在 temperature 1.0 出现过旧 `restore` hit 1417、新 `append_frontier` hit 1436。后来这四档没有复现。不要把那一条写成这次 ladder 的结果。

---

## 7. 切上去之后的抽查

2026-09-30 切换完成后，在主机 loopback 打了短请求。当时 18343 没有已建立连接。服务镜像仍是 `sha256:e753e228…`。

| 请求 | 结果 |
|---|---|
| `GET /v1/models` | 200，`openclaw/Qwen3.8-27B-WORK`，上下文 262144 |
| 工具 + 流式 + 思考开，`max_tokens` 16 | 200，`prompt_tokens` 270，上限被思考用完，`finish_reason` length，0.454s |
| 思考关，`max_tokens` 16 | 200，`prompt_tokens` 19，`completion_tokens` 2，`finish_reason` stop，正文 `pong`，0.110s |
| 思考开，`max_tokens` 128 | 200，`prompt_tokens` 21，`completion_tokens` 50，`finish_reason` stop，正文 `二`，0.521s |

前三条写入 JSONL 的 `request_done` 都是 schema 20，`prepare_detail` 六段都在，没有 `request_error`。短请求 tokenize 是 1.04ms、0.16ms、0.11ms。三条互不延续，前缀都是 `full_reset`。思考开且 `max_tokens` 只有 16 或 32 时，预算会耗在思考上，正文为空；把上限放到 128 后同一句能正常停住。这是预算，不是接口故障。

---

## 8. 还没有做

- G6 的两段上线后真实流量观察没做。这次只是切过去并做了短请求抽查，G6 不是 PASS。
- G0 不是 PASS。镜像不是从已提交的 `e0b05f7` 重建的。
- GPU 数值 ctest 没有跑。
- 没有做 B2，也没有改 TTL、L2 或路由。
- 若上线后 120K 以上热 tokenize 的 p90 仍长期高于 1 秒，再单独决定要不要做 B2。那不是这次部署的一部分。
