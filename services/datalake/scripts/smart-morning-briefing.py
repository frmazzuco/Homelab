#!/usr/bin/env python3
"""
Smart Morning Briefing — combina dados do ORA 03, clima e contexto
para gerar uma recomendação matinal prática.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

# === Config ===
DUCKDB_API = os.environ.get("DUCKDB_API_URL", "http://duckdb-api:8089")

def query_duckdb(sql):
    """Query DuckDB via HTTP API (POST /query with {query: sql})."""
    try:
        data = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            f"{DUCKDB_API}/query",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        print(f"⚠️ DuckDB query failed: {e}", file=sys.stderr)
        return None

def get_ora03_status():
    """Get latest ORA 03 battery/charging status."""
    result = query_duckdb("""
        SELECT battery_soc, battery_range_km, is_charging, is_locked,
               timestamp, address
        FROM ora03_snapshots
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    if result and isinstance(result, list) and len(result) > 0:
        row = result[0]
        return {
            "battery": row.get("battery_soc"),
            "autonomy": row.get("battery_range_km"),
            "charging": row.get("is_charging"),
            "locked": row.get("is_locked"),
            "timestamp": row.get("timestamp"),
            "address": row.get("address")
        }
    return None

def get_weather(city="Arroio+do+Silva"):
    """Get weather from wttr.in."""
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=pt"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        
        current = data.get("current_condition", [{}])[0]
        today = data.get("weather", [{}])[0]
        
        # Check for rain in hourly forecast
        rain_hours = []
        for hour in today.get("hourly", []):
            time_val = int(hour.get("time", "0")) // 100
            chance = int(hour.get("chanceofrain", "0"))
            if chance >= 40 and 6 <= time_val <= 22:
                rain_hours.append((time_val, chance))
        
        return {
            "temp": current.get("temp_C", "?"),
            "feels_like": current.get("FeelsLikeC", "?"),
            "humidity": current.get("humidity", "?"),
            "desc": current.get("lang_pt", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "?")),
            "max": today.get("maxtempC", "?"),
            "min": today.get("mintempC", "?"),
            "rain_hours": rain_hours,
            "uv": today.get("uvIndex", "?")
        }
    except Exception as e:
        print(f"⚠️ Weather failed: {e}", file=sys.stderr)
        return None

def generate_briefing():
    """Generate the smart morning briefing."""
    now = datetime.now()
    
    car = get_ora03_status()
    weather = get_weather()
    
    lines = []
    lines.append(f"🌅 **Bom dia! Briefing de {now.strftime('%d/%m')}**\n")
    
    # === Weather ===
    if weather:
        lines.append(f"🌡️ **Clima**: {weather['desc']}, {weather['temp']}°C (sensação {weather['feels_like']}°C)")
        lines.append(f"   Min {weather['min']}° / Máx {weather['max']}° — Umidade {weather['humidity']}% — UV {weather['uv']}")
        
        if weather['rain_hours']:
            rain_str = ", ".join(f"{h}h ({c}%)" for h, c in weather['rain_hours'])
            lines.append(f"   🌧️ **Chuva provável**: {rain_str}")
    
    # === Car ===
    if car:
        battery = car['battery']
        autonomy = car['autonomy']
        charging = car['charging']
        locked = car['locked']
        
        lines.append(f"\n🚗 **ORA 03**: {battery}% — {autonomy} km autonomia")
        
        if charging:
            lines.append("   ⚡ Carregando agora")
        
        if not locked:
            lines.append("   ⚠️ **DESTRANCADO!**")
        
        # === Smart recommendation ===
        lines.append(f"\n💡 **Recomendação**:")
        
        recommendations = []
        
        # Battery logic
        if battery <= 20:
            recommendations.append("🔴 Bateria crítica — carregue AGORA antes de sair")
        elif battery <= 40:
            if weather and weather['rain_hours']:
                recommendations.append("🟡 Bateria baixa + chuva prevista — carregue hoje (AC consome mais)")
            else:
                recommendations.append("🟡 Bateria baixa — considere carregar hoje")
        elif battery <= 60:
            recommendations.append("🟢 Bateria OK para o dia, mas programe carga nos próximos dias")
        else:
            recommendations.append("✅ Bateria boa, sem necessidade de carga")
        
        # Rain + car
        if weather and weather['rain_hours'] and not locked:
            recommendations.append("⚠️ Chuva prevista e carro destrancado — tranque!")
        elif not locked:
            recommendations.append("⚠️ Carro destrancado — tranque!")
        
        # Rain general
        if weather and weather['rain_hours']:
            first_rain = weather['rain_hours'][0][0]
            recommendations.append(f"☂️ Leve guarda-chuva — chuva prevista a partir das {first_rain}h")
        
        for rec in recommendations:
            lines.append(f"   {rec}")
    
    # No data fallback
    if not car and not weather:
        lines.append("⚠️ Sem dados disponíveis (DuckDB ou clima offline)")
    
    return "\n".join(lines)

if __name__ == "__main__":
    briefing = generate_briefing()
    print(briefing)
