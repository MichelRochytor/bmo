# Dependências (requirements.txt sugerido):
#   SpeechRecognition, groq, python-dotenv, piper-tts, numpy
#
# Arquivos da voz (em vozes/, ao lado deste script):
#   dii_pt-BR.onnx
#   dii_pt-BR.onnx.json   <- config da voz; o Piper acha sozinho pelo nome

import speech_recognition as sr
import wave
import io
import os
import re
import time
import math
import uuid
import json
import subprocess
import platform
import unicodedata
import numpy as np
from collections import Counter, deque
from datetime import datetime, timezone
from difflib import SequenceMatcher
from groq import Groq
from dotenv import load_dotenv
import shutil
import serial

# ============================================
# INICIALIZAÇÃO
# ============================================

recognizer = sr.Recognizer()
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
cliente_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APLAY_DISPONIVEL = platform.system() == "Linux" and shutil.which("aplay") is not None



def caminho(arquivo):
    return os.path.join(BASE_DIR, arquivo)


# ============================================
# COMUNICAÇÃO COM O ESP32 DOS BRAÇOS (serial)
# ============================================


PORTA_SERIAL_BRACOS = os.environ.get("BMO_PORTA_SERIAL_BRACOS", "COM5")
BAUD_SERIAL_BRACOS = int(os.environ.get("BMO_BAUD_SERIAL_BRACOS", "115200"))


def _conectar_serial_bracos():
    try:
        conexao = serial.Serial(PORTA_SERIAL_BRACOS, BAUD_SERIAL_BRACOS, timeout=1)
        time.sleep(2)  # o ESP32 reinicia sozinho ao abrir a porta — dá tempo dele acordar
        return conexao
    except Exception as e:
        print(f"⚠️ Não foi possível conectar com o ESP32 dos braços em {PORTA_SERIAL_BRACOS}: {e}")
        print("   Os bracinhos ficam desativados até a conexão ser resolvida (o resto do BMO continua normal).")
        return None


CONEXAO_BRACOS = _conectar_serial_bracos()


def enviar_comando_bracos(comando):
    """Manda um comando de texto pro ESP32. Uma falha aqui nunca deve travar a conversa."""
    if CONEXAO_BRACOS is None:
        return False
    try:
        CONEXAO_BRACOS.write((comando.strip() + "\n").encode("utf-8"))
        return True
    except Exception as e:
        print(f"⚠️ Erro ao mandar comando '{comando}' pro ESP32 dos braços: {e}")
        return False

# ============================================
# CONFIGURAÇÕES GERAIS
# (a maioria pode ser sobrescrita via .env, sem mexer no código)
# ============================================

# --- Áudio / microfone ---
PAUSA_APOS_FALAR = float(os.environ.get("BMO_PAUSA_APOS_FALAR", "0.35"))
TIMEOUT_ESCUTA = float(os.environ.get("BMO_TIMEOUT_ESCUTA", "6"))
PHRASE_TIME_LIMIT = float(os.environ.get("BMO_LIMITE_FALA", "10"))
DURACAO_AJUSTE_RUIDO = float(os.environ.get("BMO_DURACAO_AJUSTE_RUIDO", "0.7"))

# True = recalibra ruído a cada fala (mais robusto, ~1s a mais por turno).
# BMO_CALIBRAR_TODA_VEZ=0 no .env = calibra só uma vez (mais rápido).
CALIBRAR_RUIDO_TODA_VEZ = os.environ.get("BMO_CALIBRAR_TODA_VEZ", "0") != "0"
INTERVALO_RECALIBRACAO_RUIDO = float(os.environ.get("BMO_INTERVALO_RUIDO", "30"))
ENERGIA_MINIMA = float(os.environ.get("BMO_ENERGIA_MINIMA", "120"))
ENERGIA_MAXIMA = float(os.environ.get("BMO_ENERGIA_MAXIMA", "4000"))
_ruido_ja_calibrado = False
_ultima_calibracao_ruido = 0.0

# Ajustes de VAD (detecção de voz) pensados para conversa presencial.
recognizer.pause_threshold = float(os.environ.get("BMO_PAUSA_FIM_FALA", "0.75"))
recognizer.phrase_threshold = float(os.environ.get("BMO_FALA_MINIMA", "0.25"))
recognizer.non_speaking_duration = float(os.environ.get("BMO_PRE_ROLL", "0.45"))
recognizer.dynamic_energy_threshold = True

# Índice do microfone (útil se houver mais de um dispositivo no Pi).
# Descobrir com: python3 -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
_mic_index_env = os.environ.get("BMO_MIC_INDEX")
INDICE_MICROFONE = int(_mic_index_env) if _mic_index_env else None

DISPOSITIVO_AUDIO_ALSA = os.environ.get("BMO_AUDIO_DEVICE") or None

# Trava de segurança: aborta a reprodução se travar (ex: erro de ALSA)
# em vez de deixar o BMO mudo pra sempre.
TIMEOUT_REPRODUCAO_SEGUNDOS = 15

# Nº de tentativas em chamadas de rede (STT/LLM) antes de desistir —
# rede de evento costuma cair, vale tentar de novo automaticamente.
TENTATIVAS_API = int(os.environ.get("BMO_TENTATIVAS_API", "2"))
ESPERA_ENTRE_TENTATIVAS = 1.0

# ============================================
# CALLBACKS DE INTEGRAÇÃO COM O FRONTEND
# ============================================
on_expressao_changed = None  # def on_expressao(expressao)
on_play_audio = None         # def on_play(arquivo) -> bool
on_change_screen = None      # def on_change_screen(tela, jogo_classe=None)
on_interaction_active = None # def active() -> bool; usado para cancelar fala/escuta ao sair do rosto


def interacao_ativa():
    """No modo integrado, confirma que a tela de conversa ainda está ativa."""
    return on_interaction_active is None or bool(on_interaction_active())

# ============================================
# INTENÇÕES
# ============================================
# Sistema de áudios pré-gravados (saudação, piada, etc.) foi descontinuado —
# hoje toda resposta passa por TTS (ver ação "conversar" abaixo).

INTENCOES = {
     "saudacao": {
        "palavras_chave": ["oi bmo", "olá bmo", "e aí bmo", "opa bmo", "oi", "olá"],
        "acao": "cumprimentar",
        "resposta": "Oiiiii! Quem quer jogar Videogame?"
    },
    "dancar": {
        "palavras_chave": [
            "bmo mudança", "bmo dançar", "quer dançar", "faz uma coreografia", "você sabe dançar", "bmo dança pra gente", "dance",
            "bmo dance", "dançar"
        ],
        "acao": "dancar",
        "resposta": "Vamos dançar!"
    },
    "aura": {
        "palavras_chave": ["farme aura", "far miaura", "six, seven", "six seven", "6, 7", "seis sete", "aura"],
        "acao": "aura",
        "resposta": "Vinte. mais vinte. mais vinte. mais sete. ai é muito fácil professora, é six seven"
    },
    "jogar_velha": {
        "palavras_chave": ["jogo da velha", "jogar velha", "jogar jogo da velha", "abrir jogo da velha"],
        "acao": "abrir_jogo", "jogo": "velha", "script": "velha.py",
        "resposta": "Abrindo o jogo da velha! Boa sorte!"
    },
    "jogar_cobrinha": {
        "palavras_chave": ["jogo da cobrinha", "jogar cobrinha", "jogar snake", "abrir jogo da cobrinha"],
        "acao": "abrir_jogo", "jogo": "cobrinha", "script": "cobrinha.py",
        "resposta": "Abrindo o jogo da cobrinha! Não morda o próprio rabo!"
    },
    "jogar_blocos": {
        "palavras_chave": ["jogo dos blocos", "jogar blocos", "quebra blocos", "abrir jogo dos blocos", "abrir quebra blocos", "jogar block breaker"],
        "acao": "abrir_jogo", "jogo": "blocos", "script": "blocos.py",
        "resposta": "Abrindo o quebra-blocos! Destrua todos os tijolos!"
    },
    "jogar_space_invaders": {
        "palavras_chave": ["space invaders", "jogar space invaders", "jogo de nave", "abrir space invaders"],
        "acao": "abrir_jogo", "jogo": "space_invaders", "script": "space_invaders.py",
        "resposta": "Abrindo Space Invaders! Derrote a Nave Mãe!"
    },
    "comando_errado": {
        "palavras_chave": [],
        # Qualquer fala que não bater com nada acima vira conversa livre com a IA.
        "acao": "conversar",
        "resposta": "Desculpa, tive um probleminha para pensar agora. Pode repetir?"
    }
}

