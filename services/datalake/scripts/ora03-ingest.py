#!/usr/bin/env python3
"""
ORA 03 Data Lake Ingest
Coleta status do veículo e armazena no DuckDB.
"""
import json
import hashlib
import ssl
import http.client
import os
import sys
from datetime import datetime
import urllib.request
from pathlib import Path

# Usar DuckDB CLI via subprocess se lib não disponível
DUCKDB_CLI = "/tmp/duckdb"  # path pro CLI
USE_CLI = True  # usar CLI por padrão

try:
    import duckdb
    USE_CLI = False
except ImportError:
    import subprocess
    # Verifica se CLI existe
    if not os.path.exists(DUCKDB_CLI):
        print(f"ERROR: DuckDB CLI não encontrado em {DUCKDB_CLI}")
        print("Execute: pip3 install duckdb  OU baixe o CLI")
        sys.exit(1)

# Config
EMAIL = "chicomazfilho@gmail.com"
PASSWORD = "Chicom123"
VIN = "LGWEEUA57TK607201"
CERTS_DIR = os.environ.get("CERTS_DIR", "/home/node/.openclaw/workspace/repos/hassio-haval-h6-to-mqtt/haval-h6-mqtt/certs")
DB_PATH = os.environ.get("DUCKDB_PATH", "/home/node/.openclaw/workspace/skills/personal-datalake/datalake.duckdb")

# Endpoints
LOGIN_HOST = "br-front-service.gwmcloud.com"
LOGIN_PATH = "/br-official-commerce/br-official-gateway/pc-api/api/v1.0/userAuth/loginAccount"
API_HOST = "br-app-gateway.gwmcloud.com"
STATUS_PATH = "/app-api/api/v1.0/vehicle/getLastStatus"


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.load_cert_chain(
        os.path.join(CERTS_DIR, "gwm_general.cer"),
        os.path.join(CERTS_DIR, "gwm_general.key"),
    )
    ctx.load_verify_locations(os.path.join(CERTS_DIR, "gwm_root.cer"))
    ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    return ctx


