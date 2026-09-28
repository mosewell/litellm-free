import os, json, requests, sys
from pathlib import Path
from collections import Counter
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

CACHE = Path("/data/models_cache.json")
PROVIDERS_CONFIG_PATH = os.getenv("PROVIDERS_CONFIG_PATH", "/data/providers.json")
PROBE_TIMEOUT = int(os.getenv("PROBE_TIMEOUT", "20"))
VERBOSE = os.getenv("DISCOVERY_VERBOSE", "").lower() in ("1", "true", "yes")

def log(msg):
    print(f"[discover] {msg}", file=sys.stderr)

def detail(msg):
    print(f"  [discover] {msg}", file=sys.stderr)

def debug(msg):
    if VERBOSE:
        detail(msg)

def excerpt(text, limit=300):
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "..."

def load_providers():
    path = Path(PROVIDERS_CONFIG_PATH)
    if path.exists():
        detail(f"loading provider config from {path}")
        data = json.loads(path.read_text())
    elif os.getenv("PROVIDERS_JSON"):
        detail("loading provider config from PROVIDERS_JSON env var")
        data = json.loads(os.getenv("PROVIDERS_JSON"))
    else:
        log("no provider config found; set PROVIDERS_CONFIG_PATH or PROVIDERS_JSON")
        sys.exit(1)
    log(f"loaded {len(data['providers'])} providers: {', '.join(p['name'] for p in data['providers'])}")
    return data["providers"]

def probe_chat(url, headers, model):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=PROBE_TIMEOUT)
    except Exception as e:
        debug(f"probe {model}: ERROR {type(e).__name__}: {e}")
        return False, type(e).__name__

    if r.status_code == 200:
        debug(f"probe {model}: OK (200)")
        return True, "ok"

    debug(f"probe {model}: FAIL ({r.status_code}) {excerpt(r.text, 200)}")
    return False, f"http_{r.status_code}"

def fetch_catalogue(name, base_url, headers):
    try:
        r = requests.get(f"{base_url}/models", headers=headers, timeout=PROBE_TIMEOUT)
    except Exception as e:
        log(f"{name}: GET /models failed: {type(e).__name__}: {e}")
        return None

    detail(f"{name}: GET {base_url}/models -> {r.status_code}")
    if r.status_code != 200:
        log(f"{name}: GET /models returned {r.status_code}: {excerpt(r.text)}")
        return None

    try:
        return r.json().get("data", [])
    except Exception as e:
        log(f"{name}: GET /models returned a non-JSON body: {excerpt(r.text)} ({e})")
        return None

def probe_provider(cfg):
    name = cfg["name"]
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]
    model_filter = cfg.get("model_filter", {})
    suffix = model_filter.get("suffix")

    log(f"probing {name} models from {base_url}")
    detail(f"{name}: auth key {api_key[:6]}...{api_key[-4:]} ({len(api_key)} chars)")
    if suffix:
        detail(f"{name}: model_filter.suffix={suffix!r} (models not ending in this are dropped before probing)")

    headers = {"Authorization": f"Bearer {api_key}"}
    models = fetch_catalogue(name, base_url, headers)
    if models is None:
        log(f"{name}: 0 models found (catalogue fetch failed)")
        return []
    detail(f"{name}: {len(models)} models in catalogue")

    candidates, skipped_no_id, skipped_suffix = [], 0, 0
    for m in models:
        model = m.get("id") if isinstance(m, dict) else None
        if not model:
            skipped_no_id += 1
            debug(f"{name}: catalogue entry with no id, skipped: {m}")
            continue
        if suffix and not model.endswith(suffix):
            skipped_suffix += 1
            debug(f"{name}: skipped (suffix {suffix!r} mismatch): {model}")
            continue
        candidates.append(model)

    if skipped_suffix or skipped_no_id:
        detail(f"{name}: {len(candidates)} candidates after filtering "
               f"({skipped_suffix} skipped by suffix, {skipped_no_id} skipped for missing id)")

    chat_url = f"{base_url}/chat/completions"
    reasons = Counter()
    lock = Lock()

    def probe(model):
        ok, reason = probe_chat(chat_url, headers, model)
        with lock:
            reasons[reason] += 1
        return model if ok else None

    discovered = []
    with ThreadPoolExecutor(max_workers=int(os.getenv("DISCOVERY_THREADS", "10"))) as pool:
        for model in pool.map(probe, candidates):
            if model:
                discovered.append(model)
                debug(f"{name}: kept {model}")

    log(f"{name}: {len(discovered)} models found "
        f"({len(discovered)}/{len(candidates)} probes passed, {len(candidates) - len(discovered)} failed)")
    for reason, n in reasons.most_common():
        if reason != "ok":
            detail(f"{name}: {n} probe failure(s): {reason}")
    return [{"provider": name, "model": model} for model in discovered]

def discover_models():
    providers = load_providers()
    discovered = []
    for cfg in providers:
        discovered += probe_provider(cfg)

    by_provider = Counter(item["provider"] for item in discovered)
    log("total: " + str(len(discovered)) + " models discovered ("
        + ", ".join(f"{p}={n}" for p, n in by_provider.items()) + ")")
    CACHE.write_text(json.dumps({
        "models": discovered
    }, indent=2))
    log(f"cache written to {CACHE}")

if __name__ == "__main__":
    discover_models()