# ============================================
# UTILITÁRIO: RETENTATIVA EM CHAMADAS DE REDE
# ============================================

def _chamar_com_retentativas(func, *args, tentativas=TENTATIVAS_API, espera=ESPERA_ENTRE_TENTATIVAS, **kwargs):
    """
    Executa `func`, tentando de novo em caso de exceção (falha de rede).
    Retorna o resultado ou None se todas as tentativas falharem.
    Não trata um retorno "vazio" legítimo (ex: usuário calado) como falha.
    """
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ultimo_erro = e
            if not interacao_ativa():
                break
            if tentativa < tentativas:
                print(f"🌐 Tentativa {tentativa} falhou ({e}); tentando de novo em {espera}s...")
                time.sleep(espera)
    print(f"🌐 Todas as {tentativas} tentativa(s) falharam: {ultimo_erro}")
    return None

# ============================================
# REPRODUÇÃO DE ÁUDIO (fallback sem frontend)
# ============================================
# Usado só quando não há callback `on_play_audio` do frontend (ex: rodando
# bmo.py sozinho, sem o Pygame). Com o frontend, quem toca é o LipSync.

def tocar_audio(arquivo):
    """Toca até o fim ou até o timeout de segurança. Retorna sucesso/falha."""
    if not os.path.exists(arquivo):
        print(f"⚠️ Arquivo não encontrado: {arquivo}")
        return False

    sistema = platform.system()
    try:
        print("🔊 Tocando áudio...")

        if sistema == "Windows":
            import winsound
            winsound.PlaySound(arquivo, winsound.SND_FILENAME)
            print("✅ Áudio finalizado!")
            return True
        elif sistema == "Darwin":
            comando = ["afplay", arquivo]
        else:  # Linux / Raspberry Pi
            comando = ["aplay", "-q", arquivo]
            if DISPOSITIVO_AUDIO_ALSA:
                comando.extend(["-D", DISPOSITIVO_AUDIO_ALSA])

        resultado = subprocess.run(
            comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_REPRODUCAO_SEGUNDOS
        )
        sucesso = resultado.returncode == 0
        print("✅ Áudio finalizado!" if sucesso else f"⚠️ Reprodução retornou código {resultado.returncode}")
        return sucesso

    except subprocess.TimeoutExpired:
        print(f"⏰ Reprodução travou por mais de {TIMEOUT_REPRODUCAO_SEGUNDOS}s — abortando essa fala.")
        return False
    except FileNotFoundError:
        print(f"⚠️ Player de áudio não encontrado para {sistema}. No Linux: sudo apt install alsa-utils")
        return False
    except Exception as e:
        print(f"Erro ao tocar áudio: {e}")
        return False

# ============================================
# STT — TRANSCRIÇÃO (GROQ WHISPER)
# ============================================

MODELO_STT = "whisper-large-v3-turbo"
CONTEXTO_STT = (
    "Transcrição exclusivamente em português brasileiro. Não traduza e não invente palavras para ruído. "
    "Se não houver voz humana inteligível, retorne vazio. Vocabulário esperado do evento: "
    "BMO, Bimô, RoboAP, Copa Pinhão, UTFPR, Finn, Jake, aura, farme aura, six seven, "
    "seis sete, Space Invaders, jogo da velha, cobrinha e quebra-blocos."
)
LIMITE_SEM_FALA = float(os.environ.get("BMO_LIMITE_SEM_FALA", "0.65"))
LIMITE_LOGPROB_INCERTO = float(os.environ.get("BMO_LIMITE_LOGPROB", "-0.85"))
LIMITE_CONSENSO_STT = float(os.environ.get("BMO_LIMITE_CONSENSO_STT", "0.58"))
SALVAR_TRANSCRICOES = os.environ.get("BMO_SALVAR_TRANSCRICOES", "1") != "0"
ARQUIVO_TRANSCRICOES = caminho(os.path.join("logs", "transcricoes.jsonl"))

_CARACTERES_FORA_DO_PORTUGUES = re.compile(r"[ðþæøåäöüßłőűğış]")
_PADROES_FALA_ESTRANGEIRA = (
    r"\bhun\s+er\b", r"\bdet\s+er\b", r"\bjeg\s+(?:er|har)\b",
    r"\b(?:i|you|we|they)\s+(?:am|are|were)\b", r"\b(?:this|that)\s+is\b",
    r"\b(?:ich|du|wir)\s+(?:bin|bist|sind)\b",
    r"\b(?:je|tu|il|elle)\s+(?:suis|es|est)\b",
    r"\b(?:hello|bonjour|merci|gracias|guten\s+tag)\b",
)


def _motivo_texto_stt_suspeito(texto, idioma=None):
    """Bloqueia ruído convertido em idioma estrangeiro ou frase repetitiva."""
    texto = (texto or "").strip()
    if not texto:
        return None

    idioma_normalizado = str(idioma or "").strip().lower()
    idiomas_pt = {"pt", "por", "portuguese", "português", "portugues"}
    if idioma_normalizado and idioma_normalizado not in idiomas_pt:
        return "idioma_improvavel"
    if _CARACTERES_FORA_DO_PORTUGUES.search(texto.lower()):
        return "idioma_improvavel"
    if any(c.isalpha() and "LATIN" not in unicodedata.name(c, "") for c in texto):
        return "idioma_improvavel"

    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    normalizado = " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acentos).split())
    if any(re.search(padrao, normalizado) for padrao in _PADROES_FALA_ESTRANGEIRA):
        return "idioma_improvavel"

    palavras = normalizado.split()
    if len(palavras) >= 3:
        repeticoes = Counter(palavras).most_common(1)[0][1]
        if repeticoes >= 3 and repeticoes / len(palavras) >= 0.5:
            return "repeticao_suspeita"
        bigramas = list(zip(palavras, palavras[1:]))
        if bigramas and Counter(bigramas).most_common(1)[0][1] >= 2:
            return "repeticao_suspeita"
    return None


def _campo(objeto, nome, padrao=None):
    if isinstance(objeto, dict):
        return objeto.get(nome, padrao)
    return getattr(objeto, nome, padrao)


