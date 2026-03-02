# Mac mini

Conteudo especifico do host local do homelab.

- `launchagents/`: snapshots dos jobs do launchd (automacao local no macOS).
- `configs/`: snapshots de configuracao de energia e Tailscale.
- `services/media/docker-compose.yml`: stack declarativa usada na VM Colima.

## Observacoes importantes
- Os `.plist` atuais sao snapshots reais e podem conter caminhos absolutos de outro usuario/host.
- Antes de aplicar em outro Mac, rode:

```bash
./ops/scripts/macmini/audit-launchagents.sh
```

- Para baseline operacional do host, ver:
  - `docs/runbooks/macmini-baseline-checklist.md`

- Estado validado (2026-03-01):
  - Colima `default`: `8 CPU`, `12GiB`, `40GiB`, runtime `containerd`.
  - Stack midia+monitoramento ativa (Jellyfin/ARR/Jellyseerr/Lingarr/Apprise/Uptime/Beszel/Homepage/CloudBeaver).
  - Stack home automation ativa (Home Assistant/Mosquitto/gwm-mqtt-connector). Ver `services/homeautomation/`.
