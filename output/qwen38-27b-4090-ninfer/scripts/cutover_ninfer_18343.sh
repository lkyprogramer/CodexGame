#!/usr/bin/env bash
# Run ON 4090 as hhtele. Installs NInfer as default on 18343 and disables llama.cpp WORK.
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
SRC=/tmp/ninfer-prod
DST=/home/hhtele/ninfer-4090/launch
mkdir -p "$DST" /home/hhtele/ninfer-4090/cache /home/hhtele/ninfer-4090/logs
cp -f "$SRC/production-18343.sh" "$SRC/production-stop.sh" "$SRC/openai_compat_proxy.py" "$DST/"
chmod +x "$DST/production-18343.sh" "$DST/production-stop.sh" "$DST/openai_compat_proxy.py"
python3 -m py_compile "$DST/openai_compat_proxy.py"

"$WRAP" mkdir -p /etc/systemd/system/openclaw-qwen38-work-64k.service.d \
  /etc/systemd/system/openclaw-qwen38-text.service.d
"$WRAP" cp "$SRC/openclaw-qwen38-ninfer.service" /etc/systemd/system/openclaw-qwen38-ninfer.service
"$WRAP" cp "$SRC/conflict-ninfer.conf" /etc/systemd/system/openclaw-qwen38-work-64k.service.d/conflict-ninfer.conf
"$WRAP" cp "$SRC/conflict-ninfer.conf" /etc/systemd/system/openclaw-qwen38-text.service.d/conflict-ninfer.conf
"$WRAP" systemctl daemon-reload
"$WRAP" systemctl disable --now openclaw-qwen38-work-64k.service
"$WRAP" systemctl disable openclaw-qwen38-text.service || true
"$WRAP" systemctl enable --now openclaw-qwen38-ninfer.service
echo CUTOVER_UNIT_STARTED
for i in $(seq 1 150); do
  if curl -fsS --max-time 3 http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
    echo CUTOVER_READY ${i}s
    exit 0
  fi
  sleep 2
done
echo CUTOVER_NOT_READY
systemctl --user is-active openclaw-qwen38-ninfer.service 2>/dev/null || true
"$WRAP" systemctl status openclaw-qwen38-ninfer.service --no-pager -l | tail -n 40
docker logs ninfer-4090-prod 2>&1 | tail -n 40 || true
exit 1
