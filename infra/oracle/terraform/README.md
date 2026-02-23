# OCI A1 Flex 4 OCPU / 26 GB (Terraform)

Este modulo cria:
- VCN, subnet publica, internet gateway e route table
- Network Security Group (NSG) com SSH limitado por CIDR
- Instancia VM.Standard.A1.Flex com 4 OCPU e 26 GB
- Boot volume com 200 GB (ajustavel por `boot_volume_size_gbs`)
- Cloud-init com hardening basico (sem senha, firewall ativo)

## Como usar

1. Copie `terraform.tfvars.example` para `terraform.tfvars` e preencha os valores.
2. Garanta que sua chave publica SSH exista no caminho informado.
   Se precisar, adicione chaves extras em `additional_ssh_public_keys`.
3. Rode:

```bash
terraform init
terraform apply
```

## Ajustes para OpenClaw
- Mantenha `allowed_ssh_cidrs` restrito ao seu IP publico.
- Se precisar expor uma porta especifica para o gateway, use `allowed_tcp_ports` e `allowed_tcp_cidrs`.
- O firewall do SO so libera portas definidas em `allowed_tcp_ports`.
- Se o gateway e o browser tool rodam na mesma VM, nao exponha as portas do browser (use loopback).
- Para acessar a UI do gateway com seguranca, prefira um tunnel SSH:

```bash
ssh -L 18789:127.0.0.1:18789 opc@SEU_IP_PUBLICO
```

## Bootstrap do repo no host
- O `cloud-init` prepara Docker e clona o repo do gateway no host.
- Variaveis para ajustar:
  - `gateway_repo_url` (default: `https://github.com/openclaw/openclaw.git`)
  - `gateway_repo_dir` (default: `/opt/openclaw`)

## Observacoes
- `VM.Standard.A1.Flex` com 4 OCPU / 26 GB pode ultrapassar limites Always Free (verifique seus limites na tenancy).
- A imagem e selecionada pela combinacao de OS/versao. Altere `operating_system` se preferir Ubuntu e ajuste `ssh_user`.
- Se ocorrer `Out of host capacity`, ajuste `availability_domain_index` para outro AD (1 ou 2).
