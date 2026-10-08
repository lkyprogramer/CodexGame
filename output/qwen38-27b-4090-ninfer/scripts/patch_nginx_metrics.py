#!/usr/bin/env python3
from pathlib import Path

src = Path("/tmp/openclaw-28343.conf")
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
    text = text.replace(needle, block + needle, 1)
    src.write_text(text)
    print("METRICS_LOC_WRITTEN")
