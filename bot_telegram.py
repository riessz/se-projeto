import paho.mqtt.client as mqtt
import requests
import time
import threading

# ================= CONFIGURAÇÕES =================
BOT_TOKEN = "8778133783:AAFPF9ZeKk8m5QbLu6ULmQd88ab3EWmG42Q"
GRUPO_ANDAR1 = "-5240414153"
BROKER = "172.20.10.2"
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

# Controle do fluxo de 2 etapas por funcionário
# Estados: "aguardando_aceite" | "aguardando_conclusao" | "aguardando_motivo"
estado_funcionario = {}
tempo_aceite = {}
message_id_conclusao = {}

FUNCIONARIOS = [
    "5256289575",
    "CHAT_ID_FUNC2",
    "CHAT_ID_FUNC3"
]

mqtt_client = None

# ================= TELEGRAM =================
def enviar_telegram(chat_id, mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return None

def enviar_com_botoes(chat_id, mensagem, botoes):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": botoes}
    }
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return None

def responder_callback(callback_query_id, texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_query_id, "text": texto})
    except Exception as e:
        print(f"Erro callback: {e}")

def editar_mensagem(chat_id, message_id, novo_texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": novo_texto,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": []}
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro editar mensagem: {e}")

def enviar_chamado(func_index, tipo, mensagem):
    global chamado_ativo, func_atual, tipo_chamado, tempo_envio, message_id_chamado
    botoes_aceite = [[
        {"text": "✅ Vou atender", "callback_data": "aceitar"},
        {"text": "❌ Não posso atender", "callback_data": "recusar"}
    ]]
    r = enviar_com_botoes(FUNCIONARIOS[func_index], mensagem, botoes_aceite)
    if r and r.get("ok"):
        message_id_chamado = r["result"]["message_id"]
        chamado_ativo = True
        func_atual = func_index
        tipo_chamado = tipo
        tempo_envio = time.time()
        estado_funcionario[FUNCIONARIOS[func_index]] = "aguardando_aceite"
        print(f"Chamado enviado para funcionário {func_index + 1}")

def limpar_estado_funcionario(chat_id):
    estado_funcionario.pop(chat_id, None)
    tempo_aceite.pop(chat_id, None)
    message_id_conclusao.pop(chat_id, None)

def escalar_proximo(motivo):
    """Só é chamado quando funcionário RECUSOU ou deu TIMEOUT — nunca quando não conseguiu concluir."""
    global chamado_ativo, func_atual
    chat_atual = FUNCIONARIOS[func_atual]
    limpar_estado_funcionario(chat_atual)

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
        publicar_status(f"escalado|Funcionário {proximo + 1}")
        enviar_chamado(proximo, tipo_chamado, msg)
    else:
        for f in FUNCIONARIOS:
            enviar_telegram(f, "⚠️ *SALA 101:* Nenhum funcionário disponível para atender. Verificar manualmente.")
        publicar_status("sem_atendimento|--")
        chamado_ativo = False
        print("Nenhum funcionário disponível.")

def publicar_status(status):
    if mqtt_client:
        mqtt_client.publish("ibmec/sala101/status", status)
        print(f"Status publicado: {status}")

# ================= RELATÓRIO =================
def relatorio_temperatura():
    while True:
        time.sleep(3600)
        if temperaturas:
            msg = "📊 *Relatório de Temperatura — Andar 1*\n\n"
            for sala, (t, u) in temperaturas.items():
                st = "✅" if TEMP_MIN <= t <= TEMP_MAX else "⚠️ FORA DO PADRÃO"
                msg += f"🏫 Sala 101: {t:.1f}°C | {u:.1f}% umidade {st}\n"
            enviar_telegram(GRUPO_ANDAR1, msg)
            print("Relatório enviado.")

