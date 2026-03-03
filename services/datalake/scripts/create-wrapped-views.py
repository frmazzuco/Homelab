#!/usr/bin/env python3
import duckdb, os

DB = os.environ.get("DUCKDB_PATH", "/data/datalake.duckdb")
conn = duckdb.connect(DB)

conn.execute("""
CREATE OR REPLACE VIEW wrapped_monthly_summary AS
SELECT
    month,
    km_rodados,
    locais_visitados,
    total_gastos,
    itens_assistidos
FROM (
    SELECT DISTINCT strftime(date, '%Y-%m') as month FROM ora03_snapshots
) months
LEFT JOIN (
    SELECT strftime(date, '%Y-%m') as m, MAX(odometer_km) - MIN(odometer_km) as km_rodados
    FROM ora03_snapshots WHERE odometer_km > 0
    GROUP BY strftime(date, '%Y-%m')
) km ON km.m = months.month
LEFT JOIN (
    SELECT strftime(date, '%Y-%m') as m,
           COUNT(DISTINCT CAST(ROUND(latitude, 3) AS VARCHAR) || ',' || CAST(ROUND(longitude, 3) AS VARCHAR)) as locais_visitados
    FROM ora03_snapshots WHERE latitude IS NOT NULL
    GROUP BY strftime(date, '%Y-%m')
) loc ON loc.m = months.month
LEFT JOIN (
    SELECT strftime(date, '%Y-%m') as m,
           COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as total_gastos
    FROM nubank_transactions
    GROUP BY strftime(date, '%Y-%m')
) fin ON fin.m = months.month
LEFT JOIN (
    SELECT strftime(timestamp, '%Y-%m') as m,
           COUNT(DISTINCT item_name) as itens_assistidos
    FROM jellyfin_activity WHERE event_type = 'VideoPlaybackStopped'
    GROUP BY strftime(timestamp, '%Y-%m')
) media ON media.m = months.month
ORDER BY month
""")

conn.execute("""
CREATE OR REPLACE VIEW wrapped_daily_activity AS
SELECT
    date,
    MAX(battery_soc) as max_battery,
    MIN(battery_soc) as min_battery,
    COUNT(DISTINCT CAST(ROUND(latitude, 3) AS VARCHAR) || ',' || CAST(ROUND(longitude, 3) AS VARCHAR)) as locations
FROM ora03_snapshots
GROUP BY date
ORDER BY date
""")

# Test
rows = conn.execute("SELECT * FROM wrapped_monthly_summary").fetchall()
for r in rows:
    print(r)

print("\nViews created!")
conn.close()
