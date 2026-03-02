# Data Lake

Personal data lake: DuckDB + Grafana + automated ingests, running containerized on Mac mini (Colima).

## Architecture

```
GWM API / Pluggy / Jellyfin
        │
        ▼
  Supercronic Scheduler (container)
   ├── 06:00 BRT  Nubank (Pluggy API)
   ├── 06:05 BRT  ORA 03 (GWM Brasil API)
   └── 09:00 BRT  Jellyfin (local API)
        │
        ▼
    DuckDB (host: ~/datalake/datalake.duckdb)
        │
        ▼
  DuckDB HTTP API (container, :8089)
        │
        ▼
  Grafana (container, :3000) + Infinity Plugin
        │
        ▼
  Apprise API → Telegram alerts (on success/failure)
```

## Containers

| Container | Image | Port | Network |
|-----------|-------|------|---------|
| `grafana` | grafana/grafana:12.4.0 | 3000 | datalake |
| `duckdb-api` | datalake-duckdb-api (local) | 8089 | datalake |
| `datalake-scheduler` | datalake-scheduler (local) | — | datalake + bridge |

Notifications go through the existing `apprise-api` container on the bridge network.

## Data Sources

| Source | Script | Schedule | Data |
|--------|--------|----------|------|
| **Nubank** | `pluggy-ingest.py` | 06:00 BRT | Transactions, balances (via Pluggy API) |
| **ORA 03** | `ora03-ingest.py` | 06:05 BRT | Battery, tires, location, odometer (via GWM Brasil API) |
| **Jellyfin** | `jellyfin-ingest.py` | 09:00 BRT | Library metadata, playback activity, user stats |

## Structure

```
compose.yml               # Docker Compose (Grafana + DuckDB API + Scheduler)
Dockerfile.duckdb-api     # DuckDB HTTP API image
Dockerfile.scheduler      # Supercronic + Python + DuckDB CLI image
entrypoint.sh             # Scheduler entrypoint (symlinks + exec)
crontab                   # Supercronic schedule
run-job.sh                # Job wrapper (runs script + Apprise notification)
.env.example              # Environment variables template
provisioning/
  datasources/
    datalake.yml          # Grafana auto-provisioned Infinity datasource
scripts/
  duckdb-api.py           # HTTP API server for DuckDB queries
  pluggy-ingest.py        # Nubank ingest via Pluggy
  ora03-ingest.py         # ORA 03 ingest via GWM Brasil API
  jellyfin-ingest.py      # Jellyfin library + activity ingest
dashboards/
  nubank-financeiro.json  # 💰 Gastos, receitas, categorias, assinaturas
  jellyfin-biblioteca.json # 🎬 Catálogo, reprodução, gêneros por usuário
  ora03-veiculo.json      # 🚗 Bateria, autonomia, pneus, odômetro
schema/
  init.sql                # DuckDB table/view definitions
queries/
  examples.sql            # Example analytical queries
  nubank-analytics.sql    # Nubank-specific queries
```

## Setup

### 1. Configure environment

```bash
cp .env.example .env
# Fill in: Pluggy, Jellyfin, GWM credentials + Apprise notification URL
```

### 2. Initialize DuckDB

```bash
mkdir -p ~/datalake
duckdb ~/datalake/datalake.duckdb < schema/init.sql
```

### 3. Start containers

```bash
# With Docker Compose:
docker compose up -d

# With Colima (containerd):
colima nerdctl -- compose up -d
```

### 4. Import dashboards

Import `dashboards/*.json` via Grafana UI (http://localhost:3000) or API.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DUCKDB_PATH` | Path to DuckDB file inside container (default: `/data/datalake.duckdb`) |
| `CERTS_DIR` | GWM client certificates directory (mounted at `/app/certs`) |
| `PLUGGY_CONFIG_PATH` | Nubank config JSON path (default: `/data/nubank-config.json`) |
| `PLUGGY_CLIENT_ID` | Pluggy API client ID |
| `PLUGGY_CLIENT_SECRET` | Pluggy API client secret |
| `JELLYFIN_API_KEY` | Jellyfin API key |
| `JELLYFIN_URL` | Jellyfin server URL |
| `GWM_EMAIL` | GWM Brasil account email |
| `GWM_PASSWORD` | GWM Brasil account password |
| `APPRISE_URL` | Apprise API endpoint (default: `http://apprise-api:8000`) |
| `NOTIFY_ON_SUCCESS` | Send notification on success too (default: `true`) |

## Notes

- Secrets (API keys, tokens) stored in `.env` (gitignored)
- DuckDB `.duckdb` files are gitignored
- Grafana datasource auto-provisioned via `provisioning/datasources/datalake.yml`
- Scheduler uses Supercronic (not Ofelia — incompatible with containerd runtime)
- DuckDB CLI baked into scheduler image for scripts that use subprocess
