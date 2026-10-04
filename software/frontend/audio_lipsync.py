"""
audio_lipsync.py
============================================
Toca um arquivo .wav e, ao mesmo tempo, calcula a amplitude (volume)
em tempo real para alimentar a animação da boca (lip sync).

Reaproveita a mesma lógica de leitura de áudio usada no bmo.py
(pyaudio + wave), só que aqui a gente também mede o volume de
cada pedaço (chunk) tocado.

Uso típico (dentro do loop principal do Pygame):

    lipsync = LipSync()
    lipsync.tocar("audios/oi.wav")
    ...
    nivel = lipsync.nivel_atual()   # 0.0 a 1.0
    face.atualizar(dt, nivel_audio=nivel)
"""

import threading
import time
import wave

import numpy as np
import pyaudio


def _calcular_rms(data, largura_amostra):
    """
    Calcula o RMS (volume) de um pedaço de áudio sem depender do
    módulo `audioop` (removido da biblioteca padrão no Python 3.13).
    Só suporta 16 bits, que é o formato usado nos áudios do projeto.

    Usa numpy (vetorizado, em C) em vez de somar amostra por amostra
    em Python puro — a versão antiga atrasava o stream.write() o
    suficiente pra causar cortes no ALSA do Raspberry Pi 3.
    """
    if largura_amostra != 2:
        return 0

    amostras = np.frombuffer(data, dtype=np.int16)
    if amostras.size == 0:
        return 0

    return float(np.sqrt(np.mean(amostras.astype(np.float64) ** 2)))


class LipSync:
    CHUNK = 4096
    SUAVIZACAO = 0.5          # peso do novo valor ao suavizar o nível de áudio
    RMS_REFERENCIA = 12000    # RMS considerado "volume máximo" pra normalizar 0-1

    def __init__(self):
        self._pa = pyaudio.PyAudio()
        self._nivel = 0.0
        self._tocando = False
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = None

    def nivel_atual(self):
        with self._lock:
            return self._nivel

    def esta_tocando(self):
        return self._tocando

    def tocar(self, caminho_arquivo, stop_event=None):
        """Para qualquer reprodução em andamento e toca o novo arquivo em uma thread separada."""
        self.parar()
        self._stop_event = stop_event or threading.Event()
        self._thread = threading.Thread(
            target=self._tocar_thread, args=(caminho_arquivo, self._stop_event), daemon=True
        )
        self._thread.start()

    def parar(self):
        """Interrompe a reprodução atual, se houver, e espera a thread terminar."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()

    def _tocar_thread(self, caminho_arquivo, stop_event):
        self._tocando = True
        wf = None
        stream = None
        try:
            wf = wave.open(caminho_arquivo, "rb")
            stream = self._pa.open(
                format=self._pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                frames_per_buffer=self.CHUNK,
            )

            largura_amostra = wf.getsampwidth()
            taxa_amostragem = wf.getframerate()
            data = wf.readframes(self.CHUNK)
            interrompido = False

            while data:
                if stop_event.is_set():
                    interrompido = True
                    break
                stream.write(data)

                try:
                    rms = _calcular_rms(data, largura_amostra)
                    nivel_normalizado = min(1.0, rms / self.RMS_REFERENCIA)
                except Exception:
                    nivel_normalizado = 0.0

                with self._lock:
                    self._nivel = self._nivel * (1 - self.SUAVIZACAO) + nivel_normalizado * self.SUAVIZACAO

                data = wf.readframes(self.CHUNK)

            # stream.write() bloqueante retorna assim que o pedaço entra no buffer
            # do PortAudio, não quando termina de tocar de fato. No Pi 3 o próprio
            # custo do laço (RMS, troca de contexto) já dava esse tempo de sobra;
            # no Pi 4, o laço é rápido demais e o stream.close() corta o último
            # pedaço. Por isso damos ao PortAudio o tempo de um chunk pra esvaziar
            # o buffer antes de fechar — só quando o áudio terminou naturalmente.
            if not interrompido:
                try:
                    time.sleep(self.CHUNK / float(taxa_amostragem))
                except Exception:
                    time.sleep(0.2)

        except Exception as e:
            print(f"⚠️ Erro no lip sync: {e}")
        finally:
            with self._lock:
                self._nivel = 0.0
            self._tocando = False
            if stream:
                stream.stop_stream()
                stream.close()
            if wf:
                wf.close()

    def encerrar(self):
        self.parar()
        self._pa.terminate()
