#!/usr/bin/env python3
"""
DuckDB API simples para Grafana (JSON datasource)
Expõe queries DuckDB via HTTP/JSON
"""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from decimal import Decimal
import duckdb

DB_PATH = "/Users/franciscomazzucofilho/datalake/datalake.duckdb"
PORT = 8089


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder que converte Decimal para float e date para string"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        # Converter date/datetime para string
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)


class DuckDBHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/query":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request = json.loads(post_data.decode('utf-8'))
            
            query = request.get('query', '')
            if not query:
                self.send_error(400, "Missing query parameter")
                return
            
            try:
                conn = duckdb.connect(DB_PATH, read_only=True)
                result = conn.execute(query).fetchall()
                columns = [desc[0] for desc in conn.description] if conn.description else []
                conn.close()
                
                # Formato Grafana JSON - Infinity espera array de objetos para tabelas
                if len(columns) > 1:
                    # Múltiplas colunas = tabela = array de objetos
                    response = []
                    for row in result:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            row_dict[col] = row[i]
                        response.append(row_dict)
                else:
                    # Coluna única = valor único (para stats)
                    response = {
                        "columns": [{"text": col, "type": "string"} for col in columns],
                        "rows": result,
                        "type": "table"
                    }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response, cls=DecimalEncoder).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        elif self.path == "/search":
            # Lista de queries/tabelas disponíveis
            tables = [
                "ora03_snapshots",
                "ora03_last_30d",
                "ora03_daily_summary"
            ]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(tables).encode('utf-8'))
        
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        # Silenciar logs de request (opcional)
        sys.stderr.write(f"{self.address_string()} - {format % args}\n")


def main():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, DuckDBHandler)
    print(f"🚀 DuckDB API rodando em http://localhost:{PORT}")
    print(f"📊 Database: {DB_PATH}")
    print(f"🔗 Grafana JSON datasource URL: http://localhost:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado")
        sys.exit(0)
