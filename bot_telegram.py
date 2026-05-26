import paho.mqtt.client as mqtt
import requests
import time
import threading

# ================= CONFIGURAÇÕES =================
BOT_TOKEN = "8778133783:AAFPF9ZeKk8m5QbLu6ULmQd88ab3EWmG42Q"
GRUPO_ANDAR1 = "-5240414153"

BROKER = "192.168.0.30"
PORT = 1883

TEMP_MIN = 20
TEMP_MAX = 24

# ================= VARIÁVEIS =================
temperaturas = {}
chamado_ativo = False
func_atual = 0
tipo_chamado = ""
tempo_envio = 0
TIMEOUT = 90
message_id_chamado = None

FUNCIONARIOS = [
    "5256289575",
    "CHAT_ID_FUNC2",
    "CHAT_ID_FUNC3"
]

# ================= TELEGRAM =================
def enviar_telegram(chat_id, mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return None

def enviar_com_botoes(chat_id, mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Consegui resolver", "callback_data": "sim"},
                    {"text": "❌ Não consigo resolver", "callback_data": "nao"}
                ]
            ]
        }
    }
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return None

def responder_callback(callback_query_id, texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": texto
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro callback: {e}")

def editar_mensagem(chat_id, message_id, novo_texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": novo_texto,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro editar mensagem: {e}")

def enviar_chamado(func_index, tipo, mensagem):
    global chamado_ativo, func_atual, tipo_chamado, tempo_envio, message_id_chamado
    r = enviar_com_botoes(FUNCIONARIOS[func_index], mensagem)
    if r and r.get("ok"):
        message_id_chamado = r["result"]["message_id"]
    chamado_ativo = True
    func_atual = func_index
    tipo_chamado = tipo
    tempo_envio = time.time()
    print(f"Chamado enviado para funcionário {func_index + 1}")

def escalar_proximo(motivo):
    global chamado_ativo, func_atual
    proximo = func_atual + 1
    if proximo < len(FUNCIONARIOS):
        print(f"Escalando para funcionário {proximo + 1} — {motivo}")
        if tipo_chamado == "ar":
            msg = "❄️ *SALA 101:* Preciso regular a temperatura do Ar Condicionado."
            if "sala101" in temperaturas:
                t, u = temperaturas["sala101"]
                msg += f"\n🌡️ Temperatura: {t:.1f}°C\n💧 Umidade: {u:.1f}%"
        elif tipo_chamado == "material":
            msg = "🖊️ *SALA 101:* Preciso de material (Piloto/Apagador)."
        else:
            msg = "🙋 *SALA 101:* Necessito da sua presença na sala."
        enviar_chamado(proximo, tipo_chamado, msg)
    else:
        for f in FUNCIONARIOS:
            enviar_telegram(f, "⚠️ *SALA 101:* Nenhum funcionário conseguiu atender. Verificar manualmente.")
        chamado_ativo = False
        print("Nenhum funcionário disponível.")

# ================= RELATÓRIO =================
def relatorio_temperatura():
    while True:
        time.sleep(3600)
        if temperaturas:
            msg = "📊 *Relatório de Temperatura — Andar 1*\n\n"
            for sala, (t, u) in temperaturas.items():
                status = "✅" if TEMP_MIN <= t <= TEMP_MAX else "⚠️ FORA DO PADRÃO"
                msg += f"🏫 Sala 101: {t:.1f}°C | {u:.1f}% umidade {status}\n"
            enviar_telegram(GRUPO_ANDAR1, msg)
            print("Relatório enviado.")

# ================= VERIFICAR RESPOSTAS =================
def verificar_respostas():
    global chamado_ativo
    ultimo_update = 0
    while True:
        time.sleep(2)
        if not chamado_ativo:
            continue

        # Verifica timeout
        if time.time() - tempo_envio > TIMEOUT:
            enviar_telegram(FUNCIONARIOS[func_atual], "⏰ Tempo esgotado. Chamado da *SALA 101* repassado para outro funcionário.")
            if message_id_chamado:
                editar_mensagem(FUNCIONARIOS[func_atual], message_id_chamado, "⏰ *Chamado expirado — repassado para outro funcionário.*")
            escalar_proximo("timeout")
            continue

        # Verifica respostas e callbacks
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={ultimo_update + 1}"
        try:
            r = requests.get(url).json()
            for update in r.get("result", []):
                ultimo_update = update["update_id"]

                # Verifica botões inline (callback_query)
                if "callback_query" in update:
                    cb = update["callback_query"]
                    chat_id = str(cb["message"]["chat"]["id"])
                    data = cb["data"]
                    callback_id = cb["id"]
                    msg_id = cb["message"]["message_id"]

                    if chat_id == FUNCIONARIOS[func_atual] and chamado_ativo:
                        if data == "sim":
                            responder_callback(callback_id, "✅ Chamado confirmado!")
                            editar_mensagem(chat_id, msg_id, "✅ *Chamado da SALA 101 resolvido por você. Obrigado!*")
                            enviar_telegram(GRUPO_ANDAR1, "✅ *SALA 101:* Chamado resolvido pelo funcionário.")
                            chamado_ativo = False
                            print("Chamado resolvido!")
                        elif data == "nao":
                            responder_callback(callback_id, "Ok, escalando para outro funcionário.")
                            editar_mensagem(chat_id, msg_id, "❌ *Você recusou o chamado. Repassando para outro funcionário.*")
                            escalar_proximo("recusou")

        except Exception as e:
            print(f"Erro ao verificar respostas: {e}")

# ================= MQTT =================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Conectado ao Mosquitto!")
        client.subscribe("ibmec/sala101/#")
    else:
        print(f"Erro de conexão: {reason_code}")

def on_message(client, userdata, msg):
    global chamado_ativo
    topico = msg.topic
    payload = msg.payload.decode()
    print(f"Recebido: {topico} = {payload}")

    if topico == "ibmec/sala101/temperatura":
        try:
            partes = payload.split(",")
            t = float(partes[0])
            u = float(partes[1])
            temperaturas["sala101"] = (t, u)
            print(f"Temperatura: {t}°C | Umidade: {u}%")
        except:
            print("Erro ao processar temperatura")

    elif topico == "ibmec/sala101/chamado" and not chamado_ativo:
        if payload == "ar":
            msg_text = "❄️ *SALA 101:* Preciso regular a temperatura do Ar Condicionado."
            if "sala101" in temperaturas:
                t, u = temperaturas["sala101"]
                msg_text += f"\n🌡️ Temperatura: {t:.1f}°C\n💧 Umidade: {u:.1f}%"
            enviar_chamado(0, "ar", msg_text)
            enviar_telegram(GRUPO_ANDAR1, msg_text + "\n\n🔔 Chamado enviado ao funcionário.")
        elif payload == "material":
            msg_text = "🖊️ *SALA 101:* Preciso de material (Piloto/Apagador)."
            enviar_chamado(0, "material", msg_text)
            enviar_telegram(GRUPO_ANDAR1, msg_text + "\n\n🔔 Chamado enviado ao funcionário.")
        elif payload == "presenca":
            msg_text = "🙋 *SALA 101:* Necessito da sua presença na sala."
            enviar_chamado(0, "presenca", msg_text)
            enviar_telegram(GRUPO_ANDAR1, msg_text + "\n\n🔔 Chamado enviado ao funcionário.")

# ================= MAIN =================
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

threading.Thread(target=verificar_respostas, daemon=True).start()
threading.Thread(target=relatorio_temperatura, daemon=True).start()

print("Bot iniciado! Aguardando mensagens MQTT...")
client.loop_forever()