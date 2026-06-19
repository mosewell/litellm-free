import os, json, requests, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE = Path("/data/models_cache.json")
PROVIDERS_CONFIG_PATH = os.getenv("PROVIDERS_CONFIG_PATH", "/data/providers.json")

def load_providers():
    path = Path(PROVIDERS_CONFIG_PATH)
    if path.exists():
        data = json.loads(path.read_text())
    elif os.getenv("PROVIDERS_JSON"):
        data = json.loads(os.getenv("PROVIDERS_JSON"))
    else:
        print("[discover] no provider config found; set PROVIDERS_CONFIG_PATH or PROVIDERS_JSON", file=sys.stderr)
        sys.exit(1)
    return data["providers"]

def probe_chat(url, headers, model):
    try:
        r = requests.post(
            url,
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1
            },
            timeout=int(os.getenv("PROBE_TIMEOUT", "20"))
        )
        ok = r.status_code == 200
        print(f"  [discover] probe {model}: {'OK' if ok else 'FAIL'} ({r.status_code})", file=sys.stderr)
        return ok
    except Exception as e:
        print(f"  [discover] probe {model}: ERROR {e}", file=sys.stderr)
        return False

def probe_provider(cfg):
    name = cfg["name"]
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]
    model_filter = cfg.get("model_filter", {})
    suffix = model_filter.get("suffix")

    print(f"[discover] probing {name} models", file=sys.stderr)
    r = requests.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    models = r.json().get("data", [])

    chat_url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}

    def probe(m):
        model = m["id"]
        if suffix and not model.endswith(suffix):
            return None
        if probe_chat(chat_url, headers, model):
            return {"provider": name, "model": model}
        return None

    discovered = []
    with ThreadPoolExecutor(max_workers=int(os.getenv("DISCOVERY_THREADS", "10"))) as pool:
        futures = {pool.submit(probe, m): m for m in models}
        for future in as_completed(futures):
            result = future.result()
            if result:
                discovered.append(result)

    count = len(discovered)
    print(f"[discover] {name}: {count} models found", file=sys.stderr)
    return discovered

def discover_models():
    providers = load_providers()
    discovered = []
    for cfg in providers:
        discovered += probe_provider(cfg)

    print(f"[discover] total: {len(discovered)} models discovered", file=sys.stderr)
    CACHE.write_text(json.dumps({
        "models": discovered
    }, indent=2))
    print(f"[discover] cache written to {CACHE}", file=sys.stderr)

if __name__ == "__main__":
    discover_models()
