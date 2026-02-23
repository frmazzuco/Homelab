# Homelab

<p align="center">
  <img src="assets/homelab-house.svg" alt="Homelab house art" width="620" />
</p>

Repositorio principal do meu Homelab: infraestrutura, operacao e automacoes para stack de midia e servicos de suporte (Mac mini + Colima + OCI).

## O que tem aqui
- Infra OCI com Terraform.
- Rotinas operacionais e hardening.
- Integracoes de notificacao (Apprise, Telegram e webhooks).
- Scripts reais da stack (arr/jellyfin/openclaw/automacoes).
- Configuracoes redigidas para versionamento seguro.
- Base para evoluir o ambiente de homelab no GitHub.

## Stack atual (resumo)
- Midia: Jellyfin, Jellyseerr, Sonarr, Radarr, Bazarr, SABnzbd, Prowlarr.
- Suporte: Uptime Kuma, Beszel, Homepage, CloudBeaver.
- Automacao e IA: Lingarr, Whisper ASR.
- Gateway/IA remoto: OpenClaw na Oracle VPS.
- Infra: Colima (containerd), Tailscale, Terraform (Oracle Cloud).

## Estrutura
- `assets/`: imagem e arquivos visuais do repositorio.
- `infra/oracle/terraform/`: infraestrutura na OCI.
- `hosts/`: configuracoes por host (`macmini` e `oracle-vps`).
- `services/media/`: stack declarativa de midia/monitoramento (compose + env example + snapshots redacted).
- `services/openclaw/`: snapshots e templates redacted do OpenClaw.
- `ops/scripts/`: scripts operacionais organizados por contexto.
- `notifications/apprise/`: templates de notificacao e integracao.
- `docs/runbooks/`: notas operacionais e checklists.
- `AGENTS.md`: playbook completo de operacao.

## Subir stack local (Mac mini)
Fluxo declarativo recomendado:
```bash
cp services/media/.env.example services/media/.env.local
# ajuste caminhos/segredos no .env.local
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml up -d
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml ps
```

Fluxo legado (scripts run/start individuais):
```bash
./ops/scripts/media/arr-start-stack.sh
./ops/scripts/media/arr-status.sh
```

## OpenClaw na Oracle VPS
```bash
ssh -i ~/.ssh/id_ed25519_oci opc@<IP_PUBLICO>
sudo docker compose --env-file /opt/openclaw/.env -f /opt/openclaw/docker-compose.yml up -d
```

## Seguranca
- Este repo guarda apenas configuracoes versionaveis e snapshots redacted.
- Segredos ficam fora do Git (`.env`, chaves, tokens, `terraform.tfvars`, `terraform.tfstate`).
- Checklist de publish seguro: `docs/runbooks/secrets-checklist.md`.

## Publicar no GitHub como `Homelab`
1. Crie o repo no GitHub com nome `Homelab`.
2. Aponte o remoto local:
```bash
git remote add origin git@github.com:<seu-usuario>/Homelab.git
```
3. Suba o conteudo:
```bash
git add .
git commit -m "chore: organize homelab repo structure"
git push -u origin main
```
