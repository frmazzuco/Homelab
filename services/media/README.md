# Media + Monitoring Stack

Stack declarativa da VM Colima (midia, notificacoes e monitoramento), espelhando o estado real validado em `2026-02-23`.

## Arquivos principais
- `docker-compose.yml`: stack completa (15 servicos).
- `.env.example`: variaveis de paths, portas, imagens e segredos.
- `configs/arr/`: snapshots redacted de configuracoes relevantes.
- `configs/lingarr/`: template de runtime do Lingarr.

## Servicos incluidos
- Midia: `jellyfin`, `jellyseerr`, `sabnzbd`, `sonarr`, `radarr`, `prowlarr`, `bazarr`.
- Automacao/IA: `lingarr`, `lingarr-db`, `whisper-asr`.
- Notificacoes/monitoramento: `apprise-api`, `uptime-kuma`, `beszel`, `homepage`, `cloudbeaver`.

## Bootstrap rapido
1. Copie o env base:
```bash
cp services/media/.env.example services/media/.env.local
```
2. Ajuste no `.env.local`:
- caminhos locais (`ARR_CONFIG_ROOT`, `MEDIA_ROOT`, `JELLYFIN_CONFIG_DIR`)
- segredos (`APPRISE_STATELESS_URLS`, `LINGARR_*_PASSWORD`, `LINGARR_GEMINI_API_KEY`)
- politica de exposicao de portas (`*_BIND_HOST`)
3. Crie os diretorios-base (se ainda nao existirem):
```bash
mkdir -p \
  "$HOME/arr/config" \
  "$HOME/arr/cloudbeaver/workspace" \
  "$HOME/Media/Entrada/incomplete" \
  "$HOME/Media/Filmes" \
  "$HOME/Media/Series" \
  "$HOME/jellyfin/config" \
  "$HOME/jellyfin/cache"
```

## Subir a stack
### Docker Compose (host Linux)
```bash
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml up -d
```

### Colima + containerd (nerdctl)
```bash
colima ssh -- sudo nerdctl compose \
  --env-file /Users/SEU_USUARIO/caminho/repo/services/media/.env.local \
  -f /Users/SEU_USUARIO/caminho/repo/services/media/docker-compose.yml up -d
```

## Operacao
```bash
# status
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml ps

# logs (exemplo jellyseerr)
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml logs -f jellyseerr

# stop
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml down
```

## Notificacoes (Jellyseerr -> Apprise -> Telegram)
- `jellyseerr` usa webhook para `http://apprise-api:8000/notify/` (rede interna do compose).
- Apprise faz fan-out para Telegram via `APPRISE_STATELESS_URLS`.
- Snapshot redacted atual: `configs/arr/jellyseerr.notifications.redacted.json`.
- Template recomendado de payload: `notifications/apprise/jellyseerr-webhook-template.json`.

## Mapa de volumes
- Config ARR: `${ARR_CONFIG_ROOT}/<servico>` -> diretories internos `/config`.
- Midia: `${MEDIA_ROOT}` -> `/media`.
- Downloads: `${MEDIA_DOWNLOADS_ROOT}` -> `/downloads`.
- Jellyfin: `${JELLYFIN_CONFIG_DIR}` e `${JELLYFIN_CACHE_DIR}`.
- Lingarr DB: `${ARR_CONFIG_ROOT}/lingarr-mysql` -> `/var/lib/mysql`.

## Seguranca
- Evite `latest` em producao: fixe tags quando quiser reduzir regressao.
- Mantenha servicos de suporte em `127.0.0.1` (Apprise/Uptime/Beszel/Homepage/CloudBeaver/Jellyfin) se nao precisar expor na LAN.
- Nao commite `.env.local`.
