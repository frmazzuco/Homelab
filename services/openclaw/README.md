# OpenClaw Service (Oracle VPS)

Documentacao e artefatos redigidos do stack OpenClaw que roda na Oracle VPS.

## Estado real (2026-03-01)
- Versao: `2026.3.1` (atualizado de 2026.2.9)
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

## Procedimento de update
```bash
# Na VPS:
cd /opt/openclaw && git pull origin main
sudo docker build --build-arg OPENCLAW_DOCKER_APT_PACKAGES= -t openclaw:local -f Dockerfile .
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml up -d --force-recreate openclaw-gateway
```

### Breaking change v2026.3.x: controlUi.allowedOrigins
Bind `lan` exige `gateway.controlUi.allowedOrigins` ou:
```json
"controlUi": { "dangerouslyAllowHostHeaderOriginFallback": true }
```
Aplicado em `/home/opc/.openclaw/openclaw.json` em 2026-03-01.

## Seguranca
- Nao versionar `.env` real da VPS.
- Nao versionar cookies/session keys/tokens.
- Use `.env.example` apenas como template.
