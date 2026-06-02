# Sistema de Chamados IBMEC

Projeto desenvolvido para a disciplina de Sistemas Embarcados e Internet das Coisas — IBMEC 2026.1.

**Alunos:** Arthur Riess, Yago Carvalho, Pedro Macedo e João Victor

---

## Descrição

Sistema IoT que permite a professores solicitar suporte técnico diretamente da sala de aula através de botões físicos. Os chamados são enviados via MQTT para um servidor local, processados por um script Python e encaminhados ao funcionário responsável pelo Telegram, com acompanhamento em tempo real por um dashboard web.

---

## Arquitetura

ESP32 (botões + DHT11)
        |
   Mosquitto (broker MQTT)
        |
   Python (bot_telegram.py)
        |
   Telegram (funcionário)
        |
   Dashboard Web (tempo real)

---

## Funcionalidades

- 3 tipos de chamado: Ar Condicionado, Material e Presença
- Envio de temperatura e umidade junto ao chamado de ar
- Escalonamento automático entre funcionários com timeout de 1min30
- Botões de resposta inline no Telegram
- Relatório automático de temperatura a cada hora
- Dashboard web com histórico, pendências e estatísticas
- Envio automático de email para chamados não resolvidos

---

## Estrutura do Projeto

├── bot_telegram.py        # Integração Telegram + lógica de escalonamento
├── dashboard.py           # Servidor Flask + WebSocket
├── templates/
│   └── index.html         # Interface do dashboard
└── README.md

---

## Requisitos

Python:
pip install paho-mqtt requests flask flask-socketio

Arduino IDE:
- PubSubClient (Nick O'Leary)
- DHT sensor library (Adafruit)
- Adafruit Unified Sensor

Broker:
- Mosquitto 2.x instalado localmente

---

## Como rodar

1. Mosquitto (PowerShell como Administrador)
net stop mosquitto
& "C:\Program Files\mosquitto\mosquitto.exe" -c "C:\Program Files\mosquitto\mosquitto.conf" -v

2. Bot Telegram
python bot_telegram.py

3. Dashboard
python dashboard.py

4. Acessar o dashboard
http://127.0.0.1:5000

5. Upload do firmware no ESP32 via Arduino IDE

---

## Topicos MQTT

Topico                      | Payload              | Descricao
ibmec/sala101/chamado       | ar, material, presenca | Tipo do chamado acionado
ibmec/sala101/temperatura   | 24.5,65.0            | Temperatura e umidade
ibmec/sala101/status        | aceito, resolvido... | Status do atendimento

---

## Faixa de Temperatura Normal

- Minima: 20C
- Maxima: 24C
- Fora dessa faixa: alerta visual no dashboard e no relatorio

---

## Tecnologias

- ESP32 / Arduino IDE
- Python 3.x / Flask / Flask-SocketIO
- Paho MQTT / Mosquitto
- Telegram Bot API
- HTML / CSS / JavaScript
