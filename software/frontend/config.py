"""
config.py — compatibilidade do front-end com a configuração central.
Edite o `.env`; os valores são carregados por runtime_config.py.
"""

import os
import sys

SOFTWARE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOFTWARE_DIR not in sys.path:
    sys.path.insert(0, SOFTWARE_DIR)
import runtime_config

# --- Tela ---
LARGURA = runtime_config.LOGICAL_WIDTH
ALTURA = runtime_config.LOGICAL_HEIGHT
FULLSCREEN = runtime_config.FULLSCREEN
FPS = runtime_config.FPS
BARRA_COR = runtime_config.BAR_COLOR


def display_flags(pygame):
    return runtime_config.pygame_display_flags(pygame)

TITULO_JANELA = "BMO - Front-end"

# --- Paleta oficial do BMO ---
CORPO = (99, 189, 164)          # #63bda4
TELA_FUNDO = (217, 255, 234)    # #d9ffea
BORDA_TELA = (98, 175, 183)     # #62afb7
BOTAO_ROSA = (242, 5, 83)       # #f20553
BOTAO_AMARELO = (255, 236, 71)  # #ffec47
PRETO = (30, 30, 30)            # olhos / boca
BRANCO = (255, 255, 255)

# Aliases legados (usados em código antigo — não remover sem checar referências)
VERDE_CORPO = CORPO
AZUL_DESTAQUE = BORDA_TELA

# Cor de texto secundário (itens de menu não selecionados, dicas "ESC: voltar").
# ANTES era um alias de BORDA_TELA (98,175,183) — quase idêntico ao fundo
# VERDE_CORPO (99,189,164), diferença de luminância ~6/255, ou seja,
# praticamente invisível. Agora é uma cor própria, escura o suficiente pra
# ter contraste de verdade contra o fundo.
VERDE_CORPO_ESCURO = (35, 90, 78)

# --- Caminhos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def caminho_audio(arquivo):
    return os.path.join(BASE_DIR, "..", "backend", "audios", arquivo)
