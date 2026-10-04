"""
educacao.py
============================================
JOGO 1 (mais simples): Quiz educativo de robótica.

Pensado pras aulas do SESI / preparação pra OBR: perguntas de
múltipla escolha sobre robótica, sensores e o EV3.

Controles:
    1, 2, 3 -> escolhe a alternativa
    ESC     -> volta ao menu de jogos
"""

import random

import pygame

import config
import ranking


PERGUNTAS = [
    {
        "pergunta": "Qual sensor o EV3 usa pra detectar a linha preta?",
        "alternativas": ["Sensor de cor", "Sensor ultrassônico", "Sensor giroscópico"],
        "correta": 0,
    },
    {
        "pergunta": "Na OBR, o robô que sai da linha geralmente é...",
        "alternativas": ["Desclassificado da prova", "Penalizado em pontos", "Depende da prova"],
        "correta": 2,
    },
    {
        "pergunta": "O que mede o sensor ultrassônico?",
        "alternativas": ["Cor", "Distância", "Temperatura"],
        "correta": 1,
    },
    {
        "pergunta": "No EV3 Classroom, blocos amarelos controlam principalmente...",
        "alternativas": ["Sensores", "Motores", "Variáveis"],
        "correta": 1,
    },
    {
        "pergunta": "Um robô seguidor de linha usa qual lógica básica?",
        "alternativas": ["Aleatória", "Comparar leitura do sensor com um valor de referência", "Não usa sensores"],
        "correta": 1,
    },
    {
        "pergunta": "OBR significa...",
        "alternativas": ["Olimpíada Brasileira de Robótica", "Organização Brasileira de Robôs", "Olimpíada de Robôs Brasileiros"],
        "correta": 0,
    },
]


class JogoEducacao:
    def __init__(self, on_sair):
        """on_sair: callback chamado quando o jogo termina/sai (volta pro menu de jogos)."""
        self.on_sair = on_sair
        self.entrar()

    def entrar(self):
        self._ordem = random.sample(range(len(PERGUNTAS)), len(PERGUNTAS))
        self._indice = 0
        self._acertos = 0
        self._mostrando_resultado = False
        self._ultima_resposta_correta = None
        self._tempo_resultado = 0.0
        self._fim = False
        self.ranking_salvo = False

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self.on_sair()
                    return

                if self._fim:
                    continue

                if not self._mostrando_resultado:
                    tecla_para_indice = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
                    if evento.key in tecla_para_indice:
                        self._responder(tecla_para_indice[evento.key])
            
            if evento.type == pygame.JOYBUTTONDOWN:
                if evento.button in (6, 7): # START/SELECT
                    self.on_sair()
                    return
                if not self._fim and not self._mostrando_resultado:
                    if evento.button == 0: self._responder(0)
                    elif evento.button == 1: self._responder(1)
                    elif evento.button == 2: self._responder(2)

        if self._mostrando_resultado:
            self._tempo_resultado += dt
            if self._tempo_resultado > 1.2:
                self._avancar()

    def _responder(self, escolha):
        pergunta = PERGUNTAS[self._ordem[self._indice]]
        self._ultima_resposta_correta = (escolha == pergunta["correta"])
        if self._ultima_resposta_correta:
            self._acertos += 1
        self._mostrando_resultado = True
        self._tempo_resultado = 0.0

    def _avancar(self):
        self._mostrando_resultado = False
        self._indice += 1
        if self._indice >= len(self._ordem):
            self._fim = True

    def desenhar(self, tela):
        tela.fill((22, 26, 20))
        fonte_titulo = pygame.font.SysFont(None, 26, bold=True)
        fonte = pygame.font.SysFont(None, 20)
        fonte_pequena = pygame.font.SysFont(None, 16)

        if self._fim:
            self._desenhar_fim(tela, fonte_titulo, fonte)
            return

        titulo = fonte_titulo.render(f"Quiz Robótica  {self._indice + 1}/{len(self._ordem)}",
                                      True, config.BRANCO)
        tela.blit(titulo, (16, 14))

        pergunta = PERGUNTAS[self._ordem[self._indice]]

        # Quebra a pergunta em até 2 linhas simples
        texto_pergunta = self._quebrar_linha(pergunta["pergunta"], fonte, config.LARGURA - 32)
        y = 56
        for linha in texto_pergunta:
            render = fonte.render(linha, True, config.BRANCO)
            tela.blit(render, (16, y))
            y += 24

        y += 10
        for i, alt in enumerate(pergunta["alternativas"]):
            cor = config.BRANCO
            if self._mostrando_resultado:
                if i == pergunta["correta"]:
                    cor = (90, 220, 90)
                elif i != pergunta["correta"]:
                    cor = (150, 150, 150)

            texto = f"{i + 1}. {alt}"
            render = fonte.render(texto, True, cor)
            tela.blit(render, (24, y))
            y += 28

        rodape = fonte_pequena.render(f"Acertos: {self._acertos}   |   ESC: sair", True, (150, 150, 150))
        tela.blit(rodape, (16, config.ALTURA - 22))

        if self._mostrando_resultado:
            msg = "Acertou! ✅" if self._ultima_resposta_correta else "Errou ❌"
            cor_msg = (90, 220, 90) if self._ultima_resposta_correta else (220, 90, 90)
            render = fonte.render(msg, True, cor_msg)
            tela.blit(render, (config.LARGURA - render.get_width() - 16, 16))

    def _desenhar_fim(self, tela, fonte_titulo, fonte):
        total = len(self._ordem)
        titulo = fonte_titulo.render("Resultado final", True, config.BRANCO)
        tela.blit(titulo, titulo.get_rect(center=(config.LARGURA // 2, 60)))

        placar = fonte.render(f"{self._acertos} / {total} acertos", True, (240, 200, 60))
        tela.blit(placar, placar.get_rect(center=(config.LARGURA // 2, 110)))

        dica = pygame.font.SysFont(None, 18).render(
            "ESC: voltar ao menu de jogos", True, (150, 150, 150))
        tela.blit(dica, dica.get_rect(center=(config.LARGURA // 2, 160)))

    @staticmethod
    def _quebrar_linha(texto, fonte, largura_max):
        palavras = texto.split(" ")
        linhas = []
        linha_atual = ""
        for palavra in palavras:
            teste = (linha_atual + " " + palavra).strip()
            if fonte.size(teste)[0] <= largura_max:
                linha_atual = teste
            else:
                linhas.append(linha_atual)
                linha_atual = palavra
        if linha_atual:
            linhas.append(linha_atual)
        return linhas


if __name__ == '__main__':
    import sys
    pygame.init()
    pygame.display.set_caption("BMO - Quiz de Robótica")
    tela = pygame.display.set_mode((config.LARGURA, config.ALTURA), pygame.FULLSCREEN | pygame.SCALED)
    relogio = pygame.time.Clock()
    
    def on_sair():
        pygame.quit()
        sys.exit()
        
    jogo = JogoEducacao(on_sair)
    
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
        
        if jogo._fim and not jogo.ranking_salvo:
            ranking.mostrar_ranking_e_salvar(tela, relogio, "educacao", jogo._acertos)
            jogo.ranking_salvo = True
            jogo.entrar()
        
    pygame.quit()

