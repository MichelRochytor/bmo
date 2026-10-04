import pygame
import os
import json
import config

RANKING_FILE = os.path.join(config.BASE_DIR, "ranking.json")

def carregar_ranking():
    if os.path.exists(RANKING_FILE):
        try:
            with open(RANKING_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_ranking(dados):
    with open(RANKING_FILE, "w") as f:
        json.dump(dados, f, indent=4)

def adicionar_pontuacao(game_name, nome, pontuacao):
    dados = carregar_ranking()
    if game_name not in dados:
        dados[game_name] = []
    
    # Adiciona a nova pontuação
    dados[game_name].append({"nome": nome, "pontuacao": pontuacao})
    
    # Ordena de forma decrescente pela pontuação
    dados[game_name] = sorted(dados[game_name], key=lambda x: x["pontuacao"], reverse=True)
    
    # Mantém apenas o top 5
    dados[game_name] = dados[game_name][:5]
    salvar_ranking(dados)

def mostrar_ranking_e_salvar(tela, relogio, game_name, pontuacao, max_letras=3):
    """
    Exibe a tela para inserir o nome (ex: 3 letras) se a pontuação for digna de top 5,
    e depois mostra o leaderboard. Se pontuacao=None, apenas exibe o ranking.
    """
    dados = carregar_ranking()
    top_scores = dados.get(game_name, [])
    
    precisa_digitar = False
    if pontuacao is not None:
        if len(top_scores) < 5 or pontuacao > top_scores[-1]["pontuacao"]:
            precisa_digitar = True
            
    nome_atual = ["A", "A", "A"]
    idx_letra = 0
    fonte_titulo = pygame.font.SysFont(None, 48, bold=True)
    fonte_normal = pygame.font.SysFont(None, 36)
    
    rodando = True
    while rodando:
        dt = relogio.tick(config.FPS)
        tela.fill(config.VERDE_CORPO)
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            
            if evento.type == pygame.KEYDOWN:
                if precisa_digitar:
                    if evento.key == pygame.K_UP:
                        novo_char = chr((ord(nome_atual[idx_letra]) - 65 + 1) % 26 + 65)
                        nome_atual[idx_letra] = novo_char
                    elif evento.key == pygame.K_DOWN:
                        novo_char = chr((ord(nome_atual[idx_letra]) - 65 - 1) % 26 + 65)
                        nome_atual[idx_letra] = novo_char
                    elif evento.key == pygame.K_RIGHT:
                        idx_letra = min(max_letras - 1, idx_letra + 1)
                    elif evento.key == pygame.K_LEFT:
                        idx_letra = max(0, idx_letra - 1)
                    elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                        nome_final = "".join(nome_atual)
                        adicionar_pontuacao(game_name, nome_final, pontuacao)
                        precisa_digitar = False
                        # Atualiza os top scores pra tela
                        dados = carregar_ranking()
                        top_scores = dados.get(game_name, [])
                else:
                    if evento.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                        rodando = False
        
        # Desenho
        if precisa_digitar:
            titulo = fonte_titulo.render("NOVO RECORDE!", True, config.BOTAO_ROSA)
            tela.blit(titulo, titulo.get_rect(center=(config.LARGURA//2, 100)))
            
            sub = fonte_normal.render(f"Sua Pontuação: {pontuacao}", True, config.BRANCO)
            tela.blit(sub, sub.get_rect(center=(config.LARGURA//2, 150)))
            
            # Letras
            espaco = 40
            inicio_x = config.LARGURA//2 - (max_letras * espaco)//2 + 20
            
            for i in range(max_letras):
                cor = config.BOTAO_AMARELO if i == idx_letra else config.BRANCO
                letra_surf = fonte_titulo.render(nome_atual[i], True, cor)
                tela.blit(letra_surf, (inicio_x + i * espaco, 250))
                if i == idx_letra:
                    pygame.draw.line(tela, config.BOTAO_AMARELO, (inicio_x + i * espaco, 290), (inicio_x + i * espaco + 20, 290), 3)
            
            dica = fonte_normal.render("Setas MUDAM/MOVEM | ENTER p/ Salvar", True, config.BRANCO)
            tela.blit(dica, dica.get_rect(center=(config.LARGURA//2, 400)))
            
        else:
            titulo = fonte_titulo.render(f"RANKING - {game_name.upper()}", True, config.BOTAO_AMARELO)
            tela.blit(titulo, titulo.get_rect(center=(config.LARGURA//2, 80)))
            
            y = 160
            for i, score in enumerate(top_scores):
                texto = f"{i+1}. {score['nome']} - {score['pontuacao']}"
                cor = config.BOTAO_ROSA if i == 0 else config.BRANCO
                linha_surf = fonte_normal.render(texto, True, cor)
                tela.blit(linha_surf, linha_surf.get_rect(center=(config.LARGURA//2, y)))
                y += 50
                
            if not top_scores:
                vazio = fonte_normal.render("Nenhuma pontuação ainda.", True, config.BRANCO)
                tela.blit(vazio, vazio.get_rect(center=(config.LARGURA//2, y)))
                
            dica = fonte_normal.render("Pressione ENTER para Sair", True, config.VERDE_CORPO_ESCURO)
            tela.blit(dica, dica.get_rect(center=(config.LARGURA//2, config.ALTURA - 60)))
            
        pygame.display.flip()
