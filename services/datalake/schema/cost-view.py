#!/usr/bin/env python3
import duckdb, os

conn = duckdb.connect(os.environ.get("DUCKDB_PATH", "/data/datalake.duckdb"))

conn.execute("""
CREATE OR REPLACE VIEW ora03_cost_estimate AS
SELECT
    strftime(date, '%Y-%m') as month,
    MAX(odometer_km) - MIN(odometer_km) as km_rodados,
    ROUND((MAX(odometer_km) - MIN(odometer_km)) / 6.3, 2) as kwh_consumidos,
    ROUND((MAX(odometer_km) - MIN(odometer_km)) / 6.3 * 0.80, 2) as custo_energia_rs,
    ROUND(0.80 / 6.3, 4) as custo_por_km_ev,
    ROUND((MAX(odometer_km) - MIN(odometer_km)) / 12.0 * 6.20, 2) as custo_gasolina_equiv,
    ROUND((MAX(odometer_km) - MIN(odometer_km)) / 12.0 * 6.20 - (MAX(odometer_km) - MIN(odometer_km)) / 6.3 * 0.80, 2) as economia_vs_gasolina
FROM ora03_snapshots
WHERE odometer_km IS NOT NULL AND odometer_km > 0
GROUP BY strftime(date, '%Y-%m')
HAVING MAX(odometer_km) - MIN(odometer_km) > 0
ORDER BY month
""")

rows = conn.execute("SELECT * FROM ora03_cost_estimate").fetchall()
cols = [d[0] for d in conn.description]
for r in rows:
    print(dict(zip(cols, r)))
conn.close()
print("View created!")
