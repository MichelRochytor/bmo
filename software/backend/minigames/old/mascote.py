"""
mascote.py
============================================
Desenho do mascote ROBOAP (texugo), agora usando a arte-final de
verdade (games/assets/roboap.png) em vez de formas geométricas.

A imagem é carregada uma vez e fica em cache (já redimensionada e
espelhada quando preciso) pra não pesar no Raspberry Pi.

Se a imagem não for encontrada por algum motivo, cai automaticamente
de volta pro desenho geométrico simples (fallback), então o jogo
nunca quebra por causa disso.
============================================
"""

import math
import os

import pygame

AMARELO = (240, 175, 30)
PRETO = (20, 20, 20)
BRANCO = (245, 245, 245)
CINZA = (90, 90, 90)

CAMINHO_IMAGEM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "roboap.png")

_imagem_original = None
_imagem_carregada = False
_cache_escalas = {}  # (largura_alvo, espelhado) -> Surface


def _carregar_imagem():
    global _imagem_original, _imagem_carregada
    if _imagem_carregada:
        return _imagem_original
    _imagem_carregada = True
    try:
        _imagem_original = pygame.image.load(CAMINHO_IMAGEM).convert_alpha()
    except Exception as e:
        print(f"⚠️ Não consegui carregar {CAMINHO_IMAGEM}: {e}. Usando desenho geométrico.")
        _imagem_original = None
    return _imagem_original


def _obter_imagem_escalada(largura_alvo, espelhado):
    chave = (largura_alvo, espelhado)
    if chave in _cache_escalas:
        return _cache_escalas[chave]

    original = _carregar_imagem()
    if original is None:
        return None

    proporcao = original.get_height() / original.get_width()
    altura_alvo = int(largura_alvo * proporcao)
    img = pygame.transform.smoothscale(original, (largura_alvo, altura_alvo))
    if espelhado:
        img = pygame.transform.flip(img, True, False)

    _cache_escalas[chave] = img
    return img


def desenhar_roboap(tela, x, y, escala=1.0, espelhado=False, fase_animacao=0.0):
    """
    Desenha o ROBOAP centrado em (x, y).
    fase_animacao: 0.0 a 1.0+, usado pra dar uma leve "respirada"/balanço.
    espelhado: True faz o texugo olhar pra esquerda em vez de direita
               (a imagem original olha pra direita).
    """
    balanco = math.sin(fase_animacao * 2 * math.pi) * 3 * escala
    largura_alvo = max(20, int(100 * escala))

    imagem = _obter_imagem_escalada(largura_alvo, espelhado)

    if imagem is not None:
        rect = imagem.get_rect(center=(int(x), int(y + balanco)))
        tela.blit(imagem, rect)
    else:
        _desenhar_fallback_geometrico(tela, x, y + balanco, escala, espelhado)


def _desenhar_fallback_geometrico(tela, x, y, escala, espelhado):
    """Usado só se a imagem não puder ser carregada (ex: arquivo faltando)."""
    direcao = -1 if espelhado else 1
    raio_corpo = int(28 * escala)
    cx, cy = int(x), int(y)

    pygame.draw.circle(tela, AMARELO, (cx, cy), raio_corpo + 4)
    pygame.draw.circle(tela, PRETO, (cx, cy), raio_corpo)

    largura_faixa = int(raio_corpo * 1.1)
    altura_faixa = int(raio_corpo * 0.55)
    faixa = pygame.Rect(0, 0, largura_faixa, altura_faixa)
    faixa.center = (cx, cy - int(raio_corpo * 0.15))
    pygame.draw.ellipse(tela, BRANCO, faixa)

    olho_x = cx + direcao * int(raio_corpo * 0.35)
    olho_y = cy - int(raio_corpo * 0.1)
    pygame.draw.circle(tela, AMARELO, (olho_x, olho_y), max(2, int(raio_corpo * 0.12)))

    pygame.draw.circle(tela, PRETO, (cx + direcao * int(raio_corpo * 0.7), cy + int(raio_corpo * 0.15)),
                        max(3, int(raio_corpo * 0.22)))


def cor_fundo_tema():
    return (18, 20, 26)
