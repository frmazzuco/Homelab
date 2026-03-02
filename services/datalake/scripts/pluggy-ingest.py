#!/usr/bin/env python3
"""
Pluggy (Nubank) Data Ingest para DuckDB
Coleta transações e saldos do Nubank via API Pluggy
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import urllib.error

# Configuração
WORKSPACE = "/home/node/.openclaw/workspace"
CONFIG_PATH = os.environ.get("PLUGGY_CONFIG_PATH", f"{WORKSPACE}/nubank-config.json")
DB_PATH = os.environ.get("DUCKDB_PATH", f"{WORKSPACE}/skills/personal-datalake/datalake.duckdb")
DUCKDB_CLI = "/tmp/duckdb"

# Carregar config
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

PLUGGY_CLIENT_ID = config['pluggy']['clientId']
PLUGGY_CLIENT_SECRET = config['pluggy']['clientSecret']
PLUGGY_ITEM_ID = config['pluggy']['itemId']
CONTA_CORRENTE_ID = config['accounts']['conta_corrente']['id']
CARTAO_CREDITO_ID = config['accounts']['cartao']['id']

BASE_URL = "https://api.pluggy.ai"


def get_access_token():
    """Obter token de acesso da API Pluggy"""
    data = json.dumps({
        "clientId": PLUGGY_CLIENT_ID,
        "clientSecret": PLUGGY_CLIENT_SECRET
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{BASE_URL}/auth",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"  DEBUG Auth response: {result}")
            return result.get('accessToken') or result.get('apiKey')
    except Exception as e:
        print(f"  DEBUG Auth error: {e}")
        raise


def get_transactions(access_token, account_id, from_date=None, to_date=None):
    """Buscar transações de uma conta"""
    params = {"accountId": account_id}
    
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    
    url = f"{BASE_URL}/transactions?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-API-KEY": access_token})
    
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    # Pluggy pode retornar paginado
    transactions = data.get('results', [])
    
    # Paginar se necessário
    while data.get('hasNextPage', False):
        params['page'] = data.get('page', 0) + 1
        url = f"{BASE_URL}/transactions?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"X-API-KEY": access_token})
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            transactions.extend(data.get('results', []))
    
    return transactions


def get_account_balance(access_token, account_id):
    """Obter saldo atual de uma conta"""
    req = urllib.request.Request(
        f"{BASE_URL}/accounts/{account_id}",
        headers={"X-API-KEY": access_token}
    )
    
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))


def insert_transactions_to_duckdb(transactions, account_type):
    """Inserir transações no DuckDB"""
    if not transactions:
        print(f"  Nenhuma transação para inserir ({account_type})")
        return 0
    
    # Preparar SQL com VALUES
    values = []
    for txn in transactions:
        txn_id = txn.get('id', '')
        date = txn.get('date', '')[:10] if txn.get('date') else None
        timestamp = txn.get('date', '')
        amount = txn.get('amount', 0)
        category = txn.get('category', '') or 'Outros'
        merchant = txn.get('description', '') or txn.get('merchant', {}).get('name', '')
        description = txn.get('description', '')
        raw_json = json.dumps(txn).replace("'", "''")
        
        if not date or not txn_id:
            continue
        
        # Escapar aspas
        merchant_clean = merchant.replace("'", "''")
        description_clean = description.replace("'", "''")
        category_clean = category.replace("'", "''")
        
        values.append(
            f"('{txn_id}', '{date}', '{timestamp}', {amount}, '{category_clean}', "
            f"'{merchant_clean}', '{description_clean}', '{account_type}', '{raw_json}')"
        )
    
    if not values:
        print(f"  Nenhuma transação válida para inserir ({account_type})")
        return 0
    
    sql = f"""
    INSERT OR IGNORE INTO nubank_transactions 
    (id, date, timestamp, amount, category, merchant, description, account_type, raw_json)
    VALUES {', '.join(values)};
    """
    
    # Executar via DuckDB CLI
    result = subprocess.run(
        [DUCKDB_CLI, DB_PATH],
        input=sql,
        text=True,
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"  ERRO ao inserir: {result.stderr}")
        return 0
    
    print(f"  ✅ {len(values)} transações inseridas ({account_type})")
    return len(values)


def main():
    print("🏦 Pluggy (Nubank) Data Ingest")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Obter token
        print("🔑 Autenticando...")
        token = get_access_token()
        print("✅ Autenticado")
        print()
        
        # Definir período (últimos 90 dias por padrão)
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        total_inserted = 0
        
        # Conta Corrente
        print("💳 Conta Corrente (Nu Pagamentos)")
        txns_checking = get_transactions(token, CONTA_CORRENTE_ID, from_date, to_date)
        print(f"  📊 {len(txns_checking)} transações encontradas")
        inserted = insert_transactions_to_duckdb(txns_checking, 'checking_account')
        total_inserted += inserted
        
        # Saldo atual
        balance = get_account_balance(token, CONTA_CORRENTE_ID)
        saldo_atual = balance.get('balance', 0)
        print(f"  💰 Saldo atual: R$ {saldo_atual:,.2f}")
        print()
        
        # Cartão de Crédito
        print("💎 Cartão de Crédito (Ultraviolet Black)")
        txns_credit = get_transactions(token, CARTAO_CREDITO_ID, from_date, to_date)
        print(f"  📊 {len(txns_credit)} transações encontradas")
        inserted = insert_transactions_to_duckdb(txns_credit, 'credit_card')
        total_inserted += inserted
        
        # Limite do cartão
        credit_info = get_account_balance(token, CARTAO_CREDITO_ID)
        limite = credit_info.get('creditData', {}).get('limit', 0)
        utilizado = abs(credit_info.get('balance', 0))
        print(f"  💎 Limite: R$ {limite:,.2f}")
        print(f"  📊 Utilizado: R$ {utilizado:,.2f} ({(utilizado/limite*100) if limite else 0:.1f}%)")
        print()
        
        # Resumo
        print("=" * 60)
        print(f"✅ Total de transações inseridas: {total_inserted}")
        print(f"📅 Período: {from_date} até {to_date}")
        
        # Estatísticas do banco
        stats_sql = """
        SELECT 
            account_type,
            COUNT(*) as total_txns,
            MIN(date) as primeira,
            MAX(date) as ultima,
            ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 2) as total_gastos,
            ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as total_receitas
        FROM nubank_transactions
        GROUP BY account_type;
        """
        
        result = subprocess.run(
            [DUCKDB_CLI, DB_PATH, "-json"],
            input=stats_sql,
            text=True,
            capture_output=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            stats = json.loads(result.stdout)
            print()
            print("📊 Estatísticas do banco:")
            for stat in stats:
                tipo = "Conta Corrente" if stat['account_type'] == 'checking_account' else "Cartão de Crédito"
                print(f"\n  {tipo}:")
                print(f"    • Total de transações: {stat['total_txns']}")
                print(f"    • Período: {stat['primeira']} até {stat['ultima']}")
                print(f"    • Total gastos: R$ {abs(stat['total_gastos']):,.2f}")
                print(f"    • Total receitas: R$ {stat['total_receitas']:,.2f}")
        
        print()
        print("✅ Ingest concluído com sucesso!")
        
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.reason}")
        print(f"   Response: {e.read().decode('utf-8') if hasattr(e, 'read') else 'N/A'}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
