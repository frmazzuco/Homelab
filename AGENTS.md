# Moltbot (infra + operacao)

## Visao geral
Este repositorio guarda a infraestrutura (Terraform) e as rotinas de operacao para um
gateway do Moltbot rodando em uma VM Oracle Cloud (OCI). O bot roda via Docker Compose
no host remoto e expomos o gateway por tunel SSH quando preciso.

## Estrutura do repositorio
- `infra/oracle/terraform/`: Infra OCI (rede, instancia, outputs, cloud-init). Ver `infra/oracle/terraform/README.md`.
- `.env`: uso local apenas (nao versionado).

## Infra (Terraform OCI)
Entre na pasta e aplique:
```bash
cd infra/oracle/terraform
terraform init
terraform apply -auto-approve
```
Use `infra/oracle/terraform/README.md` e `infra/oracle/terraform/terraform.tfvars.example` como referencia
para as variaveis. As credenciais nao devem ser commitadas.

## Acesso a VM
Host atual (exemplo usado neste projeto):
- IP: `137.131.165.40`
- Usuario: `opc`
- Chave: `~/.ssh/id_ed25519_oci`

SSH direto:
```bash
ssh -i ~/.ssh/id_ed25519_oci opc@137.131.165.40
```

## Tunel para o gateway (Control UI / RPC)
Para acessar o gateway localmente:
```bash
ssh -i ~/.ssh/id_ed25519_oci -L 18789:127.0.0.1:18789 opc@137.131.165.40
```
Depois disso, use a porta local `18789` no seu browser ou na Control UI (quando aplicavel).

## Onde o Moltbot roda
No host remoto:
- Repo clonado em `/opt/moltbot`
- Compose: `/opt/moltbot/docker-compose.yml`
- Config: `/home/opc/.clawdbot/moltbot.json`
- Estado/credenciais: `/home/opc/.clawdbot/`
- Env do Compose: `/opt/moltbot/.env`

## Subir / Descer o stack
```bash
sudo docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml up -d
sudo docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml down
```

Logs do gateway:
```bash
sudo docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml logs -f moltbot-gateway
```

## CLI do Moltbot (no host)
Use sempre o `--env-file`:
```bash
sudo docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml run --rm moltbot-cli status
sudo docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml run --rm moltbot-cli models status --plain
```

## Telegram (canal principal)
Configuracao no arquivo `/home/opc/.clawdbot/moltbot.json`:
```json5
{
  channels: {
    telegram: {
      enabled: true,
      botToken: "<TOKEN_DO_BOTFATHER>",
      dmPolicy: "pairing"
    }
  }
}
```

### Pairing (DM)
1) Envie uma mensagem para o bot no Telegram.
2) O bot retorna um codigo de pairing.
3) Aprove no host:
```bash
docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml run --rm moltbot-cli pairing list telegram
docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml run --rm moltbot-cli pairing approve telegram <CODIGO>
```

## Modelo (Anthropic)
Ver status e trocar modelo:
```bash
docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml run --rm -T moltbot-cli models status --plain
docker compose --env-file /opt/moltbot/.env -f /opt/moltbot/docker-compose.yml run --rm -T moltbot-cli models set anthropic/claude-sonnet-4-5
```

## Seguranca (tokens)
- Nao commitar tokens (BotFather, gateway, Anthropic).
- Tokens ficam no host remoto, por exemplo:
  - `/home/opc/.clawdbot/moltbot.json` (config)
  - `/home/opc/.clawdbot/agents/main/agent/auth-profiles.json` (auth)
  - `/opt/moltbot/.env` (gateway compose)

## Hardening (SSH + alertas)
### SSH hardening
Aplicado no host (`/etc/ssh/sshd_config`):
- `AllowUsers opc`
- `MaxAuthTries 3`
- `LoginGraceTime 20`
- `AllowAgentForwarding no`
- `AllowTcpForwarding local`
- `PermitOpen 127.0.0.1:18789`

Backup: `/etc/ssh/sshd_config.bak.*`

### Fail2ban (SSH)
- Fail2ban instalado no host (Oracle Linux 8).
- Jail do SSH: `/etc/fail2ban/jail.d/sshd.local`.
- Logs: `/var/log/fail2ban.log`.

Checar status:
```bash
sudo systemctl status fail2ban
sudo fail2ban-client status sshd
```

### Alertas Telegram (ban/unban)
Para evitar relaxar o SELinux do Fail2ban, o alerta usa um **notifier separado**
que le o log do Fail2ban e envia ao Telegram.

Arquivos no host:
- Token/Chat: `/etc/fail2ban/telegram.env` (permissao 600).
- Script de envio: `/usr/local/bin/fail2ban-telegram.sh`.
- Notifier: `/usr/local/bin/fail2ban-telegram-notify.sh`.
- Service: `/etc/systemd/system/fail2ban-telegram-notify.service`.
- Log de erro do notifier: `/var/log/fail2ban-telegram.log`.

Status:
```bash
sudo systemctl status fail2ban-telegram-notify
```

Teste manual (simula ban/unban no SSH):
```bash
sudo fail2ban-client set sshd banip 1.2.3.4
sudo fail2ban-client set sshd unbanip 1.2.3.4
```

### Alertas Telegram (login SSH bem-sucedido)
Notifier dedicado para logins aceitos pelo SSH (le `/var/log/secure`):
- Script: `/usr/local/bin/ssh-login-notify.sh`.
- Service: `/etc/systemd/system/ssh-login-telegram-notify.service`.
- Log de erro: `/var/log/ssh-login-telegram.log`.

Status:
```bash
sudo systemctl status ssh-login-telegram-notify
```

Teste real: abra um novo SSH e confirme a mensagem no Telegram.

### Repositorios e atualizacoes
Para instalar o Fail2ban foi habilitado o repo `ol8_developer_EPEL`.
Se quiser reduzir superficie de supply-chain, desabilite apos instalar:
```bash
sudo dnf config-manager --set-disabled ol8_developer_EPEL
```

### Updates automaticos (security-only)
`dnf-automatic` configurado para aplicar apenas updates de seguranca.

Arquivos:
- Config: `/etc/dnf/automatic.conf`
- Backup: `/etc/dnf/automatic.conf.bak`
- Timer: `dnf-automatic.timer`

Checar status:
```bash
sudo systemctl status dnf-automatic.timer
```

## Saude do gateway (health + auto-restart + alerta)
### Healthcheck no Compose
O `moltbot-gateway` tem healthcheck via CLI:
```yaml
healthcheck:
  test: ["CMD", "node", "dist/index.js", "health", "--json", "--timeout", "5000"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### Auto-restart quando unhealthy
O Compose inclui o sidecar `autoheal` (imagem `willfarrell/autoheal`) e label
`autoheal=true` no gateway. Quando o healthcheck fica `unhealthy`, o container
e reiniciado automaticamente.

### Alertas de saude (Telegram)
Um timer systemd checa o status do healthcheck e envia alerta no Telegram
quando muda para `unhealthy`/`missing`/`nohealth` e quando recupera.

Arquivos no host:
- Script: `/usr/local/bin/openclaw-health-check.sh`
- Service: `/etc/systemd/system/openclaw-health-check.service`
- Timer: `/etc/systemd/system/openclaw-health-check.timer`
- Estado: `/var/lib/openclaw/health-status`

Status:
```bash
sudo systemctl status openclaw-health-check.timer
sudo systemctl status openclaw-health-check.service
```