def _reduzir_ruido_audio(audio):
    """Aplica filtro de graves + gate espectral leve antes do Whisper.

    O piso de ruído é estimado dentro da própria fala usando o percentil 20
    de cada faixa. A atenuação tem piso, portanto consoantes fracas não são
    completamente apagadas em ambientes de evento.
    """
    try:
        taxa = 16000
        pcm = audio.get_raw_data(convert_rate=taxa, convert_width=2)
        amostras = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if amostras.size < 1024:
            return audio

        tamanho = 512
        salto = 256
        quantidade = 1 + int(math.ceil(max(0, amostras.size - tamanho) / salto))
        total = (quantidade - 1) * salto + tamanho
        sinal = np.pad(amostras, (0, total - amostras.size))
        janela = np.hanning(tamanho).astype(np.float32)
        quadros = np.stack([sinal[i * salto:i * salto + tamanho] * janela for i in range(quantidade)])
        espectro = np.fft.rfft(quadros, axis=1)
        magnitude = np.abs(espectro)
        piso_ruido = np.percentile(magnitude, 20, axis=0)
        ganho = np.clip(1.0 - 1.25 * piso_ruido[None, :] / (magnitude + 1e-8), 0.15, 1.0)

        # Suaviza o gate entre quadros para não criar som "metálico".
        for i in range(1, quantidade):
            ganho[i] = 0.65 * ganho[i - 1] + 0.35 * ganho[i]

        frequencias = np.fft.rfftfreq(tamanho, 1.0 / taxa)
        passa_altas = np.clip((frequencias - 70.0) / 60.0, 0.0, 1.0)
        filtrado = espectro * ganho * passa_altas[None, :]

        saida = np.zeros(total, dtype=np.float64)
        soma_janela = np.zeros(total, dtype=np.float64)
        for i in range(quantidade):
            inicio = i * salto
            quadro = np.fft.irfft(filtrado[i], n=tamanho).real * janela
            saida[inicio:inicio + tamanho] += quadro
            soma_janela[inicio:inicio + tamanho] += janela * janela
        mascara = soma_janela > 1e-8
        saida[mascara] /= soma_janela[mascara]
        saida = saida[:amostras.size]

        pico = float(np.max(np.abs(saida))) if saida.size else 0.0
        if pico > 0:
            saida *= min(3.0, 0.92 / pico)
        pcm_filtrado = np.clip(saida * 32767.0, -32768, 32767).astype(np.int16).tobytes()
        return sr.AudioData(pcm_filtrado, taxa, 2)
    except Exception as e:
        print(f"⚠️ Redução de ruído indisponível; usando áudio original: {e}")
        return audio

def _transcrever_audio_bruto(audio):
    return cliente_groq.audio.transcriptions.create(
        file=("fala.wav", audio.get_wav_data()),
        model=MODELO_STT, language="pt", prompt=CONTEXTO_STT,
        response_format="verbose_json", temperature=0
    )


def _avaliar_transcricao(resultado):
    if resultado is None:
        return {"texto": None, "confiavel": False, "motivo": "falha_api"}

    texto = (_campo(resultado, "text", "") or "").strip()
    idioma = _campo(resultado, "language", None)
    segmentos = _campo(resultado, "segments", None) or []
    probs_sem_fala = [float(_campo(s, "no_speech_prob", 0) or 0) for s in segmentos]
    logprobs = [float(_campo(s, "avg_logprob", 0) or 0) for s in segmentos]
    compressoes = [float(_campo(s, "compression_ratio", 0) or 0) for s in segmentos]
    media_sem_fala = sum(probs_sem_fala) / len(probs_sem_fala) if probs_sem_fala else 0.0
    media_logprob = sum(logprobs) / len(logprobs) if logprobs else None
    max_compressao = max(compressoes, default=0.0)

    motivo = None
    if not texto:
        motivo = "vazio"
    elif media_sem_fala > LIMITE_SEM_FALA:
        motivo = "provavel_ruido"
    elif _motivo_texto_stt_suspeito(texto, idioma):
        motivo = _motivo_texto_stt_suspeito(texto, idioma)
    elif media_logprob is not None and media_logprob < LIMITE_LOGPROB_INCERTO:
        motivo = "baixa_confianca"
    elif max_compressao > 2.4:
        motivo = "repeticao_suspeita"
    elif len(re.sub(r"\W", "", texto, flags=re.UNICODE)) < 2:
        motivo = "curto_demais"

    return {
        "texto": texto or None,
        "confiavel": motivo is None,
        "motivo": motivo,
        "avg_logprob": media_logprob,
        "no_speech_prob": media_sem_fala,
        "language": idioma,
    }


def _normalizar_transcricao(texto):
    return extrair_texto_sem_pontuacao(texto or "").strip()


