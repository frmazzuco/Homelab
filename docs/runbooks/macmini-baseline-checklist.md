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
- Validar start/status:
  - `./ops/scripts/media/arr-start-stack.sh`
  - `./ops/scripts/media/arr-status.sh`
- Confirmar health das UIs (Jellyfin/ARR/Lingarr) apos reboot.
- Fixar tags de imagem (evitar `:latest`) para reduzir regressao inesperada.

## Notificacoes
- Confirmar webhook -> Apprise -> Telegram com mensagem de teste.
- Padronizar payload para evitar `\\n` literal no Telegram.
- Definir quais eventos sao obrigatorios (ex: download concluido, erro de indexer, health degraded).

## Backup e recuperacao
- Definir backup de:
  - `$HOME/arr/config/*`
  - bibliotecas/pastas de metadados criticas
  - snapshots de dotfiles e LaunchAgents
- Validar restauracao em ambiente de teste periodicamente.
