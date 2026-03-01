# Oracle VPS

Baseline operacional da VPS Oracle onde roda o gateway OpenClaw.

## Estado atual (2026-02-23)
- Host: `always-free-2gb`.
- OS: Oracle Linux 8.10.
- Stack ativo:
  - `openclaw-openclaw-gateway-1`
  - `openclaw-autoheal-1`
- Timers/services ativos:
  - `openclaw-health-check.timer`
  - `fail2ban`
  - `dnf-automatic.timer`

## Caminhos relevantes no host
- Repo: `/opt/openclaw`
- Compose: `/opt/openclaw/docker-compose.yml`
- Env: `/opt/openclaw/.env`
- Config/state do OpenClaw: `/home/opc/.openclaw`
- Script de health: `/usr/local/bin/openclaw-health-check.sh`

## Automacao e hardening versionados neste repo
- Terraform: `infra/oracle/terraform/`
- Preflight local: `ops/scripts/oracle-vps/preflight-check.sh`
- Checklist operacional: `docs/runbooks/oracle-vps-baseline-checklist.md`

## Comandos uteis
```bash
ssh -i ~/.ssh/id_ed25519_oci opc@<IP_PUBLICO>
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml ps
sudo systemctl status openclaw-health-check.timer fail2ban dnf-automatic.timer
```
