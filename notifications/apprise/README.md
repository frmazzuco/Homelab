# Apprise Notifications

Configuracao de notificacoes centralizada:
- produtor: `jellyseerr` (webhook)
- router: `seerr-router` (FastAPI)
- broker/fan-out: `apprise-api`
- destino ativo: Telegram
- destino futuro: email (sem SMTP por enquanto)

## Fluxo recomendado
`Jellyseerr` -> `seerr-router` -> `apprise-api` -> `Telegram`

O `seerr-router` tenta identificar o usuario solicitante no payload e aplica roteamento por usuario.
Se nao houver rota dedicada, usa fallback.

## Arquivos
- `apprise.env.example`: placeholders de Telegram + SMTP (futuro).
- `jellyseerr-webhook-template.json`: payload linear simples (compativel).
- `jellyseerr-webhook-router-template.json`: payload recomendado para uso com `seerr-router`.

## Configuracao de env (`services/media/.env.local`)
1. Configure destino base do Apprise:
- `APPRISE_STATELESS_URLS=tgram://BOT_TOKEN/CHAT_ID/`
2. Configure o router:
- `SEERR_ROUTER_SHARED_TOKEN=<TOKEN_FORTE>`
- `SEERR_ROUTER_APPRISE_URL=http://apprise-api:8000/notify/`
- `SEERR_ROUTER_USER_DESTINATION_MAP={"usuario1":"tgram://BOT_TOKEN/CHAT_1/","usuario2":"tgram://BOT_TOKEN/CHAT_2/"}`
- `SEERR_ROUTER_DEFAULT_URLS=tgram://BOT_TOKEN/CHAT_FALLBACK/` (opcional)

## Configuracao no Jellyseerr
1. URL do webhook: `http://seerr-router:8080/webhook/jellyseerr`.
2. Header customizado (se disponivel na sua versao):
- `X-Seerr-Router-Token: <SEERR_ROUTER_SHARED_TOKEN>`
3. `types=2147483647` (todos os eventos).
4. JSON Payload: usar `jellyseerr-webhook-router-template.json`.

Se sua versao nao suportar header customizado, deixe `SEERR_ROUTER_SHARED_TOKEN` vazio.

## Como o roteamento funciona
1. O router extrai o solicitante por campos comuns (`requester`, `requested_by`, `request.requestedBy.username`) e fallback por texto.
2. Se houver match no `SEERR_ROUTER_USER_DESTINATION_MAP`, usa a URL do usuario.
3. Se nao houver match:
- usa `SEERR_ROUTER_DEFAULT_URLS` se definido.
- se estiver vazio, delega para `APPRISE_STATELESS_URLS`.

## Checklist rapido
1. `docker compose ... up -d` com `seerr-router` ativo.
2. Envie `Test Notification` no Jellyseerr.
3. Verifique log do router:
```bash
docker compose --env-file services/media/.env.local -f services/media/docker-compose.yml logs -f seerr-router
```
4. Valide recebimento no Telegram (chat do usuario ou fallback).

## Email (melhoria futura)
Quando tiver SMTP:
1. Preencha variaveis `APPRISE_SMTP_*`.
2. Adicione destino SMTP na URL/arquivo de config do Apprise.
3. Teste com uma notificacao manual antes de habilitar em producao.
