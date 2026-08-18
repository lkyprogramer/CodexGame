#!/usr/bin/env bash
set -u

SERVICE="openclaw-qwen36-mtp4-128k.service"
ROOT="/home/hhtele/qwen38-27b-4090-20260817"
SUDO_PASS="${SUDO_PASS:?SUDO_PASS is required but is never written to disk}"

was_active="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
was_enabled="$(systemctl is-enabled "$SERVICE" 2>/dev/null || true)"
restore() {
  rc=$?
  if [ "$was_active" = "active" ]; then
    printf '%s\n' "$SUDO_PASS" | sudo -S systemctl start "$SERVICE" >/dev/null 2>&1 || true
  fi
  {
    echo "wrapper_exit_rc=$rc"
    echo "restored_active=$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
    echo "restored_enabled=$(systemctl is-enabled "$SERVICE" 2>/dev/null || true)"
    echo "restored_at=$(date -Is)"
  } >> "$ROOT/logs/service-restore.log"
  unset SUDO_PASS
  exit "$rc"
}
trap restore EXIT INT TERM

if [ "$was_active" = "active" ]; then
  printf '%s\n' "$SUDO_PASS" | sudo -S systemctl stop "$SERVICE"
fi

for _ in $(seq 1 30); do
  used="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
  [ "${used:-999999}" -lt 1500 ] && break
  sleep 2
done

echo "service_before_active=$was_active" > "$ROOT/logs/service-test-window.log"
echo "service_before_enabled=$was_enabled" >> "$ROOT/logs/service-test-window.log"
echo "test_window_started=$(date -Is)" >> "$ROOT/logs/service-test-window.log"

set -o pipefail
python3 "$ROOT/qwen38_eval.py" "$@"
