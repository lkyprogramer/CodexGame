# Full Host Upgrade Path: Driver + CUDA 13

Use this only if you want the native venv/source stack or want CUDA 13 tooling available outside Docker.

## Recommended order

1. Upgrade NVIDIA driver to R580+.
2. Reboot and verify `nvidia-smi`.
3. Install CUDA Toolkit 13.0 **side-by-side** rather than deleting 12.3.
4. Keep `/usr/local/cuda-12.3` available for existing work.
5. Point the vLLM environment explicitly at CUDA 13.

Example layout:

```text
/usr/local/cuda-12.3
/usr/local/cuda-13.0
/usr/local/cuda -> choose explicitly per shell/project
```

Helper:

```bash
./scripts/install_cuda13_host.sh --check
./scripts/install_cuda13_host.sh --apply
```

The package still recommends Docker for reproducibility even after the host upgrade. Native source/venv mode should be considered an optimization/development environment, not the first production qualification target.

## Why Docker remains preferred

The pinned upstream container freezes:

- Python 3.12;
- vLLM 0.27.1;
- torch 2.13 / cu130;
- Triton 3.7.1;
- KVarN port;
- custom vLLM patches;
- compile/JIT cache locations.

That makes benchmark results easier to reproduce and prevents Python/CUDA dependency changes from contaminating your normal Java/llama.cpp workstation.
