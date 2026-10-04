# Mortal UTFPR — Arena dos Cursos

## Versão visual 2

- Nova abertura cinematográfica da UTFPR.
- Nova seleção com prévia dos dois lutadores e dez cards.
- Arena da UTFPR, cronômetro de 90 segundos e HUD renovado.
- Fatality mostra somente o vencedor na cena final.
- Artes atualizadas da ROBOAP incluídas no próprio projeto.

### Como executar uma Fatality

Esgote completamente a vida do adversário. Quando aparecer **FINISH!**, ele
ficará vulnerável durante 6 segundos. Aproxime-se e pressione `R` com o P1 ou
`P` com o P2. A Fatality não consome energia. Se o tempo acabar, será uma
vitória normal.

Um jogo de luta local em Python/Pygame feito para os 10 personagens da UTFPR. As artes são carregadas da pasta original `C:\Users\Olá\Downloads\Mortal_UTFPR_AP`; ela não é alterada.

## Como executar

No Windows, extraia todo o ZIP e dê dois cliques em `INICIAR_JOGO.bat`.
O iniciador verifica o Python e prepara o Pygame automaticamente. Se o Python
não estiver instalado, instale a versão atual em
<https://www.python.org/downloads/windows/> e marque **Add Python to PATH**.

Alternativamente, abra o PowerShell nesta pasta e rode:

```powershell
python -m pip install -r requirements.txt
python main.py
```

O pacote gráfico também pode ficar somente dentro do projeto (sem instalação
global), usando `python -m pip install --target .deps -r requirements.txt`.

Se suas artes estiverem em outro local, defina a variável `MORTAL_UTFPR_ART` antes de iniciar:

```powershell
$env:MORTAL_UTFPR_ART = 'D:\minhas-artes\Mortal_UTFPR_AP'
python main.py
```

## Modos

- `1`: jogador contra computador.
- `2`: jogador contra jogador com dois controles ou no mesmo teclado.

Após escolher o modo, selecione P1 e o adversário. Contra o computador, o segundo lutador é sorteado, mas pode ser trocado antes de confirmar.

## Controles durante a luta

Controles de PS4 e Xbox são reconhecidos pela camada SDL do Pygame. Conecte-os
antes de abrir o jogo (ou durante a execução) e use:

| Ação | Xbox | PS4 |
| --- | --- | --- |
| Mover / agachar e defender | Analógico esquerdo ou direcional | Analógico esquerdo ou direcional |
| Pular / confirmar | `A` | `X` (Cross) |
| Golpe rápido | `X` | `Quadrado` |
| Golpe forte | `Y` | `Triângulo` |
| Chute / voltar nos menus | `B` | `Círculo` |
| Especial 1 | `LB` | `L1` |
| Especial 2 | `RB` | `R1` |
| Especial 3 / Fatality | `RT` ou analógico direito pressionado | `R2` ou `R3` |
| Arremesso | `LT` ou analógico esquerdo pressionado | `L2` ou `L3` |

No modo contra a CPU, o primeiro controle comanda o P1. No modo para dois
jogadores, o primeiro controle comanda o P1 e o segundo comanda o P2. O teclado
continua disponível como alternativa.

| Jogador 1 | Jogador 2 |
| --- | --- |
| `A` / `D`: mover | `←` / `→`: mover |
| `W`: pular | `↑`: pular |
| `S`: defender / agachar | `↓`: defender / agachar |
| `F`, `G`, `H`: rápido, forte, chute | `J`, `K`, `L`: rápido, forte, chute |
| `Q`, `E`, `R`: especiais 1, 2 e 3 | `U`, `O`, `P`: especiais 1, 2 e 3 |
| `T`: arremesso | `I`: arremesso |

O arremesso é instantâneo, não pode ser bloqueado e só funciona bem coladinho no adversário — é a forma de quebrar quem fica só defendendo. Golpes feitos no ar (pulando) são mais rápidos e alcançam mais, mas deixam o personagem um instante vulnerável ao aterrissar. Os personagens também não conseguem mais atravessar um ao outro.

Quando o adversário estiver com até 20% de vida e houver 35% de energia, use o terceiro especial para executar a **Fatality**.

## Sons

Esta versão já inclui os áudios fornecidos, com trilha ambiente ainda mais baixa e contínua
desde a abertura do jogo, voz de início tocada uma vez por partida e impactos
exclusivos para cada personagem (um único som por golpe acertado). CAEC, CAEQ e
CADEM possuem uma segunda variação; assim, os 13 efeitos de luta enviados estão
no jogo. Há também alerta nos 10 segundos finais e efeito exclusivo
da Fatality do ROBOAP e som de game over. Os demais eventos continuam usando os
efeitos gerados pelo próprio Pygame quando não houver um arquivo próprio. Esses
efeitos funcionam mesmo sem o pacote NumPy instalado.

A antiga faixa `combat.mp3`, que também pronunciava “FIGHT”, não é usada nos
ataques. A voz `round_start.mp3` toca somente quando uma nova partida começa.

Para usar sons de verdade no lugar deles, crie a pasta `assets/sounds/` dentro do projeto e coloque arquivos `.wav`, `.ogg` ou `.mp3` com estes nomes exatos (sem o prefixo do personagem):

| Nome do arquivo | Quando toca |
| --- | --- |
| `hit_<personagem>` | impacto próprio de cada lutador |
| `hit_caec_alt`, `hit_caeq_alt`, `hit_cadem_alt` | variações aleatórias desses lutadores |
| `block` | golpe bloqueado |
| `throw` | arremesso |
| `special` | ativar um especial |
| `jump` | pular |
| `land` | aterrissar |
| `fatality` | executar a Fatality |
| `victory` | round vencido |
| `select` | confirmar no menu |
| `move` | navegar no menu/seleção |
| `round_start` | início da luta |
| `background_music` | som ambiente da arena (em loop) |
| `timer_warning` | alerta nos 10 segundos finais (em loop) |
| `fatality_roboap` | Fatality exclusiva do ROBOAP |
| `game_over` | encerramento da luta |

Basta o arquivo existir com o nome certo (ex: `assets/sounds/hit_heavy.wav`) que o jogo passa a usá-lo automaticamente no lugar do som gerado — não precisa mexer em nenhum código.

## Lutadores e especiais

- CAECOMP: Código Fatal, Overclock, Dados Destrutivos
- CAETX: Trama Secreta, Fibra Imparável, Tecido Protetor
- CAEC: Fundação Inabalável, Construção Perfeita, Estrutura Suprema
- CALIQ: Reação em Cadeia, Solução Tóxica, Transformação Química
- ROBOAP: Protocolo Alfa, Sistema Robótico, Upgrade Total
- PANTHERION: Garra Afiada, Elegância Letal, Conforto Dominante
- CAEQ: Síntese Precisa, Reação Controlada, Elemento Surpresa
- CODIFICADORAS: Ataque de Código, Firewall Rosa, Quebra de Sistema
- CAEL: Choque Elétrico, Circuito Sobrecarga, Campo Eletromagnético
- CADEM: Corte Preciso, Costura Letal, Estilo Único

Cada lutador tem atributos próprios de vida, força, velocidade, defesa e técnica. O motor usa as poses PNG disponíveis para parado, caminhada, salto, ataque, defesa, especiais, vitória e fatality, com fallback automático quando algum arquivo ainda não existir.
