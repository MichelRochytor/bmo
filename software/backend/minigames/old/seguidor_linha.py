"""
seguidor_linha.py
============================================
JOGO 2: Simulador de seguidor de linha.

Uma pista (linha preta sinuosa) rola na tela. O jogador usa
ESQUERDA/DIREITA pra corrigir a posição do robô em cima da linha,
simulando a lógica de "ficar em cima do sensor". Quanto mais tempo
em cima da linha, mais pontos. Se sair muito da linha, "perde"
(igual penalização na OBR).

Controles:
    ESQUERDA / DIREITA -> move o robô
    ESC -> volta ao menu de jogos
"""

import math
import random

import pygame

import config
from mascote import desenhar_roboap
import ranking

class JogoSeguidorLinha:
    VELOCIDADE_LATERAL = 260        # pixels/segundo (resposta mais ágil do robô)
    VELOCIDADE_SCROLL_INICIAL = 55  # pixels/segundo - começa bem mais devagar
    TOLERANCIA = 42                 # bem mais margem antes de penalizar
    TEMPO_GRACA_FORA = 2.5          # segundos fora da linha antes de "perder"

    def __init__(self, on_sair):
        self.on_sair = on_sair
        self.entrar()

    def entrar(self):
        self.robo_x = config.LARGURA / 2
        self.pontos = 0.0
        self.tempo_fora = 0.0
        self.fim = False
        self.ranking_salvo = False
        self.tempo_total = 0.0
        self._semente = random.uniform(0, 1000)

    def _velocidade_scroll(self):
        # Aumenta bem devagar com o tempo, sem virar punição
        return min(140, self.VELOCIDADE_SCROLL_INICIAL + self.tempo_total * 2.5)

    def _linha_x_em(self, y_mundo):
        """Calcula a posição X da linha (sinuosa e suave) pra uma dada altura 'do mundo'."""
        centro = config.LARGURA / 2
        amplitude = config.LARGURA * 0.20   # curva mais suave que antes
        return centro + amplitude * math.sin((y_mundo + self._semente) * 0.005)

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                self.on_sair()
                return
            if evento.type == pygame.JOYBUTTONDOWN:
                if evento.button in (6, 7): # START/SELECT
                    self.on_sair()
                    return

        if self.fim:
            for evento in eventos:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN:
                    self.entrar()
                if evento.type == pygame.JOYBUTTONDOWN and evento.button in (0, 1, 2, 3):
                    self.entrar()
            return

        teclas = pygame.key.get_pressed()
        joy_state = config.get_joystick_state(self.joysticks) if hasattr(self, 'joysticks') else {'left': False, 'right': False}
        
        if teclas[pygame.K_LEFT] or joy_state['left']:
            self.robo_x -= self.VELOCIDADE_LATERAL * dt
        if teclas[pygame.K_RIGHT] or joy_state['right']:
            self.robo_x += self.VELOCIDADE_LATERAL * dt
        self.robo_x = max(20, min(config.LARGURA - 20, self.robo_x))

        self.tempo_total += dt
        y_robo_mundo = self.tempo_total * self._velocidade_scroll()
        linha_x = self._linha_x_em(y_robo_mundo)
        distancia = abs(self.robo_x - linha_x)

        if distancia <= self.TOLERANCIA:
            self.pontos += dt * 10
            self.tempo_fora = 0.0
        else:
            self.tempo_fora += dt
            if self.tempo_fora > self.TEMPO_GRACA_FORA:
                self.fim = True

    def desenhar(self, tela):
        tela.fill((30, 30, 30))

        # Desenha a pista (linha sinuosa) "rolando" pra baixo
        y_base_mundo = self.tempo_total * self._velocidade_scroll()
        pontos_linha = []
        for offset_tela in range(-20, config.ALTURA + 20, 8):
            y_tela = offset_tela
            y_mundo = y_base_mundo + (config.ALTURA - y_tela)
            x = self._linha_x_em(y_mundo)
            pontos_linha.append((x, y_tela))

        if len(pontos_linha) >= 2:
            # Zona de tolerância (faixa clara em volta da linha, pra ficar visível o quanto pode errar)
            for px, py in pontos_linha[::3]:
                pygame.draw.circle(tela, (70, 70, 70), (int(px), int(py)), self.TOLERANCIA)
            pygame.draw.lines(tela, (240, 240, 240), False, pontos_linha, 10)

        # Robô (mascote) numa posição fixa na vertical, andando lateralmente
        desenhar_roboap(tela, self.robo_x, config.ALTURA - 60, escala=0.8,
                         fase_animacao=self.tempo_total * 1.5)

        fonte = pygame.font.SysFont(None, 22)
        fonte_pequena = pygame.font.SysFont(None, 16)

        placar = fonte.render(f"Pontos: {int(self.pontos)}", True, config.BRANCO)
        tela.blit(placar, (10, 10))

        dica = fonte_pequena.render("← → mexe o robô  |  ESC: sair", True, (180, 180, 180))
        tela.blit(dica, (10, config.ALTURA - 22))

        if self.fim:
            self._desenhar_fim(tela, fonte)

    def _desenhar_fim(self, tela, fonte):
        overlay = pygame.Surface((config.LARGURA, config.ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        tela.blit(overlay, (0, 0))

        msg = fonte.render("Saiu da linha!", True, (220, 90, 90))
        tela.blit(msg, msg.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 - 20)))

        placar = fonte.render(f"Pontuação final: {int(self.pontos)}", True, config.BRANCO)
        tela.blit(placar, placar.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 + 10)))

        dica = pygame.font.SysFont(None, 18).render(
            "ENTER: jogar de novo   |   ESC: voltar", True, (180, 180, 180))
        tela.blit(dica, dica.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 + 40)))


if __name__ == '__main__':
    import sys
    pygame.init()
    pygame.display.set_caption("BMO - Seguidor de Linha")
    tela = pygame.display.set_mode((config.LARGURA, config.ALTURA), pygame.FULLSCREEN | pygame.SCALED)
    relogio = pygame.time.Clock()
    
    def on_sair():
        pygame.quit()
        sys.exit()
        
    jogo = JogoSeguidorLinha(on_sair)
    jogo.joysticks = config.init_joystick()
    
    rodando = True
    while rodando:
        dt = relogio.tick(config.FPS) / 1000.0
        eventos = pygame.event.get()
        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
                
        jogo.atualizar(dt, eventos)
        jogo.desenhar(tela)
        pygame.display.flip()
        
        if jogo.fim and not jogo.ranking_salvo:
            ranking.mostrar_ranking_e_salvar(tela, relogio, "seguidor_linha", int(jogo.pontos))
            jogo.ranking_salvo = True
            jogo.entrar() # Restart the game after ranking
        
    pygame.quit()

