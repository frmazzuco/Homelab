-- Personal Data Lake - Schema inicial
-- DuckDB DDL

-- Tabela ORA 03 - snapshots diários do veículo
CREATE TABLE IF NOT EXISTS ora03_snapshots (
    timestamp TIMESTAMP NOT NULL,
    date DATE NOT NULL,
    
    -- Bateria
    battery_soc DECIMAL(5,2),           -- State of charge (%)
    battery_range_km DECIMAL(6,2),      -- Range estimado (km)
    battery_voltage DECIMAL(6,2),       -- Voltagem (V)
    battery_current DECIMAL(6,2),       -- Corrente (A)
    battery_temperature DECIMAL(5,2),   -- Temperatura (°C)
    
    -- Localização
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    address VARCHAR,
    
    -- Veículo
    odometer_km DECIMAL(10,2),          -- Odômetro total (km)
    is_locked BOOLEAN,
    is_charging BOOLEAN,
    is_ac_on BOOLEAN,
    
    -- Metadata
    raw_json JSON,                       -- Resposta completa da API
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (timestamp)
);

-- Índices para queries comuns
CREATE INDEX IF NOT EXISTS idx_ora03_date ON ora03_snapshots(date DESC);
CREATE INDEX IF NOT EXISTS idx_ora03_battery ON ora03_snapshots(battery_soc, date);

-- View para últimos 30 dias
CREATE OR REPLACE VIEW ora03_last_30d AS
SELECT 
    date,
    AVG(battery_soc) as avg_soc,
    MIN(battery_soc) as min_soc,
    MAX(battery_soc) as max_soc,
    MAX(odometer_km) - MIN(odometer_km) as km_driven,
    COUNT(*) as snapshots
FROM ora03_snapshots
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;

-- Tabela Nubank (preparada para futuro)
CREATE TABLE IF NOT EXISTS nubank_transactions (
    id VARCHAR PRIMARY KEY,
    date DATE NOT NULL,
    timestamp TIMESTAMP,
    amount DECIMAL(12,2),
    category VARCHAR,
    merchant VARCHAR,
    description VARCHAR,
    account_type VARCHAR,  -- credit_card | checking_account
    raw_json JSON,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nubank_date ON nubank_transactions(date DESC);
CREATE INDEX IF NOT EXISTS idx_nubank_category ON nubank_transactions(category, date);

-- Tabela Jellyfin (preparada para futuro)
CREATE TABLE IF NOT EXISTS jellyfin_views (
    id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_name VARCHAR,
    item_name VARCHAR,
    item_type VARCHAR,  -- Movie | Series | Episode
    duration_seconds INTEGER,
    play_percentage DECIMAL(5,2),
    raw_json JSON,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jellyfin_timestamp ON jellyfin_views(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_jellyfin_item ON jellyfin_views(item_name, timestamp);

-- View sumário geral
CREATE OR REPLACE VIEW data_summary AS
SELECT 
    'ORA 03' as source,
    COUNT(*) as records,
    MIN(date) as first_record,
    MAX(date) as last_record
FROM ora03_snapshots
UNION ALL
SELECT 
    'Nubank' as source,
    COUNT(*) as records,
    MIN(date) as first_record,
    MAX(date) as last_record
FROM nubank_transactions
UNION ALL
SELECT 
    'Jellyfin' as source,
    COUNT(*) as records,
    CAST(MIN(timestamp) AS DATE) as first_record,
    CAST(MAX(timestamp) AS DATE) as last_record
FROM jellyfin_views;
