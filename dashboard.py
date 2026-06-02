from flask import Flask, render_template, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import threading
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__, template_folder=r"C:\Users\pedri\Projeto Terça Ibmec")
app.config['SECRET_KEY'] = 'ibmec2026'
socketio = SocketIO(app, cors_allowed_origins="*")

BROKER = "172.20.10.2"
PORT = 1883
TEMP_MIN = 20
TEMP_MAX = 24

EMAIL_REMETENTE = "pedrinho.maraujo@gmail.com"
EMAIL_SENHA     = "pfjxrdnehyskrdzv"
EMAIL_DESTINO   = "pedro@cafemataalta.com"

estado = {
    "salas": {
        "sala101": {
            "nome": "Sala 101",
            "temperatura": "--",
            "umidade": "--",
            "status": "normal",
            "chamado_ativo": False,
            "tipo_chamado": "",
            "ultimo_chamado": "--",
            "situacao": "--",
            "funcionario_atual": "--",
            "tempo_atendimento": "--",
            "situacao_expira": None
        }
    },
    "pendentes": [],
    "historico": [],
    "estatisticas": {
        "total_chamados": 0,
        "resolvidos": 0,
        "nao_resolvidos": 0,
        "escalados": 0,
        "sem_atendimento": 0
    }
}

_indice_chamado_ativo = None
_tempo_inicio_chamado = None

