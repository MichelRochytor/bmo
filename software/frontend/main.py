import sys
import time
import subprocess
 
import pygame
 
import config
import screens
 
 
def main():
    pygame.init()
    pygame.display.set_caption(config.TITULO_JANELA)
 
    flags = config.display_flags(pygame)
    tela = pygame.display.set_mode((config.LARGURA, config.ALTURA), flags)
 
    relogio = pygame.time.Clock()
    scene_manager = screens.SceneManager()
 
    jogo_processo = None
    rodando = True
    while rodando:
        dt = relogio.tick(config.FPS) / 1000.0
        eventos = pygame.event.get()
 
        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE \
                    and scene_manager.atual == screens.TELA_MENU:
                rodando = False
 
        # Um jogo foi escolhido em TelaJogos -> lança como subprocesso, do
        # mesmo jeito que software/main.py já fazia.
        if getattr(screens, "jogo_pendente", None) is not None:
            caminho_script = screens.jogo_pendente
            screens.jogo_pendente = None
 
            if jogo_processo is not None and jogo_processo.poll() is None:
                jogo_processo.terminate()
                jogo_processo.wait()
 
            jogo_processo = subprocess.Popen([sys.executable, caminho_script])
 
        # Enquanto o jogo está aberto, pausa o loop do rosto (a janela do
        # jogo assume a tela) e espera ele fechar pra voltar ao menu.
        if jogo_processo is not None:
            if jogo_processo.poll() is not None:
                jogo_processo = None
                tela = pygame.display.set_mode((config.LARGURA, config.ALTURA), flags)
                pygame.event.clear()
                scene_manager.trocar_para(screens.TELA_ROSTO)
            else:
                time.sleep(0.05)
                continue
 
        scene_manager.atualizar(dt, eventos)
        scene_manager.desenhar(tela)
        pygame.display.flip()
 
    if jogo_processo is not None and jogo_processo.poll() is None:
        jogo_processo.terminate()
        jogo_processo.wait()
 
    pygame.quit()
    sys.exit()
 
 
if __name__ == "__main__":
    main()
