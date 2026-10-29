#!/usr/bin/env bash
set -euo pipefail
candidate=${1:?mini, mini-dspark or ovis}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
if [[ "$candidate" == mini || "$candidate" == mini-dspark ]]; then
    export PATH=/opt/minicpm-ocr/.venv-vllm/bin:$PATH
    export CC=gcc-13 CXX=g++-13
    CUDA_HOME=$(python -c 'import sysconfig; print(sysconfig.get_path("purelib") + "/nvidia/cu13")')
    export CUDA_HOME PATH="$CUDA_HOME/bin:$PATH" FLASHINFER_NVCC="$CUDA_HOME/bin/nvcc"
    speculative_args=()
    if [[ "$candidate" == mini-dspark ]]; then
        speculative_args=(--speculative-config '{"method":"dspark","model":"/models/MiniCPM-OCR-1.0-DSpark","num_speculative_tokens":15,"enable_adaptive_verification":false}')
    fi
    exec vllm serve /models/MiniCPM-OCR-1.0 --served-model-name minicpm-ocr \
        --host 0.0.0.0 --port 18499 --dtype bfloat16 --max-model-len 16384 \
        --max-num-batched-tokens 8192 --max-num-seqs 4 --gpu-memory-utilization 0.65 \
        --no-enable-prefix-caching --mm-processor-cache-gb 0 \
        --limit-mm-per-prompt '{"image":1,"video":0}' \
        --attention-backend FLASH_ATTN --mm-encoder-attn-backend FLASH_ATTN \
        --mm-processor-kwargs '{"downsample_mode":"4x","max_slice_nums":9}' \
        --trust-request-mm-kwargs --default-chat-template-kwargs '{"enable_thinking":false}' \
        "${speculative_args[@]}"
elif [[ "$candidate" == ovis ]]; then
    export PATH=/work/releases/ovis/bin:$PATH
    exec vllm serve /models/OvisOCR3 --served-model-name ovisocr3 \
        --host 0.0.0.0 --port 18500 --dtype bfloat16 --max-model-len 16384 \
        --max-num-batched-tokens 8192 --max-num-seqs 4 --gpu-memory-utilization 0.65 \
        --no-enable-prefix-caching --mm-processor-cache-gb 0 --gdn-prefill-backend triton \
        --limit-mm-per-prompt "{\"image\":${OCR_IMAGE_LIMIT:-1},\"video\":0}" \
        --mm-processor-kwargs "{\"min_pixels\":200704,\"max_pixels\":${OCR_OVIS_MAX_PIXELS:-8294400}}" \
        --default-chat-template-kwargs '{"enable_thinking":false}'
else
    echo 'Unknown candidate' >&2
    exit 2
fi
