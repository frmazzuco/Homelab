# Data Lake

Personal data lake: DuckDB + Grafana + Python ingest, running on Mac mini.

## Architecture

```
GWM API / Pluggy / Jellyfin
        │
        ▼
  Python Ingest Scripts (cron daily 6h BRT)
        │
        ▼
    DuckDB (~/datalake/datalake.duckdb)
        │
        ▼
  DuckDB HTTP API (:8089)
        │
        ▼
  Grafana (:3000) + Infinity Plugin
```

## Data Sources

| Source | Script | Data |
|--------|--------|------|
| **Nubank** | `pluggy-ingest.py` | Transactions, balances (via Pluggy API) |
| **ORA 03** | `ora03-ingest.py` | Battery, tires, location, odometer (via GWM Brasil API) |
| **Jellyfin** | `jellyfin-ingest.py` | Library metadata, playback activity, user stats |

## Structure

```
scripts/          # Ingest scripts + DuckDB HTTP API server
dashboards/       # Grafana dashboard JSON (importable)
schema/           # DuckDB init schema
queries/          # Example analytical queries
```

## Dashboards

- **💰 nubank-financeiro** — Gastos/receitas, categorias, assinaturas, transações
- **🎬 jellyfin-biblioteca** — Catálogo, atividade de reprodução, gêneros por usuário
- **🚗 ora03-veiculo** — Bateria, autonomia, pneus, odômetro, localização

## Setup

```bash
pip3 install duckdb
duckdb ~/datalake/datalake.duckdb < schema/init.sql
python3 scripts/duckdb-api.py &    # HTTP API on :8089
# Import dashboards via Grafana API or UI
```

## Notes

- Secrets (API keys, tokens) are **not** stored here
- DuckDB `.duckdb` files are gitignored
- Dashboards use Grafana Infinity plugin pointing to `localhost:8089`