def _salvar_transcricao(resultado, alternativas):
    if not SALVAR_TRANSCRICOES:
        return
    try:
        os.makedirs(os.path.dirname(ARQUIVO_TRANSCRICOES), exist_ok=True)
        registro = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "texto": resultado.get("texto"),
            "status": "entendido" if resultado.get("confiavel") else resultado.get("motivo", "incerto"),
            "alternativas": [a.get("texto") for a in alternativas if a.get("texto")],
        }
        with open(ARQUIVO_TRANSCRICOES, "a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"⚠️ Não foi possível salvar a transcrição: {e}")


def transcrever_audio_detalhado(audio, cancelar_evento=None):
    """Transcreve, mede incerteza e faz uma segunda leitura quando preciso."""
    filtrado = _reduzir_ruido_audio(audio)
    primeira = _avaliar_transcricao(_chamar_com_retentativas(_transcrever_audio_bruto, filtrado))
    alternativas = [primeira]

    if _foi_cancelado(cancelar_evento) or not interacao_ativa():
        return {"texto": None, "confiavel": False, "motivo": "cancelado"}

    if primeira["confiavel"]:
        primeira = dict(primeira)
        primeira["texto"] = corrigir_transcricao(primeira["texto"])
        _salvar_transcricao(primeira, alternativas)
        return primeira

    print(f"🔎 Primeira transcrição incerta ({primeira['motivo']}); tentando entender pelo áudio original...")
    segunda = _avaliar_transcricao(_chamar_com_retentativas(_transcrever_audio_bruto, audio))
    alternativas.append(segunda)

    if _foi_cancelado(cancelar_evento) or not interacao_ativa():
        return {"texto": None, "confiavel": False, "motivo": "cancelado"}

    if segunda["confiavel"]:
        if primeira.get("texto"):
            semelhanca = SequenceMatcher(
                None, _normalizar_transcricao(primeira["texto"]), _normalizar_transcricao(segunda["texto"])
            ).ratio()
            escolhida = (
                segunda if semelhanca >= LIMITE_CONSENSO_STT
                else {"texto": None, "confiavel": False, "motivo": "alternativas_divergentes"}
            )
        else:
            escolhida = segunda
    elif primeira.get("texto") and segunda.get("texto"):
        semelhanca = SequenceMatcher(
            None, _normalizar_transcricao(primeira["texto"]), _normalizar_transcricao(segunda["texto"])
        ).ratio()
        motivos_bloqueados = {"idioma_improvavel", "repeticao_suspeita", "provavel_ruido"}
        pode_confirmar = not ({primeira.get("motivo"), segunda.get("motivo")} & motivos_bloqueados)
        if semelhanca >= 0.78 and pode_confirmar:
            escolhida = dict(max((primeira, segunda), key=lambda item: len(item["texto"])))
            escolhida.update(confiavel=True, motivo="confirmada_por_repeticao_stt")
        else:
            escolhida = {"texto": None, "confiavel": False, "motivo": "alternativas_divergentes"}
    else:
        escolhida = {"texto": None, "confiavel": False, "motivo": segunda.get("motivo") or primeira.get("motivo")}

    if escolhida.get("texto"):
        escolhida = dict(escolhida)
        escolhida["texto"] = corrigir_transcricao(escolhida["texto"])
    _salvar_transcricao(escolhida, alternativas)
    return escolhida


def transcrever_audio(audio):
    return transcrever_audio_detalhado(audio).get("texto")

# ============================================
# CORREÇÃO LEVE DE TRANSCRIÇÃO (pós-STT)
# ============================================
CORRECOES_STT = {
    "jeique": "Jake", "jaik": "Jake", "jayque": "Jake",
    "fine": "Finn", "fin": "Finn",
    "biemo": "BMO", "bimo": "BMO", "bimô": "BMO", "bíumó": "BMO",
}

CORRECOES_FRASES_STT = (
    (r"\b(?:six|6|seis)\s+(?:e\s+)?(?:o\s+)?(?:seven|7|sete)\b", "six seven"),
    (r"\bfar\s+(?:me|mi|mig)\s+(?:ára|ara|aura)\b", "farme aura"),
    (r"\bfar\s+miaura\b", "farme aura"),
    (r"\baparmiaura\b", "farme aura"),
)

def corrigir_transcricao(texto):
    if not texto:
        return texto

    for padrao, substituicao in CORRECOES_FRASES_STT:
        texto = re.sub(padrao, substituicao, texto, flags=re.IGNORECASE)

    palavras = texto.split()
    for i, palavra in enumerate(palavras):
        nucleo = re.sub(r'[^\wÀ-ÿ]', '', palavra).lower()
        if nucleo in CORRECOES_STT:
            match_nucleo = re.match(r'^[\wÀ-ÿ]*', palavra)
            sufixo = palavra[match_nucleo.end():] if match_nucleo else ""
            palavras[i] = CORRECOES_STT[nucleo] + sufixo
    return " ".join(palavras)

# ============================================
# AGENTE CONVERSACIONAL (GROQ LLM)
# ============================================

MODELO_CHAT = "openai/gpt-oss-120b"
ARQUIVO_PERSONALIDADE = caminho("prompt/bmo_prompt.txt")


def carregar_personalidade():
    try:
        with open(ARQUIVO_PERSONALIDADE, "r", encoding="utf-8") as arquivo:
            return arquivo.read().strip()
    except FileNotFoundError:
        print(f"[BMO] ERRO: Arquivo de personalidade não encontrado: {ARQUIVO_PERSONALIDADE}")
        return ""


PERSONALIDADE_BMO = carregar_personalidade()

# Memória de curto prazo — fica na RAM, reinicia com o programa.
historico_conversa = [{"role": "system", "content": PERSONALIDADE_BMO}]
LIMITE_HISTORICO = 6


def _chamar_llm_bruto(mensagens):
    resposta = cliente_groq.chat.completions.create(
        model=MODELO_CHAT, messages=mensagens, temperature=0.5,
        max_completion_tokens=200, include_reasoning=False, reasoning_effort="low"
    )
    return resposta.choices[0].message.content.strip()


# bmo_prompt.txt instrui o modelo a sempre prefixar a resposta com uma tag de
# emoção, ex: "[FELIZ] Eba!". Regex tolerante a variações de espaço/case, mas
# só aceita a tag se estiver nos primeiros ~15 caracteres (senão é fala normal).
_REGEX_TAG_EXPRESSAO = re.compile(r'\[\s*(neutro|feliz|triste|surpreso)\s*\]\s*', re.IGNORECASE)


def _extrair_expressao(texto_bruto):
    """Separa a tag de expressão do texto falado. Retorna (texto_falado, expressao)."""
    # Defesa para modelos de raciocínio que eventualmente vazem um bloco de
    # análise apesar de include_reasoning=False.
    texto_bruto = re.sub(r"<think>.*?</think>", "", texto_bruto, flags=re.IGNORECASE | re.DOTALL).strip()
    m = _REGEX_TAG_EXPRESSAO.search(texto_bruto)
    if not m:
        texto_falado, expressao = texto_bruto, "neutro"
    else:
        expressao = m.group(1).lower()
        # Se houver preâmbulo antes da tag, ele não é fala do personagem.
        texto_falado = texto_bruto[m.end():].strip()

    # O contrato também é garantido pelo programa: remove outras tags,
    # markdown e limita a fala mesmo quando o modelo desobedecer ao prompt.
    texto_falado = re.sub(r"\[\s*(?:neutro|feliz|triste|surpreso)\s*\]", "", texto_falado, flags=re.IGNORECASE)
    texto_falado = re.sub(r"[*_`#]", "", texto_falado)
    texto_falado = " ".join(texto_falado.split())
    palavras = texto_falado.split()
    if len(palavras) > 30:
        texto_falado = " ".join(palavras[:30]).rstrip(",;:-") + "."
    if not texto_falado:
        texto_falado = "Hã? Bimô ficou sem resposta agora."
    return texto_falado, expressao


def gerar_resposta_ia(texto_usuario):
    """Manda a fala do usuário pro LLM com histórico + personalidade. Retorna (texto_falado, expressao)."""
    global historico_conversa

    historico_conversa.append({"role": "user", "content": texto_usuario})
    texto_bruto = _chamar_com_retentativas(_chamar_llm_bruto, historico_conversa)

    if not interacao_ativa():
        # Não deixa na memória uma resposta que o visitante nunca ouviu.
        if historico_conversa and historico_conversa[-1].get("role") == "user":
            historico_conversa.pop()
        return "", "neutro"

    if not texto_bruto:  # falha de rede OU resposta vazia
        historico_conversa.pop()
        return "Desculpa, tive um probleminha para pensar agora. Pode repetir?", "neutro"

    # Guarda a resposta CRUA (com tag) — mantém o modelo consistente com o
    # próprio formato que ele já usou antes.
    historico_conversa.append({"role": "assistant", "content": texto_bruto})
    if len(historico_conversa) > LIMITE_HISTORICO + 1:
        historico_conversa[:] = [historico_conversa[0]] + historico_conversa[-LIMITE_HISTORICO:]

    return _extrair_expressao(texto_bruto)


def reiniciar_memoria_conversa():
    global historico_conversa
    historico_conversa = [{"role": "system", "content": PERSONALIDADE_BMO}]

# ============================================
# TTS — PIPER (offline, roda local no Pi)
# ============================================
# Instalação: pip install piper-tts
# Arquivos necessários em vozes/: dii_pt-BR.onnx + dii_pt-BR.onnx.json

try:
    from piper import PiperVoice, SynthesisConfig
except ImportError:
    # Versões antigas do piper-tts não têm esse atalho de import.
    from piper.voice import PiperVoice
    SynthesisConfig = None

def _resolver_caminho_voz_piper():
    """Resolve a voz sem deixar uma variável .env vazia quebrar o fallback.

    Piper recebe um *modelo* ONNX, nunca um .wav/.mp3 de resposta. Caminhos
    relativos informados no .env são interpretados a partir de backend/.
    """
    configurado = (os.environ.get("BMO_VOZ_PIPER") or "").strip()
    if not configurado:
        return caminho("vozes/dii_pt-BR.onnx")
    configurado = os.path.expanduser(configurado)
    return configurado if os.path.isabs(configurado) else caminho(configurado)


CAMINHO_VOZ_PIPER = _resolver_caminho_voz_piper()


# (velocidade) e noise_scale/noise_w_scale (variação de entonação/ritmo).
PIPER_VELOCIDADE = 0.9       # length_scale: 1.0 = normal, >1 mais lento, <1 mais rápido
PIPER_VOLUME = 1.0
PIPER_VARIACAO = 0.7         # noise_scale: variação da entonação
PIPER_VARIACAO_FALA = 0.8    # noise_w_scale: variação do ritmo da fala

# Taxa de saída fixa: o modelo sintetiza nativamente em 22050Hz, mas alguns
# adaptadores USB distorcem nessa taxa. Reamostramos pra 44100Hz
TAXA_AMOSTRAGEM_SAIDA = 44100


def _reamostrar_wav_pcm16(dados_pcm, n_canais, taxa_origem, taxa_alvo):
    """Reamostra PCM 16-bit via interpolação linear (numpy) — leve, sem ffmpeg/scipy."""
    amostras = np.frombuffer(dados_pcm, dtype=np.int16)
    if amostras.size == 0 or taxa_origem == taxa_alvo:
        return dados_pcm

    if n_canais > 1:
        amostras = amostras.reshape(-1, n_canais)
    n_amostras_origem = amostras.shape[0]

    duracao = n_amostras_origem / float(taxa_origem)
    n_amostras_alvo = max(1, int(round(duracao * taxa_alvo)))
    indices_origem = np.arange(n_amostras_origem)
    posicoes_alvo = np.linspace(0, n_amostras_origem - 1, num=n_amostras_alvo)

    if n_canais > 1:
        canais = [np.interp(posicoes_alvo, indices_origem, amostras[:, c].astype(np.float64)) for c in range(n_canais)]
        amostras_finais = np.stack(canais, axis=1).reshape(-1)
    else:
        amostras_finais = np.interp(posicoes_alvo, indices_origem, amostras.astype(np.float64))

    return np.clip(amostras_finais, -32768, 32767).astype(np.int16).tobytes()


def _carregar_voz_piper():
    extensao = os.path.splitext(CAMINHO_VOZ_PIPER)[1].lower()
    if extensao != ".onnx":
        print(f"⚠️ BMO_VOZ_PIPER precisa apontar para um modelo .onnx, não para '{extensao or 'um arquivo sem extensão'}'.")
        print("   Exemplo: BMO_VOZ_PIPER=vozes/dii_pt-BR.onnx")
        return None
    if not os.path.exists(CAMINHO_VOZ_PIPER):
        print(f"⚠️ Voz do Piper não encontrada em: {CAMINHO_VOZ_PIPER}")
        print("   O BMO vai continuar rodando, mas falar_texto() sempre vai falhar até o arquivo existir.")
        return None
    caminho_config = CAMINHO_VOZ_PIPER + ".json"
    if not os.path.exists(caminho_config):
        print(f"⚠️ Configuração da voz do Piper não encontrada: {caminho_config}")
        print("   Mantenha o arquivo .onnx.json ao lado do modelo .onnx.")
        return None
    try:
        return PiperVoice.load(CAMINHO_VOZ_PIPER)
    except Exception as e:
        print(f"⚠️ Erro ao carregar a voz do Piper: {e}")
        return None


# Carregado uma única vez na inicialização — recarregar o .onnx a cada fala
# seria lento demais.
VOZ_PIPER = _carregar_voz_piper()

CONFIG_SINTESE_PIPER = SynthesisConfig(
    volume=PIPER_VOLUME,
    length_scale=PIPER_VELOCIDADE,
    noise_scale=PIPER_VARIACAO,
    noise_w_scale=PIPER_VARIACAO_FALA,
    normalize_audio=True,
) if SynthesisConfig is not None else None


def _sintetizar_com_piper(texto, caminho_wav):
    """Sintetiza em memória, reamostra pra 44100Hz e grava em `caminho_wav`."""
    if VOZ_PIPER is None:
        return False
    try:
        buffer_bruto = io.BytesIO()
        with wave.open(buffer_bruto, "wb") as arquivo_wav:
            metodo = getattr(VOZ_PIPER, "synthesize_wav", None) or VOZ_PIPER.synthesize
            try:
                metodo(texto, arquivo_wav, syn_config=CONFIG_SINTESE_PIPER)
            except TypeError:  # versões antigas sem syn_config
                metodo(texto, arquivo_wav)

        buffer_bruto.seek(0)
        with wave.open(buffer_bruto, "rb") as wf_bruto:
            n_canais = wf_bruto.getnchannels()
            largura_amostra = wf_bruto.getsampwidth()
            taxa_origem = wf_bruto.getframerate()
            dados_brutos = wf_bruto.readframes(wf_bruto.getnframes())

        if largura_amostra == 2 and taxa_origem != TAXA_AMOSTRAGEM_SAIDA:
            dados_finais = _reamostrar_wav_pcm16(dados_brutos, n_canais, taxa_origem, TAXA_AMOSTRAGEM_SAIDA)
            taxa_final = TAXA_AMOSTRAGEM_SAIDA
        else:
            dados_finais = dados_brutos
            taxa_final = taxa_origem

        with wave.open(caminho_wav, "wb") as arquivo_final:
            arquivo_final.setnchannels(n_canais)
            arquivo_final.setsampwidth(largura_amostra)
            arquivo_final.setframerate(taxa_final)
            arquivo_final.writeframes(dados_finais)
        return True

    except Exception as e:
        print(f"⚠️ Erro ao gerar fala com o Piper: {e}")
        return False


def falar_texto(texto):
    if not interacao_ativa() or not texto or not texto.strip() or VOZ_PIPER is None:
        return False
    # No programa integrado, o arquivo temporário passa pelo LipSync. Isso
    # permite interromper a fala ao sair da tela; o streaming direto no aplay
    # não oferecia essa garantia e continuava falando no menu.
    if on_play_audio:
        return _falar_arquivo_temporario(texto)
    if APLAY_DISPONIVEL:
        return _falar_streaming(texto)
    return _falar_arquivo_temporario(texto)


def _falar_streaming(texto):
    """Linux/Pi: pipeia PCM direto pro aplay, sem gravar em disco."""
    taxa = getattr(getattr(VOZ_PIPER, "config", None), "sample_rate", 22050)
    comando = ["aplay", "-q", "-r", str(taxa), "-f", "S16_LE", "-t", "raw", "-c", "1"]
    if DISPOSITIVO_AUDIO_ALSA:
        comando.extend(["-D", DISPOSITIVO_AUDIO_ALSA])

    metodo_stream = getattr(VOZ_PIPER, "synthesize_stream_raw", None)
    if metodo_stream is None:
        print("⚠️ piper-tts sem synthesize_stream_raw — atualize o pacote.")
        return _falar_arquivo_temporario(texto)

    try:
        processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for pedaco in metodo_stream(texto, syn_config=CONFIG_SINTESE_PIPER):
            processo.stdin.write(pedaco)
        processo.stdin.close()
        processo.wait(timeout=TIMEOUT_REPRODUCAO_SEGUNDOS)
        return processo.returncode == 0
    except Exception as e:
        print(f"⚠️ Erro na síntese em streaming: {e}")
        return False


def _falar_arquivo_temporario(texto):
    """Windows/Mac (dev sem aplay): grava um wav e toca com tocar_audio()."""
    nome_temp = f"_fala_temp_{uuid.uuid4().hex}.wav"
    caminho_wav = caminho(os.path.join("audios", nome_temp))
    os.makedirs(os.path.dirname(caminho_wav), exist_ok=True)
    try:
        if not _sintetizar_com_piper(texto, caminho_wav):
            return False
        tocou = on_play_audio(caminho_wav) if on_play_audio else tocar_audio(caminho_wav)
    except Exception as e:
        print(f"⚠️ Erro ao gerar fala com o Piper: {e}")
        return False
    finally:
        if os.path.exists(caminho_wav):
            try:
                os.remove(caminho_wav)
            except OSError:
                pass
    return tocou
# ============================================
# DETECÇÃO DE INTENÇÃO POR SIMILARIDADE
# ============================================

def extrair_texto_sem_pontuacao(texto):
    return re.sub(r'[^\w\s]', '', texto.lower())


def _normalizar_comando(texto):
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFD", corrigir_transcricao(texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acentos).split())


def _e_comando_aura(texto):
    """Reconhece o gatilho Aura sem depender da similaridade nem do LLM."""
    normalizado = _normalizar_comando(texto)
    alvo = r"(?:six\s+seven|farme\s+aura)"
    wake = r"(?:bmo|bimo|biemo|biumo)"

    # O gatilho sozinho ou precedido pelo nome do BMO é um comando válido.
    if re.fullmatch(rf"(?:{wake}\s+)?{alvo}", normalizado):
        return True

    # Negação diretamente ligada ao pedido nunca executa a ação.
    if re.search(
        r"\bnao\s+(?:(?:quero|queremos)\s+que\s+\w+\s+)?"
        r"(?:fale|fala|faca|faz|mande|manda|ative|ativa|execute|executa|solte|solta)\b",
        normalizado,
    ):
        return False

    acao = (
        r"(?:faz|faca|manda|mande|ativa|ative|executa|execute|solta|solte|"
        r"fale|fala|diga|diz|quero\s+que\s+(?:voce|bmo|bimo|biemo|biumo)\s+fale)"
    )
    return bool(re.search(rf"\b{acao}\b.{{0,35}}\b{alvo}\b", normalizado))


# --- Pesos de palavra (calculado uma vez, a partir do próprio INTENCOES) ---
# Palavras que aparecem em várias intenções ("jogo", "jogar", "abrir") são
# pouco úteis pra diferenciar comandos e devem pesar menos. Palavras que só
# aparecem numa intenção ("cobrinha", "velha", "combate") identificam de
# verdade o comando e devem pesar mais. Isso é recalculado automaticamente
# se você adicionar/remover keywords depois — não precisa mexer aqui.
def _construir_pesos_palavras(intencoes):
    intencoes_por_palavra = Counter()
    for dados in intencoes.values():
        palavras_da_intencao = set()
        for chave in dados["palavras_chave"]:
            palavras_da_intencao.update(extrair_texto_sem_pontuacao(chave).split())
        for palavra in palavras_da_intencao:
            intencoes_por_palavra[palavra] += 1

    n_intencoes = len(intencoes)
    return {
        palavra: math.log((n_intencoes + 1) / (freq + 1)) + 1
        for palavra, freq in intencoes_por_palavra.items()
    }


PESOS_PALAVRAS = _construir_pesos_palavras(INTENCOES)
PESO_PADRAO = 1.0  # palavra nunca vista antes (ex: erro de transcrição) — peso neutro
LIMIAR_MATCH_PALAVRA = 0.75  # abaixo disso, duas palavras não contam como "a mesma"


def _peso(palavra):
    return PESOS_PALAVRAS.get(palavra, PESO_PADRAO)


def _melhor_correspondencia_palavra(palavra, palavras_alvo):
    """Encontra o quanto `palavra` se parece com a palavra mais próxima em
    `palavras_alvo` (tolera erro de digitação/transcrição em UMA palavra,
    sem deixar o resto da frase contaminar o resultado)."""
    melhor = 0.0
    for alvo in palavras_alvo:
        if palavra == alvo:
            return 1.0
        melhor = max(melhor, SequenceMatcher(None, palavra, alvo).ratio())
    return melhor


def _cobertura_ponderada(palavras_origem, palavras_alvo):
    """Fração ponderada de `palavras_origem` que encontra correspondência em `palavras_alvo`."""
    peso_total = peso_casado = 0.0
    for p in palavras_origem:
        peso = _peso(p)
        peso_total += peso
        sim = _melhor_correspondencia_palavra(p, palavras_alvo)
        if sim >= LIMIAR_MATCH_PALAVRA:
            peso_casado += peso * sim
    return (peso_casado / peso_total) if peso_total > 0 else 0.0


def calcular_similaridade(texto, palavra_chave):
    t = extrair_texto_sem_pontuacao(texto).strip()
    pc = extrair_texto_sem_pontuacao(palavra_chave).strip()
    if not t or not pc:
        return 0.0
    if t == pc:
        return 100.0

    palavras_t = t.split()
    palavras_pc = pc.split()

    # RECALL: quanto da keyword está coberto pelo que o usuário disse.
    recall = _cobertura_ponderada(palavras_pc, palavras_t)
    # PRECISÃO: quanto do que o usuário disse é explicado pela keyword.
    # Sem isso, uma palavra extra e "estranha" no meio da frase nunca
    # custava nada — foi o que causou "jogo de combate" casando com
    # "jogo da cobrinha" antes.
    precisao = _cobertura_ponderada(palavras_t, palavras_pc)

    if recall + precisao == 0:
        return 0.0
    f1 = 2 * recall * precisao / (recall + precisao)
    return f1 * 100


# ============================================
# FALLBACK: CLASSIFICAÇÃO POR LLM QUANDO A SIMILARIDADE FICA AMBÍGUA
# ============================================
# Similaridade de texto (mesmo ponderada) só pega variação de ESCRITA da
# mesma palavra (erro de digitação, transcrição, plural). Ela não sabe que
# "luta" e "combate" significam a mesma coisa -- isso é sinônimo, não
# parecença de string, e nenhum ajuste de fórmula resolve isso. Por isso,
# quando a similaridade não tem um vencedor claro, perguntamos pro LLM
# (que já está conectado pro chat livre) qual intenção faz mais sentido.
# Isso só roda nos casos ambíguos -- comandos batendo direto no keyword
# continuam instantâneos, sem essa chamada de rede.

def _montar_prompt_classificacao(texto, nomes_intencoes):
    opcoes = ", ".join(nomes_intencoes)
    return (
        f"O usuário de um assistente de voz disse: \"{texto}\"\n\n"
        f"Qual das intenções abaixo melhor descreve o que ele quer?\n"
        f"{opcoes}\n\n"
        f"Se nenhuma fizer sentido, responda exatamente: nenhuma\n"
        f"Responda APENAS com o nome exato de uma intenção da lista, "
        f"sem explicação, sem pontuação."
    )


def _classificar_com_llm_bruto(texto, nomes_intencoes):
    resposta = cliente_groq.chat.completions.create(
        model=MODELO_CHAT,
        messages=[{"role": "user", "content": _montar_prompt_classificacao(texto, nomes_intencoes)}],
        temperature=0,
        max_completion_tokens=15,
    )
    return resposta.choices[0].message.content.strip().lower()


def classificar_intencao_com_llm(texto, nomes_intencoes):
    """Pergunta pro LLM qual intenção bate com o texto. Retorna o nome da
    intenção, ou None se o LLM não tiver certeza ou a chamada falhar
    (falha de rede aqui nunca deve travar o BMO -- só cai pra 'comando_errado',
    que já é o comportamento seguro de sempre)."""
    escolha = _chamar_com_retentativas(_classificar_com_llm_bruto, texto, nomes_intencoes)
    if escolha and escolha in nomes_intencoes:
        return escolha
    return None


def detectar_intencao(texto):
    LIMITE_CONFIE = 60.0
    MARGEM_MINIMA = 10.0  # vencedor precisa passar o 2º colocado por essa margem

    texto = corrigir_transcricao(texto or "")
    if _e_comando_aura(texto):
        return "aura", 100.0
    normalizado_aura = _normalizar_comando(texto)
    if re.search(r"\b(?:six\s+seven|farme\s+aura)\b", normalizado_aura):
        # Menção em pergunta/comentário não deve acionar a coreografia.
        return "comando_errado", 0.0

    candidatos = []
    for intencao, dados in INTENCOES.items():
        if intencao == "comando_errado":
            continue
        melhor_desta_intencao = max(
            (calcular_similaridade(texto, palavra) for palavra in dados["palavras_chave"]),
            default=0.0,
        )
        candidatos.append((melhor_desta_intencao, intencao))

    if not candidatos:
        return "comando_errado", 0.0

    candidatos.sort(reverse=True)
    melhor_pct, melhor_intencao = candidatos[0]
    segunda_pct = candidatos[1][0] if len(candidatos) > 1 else 0.0

    # Caso claro: a similaridade já resolve, sem gastar chamada de rede.
    if melhor_pct >= LIMITE_CONFIE and (melhor_pct - segunda_pct) >= MARGEM_MINIMA:
        return melhor_intencao, round(melhor_pct, 1)

    # Caso ambíguo (empate técnico, ou nada bateu bem o suficiente): só
    # aqui vale a pena perguntar pro LLM, que entende sinônimo de verdade.
    nomes_intencoes = [i for i in INTENCOES if i != "comando_errado"]
    escolha_llm = classificar_intencao_com_llm(texto, nomes_intencoes)
    if escolha_llm:
        print(f"🤖 Similaridade ficou ambígua ({melhor_pct:.1f}% vs {segunda_pct:.1f}%); LLM escolheu '{escolha_llm}'.")
        return escolha_llm, melhor_pct

    return "comando_errado", round(melhor_pct, 1)


def atualizar_expressao_por_intencao(intencao):
    if not on_expressao_changed:
        return
    # "comando_errado" dispara a ação "conversar" — expressão fica neutra
    # aqui porque ainda não sabemos o que a IA vai responder; a expressão
    # real chega depois, junto com a resposta gerada.
    mapeamento = {"comando_errado": "neutro", "aura": "feliz", "dancar": "feliz"}
    on_expressao_changed(mapeamento.get(intencao, "neutro"))


def reproduzir_resposta(dados):
    arquivo = dados.get("arquivo")
    if arquivo and os.path.exists(arquivo):
        return on_play_audio(arquivo) if on_play_audio else tocar_audio(arquivo)
    return falar_texto(dados["resposta"])


def executar_intencao(intencao, dados, texto=None):
    """Executa a ação da intenção. Retorna False se deve sair, True se continua."""
    if not interacao_ativa():
        print("🛑 Interação cancelada porque a tela de conversa foi fechada.")
        return True
    print(f"🎯 Ação: {dados['acao']}")
    atualizar_expressao_por_intencao(intencao)

    if dados["acao"] == "tocar_audio":
        print(f"💬 {dados.get('resposta', 'Tocando áudio...')}")
        if not reproduzir_resposta(dados):
            print("🔊 Erro ao tocar áudio!")
        return True

    elif dados["acao"] == "responder":
        print(f"💬 {dados['resposta']}")
        reproduzir_resposta(dados)
        return True

    elif dados["acao"] == "sair":
        print(f"👋 {dados['resposta']}")
        reproduzir_resposta(dados)
        return False

    elif dados["acao"] == "cumprimentar":
        print(f"👋 {dados['resposta']}")
        enviar_comando_bracos("OI")
        reproduzir_resposta(dados)
        return True

    elif dados["acao"] == "dancar":
        print(f"💃 {dados['resposta']}")
        enviar_comando_bracos("DANCAR")
        reproduzir_resposta(dados)
        return True

    elif dados["acao"] == "aura":
        print(f"💃 {dados['resposta']}")
        enviar_comando_bracos("AURA")
        reproduzir_resposta(dados)
        return True

    elif dados["acao"] == "abrir_jogo":
        print(f"🎮 {dados['resposta']}")
        if "resposta" in dados:
            reproduzir_resposta(dados)
        script = dados.get("script")
        if script and on_change_screen:
            on_change_screen("jogos", script)
        return True

    elif dados["acao"] == "conversar":
        print("🤔 Pensando em uma resposta...")
        if texto:
            resposta_ia, expressao_ia = gerar_resposta_ia(texto)
        else:
            resposta_ia, expressao_ia = dados["resposta"], "neutro"
        if not interacao_ativa():
            print("🛑 Resposta descartada: o usuário saiu da tela de conversa.")
            return True
        print(f"🤖 BMO ({expressao_ia}): {resposta_ia}")

        # Expressão aplicada ANTES de falar, pro rosto já mudar no instante
        # em que o áudio começa (boca anima por cima, sem apagar a emoção).
        if on_expressao_changed:
            on_expressao_changed(expressao_ia)
        falar_texto(resposta_ia)
        return True

    return True

# ============================================
# MICROFONE
# ============================================

def _foi_cancelado(cancelar_evento):
    return cancelar_evento is not None and cancelar_evento.is_set()


def _energia_pcm(buffer):
    amostras = np.frombuffer(buffer, dtype=np.int16)
    if amostras.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(amostras.astype(np.float64) ** 2)))


