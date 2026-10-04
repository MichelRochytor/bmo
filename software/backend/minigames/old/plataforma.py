"""
plataforma.py
============================================
JOGO 4: Plataforma — estilo Super Mario, com o cenário do UTFPR
(8-bit) rolando ao fundo e o ROBOAP em pixel art como personagem.

Controles:
    ESPAÇO / SETA CIMA   -> pular
    SETA BAIXO            -> abaixar (desviar dos drones)
    ESC -> volta ao menu de jogos
"""
import random
import pygame

import config
import imagens
import ranking


CHAO_Y_OFFSET = 56


class Obstaculo:
    def __init__(self, x, tipo):
        self.x = x
        self.tipo = tipo  # "espinho", "drone" ou "moeda"
        self.coletado = False


class Particula:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vy = random.uniform(-120, -40)
        self.vx = random.uniform(-40, 40)
        self.vida = 0.5


class JogoPlataforma:
    GRAVIDADE = 1500
    FORCA_PULO = 480
    VELOCIDADE_INICIAL = 200

    def __init__(self, on_sair):
        self.on_sair = on_sair
        self._fundo_cache = None
        self.entrar()

    def entrar(self):
        self.chao_y = config.ALTURA - CHAO_Y_OFFSET
        self.robo_x = 90
        self.robo_y = self.chao_y
        self.velocidade_y = 0
        self.no_chao = True
        self.abaixado = False

        self.velocidade_jogo = self.VELOCIDADE_INICIAL
        self.distancia = 0.0
        self.scroll_fundo = 0.0
        self.moedas = 0
        self.combo = 0
        self.melhor_combo = 0
        self.tempo = 0.0
        self.fim = False
        self.ranking_salvo = False

        self.obstaculos = []
        self.particulas = []
        self._proximo_spawn = 0.6

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self.on_sair()
                    return
                if self.fim:
                    if evento.key == pygame.K_RETURN:
                        self.entrar()
                    continue
                if evento.key in (pygame.K_SPACE, pygame.K_UP) and self.no_chao:
                    self.velocidade_y = -self.FORCA_PULO
                    self.no_chao = False
            
            if evento.type == pygame.JOYBUTTONDOWN:
                if evento.button in (6, 7): # START/SELECT
                    self.on_sair()
                    return
                if self.fim:
                    if evento.button in (0, 1, 2, 3):
                        self.entrar()
                    continue
                if evento.button in (0, 1, 2, 3) and self.no_chao:
                    self.velocidade_y = -self.FORCA_PULO
                    self.no_chao = False

        if self.fim:
            return

        teclas = pygame.key.get_pressed()
        joy_state = config.get_joystick_state(self.joysticks) if hasattr(self, 'joysticks') else {'down': False}
        self.abaixado = (teclas[pygame.K_DOWN] or joy_state['down']) and self.no_chao

        self.tempo += dt
        self.velocidade_jogo = self.VELOCIDADE_INICIAL + self.tempo * 9
        self.distancia += self.velocidade_jogo * dt
        self.scroll_fundo += self.velocidade_jogo * 0.5 * dt  # paralaxe: fundo anda mais devagar

        self.velocidade_y += self.GRAVIDADE * dt
        self.robo_y += self.velocidade_y * dt
        if self.robo_y >= self.chao_y:
            self.robo_y = self.chao_y
            self.velocidade_y = 0
            self.no_chao = True

        self._atualizar_obstaculos(dt)
        self._atualizar_particulas(dt)
        self._checar_colisoes()

    def _atualizar_obstaculos(self, dt):
        self._proximo_spawn -= dt
        if self._proximo_spawn <= 0:
            sorteio = random.random()
            if sorteio < 0.32:
                tipo = "moeda"
            elif sorteio < 0.66:
                tipo = "espinho"
            else:
                tipo = "drone"
            self.obstaculos.append(Obstaculo(config.LARGURA + 30, tipo))
            self._proximo_spawn = random.uniform(0.75, 1.4)

        for obs in self.obstaculos:
            obs.x -= self.velocidade_jogo * dt

        self.obstaculos = [o for o in self.obstaculos if o.x > -30]

    def _atualizar_particulas(self, dt):
        for p in self.particulas:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 600 * dt
            p.vida -= dt
        self.particulas = [p for p in self.particulas if p.vida > 0]

    def _checar_colisoes(self):
        raio_robo = 24
        for obs in self.obstaculos:
            distancia_x = abs(obs.x - self.robo_x)
            if distancia_x > raio_robo:
                continue

            if obs.tipo == "espinho":
                if self.robo_y > self.chao_y - 18:
                    self.fim = True
            elif obs.tipo == "drone":
                if not self.abaixado:
                    self.fim = True
            elif obs.tipo == "moeda" and not obs.coletado:
                obs.coletado = True
                self.combo += 1
                self.melhor_combo = max(self.melhor_combo, self.combo)
                ganho = 1 + self.combo // 3
                self.moedas += ganho
                for _ in range(6):
                    self.particulas.append(Particula(obs.x, self.chao_y - 50))

    def desenhar(self, tela):
        self._desenhar_fundo(tela)

        for obs in self.obstaculos:
            self._desenhar_obstaculo(tela, obs)

        for p in self.particulas:
            pygame.draw.circle(tela, config.BOTAO_AMARELO, (int(p.x), int(p.y)), 3)

        self._desenhar_robo(tela)
        self._desenhar_hud(tela)

        if self.fim:
            self._desenhar_fim(tela)

    def _desenhar_fundo(self, tela):
        """Fundo do UTFPR estilo 8-bit, rolando em paralaxe (tipo Super Mario)."""
        original = imagens.carregar("fundo_plataforma.png")
        if original is None:
            tela.fill((92, 148, 252))  # azul clássico de céu 8-bit, como fallback
            return

        if self._fundo_cache is None:
            altura_alvo = config.ALTURA
            proporcao = original.get_width() / original.get_height()
            largura_alvo = int(altura_alvo * proporcao)
            self._fundo_cache = pygame.transform.smoothscale(original, (largura_alvo, altura_alvo))

        img = self._fundo_cache
        largura_img = img.get_width()
        offset = int(self.scroll_fundo) % largura_img

        x = -offset
        while x < config.LARGURA:
            tela.blit(img, (x, 0))
            x += largura_img

    def _desenhar_robo(self, tela):
        altura_robo = self.robo_y - 6 + (14 if self.abaixado else 0)
        largura_alvo = 56 if not self.abaixado else 64
        img = imagens.escalar_para_largura("roboap_pixel.png", largura_alvo)
        if img is not None:
            rect = img.get_rect(center=(int(self.robo_x), int(altura_robo)))
            tela.blit(img, rect)

    def _desenhar_obstaculo(self, tela, obs):
        y_base = self.chao_y + 18
        if obs.tipo == "espinho":
            pontos = [(obs.x - 14, y_base), (obs.x, y_base - 28), (obs.x + 14, y_base)]
            pygame.draw.polygon(tela, (235, 235, 235), pontos)
            pygame.draw.polygon(tela, (60, 60, 60), pontos, 2)
        elif obs.tipo == "drone":
            y = self.chao_y - 60
            pygame.draw.rect(tela, (90, 90, 100), (obs.x - 16, y - 6, 32, 10), border_radius=4)
            pygame.draw.circle(tela, config.BOTAO_ROSA, (int(obs.x), int(y) - 8), 4)
            pygame.draw.line(tela, (150, 150, 150), (obs.x - 20, y - 1), (obs.x - 28, y - 10), 2)
            pygame.draw.line(tela, (150, 150, 150), (obs.x + 20, y - 1), (obs.x + 28, y - 10), 2)
        else:
            if not obs.coletado:
                pygame.draw.circle(tela, config.BOTAO_AMARELO, (int(obs.x), int(self.chao_y - 50)), 9)
                pygame.draw.circle(tela, (200, 170, 30), (int(obs.x), int(self.chao_y - 50)), 9, 2)

    def _desenhar_hud(self, tela):
        fonte = pygame.font.SysFont(None, 20, bold=True)
        sombra = fonte.render(f"Moedas: {self.moedas}   Distância: {int(self.distancia)}m", True, (0, 0, 0))
        placar = fonte.render(f"Moedas: {self.moedas}   Distância: {int(self.distancia)}m",
                               True, config.BRANCO)
        tela.blit(sombra, (11, 11))
        tela.blit(placar, (10, 10))

        if self.combo > 1:
            fonte_combo = pygame.font.SysFont(None, 18, bold=True)
            combo_txt = fonte_combo.render(f"Combo x{self.combo}!", True, config.BOTAO_AMARELO)
            tela.blit(combo_txt, (10, 32))

        fonte_pequena = pygame.font.SysFont(None, 16)
        dica = fonte_pequena.render("ESPAÇO: pula   ↓: abaixa   ESC: sair", True, config.BRANCO)
        sombra_dica = fonte_pequena.render("ESPAÇO: pula   ↓: abaixa   ESC: sair", True, (0, 0, 0))
        tela.blit(sombra_dica, (11, config.ALTURA - 21))
        tela.blit(dica, (10, config.ALTURA - 22))

    def _desenhar_fim(self, tela):
        overlay = pygame.Surface((config.LARGURA, config.ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        tela.blit(overlay, (0, 0))

        fonte = pygame.font.SysFont(None, 24)
        msg = fonte.render("Bateu no obstáculo!", True, config.BOTAO_ROSA)
        tela.blit(msg, msg.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 - 26)))

        placar = fonte.render(f"Moedas: {self.moedas}   |   Melhor combo: x{self.melhor_combo}",
                               True, config.BRANCO)
        tela.blit(placar, placar.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 + 4)))

        dica = pygame.font.SysFont(None, 18).render(
            "ENTER: jogar de novo   |   ESC: voltar", True, (220, 220, 220))
        tela.blit(dica, dica.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 + 34)))


if __name__ == '__main__':
    import sys
    pygame.init()
    pygame.display.set_caption("BMO - Plataforma")
    tela = pygame.display.set_mode((config.LARGURA, config.ALTURA), pygame.FULLSCREEN | pygame.SCALED)
    relogio = pygame.time.Clock()
    
    def on_sair():
        pygame.quit()
        sys.exit()
        
    jogo = JogoPlataforma(on_sair)
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
            score_final = int(jogo.distancia) + (jogo.moedas * 50)
            ranking.mostrar_ranking_e_salvar(tela, relogio, "plataforma", score_final)
            jogo.ranking_salvo = True
            jogo.entrar()
        
    pygame.quit()

