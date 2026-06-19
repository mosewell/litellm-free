import os, json, sys, time, signal
from pathlib import Path

CACHE = Path("/data/models_cache.json")
PID_FILE = Path("/tmp/litellm.pid")

for item in open("/proc/1/environ", "rb").read().split(b"\0"):
    if b"=" in item:
        k, v = item.split(b"=", 1)
        os.environ.setdefault(k.decode(), v.decode())

REFRESH_DAYS = int(os.getenv("MODEL_REFRESH_DAYS", "30"))

def cache_valid():
    if not CACHE.exists():
        return False
    age_days = (time.time() - CACHE.stat().st_mtime) / 86400
    return age_days < REFRESH_DAYS

if cache_valid():
    print("[cron] cache is fresh, nothing to do", file=sys.stderr)
    sys.exit(0)

print("[cron] cache expired, refreshing models", file=sys.stderr)
from discover_models import discover_models
from generate_config import generate_config

discover_models()
generate_config()

if PID_FILE.exists():
    pid = int(PID_FILE.read_text())
    os.kill(pid, signal.SIGTERM)
    print(f"[cron] signalled litellm (pid {pid}) to restart", file=sys.stderr)
else:
    print("[cron] no litellm PID file found", file=sys.stderr)
