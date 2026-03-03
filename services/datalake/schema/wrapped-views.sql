-- Personal Wrapped views

-- Locais visitados (agrupa por coordenada aproximada ~100m)
CREATE OR REPLACE VIEW wrapped_locations AS
SELECT 
    ROUND(latitude, 3) as lat_group,
    ROUND(longitude, 3) as lon_group,
    MIN(address) as address,
    COUNT(*) as visits,
    MIN(timestamp) as first_visit,
    MAX(timestamp) as last_visit,
    MIN(latitude) as latitude,
    MIN(longitude) as longitude
FROM ora03_snapshots
WHERE latitude IS NOT NULL
GROUP BY ROUND(latitude, 3), ROUND(longitude, 3)
ORDER BY visits DESC;

-- KM rodados por mês
CREATE OR REPLACE VIEW wrapped_monthly_km AS
SELECT 
    strftime(date, '%Y-%m') as month,
    MAX(odometer_km) - MIN(odometer_km) as km_rodados,
    COUNT(*) as snapshots
FROM ora03_snapshots
WHERE odometer_km IS NOT NULL AND odometer_km > 0
GROUP BY strftime(date, '%Y-%m')
ORDER BY month;

-- Resumo mensal combinado
CREATE OR REPLACE VIEW wrapped_monthly_summary AS
SELECT
    strftime(date, '%Y-%m') as month,
    -- ORA 03
    (SELECT MAX(o2.odometer_km) - MIN(o2.odometer_km) 
     FROM ora03_snapshots o2 
     WHERE strftime(o2.date, '%Y-%m') = strftime(o.date, '%Y-%m') 
       AND o2.odometer_km > 0) as km_rodados,
    (SELECT COUNT(DISTINCT ROUND(o2.latitude, 3) || ',' || ROUND(o2.longitude, 3))
     FROM ora03_snapshots o2
     WHERE strftime(o2.date, '%Y-%m') = strftime(o.date, '%Y-%m')
       AND o2.latitude IS NOT NULL) as locais_visitados,
    -- Nubank
    (SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)
     FROM nubank_transactions t
     WHERE strftime(t.date, '%Y-%m') = strftime(o.date, '%Y-%m')) as total_gastos,
    -- Jellyfin
    (SELECT COUNT(DISTINCT item_name) 
     FROM jellyfin_activity a
     WHERE a.event_type = 'VideoPlaybackStopped'
       AND strftime(a.timestamp, '%Y-%m') = strftime(o.date, '%Y-%m')) as itens_assistidos
FROM ora03_snapshots o
GROUP BY strftime(date, '%Y-%m')
ORDER BY month;

-- Mapa de pontos (para Grafana Geomap)
CREATE OR REPLACE VIEW wrapped_location_map AS
SELECT
    latitude,
    longitude,
    address,
    timestamp,
    battery_soc as battery,
    battery_range_km as range_km
FROM ora03_snapshots
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY timestamp DESC;
