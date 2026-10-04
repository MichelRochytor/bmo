import pygame
import math
import random
import sys

pygame.init()

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Define dimensões do quadro de desenho (tela cheia dinâmica)
WIDTH = config.LARGURA
HEIGHT = config.ALTURA
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Codificadoras Flappy Game")

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

# Cores utilizadas no jogo original
COLOR_BG = (203, 108, 230)      # #cb6ce6
COLOR_PIPES = (255, 102, 196)   # #ff66c4
COLOR_BALL = (255, 255, 255)    # white
COLOR_BALL_COL = (255, 0, 0)    # red
COLOR_TEXT = (255, 255, 255)    # white

# Variáveis do cenário
qtdPipes = math.ceil(WIDTH / 260)
espacoEntrePipes = HEIGHT * 0.70

class GameState:
    def __init__(self):
        self.reset_to_start()

    def reset_to_start(self):
        self.state = "START"
        self.bolinhaPosicaoY = HEIGHT / 2 - 14
        self.bolinhaPosicaoX = WIDTH / 2 - 20
        self.pontuacao = 0
        self.start = False
        self.colisao = False
        self.jump = False
        self.tempo = 0
        self.tempoPulo = 0
        self.posicaoOriginalY = self.bolinhaPosicaoY
        self.incremento = 10
        self.alturaPipe = [0] * qtdPipes
        self.posicaoPipe = [0] * qtdPipes
        for i in range(qtdPipes):
            self.atualiza_cenario(i)

    def atualiza_cenario(self, indice):
        self.alturaPipe[indice] = round(random.random() * espacoEntrePipes)
        if not self.start:
            self.posicaoPipe[indice] = WIDTH + 260 * indice

    def start_game(self):
        self.state = "PLAYING"
        self.pontuacao = 0
        self.start = True
        self.colisao = False
        self.jump = True
        self.tempoPulo = self.tempo

    def update(self):
        self.tempo += 10
        
        if self.state == "START":
            # A tela de início original atualiza a 60ms (nós rodamos a 10ms por frame)
            # Então a cada 6 frames (~60ms) nós movemos a bolinha
            if self.tempo % 60 == 0:
                if self.bolinhaPosicaoY > self.posicaoOriginalY + 10:
                    self.incremento = -10
                elif self.bolinhaPosicaoY < self.posicaoOriginalY - 10:
                    self.incremento = 10
                self.bolinhaPosicaoY += self.incremento
                
        elif self.state == "PLAYING":
            if self.jump:
                # decrementa a posição da bolinha de 4 em 4 (sobe)
                self.bolinhaPosicaoY -= 4
                # quando passa 240ms, a bolinha volta a descer
                if self.tempo - self.tempoPulo > 240:
                    self.jump = False
                    self.tempoPulo = 0
            elif self.colisao:
                self.bolinhaPosicaoY += 6
            else:
                self.bolinhaPosicaoY += 4

            if not self.colisao:
                self.verifica_colisao()
                self.calcula_pontuacao()

            # Move e reseta pipes
            for i in range(qtdPipes):
                if not self.colisao:
                    self.posicaoPipe[i] -= 1
                    
                # se o pipe saiu da tela, coloca de volta no início
                if self.posicaoPipe[i] < -80:
                    self.posicaoPipe[i] = WIDTH
                    self.atualiza_cenario(i)

            # Bolinha caiu muito além da tela
            if self.bolinhaPosicaoY > HEIGHT + 20:
                self.reset_to_start()

    def verifica_colisao(self):
        for i in range(qtdPipes):
            if (self.posicaoPipe[i] < self.bolinhaPosicaoX + 20 and 
                self.bolinhaPosicaoX - 20 < self.posicaoPipe[i] + 80):
                if (self.bolinhaPosicaoY - 20 < espacoEntrePipes - self.alturaPipe[i] or 
                    self.bolinhaPosicaoY + 20 > HEIGHT - self.alturaPipe[i]):
                    self.jump = False
                    self.colisao = True

    def calcula_pontuacao(self):
        for i in range(qtdPipes):
            # se a bolinha ultrapassa um dos pipes (mesma lógica do original)
            if self.bolinhaPosicaoX == self.posicaoPipe[i] + 80:
                self.pontuacao += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        # Desenha os pipes (apenas quando o jogo iniciou, para corresponder ao original)
        # O original também desenha na tela de inicio?
        # JS: No desenhaTelaInicio ele NÃO chama desenhaCenario. Ele desenha apenas bg, msg e bolinha.
        if self.state == "PLAYING":
            for i in range(qtdPipes):
                pipe_x = self.posicaoPipe[i]
                
                # Pipe de cima
                rect_cima = pygame.Rect(pipe_x, 0, 80, espacoEntrePipes - self.alturaPipe[i])
                pygame.draw.rect(surface, COLOR_PIPES, rect_cima)
                pygame.draw.rect(surface, (0, 0, 0), rect_cima, 1) # contorno (stroke do original)
                
                # Pipe de baixo
                rect_baixo = pygame.Rect(pipe_x, HEIGHT - self.alturaPipe[i], 80, self.alturaPipe[i])
                pygame.draw.rect(surface, COLOR_PIPES, rect_baixo)
                pygame.draw.rect(surface, (0, 0, 0), rect_baixo, 1) # contorno (stroke do original)
        
        # Desenha a bolinha
        color = COLOR_BALL_COL if self.colisao else COLOR_BALL
        pygame.draw.circle(surface, color, (int(self.bolinhaPosicaoX), int(self.bolinhaPosicaoY)), 20)

        # Desenha textos de score e inicio
        if self.state == "START":
            text = font.render("Press space to start...", True, COLOR_TEXT)
            surface.blit(text, (WIDTH/2 - 100, HEIGHT/2 + 80))
            
        elif self.state == "PLAYING":
            color_score = COLOR_BALL_COL if self.colisao else COLOR_TEXT
            score_text = font.render(f"Score: {self.pontuacao}", True, color_score)
            surface.blit(score_text, (WIDTH - 120, 30))

def main():
    joysticks = config.init_joystick()
    game = GameState()

    # Loop principal
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_SPACE:
                    if game.state == "START":
                        game.start_game()
                    else:
                        if not game.colisao:
                            game.jump = True
                            game.tempoPulo = game.tempo
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (6, 7): # START/SELECT
                    pygame.quit()
                    sys.exit()
                if event.button in (0, 1, 2, 3):
                    if game.state == "START":
                        game.start_game()
                    else:
                        if not game.colisao:
                            game.jump = True
                            game.tempoPulo = game.tempo

        game.update()
        game.draw(screen)
        
        pygame.display.flip()
        clock.tick(100) # O intervalo original era de 10ms, resultando em ~100 FPS

if __name__ == "__main__":
    main()
