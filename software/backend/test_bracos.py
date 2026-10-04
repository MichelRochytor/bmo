# Script isolado só pra testar os bracinhos do BMO, sem o bmo.py inteiro.
# Ajuda a descobrir se o problema tá no ESP32/hardware ou no resto do backend.
#
# Uso: troca a PORTA abaixo pela sua (ou passa via variável de ambiente
# BMO_PORTA_SERIAL_BRACOS, do jeito que o bmo.py também usa), roda o
# script, e digita OI ou DANCAR quando ele pedir.

import os
import time
import serial

PORTA = os.environ.get("BMO_PORTA_SERIAL_BRACOS", "COM5")  # <- troca aqui se preferir fixo
BAUD = int(os.environ.get("BMO_BAUD_SERIAL_BRACOS", "115200"))

print(f"Tentando conectar em {PORTA} @ {BAUD} baud...")

try:
    conexao = serial.Serial(PORTA, BAUD, timeout=1)
except Exception as e:
    print(f"❌ Não conseguiu abrir a porta: {e}")
    raise SystemExit(1)

print("✅ Porta aberta. Esperando o ESP32 reiniciar...")
time.sleep(2)  # o ESP32 reinicia sozinho ao abrir a porta serial

print("\nConectado! Digite OI, DANCAR, ou 'sair' pra encerrar.\n")

while True:
    comando = input("Comando: ").strip()
    if comando.lower() == "sair":
        break
    if not comando:
        continue

    conexao.write((comando + "\n").encode("utf-8"))
    print(f"📤 Enviado: {comando}")

    # Mostra qualquer coisa que o ESP32 mandar de volta pela serial
    # (o firmware atual não manda nada de volta, mas ajuda a debugar
    # se você adicionar algum Serial.println() lá no código do ESP32)
    time.sleep(0.3)
    while conexao.in_waiting:
        linha = conexao.readline().decode(errors="ignore").strip()
        if linha:
            print(f"📥 ESP32 disse: {linha}")

conexao.close()
print("Porta fechada. Até mais!")