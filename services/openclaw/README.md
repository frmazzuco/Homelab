# OpenClaw Service (Oracle VPS)

Documentacao e artefatos redigidos do stack OpenClaw que roda na Oracle VPS.

## Estado real (2026-02-23)
- Host: `always-free-2gb`
- Repo/runtime: `/opt/openclaw`
- Compose: `/opt/openclaw/docker-compose.yml`
- Env: `/opt/openclaw/.env`
- Config OpenClaw: `/home/opc/.openclaw`
- Containers:
  - `openclaw-openclaw-gateway-1`
  - `openclaw-autoheal-1`

## Arquivos deste diretorio
- `docker-compose.oracle.redacted.yml`: compose redigido com servicos e mounts estruturais.
- `.env.example`: variaveis necessarias para bootstrap do gateway.
- `configs/openclaw/*.redacted`: snapshots de config/launchd sem segredos.

## Operacao no host remoto
```bash
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml up -d
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml logs -f openclaw-gateway
```

## Health/alerta
- Script: `/usr/local/bin/openclaw-health-check.sh`
- Timer: `openclaw-health-check.timer`
- Integracao alerta Telegram via `fail2ban-telegram.sh`

## Seguranca
- Nao versionar `.env` real da VPS.
- Nao versionar cookies/session keys/tokens.
- Use `.env.example` apenas como template.
