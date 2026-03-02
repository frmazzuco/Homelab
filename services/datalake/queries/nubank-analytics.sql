-- Nubank Analytics Queries

-- 1. Resumo Mensal (gastos x receitas)
CREATE OR REPLACE VIEW nubank_monthly_summary AS
SELECT 
    STRFTIME(date, '%Y-%m') as mes,
    account_type,
    COUNT(*) as total_transacoes,
    ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as gastos,
    ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as receitas,
    ROUND(SUM(amount), 2) as saldo
FROM nubank_transactions
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- 2. Top 10 Categorias de Gasto (último mês)
CREATE OR REPLACE VIEW nubank_top_categories_month AS
SELECT 
    category,
    COUNT(*) as transacoes,
    ROUND(SUM(ABS(amount)), 2) as total_gasto,
    ROUND(AVG(ABS(amount)), 2) as ticket_medio
FROM nubank_transactions
WHERE 
    amount < 0 
    AND date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY category
ORDER BY total_gasto DESC
LIMIT 10;

-- 3. Maiores Gastos do Mês
CREATE OR REPLACE VIEW nubank_top_expenses_month AS
SELECT 
    date,
    merchant,
    category,
    ROUND(ABS(amount), 2) as valor,
    account_type
FROM nubank_transactions
WHERE 
    amount < 0
    AND date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ABS(amount) DESC
LIMIT 20;

-- 4. Evolução de Gastos por Categoria (últimos 6 meses)
CREATE OR REPLACE VIEW nubank_category_trend_6m AS
SELECT 
    STRFTIME(date, '%Y-%m') as mes,
    category,
    ROUND(SUM(ABS(amount)), 2) as total
FROM nubank_transactions
WHERE 
    amount < 0
    AND date >= CURRENT_DATE - INTERVAL '180 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;

-- 5. Gastos Diários (últimos 30 dias)
CREATE OR REPLACE VIEW nubank_daily_expenses AS
SELECT 
    date,
    COUNT(*) as num_transacoes,
    ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as gastos,
    ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as receitas
FROM nubank_transactions
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;

-- 6. Comparação Mês a Mês
CREATE OR REPLACE VIEW nubank_month_comparison AS
WITH monthly AS (
    SELECT 
        STRFTIME(date, '%Y-%m') as mes,
        ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as gastos,
        ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as receitas
    FROM nubank_transactions
    GROUP BY 1
)
SELECT 
    mes,
    gastos,
    receitas,
    gastos - receitas as deficit,
    LAG(gastos) OVER (ORDER BY mes) as gastos_mes_anterior,
    ROUND(((gastos - LAG(gastos) OVER (ORDER BY mes)) / NULLIF(LAG(gastos) OVER (ORDER BY mes), 0)) * 100, 1) as variacao_percent
FROM monthly
ORDER BY mes DESC;

-- 7. Análise por Estabelecimento
CREATE OR REPLACE VIEW nubank_top_merchants AS
SELECT 
    merchant,
    category,
    COUNT(*) as num_compras,
    ROUND(SUM(ABS(amount)), 2) as total_gasto,
    ROUND(AVG(ABS(amount)), 2) as ticket_medio,
    MIN(date) as primeira_compra,
    MAX(date) as ultima_compra
FROM nubank_transactions
WHERE 
    amount < 0
    AND merchant IS NOT NULL
    AND merchant != ''
GROUP BY merchant, category
HAVING COUNT(*) >= 2
ORDER BY total_gasto DESC
LIMIT 30;

-- 8. Resumo Semanal (últimas 4 semanas)
CREATE OR REPLACE VIEW nubank_weekly_summary AS
SELECT 
    STRFTIME(date, '%Y-W%W') as semana,
    ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as gastos,
    ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as receitas,
    COUNT(CASE WHEN amount < 0 THEN 1 END) as num_gastos,
    COUNT(CASE WHEN amount > 0 THEN 1 END) as num_receitas
FROM nubank_transactions
WHERE date >= CURRENT_DATE - INTERVAL '28 days'
GROUP BY 1
ORDER BY 1 DESC;

-- 9. Estatísticas Gerais
CREATE OR REPLACE VIEW nubank_stats_overview AS
SELECT 
    'Total de transações' as metrica,
    CAST(COUNT(*) AS VARCHAR) as valor
FROM nubank_transactions
UNION ALL
SELECT 
    'Período de dados',
    MIN(date) || ' até ' || MAX(date)
FROM nubank_transactions
UNION ALL
SELECT 
    'Total gasto (histórico)',
    'R$ ' || CAST(ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) AS VARCHAR)
FROM nubank_transactions
UNION ALL
SELECT 
    'Total recebido (histórico)',
    'R$ ' || CAST(ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) AS VARCHAR)
FROM nubank_transactions
UNION ALL
SELECT 
    'Gasto médio mensal',
    'R$ ' || CAST(ROUND(AVG(monthly_expense), 2) AS VARCHAR)
FROM (
    SELECT SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as monthly_expense
    FROM nubank_transactions
    GROUP BY STRFTIME(date, '%Y-%m')
) m
UNION ALL
SELECT 
    'Transação média',
    'R$ ' || CAST(ROUND(AVG(CASE WHEN amount < 0 THEN ABS(amount) END), 2) AS VARCHAR)
FROM nubank_transactions;

-- 10. Heatmap de gastos (dia da semana x hora - precisa timestamp)
-- Nota: Pluggy pode não fornecer hora exata em todas transações
CREATE OR REPLACE VIEW nubank_spending_heatmap AS
SELECT 
    DAYNAME(date) as dia_semana,
    COUNT(*) as num_transacoes,
    ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as total_gasto
FROM nubank_transactions
WHERE amount < 0
GROUP BY dia_semana
ORDER BY 
    CASE DAYNAME(date)
        WHEN 'Monday' THEN 1
        WHEN 'Tuesday' THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday' THEN 4
        WHEN 'Friday' THEN 5
        WHEN 'Saturday' THEN 6
        WHEN 'Sunday' THEN 7
    END;
