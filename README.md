# LiteLLM Free Discovery Router

Creates a LiteLLM proxy that auto-discovers free models from configured providers.

## Setup

1. Copy the environment file and adjust if needed:

   ```bash
   cp .env.example .env
   ```

2. Copy the example provider config and add your API keys:

   ```bash
   cp data/providers.example.json data/providers.json
   # then edit data/providers.json with your real keys
   ```

   Provider credentials live in a single JSON file instead of individual env vars.
   The JSON is loaded from `PROVIDERS_CONFIG_PATH` (default `/data/providers.json`) or from the `PROVIDERS_JSON` env var.

## Running

```bash
docker compose up -d
```

On every start, the container re-discovers models and regenerates the LiteLLM config, then starts the proxy on port 4000. If discovery fails (e.g. a provider is briefly unreachable), startup falls back to the existing `models_cache.json`; it only aborts if there is no cache to fall back on.

A daily cron job (`/app/refresh_cron.py`) covers containers that stay up without restarting: it checks whether the model cache is older than `MODEL_REFRESH_DAYS` (default 30). If so, it re-discovers models, regenerates the config, and signals the LiteLLM process to restart — no container restart needed.

## Manual refresh

To force an immediate refresh:

```bash
docker exec litellm python /app/refresh_cron.py
```

## Discovery logging

`discover_models.py` logs to stderr, so it appears in `docker logs litellm`. Each run reports, per provider, the `/models` HTTP status, how many models were in the catalogue, how many were dropped by `model_filter.suffix` before any probe, and a tally of probe failures grouped by reason (e.g. `4 probe failure(s): http_429`).

Set `DISCOVERY_VERBOSE=true` for a per-model line each: the reason a catalogue entry was skipped, the status code and response body of each failed probe, and every model that was kept.
