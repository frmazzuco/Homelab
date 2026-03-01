# Homelab (infra + operacao)

## Visao geral
Este repositorio guarda a infraestrutura (Terraform), configuracoes redigidas e rotinas
operacionais do homelab.

Ambiente atual:
- Mac mini (Colima) para stack de midia + monitoramento + Apprise.
- Oracle VPS (OCI) para gateway OpenClaw em Docker Compose.

## Estrutura do repositorio
- `infra/oracle/terraform/`: provisao da VPS OCI (rede, VM, cloud-init, outputs).
- `hosts/macmini/`: snapshots/configs de launchd, energia e Tailscale do Mac mini.
- `hosts/oracle-vps/`: baseline e notas operacionais da VPS Oracle.
- `services/media/`: stack declarativa de midia+monitoramento (compose + env example).
- `services/openclaw/`: snapshots redigidos e templates do OpenClaw.
- `notifications/apprise/`: integracao de notificacao (webhook -> Apprise -> Telegram).
- `ops/scripts/`: scripts operacionais por contexto (`media`, `macmini`, `openclaw`, `oracle-vps`).
- `docs/runbooks/`: checklists e runbooks de operacao/seguranca.

## Estado real validado (2026-02-23)
### Mac mini (Colima)
- Perfil `default` em execucao: `8 CPU`, `12GiB RAM`, `40GiB`, runtime `containerd`.
- Containers ativos:
  - Midia: `jellyfin`, `jellyseerr`, `sonarr`, `radarr`, `prowlarr`, `bazarr`, `sabnzbd`, `lingarr`, `lingarr-db`, `whisper-asr`.
  - Monitoramento/suporte: `apprise-api`, `uptime-kuma`, `beszel`, `homepage`, `cloudbeaver`.

### Oracle VPS
- Host: `always-free-2gb`.
- Stack OpenClaw ativa em `/opt/openclaw`.
- Containers ativos: `openclaw-openclaw-gateway-1`, `openclaw-autoheal-1`.
- Timers/services ativos: `openclaw-health-check.timer`, `fail2ban`, `dnf-automatic.timer`.

## Mac mini: stack declarativa (replicavel)
A stack declarativa principal esta em:
- `services/media/docker-compose.yml`
- `services/media/.env.example`

Fluxo recomendado para subir a stack:
```bash
cp services/media/.env.example services/media/.env.local
# ajuste caminhos/segredos no arquivo local

# Docker Engine no host Linux:
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml up -d

# Colima + containerd (nerdctl) no macOS:
colima ssh -- sudo nerdctl compose --env-file /Users/SEU_USUARIO/caminho/repo/services/media/.env.local \
  -f /Users/SEU_USUARIO/caminho/repo/services/media/docker-compose.yml up -d
```

## Oracle VPS: OpenClaw
### Terraform
```bash
cd infra/oracle/terraform
terraform init
terraform apply
```

Variaveis importantes:
- `gateway_repo_url` (default: `https://github.com/openclaw/openclaw.git`)
- `gateway_repo_dir` (default: `/opt/openclaw`)
- `allowed_ssh_cidrs` e `allowed_tcp_ports` (minimo necessario)

### Acesso
```bash
ssh -i ~/.ssh/id_ed25519_oci opc@<IP_PUBLICO>
```

Tunnel para gateway local:
```bash
ssh -i ~/.ssh/id_ed25519_oci -L 18789:127.0.0.1:18789 opc@<IP_PUBLICO>
```

### Operacao do stack OpenClaw
```bash
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml up -d
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml down
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml logs -f openclaw-gateway
```

Comandos CLI (pass-through):
```bash
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml run --rm openclaw-cli --help
```

## Notificacoes (Apprise)
Fluxo padrao:
- `Jellyseerr webhook` -> `apprise-api` -> `Telegram`.
- Email fica como melhoria futura (sem SMTP no momento).

Referencia:
- `notifications/apprise/README.md`
- `notifications/apprise/apprise.env.example`

## Hardening e alertas
### SSH/F2B
- `AllowUsers` restrito ao usuario operacional.
- `PasswordAuthentication no`.
- Fail2ban ativo para SSH.

Checks:
```bash
sudo systemctl status fail2ban
sudo fail2ban-client status sshd
```

### Alertas Telegram (seguranca e saude)
- Ban/unban: `fail2ban-telegram-notify.service`
- Health OpenClaw: `openclaw-health-check.timer`

Checks:
```bash
sudo systemctl status fail2ban-telegram-notify
sudo systemctl status openclaw-health-check.timer
```

### Atualizacoes automaticas
- `dnf-automatic.timer` ativo (security updates).

Check:
```bash
sudo systemctl status dnf-automatic.timer
```

## Segredos
- Nao commitar tokens/chaves/sessoes.
- Segredos ficam fora do Git (`.env`, `terraform.tfvars`, chaves SSH, arquivos de auth).
- Checklist: `docs/runbooks/secrets-checklist.md`.

## Backups (minimo)
- Mac mini:
  - `$HOME/arr/config/*`
  - `$HOME/jellyfin/*`
  - snapshots de `LaunchAgents` e dotfiles
- Oracle:
  - `/home/opc/.openclaw/`
  - `/opt/openclaw/.env`
  - `/etc/systemd/system/*.service` e `*.timer`
  - arquivos de hardening (`sshd_config`, fail2ban, dnf)
