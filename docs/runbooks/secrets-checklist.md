# Secrets Checklist Before Push

Checklist rapido antes de publicar no GitHub.

- Confirmar que `.env` local nao esta staged (`git status`).
- Confirmar que `terraform.tfvars` nao esta staged.
- Confirmar que `terraform.tfstate*` nao esta staged.
- Verificar se nao existe token real em arquivos `*.yaml`, `*.json`, `*.txt`.
- Verificar se arquivos de chaves (`*.pem`, `*.key`, `*.p12`) nao foram adicionados.
- Revisar diff final com `git diff --staged`.

Comando util de varredura local:

```bash
rg -n "(token|api[_-]?key|secret|password|smtp|bearer)" . \
  -g '!**/.git/**' \
  -g '!**/.terraform/**'
```
