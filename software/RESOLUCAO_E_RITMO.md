# Resolução unificada e ritmo dos jogos

## Avaliação de complexidade

Complexidade geral: **média, 6/10**.

O projeto tinha cinco fontes independentes de resolução: interface principal em 1024x768, configuração dos minigames em 1920x1080, Space Invaders fixo em 1920x1080, Mortal desenhado em 1280x720 e Planeta do Tesouro em C fixo em 1000x1000.

| Parte | Complexidade | Solução |
|---|---:|---|
| BMO, menus e jogos Pygame simples | Baixa | Todos leem `runtime_config.py`, que carrega `.env`. |
| Cobrinha e Space Invaders | Média | Resolução compartilhada e ritmo configurável. |
| Mortal | Média | Mantém canvas interno 1280x720 e o compõe dentro de 1024x1080 sem distorcer a arte. |
| Planeta do Tesouro/Raylib | Média-alta | Canvas virtual, letterbox e coordenadas do mouse convertidas. |

## Configuração padrão

Copie `.env.example` para `.env`. Os valores entregues são:

```dotenv
BMO_LOGICAL_WIDTH=1024
BMO_LOGICAL_HEIGHT=1080
BMO_DISPLAY_WIDTH=1920
BMO_DISPLAY_HEIGHT=1080
BMO_FULLSCREEN=1
BMO_FPS=60
BMO_BAR_COLOR=0,0,0
```

Em Pygame, `SCALED + FULLSCREEN` preserva a proporção. Num desktop 1920x1080, o canvas 1024x1080 fica centralizado e o SDL cria barras pretas de 448 pixels em cada lateral. A resolução do desktop do sistema operacional deve estar em 1920x1080.

`BMO_DISPLAY_WIDTH` e `BMO_DISPLAY_HEIGHT` também controlam diretamente a janela do jogo Raylib. `BMO_BAR_COLOR` controla as barras desenhadas pelos canvases de compatibilidade; as barras externas do SDL são pretas.

## Ritmo entregue

- Cobrinha: 6 movimentos por segundo, antes 10. A grade agora é centralizada e o tamanho da célula é configurável.
- Space Invaders: jogador a 9 px/quadro, antes 20; inimigos a 55% da velocidade anterior; nave-mãe mais lenta; tiros e power-ups mais lentos; inimigos aparecem a cada 90 quadros, antes 60.
- O zigue-zague dos inimigos foi mantido com movimento lateral mais suave para continuar divertido.

Altere `BMO_SNAKE_FPS`, `BMO_SPACE_PLAYER_SPEED`, `BMO_SPACE_ENEMY_SPEED_FACTOR`, `BMO_SPACE_MOTHERSHIP_SPEED` e `BMO_SPACE_SPAWN_FRAMES` no `.env` para calibrar no evento.

## Validação

Todos os arquivos Python passaram pela compilação de sintaxe e os cinco testes existentes do pipeline de voz continuam passando. O arquivo C modificado do Planeta do Tesouro também compila isoladamente.

O link final do executável Raylib não pôde ser concluído neste computador: o `libraylib.a` incluído no projeto usa arquitetura diferente do MinGW 32-bit instalado. No Raspberry Pi, use a biblioteca Raylib nativa da mesma arquitetura; no Windows, use MinGW e Raylib ambos 64-bit ou ambos 32-bit.
