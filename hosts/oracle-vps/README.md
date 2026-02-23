# Oracle VPS

Espaco para snapshots operacionais e baseline do host da VPS Oracle.

## O que ja existe
- Infra declarativa da VPS em `infra/oracle/terraform/`.
- Preflight local de Terraform em `ops/scripts/oracle-vps/preflight-check.sh`.

## O que ainda falta versionar (recomendado)
- Snapshots redacted de hardening:
  - `/etc/ssh/sshd_config`
  - `/etc/fail2ban/jail.d/sshd.local`
  - `/etc/dnf/automatic.conf`
- Snapshots redacted de systemd:
  - `openclaw-health-check.service/.timer`
  - `fail2ban-telegram-notify.service`
  - `ssh-login-telegram-notify.service`
- Inventario de backup/restore (o que e backupado, onde e periodicidade).

## Runbook
- `docs/runbooks/oracle-vps-baseline-checklist.md`
