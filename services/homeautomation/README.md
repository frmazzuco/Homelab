# Home Automation (Mac Mini)

Stack de automacao residencial rodando na VM Colima do Mac Mini.

## Estado real (2026-03-01)
- Host: `mac-mini` (Colima `default`)
- Rede interna: `ha-net`

## Servicos

### Home Assistant
- Imagem: `ghcr.io/home-assistant/home-assistant:stable`
- Container: `homeassistant`
- Porta: `8123` (network_mode: host)
- URL Tailscale: `http://mac-mini-de-francisco.tailf1e5f9.ts.net:8123`
- Config: `~/homeassistant/config`

### Mosquitto (MQTT broker)
- Imagem: `eclipse-mosquitto:latest`
- Container: `mosquitto`
- Porta: `0.0.0.0:1883`
- Config: `~/mosquitto/config/mosquitto.conf`
  - `allow_anonymous true`, persistencia ativa, log em `~/mosquitto/log/`

### gwm-mqtt-connector (Haval H6)
- Imagem: `gwm-mqtt-connector:patched` (build local)
- Container: `gwm-connector`
- Fonte: `~/hassio-haval-h6-to-mqtt/` (fork do projeto hassio-haval-h6-to-mqtt)
- Publica telemetria do veiculo GWM Haval H6 no Mosquitto via MQTT
- Refresh: 10s, device tracker habilitado
- Credenciais via `.env` (nao versionar)

## Arquivos deste diretorio
- `docker-compose.macmini.redacted.yml`: compose redigido com variaveis de ambiente no lugar de segredos.
- `.env.example`: template das variaveis necessarias.

## Operacao no host

```bash
export PATH="$HOME/Tools/colima:$HOME/Tools/lima/bin:$PATH"
# Status
colima nerdctl -- ps | grep -E "homeassistant|mosquitto|gwm"
# Logs HA
colima nerdctl -- logs -f homeassistant
# Logs connector
colima nerdctl -- logs -f gwm-connector
```

## Build da imagem gwm-mqtt-connector

A imagem `gwm-mqtt-connector:patched` e um build local com patches sobre o projeto original:

```bash
cd ~/hassio-haval-h6-to-mqtt
colima nerdctl -- build -t gwm-mqtt-connector:patched .
```

## Seguranca
- Nao versionar `.env` real (contem credenciais GWM e VIN do veiculo).
- Use `.env.example` como template.
