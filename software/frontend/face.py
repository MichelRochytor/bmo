"""
face.py — desenha e anima o rosto do BMO em camadas independentes:
corpo -> olhos (emoção, self.expressao) -> boca (fala, self.falando).

Por padrão desenha por código (formas geométricas). Pra usar imagens
prontas, coloque PNGs em assets/faces/ com fundo transparente, no
tamanho de config.LARGURA x ALTURA:

    corpo.png
    olhos_{neutro,feliz,triste,surpreso,dormindo}.png
    boca_{neutro,feliz,triste,surpreso,dormindo}.png      (boca parada)
    boca_falando_{fechada,meio,aberta}.png                (lip sync)

Olhos e boca são independentes de propósito: dá pra estar "feliz" e
"falando" ao mesmo tempo sem um estado atropelar o outro.
"""

import math
import os
import random
import pygame

import config
import states


_EXTENSOES_ACEITAS = (".png", ".jpg", ".jpeg")
PASTA_ROSTOS = os.path.join(config.BASE_DIR, "assets", "faces")

_NOME_CORPO = "corpo"
_NOMES_OLHOS = {
    states.NEUTRO: "olhos_neutro",
    states.FELIZ: "olhos_feliz",
    states.TRISTE: "olhos_triste",
    states.SURPRESO: "olhos_surpreso",
    states.DORMINDO: "olhos_dormindo",
}
_NOMES_BOCA_PARADA = {
    states.NEUTRO: "boca_neutro",
    states.FELIZ: "boca_feliz",
    states.TRISTE: "boca_triste",
    states.SURPRESO: "boca_surpreso",
    states.DORMINDO: "boca_dormindo",
}
_NOMES_BOCA_FALANDO = ["boca_falando_fechada", "boca_falando_meio", "boca_falando_aberta"]

# Piscar nessas expressões usa o visual de "dormindo" (olhos fechados)
# em vez de um asset de piscada dedicado.
_EXPRESSOES_QUE_PISCAM_COM_OLHO_DE_DORMIR = (states.NEUTRO, states.TRISTE, states.SURPRESO)

_TODOS_OS_NOMES = (
    [_NOME_CORPO] + list(_NOMES_OLHOS.values())
    + list(_NOMES_BOCA_PARADA.values()) + _NOMES_BOCA_FALANDO
)


