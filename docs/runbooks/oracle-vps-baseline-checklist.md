# Oracle VPS Baseline Checklist

Checklist para garantir que a VPS Oracle esteja segura e operacional.

## Terraform / provisao
- Rodar preflight local:
  - `./ops/scripts/oracle-vps/preflight-check.sh`
- `allowed_ssh_cidrs` restrito (evitar `0.0.0.0/0`).
- `allowed_tcp_ports` minimo necessario.
- Revisar `cloud-init` antes de `terraform apply`.

## Acesso e hardening
- SSH sem senha (`PasswordAuthentication no`).
- `AllowUsers` restrito ao usuario operacional.
- Fail2ban ativo e com jail de SSH validada.
- Atualizacoes de seguranca automaticas ativas (`dnf-automatic`).

## Observabilidade e alertas
- Services/timers ativos:
  - `openclaw-health-check.timer`
  - `fail2ban-telegram-notify.service`
- Alerta de teste no Telegram para cada fluxo.

## Backup e DR
- Definir backup de:
  - `/home/opc/.openclaw/`
  - `/opt/openclaw/.env` (com criptografia)
  - `/opt/openclaw/docker-compose.yml`
  - `/etc/systemd/system/*.service` e `*.timer`
  - arquivos de hardening (`sshd_config`, fail2ban, dnf-automatic)
- Testar restore em host limpo (simulado) com periodicidade.

## Hygiene operacional
- Desabilitar repositorios temporarios nao essenciais apos uso.
- Revisar periodicamente logs de seguranca e falhas de healthcheck.
- Manter runbook de incidentes com passos de rollback.
