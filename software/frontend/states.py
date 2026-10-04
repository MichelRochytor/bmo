"""
states.py
============================================
Estados/expressões possíveis do rosto do BMO. Centralizar aqui evita
strings soltas espalhadas pelo código.
============================================
"""

NEUTRO = "neutro"
FELIZ = "feliz"
TRISTE = "triste"
SURPRESO = "surpreso"
DORMINDO = "dormindo"   # estado de "tela de descanso"

# FALANDO não é um humor (não entra em TODOS) -- é o estado de lip sync,
# controlado à parte por Face.falando/set_falando(). Mantido aqui só para
# compatibilidade com Face.set_expressao(), ainda usado em screens.py.
FALANDO = "falando"

TODOS = [NEUTRO, FELIZ, TRISTE, SURPRESO, DORMINDO]
