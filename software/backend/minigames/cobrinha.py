import pygame
import sys
import random
import pickle
import os
import ranking

# Inicializa o Pygame
pygame.init()

# Cores (Paleta BMO)
BMO_BG = (156, 206, 168)
BMO_SNAKE = (45, 90, 50)
BMO_APPLE = (200, 50, 50)
BMO_TEXT = (20, 40, 20)
BMO_OVERLAY = (156, 206, 168)

# Configurações de Tela e Grade
import config
WIDTH, HEIGHT = config.LARGURA, config.ALTURA
CELL_SIZE = config.SNAKE_CELL_SIZE
FPS = config.SNAKE_FPS
GRID_COLS = max(8, WIDTH // CELL_SIZE)
GRID_ROWS = max(8, HEIGHT // CELL_SIZE)
GRID_X = (WIDTH - GRID_COLS * CELL_SIZE) // 2
GRID_Y = (HEIGHT - GRID_ROWS * CELL_SIZE) // 2



screen = pygame.display.set_mode((WIDTH, HEIGHT), config.display_flags(pygame))
pygame.display.set_caption("BMO - Jogo da Cobrinha")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Courier", 64, bold=True)
font_large = pygame.font.SysFont("Courier", 32, bold=True)

class Snake:
    def __init__(self):
        centro_x, centro_y = GRID_COLS // 2, GRID_ROWS // 2
        self.body = [(centro_x, centro_y), (centro_x - 1, centro_y), (centro_x - 2, centro_y)]
        self.direction = (1, 0)
        self.grow = False

    def move(self):
        head_x, head_y = self.body[0]
        dir_x, dir_y = self.direction
        new_head = (head_x + dir_x, head_y + dir_y)
        
        self.body.insert(0, new_head)
        if not self.grow:
            self.body.pop()
        else:
            self.grow = False

    def draw(self, surface):
        for segment in self.body:
            rect = pygame.Rect(GRID_X + segment[0] * CELL_SIZE, GRID_Y + segment[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(surface, BMO_SNAKE, rect)
            pygame.draw.rect(surface, BMO_BG, rect, 1) # Borda

class Apple:
    def __init__(self):
        self.randomize()

    def randomize(self):
        self.position = (random.randint(0, GRID_COLS - 1), random.randint(0, GRID_ROWS - 1))

    def draw(self, surface):
        rect = pygame.Rect(GRID_X + self.position[0] * CELL_SIZE, GRID_Y + self.position[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(surface, BMO_APPLE, rect)

def main():
    joysticks = config.init_joystick()
    snake = Snake()
    apple = Apple()
    score = 0
    game_over = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if not game_over:
                    if (event.key == pygame.K_UP or event.key == pygame.K_w) and snake.direction != (0, 1):
                        snake.direction = (0, -1)
                    elif (event.key == pygame.K_DOWN or event.key == pygame.K_s) and snake.direction != (0, -1):
                        snake.direction = (0, 1)
                    elif (event.key == pygame.K_LEFT or event.key == pygame.K_a) and snake.direction != (1, 0):
                        snake.direction = (-1, 0)
                    elif (event.key == pygame.K_RIGHT or event.key == pygame.K_d) and snake.direction != (-1, 0):
                        snake.direction = (1, 0)
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (6, 7): # START/SELECT
                    pygame.quit()
                    sys.exit()

        joy_state = config.get_joystick_state(joysticks)
        if not game_over:
            if joy_state['up'] and snake.direction != (0, 1):
                snake.direction = (0, -1)
            elif joy_state['down'] and snake.direction != (0, -1):
                snake.direction = (0, 1)
            elif joy_state['left'] and snake.direction != (1, 0):
                snake.direction = (-1, 0)
            elif joy_state['right'] and snake.direction != (-1, 0):
                snake.direction = (1, 0)

        if not game_over:
            snake.move()

            # Checar colisão com a maçã
            if snake.body[0] == apple.position:
                snake.grow = True
                apple.randomize()
                score += 1

            # Checar colisão com paredes
            head_x, head_y = snake.body[0]
            if head_x < 0 or head_x >= GRID_COLS or head_y < 0 or head_y >= GRID_ROWS:
                game_over = True

            # Checar colisão com o próprio corpo
            if snake.body[0] in snake.body[1:]:
                game_over = True

        screen.fill(BMO_BG)
        
        apple.draw(screen)
        snake.draw(screen)

        if game_over:
            snake = Snake()
            apple.randomize()
            score = 0
            game_over = False

        else:
            score_text = font.render(f"Pontos: {score}", True, BMO_TEXT)
            screen.blit(score_text, (100, 10))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
