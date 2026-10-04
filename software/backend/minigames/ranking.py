import json
import os
import pygame
import config

RANKING_FILE = os.path.join(config.BASE_DIR, "ranking.json")

DEADZONE = 0.5
REPEAT_DELAY = 180


def carregar_ranking():
    if not os.path.exists(RANKING_FILE):
        return {}

    try:
        with open(RANKING_FILE, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return {}


def salvar_ranking(dados):
    with open(RANKING_FILE, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)


def adicionar_pontuacao(game_name, nome, pontuacao):
    dados = carregar_ranking()

    if game_name not in dados:
        dados[game_name] = []

    dados[game_name].append({
        "nome": nome,
        "pontuacao": pontuacao
    })

    dados[game_name] = sorted(
        dados[game_name],
        key=lambda score: score["pontuacao"],
        reverse=True
    )[:5]

    salvar_ranking(dados)


def iniciar_controles():
    pygame.joystick.init()
    controles = []

    for index in range(pygame.joystick.get_count()):
        controle = pygame.joystick.Joystick(index)
        controle.init()
        controles.append(controle)

    return controles


def direcao_do_controle(controles):
    for controle in controles:
        # D-pad
        if controle.get_numhats() > 0:
            hat_x, hat_y = controle.get_hat(0)

            if hat_y > 0:
                return "up"
            if hat_y < 0:
                return "down"
            if hat_x < 0:
                return "left"
            if hat_x > 0:
                return "right"

        # Left analog stick
        if controle.get_numaxes() >= 2:
            axis_x = controle.get_axis(0)
            axis_y = controle.get_axis(1)

            if axis_y < -DEADZONE:
                return "up"
            if axis_y > DEADZONE:
                return "down"
            if axis_x < -DEADZONE:
                return "left"
            if axis_x > DEADZONE:
                return "right"

    return None


def mostrar_ranking_e_salvar(tela, relogio, game_name, pontuacao, max_letras=3, presenter=None):
    largura, altura = tela.get_size()
    dados = carregar_ranking()
    top_scores = dados.get(game_name, [])

    precisa_digitar = (
        pontuacao is not None
        and (len(top_scores) < 5 or pontuacao > top_scores[-1]["pontuacao"])
    )

    nome_atual = ["A"] * max_letras
    indice_letra = 0

    fonte_titulo = pygame.font.SysFont(None, 48, bold=True)
    fonte_normal = pygame.font.SysFont(None, 36)

    controles = iniciar_controles()
    ultimo_movimento = 0
    rodando = True

    def mudar_letra(valor):
        codigo = ord(nome_atual[indice_letra])
        nome_atual[indice_letra] = chr((codigo - 65 + valor) % 26 + 65)

    def confirmar_nome():
        nonlocal precisa_digitar, dados, top_scores

        adicionar_pontuacao(
            game_name,
            "".join(nome_atual),
            pontuacao
        )

        precisa_digitar = False
        dados = carregar_ranking()
        top_scores = dados.get(game_name, [])

    while rodando:
        relogio.tick(config.FPS)
        agora = pygame.time.get_ticks()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

            if evento.type == pygame.KEYDOWN:
                if precisa_digitar:
                    if evento.key == pygame.K_UP:
                        mudar_letra(1)
                    elif evento.key == pygame.K_DOWN:
                        mudar_letra(-1)
                    elif evento.key == pygame.K_LEFT:
                        indice_letra = max(0, indice_letra - 1)
                    elif evento.key == pygame.K_RIGHT:
                        indice_letra = min(
                            max_letras - 1,
                            indice_letra + 1
                        )
                    elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                        confirmar_nome()
                    elif evento.key == pygame.K_ESCAPE:
                        rodando = False

                elif evento.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                    pygame.K_ESCAPE
                ):
                    rodando = False

            # Any main action button confirms/saves.
            if evento.type == pygame.JOYBUTTONDOWN:
                if evento.button in (0, 1, 2, 3):
                    if precisa_digitar:
                        confirmar_nome()
                    else:
                        rodando = False

                # Start or Select exits the ranking.
                elif evento.button in (6, 7):
                    rodando = False

        # Allows holding D-pad / analog stick with a short repeat delay.
        direction = direcao_do_controle(controles)

        if (
            precisa_digitar
            and direction is not None
            and agora - ultimo_movimento >= REPEAT_DELAY
        ):
            if direction == "up":
                mudar_letra(1)
            elif direction == "down":
                mudar_letra(-1)
            elif direction == "left":
                indice_letra = max(0, indice_letra - 1)
            elif direction == "right":
                indice_letra = min(max_letras - 1, indice_letra + 1)

            ultimo_movimento = agora

        tela.fill(config.VERDE_CORPO)

        if precisa_digitar:
            titulo = fonte_titulo.render(
                "NOVO RECORDE!",
                True,
                config.BOTAO_ROSA
            )
            tela.blit(
                titulo,
                titulo.get_rect(center=(largura // 2, 100))
            )

            pontos = fonte_normal.render(
                f"Sua Pontuação: {pontuacao}",
                True,
                config.BRANCO
            )
            tela.blit(
                pontos,
                pontos.get_rect(center=(largura // 2, 150))
            )

            espaco = 55
            inicio_x = (
                largura // 2
                - ((max_letras - 1) * espaco) // 2
            )

            for index in range(max_letras):
                cor = (
                    config.BOTAO_AMARELO
                    if index == indice_letra
                    else config.BRANCO
                )

                letra = fonte_titulo.render(nome_atual[index], True, cor)
                letra_rect = letra.get_rect(
                    center=(inicio_x + index * espaco, 270)
                )
                tela.blit(letra, letra_rect)

                if index == indice_letra:
                    pygame.draw.line(
                        tela,
                        config.BOTAO_AMARELO,
                        (letra_rect.left, letra_rect.bottom + 8),
                        (letra_rect.right, letra_rect.bottom + 8),
                        3
                    )

            dica = fonte_normal.render(
                "Direcional: nome | Botão: salvar",
                True,
                config.BRANCO
            )
            tela.blit(
                dica,
                dica.get_rect(center=(largura // 2, 400))
            )

        else:
            titulo = fonte_titulo.render(
                f"RANKING - {game_name.upper()}",
                True,
                config.BOTAO_AMARELO
            )
            tela.blit(
                titulo,
                titulo.get_rect(center=(largura // 2, 80))
            )

            y = 160

            for index, score in enumerate(top_scores):
                texto = (
                    f"{index + 1}. "
                    f"{score['nome']} - {score['pontuacao']}"
                )

                cor = (
                    config.BOTAO_ROSA
                    if index == 0
                    else config.BRANCO
                )

                linha = fonte_normal.render(texto, True, cor)
                tela.blit(
                    linha,
                    linha.get_rect(center=(largura // 2, y))
                )
                y += 50

            if not top_scores:
                vazio = fonte_normal.render(
                    "Nenhuma pontuação ainda.",
                    True,
                    config.BRANCO
                )
                tela.blit(
                    vazio,
                    vazio.get_rect(center=(largura // 2, y))
                )

            dica = fonte_normal.render(
                "Botão de ação para sair",
                True,
                config.VERDE_CORPO_ESCURO
            )
            tela.blit(
                dica,
                dica.get_rect(
                    center=(largura // 2, altura - 60)
                )
            )

        if presenter:
            presenter()
        else:
            pygame.display.flip()