# ================= EMAIL =================
def enviar_email_pendencia(sala, tipo, motivo, funcionario, hora, tempo_atendimento):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[IBMEC] Chamado Pendente — {sala}"
        msg["From"]    = EMAIL_REMETENTE
        msg["To"]      = EMAIL_DESTINO

        corpo = f"""
        <html><body style="font-family:sans-serif;color:#222;padding:24px">
          <h2 style="color:#e05454">Chamado Pendente — {sala}</h2>
          <table style="border-collapse:collapse;width:100%;max-width:500px">
            <tr><td style="padding:8px;color:#666;width:140px">Sala</td><td style="padding:8px"><b>{sala}</b></td></tr>
            <tr><td style="padding:8px;color:#666">Tipo</td><td style="padding:8px">{tipo}</td></tr>
            <tr><td style="padding:8px;color:#666">Funcionário</td><td style="padding:8px">{funcionario}</td></tr>
            <tr><td style="padding:8px;color:#666">Horário</td><td style="padding:8px">{hora}</td></tr>
            <tr><td style="padding:8px;color:#666">Duração</td><td style="padding:8px">{tempo_atendimento}</td></tr>
            <tr><td style="padding:8px;color:#666;vertical-align:top">Descrição</td>
                <td style="padding:8px;background:#fff3f3;border-left:3px solid #e05454">{motivo}</td></tr>
          </table>
          <p style="margin-top:24px;color:#999;font-size:12px">Sistema de Chamados IBMEC — Dashboard automático</p>
        </body></html>
        """

        msg.attach(MIMEText(corpo, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, msg.as_string())

        print(f"Email enviado para {EMAIL_DESTINO}")
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

# ================= ROTAS =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/estado')
def get_estado():
    return json.dumps(estado)

@app.route('/api/historico')
def get_historico():
    return json.dumps(estado["historico"])

@app.route('/api/pendentes')
def get_pendentes():
    return json.dumps(estado["pendentes"])

@app.route('/api/estatisticas')
def get_estatisticas():
    return json.dumps(estado["estatisticas"])

@app.route('/api/reenviar_email', methods=['POST'])
def reenviar_email_route():
    p = request.get_json()
    threading.Thread(
        target=enviar_email_pendencia,
        args=(p.get('sala','--'), p.get('tipo','--'), p.get('motivo','--'),
              p.get('funcionario','--'), p.get('hora','--'), p.get('tempo_atendimento','--')),
        daemon=True
    ).start()
    return json.dumps({"ok": True})

# ================= MQTT =================
def on_connect(client, userdata, flags, reason_code, properties):
    print("Dashboard conectado ao Mosquitto!")
    client.subscribe("ibmec/sala101/#")

def on_message(client, userdata, msg):
    global _indice_chamado_ativo, _tempo_inicio_chamado

    topico = msg.topic
    payload = msg.payload.decode()

    if topico == "ibmec/sala101/temperatura":
        try:
            partes = payload.split(",")
            t = float(partes[0])
            u = float(partes[1])
            estado["salas"]["sala101"]["temperatura"] = f"{t:.1f}"
            estado["salas"]["sala101"]["umidade"] = f"{u:.1f}"
            st = "normal" if TEMP_MIN <= t <= TEMP_MAX else "alerta"
            estado["salas"]["sala101"]["status"] = st
            socketio.emit('atualizar', estado)
        except:
            pass

    elif topico == "ibmec/sala101/chamado":
        tipos = {"ar": "Ar Condicionado", "material": "Material", "presenca": "Presenca"}
        tipo = tipos.get(payload, payload)
        agora = datetime.now().strftime("%d/%m %H:%M")

        estado["salas"]["sala101"].update({
            "chamado_ativo": True,
            "tipo_chamado": tipo,
            "ultimo_chamado": agora,
            "situacao": "Aguardando aceite",
            "funcionario_atual": "Funcionario 1",
            "tempo_atendimento": "--",
            "situacao_expira": None
        })

        novo_registro = {
            "id": len(estado["historico"]) + 1,
            "sala": "Sala 101",
            "tipo": tipo,
            "hora_abertura": agora,
            "hora_fechamento": "--",
            "situacao": "Aguardando aceite",
            "funcionario": "Funcionario 1",
            "tempo_atendimento": "--",
            "motivo_falha": "--"
        }
        estado["historico"].insert(0, novo_registro)
        _indice_chamado_ativo = 0
        _tempo_inicio_chamado = datetime.now()
        estado["estatisticas"]["total_chamados"] += 1

        if len(estado["historico"]) > 50:
            estado["historico"].pop()

        socketio.emit('atualizar', estado)

    elif topico == "ibmec/sala101/status":
        partes = payload.split("|")
        evento = partes[0]
        agora = datetime.now().strftime("%d/%m %H:%M")

        reg = None
        if _indice_chamado_ativo is not None and _indice_chamado_ativo < len(estado["historico"]):
            reg = estado["historico"][_indice_chamado_ativo]

        if evento == "aceito":
            func_nome = partes[1] if len(partes) > 1 else "Funcionario 1"
            if reg:
                reg["situacao"] = "Em atendimento"
                reg["funcionario"] = func_nome
            estado["salas"]["sala101"]["situacao"] = "Em atendimento"
            estado["salas"]["sala101"]["funcionario_atual"] = func_nome
            estado["salas"]["sala101"]["situacao_expira"] = None

        elif evento == "resolvido":
            tempo_str = partes[1] if len(partes) > 1 else "--"
            if reg:
                reg["situacao"] = "Resolvido"
                reg["hora_fechamento"] = agora
                reg["tempo_atendimento"] = tempo_str
            estado["salas"]["sala101"].update({
                "situacao": "Resolvido",
                "chamado_ativo": False,
                "tipo_chamado": "",
                "funcionario_atual": "--",
                "tempo_atendimento": tempo_str,
                "situacao_expira": datetime.now().timestamp() + 30
            })
            estado["estatisticas"]["resolvidos"] += 1
            _indice_chamado_ativo = None
            _tempo_inicio_chamado = None

        elif evento == "nao_resolvido":
            motivo = partes[1] if len(partes) > 1 else "--"
            tempo_str = partes[2] if len(partes) > 2 else "--"
            if reg:
                reg["situacao"] = "Nao resolvido"
                reg["hora_fechamento"] = agora
                reg["tempo_atendimento"] = tempo_str
                reg["motivo_falha"] = motivo

            pendente = {
                "sala": "Sala 101",
                "tipo": reg["tipo"] if reg else "--",
                "hora": agora,
                "motivo": motivo,
                "funcionario": reg["funcionario"] if reg else "--",
                "tempo_atendimento": tempo_str,
                "prioridade": "alta"
            }
            estado["pendentes"].insert(0, pendente)

            estado["salas"]["sala101"].update({
                "situacao": "Nao resolvido",
                "chamado_ativo": False,
                "tipo_chamado": "",
                "funcionario_atual": "--",
                "tempo_atendimento": tempo_str,
                "situacao_expira": datetime.now().timestamp() + 30
            })
            estado["estatisticas"]["nao_resolvidos"] += 1
            _indice_chamado_ativo = None
            _tempo_inicio_chamado = None

            threading.Thread(
                target=enviar_email_pendencia,
                args=("Sala 101", reg["tipo"] if reg else "--", motivo,
                      reg["funcionario"] if reg else "--", agora, tempo_str),
                daemon=True
            ).start()

        elif evento == "escalado":
            func_nome = partes[1] if len(partes) > 1 else "Proximo funcionario"
            if reg:
                reg["situacao"] = f"Escalado para {func_nome}"
                reg["funcionario"] = func_nome
            estado["salas"]["sala101"]["situacao"] = f"Escalado para {func_nome}"
            estado["salas"]["sala101"]["funcionario_atual"] = func_nome
            estado["salas"]["sala101"]["situacao_expira"] = None
            estado["estatisticas"]["escalados"] += 1

        elif evento == "sem_atendimento":
            if reg:
                reg["situacao"] = "Sem atendimento"
                reg["hora_fechamento"] = agora

            pendente = {
                "sala": "Sala 101",
                "tipo": reg["tipo"] if reg else "--",
                "hora": agora,
                "motivo": "Nenhum funcionario disponivel",
                "funcionario": "--",
                "tempo_atendimento": "--",
                "prioridade": "alta"
            }
            estado["pendentes"].insert(0, pendente)

            estado["salas"]["sala101"].update({
                "situacao": "Sem atendimento",
                "chamado_ativo": False,
                "tipo_chamado": "",
                "funcionario_atual": "--",
                "situacao_expira": datetime.now().timestamp() + 30
            })
            estado["estatisticas"]["sem_atendimento"] += 1
            _indice_chamado_ativo = None
            _tempo_inicio_chamado = None

            threading.Thread(
                target=enviar_email_pendencia,
                args=("Sala 101", reg["tipo"] if reg else "--",
                      "Nenhum funcionario disponivel", "--", agora, "--"),
                daemon=True
            ).start()

        socketio.emit('atualizar', estado)

def limpar_situacoes_expiradas():
    while True:
        threading.Event().wait(5)
        agora = datetime.now().timestamp()
        for sala in estado["salas"].values():
            exp = sala.get("situacao_expira")
            if exp and agora >= exp:
                sala["situacao"] = "--"
                sala["situacao_expira"] = None
                sala["funcionario_atual"] = "--"
                socketio.emit('atualizar', estado)

def atualizar_tempo_espera():
    while True:
        threading.Event().wait(30)
        if _tempo_inicio_chamado and estado["salas"]["sala101"]["chamado_ativo"]:
            delta = datetime.now() - _tempo_inicio_chamado
            minutos = int(delta.total_seconds() // 60)
            segundos = int(delta.total_seconds() % 60)
            estado["salas"]["sala101"]["tempo_atendimento"] = f"{minutos}min {segundos}s"
            socketio.emit('atualizar', estado)

def iniciar_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

# ================= MAIN =================
if __name__ == '__main__':
    threading.Thread(target=iniciar_mqtt, daemon=True).start()
    threading.Thread(target=atualizar_tempo_espera, daemon=True).start()
    threading.Thread(target=limpar_situacoes_expiradas, daemon=True).start()
    print("Dashboard rodando em http://127.0.0.1:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)