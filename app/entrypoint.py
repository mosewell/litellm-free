import json, os, time, subprocess, sys
from pathlib import Path
from discover_models import discover_models
from generate_config import generate_config

CACHE = Path("/data/models_cache.json")

print("[entrypoint] starting model discovery", file=sys.stderr)
try:
    discover_models()
    print("[entrypoint] model discovery complete", file=sys.stderr)
except Exception as e:
    if CACHE.exists():
        print(f"[entrypoint] model discovery failed ({e}); falling back to existing cache", file=sys.stderr)
    else:
        print(f"[entrypoint] model discovery failed ({e}) and no cache to fall back on", file=sys.stderr)
        raise

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
