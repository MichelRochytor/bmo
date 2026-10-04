"""
screens.py — telas do front-end do BMO.

Cada tela: entrar() (uma vez ao abrir) -> atualizar(dt, eventos) (retorna
o nome da próxima tela, ou None pra continuar) -> desenhar(tela).
SceneManager troca entre elas.

Layout escalável:
Todos os tamanhos de fonte e posições abaixo foram desenhados pensando em
uma tela BASE de 480x320. A resolução de execução vem do `.env` por meio de
runtime_config.py. Pra não ficar tudo espremido no canto quando
LARGURA/ALTURA mudam (ex: testando em um monitor 1920x1080), as funções
_fonte() e _pos() escalam fonte e posição proporcionalmente ao tamanho
configurado. O layout base é centralizado no espaço adicional.
"""

import pygame

import config
import states
from face import Face
from audio_lipsync import LipSync

TELA_BOOT = "boot"
TELA_MENU = "menu"
TELA_ROSTO = "rosto"
TELA_CONFIG = "config"
TELA_JOGOS = "jogos"

# --- Escala de layout ---
# Resolução em que os números de fonte/posição abaixo foram pensados.
_LARGURA_BASE = 480
_ALTURA_BASE = 320


def _escala():
    """Fator de escala atual, preservando proporção (usa o menor eixo pra
    nunca estourar a tela em nenhuma direção)."""
    return min(config.LARGURA / _LARGURA_BASE, config.ALTURA / _ALTURA_BASE)


def _fonte(tamanho_base, bold=False):
    """SysFont com tamanho escalado a partir da resolução base 480x320."""
    tamanho = max(1, round(tamanho_base * _escala()))
    return pygame.font.SysFont(None, tamanho, bold=bold)


def _pos(x_base, y_base):
    """Posição escalada e centralizada dentro do canvas configurado."""
    e = _escala()
    offset_x = (config.LARGURA - round(_LARGURA_BASE * e)) // 2
    offset_y = (config.ALTURA - round(_ALTURA_BASE * e)) // 2
    return (offset_x + round(x_base * e), offset_y + round(y_base * e))


class SceneManager:
    def __init__(self):
        self.telas = {
            TELA_BOOT: TelaBoot(self),
            TELA_MENU: TelaMenu(self),
            TELA_ROSTO: TelaRosto(self),
            TELA_CONFIG: TelaConfig(self),
            TELA_JOGOS: TelaJogos(self),
        }
        self.atual = TELA_BOOT
        self.on_tela_mudou = None
        self.telas[self.atual].entrar()

    def trocar_para(self, nome_tela):
        if nome_tela and nome_tela != self.atual and nome_tela in self.telas:
            self.atual = nome_tela
            self.telas[self.atual].entrar()
            if self.on_tela_mudou:
                self.on_tela_mudou(nome_tela)

    def atualizar(self, dt, eventos):
        proxima = self.telas[self.atual].atualizar(dt, eventos)
        self.trocar_para(proxima)

    def desenhar(self, tela):
        self.telas[self.atual].desenhar(tela)


class TelaBase:
    def __init__(self, manager):
        self.manager = manager

    def entrar(self):
        pass

    def atualizar(self, dt, eventos):
        return None

    def desenhar(self, tela):
        pass


