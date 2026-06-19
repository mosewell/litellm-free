import json, os, time, subprocess, sys
from pathlib import Path
from discover_models import discover_models
from generate_config import generate_config

CACHE = Path("/data/models_cache.json")
REFRESH_DAYS = int(os.getenv("MODEL_REFRESH_DAYS", "30"))

def cache_valid():
    if not CACHE.exists():
        return False
    age_days = (time.time() - CACHE.stat().st_mtime) / 86400
    return age_days < REFRESH_DAYS

print("[entrypoint] cache valid:", cache_valid(), file=sys.stderr)

if not cache_valid():
    print("[entrypoint] cache expired or missing, starting model discovery", file=sys.stderr)
    discover_models()
    print("[entrypoint] model discovery complete", file=sys.stderr)

print("[entrypoint] generating litellm config", file=sys.stderr)
generate_config()
print("[entrypoint] config generated", file=sys.stderr)

subprocess.Popen(["cron"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("[entrypoint] cron daemon started", file=sys.stderr)

print("[entrypoint] starting litellm server on 0.0.0.0:4000", file=sys.stderr)

while True:
    proc = subprocess.Popen([
        "litellm",
        "--config", "/data/config.yaml",
        "--host", "0.0.0.0",
        "--port", "4000"
    ])
    Path("/tmp/litellm.pid").write_text(str(proc.pid))
    proc.wait()
    print("[entrypoint] litellm exited, restarting", file=sys.stderr)
    time.sleep(1)
