import pygame
import sys
import os
import ranking

# Inicializa o Pygame
pygame.init()

# Cores (Paleta BMO)
BMO_BG = (156, 206, 168)
BMO_PADDLE = (45, 90, 50)
BMO_BALL = (200, 50, 50)
BMO_BLOCK = (45, 90, 50)
BMO_TEXT = (20, 40, 20)
BMO_OVERLAY = (156, 206, 168)

# Configurações de Tela
import config
WIDTH, HEIGHT = config.LARGURA, config.ALTURA
FPS = config.FPS

screen = pygame.display.set_mode((WIDTH, HEIGHT), config.display_flags(pygame))
pygame.display.set_caption("BMO - Quebra-Blocos")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Courier", 24, bold=True)
font_large = pygame.font.SysFont("Courier", 32, bold=True)

class Paddle:
    def __init__(self):
        self.width = 100
        self.height = 15
        self.x = (WIDTH - self.width) // 2
        self.y = HEIGHT - 40
        self.speed = 8
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def move(self, dx):
        self.rect.x += dx * self.speed
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

    def draw(self, surface):
        pygame.draw.rect(surface, BMO_PADDLE, self.rect)

class Ball:
    def __init__(self):
        self.radius = 8
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.dx = 4
        self.dy = -4
        self.rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius*2, self.radius*2)

    def move(self):
        self.rect.x += self.dx
        self.rect.y += self.dy

        # Quicar nas paredes laterais
        if self.rect.left <= 0 or self.rect.right >= WIDTH:
            self.dx *= -1
            # Para evitar que fique presa nas bordas
            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > WIDTH: self.rect.right = WIDTH
            
        # Quicar no teto
        if self.rect.top <= 0:
            self.dy *= -1
            self.rect.top = 0

    def draw(self, surface):
        pygame.draw.circle(surface, BMO_BALL, self.rect.center, self.radius)

class Block:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.active = True

    def draw(self, surface):
        if self.active:
            pygame.draw.rect(surface, BMO_BLOCK, self.rect)
            pygame.draw.rect(surface, BMO_BG, self.rect, 2) # Borda interna pra separar blocos

def create_blocks(rows, cols):
    blocks = []
    block_width = WIDTH // cols
    block_height = 30
    for row in range(rows):
        for col in range(cols):
            b = Block(col * block_width, row * block_height + 50, block_width, block_height)
            blocks.append(b)
    return blocks

def main():
    joysticks = config.init_joystick()
    paddle = Paddle()
    ball = Ball()
    blocks = create_blocks(5, 10)
    
    score = 0
    game_over = False
    victory = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (6, 7): # START/SELECT usually
                    pygame.quit()
                    sys.exit()

        keys = pygame.key.get_pressed()
        joy_state = config.get_joystick_state(joysticks)
        if not game_over and not victory:
            if keys[pygame.K_LEFT] or keys[pygame.K_a] or joy_state['left']:
                paddle.move(-1)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d] or joy_state['right']:
                paddle.move(1)

            ball.move()

            # Colisão bola com paddle
            if ball.rect.colliderect(paddle.rect) and ball.dy > 0:
                ball.dy *= -1
                
                # Controle avançado de ângulo: a direção e velocidade horizontal (dx)
                # mudam baseadas em onde a bolinha bate no paddle.
                # offset vai de -1 (borda esquerda) até 1 (borda direita)
                offset = (ball.rect.centerx - paddle.rect.centerx) / (paddle.rect.width / 2)
                
                # Velocidade máxima horizontal
                velocidade_max_x = 6
                ball.dx = offset * velocidade_max_x

            # Colisão bola com blocos
            for b in blocks:
                if b.active and ball.rect.colliderect(b.rect):
                    b.active = False
                    ball.dy *= -1
                    score += 10
                    break # Apenas um bloco quebrado por frame

            # Bola cai no abismo
            if ball.rect.bottom > HEIGHT:
                game_over = True

            # Condição de Vitória
            if all(not b.active for b in blocks):
                victory = True

        screen.fill(BMO_BG)

        for b in blocks:
            b.draw(screen)
        
        paddle.draw(screen)
        ball.draw(screen)

        # Textos superiores
        score_text = font.render(f"Pontos: {score}", True, BMO_TEXT)
        screen.blit(score_text, (10, 10))

        if game_over or victory:
            ranking.mostrar_ranking_e_salvar(screen, clock, "blocos", score)
            paddle = Paddle()
            ball = Ball()
            blocks = create_blocks(5, 10)
            score = 0
            game_over = False
            victory = False

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
