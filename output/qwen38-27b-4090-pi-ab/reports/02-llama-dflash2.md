# Pi × llama.cpp DFlash2 n=4（160K q4）

时间：2026-09-04 16:15  
现网二进制 **不能** 加载 DFlash2 GGUF。`llama.cpp-qwen38-20260817` 的 `--help` 虽有 `draft-dflash`，实际 `expected 81, got 58`。改用 `/home/hhtele/llama.cpp-qwen38-dflash2-pr27342` + `LD_LIBRARY_PATH` 后加载成功。

配方：V3 `UD-Q4_K_XL-dv3` + `DFlash2-Q4_K_M`，`--spec-type draft-dflash --spec-draft-n-max 4`，`-c 160000` q4 KV，medium thinking，`--cache-prompt`。空载 **22382 / 1835 MiB**。trap 已 restore WORK。

## Pi 同一剧本

| 后端 | P-short | P-loop | 任务 |
|---|---:|---:|---|
| WORK MTP n=2 200K | **4.67s** | 15.26s | 过 |
| Lucebox prefix | **4.26s** | **10.63s** | 过 |
| Lucebox + agent-turn-cache | 4.73s | 12.39s | 过 |
| **llama.cpp DFlash2 n=4 160K** | **7.79s** | **16.23s** | 过 |

DFlash2 草稿接受率 0.58–0.80，mean draft len 3.3–4.2，spec 在干活。末轮 704 completion / 7.6s。JSON `tick=200` 正确，reconnect 护栏读对。

## 判断

- **Pi 短工具环上，DFlash2 n=4 没有打赢现网 WORK，更打不赢 Lucebox+prefix。** 与 2026-08-18「DFlash2 快在代码复述、工具环不占优」同方向；这次任务仍完成，没有崩工具 JSON。
- 不能把生产 `llama-server` 直接改 `--spec-type draft-dflash`。要切必须换 PR27342 那套 so。
- n_max=3/5 本轮未跑：n=4 已是门禁失败（墙钟不优于 WORK），不必为 tok/s 再占卡。
- 未把 DFlash2 写成开机默认。

## 现网

`openclaw/Qwen3.8-27B-WORK`，unit active，22958 MiB。
