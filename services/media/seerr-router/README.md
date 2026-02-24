# Seerr Router (FastAPI)

Servico intermediario para rotear notificacoes do Jellyseerr por usuario solicitante.

Fluxo:
`jellyseerr webhook` -> `seerr-router` -> `apprise-api` -> `Telegram`

## Endpoints
- `GET /healthz`: status do servico.
- `POST /webhook/jellyseerr`: recebe payload do Jellyseerr e encaminha ao Apprise.

## Variaveis
- `SEERR_ROUTER_APPRISE_URL`: endpoint de notificacao do Apprise (`http://apprise-api:8000/notify/`).
- `SEERR_ROUTER_SHARED_TOKEN`: token esperado no header `X-Seerr-Router-Token`.
- `SEERR_ROUTER_USER_DESTINATION_MAP`: JSON `usuario -> url(s)` do Apprise.
- `SEERR_ROUTER_DEFAULT_URLS`: URLs fallback (CSV), usado quando nao houver rota do usuario.
- `SEERR_ROUTER_HTTP_TIMEOUT_SECONDS`: timeout do envio para Apprise.
- `SEERR_ROUTER_LOG_LEVEL`: nivel de log.

## Formato do mapa de rotas
String JSON, exemplo:
```json
{"franciscomazzuco":"tgram://BOT_TOKEN/CHAT_ID_1/","convidado":["tgram://BOT_TOKEN/CHAT_ID_2/","mailto://smtp_user:smtp_pass@smtp.host/to@example.com"]}
```

Se `SEERR_ROUTER_DEFAULT_URLS` estiver vazio e nao houver match de usuario, o router encaminha sem `urls`, e o `apprise-api` usa `APPRISE_STATELESS_URLS`.