def _calibrar_ruido_cancelavel(source, recognizer_obj, duracao, cancelar_evento):
    global _ruido_ja_calibrado, _ultima_calibracao_ruido
    segundos_buffer = source.CHUNK / float(source.SAMPLE_RATE)
    energias = []
    limite = max(1, int(math.ceil(duracao / segundos_buffer)))
    for _ in range(limite):
        if _foi_cancelado(cancelar_evento):
            return False
        buffer = source.stream.read(source.CHUNK)
        if not buffer:
            break
        energias.append(_energia_pcm(buffer))

    if energias:
        # Percentil alto ignora pequenos silêncios; o multiplicador separa a
        # voz próxima do burburinho constante sem deixar o limiar explodir.
        ambiente = float(np.percentile(energias, 70))
        recognizer_obj.energy_threshold = min(ENERGIA_MAXIMA, max(ENERGIA_MINIMA, ambiente * 1.45))
        _ruido_ja_calibrado = True
        _ultima_calibracao_ruido = time.monotonic()
        print(f"🎚️ Limiar de voz calibrado em {recognizer_obj.energy_threshold:.0f}")
    return True


def _capturar_fala_cancelavel(source, recognizer_obj, timeout, phrase_time_limit, cancelar_evento):
    """Versão cancelável da captura do SpeechRecognition.

    Lê um buffer curto por vez para que sair da tela feche o microfone em
    dezenas de milissegundos, em vez de esperar o timeout inteiro.
    """
    segundos_buffer = source.CHUNK / float(source.SAMPLE_RATE)
    inicio = time.monotonic()
    pre_roll = deque(maxlen=max(1, int(math.ceil(recognizer_obj.non_speaking_duration / segundos_buffer))))

    while True:
        if _foi_cancelado(cancelar_evento):
            return None
        if timeout is not None and time.monotonic() - inicio >= timeout:
            return None
        buffer = source.stream.read(source.CHUNK)
        if not buffer:
            return None
        pre_roll.append(buffer)
        energia = _energia_pcm(buffer)
        if energia > recognizer_obj.energy_threshold:
            break

        if recognizer_obj.dynamic_energy_threshold:
            amortecimento = recognizer_obj.dynamic_energy_adjustment_damping ** segundos_buffer
            alvo = energia * recognizer_obj.dynamic_energy_ratio
            novo_limiar = recognizer_obj.energy_threshold * amortecimento + alvo * (1 - amortecimento)
            recognizer_obj.energy_threshold = min(ENERGIA_MAXIMA, max(ENERGIA_MINIMA, novo_limiar))

    quadros = list(pre_roll)
    inicio_fala = time.monotonic()
    buffers_pausa = max(1, int(math.ceil(recognizer_obj.pause_threshold / segundos_buffer)))
    buffers_minimos = max(1, int(math.ceil(recognizer_obj.phrase_threshold / segundos_buffer)))
    pausa = 0
    falados = 0

    while True:
        if _foi_cancelado(cancelar_evento):
            return None
        if phrase_time_limit is not None and time.monotonic() - inicio_fala >= phrase_time_limit:
            break
        buffer = source.stream.read(source.CHUNK)
        if not buffer:
            break
        quadros.append(buffer)
        falados += 1
        if _energia_pcm(buffer) > recognizer_obj.energy_threshold:
            pausa = 0
        else:
            pausa += 1
            if pausa > buffers_pausa:
                break

    if falados - pausa < buffers_minimos:
        return None
    excesso_silencio = max(0, pausa - pre_roll.maxlen)
    if excesso_silencio:
        quadros = quadros[:-excesso_silencio]
    return sr.AudioData(b"".join(quadros), source.SAMPLE_RATE, source.SAMPLE_WIDTH)


