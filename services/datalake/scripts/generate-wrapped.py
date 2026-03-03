#!/usr/bin/env python3
"""
Personal Wrapped — Monthly PDF report generator.
Queries DuckDB, renders HTML template, converts to PDF via weasyprint.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

DUCKDB_API = os.environ.get("DUCKDB_API_URL", "http://duckdb-api:8089")
TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", "/app/scripts/wrapped-template.html")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data")

def query_duckdb(sql):
    try:
        data = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            f"{DUCKDB_API}/query", data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  Query error: {e}", file=sys.stderr)
        return None

def fmt_number(n):
    """Format number with thousands separator."""
    if n is None:
        return "0"
    try:
        n = float(n)
        if n == int(n):
            return f"{int(n):,}".replace(",", ".")
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(n)

def shorten_address(addr):
    """Shorten Nominatim address to something readable."""
    if not addr:
        return "Local desconhecido"
    parts = [p.strip() for p in addr.split(",")]
    # Keep street + neighborhood/city
    if len(parts) >= 3:
        return f"{parts[0]}, {parts[2]}"
    return parts[0]

def get_month_range(month_str=None):
    """Get start/end dates for a month. Default: last month."""
    if month_str:
        year, month = map(int, month_str.split("-"))
    else:
        today = datetime.now()
        first_of_this = today.replace(day=1)
        last_month = first_of_this - timedelta(days=1)
        year, month = last_month.year, last_month.month
    
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{month+1:02d}-01"
    
    months_pt = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    period = f"{months_pt[month]} {year}"
    
    return start, end, period

def generate():
    # Parse args
    month_str = sys.argv[1] if len(sys.argv) > 1 else None
    start, end, period = get_month_range(month_str)
    
    print(f"📊 Personal Wrapped — {period}")
    print(f"   Período: {start} → {end}")
    
    # === Fetch data ===
    
    # Stats
    print("   Buscando stats...")
    stats = query_duckdb(f"""
        SELECT 
            COALESCE(MAX(odometer_km) - MIN(odometer_km), 0) as km,
            ROUND(AVG(battery_soc), 0) as avg_bat,
            ROUND(AVG(battery_range_km), 0) as avg_range,
            COUNT(*) as snapshots
        FROM ora03_snapshots
        WHERE date >= '{start}' AND date < '{end}' AND battery_soc IS NOT NULL
    """)
    
    km = 0; avg_bat = 0; avg_range = 0
    if stats and isinstance(stats, list) and stats:
        km = stats[0].get("km", 0) or 0
        avg_bat = stats[0].get("avg_bat", 0) or 0
        avg_range = stats[0].get("avg_range", 0) or 0
    
    # Locations
    print("   Buscando locais...")
    locations = query_duckdb(f"""
        SELECT 
            MIN(address) as address,
            COUNT(*) as visits
        FROM ora03_snapshots
        WHERE latitude IS NOT NULL AND date >= '{start}' AND date < '{end}'
        GROUP BY ROUND(latitude, 3), ROUND(longitude, 3)
        ORDER BY visits DESC
        LIMIT 5
    """)
    
    loc_count_result = query_duckdb(f"""
        SELECT COUNT(DISTINCT CAST(ROUND(latitude, 3) AS VARCHAR) || ',' || CAST(ROUND(longitude, 3) AS VARCHAR)) as n
        FROM ora03_snapshots
        WHERE latitude IS NOT NULL AND date >= '{start}' AND date < '{end}'
    """)
    loc_count = 0
    if loc_count_result and isinstance(loc_count_result, list) and loc_count_result:
        loc_count = loc_count_result[0].get("n", 0) or 0
    
    # Finances
    print("   Buscando finanças...")
    fin = query_duckdb(f"""
        SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as gastos
        FROM nubank_transactions
        WHERE date >= '{start}' AND date < '{end}'
    """)
    total_gastos = 0
    if fin and isinstance(fin, list) and fin:
        total_gastos = fin[0].get("gastos", 0) or 0
    
    categories = query_duckdb(f"""
        SELECT category as name, ROUND(SUM(amount), 2) as amount
        FROM nubank_transactions
        WHERE amount > 0 AND date >= '{start}' AND date < '{end}'
        GROUP BY category ORDER BY amount DESC LIMIT 8
    """) or []
    
    top_expenses = query_duckdb(f"""
        SELECT description as desc, ROUND(amount, 2) as amount, category
        FROM nubank_transactions
        WHERE amount > 0 AND date >= '{start}' AND date < '{end}'
        ORDER BY amount DESC LIMIT 5
    """) or []
    
    # Entertainment
    print("   Buscando entretenimento...")
    ent = query_duckdb(f"""
        SELECT DISTINCT item_name as title, user_name as user, device
        FROM jellyfin_activity
        WHERE event_type = 'VideoPlaybackStopped'
          AND timestamp >= '{start}' AND timestamp < '{end}'
        ORDER BY timestamp DESC
    """) or []
    
    ent_count = len(ent) if isinstance(ent, list) else 0
    
    # Extra finance stats
    print("   Buscando extras...")
    avg_day_result = query_duckdb(f"""
        SELECT ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) / 
               COUNT(DISTINCT date), 2) as avg_day
        FROM nubank_transactions
        WHERE date >= '{start}' AND date < '{end}'
    """)
    monthly_avg_day = None
    if avg_day_result and isinstance(avg_day_result, list) and avg_day_result:
        v = avg_day_result[0].get("avg_day")
        if v and float(v) > 0:
            monthly_avg_day = fmt_number(v)
    
    top_day_result = query_duckdb(f"""
        SELECT date, ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as total
        FROM nubank_transactions
        WHERE date >= '{start}' AND date < '{end}'
        GROUP BY date ORDER BY total DESC LIMIT 1
    """)
    top_day_spending = None
    if top_day_result and isinstance(top_day_result, list) and top_day_result:
        d = top_day_result[0]
        if d.get("total") and float(d["total"]) > 0:
            raw_date = str(d.get("date", ""))[:10]
            try:
                dt = datetime.strptime(raw_date, "%Y-%m-%d")
                formatted_date = dt.strftime("%d/%m")
            except:
                formatted_date = raw_date
            top_day_spending = {"amount": fmt_number(d["total"]), "date": formatted_date}
    
    tx_count_result = query_duckdb(f"""
        SELECT COUNT(*) as n FROM nubank_transactions
        WHERE amount > 0 AND date >= '{start}' AND date < '{end}'
    """)
    total_transactions = None
    if tx_count_result and isinstance(tx_count_result, list) and tx_count_result:
        n = tx_count_result[0].get("n", 0)
        if n and int(n) > 0:
            total_transactions = int(n)

    snapshots_count = 0
    if stats and isinstance(stats, list) and stats:
        snapshots_count = stats[0].get("snapshots", 0) or 0

    # === Generate fun fact ===
    fun_facts = []
    if float(total_gastos) > 0 and categories and isinstance(categories, list):
        top_cat = categories[0]
        pct = round(float(top_cat["amount"]) / float(total_gastos) * 100)
        fun_facts.append(f"<strong>{pct}%</strong> dos seus gastos foram em <strong>{top_cat['name']}</strong>.")
    if float(km) > 0:
        fun_facts.append(f"Você rodou <strong>{fmt_number(km)} km</strong> — equivalente a {fmt_number(float(km)/12500*100)}% da circunferência da Terra!")
    if ent_count > 0:
        fun_facts.append(f"Você assistiu <strong>{ent_count} títulos</strong> diferentes. Cinéfilo de carteirinha! 🎬")
    
    fun_fact = fun_facts[0] if fun_facts else ""
    
    # === Render template ===
    print("   Renderizando...")
    
    with open(TEMPLATE_PATH) as f:
        template = f.read()
    
    # Simple Jinja-like replacement (avoid dependency)
    from jinja2 import Template
    tmpl = Template(template)
    
    top_locations_data = []
    if locations and isinstance(locations, list):
        for loc in locations:
            top_locations_data.append({
                "name": shorten_address(loc.get("address")),
                "visits": loc.get("visits", 0)
            })
    
    categories_data = []
    if isinstance(categories, list) and categories:
        max_cat = max(float(c.get("amount", 0) or 0) for c in categories) or 1
        for cat in categories:
            amt = float(cat.get("amount", 0) or 0)
            categories_data.append({
                "name": cat.get("name", "?"),
                "amount": fmt_number(amt),
                "pct": round(amt / max_cat * 100)
            })
    
    expenses_data = []
    if isinstance(top_expenses, list):
        for exp in top_expenses:
            expenses_data.append({
                "desc": (exp.get("desc", "?") or "?")[:40],
                "amount": fmt_number(exp.get("amount", 0)),
                "category": exp.get("category", "")
            })
    
    ent_data = []
    if isinstance(ent, list):
        for item in ent[:8]:
            ent_data.append({
                "title": (item.get("title", "?") or "?")[:35],
                "user": item.get("user", ""),
                "device": (item.get("device", "") or "")[:20]
            })
    
    html = tmpl.render(
        user_name="Francisco Mazzuco",
        period=period,
        km_rodados=fmt_number(km),
        locais_visitados=loc_count,
        total_gastos=fmt_number(total_gastos),
        itens_assistidos=ent_count,
        bateria_media=int(float(avg_bat)),
        autonomia_media=int(float(avg_range)),
        snapshots=int(snapshots_count),
        top_locations=top_locations_data,
        top_categories=categories_data,
        top_expenses=expenses_data,
        entertainment=ent_data,
        fun_fact=fun_fact,
        monthly_avg_day=monthly_avg_day,
        top_day_spending=top_day_spending,
        total_transactions=total_transactions,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    
    # Save HTML
    html_path = os.path.join(OUTPUT_DIR, "wrapped-latest.html")
    with open(html_path, "w") as f:
        f.write(html)
    
    # Generate PDF
    from weasyprint import HTML
    pdf_path = os.path.join(OUTPUT_DIR, f"wrapped-{start[:7]}.pdf")
    HTML(string=html).write_pdf(pdf_path)
    
    print(f"✅ PDF gerado: {pdf_path}")
    print(f"   HTML: {html_path}")
    return pdf_path

if __name__ == "__main__":
    generate()