class Face:
    def __init__(self):
        self.expressao = states.NEUTRO
        self.falando = False  # independente de self.expressao — ver docstring

        self.piscando = False
        self.tempo_proximo_piscar = self._novo_intervalo_piscar()
        self.duracao_piscada = 0.12
        self._cronometro_piscada = 0.0

        self.nivel_boca = 0.0  # 0.0 fechada -> 1.0 aberta
        self._tempo_fala_simulada = 0.0

        self.cx = config.LARGURA // 2
        self.cy = config.ALTURA // 2

        self.imagens = self._carregar_imagens()

    # --- Atualização por frame ---

    def atualizar(self, dt, nivel_audio=None):
        """nivel_audio: 0.0-1.0 vindo do áudio real; se None e self.falando, simula fala."""
        self._atualizar_piscar(dt)
        self._atualizar_boca(dt, nivel_audio)

    def _novo_intervalo_piscar(self):
        return random.uniform(2.0, 6.0)

    def _atualizar_piscar(self, dt):
        # FELIZ/DORMINDO não piscam (olhos já ficam fechados/curvos). Se a
        # expressão mudar no meio de uma piscada, encerra ela na hora.
        if self.expressao in (states.DORMINDO, states.FELIZ):
            if self.piscando:
                self.piscando = False
                self._cronometro_piscada = 0.0
            return

        if self.piscando:
            self._cronometro_piscada += dt
            if self._cronometro_piscada >= self.duracao_piscada:
                self.piscando = False
                self._cronometro_piscada = 0.0
                self.tempo_proximo_piscar = self._novo_intervalo_piscar()
        else:
            self.tempo_proximo_piscar -= dt
            if self.tempo_proximo_piscar <= 0:
                self.piscando = True

    def _atualizar_boca(self, dt, nivel_audio):
        if not self.falando:
            self.nivel_boca = 0.0
            return

        if nivel_audio is not None:
            self.nivel_boca = max(0.0, min(1.0, nivel_audio))
        else:
            # Sem áudio real conectado ainda -> simula um "blá blá blá"
            self._tempo_fala_simulada += dt * 9
            self.nivel_boca = (math.sin(self._tempo_fala_simulada) + 1) / 2

    # --- Controle de estado ---

    def set_expressao(self, nova_expressao):
        # FALANDO não é uma emoção — é controlado por set_falando(). Aceitar
        # aqui foi a causa dos olhos "resetarem" durante a fala (ver nota acima).
        if nova_expressao == states.FALANDO:
            print("⚠️ set_expressao(FALANDO) ignorado — use set_falando(True/False).")
            return
        if nova_expressao in states.TODOS:
            self.expressao = nova_expressao
        else:
            print(f"⚠️ Expressão desconhecida: {nova_expressao}")

    def set_falando(self, falando):
        """Liga/desliga a animação de fala, sem mexer na emoção do rosto."""
        self.falando = bool(falando)
        if not self.falando:
            self.nivel_boca = 0.0

    def piscar_agora(self):
        self.piscando = True
        self._cronometro_piscada = 0.0

    # --- Imagens opcionais ---

    def _carregar_imagens(self):
        imagens = {}
        if not os.path.isdir(PASTA_ROSTOS):
            return imagens

        tamanho_alvo = (config.LARGURA, config.ALTURA)
        for nome in _TODOS_OS_NOMES:
            for ext in _EXTENSOES_ACEITAS:
                caminho_arquivo = os.path.join(PASTA_ROSTOS, nome + ext)
                if not os.path.exists(caminho_arquivo):
                    continue
                try:
                    imagem = pygame.image.load(caminho_arquivo).convert_alpha()
                    if imagem.get_size() != tamanho_alvo:
                        escala = min(
                            tamanho_alvo[0] / imagem.get_width(),
                            tamanho_alvo[1] / imagem.get_height(),
                        )
                        tamanho = (
                            max(1, round(imagem.get_width() * escala)),
                            max(1, round(imagem.get_height() * escala)),
                        )
                        redimensionada = pygame.transform.smoothscale(imagem, tamanho)
                        camada = pygame.Surface(tamanho_alvo, pygame.SRCALPHA)
                        if nome == _NOME_CORPO:
                            camada.fill(config.CORPO)
                        camada.blit(
                            redimensionada,
                            ((tamanho_alvo[0] - tamanho[0]) // 2, (tamanho_alvo[1] - tamanho[1]) // 2),
                        )
                        imagem = camada
                    imagens[nome] = imagem
                    print(f"🖼️  Rosto: '{nome}{ext}' carregada.")
                except Exception as e:
                    print(f"⚠️ Rosto: falha ao carregar '{caminho_arquivo}': {e}")
                break
        return imagens

    def _imagem_boca_falando_atual(self):
        fechada = self.imagens.get("boca_falando_fechada")
        meio = self.imagens.get("boca_falando_meio")
        aberta = self.imagens.get("boca_falando_aberta")
        if not fechada and not aberta:
            return None
        if self.nivel_boca < 0.2:
            return fechada or aberta
        if self.nivel_boca < 0.6 and meio:
            return meio
        return aberta or fechada

    # --- Desenho (corpo -> olhos -> boca) ---

    def desenhar(self, tela):
        self._desenhar_corpo(tela)
        self._desenhar_olhos(tela)
        self._desenhar_boca(tela)

    def _desenhar_corpo(self, tela):
        imagem_corpo = self.imagens.get(_NOME_CORPO)
        if imagem_corpo:
            tela.blit(imagem_corpo, (0, 0))
        else:
            self._desenhar_tela_rosto(tela)

    def _desenhar_tela_rosto(self, tela):
        margem_corpo = 8
        corpo = pygame.Rect(margem_corpo, margem_corpo,
                             config.LARGURA - margem_corpo * 2,
                             config.ALTURA - margem_corpo * 2)
        pygame.draw.rect(tela, config.CORPO, corpo, border_radius=22)

        margem_tela = 24
        rect = pygame.Rect(margem_tela, margem_tela - 6,
                            config.LARGURA - margem_tela * 2,
                            config.ALTURA - margem_tela * 2 - 34)
        pygame.draw.rect(tela, config.TELA_FUNDO, rect, border_radius=14)
        pygame.draw.rect(tela, config.BORDA_TELA, rect, width=5, border_radius=14)

        botao_y = config.ALTURA - margem_corpo - 22
        pygame.draw.circle(tela, config.BOTAO_ROSA, (config.LARGURA // 2 - 24, botao_y), 9)
        pygame.draw.circle(tela, config.BOTAO_AMARELO, (config.LARGURA // 2 + 24, botao_y), 9)

    def _desenhar_olhos(self, tela):
        expressao_para_olhos = self.expressao
        if self.piscando and self.expressao in _EXPRESSOES_QUE_PISCAM_COM_OLHO_DE_DORMIR:
            expressao_para_olhos = states.DORMINDO

        imagem_olhos = self.imagens.get(_NOMES_OLHOS.get(expressao_para_olhos))
        if imagem_olhos:
            tela.blit(imagem_olhos, (0, 0))
            return

        olho_largura = 34
        olho_altura = 46
        espaco = 70

        if expressao_para_olhos == states.SURPRESO:
            olho_largura = 40
            olho_altura = 56
        elif expressao_para_olhos == states.DORMINDO:
            olho_altura = 6

        offset_y_extra = 6 if self.expressao == states.TRISTE else 0

        olho_esq = pygame.Rect(0, 0, olho_largura, olho_altura)
        olho_dir = pygame.Rect(0, 0, olho_largura, olho_altura)
        olho_esq.center = (self.cx - espaco, self.cy - 20 + offset_y_extra)
        olho_dir.center = (self.cx + espaco, self.cy - 20 + offset_y_extra)

        for olho in (olho_esq, olho_dir):
            pygame.draw.rect(tela, config.PRETO, olho, border_radius=olho_largura // 2)

    def _desenhar_boca(self, tela):
        if self.falando:
            imagem_boca_falando = self._imagem_boca_falando_atual()
            if imagem_boca_falando:
                tela.blit(imagem_boca_falando, (0, 0))
            else:
                self._desenhar_boca_falando(tela)
            return

        imagem_boca = self.imagens.get(_NOMES_BOCA_PARADA.get(self.expressao))
        if imagem_boca:
            tela.blit(imagem_boca, (0, 0))
            return

        if self.expressao == states.FELIZ:
            self._desenhar_boca_curva(tela, para_cima=True)
        elif self.expressao == states.TRISTE:
            self._desenhar_boca_curva(tela, para_cima=False)
        elif self.expressao == states.SURPRESO:
            pygame.draw.circle(tela, config.PRETO, (self.cx, self.cy + 55), 16)
        elif self.expressao == states.DORMINDO:
            pygame.draw.line(tela, config.PRETO,
                              (self.cx - 18, self.cy + 55),
                              (self.cx + 18, self.cy + 55), 4)
        else:  # NEUTRO
            pygame.draw.line(tela, config.PRETO,
                              (self.cx - 24, self.cy + 55),
                              (self.cx + 24, self.cy + 55), 5)

    def _desenhar_boca_curva(self, tela, para_cima=True):
        largura = 60
        altura = 26
        rect = pygame.Rect(0, 0, largura, altura)
        rect.center = (self.cx, self.cy + 50 if para_cima else self.cy + 65)

        if para_cima:
            pygame.draw.arc(tela, config.PRETO, rect, math.pi, 2 * math.pi, 5)
        else:
            pygame.draw.arc(tela, config.PRETO, rect, 0, math.pi, 5)

    def _desenhar_boca_falando(self, tela):
        altura_max = 36
        altura = max(4, int(altura_max * self.nivel_boca))
        largura = 44

        rect = pygame.Rect(0, 0, largura, altura)
        rect.center = (self.cx, self.cy + 55)
        pygame.draw.ellipse(tela, config.PRETO, rect)
