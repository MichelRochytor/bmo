"""
imagens.py
============================================
Carregador genérico de imagens com cache, usado pelos jogos pra
não recarregar/redimensionar a mesma imagem a cada frame (importante
pra rodar bem no Raspberry Pi).
============================================
"""

import os

import pygame

PASTA_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

_cache_originais = {}
_cache_escaladas = {}


def carregar(nome_arquivo):
    """Carrega (com cache) uma imagem da pasta games/assets. Retorna None se falhar."""
    if nome_arquivo in _cache_originais:
        return _cache_originais[nome_arquivo]

    caminho = os.path.join(PASTA_ASSETS, nome_arquivo)
    try:
        img = pygame.image.load(caminho).convert_alpha()
    except Exception as e:
        print(f"⚠️ Não consegui carregar {caminho}: {e}")
        img = None

    _cache_originais[nome_arquivo] = img
    return img


def escalar_para_largura(nome_arquivo, largura_alvo, espelhado=False):
    """Retorna a imagem redimensionada (com cache) pra uma largura específica."""
    chave = (nome_arquivo, largura_alvo, espelhado)
    if chave in _cache_escaladas:
        return _cache_escaladas[chave]

    original = carregar(nome_arquivo)
    if original is None:
        return None

    proporcao = original.get_height() / original.get_width()
    altura_alvo = max(1, int(largura_alvo * proporcao))
    img = pygame.transform.smoothscale(original, (max(1, largura_alvo), altura_alvo))
    if espelhado:
        img = pygame.transform.flip(img, True, False)

    _cache_escaladas[chave] = img
    return img


def escalar_para_preencher(nome_arquivo, largura_tela, altura_tela):
    """
    Retorna a imagem redimensionada (com cache) pra preencher a tela toda,
    cortando o excesso (como um 'background-size: cover' do CSS).
    """
    chave = (nome_arquivo, "cover", largura_tela, altura_tela)
    if chave in _cache_escaladas:
        return _cache_escaladas[chave]

    original = carregar(nome_arquivo)
    if original is None:
        return None

    prop_imagem = original.get_width() / original.get_height()
    prop_tela = largura_tela / altura_tela

    if prop_imagem > prop_tela:
        nova_altura = altura_tela
        nova_largura = int(nova_altura * prop_imagem)
    else:
        nova_largura = largura_tela
        nova_altura = int(nova_largura / prop_imagem)

    img = pygame.transform.smoothscale(original, (nova_largura, nova_altura))

    x_corte = (nova_largura - largura_tela) // 2
    y_corte = (nova_altura - altura_tela) // 2
    img = img.subsurface((x_corte, y_corte, largura_tela, altura_tela)).copy()

    _cache_escaladas[chave] = img
    return img