class TelaBoot(TelaBase):
    DURACAO = 2.0

    def entrar(self):
        self._tempo = 0.0

    def atualizar(self, dt, eventos):
        self._tempo += dt
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                return TELA_MENU
        if self._tempo >= self.DURACAO:
            return TELA_MENU
        return None

    def desenhar(self, tela):
        tela.fill(config.VERDE_CORPO)
        fonte_titulo = _fonte(48, bold=True)
        fonte_sub = _fonte(22)

        titulo = fonte_titulo.render("BMO", True, config.BRANCO)
        tela.blit(titulo, titulo.get_rect(center=(config.LARGURA // 2, config.ALTURA // 2 - 20)))

        progresso = min(1.0, self._tempo / self.DURACAO)
        largura_barra = round(200 * _escala())
        x = config.LARGURA // 2 - largura_barra // 2
        y = config.ALTURA // 2 + round(30 * _escala())
        altura_barra = max(2, round(10 * _escala()))
        pygame.draw.rect(tela, config.VERDE_CORPO_ESCURO, (x, y, largura_barra, altura_barra), border_radius=5)
        pygame.draw.rect(tela, config.BRANCO, (x, y, int(largura_barra * progresso), altura_barra), border_radius=5)

        sub = fonte_sub.render("iniciando...", True, config.BRANCO)
        tela.blit(sub, sub.get_rect(center=(config.LARGURA // 2, y + round(30 * _escala()))))


class TelaMenu(TelaBase):
    OPCOES = [
        ("Rosto / Conversar", TELA_ROSTO),
        ("Configurações", TELA_CONFIG),
        ("Jogos", TELA_JOGOS),
    ]

    def entrar(self):
        self._selecionado = 0

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_DOWN:
                    self._selecionado = (self._selecionado + 1) % len(self.OPCOES)
                elif evento.key == pygame.K_UP:
                    self._selecionado = (self._selecionado - 1) % len(self.OPCOES)
                elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    _, destino = self.OPCOES[self._selecionado]
                    if destino:
                        return destino
        return None

    def desenhar(self, tela):
        tela.fill(config.VERDE_CORPO)
        fonte = _fonte(28)
        topo = 60
        espaco = 44

        for i, (texto, _) in enumerate(self.OPCOES):
            selecionado = (i == self._selecionado)
            cor = config.BRANCO if selecionado else config.VERDE_CORPO_ESCURO
            prefixo = "> " if selecionado else "   "
            render = fonte.render(prefixo + texto, True, cor)
            tela.blit(render, _pos(40, topo + i * espaco))


class TelaRosto(TelaBase):
    def __init__(self, manager):
        super().__init__(manager)
        self.face = Face()
        self.lipsync = LipSync()

    def entrar(self):
        self.face.set_expressao(states.NEUTRO)
        # Reset defensivo: garante boca fechada ao entrar, mesmo se a tela
        # tiver trocado no meio de uma fala anterior.
        self.face.set_falando(False)
        self._tocando_audio_no_frame_anterior = False

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    return TELA_MENU
                elif evento.key == pygame.K_1:
                    self.face.set_expressao(states.NEUTRO)
                elif evento.key == pygame.K_2:
                    self.face.set_expressao(states.FELIZ)
                elif evento.key == pygame.K_3:
                    self.face.set_expressao(states.TRISTE)
                elif evento.key == pygame.K_4:
                    self.face.set_expressao(states.SURPRESO)
                elif evento.key == pygame.K_5:
                    self.face.set_expressao(states.DORMINDO)
                elif evento.key == pygame.K_SPACE:
                    # Fala simulada pra testar a boca sem áudio real.
                    self.face.set_falando(not self.face.falando)
                elif evento.key == pygame.K_b:
                    self.face.piscar_agora()
                elif evento.key == pygame.K_t:
                    self._tocar_audio_teste()

        esta_tocando_audio = self.lipsync.esta_tocando()
        nivel_real = self.lipsync.nivel_atual() if esta_tocando_audio else None

        # Boca liga/desliga sozinha com o áudio real. Sem áudio real tocando,
        # não mexe em face.falando aqui — preserva o toggle manual (K_SPACE).
        if esta_tocando_audio:
            self.face.set_falando(True)
        elif self._tocando_audio_no_frame_anterior:
            self.face.set_falando(False)
        self._tocando_audio_no_frame_anterior = esta_tocando_audio

        self.face.atualizar(dt, nivel_audio=nivel_real)
        return None

    def desenhar(self, tela):
        tela.fill(config.VERDE_CORPO)
        self.face.desenhar(tela)

        fonte = _fonte(18)
        dica = fonte.render("ESC: voltar ao menu", True, config.VERDE_CORPO_ESCURO)
        tela.blit(dica, (round(10 * _escala()), config.ALTURA - dica.get_height() - round(4 * _escala())))

    def _tocar_audio_teste(self):
        import os
        # Mesma pasta que o bmo.py usa de verdade (ver config.caminho_audio).
        pasta_audios = os.path.join(config.BASE_DIR, "..", "backend", "audios")
        if not os.path.isdir(pasta_audios):
            print("⚠️ Pasta de áudios não encontrada.")
            return
        arquivos_wav = [f for f in os.listdir(pasta_audios) if f.lower().endswith(".wav")]
        if not arquivos_wav:
            print("⚠️ Nenhum .wav encontrado em backend/audios.")
            return
        caminho = os.path.join(pasta_audios, arquivos_wav[0])
        print(f"🔊 Testando lip sync com: {arquivos_wav[0]}")
        self.lipsync.tocar(caminho)


class TelaConfig(TelaBase):
    def entrar(self):
        self._volume = 70    # placeholder — vem do sistema real depois
        self._bateria = 85   # placeholder — vem do hardware depois

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    return TELA_MENU
                elif evento.key == pygame.K_LEFT:
                    self._volume = max(0, self._volume - 10)
                elif evento.key == pygame.K_RIGHT:
                    self._volume = min(100, self._volume + 10)
        return None

    def desenhar(self, tela):
        tela.fill(config.VERDE_CORPO)
        fonte_titulo = _fonte(30, bold=True)
        fonte = _fonte(22)

        titulo = fonte_titulo.render("Configurações", True, config.BRANCO)
        tela.blit(titulo, _pos(30, 30))

        texto_volume = fonte.render(f"Volume: {self._volume}%  (use ← →)", True, config.BRANCO)
        tela.blit(texto_volume, _pos(30, 90))

        texto_bateria = fonte.render(f"Bateria: {self._bateria}%", True, config.BRANCO)
        tela.blit(texto_bateria, _pos(30, 130))

        dica = fonte.render("ESC: voltar ao menu", True, config.VERDE_CORPO_ESCURO)
        tela.blit(dica, (round(30 * _escala()), config.ALTURA - dica.get_height() - round(10 * _escala())))


class TelaJogos(TelaBase):
    """Submenu que escolhe qual minigame abrir como subprocesso no backend."""

    OPCOES = [
        ("1. Jogo da Velha", "velha.py"),
        ("2. Cobrinha", "cobrinha.py"),
        ("3. Blocos", "blocos.py"),
        ("4. Space Invaders", "space_invaders.py"),
    ]

    def entrar(self):
        self._selecionado = 0

    def iniciar_jogo_direto(self, script):
        # TODO: comunicação via global module-level é frágil — provável
        # causa dos bugs de "volta errada"/"loop de animação" reportados.
        # Revisar junto com main.py (quem consome jogo_pendente).
        import os
        global jogo_pendente
        jogo_pendente = os.path.join(config.BASE_DIR, "..", "backend", "minigames", script)

    def atualizar(self, dt, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    return TELA_MENU
                elif evento.key == pygame.K_DOWN:
                    self._selecionado = (self._selecionado + 1) % len(self.OPCOES)
                elif evento.key == pygame.K_UP:
                    self._selecionado = (self._selecionado - 1) % len(self.OPCOES)
                elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    _, script = self.OPCOES[self._selecionado]
                    self.iniciar_jogo_direto(script)
        return None

    def desenhar(self, tela):
        tela.fill(config.VERDE_CORPO)
        fonte_titulo = _fonte(28, bold=True)
        fonte = _fonte(24)

        titulo = fonte_titulo.render("Jogos da Roboap", True, config.BRANCO)
        tela.blit(titulo, _pos(30, 24))

        topo = 70
        espaco = 38
        for i, (texto, _) in enumerate(self.OPCOES):
            selecionado = (i == self._selecionado)
            cor = config.BRANCO if selecionado else config.VERDE_CORPO_ESCURO
            prefixo = "> " if selecionado else "   "
            render = fonte.render(prefixo + texto, True, cor)
            tela.blit(render, _pos(30, topo + i * espaco))

        dica = _fonte(18).render(
            "ENTER: jogar   |   ESC: voltar", True, config.VERDE_CORPO_ESCURO)
        tela.blit(dica, (round(30 * _escala()), config.ALTURA - dica.get_height() - round(4 * _escala())))
