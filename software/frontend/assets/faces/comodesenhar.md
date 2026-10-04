# Como trocar o rosto do BMO por desenhos prontos

Isso é 100% opcional. Se essa pasta ficar vazia, o BMO continua com o rosto
desenhado por código (bolinhas/linhas), exatamente como já era.

## Por que em camadas, e não um rosto inteiro por expressão

Os olhos (emoção) e a boca (falando ou não) são controlados de forma
INDEPENDENTE no código — o BMO pode estar com olhos felizes E boca falando
ao mesmo tempo. Por isso cada peça é um arquivo separado: se você desenhasse
um único "rosto feliz inteiro" e um único "rosto falando inteiro", só um dos
dois apareceria por vez, e a combinação "feliz enquanto fala" nunca
apareceria. Desenhando em camadas, elas se combinam sozinhas.

## O que desenhar

Três grupos de arquivo, todos opcionais — desenhe só os que quiser, o resto
continua sendo desenhado por código:

**1. Corpo (fundo, sempre igual)**
| Arquivo | O que é |
|---|---|
| `corpo.png` | Corpo, tela, botões — tudo que NÃO muda com a emoção |

**2. Olhos (um por emoção)**
| Arquivo | Quando aparece |
|---|---|
| `olhos_neutro.png` | Estado de repouso / pensando |
| `olhos_feliz.png` | BMO empolgado, contente |
| `olhos_triste.png` | BMO chateado, desanimado |
| `olhos_surpreso.png` | BMO surpreso, chocado |
| `olhos_dormindo.png` | Tela de descanso / ocioso |

**3. Boca — dois conjuntos separados:**

*Boca parada* (usada quando ele NÃO está falando, uma por emoção):
`boca_neutro.png`, `boca_feliz.png`, `boca_triste.png`, `boca_surpreso.png`, `boca_dormindo.png`

*Boca falando* (usada SEMPRE que ele está falando, não importa a emoção —
substitui a boca parada e alterna sozinha conforme o volume do áudio):
`boca_falando_fechada.png`, `boca_falando_meio.png` (opcional), `boca_falando_aberta.png`

Sem `boca_falando_*`, ele usa a animação por código (uma "bolinha preta" que
abre/fecha) na mesma posição, então falar continua funcionando mesmo sem
desenhar essas três.

## Especificação técnica

- **Formato:** PNG com fundo TRANSPARENTE. Isso é importante aqui (diferente
  de antes) — a imagem de olhos só tem os olhos desenhados, o resto
  transparente, senão ela tampa o corpo/telinha por baixo. O mesmo vale pra
  boca.
- **Resolução/enquadramento:** desenhe todas as camadas no MESMO canvas
  (tamanho e posição), do tamanho da tela configurada em
  `software/frontend/config.py` (`LARGURA` x `ALTURA`, hoje 480x320,
  proporção 3:2) — assim elas se alinham exatamente quando empilhadas. Se
  desenhar em outra resolução ele redimensiona sozinho, mas mantenha a
  mesma proporção pra não distorcer nem desalinhar as camadas entre si.
- Referência de posição atual (pra alinhar com o corpo, se for reaproveitar
  o `corpo.png` desenhado por código como guia visual): olhos centralizados
  horizontalmente, ~20px acima do centro vertical; boca ~55px abaixo do
  centro vertical.

## Onde colocar

Salve os arquivos direto nesta pasta:
`software/frontend/assets/faces/`

Não precisa mexer em nenhum código — o `face.py` já procura os arquivos
aqui sozinho quando o BMO liga (e avisa no terminal quais carregou).
