# Ops Scripts

Scripts utilitarios organizados por contexto.

- `media/`: start/stop/status da stack e workers de midia (fluxo legado por `nerdctl run/start`).
- `macmini/`: scripts locais de dotfiles, automacao assistida e auditoria de LaunchAgents.
- `openclaw/`: watchdog e utilitarios do OpenClaw.
- `oracle-vps/`: preflight de Terraform e checagens basicas da VPS Oracle.

Para fluxo declarativo da stack de midia/monitoramento, prefira:
- `services/media/docker-compose.yml`
- `services/media/.env.example`
