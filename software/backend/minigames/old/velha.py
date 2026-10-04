import pygame
import sys
import random
import time
import ranking

# Cores
BMO_GREEN = (156, 206, 168)
BMO_DARK_GREEN = (45, 90, 50)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Configurações da tela
import config
WIDTH, HEIGHT = config.LARGURA, config.ALTURA
LINE_WIDTH = 15
BOARD_ROWS, BOARD_COLS = 3, 3
SQUARE_SIZE = WIDTH // BOARD_COLS
CIRCLE_RADIUS = SQUARE_SIZE // 3
CIRCLE_WIDTH = 15
CROSS_WIDTH = 25
SPACE = SQUARE_SIZE // 4

def draw_lines(screen):
    # Linhas horizontais
    pygame.draw.line(screen, BMO_DARK_GREEN, (0, SQUARE_SIZE), (WIDTH, SQUARE_SIZE), LINE_WIDTH)
    pygame.draw.line(screen, BMO_DARK_GREEN, (0, 2 * SQUARE_SIZE), (WIDTH, 2 * SQUARE_SIZE), LINE_WIDTH)
    # Linhas verticais
    pygame.draw.line(screen, BMO_DARK_GREEN, (SQUARE_SIZE, 0), (SQUARE_SIZE, HEIGHT), LINE_WIDTH)
    pygame.draw.line(screen, BMO_DARK_GREEN, (2 * SQUARE_SIZE, 0), (2 * SQUARE_SIZE, HEIGHT), LINE_WIDTH)

