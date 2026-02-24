# Mac mini Baseline Checklist

Checklist para manter o Mac mini do homelab consistente.

## Base do host
- `colima` instalado e funcional (`colima status`).
- `nerdctl` funcional dentro do Colima.
- `tailscale` conectado e com SSH habilitado.
- Espaco livre suficiente para media e transcode (>= 20% recomendado).

## LaunchAgents
- Rodar auditoria:
  - `./ops/scripts/macmini/audit-launchagents.sh`
- Confirmar `RunAtLoad`/`KeepAlive` apenas onde necessario.
- Remover caminhos hardcoded de usuario antigo (`/Users/...`) antes de reaplicar.

## Stack de midia
- Validar stack declarativa:
  - `docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml ps`
  - `docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml logs --tail 30 jellyseerr`
- Fluxo legado (se necessario):
  - `./ops/scripts/media/arr-start-stack.sh`
  - `./ops/scripts/media/arr-status.sh`
- Confirmar health das UIs (Jellyfin/ARR/Lingarr) apos reboot.
- Fixar tags de imagem (evitar `:latest`) para reduzir regressao inesperada.

## Notificacoes
- Confirmar webhook -> seerr-router -> Apprise -> Telegram com mensagem de teste.
- Usar template versionado em `notifications/apprise/jellyseerr-webhook-router-template.json`.
- Definir quais eventos sao obrigatorios (ex: download concluido, erro de indexer, health degraded).

## Backup e recuperacao
- Definir backup de:
  - `$HOME/arr/config/*`
  - bibliotecas/pastas de metadados criticas
  - snapshots de dotfiles e LaunchAgents
- Backup automatico de bancos da stack:
  - Script: `ops/scripts/media/media-db-backup.sh`
  - LaunchAgent: `hosts/macmini/launchagents/com.francisco.media-db-backup.plist`
  - Destino padrao: `$HOME/arr/backups/databases/stack-db-<timestamp>/`
  - Retencao padrao: `14` dias (`RETENTION_DAYS`)
- Validar restauracao em ambiente de teste periodicamente.
