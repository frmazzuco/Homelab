-- Personal Data Lake - Queries de exemplo
-- Execute com: duckdb datalake.duckdb < queries/examples.sql

-- ============================================
-- ORA 03 - Queries de análise
-- ============================================

-- 1. Status atual do veículo
SELECT 
    timestamp,
    battery_soc || '%' as bateria,
    battery_range_km || ' km' as autonomia,
    odometer_km || ' km' as odometro,
    CASE WHEN is_locked THEN '🔒 Trancado' ELSE '🔓 Aberto' END as status_trava,
    CASE WHEN is_charging THEN '⚡ Carregando' ELSE '🔋 Normal' END as status_carga
FROM ora03_snapshots
ORDER BY timestamp DESC
LIMIT 1;

-- 2. Histórico de bateria (últimos 30 dias)
SELECT 
    date,
    ROUND(AVG(battery_soc), 1) as soc_medio,
    ROUND(MIN(battery_soc), 1) as soc_minimo,
    ROUND(MAX(battery_soc), 1) as soc_maximo,
    ROUND(AVG(battery_range_km), 0) as autonomia_media
FROM ora03_snapshots
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;

-- 3. Quilometragem por dia (últimos 30 dias)
WITH daily_km AS (
    SELECT 
        date,
        MAX(odometer_km) as km_fim,
        LAG(MAX(odometer_km)) OVER (ORDER BY date) as km_inicio
    FROM ora03_snapshots
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date
)
SELECT 
    date,
    ROUND(km_fim - COALESCE(km_inicio, km_fim), 1) as km_rodados,
    km_fim as odometro_total
FROM daily_km
WHERE km_inicio IS NOT NULL
ORDER BY date DESC;

-- 4. Média de SOC por dia da semana
SELECT 
    CASE DAYOFWEEK(date)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terça'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sábado'
    END as dia_semana,
    ROUND(AVG(battery_soc), 1) as soc_medio,
    COUNT(*) as snapshots
FROM ora03_snapshots
WHERE date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DAYOFWEEK(date)
ORDER BY DAYOFWEEK(date);

-- 5. Eventos de carga (quando o carro foi carregado)
SELECT 
    date,
    COUNT(*) as vezes_carregando,
    ROUND(AVG(battery_soc), 1) as soc_medio_durante_carga
FROM ora03_snapshots
WHERE is_charging = true
GROUP BY date
ORDER BY date DESC
LIMIT 30;

-- 6. Consumo estimado (quando SOC diminui sem carregar)
WITH battery_changes AS (
    SELECT 
        timestamp,
        date,
        battery_soc,
        LAG(battery_soc) OVER (ORDER BY timestamp) as prev_soc,
        LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp,
        is_charging
    FROM ora03_snapshots
)
SELECT 
    date,
    ROUND(SUM(prev_soc - battery_soc), 1) as soc_consumido_total,
    ROUND(AVG(prev_soc - battery_soc), 2) as soc_consumido_medio_snapshot,
    COUNT(*) as snapshots_consumo
FROM battery_changes
WHERE 
    is_charging = false 
    AND prev_soc IS NOT NULL
    AND prev_soc > battery_soc
    AND date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;

-- 7. Localização mais frequente
SELECT 
    address,
    COUNT(*) as vezes,
    ROUND(AVG(battery_soc), 1) as soc_medio_neste_local
FROM ora03_snapshots
WHERE address IS NOT NULL
GROUP BY address
ORDER BY COUNT(*) DESC
LIMIT 10;

-- 8. Resumo geral (estatísticas gerais)
SELECT 
    COUNT(*) as total_snapshots,
    MIN(date) as primeira_coleta,
    MAX(date) as ultima_coleta,
    ROUND(AVG(battery_soc), 1) as soc_medio_geral,
    ROUND(MIN(battery_soc), 1) as soc_minimo_historico,
    ROUND(MAX(battery_soc), 1) as soc_maximo_historico,
    ROUND(MAX(odometer_km) - MIN(odometer_km), 1) as total_km_rodados
FROM ora03_snapshots;

-- ============================================
-- VIEWS ÚTEIS (criar uma vez)
-- ============================================

-- View: consumo diário estimado
CREATE OR REPLACE VIEW ora03_daily_consumption AS
WITH battery_changes AS (
    SELECT 
        timestamp,
        date,
        battery_soc,
        LAG(battery_soc) OVER (ORDER BY timestamp) as prev_soc,
        is_charging
    FROM ora03_snapshots
)
SELECT 
    date,
    ROUND(SUM(CASE WHEN prev_soc > battery_soc AND is_charging = false 
               THEN prev_soc - battery_soc ELSE 0 END), 1) as soc_consumido,
    COUNT(*) as snapshots
FROM battery_changes
WHERE prev_soc IS NOT NULL
GROUP BY date
ORDER BY date DESC;

-- View: status diário agregado
CREATE OR REPLACE VIEW ora03_daily_summary AS
SELECT 
    date,
    ROUND(AVG(battery_soc), 1) as soc_medio,
    ROUND(MIN(battery_soc), 1) as soc_minimo,
    ROUND(MAX(battery_soc), 1) as soc_maximo,
    MAX(odometer_km) - MIN(odometer_km) as km_rodados,
    SUM(CASE WHEN is_charging THEN 1 ELSE 0 END) as snapshots_carregando,
    COUNT(*) as total_snapshots
FROM ora03_snapshots
GROUP BY date
ORDER BY date DESC;

-- ============================================
-- Queries cross-source (futuro - quando tiver mais dados)
-- ============================================

-- Exemplo: gastos Nubank vs uso do carro (quando tiver ambos)
-- SELECT 
--     o.date,
--     o.km_rodados,
--     COALESCE(n.gasto_total, 0) as gasto_total,
--     ROUND(COALESCE(n.gasto_total, 0) / NULLIF(o.km_rodados, 0), 2) as custo_por_km
-- FROM ora03_daily_summary o
-- LEFT JOIN (
--     SELECT date, SUM(amount) as gasto_total 
--     FROM nubank_transactions 
--     GROUP BY date
-- ) n ON o.date = n.date
-- WHERE o.km_rodados > 0
-- ORDER BY o.date DESC;