def draw_figures(screen, board):
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == 1:
                pygame.draw.circle(screen, WHITE, (int(col * SQUARE_SIZE + SQUARE_SIZE // 2), int(row * SQUARE_SIZE + SQUARE_SIZE // 2)), CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif board[row][col] == 2:
                pygame.draw.line(screen, BLACK, (col * SQUARE_SIZE + SPACE, row * SQUARE_SIZE + SQUARE_SIZE - SPACE), (col * SQUARE_SIZE + SQUARE_SIZE - SPACE, row * SQUARE_SIZE + SPACE), CROSS_WIDTH)
                pygame.draw.line(screen, BLACK, (col * SQUARE_SIZE + SPACE, row * SQUARE_SIZE + SPACE), (col * SQUARE_SIZE + SQUARE_SIZE - SPACE, row * SQUARE_SIZE + SQUARE_SIZE - SPACE), CROSS_WIDTH)

def check_win(player, board):
    # Vertical win
    for col in range(BOARD_COLS):
        if board[0][col] == player and board[1][col] == player and board[2][col] == player:
            return True
    # Horizontal win
    for row in range(BOARD_ROWS):
        if board[row][0] == player and board[row][1] == player and board[row][2] == player:
            return True
    # Ascending diagonal win
    if board[2][0] == player and board[1][1] == player and board[0][2] == player:
        return True
    # Descending diagonal win
    if board[0][0] == player and board[1][1] == player and board[2][2] == player:
        return True
    return False

def check_draw(board):
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == 0:
                return False
    return True

def get_bmo_move(board):
    # AI simples: tentar achar uma jogada vencedora
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == 0:
                board[row][col] = 2
                if check_win(2, board):
                    board[row][col] = 0
                    return (row, col)
                board[row][col] = 0

    # Tentar bloquear o jogador (jogador 1)
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == 0:
                board[row][col] = 1
                if check_win(1, board):
                    board[row][col] = 0
                    return (row, col)
                board[row][col] = 0

    # Jogada aleatória
    empty_squares = []
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == 0:
                empty_squares.append((row, col))
    
    if empty_squares:
        return random.choice(empty_squares)
    return None

def draw_text_centered(screen, text, font, color, y_offset=0):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WIDTH//2, HEIGHT//2 + y_offset))
    
    # Desenhar um fundo escuro atrás do texto para leitura fácil
    bg_rect = pygame.Rect(text_rect.left - 10, text_rect.top - 5, text_rect.width + 20, text_rect.height + 10)
    pygame.draw.rect(screen, BMO_DARK_GREEN, bg_rect)
    screen.blit(text_surface, text_rect)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    pygame.display.set_caption('BMO - Jogo da Velha')
    
    font_large = pygame.font.SysFont("Courier", 40, bold=True)
    font_small = pygame.font.SysFont("Courier", 24, bold=True)

    clock = pygame.time.Clock()
    
    import config
    joysticks = config.init_joystick()

    ESTADO_MENU = 0
    ESTADO_JOGANDO = 1
    ESTADO_FIM = 2

    estado = ESTADO_MENU
    modo_vs_bmo = False
    board = [[0, 0, 0] for _ in range(3)]
    player = 1 # 1 = O (Branco), 2 = X (Preto)
    mensagem_fim = ""
    pontuacao_atual = 0
    bmo_turn_time = 0
    
    cursor_row, cursor_col = 1, 1
    joy_cooldown = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if estado == ESTADO_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        modo_vs_bmo = True
                        estado = ESTADO_JOGANDO
                        board = [[0, 0, 0] for _ in range(3)]
                        player = 1
                    elif event.key == pygame.K_2:
                        modo_vs_bmo = False
                        estado = ESTADO_JOGANDO
                        board = [[0, 0, 0] for _ in range(3)]
                        player = 1
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            elif estado == ESTADO_JOGANDO:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                # Jogada do Humano
                if event.type == pygame.MOUSEBUTTONDOWN and (player == 1 or not modo_vs_bmo):
                    mouseX = event.pos[0]
                    mouseY = event.pos[1]

                    clicked_row = mouseY // SQUARE_SIZE
                    clicked_col = mouseX // SQUARE_SIZE

                    if board[clicked_row][clicked_col] == 0:
                        board[clicked_row][clicked_col] = player

                        if check_win(player, board):
                            if modo_vs_bmo:
                                mensagem_fim = "Você Venceu!"
                                pontuacao_atual = 100
                            else:
                                mensagem_fim = f"Jogador {player} Venceu!"
                                pontuacao_atual = 100
                            estado = ESTADO_FIM
                        elif check_draw(board):
                            mensagem_fim = "Deu Velha!"
                            pontuacao_atual = 50
                            estado = ESTADO_FIM
                        else:
                            player = 2 if player == 1 else 1
                            if modo_vs_bmo and player == 2:
                                bmo_turn_time = pygame.time.get_ticks()

            elif estado == ESTADO_FIM:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        ranking.mostrar_ranking_e_salvar(screen, clock, "velha", pontuacao_atual)
                        estado = ESTADO_MENU
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button in (0, 1, 2, 3):
                        ranking.mostrar_ranking_e_salvar(screen, clock, "velha", pontuacao_atual)
                        estado = ESTADO_MENU
                    if event.button in (6, 7):
                        pygame.quit()
                        sys.exit()

        joy_state = config.get_joystick_state(joysticks)
        if joy_cooldown > 0:
            joy_cooldown -= 1
        else:
            if estado == ESTADO_MENU:
                if joy_state['action'] or joy_state['action2']: # Botão para VS BMO
                    modo_vs_bmo = True
                    estado = ESTADO_JOGANDO
                    board = [[0, 0, 0] for _ in range(3)]
                    player = 1
                    joy_cooldown = 15
                elif joy_state['action3']: # Outro Botão para VS Amigo
                    modo_vs_bmo = False
                    estado = ESTADO_JOGANDO
                    board = [[0, 0, 0] for _ in range(3)]
                    player = 1
                    joy_cooldown = 15
            elif estado == ESTADO_JOGANDO and (player == 1 or not modo_vs_bmo):
                if joy_state['up'] and cursor_row > 0: cursor_row -= 1; joy_cooldown = 10
                if joy_state['down'] and cursor_row < 2: cursor_row += 1; joy_cooldown = 10
                if joy_state['left'] and cursor_col > 0: cursor_col -= 1; joy_cooldown = 10
                if joy_state['right'] and cursor_col < 2: cursor_col += 1; joy_cooldown = 10
                
                if (joy_state['action'] or joy_state['action2']) and board[cursor_row][cursor_col] == 0:
                    board[cursor_row][cursor_col] = player
                    joy_cooldown = 20
                    if check_win(player, board):
                        if modo_vs_bmo:
                            mensagem_fim = "Você Venceu!"
                            pontuacao_atual = 100
                        else:
                            mensagem_fim = f"Jogador {player} Venceu!"
                            pontuacao_atual = 100
                        estado = ESTADO_FIM
                    elif check_draw(board):
                        mensagem_fim = "Deu Velha!"
                        pontuacao_atual = 50
                        estado = ESTADO_FIM
                    else:
                        player = 2 if player == 1 else 1
                        if modo_vs_bmo and player == 2:
                            bmo_turn_time = pygame.time.get_ticks()

        # Lógica do turno do BMO
        if estado == ESTADO_JOGANDO and modo_vs_bmo and player == 2:
            if pygame.time.get_ticks() - bmo_turn_time > 800: # 800ms de pausa para simular pensamento
                move = get_bmo_move(board)
                if move:
                    row, col = move
                    board[row][col] = 2

                    if check_win(2, board):
                        mensagem_fim = "BMO Venceu!"
                        pontuacao_atual = 0
                        estado = ESTADO_FIM
                    elif check_draw(board):
                        mensagem_fim = "Deu Velha!"
                        pontuacao_atual = 50
                        estado = ESTADO_FIM
                    else:
                        player = 1

        # Desenho
        screen.fill(BMO_GREEN)

        if estado == ESTADO_MENU:
            draw_text_centered(screen, "ESCOLHA O MODO:", font_large, WHITE, -50)
            draw_text_centered(screen, "[1] Jogar vs BMO", font_small, WHITE, 10)
            draw_text_centered(screen, "[2] Jogar vs Amigo", font_small, WHITE, 50)

        elif estado == ESTADO_JOGANDO or estado == ESTADO_FIM:
            draw_lines(screen)
            draw_figures(screen, board)
            
            if estado == ESTADO_JOGANDO and (player == 1 or not modo_vs_bmo):
                # Desenha cursor
                cx = cursor_col * SQUARE_SIZE
                cy = cursor_row * SQUARE_SIZE
                s_size = SQUARE_SIZE
                pygame.draw.rect(screen, (200, 200, 50), (cx+5, cy+5, s_size-10, s_size-10), 4, border_radius=10)

            if estado == ESTADO_FIM:
                # Fundo translúcido para o texto
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill(BMO_GREEN)
                screen.blit(overlay, (0, 0))
                draw_text_centered(screen, mensagem_fim, font_large, WHITE, -20)
                draw_text_centered(screen, "Pressione 'R' para o Menu", font_small, WHITE, 30)

        pygame.display.update()
        clock.tick(60)

if __name__ == '__main__':
    main()