# ================= VERIFICAR RESPOSTAS =================
def verificar_respostas():
    global chamado_ativo
    ultimo_update = 0

    while True:
        time.sleep(1)

        if not chamado_ativo:
            continue

        chat_func = FUNCIONARIOS[func_atual]

        # Timeout só se funcionário ainda não aceitou
        if (estado_funcionario.get(chat_func) == "aguardando_aceite"
                and time.time() - tempo_envio > TIMEOUT):
            enviar_telegram(chat_func,
                "⏰ Tempo esgotado. Chamado da *SALA 101* repassado para outro funcionário.")
            if message_id_chamado:
                editar_mensagem(chat_func, message_id_chamado,
                    "⏰ *Chamado expirado — repassado para outro funcionário.*")
            escalar_proximo("timeout")
            continue

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={ultimo_update + 1}&timeout=5"
        try:
            r = requests.get(url, timeout=10).json()
            for update in r.get("result", []):
                ultimo_update = update["update_id"]

                # ===== CALLBACK (botões inline) =====
                if "callback_query" in update:
                    cb = update["callback_query"]
                    chat_id = str(cb["message"]["chat"]["id"])
                    data = cb["data"]
                    callback_id = cb["id"]
                    msg_id = cb["message"]["message_id"]
                    est = estado_funcionario.get(chat_id, "")

                    if chat_id != FUNCIONARIOS[func_atual] or not chamado_ativo:
                        continue

                    # ---- ETAPA 1: aceitar ou recusar ----
                    if est == "aguardando_aceite":
                        if data == "aceitar":
                            responder_callback(callback_id, "✅ Chamado aceito! Dirija-se à sala.")
                            editar_mensagem(chat_id, msg_id,
                                "✅ *Você aceitou o chamado da SALA 101.*\nDirija-se à sala e resolva o problema.")
                            tempo_aceite[chat_id] = time.time()
                            estado_funcionario[chat_id] = "aguardando_conclusao"

                            func_nome = f"Funcionário {func_atual + 1}"
                            enviar_telegram(GRUPO_ANDAR1,
                                f"🔔 *SALA 101:* Chamado aceito por {func_nome}. Indo atender...")
                            publicar_status(f"aceito|{func_nome}")

                            botoes_conclusao = [[
                                {"text": "✅ Problema resolvido", "callback_data": "concluido"},
                                {"text": "❌ Não consegui resolver", "callback_data": "nao_resolvido"}
                            ]]
                            r2 = enviar_com_botoes(chat_id,
                                "Quando terminar, informe o resultado:", botoes_conclusao)
                            if r2 and r2.get("ok"):
                                message_id_conclusao[chat_id] = r2["result"]["message_id"]

                        elif data == "recusar":
                            # ✅ RECUSA → escala para próximo funcionário
                            responder_callback(callback_id, "Ok, repassando para outro.")
                            editar_mensagem(chat_id, msg_id,
                                "❌ *Você recusou o chamado. Repassando para outro funcionário.*")
                            publicar_status(f"escalado|Funcionário {func_atual + 2}")
                            escalar_proximo("recusou")

                    # ---- ETAPA 2: concluiu ou não conseguiu ----
                    elif est == "aguardando_conclusao":
                        inicio = tempo_aceite.get(chat_id, time.time())
                        duracao_seg = int(time.time() - inicio)
                        minutos = duracao_seg // 60
                        segundos = duracao_seg % 60
                        tempo_str = f"{minutos}min {segundos}s"
                        mid_conc = message_id_conclusao.get(chat_id)

                        if data == "concluido":
                            responder_callback(callback_id, "✅ Ótimo trabalho!")
                            if mid_conc:
                                editar_mensagem(chat_id, mid_conc,
                                    f"✅ *Chamado concluído!*\n⏱️ Tempo de atendimento: {tempo_str}")
                            enviar_telegram(GRUPO_ANDAR1,
                                f"✅ *SALA 101:* Problema resolvido por Funcionário {func_atual + 1}.\n⏱️ Tempo: {tempo_str}")
                            publicar_status(f"resolvido|{tempo_str}")
                            limpar_estado_funcionario(chat_id)
                            chamado_ativo = False
                            print(f"Chamado resolvido em {tempo_str}!")

                        elif data == "nao_resolvido":
                            # ✅ NÃO RESOLVIDO → NÃO escala, apenas pede motivo
                            responder_callback(callback_id, "Entendido. Por favor, escreva o motivo.")
                            if mid_conc:
                                editar_mensagem(chat_id, mid_conc,
                                    "❌ *Não conseguiu resolver.*\nDescreva abaixo o motivo para registrarmos:")
                            estado_funcionario[chat_id] = "aguardando_motivo"
                            print(f"Funcionário {func_atual + 1} não resolveu. Aguardando motivo.")

                # ===== MENSAGEM DE TEXTO (motivo) =====
                elif "message" in update:
                    msg_upd = update["message"]
                    chat_id = str(msg_upd["chat"]["id"])
                    texto = msg_upd.get("text", "")
                    est = estado_funcionario.get(chat_id, "")

                    if (chat_id == FUNCIONARIOS[func_atual]
                            and chamado_ativo
                            and est == "aguardando_motivo"
                            and texto):

                        inicio = tempo_aceite.get(chat_id, time.time())
                        duracao_seg = int(time.time() - inicio)
                        minutos = duracao_seg // 60
                        segundos = duracao_seg % 60
                        tempo_str = f"{minutos}min {segundos}s"

                        enviar_telegram(chat_id,
                            f"📝 *Motivo registrado:* _{texto}_\nObrigado por informar!")
                        enviar_telegram(GRUPO_ANDAR1,
                            f"❌ *SALA 101:* Funcionário {func_atual + 1} não conseguiu resolver.\n"
                            f"📝 *Motivo:* {texto}\n⏱️ Tempo: {tempo_str}\n\n"
                            f"⚠️ Chamado pendente — necessita atenção manual.")

                        # ✅ Publica como "nao_resolvido" — dashboard move para topo como pendente
                        publicar_status(f"nao_resolvido|{texto}|{tempo_str}")

                        limpar_estado_funcionario(chat_id)
                        chamado_ativo = False
                        print(f"Chamado encerrado sem resolução. Motivo: {texto}")

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
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)

threading.Thread(target=verificar_respostas, daemon=True).start()
threading.Thread(target=relatorio_temperatura, daemon=True).start()

print("Bot iniciado! Aguardando mensagens MQTT...")
mqtt_client.loop_forever()