def login():
    body = json.dumps({
        "account": EMAIL,
        "password": md5(PASSWORD),
        "deviceid": "ora2mqtt-datalake-001",
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "appid": "6", "brand": "6", "brandid": "CCZ001",
        "country": "BR", "devicetype": "0", "enterpriseid": "CC01",
        "gwid": "", "language": "pt_BR", "rs": "5", "terminal": "GW_PC_GWM",
    }
    ctx = ssl_context()
    conn = http.client.HTTPSConnection(LOGIN_HOST, context=ctx)
    conn.request("POST", LOGIN_PATH, body, headers)
    resp = json.loads(conn.getresponse().read())
    conn.close()
    if resp.get("code") != "000000":
        raise Exception(f"Login failed: {resp.get('description')}")
    return resp["data"]["accessToken"]


def get_status(token):
    headers = {
        "rs": "2", "terminal": "GW_APP_GWM", "brand": "6",
        "language": "pt_BR", "systemtype": "2", "regioncode": "BR",
        "country": "BR", "accessToken": token,
    }
    ctx = ssl_context()
    conn = http.client.HTTPSConnection(API_HOST, context=ctx)
    conn.request("GET", f"{STATUS_PATH}?vin={VIN}&flag=true", headers=headers)
    resp = json.loads(conn.getresponse().read())
    conn.close()
    if resp.get("code") != "000000":
        raise Exception(f"Status failed: {resp.get('description')}")
    return resp["data"]


def parse_sensor(items, code, default=None):
    """Extrai valor de um sensor específico."""
    for item in items:
        if item.get("code") == code:
            val = item.get("value", "")
            try:
                return float(val) if val and val != "" else default
            except (ValueError, TypeError):
                return default
    return default


def parse_bool_sensor(items, code, true_val="1"):
    """Extrai valor booleano de um sensor."""
    for item in items:
        if item.get("code") == code:
            return str(item.get("value")) == true_val
    return None



def reverse_geocode(lat, lon):
    """Reverse geocode lat/lon to address via Nominatim."""
    if lat is None or lon is None:
        return None
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=16&addressdetails=1"
        req = urllib.request.Request(url, headers={"User-Agent": "homelab-datalake/1.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return data.get("display_name", "")[:200]
    except Exception:
        return None
def ingest_snapshot(data):
    """Insere snapshot no DuckDB."""
    items = data.get("items", [])
    
    # Extrai campos
    timestamp = datetime.now()
    date = timestamp.date()
    
    battery_soc = parse_sensor(items, "2013021")          # %
    battery_range = parse_sensor(items, "2011501")        # km
    odometer_raw = parse_sensor(items, "2103010")  # totalDistance (km)
    if odometer_raw is None or odometer_raw == 0:
        odometer_raw = parse_sensor(items, "2042082")  # fallback
    odometer = odometer_raw
    is_locked = parse_bool_sensor(items, "2310001", "1")
    is_charging = parse_bool_sensor(items, "2013023", "5")
    is_ac_on = parse_bool_sensor(items, "2078020", "1")
    
    # Pneus (pressão kPa e temperatura °C)
    tire_fl_pressure = parse_sensor(items, "2101001")  # Front Left
    tire_fr_pressure = parse_sensor(items, "2101002")  # Front Right
    tire_rl_pressure = parse_sensor(items, "2101003")  # Rear Left
    tire_rr_pressure = parse_sensor(items, "2101004")  # Rear Right
    tire_fl_temp = parse_sensor(items, "2101005")
    tire_fr_temp = parse_sensor(items, "2101006")
    tire_rl_temp = parse_sensor(items, "2101007")
    tire_rr_temp = parse_sensor(items, "2101008")
    charging_time = parse_sensor(items, "2013022")  # min
    
    # Localização - vem no top-level do response
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    address = reverse_geocode(latitude, longitude)
    
    if USE_CLI:
        # Usar DuckDB CLI via subprocess
        import subprocess
        
        def sql_val(v):
            """Formata valor pra SQL"""
            if v is None:
                return "NULL"
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, (int, float)):
                return str(v)
            escaped = str(v).replace("'", "''")
            return f"'{escaped}'"
        
        sql = f"""
        INSERT INTO ora03_snapshots (
            timestamp, date,
            battery_soc, battery_range_km, odometer_km,
            latitude, longitude, address,
            is_locked, is_charging, is_ac_on,
            tire_fl_pressure, tire_fr_pressure, tire_rl_pressure, tire_rr_pressure,
            tire_fl_temp, tire_fr_temp, tire_rl_temp, tire_rr_temp,
            charging_time_min,
            raw_json
        ) VALUES (
            '{timestamp}', '{date}',
            {sql_val(battery_soc)}, {sql_val(battery_range)}, {sql_val(odometer)},
            {sql_val(latitude)}, {sql_val(longitude)}, {sql_val(address)},
            {sql_val(is_locked)}, {sql_val(is_charging)}, {sql_val(is_ac_on)},
            {sql_val(tire_fl_pressure)}, {sql_val(tire_fr_pressure)}, {sql_val(tire_rl_pressure)}, {sql_val(tire_rr_pressure)},
            {sql_val(tire_fl_temp)}, {sql_val(tire_fr_temp)}, {sql_val(tire_rl_temp)}, {sql_val(tire_rr_temp)},
            {sql_val(charging_time)},
            {sql_val(json.dumps(data))}
        );
        """
        result = subprocess.run(
            [DUCKDB_CLI, DB_PATH, "-c", sql],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"DuckDB CLI error: {result.stderr}")
    else:
        # Usar lib Python
        # Retry logic: DuckDB só permite 1 writer — espera até 3 tentativas
        import time as _time
        conn = None
        for _attempt in range(1, 4):
            try:
                conn = duckdb.connect(DB_PATH)
                break
            except Exception as _e:
                if _attempt == 3:
                    raise
                print(f"  [WARN] DuckDB lock conflict (tentativa {_attempt}/3): {_e}")
                _time.sleep(30)
        conn.execute("""
            INSERT INTO ora03_snapshots (
                timestamp, date,
                battery_soc, battery_range_km, odometer_km,
                latitude, longitude, address,
                is_locked, is_charging, is_ac_on,
                tire_fl_pressure, tire_fr_pressure, tire_rl_pressure, tire_rr_pressure,
                tire_fl_temp, tire_fr_temp, tire_rl_temp, tire_rr_temp,
                charging_time_min,
                raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            timestamp, date,
            battery_soc, battery_range, odometer,
            latitude, longitude, address,
            is_locked, is_charging, is_ac_on,
            tire_fl_pressure, tire_fr_pressure, tire_rl_pressure, tire_rr_pressure,
            tire_fl_temp, tire_fr_temp, tire_rl_temp, tire_rr_temp,
            charging_time,
            json.dumps(data)
        ])
        conn.commit()
        conn.close()
    
    return {
        "timestamp": str(timestamp),
        "battery_soc": battery_soc,
        "battery_range_km": battery_range,
        "odometer_km": odometer,
        "is_locked": is_locked,
        "is_charging": is_charging,
    }


def main():
    print("🔌 Conectando à API GWM...")
    token = login()
    print("✅ Autenticado")
    
    print("📡 Buscando status do veículo...")
    data = get_status(token)
    print("✅ Dados recebidos")
    
    print("💾 Inserindo no DuckDB...")
    result = ingest_snapshot(data)
    print("✅ Snapshot armazenado")
    
    print("\n📊 Resumo:")
    print(f"  Timestamp: {result['timestamp']}")
    if result['battery_soc'] is not None:
        print(f"  Bateria: {result['battery_soc']:.1f}%")
    if result['battery_range_km'] is not None:
        print(f"  Autonomia: {result['battery_range_km']:.0f} km")
    if result['odometer_km'] is not None:
        print(f"  Odômetro: {result['odometer_km']:.0f} km")
    if result['is_locked'] is not None:
        print(f"  Trancado: {'Sim' if result['is_locked'] else 'Não'}")
    if result['is_charging'] is not None:
        print(f"  Carregando: {'Sim' if result['is_charging'] else 'Não'}")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
