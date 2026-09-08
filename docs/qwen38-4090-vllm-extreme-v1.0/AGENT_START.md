# Autonomous Execution Entry Point

This package is intentionally executable by an AI coding/ops agent with minimal human interaction.

## Goal

Deploy and qualify the `huge-mtp` patched-vLLM profile on one RTX 4090 24 GiB while preserving the machine's existing CUDA 12.3 toolkit and llama.cpp installation.

## Non-negotiable constraints

1. Never uninstall or overwrite the existing CUDA 12.3 toolkit in the preferred path.
2. Never delete or modify the user's existing llama.cpp models/configuration.
3. Do not attempt CUDA-13 userspace on driver 545.23.08; stop and report the driver gate.
4. Do not claim a 200K context result from a configured context ceiling. The benchmark must report actual `prompt_tokens` >= 185K.
5. Do not accept silent truncation.
6. Do not edit benchmark test sources under `fixtures/*/src/test` or any `verify.sh` file.
7. Preserve raw logs and JSON results under `logs/` and `results/`.

## Execution sequence

```bash
cp -n configs/benchmark.env.example configs/benchmark.env
./scripts/preflight.sh | tee logs/preflight.log
```

If the driver is below R580, preferred path:

```bash
# Review first. This changes only the NVIDIA driver, not /usr/local/cuda-12.3.
./scripts/upgrade_driver_only_ubuntu.sh --check
# If Ubuntu and package availability is confirmed:
./scripts/upgrade_driver_only_ubuntu.sh --apply
# Reboot is mandatory. Continue only after nvidia-smi works again.
```

After reboot:

```bash
./scripts/preflight.sh
./scripts/setup_upstream.sh
./scripts/prepare_model.sh
./scripts/start_server.sh huge-mtp
./scripts/wait_server.sh
nohup ./scripts/run_all.sh configs/benchmark.env > logs/nohup-suite.log 2>&1 &
```

Monitor:

```bash
tail -f logs/nohup-suite.log
watch -n 2 nvidia-smi
```

At completion read:

```text
results/FINAL_REPORT.md
results/summary.json
```

If `huge-mtp` is `GO`, optionally repeat only the short profile comparison:

```bash
./scripts/stop_server.sh
./scripts/start_server.sh fast-dflash2
./scripts/wait_server.sh
QUICK_ONLY=1 ./scripts/run_all.sh configs/benchmark.env
```

Do not run a full multi-profile matrix by default; it violates the one-hour objective.
