# Mac mini

Conteudo especifico do host local do homelab.

- `dotfiles/`: shell profiles versionados.
- `launchagents/`: snapshots dos jobs do launchd (automacao local no macOS).
- `configs/`: snapshots de configuracao de energia e Tailscale.

## Observacoes importantes
- Os `.plist` atuais sao snapshots reais e podem conter caminhos absolutos de outro usuario/host.
- Antes de aplicar em outro Mac, rode:

```bash
./ops/scripts/macmini/audit-launchagents.sh
```

- Para baseline operacional do host, ver:
  - `docs/runbooks/macmini-baseline-checklist.md`
