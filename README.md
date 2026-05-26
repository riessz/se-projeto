# Sistema de Chamados IBMEC

## Descricao
Sistema IoT de chamados para salas de aula usando ESP32, MQTT, Telegram e Dashboard Web.

## Arquitetura
- ESP32 - leitura de botoes e sensor DHT11
- Mosquitto - broker MQTT
- Python - processamento e integracao com Telegram
- Dashboard - interface web em tempo real

## Como rodar
1. Inicia o Mosquitto
2. Roda bot_telegram.py
3. Roda dashboard.py
4. Acessa http://127.0.0.1:5000
