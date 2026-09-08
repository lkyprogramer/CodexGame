# Preferred Deployment: Keep Host CUDA Toolkit 12.3

## Meaning of "do not upgrade CUDA"

This path preserves the existing host CUDA Toolkit 12.3 installation. It does **not** preserve the old GPU driver, because the pinned runtime is CUDA 13 and the reference container explicitly requires a driver that can execute CUDA 13 (R580+).

```text
BEFORE
Driver 545.23.08
Host CUDA Toolkit 12.3

AFTER preferred path
Driver R580+
Host CUDA Toolkit 12.3 unchanged
CUDA 13 userspace only inside Docker
```

This is the lowest-impact way to introduce the patched vLLM stack while leaving existing llama.cpp/CUDA-12.3 development environments intact.

## Stage 0 — preflight

```bash
./scripts/preflight.sh
```

Expected current result: driver gate fails, CUDA Toolkit 12.3 is simply reported.

## Stage 1 — driver only

Ubuntu helper:

```bash
./scripts/upgrade_driver_only_ubuntu.sh --check
./scripts/upgrade_driver_only_ubuntu.sh --apply
sudo reboot
```

The helper refuses non-Ubuntu systems and refuses to remove CUDA packages. Review the chosen driver package before applying.

After reboot:

```bash
nvidia-smi
nvcc --version
```

Success means:

- driver is R580 or newer;
- `nvcc` can still report the old host Toolkit 12.3 — that is expected.

## Stage 2 — Docker/NVIDIA runtime

Install Docker Engine and NVIDIA Container Toolkit if absent, then verify:

```bash
docker run --rm --gpus all nvidia/cuda:13.0.1-base-ubuntu24.04 nvidia-smi
```

If this fails, do not proceed to vLLM.

## Stage 3 — pinned upstream

```bash
./scripts/setup_upstream.sh
```

This pins the reference implementation to the revision recorded in `configs/source.lock`.

## Stage 4 — build and prepare weights

```bash
./scripts/prepare_model.sh
```

This performs the upstream idempotent sequence:

1. download W4A16 AutoRound target;
2. int8 lm-head preparation;
3. int8 embedding preparation;
4. MTP preparation and draft vocabulary;
5. optional fast target variant;
6. W4A16 DFlash2 draft preparation;
7. install KVarN and the pinned vLLM patches in the container image.

## Stage 5 — long-Agent server

```bash
./scripts/start_server.sh huge-mtp
./scripts/wait_server.sh
```

Then:

```bash
curl http://127.0.0.1:18020/v1/models   -H "Authorization: Bearer $(grep '^API_KEY=' configs/benchmark.env | cut -d= -f2-)"
```

## Strict no-driver-change path

`Driver 545 + CUDA 12.3` is a **NO-GO for this pinned cu130 container**. Do not attempt to solve this with a CUDA compatibility package or library-path tricks: the kernel driver itself is below the container stack's minimum.

If the driver cannot be upgraded, keep using the current llama.cpp WORK deployment and postpone this stack.
