#!/usr/bin/env bash
set -euo pipefail
MODE=${1:---check}
PKG=${NVIDIA_DRIVER_PACKAGE:-nvidia-driver-580}
if [ ! -f /etc/os-release ]; then echo 'Unsupported OS: /etc/os-release missing'; exit 2; fi
. /etc/os-release
case "${ID:-}" in ubuntu) ;; *) echo "Refusing automatic driver operation on ID=${ID:-unknown}. Follow distro NVIDIA instructions."; exit 2;; esac

echo "Target driver package: $PKG"
echo 'This helper does NOT remove or install CUDA Toolkit packages.'
apt-cache policy "$PKG" || true
if [ "$MODE" = '--check' ]; then
  echo "Check only. If Candidate is available, run: $0 --apply"
  exit 0
fi
[ "$MODE" = '--apply' ] || { echo "Usage: $0 --check|--apply"; exit 2; }

sudo apt-get update
apt-cache show "$PKG" >/dev/null 2>&1 || { echo "Package $PKG unavailable in configured repositories."; exit 3; }
sudo apt-get install -y "$PKG"
echo 'Driver package installed. Reboot is mandatory before continuing.'
echo 'After reboot verify nvidia-smi and rerun scripts/preflight.sh.'
