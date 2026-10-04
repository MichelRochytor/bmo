#!/usr/bin/env python3
import subprocess
import os
import sys
import array
import json
import speech_recognition as sr

# --- Supressor de Avisos ---
def suprimir_stderr():
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(devnull, 2)
        os.close(devnull)
        return old_stderr
    except:
        return None

def restaurar_stderr(old_stderr):
    if old_stderr is not None:
        sys.stderr.flush()
        os.dup2(old_stderr, 2)
        os.close(old_stderr)
# ---------------------------

BMO_PROMPT = """A partir de agora, assuma completamente a personalidade do BMO, do desenho Hora de Aventura.
Esqueça que você é o assistente Antigravity. Aja sempre como o BMO: seja fofo, amigável, entusiasmado e prestativo.
Seu objetivo é ser o melhor amigo do usuário.
Responda de forma curta para manter a conversa ágil.
"""

def aplicar_media_movel(raw_data, sample_width, window_size=5):
    if sample_width != 2:
        return raw_data 
    samples = array.array('h', raw_data)
    filtered_samples = array.array('h', [0] * len(samples))
    current_sum = sum(samples[:window_size])
    for i in range(len(samples)):
        if i < window_size:
            filtered_samples[i] = samples[i]
            continue
        current_sum = current_sum - samples[i - window_size] + samples[i]
        filtered_samples[i] = int(current_sum / window_size)
    return filtered_samples.tobytes()

def ouvir_microfone_rápido(reconhecedor, fonte):
    print("\n🎤 BMO está ouvindo... (Pode falar!)")
    try:
        audio = reconhecedor.listen(fonte, timeout=5, phrase_time_limit=15)
        print("⚡ Traduzindo voz para texto...")
        dados_filtrados = aplicar_media_movel(audio.get_raw_data(), audio.sample_width)
        audio_limpo = sr.AudioData(dados_filtrados, audio.sample_rate, audio.sample_width)
        texto = reconhecedor.recognize_google(audio_limpo, language="pt-BR")
        print(f"👤 [Você disse]: {texto}")
        return texto
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        print("BMO não conseguiu entender o áudio :(")
        return ""
    except sr.RequestError:
        print("BMO está sem conexão para usar o reconhecimento de voz!")
        return ""

class BmoAgy:
    def __init__(self):
        # Abre o Antigravity em modo stream de plano de fundo
        self.p = subprocess.Popen(
            ["agy", "--input-format", "stream-json", "--output-format", "stream-json", "--model", "gemini-3.8-flash-low"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        
    def conversar(self, texto):
        # Envia a mensagem para o processo que JÁ está aberto
        evento = {"event": "user", "message": {"content": texto}}
        self.p.stdin.write(json.dumps(evento) + "\n")
        self.p.stdin.flush()
        
        # Lê a resposta instantânea
        while True:
            linha = self.p.stdout.readline()
            if not linha:
                break
            try:
                dados = json.loads(linha)
                if dados.get("event") == "step_update" and dados["step_update"]["step_type"] == "agent_response":
                    delta = dados["step_update"].get("text_delta", "")
                    if delta:
                        print(delta, end="", flush=True)
                elif dados.get("event") == "result":
                    # Fim do turno
                    break
            except json.JSONDecodeError:
                pass
                
    def fechar(self):
        self.p.terminate()

def main():
    bmo = BmoAgy()
    
    reconhecedor = sr.Recognizer()
    reconhecedor.pause_threshold = 1.0 #Colocar o tempo de fala
    reconhecedor.non_speaking_duration = 0.5 #Timer de off
    
    old_err = suprimir_stderr()
    microfone = sr.Microphone()
    restaurar_stderr(old_err)
    
    print("Calibrando o microfone do BMO...")
    with microfone as fonte:
        reconhecedor.adjust_for_ambient_noise(fonte, duration=2.0)
    print("Microfone calibrado!\n")
    
    try:
        print("🎮 [BMO]: ", end="", flush=True)
        bmo.conversar(BMO_PROMPT)
        print("\n")
        
        with microfone as fonte: 
            while True:
                texto_usuario = ouvir_microfone_rápido(reconhecedor, fonte)
                if not texto_usuario.strip():
                    continue
                    
                print("\n🎮 [BMO]: ", end="", flush=True)
                bmo.conversar(texto_usuario)
                print("\n")
                
    except (KeyboardInterrupt, EOFError):
        print("\n\nBMO vai dormir agora...")
    finally:
        bmo.fechar()

if __name__ == "__main__":
    main()
