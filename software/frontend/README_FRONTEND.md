# 🎨 Front-end do BMO

Rosto animado feito em **Pygame**, desenhado por código (sem precisar de
imagens prontas), pra já dar pra testar no notebook e depois só trocar a
resolução pra rodar no Raspberry Pi com o display.

## Como rodar

```bash
pip install pygame pyaudio
python main.py
```

> No Raspberry, edite `config.py`: troque `LARGURA`/`ALTURA` pela resolução
> real do display e coloque `FULLSCREEN = True`.

## Fluxo de telas

```
Boot (2s) -> Menu -> Rosto / Conversar
                  -> Configurações
                  -> Jogos (placeholder p/ o time de back-end)
```

## Controles

**Tela de Boot:** qualquer tecla pula direto pro menu.

**Menu:** `↑` `↓` navega, `ENTER`/`ESPAÇO` seleciona, `ESC` fecha o programa.

**Tela do Rosto:**
| Tecla | Ação |
|---|---|
| `1` | Expressão Neutra |
| `2` | Expressão Feliz |
| `3` | Expressão Triste |
| `4` | Expressão Surpreso |
| `5` | Tela de descanso (dormindo) |
| `ESPAÇO` | Simula fala (boca mexendo sozinha) |
| `T` | Toca um `.wav` real de `software/audios` com lip sync de verdade |
| `B` | Força uma piscada |
| `ESC` | Volta ao menu |

**Tela de Configurações:** `←` `→` ajusta volume (placeholder), `ESC` volta ao menu.

## Estrutura

```
frontend/
  config.py          # tela, cores, FPS, caminhos
  states.py           # nomes das expressões (NEUTRO, FELIZ, FALANDO...)
  face.py              # classe Face: desenha e anima olhos/boca
  audio_lipsync.py     # toca .wav e calcula amplitude p/ lip sync real
  screens.py            # SceneManager + telas (Boot, Menu, Rosto, Config, Jogos)
  main.py                 # loop principal (janela Pygame)
  games/
    mascote.py             # desenho do ROBOAP (texugo) reaproveitado nos jogos
    educacao.py             # Jogo 1: Quiz de robótica (OBR / EV3 Classroom)
    seguidor_linha.py        # Jogo 2: Simulador de seguidor de linha
    combate.py                # Jogo 3: Combate (ataca/defende)
    plataforma.py               # Jogo 4: Corrida/plataforma (pular obstáculos)
```

## 🎮 Jogos da Roboap

Acessíveis pelo Menu -> Jogos. Cada um simula/celebra uma das modalidades
que o time disputa (artbot, seguidor de linha, combate) + um quiz educativo
pras aulas do SESI / preparação pra OBR.

| Jogo | Controles | Ideia |
|---|---|---|
| **Educação** | `1` `2` `3` escolhem a alternativa | Quiz de robótica (sensores, EV3, OBR) |
| **Seguidor de Linha** | `←` `→` move o robô | Mantenha o robô em cima da linha sinuosa o máximo de tempo |
| **Combate** | `J` ataca, `K` defende | Reduza a vida do robô inimigo antes que ele reduza a sua |
| **Plataforma** | `ESPAÇO`/`↑` pula | Desvie dos espinhos, pegue moedas, estilo corrida infinita |

Em todos: `ESC` volta pro menu (do jogo -> submenu -> menu principal).
`ENTER` reinicia quando a partida termina.

O mascote (`games/mascote.py`) é desenhado por código, no estilo visual do
material que vocês já têm (preto/branco com contorno amarelo). Se quiserem
trocar pelo arte-final de verdade depois, é só editar essa única função —
todos os 4 jogos chamam `desenhar_roboap()` e mudam automaticamente.

## Como o back-end (bmo.py) vai integrar isso

A ideia é que `bmo.py` acesse a tela do rosto direto pelo `scene_manager`:

```python
import screens

scene_manager = screens.SceneManager()
scene_manager.trocar_para(screens.TELA_ROSTO)

tela_rosto = scene_manager.telas[screens.TELA_ROSTO]
tela_rosto.face.set_expressao(states.FALANDO)
tela_rosto.lipsync.tocar(caminho_do_audio_da_resposta)
```

O ideal é juntar o loop do `main.py` com o loop de reconhecimento de voz do
`bmo.py` rodando em threads separadas (a escuta de voz já roda em thread no
`bmo.py`, então dá pra encaixar o Pygame como o loop principal e mandar
eventos pra ele).

## Próximos passos sugeridos

- [ ] Trocar olhos/boca desenhados por código por sprites/GIFs (se o time de
      design quiser um visual mais "desenho animado")
- [ ] Tela de jogos de verdade (hoje é só um placeholder no menu)
- [ ] Volume/bateria reais (hoje são valores fixos na TelaConfig)
- [ ] Sincronizar `face.set_expressao()` com as intenções do `bmo.py`
      (ex: intenção "saudacao" -> `states.FELIZ`)
