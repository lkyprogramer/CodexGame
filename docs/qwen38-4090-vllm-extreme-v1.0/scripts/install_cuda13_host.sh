#!/usr/bin/env bash
set -euo pipefail
MODE=${1:---check}
if [ ! -f /etc/os-release ]; then echo unsupported; exit 2; fi
. /etc/os-release
case "${ID:-}" in ubuntu) ;; *) echo "Automatic helper only supports Ubuntu."; exit 2;; esac
PKG=${CUDA13_PACKAGE:-cuda-toolkit-13-0}
echo "Host toolkit package: $PKG"
apt-cache policy "$PKG" || true
if [ "$MODE" = '--check' ]; then exit 0; fi
[ "$MODE" = '--apply' ] || { echo "Usage: $0 --check|--apply"; exit 2; }
sudo apt-get update
apt-cache show "$PKG" >/dev/null 2>&1 || { echo "$PKG not available; configure NVIDIA CUDA repository first."; exit 3; }
sudo apt-get install -y "$PKG"
echo 'Installed side-by-side. Do not remove /usr/local/cuda-12.3.'
