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

On first start, the container automatically discovers models and generates the LiteLLM config, then starts the proxy on port 4000.

A daily cron job (`/app/refresh_cron.py`) checks whether the model cache is older than `MODEL_REFRESH_DAYS` (default 30). If so, it re-discovers models, regenerates the config, and signals the LiteLLM process to restart — no container restart needed.

## Manual refresh

To force an immediate refresh:

```bash
docker exec litellm python /app/refresh_cron.py
```
