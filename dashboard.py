from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import threading
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ibmec2026'
socketio = SocketIO(app, cors_allowed_origins="*")

BROKER = "192.168.0.30"
PORT = 1883
TEMP_MIN = 20
TEMP_MAX = 24

# ================= ESTADO DO SISTEMA =================
estado = {
    "salas": {
        "sala101": {
            "nome": "Sala 101",
            "temperatura": "--",
            "umidade": "--",
            "status": "normal",
            "chamado_ativo": False,
            "tipo_chamado": "",
            "ultimo_chamado": "--"
        }
    },
    "historico": []
}

# ================= ROTAS =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/estado')
def get_estado():
    return json.dumps(estado)

# ================= MQTT =================
def on_connect(client, userdata, flags, reason_code, properties):
    print("Dashboard conectado ao Mosquitto!")
    client.subscribe("ibmec/sala101/#")

def on_message(client, userdata, msg):
    topico = msg.topic
    payload = msg.payload.decode()

    if topico == "ibmec/sala101/temperatura":
        try:
            partes = payload.split(",")
            t = float(partes[0])
            u = float(partes[1])
            estado["salas"]["sala101"]["temperatura"] = f"{t:.1f}"
            estado["salas"]["sala101"]["umidade"] = f"{u:.1f}"
            status = "normal" if TEMP_MIN <= t <= TEMP_MAX else "alerta"
            estado["salas"]["sala101"]["status"] = status
            socketio.emit('atualizar', estado)
        except:
            pass

    elif topico == "ibmec/sala101/chamado":
        tipos = {"ar": "Ar Condicionado", "material": "Material", "presenca": "Presença"}
        tipo = tipos.get(payload, payload)
        agora = datetime.now().strftime("%d/%m %H:%M")
        estado["salas"]["sala101"]["chamado_ativo"] = True
        estado["salas"]["sala101"]["tipo_chamado"] = tipo
        estado["salas"]["sala101"]["ultimo_chamado"] = agora
        estado["historico"].insert(0, {
            "sala": "Sala 101",
            "tipo": tipo,
            "hora": agora,
            "status": "Aguardando"
        })
        if len(estado["historico"]) > 20:
            estado["historico"].pop()
        socketio.emit('atualizar', estado)

    elif topico == "ibmec/sala101/status":
        estado["salas"]["sala101"]["chamado_ativo"] = False
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
    print("Dashboard rodando em http://127.0.0.1:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)