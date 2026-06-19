import json, yaml, os, sys
from pathlib import Path

PROVIDERS_CONFIG_PATH = os.getenv("PROVIDERS_CONFIG_PATH", "/data/providers.json")

def load_providers():
    path = Path(PROVIDERS_CONFIG_PATH)
    if path.exists():
        data = json.loads(path.read_text())
    elif os.getenv("PROVIDERS_JSON"):
        data = json.loads(os.getenv("PROVIDERS_JSON"))
    else:
        print("[config] no provider config found; set PROVIDERS_CONFIG_PATH or PROVIDERS_JSON", file=sys.stderr)
        sys.exit(1)
    return data["providers"]

def generate_config():
    providers = load_providers()
    cache = json.loads(Path("/data/models_cache.json").read_text())
    total = len(cache.get("models", []))
    print(f"[config] loaded {total} models from cache", file=sys.stderr)

    provider_map = {p["name"]: p for p in providers}

    cfg = {
        "model_list": [],
        "general_settings": {
            "master_key": os.getenv("LITELLM_MASTER_KEY", "sk-admin-key")
        }
    }

    for item in cache["models"]:
        provider_name = item["provider"]
        model = item["model"]
        p = provider_map.get(provider_name)
        if not p:
            print(f"[config] unknown provider '{provider_name}', skipping", file=sys.stderr)
            continue

        entry = {
            "model_name": f"{p['model_name_prefix']}{model}",
            "litellm_params": {
                "model": f"{p['model_path_prefix']}{model}",
                "api_key": p["api_key"]
            }
        }
        if "api_base" in p:
            entry["litellm_params"]["api_base"] = p["api_base"]

        cfg["model_list"].append(entry)

    out = Path("/data/config.yaml")
    out.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print(f"[config] wrote {len(cfg['model_list'])} model entries to {out}", file=sys.stderr)

if __name__ == "__main__":
    generate_config()
