# 本机 diff 与 v0.1.40.3

核对日期：2026-10-08。当时工作区是 `v0.1.40.1`（`82f46a8`），相对上游有 3 个已修改文件。`v0.1.40.3` 里这三处都已经有等价实现。升级后不要把旧 diff `git apply` 回去。

| 本机改动 | v0.1.40.3 |
|---|---|
| `src/core/vmm.cpp`：`CUDART_VERSION < 12050` 时改用 `cudaGetDriverEntryPoint` | 提交 `b4182a8`（#1071，2026-10-06）已做同样分支，并多清一次失败查询留下的 sticky CUDA error |
| `include/strata/core/vmm.hpp`：`h_[(std::size_t) i]` | 同一行已经是 `std::size_t` |
| `tools/mtp_fetch.py`：`STRATA_MTP_VERIFY_PINNED=1` 仍做 SHA256 | `STRATA_SOURCE=modelscope`（或 `ms`）把 `REPO` 和 `PINNED` 设成同一个 ModelScope `master` URL，`pinned()` 为真，哈希照查 |

`git pull --ff-only` 会被这 3 个脏文件挡住。升级前只丢掉这 3 个文件上的本地 diff，不要 `git reset --hard`，也不要 `git clean`。未跟踪的 `build-engine-only.sh`、`.no-sudo-bin/` 会留下。

```bash
cd /home/hhtele/strata
git diff -- include/strata/core/vmm.hpp src/core/vmm.cpp tools/mtp_fetch.py \
  > /home/hhtele/strata-patches/worktree-before-upgrade.diff
git checkout -- include/strata/core/vmm.hpp src/core/vmm.cpp tools/mtp_fetch.py
git pull --ff-only
/home/hhtele/strata-patches/check-after-upgrade.sh /home/hhtele/strata
```

`checkout` 之后、`pull` 之前，这棵树暂时编不过 CUDA 12.3。不要在这个窗口重编或重启服务。不要 `git stash pop` 把旧 diff 盖回新文件上。

`./update.sh` 在 pull 之后还会跑 `setup.sh --update`。4090（sm_89）走的是现成引擎，不是用 `/usr/local/cuda-12.3` 重编。现成包是 CUDA 13.0，随 pip 轮子带运行库；这台驱动 610.57.04，高于 setup 要求的 580。系统里的 CUDA 12.3 保持不动。要继续用 12.3 自己编，才用 `setup.sh --build`，并且验收脚本必须是 0。

若验收失败，只补缺的那一处，按下面的上游写法，不要套 0.1.40.1 的旧 diff。

`src/core/vmm.cpp` 的 `resolve()`：

```cpp
#if CUDART_VERSION >= 12050
    const cudaError_t e = cudaGetDriverEntryPointByVersion(name, &p, 12000, cudaEnableDefault, &q);
#else   // the versioned query arrived in CUDA 12.5
    const cudaError_t e = cudaGetDriverEntryPoint(name, &p, cudaEnableDefault, &q);
#endif
    if (e != cudaSuccess || q != cudaDriverEntryPointSuccess || p == nullptr) {
        (void) cudaGetLastError();
        return false;
    }
```

`include/strata/core/vmm.hpp`：

```cpp
bool mapped(int64_t i) const { return i >= 0 && i < chunks() && h_[(std::size_t) i] != 0; }
```

`tools/mtp_fetch.py` 在 `PINNED = ...` 之后：

```python
if (os.environ.get("STRATA_SOURCE") or "").strip().lower() in ("ms", "modelscope"):
    MS_ENDPOINT = (os.environ.get("MODELSCOPE_ENDPOINT") or "").strip().rstrip("/") or "https://www.modelscope.cn"
    REPO = PINNED = MS_ENDPOINT + "/models/Qwen/Qwen3.8-Flash-Next/resolve/master/"
```

重新下载 MTP 时用 `STRATA_SOURCE=modelscope`，不要再设 `STRATA_MTP_VERIFY_PINNED`。权重已在 `/data/strata-data/mtp` 时，升级不需要重下。
