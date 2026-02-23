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
- Infra: Colima (containerd), Tailscale, Terraform (Oracle Cloud).

## Estrutura
- `assets/`: imagem e arquivos visuais do repositorio.
- `infra/oracle/terraform/`: infraestrutura na OCI.
- `hosts/`: configuracoes por host (`macmini` e placeholder `oracle-vps`).
- `services/media/`: configs da stack Jellyfin/ARR/Lingarr.
- `services/openclaw/`: snapshots e configs redacted do OpenClaw.
- `ops/scripts/`: scripts operacionais organizados por contexto.
- `notifications/apprise/`: templates de notificacao e integracao.
- `docs/runbooks/`: notas operacionais e checklists.
- `AGENTS.md`: playbook completo de operacao.

## Subir stack local (Mac mini)
```bash
./ops/scripts/media/arr-start-stack.sh
./ops/scripts/media/arr-status.sh
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
git push -u origin master
```
