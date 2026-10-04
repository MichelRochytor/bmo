"""Testes do pipeline sem exigir placa de som, rede, Piper ou ESP32."""

import importlib.util
import os
import sys
import threading
import types
import unittest

import numpy as np


class AudioData:
    def __init__(self, frame_data, sample_rate, sample_width):
        self.frame_data = frame_data
        self.sample_rate = sample_rate
        self.sample_width = sample_width

    def get_raw_data(self, convert_rate=None, convert_width=None):
        return self.frame_data

    def get_wav_data(self):
        return self.frame_data


class Recognizer:
    pause_threshold = 0.75
    phrase_threshold = 0.25
    non_speaking_duration = 0.45
    dynamic_energy_threshold = True
    dynamic_energy_adjustment_damping = 0.15
    dynamic_energy_ratio = 1.5
    energy_threshold = 300


def carregar_bmo():
    sr = types.ModuleType("speech_recognition")
    sr.Recognizer = Recognizer
    sr.AudioData = AudioData
    sr.Microphone = object
    sr.WaitTimeoutError = TimeoutError
    sys.modules["speech_recognition"] = sr

    groq = types.ModuleType("groq")
    groq.Groq = lambda **kwargs: types.SimpleNamespace()
    sys.modules["groq"] = groq

    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv

    serial = types.ModuleType("serial")
    serial.Serial = lambda *args, **kwargs: types.SimpleNamespace(write=lambda data: None)
    sys.modules["serial"] = serial

    piper = types.ModuleType("piper")
    piper.PiperVoice = types.SimpleNamespace(load=lambda path: None)
    piper.SynthesisConfig = lambda **kwargs: None
    sys.modules["piper"] = piper

    os.environ["BMO_SALVAR_TRANSCRICOES"] = "0"
    caminho = os.path.join(os.path.dirname(__file__), "..", "backend", "bmo.py")
    spec = importlib.util.spec_from_file_location("bmo_em_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class PipelineVozTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bmo = carregar_bmo()

    def test_contrato_do_modelo_e_limitado_pelo_codigo(self):
        longo = "<think>segredo</think>[FELIZ] **" + " ".join(f"p{i}" for i in range(40))
        texto, expressao = self.bmo._extrair_expressao(longo)
        self.assertEqual(expressao, "feliz")
        self.assertEqual(len(texto.split()), 30)
        self.assertNotIn("think", texto)
        self.assertNotIn("*", texto)

    def test_stt_marca_segmento_de_baixa_confianca(self):
        resultado = {"text": "talvez alguma coisa", "segments": [{"avg_logprob": -1.2, "no_speech_prob": 0.1}]}
        avaliado = self.bmo._avaliar_transcricao(resultado)
        self.assertFalse(avaliado["confiavel"])
        self.assertEqual(avaliado["motivo"], "baixa_confianca")

    def test_filtro_de_ruido_preserva_formato_pcm(self):
        rng = np.random.default_rng(42)
        amostras = rng.normal(0, 600, 16000).astype(np.int16)
        audio = AudioData(amostras.tobytes(), 16000, 2)
        filtrado = self.bmo._reduzir_ruido_audio(audio)
        self.assertEqual(filtrado.sample_rate, 16000)
        self.assertEqual(filtrado.sample_width, 2)
        self.assertEqual(len(filtrado.frame_data), len(audio.frame_data))

    def test_voz_piper_vazia_usa_o_modelo_padrao(self):
        anterior = os.environ.get("BMO_VOZ_PIPER")
        os.environ["BMO_VOZ_PIPER"] = ""
        try:
            caminho = self.bmo._resolver_caminho_voz_piper()
        finally:
            if anterior is None:
                os.environ.pop("BMO_VOZ_PIPER", None)
            else:
                os.environ["BMO_VOZ_PIPER"] = anterior
        self.assertEqual(os.path.basename(caminho), "dii_pt-BR.onnx")
        self.assertEqual(os.path.basename(os.path.dirname(caminho)), "vozes")

    def test_duas_transcricoes_incertas_e_divergentes_sao_rejeitadas(self):
        resultados = iter([
            {"text": "abrir jogo da velha", "segments": [{"avg_logprob": -1.0}]},
            {"text": "qual a cor da mesa", "segments": [{"avg_logprob": -1.0}]},
        ])
        original = self.bmo._chamar_com_retentativas
        self.bmo._chamar_com_retentativas = lambda *args, **kwargs: next(resultados)
        try:
            audio = AudioData(np.zeros(2000, dtype=np.int16).tobytes(), 16000, 2)
            resposta = self.bmo.transcrever_audio_detalhado(audio)
        finally:
            self.bmo._chamar_com_retentativas = original
        self.assertIsNone(resposta["texto"])
        self.assertEqual(resposta["motivo"], "alternativas_divergentes")

    def test_captura_para_antes_de_ler_quando_cancelada(self):
        class Stream:
            leituras = 0

            def read(self, _):
                self.leituras += 1
                return b"\0" * 2048

        source = types.SimpleNamespace(CHUNK=1024, SAMPLE_RATE=16000, SAMPLE_WIDTH=2, stream=Stream())
        evento = threading.Event()
        evento.set()
        audio = self.bmo._capturar_fala_cancelavel(source, Recognizer(), 5, 10, evento)
        self.assertIsNone(audio)
        self.assertEqual(source.stream.leituras, 0)


if __name__ == "__main__":
    unittest.main()
