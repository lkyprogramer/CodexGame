#!/usr/bin/env bash
# On 4090: add location = /metrics to openclaw-28343.conf (same Bearer as /v1).
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
$WRAP cp /etc/nginx/conf.d/openclaw-28343.conf /etc/nginx/conf.d/openclaw-28343.conf.bak-metrics
$WRAP python3 - <<'PY'
from pathlib import Path
src = Path("/etc/nginx/conf.d/openclaw-28343.conf")
text = src.read_text()
needle = "    location / {"
block = """    location = /metrics {
        default_type text/plain;
        if ($openclaw_authorized = 0) {
            return 401 "{\\"error\\":{\\"message\\":\\"Unauthorized\\",\\"type\\":\\"authentication_error\\",\\"code\\":\\"invalid_api_key\\"}}\\n";
        }

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_pass http://127.0.0.1:18343/metrics;
    }

"""
if "location = /metrics" in text:
    print("METRICS_LOC_EXISTS")
else:
    if needle not in text:
        raise SystemExit("anchor not found")
    Path("/tmp/openclaw-28343.conf.new").write_text(text.replace(needle, block + needle, 1))
    print("METRICS_LOC_WRITTEN")
PY
if [ -f /tmp/openclaw-28343.conf.new ]; then
  $WRAP cp /tmp/openclaw-28343.conf.new /etc/nginx/conf.d/openclaw-28343.conf
  rm -f /tmp/openclaw-28343.conf.new
fi
$WRAP nginx -t
$WRAP systemctl reload nginx
echo NGINX_RELOADED
python3 - <<'PY'
import re, subprocess, urllib.request, urllib.error
conf = subprocess.check_output(
    ["/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh", "cat", "/etc/nginx/conf.d/openclaw-28343.conf"],
    text=True,
)
auth = re.search(r'"(Bearer [^"]+)"', conf).group(1)

def hit(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

s, b = hit("http://127.0.0.1:28343/metrics")
print("NOAUTH", s)
s, b = hit("http://127.0.0.1:28343/metrics", {"Authorization": auth})
print("AUTH28343", s, "bytes", len(b))
text = b.decode("utf-8", "replace")
keys = [
    "llamacpp:prompt_tokens_total",
    "ninfer:prefix_cache_hit_tokens_total",
    "ninfer:requests_total",
    "ninfer:continuation_stable_prefix_restores_total",
]
for k in keys:
    line = next((ln for ln in text.splitlines() if ln.startswith(k + " ")), None)
    print("28343", k, line.split()[-1] if line else "MISSING")
s, b = hit("http://47.106.205.246:1082/metrics", {"Authorization": auth})
print("AUTH1082", s, "bytes", len(b) if s == 200 else b[:80])
if s == 200:
    text = b.decode("utf-8", "replace")
    for k in keys:
        line = next((ln for ln in text.splitlines() if ln.startswith(k + " ")), None)
        print("1082", k, line.split()[-1] if line else "MISSING")
PY
