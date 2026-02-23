# Apprise Notifications

Configuracao base para centralizar notificacoes da stack no Apprise e propagar para Telegram.

## Objetivo
- Receber eventos por webhook (Jellyseerr/automacoes/scripts).
- Fazer fan-out para Telegram agora.
- Preparar email como melhoria futura (quando houver SMTP).

## Arquivos
- `apprise.env.example`: placeholders de credenciais e destino.

## Formato recomendado de mensagem
Use quebra de linha real na mensagem (nao use o texto literal `\\n`), por exemplo:

```text
Homelab
Servico: Jellyseerr
Evento: Download concluido
Item: Nome do filme
```

## Proximos passos
1. Copiar `apprise.env.example` para um arquivo local nao versionado.
2. Preencher bot token/chat id do Telegram.
3. Criar a URL do Apprise com os destinos habilitados.
