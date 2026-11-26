#!/usr/bin/env bash
# Read-only NVIDIA driver fingerprint guard.
#   snapshot <file>      write the current fingerprint
#   check <baseline>     compare the current fingerprint with <baseline>
#   compare <a> <b>      compare two fingerprint files
#   scan <log>           look for driver-related lines in installer output
# Exit codes: 0 unchanged / clean, 3 DRIVER RISK (stop everything and notify the user), 2 usage error.
set -u -o pipefail

collect() {
  echo "## kernel"; uname -r
  echo "## proc_driver_version"; cat /proc/driver/nvidia/version 2>/dev/null || echo unreadable
  echo "## nvidia_smi"; nvidia-smi --query-gpu=driver_version,name,uuid,pci.bus_id --format=csv,noheader 2>&1
  echo "## modinfo_version"; { /sbin/modinfo -F version nvidia 2>/dev/null || modinfo -F version nvidia 2>/dev/null; } || echo unavailable
  echo "## module_files"
  find "/lib/modules/$(uname -r)" -name 'nvidia*.ko*' -printf '%p %s %TY-%Tm-%Td_%TH:%TM\n' 2>/dev/null | LC_ALL=C sort
  echo "## dpkg"
  dpkg-query -W -f='${Package} ${Version} ${Status}\n' 2>/dev/null | grep -Ei 'nvidia|libcuda|cuda-drivers|cuda-compat' | LC_ALL=C sort
  echo "## libcuda"
  local ldc p r
  ldc=$(command -v ldconfig || echo /sbin/ldconfig)
  p=$("$ldc" -p 2>/dev/null | awk '/libcuda\.so\.1 /{print $NF; exit}')
  if [ -n "$p" ]; then r=$(readlink -f "$p"); echo "$r"; sha256sum "$r" | cut -d' ' -f1; else echo none; fi
}

compare() {
  if diff -u "$1" "$2"; then echo "driver fingerprint unchanged"; return 0; fi
  echo "DRIVER FINGERPRINT CHANGED: stop all work and notify the user" >&2
  return 3
}

pattern='nvidia[-_ ]?driver|cuda-drivers|nvidia-kernel|nvidia-dkms|\bdkms\b|kernel[ -]module|nouveau|modprobe|rmmod|insmod|/lib/modules|libnvidia-compute|nvidia-open'

case "${1:-}" in
  snapshot)
    [ $# -eq 2 ] || { echo "usage: $0 snapshot <file>" >&2; exit 2; }
    [ -e "$2" ] && { echo "refusing to overwrite existing baseline $2" >&2; exit 2; }
    collect > "$2"; echo "wrote $2" ;;
  check)
    [ $# -eq 2 ] && [ -f "$2" ] || { echo "usage: $0 check <baseline>" >&2; exit 2; }
    tmp=$(mktemp); collect > "$tmp"; compare "$2" "$tmp"; rc=$?; rm -f "$tmp"; exit $rc ;;
  compare)
    [ $# -eq 3 ] && [ -f "$2" ] && [ -f "$3" ] || { echo "usage: $0 compare <a> <b>" >&2; exit 2; }
    compare "$2" "$3"; exit $? ;;
  scan)
    [ $# -eq 2 ] && [ -f "$2" ] || { echo "usage: $0 scan <log>" >&2; exit 2; }
    hits=$(grep -Eni "$pattern" "$2" | grep -vi 'cuda-driver-dev' || true)
    if [ -n "$hits" ]; then
      printf '%s\n' "$hits"; echo "DRIVER-RELATED OUTPUT FOUND: stop and notify the user" >&2; exit 3
    fi
    echo "scan clean: $2" ;;
  *) echo "usage: $0 snapshot|check|compare|scan ..." >&2; exit 2 ;;
esac
