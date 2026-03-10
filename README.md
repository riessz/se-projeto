# Sistema Embarcado de Chamado e Localização de Suporte Acadêmico

## Integrantes

* Pedro Macedo
* Arthur Riess
* Yago Carvalho
* João Victor

Disciplina: **Sistemas Embarcados e Internet das Coisas**
Instituição: **IBMEC**

---

# Descrição do Projeto

O projeto **Sistema Embarcado de Chamado e Localização de Suporte Acadêmico** consiste em uma solução baseada em Internet das Coisas (IoT) que permite que professores solicitem assistência técnica de forma rápida e eficiente durante as aulas.

Cada sala de aula possui um botão conectado a um microcontrolador **ESP32**. Quando o botão é pressionado, o sistema envia automaticamente um chamado via rede Wi-Fi para um servidor central, que identifica o funcionário mais próximo disponível para atender à solicitação.

O funcionário recebe a notificação diretamente em seu celular, podendo assumir o chamado ou informar que está ocupado.

---

# Problema

Durante as aulas, professores podem enfrentar problemas técnicos que dificultam a continuidade da aula, como:

* falha no computador
* problemas no projetor
* falta de material (piloto ou apagador)
* dificuldades técnicas em equipamentos

Normalmente, resolver esses problemas exige interromper a aula para buscar ajuda.

---

# Solução Proposta

O sistema propõe a instalação de um **botão inteligente em cada sala de aula**.

Quando pressionado:

1. O ESP32 detecta o acionamento do botão.
2. O dispositivo envia um chamado através da rede Wi-Fi.
3. Um servidor recebe o chamado e processa a solicitação.
4. O sistema identifica o funcionário mais próximo disponível.
5. O funcionário recebe uma notificação em seu celular.

---

# Arquitetura do Sistema

Professor
↓
Botão na sala
↓
ESP32
↓ Wi-Fi
Servidor
↓
Telegram Bot
↓
Celular do Funcionário

---

# Lógica de Encaminhamento

O sistema utiliza uma lógica de prioridade baseada no andar onde o chamado foi realizado.

Chamado no **1º andar**

1º andar → 2º andar → 3º andar

Chamado no **2º andar**

2º andar → 3º andar → 1º andar

Chamado no **3º andar**

3º andar → 2º andar → 1º andar

Caso o funcionário esteja ocupado ou não responda dentro do tempo limite, o sistema encaminha automaticamente o chamado para o próximo funcionário disponível.

---

# Tecnologias Utilizadas

* ESP32
* Arduino IDE
* Python
* Flask
* Telegram Bot API
* Wi-Fi
* GitHub

---

# Demonstração

A demonstração do funcionamento do sistema pode ser encontrada na pasta:

video/demonstracao.mp4

---

# Escalabilidade

O sistema pode ser expandido para:

* múltiplas salas de aula
* múltiplos funcionários por andar
* dashboards de monitoramento
* análise de tempo médio de atendimento
* sistemas de localização indoor

---

# Melhorias Futuras

* utilização de **BLE Beacons para localização indoor**
* aplicativo próprio para funcionários
* painel administrativo em tempo real
* relatórios automáticos de chamados
