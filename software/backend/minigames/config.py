"""
config.py
============================================
Compatibilidade dos minigames com a configuração central.
Resolução, fullscreen, FPS e ritmo vêm do `.env` via runtime_config.py.
============================================
"""

import os
import sys

SOFTWARE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SOFTWARE_DIR not in sys.path:
    sys.path.insert(0, SOFTWARE_DIR)
import runtime_config

# ============================================
# TELA
# ============================================

# Não duplique valores aqui; runtime_config.py é a fonte única.
LARGURA = runtime_config.LOGICAL_WIDTH
ALTURA = runtime_config.LOGICAL_HEIGHT
FULLSCREEN = runtime_config.FULLSCREEN
FPS = runtime_config.FPS
BARRA_COR = runtime_config.BAR_COLOR
SNAKE_FPS = runtime_config.SNAKE_FPS
SNAKE_CELL_SIZE = runtime_config.SNAKE_CELL_SIZE
SPACE_PLAYER_SPEED = runtime_config.SPACE_PLAYER_SPEED
SPACE_ENEMY_SPEED_FACTOR = runtime_config.SPACE_ENEMY_SPEED_FACTOR
SPACE_MOTHERSHIP_SPEED = runtime_config.SPACE_MOTHERSHIP_SPEED
SPACE_SPAWN_FRAMES = runtime_config.SPACE_SPAWN_FRAMES


def display_flags(pygame):
    return runtime_config.pygame_display_flags(pygame)

TITULO_JANELA = "BMO - Front-end"

# ============================================
# CORES (paleta oficial do BMO)
# ============================================

CORPO = (99, 189, 164)            # #63bda4 - Corpo e base do rosto (verde-azulado claro)
TELA_FUNDO = (217, 255, 234)      # #d9ffea - Tela do rosto (cinza esverdeado claro)
BORDA_TELA = (98, 175, 183)       # #62afb7 - Borda da tela / detalhes (ciano)
BOTAO_ROSA = (242, 5, 83)         # #f20553 - Botão 1 (rosa/magenta)
BOTAO_AMARELO = (255, 236, 71)    # #ffec47 - Botão 2 (amarelo)

# Mantidos por compatibilidade com código existente
VERDE_CORPO = CORPO
VERDE_CORPO_ESCURO = BORDA_TELA
PRETO = (30, 30, 30)              # olhos / boca
BRANCO = (255, 255, 255)
AZUL_DESTAQUE = BORDA_TELA

# ============================================
# CAMINHOS
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def caminho_audio(arquivo):
    """Aponta para a pasta de áudios já usada no bmo.py (software/backend/audios)."""
    return os.path.join(BASE_DIR, "..", "backend", "audios", arquivo)


import pygame

# Inicialização global do Joystick
def init_joystick():
    if not pygame.get_init():
        pygame.init()
    if not pygame.joystick.get_init():
        pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
    return joysticks

def get_joystick_state(joysticks):
    state = {'left': False, 'right': False, 'up': False, 'down': False, 'action': False, 'action2': False, 'action3': False}
    if not joysticks: return state
    pad = joysticks[0]
    
    axis_x = pad.get_axis(0) if pad.get_numaxes() > 0 else 0
    axis_y = pad.get_axis(1) if pad.get_numaxes() > 1 else 0
    hat = pad.get_hat(0) if pad.get_numhats() > 0 else (0, 0)
    
    state['left'] = axis_x < -0.5 or hat[0] == -1
    state['right'] = axis_x > 0.5 or hat[0] == 1
    state['up'] = axis_y < -0.5 or hat[1] == 1
    state['down'] = axis_y > 0.5 or hat[1] == -1
    
    num_btns = pad.get_numbuttons()
    state['action'] = pad.get_button(0) if num_btns > 0 else False
    state['action2'] = pad.get_button(1) if num_btns > 1 else False
    state['action3'] = pad.get_button(2) if num_btns > 2 else False
    
    return state
