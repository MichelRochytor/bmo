"""
main.py
============================================
Ponto de entrada integrado do BMO (Front-end + Back-end).

Inicia a interface gráfica (Pygame) na thread principal e roda
o assistente de voz do BMO em uma thread secundária.
============================================
"""

import sys
import os
import time
import threading
import pygame

# Ajusta caminhos para que os subarquivos consigam importar uns aos outros
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "frontend"))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

import config
import screens
import states
import bmo

# Gerenciador global de telas do Pygame
scene_manager = None

def callback_expressao(expressao):
    """Callback para o backend mudar o humor (olhos) do rosto no Pygame."""
    if not scene_manager:
        return
    if scene_manager.atual == screens.TELA_ROSTO:
        map_expr = {
            "neutro": states.NEUTRO,
            "feliz": states.FELIZ,
            "triste": states.TRISTE,
            "surpreso": states.SURPRESO,
            "dormindo": states.DORMINDO
            # "falando" não entra aqui -- é controlado à parte por
            # Face.falando, ligado automaticamente pelo lip sync real
            # (ver TelaRosto.atualizar() em screens.py).
        }
        tela_rosto = scene_manager.telas[screens.TELA_ROSTO]
        tela_rosto.face.set_expressao(map_expr.get(expressao, states.NEUTRO))
        
def callback_tocar_audio(arquivo):
    """
    Callback para o backend tocar áudio de resposta atAravés do LipSync do frontend.
    Bloqueia a thread do backend até a reprodução terminar.
    """
    if not scene_manager or not bmo_ativo.is_set():
        return False

    tela_rosto = scene_manager.telas[screens.TELA_ROSTO]

    # Uma resposta que terminou depois de o usuário sair do rosto não pode
    # puxar a interface de volta para a conversa.
    if scene_manager.atual != screens.TELA_ROSTO:
        return False

    tela_rosto.lipsync.tocar(arquivo, stop_event=None)

    while tela_rosto.lipsync.esta_tocando() and bmo_ativo.is_set():
        time.sleep(0.05)

    if not bmo_ativo.is_set():
        tela_rosto.lipsync.parar()

    # Desligado explicitamente aqui (em vez de confiar só no próximo frame
    # de TelaRosto.atualizar()): se o backend trocar de tela logo em seguida
    # (ex: "jogar jogo da velha"), esse "próximo frame" pode nunca vir
    # enquanto a tela do rosto não está mais ativa, e a boca ficaria travada
    # aberta pra sempre.
    tela_rosto.face.set_falando(False)

    return True

def callback_mudar_tela(tela, jogo_nome=None):
    """Callback para o backend mudar de tela ou abrir jogos integrados."""
    if not scene_manager or not bmo_ativo.is_set():
        return

    if tela == "jogos" and jogo_nome:
        scene_manager.trocar_para(screens.TELA_JOGOS)
        scene_manager.telas[screens.TELA_JOGOS].iniciar_jogo_direto(jogo_nome)
    elif tela == "rosto":
        scene_manager.trocar_para(screens.TELA_ROSTO)
    elif tela == "menu":
        scene_manager.trocar_para(screens.TELA_MENU)

bmo_ativo = threading.Event()
bmo_cancelar = threading.Event()
bmo_cancelar.set()  # boot/menu começam com microfone e fala desativados

def callback_tela_mudou(nome_tela):
    """Chamado pelo SceneManager toda vez que a tela ativa muda."""
    if nome_tela == screens.TELA_ROSTO:
        bmo_cancelar.clear()
        bmo_ativo.set()
    else:
        bmo_ativo.clear()
        bmo_cancelar.set()
        # Interrompe também uma fala que já estava no buffer do PortAudio.
        try:
            tela_rosto = scene_manager.telas[screens.TELA_ROSTO]
            tela_rosto.lipsync.parar()
            tela_rosto.face.set_falando(False)
        except Exception:
            pass

def rodar_backend(modo_texto):
    bmo.on_expressao_changed = callback_expressao
    bmo.on_play_audio = callback_tocar_audio
    bmo.on_change_screen = callback_mudar_tela
    bmo.on_interaction_active = bmo_ativo.is_set

    import pyaudio
    import atexit
    bmo._pa_output = pyaudio.PyAudio()
    atexit.register(bmo._pa_output.terminate)

    executando = True
    while executando:
        if not bmo_ativo.is_set():
            # Bloqueia sem gastar CPU até a tela do rosto abrir. Timeout
            # evita ficar preso pra sempre se o programa fechar nesse instante.
            bmo_ativo.wait(timeout=0.5)
            continue
        executando = bmo.reconhecer_e_agir(modo_texto, cancelar_evento=bmo_cancelar)
        time.sleep(0.03)

def main():
    global scene_manager

    print("\n" + "="*50)
    print("🎙️ BMO INTEGRADO - CONTROLE POR VOZ E TERMINAL")
    print("="*50)
    print("[1] Usar Microfone (Padrão)")
    print("[2] Usar Teclado (Entrada via Terminal)")
    print("Escolha uma opção no terminal...")

    modo_texto = False
    try:
        escolha = input("Digite 1 ou 2: ").strip()
        modo_texto = (escolha == "2")
    except (KeyboardInterrupt, EOFError):
        pass

    if modo_texto:
        print("⌨️ Modo texto ativado. Digite no terminal e veja o rosto do BMO reagir!")
    else:
        print("🎙️ Modo voz ativado. Fale naturalmente!")

    pygame.init()
    pygame.display.set_caption(config.TITULO_JANELA)

    flags = config.display_flags(pygame)
    tela = pygame.display.set_mode((config.LARGURA, config.ALTURA), flags)

    relogio = pygame.time.Clock()
    scene_manager = screens.SceneManager()
    scene_manager.on_tela_mudou = callback_tela_mudou

    thread_b = threading.Thread(target=rodar_backend, args=(modo_texto,), daemon=True)
    thread_b.start()

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

        if getattr(screens, "jogo_pendente", None) is not None:
            caminho_script = screens.jogo_pendente
            screens.jogo_pendente = None

            if jogo_processo is not None and jogo_processo.poll() is None:
                jogo_processo.terminate()
                jogo_processo.wait()

            import subprocess
            jogo_processo = subprocess.Popen([sys.executable, caminho_script])

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

    # Encerra qualquer jogo ainda aberto (bug corrigido: antes, fechar o
    # BMO com um jogo rodando deixava o processo órfão, ainda ativo).
    if jogo_processo is not None and jogo_processo.poll() is None:
        jogo_processo.terminate()
        jogo_processo.wait()

    try:
        bmo_ativo.clear()
        bmo_cancelar.set()
        scene_manager.telas[screens.TELA_ROSTO].lipsync.encerrar()
    except Exception:
        pass

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