def escutar_microfone(recognizer_obj, timeout, phrase_time_limit=None, ajustar_ruido=False,
                      duracao_ajuste=1, cancelar_evento=None):
    """Escuta uma fala e permite cancelamento imediato ao trocar de tela."""
    global _ruido_ja_calibrado
    try:
        with sr.Microphone(device_index=INDICE_MICROFONE) as source:
            calibracao_expirada = time.monotonic() - _ultima_calibracao_ruido >= INTERVALO_RECALIBRACAO_RUIDO
            deve_calibrar = ajustar_ruido and (
                CALIBRAR_RUIDO_TODA_VEZ or not _ruido_ja_calibrado or calibracao_expirada
            )
            if deve_calibrar:
                if not _calibrar_ruido_cancelavel(source, recognizer_obj, duracao_ajuste, cancelar_evento):
                    return None
            return _capturar_fala_cancelavel(
                source, recognizer_obj, timeout, phrase_time_limit, cancelar_evento
            )
    except OSError as e:
        print(f"🎤 Erro ao acessar o microfone: {e}")
        return None

# ============================================
# CICLO PRINCIPAL DE RECONHECIMENTO
# ============================================

def reconhecer_e_agir(modo_texto=False, cancelar_evento=None):
    """Escuta/lê, reconhece a intenção e executa a ação correspondente."""
    texto = None

    if modo_texto:
        try:
            texto = input("\n📝 Digite seu comando: ").strip()
            if not texto:
                return True
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            return False
    else:
        time.sleep(PAUSA_APOS_FALAR)
        if _foi_cancelado(cancelar_evento) or not interacao_ativa():
            return True
        print("\n🎙️ Ajustando ruído ambiente...")
        print("🎤 Escutando... (fale naturalmente)")

        try:
            audio = escutar_microfone(
                recognizer, timeout=TIMEOUT_ESCUTA, phrase_time_limit=PHRASE_TIME_LIMIT,
                ajustar_ruido=True, duracao_ajuste=DURACAO_AJUSTE_RUIDO,
                cancelar_evento=cancelar_evento,
            )
        except Exception as e:
            print(f"⚠️ Erro inesperado: {e}")
            return True

        if audio is None:
            if not _foi_cancelado(cancelar_evento):
                print("⏰ Ninguém falou... (pausa)")
            return True

        print("🔄 Processando com a Groq (Whisper)...")
        resultado_stt = transcrever_audio_detalhado(audio, cancelar_evento=cancelar_evento)
        texto = corrigir_transcricao(resultado_stt.get("texto"))

        if _foi_cancelado(cancelar_evento) or not interacao_ativa():
            print("🛑 Transcrição descartada: a tela de conversa foi fechada.")
            return True

        if not texto:
            print(f"❓ Não foi possível entender a fala ({resultado_stt.get('motivo', 'incerto')}).")
            falar_texto("Desculpa, Bimô não conseguiu entender. Pode repetir?")
            return True

        print(f"📝 Você disse: '{texto}'")

    if _foi_cancelado(cancelar_evento) or not interacao_ativa():
        return True
    intencao, score = detectar_intencao(texto)
    print(f"🎯 Intenção: {intencao} (confiança: {score}%)")
    return executar_intencao(intencao, INTENCOES[intencao], texto)

