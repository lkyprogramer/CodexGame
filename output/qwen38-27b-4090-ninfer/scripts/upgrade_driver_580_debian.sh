#!/usr/bin/env bash
# Debian 12: install cuda-drivers-580 from NVIDIA debian12 repo (nvidia.cn).
# Does NOT install/remove CUDA Toolkit 12.3. Requires reboot after --apply.
set -euo pipefail
MODE=${1:---check}
WRAP=${WRAP:-/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh}
REPO=https://developer.download.nvidia.cn/compute/cuda/repos/debian12/x86_64
KEYDEB=/tmp/cuda-keyring_1.1-1_all.deb
root() { "$WRAP" "$@"; }

echo "OS: $(. /etc/os-release; echo $ID $VERSION_ID)"
echo "Current: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo unknown)"
dpkg -l cuda-toolkit-12-3 >/dev/null
echo "cuda-toolkit-12-3 is installed (will hold)"

if [ ! -f /usr/share/keyrings/cuda-archive-keyring.gpg ] && [ ! -f /usr/share/keyrings/cuda-*-keyring.gpg ]; then
  echo "Need cuda-keyring"
fi

case "$MODE" in
  --check)
    echo "Would: dpkg -i cuda-keyring if needed; apt-get update; apt-mark hold cuda-toolkit-12-3; apt-get install --no-install-recommends cuda-drivers-580"
    apt-cache policy cuda-drivers-580 2>/dev/null | head -n 8 || echo "cuda-drivers-580 not in apt yet (repo not enabled)"
    exit 0
    ;;
  --apply) ;;
  *) echo "Usage: $0 --check|--apply"; exit 2 ;;
esac

curl -fsSL --retry 3 -o "$KEYDEB" "$REPO/cuda-keyring_1.1-1_all.deb"
root dpkg -i "$KEYDEB"
# Prefer nvidia.cn over .com in case the keyring writes developer.download.nvidia.com
if [ -f /etc/apt/sources.list.d/cuda-debian12-x86_64.list ]; then
  root sed -i 's|developer.download.nvidia.com|developer.download.nvidia.cn|g' /etc/apt/sources.list.d/cuda-debian12-x86_64.list || true
  root bash -c "echo 'deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] $REPO/ /' > /etc/apt/sources.list.d/cuda-debian12-x86_64.list"
fi
root apt-get update
root apt-mark hold cuda-toolkit-12-3 cuda-toolkit-12-3-config-common cuda-toolkit-12-config-common cuda-toolkit-config-common
apt-cache policy cuda-drivers-580 || true
root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cuda-drivers-580
dpkg -l cuda-toolkit-12-3 cuda-drivers-580 nvidia-driver 2>/dev/null | awk '{print $1,$2,$3}' || true
echo "APPLY_OK reboot required"
echo "nvcc still: $(/usr/local/cuda-12.3/bin/nvcc --version | tail -n 1)"
