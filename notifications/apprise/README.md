# Apprise Notifications

Configuracao de notificacoes centralizada:
- produtor: `jellyseerr` (webhook)
- broker/fan-out: `apprise-api`
- destino ativo: Telegram
- destino futuro: email (sem SMTP por enquanto)

## Estado atual (validado em 2026-02-23)
- No Jellyseerr, o agente `webhook` esta `enabled=true`.
- `types=2147483647` (todos os eventos de notificacao do Jellyseerr).
- URL interna usada: `http://apprise-api:8000/notify/`.
- Snapshot redacted: `services/media/configs/arr/jellyseerr.notifications.redacted.json`.

## Arquivos
- `apprise.env.example`: placeholders de Telegram + SMTP (futuro).
- `jellyseerr-webhook-template.json`: payload recomendado para evitar `\\n` literal no Telegram.

## Payload recomendado (Jellyseerr)
Use o conteudo de `jellyseerr-webhook-template.json` no campo **JSON Payload** do webhook.

Motivo:
- Mensagem linear (com `|`) evita o problema visual de `\\n` literal.
- Continua legivel em Telegram, email e outros canais futuros.

## Checklist rapido
1. Defina `APPRISE_STATELESS_URLS` no `.env.local` da stack (`tgram://BOT_TOKEN/CHAT_ID/`).
2. No Jellyseerr, webhook URL = `http://apprise-api:8000/notify/`.
3. Envie `Test Notification` no Jellyseerr.
4. Valide recebimento no Telegram.

## Email (melhoria futura)
Quando tiver SMTP:
1. Preencha variaveis `APPRISE_SMTP_*`.
2. Adicione destino SMTP na URL/arquivo de config do Apprise.
3. Teste com uma notificacao manual antes de habilitar em producao.