# ============================================
# ENTRYPOINT DE DESENVOLVIMENTO
# (a integração real roda via main.py + frontend; isso aqui é pra testar
# o backend isolado, sem Pygame)
# ============================================

def testar_microfone():
    print("\n🎤 Teste de microfone - Fale algo...")
    try:
        audio = escutar_microfone(recognizer, timeout=3, ajustar_ruido=True, duracao_ajuste=1)
        if audio is None:
            raise sr.WaitTimeoutError()
        print(f"✅ Microfone OK! Você disse: {transcrever_audio(audio)}")
        return True
    except Exception:
        print("❌ Microfone com problema ou sem som detectado")
        return False


def main():
    print("🔍 Verificando voz do Piper...")
    print("   ✅  Voz do Piper carregada." if VOZ_PIPER else f"   ⚠️  Voz não carregada ({CAMINHO_VOZ_PIPER}) — o BMO vai rodar SEM conseguir falar.")

    print("\n" + "=" * 50)
    print("🎙️ BMO - ASSISTENTE INTERATIVO (modo standalone)")
    print("=" * 50)
    print("[1] Microfone (Padrão)")
    print("[2] Teclado (Terminal)")
    modo_texto = input("Digite 1 ou 2: ").strip() == "2"
    print("⌨️  Modo texto ativado.\n" if modo_texto else "🎙️ Modo microfone ativado.\n")

    executando = True
    while executando:
        try:
            executando = reconhecer_e_agir(modo_texto)
        except Exception as e:
            # Um erro inesperado em qualquer parte do ciclo não deve
            # derrubar o programa numa apresentação ao vivo.
            print(f"❌ Erro inesperado no ciclo principal: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
