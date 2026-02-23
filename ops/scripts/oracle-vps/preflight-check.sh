#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TF_DIR="$REPO_ROOT/infra/oracle/terraform"

warn_count=0
err_count=0

ok() {
  printf '[OK] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*"
  warn_count=$((warn_count + 1))
}

err() {
  printf '[ERR] %s\n' "$*"
  err_count=$((err_count + 1))
}

echo "Preflight Oracle VPS (repo): $REPO_ROOT"
echo

if [ ! -d "$TF_DIR" ]; then
  err "Diretorio Terraform nao encontrado: $TF_DIR"
  echo
  echo "Falhou com erro."
  exit 1
fi
ok "Diretorio Terraform encontrado"

for required in main.tf variables.tf outputs.tf versions.tf cloud-init.yaml.tftpl terraform.tfvars.example; do
  if [ -f "$TF_DIR/$required" ]; then
    ok "Arquivo presente: $required"
  else
    err "Arquivo ausente: $required"
  fi
done

if command -v terraform >/dev/null 2>&1; then
  if terraform -chdir="$TF_DIR" fmt -check -recursive >/dev/null 2>&1; then
    ok "terraform fmt -check"
  else
    warn "terraform fmt detectou arquivos fora do padrao"
  fi

  if terraform -chdir="$TF_DIR" validate -no-color >/dev/null 2>&1; then
    ok "terraform validate"
  else
    warn "terraform validate falhou (rode terraform init primeiro, se necessario)"
  fi
else
  warn "terraform nao encontrado no PATH"
fi

if [ -f "$TF_DIR/terraform.tfvars" ]; then
  ok "terraform.tfvars local existe"
  if rg -n '0\\.0\\.0\\.0/0' "$TF_DIR/terraform.tfvars" >/dev/null 2>&1; then
    warn "terraform.tfvars contem 0.0.0.0/0 (revise exposicao de SSH/servicos)"
  fi
else
  warn "terraform.tfvars local nao encontrado (ok se ainda nao configurado)"
fi

if git -C "$REPO_ROOT" check-ignore "$TF_DIR/terraform.tfvars" >/dev/null 2>&1; then
  ok "terraform.tfvars ignorado pelo git"
else
  err "terraform.tfvars NAO esta sendo ignorado pelo git"
fi

if git -C "$REPO_ROOT" check-ignore "$TF_DIR/terraform.tfstate" >/dev/null 2>&1; then
  ok "terraform.tfstate ignorado pelo git"
else
  err "terraform.tfstate NAO esta sendo ignorado pelo git"
fi

echo
echo "Resumo: $warn_count aviso(s), $err_count erro(s)."
if [ "$err_count" -gt 0 ]; then
  exit 1
fi
