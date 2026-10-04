/*
  Controle dos bracinhos do BMO (Artbot) — ESP32
  ------------------------------------------------
  Recebe comandos por Serial vindos do backend em Python (bmo.py) e move
  dois servos, um em cada braço.

  Comandos aceitos (uma linha de texto terminada em '\n'):
    OI      -> aceno de cumprimento (só o braço direito)
    DANCAR  -> coreografia (os dois bracinhos alternando, 3x)

  Biblioteca necessária:
    ESP32Servo (Gerenciador de Bibliotecas do Arduino IDE > buscar "ESP32Servo")
    A lib "Servo" padrão do Arduino não funciona direito no ESP32 (usa
    timers diferentes), por isso o ESP32Servo é obrigatório aqui.
*/

#include <ESP32Servo.h>

// --- Pinos ---
// Atenção: no ESP32-WROOM, os GPIOs 6-11 costumam estar reservados pra
// memória flash interna e não ficam expostos nos dev kits comuns. Se o
// braço direito não se mexer, tenta trocar PINO_BRACO_DIREITO por um GPIO
// livre (ex: 27) antes de desconfiar do código ou do servo.
const int PINO_BRACO_DIREITO = 12;
const int PINO_BRACO_ESQUERDO = 13;

Servo bracoDireito;
Servo bracoEsquerdo;

void posicaoInicial();
void saudar();
void dancar();
void aura();

// --- Posições, em graus (0-180) ---
const int POSICAO_INICIAL_ESQUERDA = 180;   // centro, os dois bracinhos "descansando"
const int POSICAO_INICIAL_DIREITA = 0;
const int ANGULO_SAUDACAO = 150;    // quanto o braço direito sobe ao acenar
const int ANGULO_DANCA = 150;      
const int ANGULO_AURA = 60;
// ANGULO_DANCA = 90 leva os servos até os extremos (0° e 180°). Se o braço
// forçar ou travar perto do fim do curso, é só baixar esse valor (ex: 80).

// --- Tempos (ms) ---
const int TEMPO_MOVIMENTO = 300;       // tempo pro servo físico chegar na posição
const int TEMPO_PAUSA_SAUDACAO = 500;  // quanto tempo o braço fica levantado ao acenar
const int TEMPO_PAUSA_DANCA = 500;     
const int TEMPO_REPETICAO_AURA = 200; 

const int REPETICOES_DANCA = 6;
const int REPETICOES_AURA = 10;

void setup() {
  Serial.begin(115200);

  // ESP32Servo precisa que os timers de PWM sejam alocados manualmente
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);

  bracoDireito.setPeriodHertz(50);
  bracoEsquerdo.setPeriodHertz(50);
  bracoDireito.attach(PINO_BRACO_DIREITO, 500, 2400);
  bracoEsquerdo.attach(PINO_BRACO_ESQUERDO, 500, 2400);

  posicaoInicial();
}

void loop() {
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    comando.toUpperCase();

    if (comando == "OI") {
      saudar();
    } else if (comando == "DANCAR") {
      dancar();
      bracoDireito.write(POSICAO_INICIAL_DIREITA);
    } else if (comando == "AURA") {
      aura();
      bracoDireito.write(POSICAO_INICIAL_DIREITA); // braço que termina para cima
    }
  }
    // qualquer outro texto chegando pelo cabo é ignorado — evita travar o
    // loop se vier lixo (ruído, comando de outra versão do bmo.py, etc.)
    bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA);
}

void posicaoInicial() {
  bracoDireito.write(POSICAO_INICIAL_DIREITA);
  bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA);
}

// Aceno: braço esquerdo sobe alguns graus e volta.
void saudar() {
  bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA - ANGULO_SAUDACAO);
  delay(TEMPO_MOVIMENTO + TEMPO_PAUSA_SAUDACAO);
  bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA);
  delay(TEMPO_MOVIMENTO);
}

// Dança: os bracinhos sempre em direções opostas (um sobe enquanto o outro
// desce). Repete REPETICOES_DANCA vezes e volta pro centro no final.

// O calculo de gasto de tempo é (2 * (TEMPO_MOVIMENTO + TEMPO_PAUSA_DANCA)) * REPETICOES_DANCA
void dancar() {
  for (int i = 0; i < REPETICOES_DANCA; i++) {
    // Fase A: esquerdo sobe, direito sobe também (mas precisa do sinal invertido
    // porque o servo dele tá montado espelhado)
    bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA - ANGULO_DANCA);
    bracoDireito.write((POSICAO_INICIAL_DIREITA) - ANGULO_DANCA);
    delay(TEMPO_MOVIMENTO + TEMPO_PAUSA_DANCA);

    // Fase B: inverte os dois
    bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA + ANGULO_DANCA);
    bracoDireito.write((POSICAO_INICIAL_DIREITA) + ANGULO_DANCA);
    delay(TEMPO_MOVIMENTO + TEMPO_PAUSA_DANCA);
  }
  posicaoInicial();
  delay(TEMPO_MOVIMENTO);
}

void aura() {
  for (int i = 0; i < REPETICOES_DANCA; i++) {
    // Fase A: esquerdo sobe, direito sobe também (mas precisa do sinal invertido
    // porque o servo dele tá montado espelhado)
    bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA - ANGULO_AURA);
    bracoDireito.write((POSICAO_INICIAL_DIREITA) - ANGULO_AURA);
    delay(TEMPO_REPETICAO_AURA);

    // Fase B: inverte os dois
    bracoEsquerdo.write(POSICAO_INICIAL_ESQUERDA + ANGULO_AURA);
    bracoDireito.write((POSICAO_INICIAL_DIREITA) + ANGULO_AURA);
    delay(TEMPO_REPETICAO_AURA);
  }
  posicaoInicial();
  delay(TEMPO_MOVIMENTO);
}