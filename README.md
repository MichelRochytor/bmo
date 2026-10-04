# **🤖 Projeto BMO: "Be More"**
"Quem quer jogar videogame?" — BMO
---
## ESPECIALIDADES E RESPONSABILIDADES DO TIME

**OBS1: Não sera 100% assim é só para que eu tenha uma base no que cada um gosta mais e o que tem mais afinidade, a ideia é que todos façam um pouco de tudo, então escolham por conhecimento por favor**

**OBS2: Pode ter mais de um nome em cada um dos 3**
### **🏗️ [Gabrielle Kyoko] [Naidson Quintino]| O CONSTRUTOR (HARDWARE & DESIGN)**
 - DESIGN INDUSTRIAL: Modelagem 3D da carcaça, impressão e acabamento.
 - ELETRÔNICA: Soldagem, gerenciamento de energia e fiação do display.
 - INTERFACE FÍSICA: Configuração dos botões (GPIO) e alto-falantes.

### **🎨 [Gabrielle Kyoko] [Ralison Trovão]| O ARTISTA (FRONT-END & UX)**
 - ANIMAÇÃO FACIAL: Criação de estados visuais (piscando, rindo, falando).
 - INTERFACE DE USUÁRIO (UI): Design dos menus e telas de carregamento.
 - COREOGRAFIA DIGITAL: Animações de dança sincronizadas com áudio.

### **🧠 [Caio Eduardo] [Yuji Aoki]| O ARQUITETO (BACK-END & INTELIGÊNCIA)**
 - LÓGICA DE CONVERSA: Integração com APIs de IA e processamento de fala.
 - ENGENHARIA DE JOGOS: Estrutura base para rodar os jogos autorais.
 - PROCESSAMENTO DE ÁUDIO: Algoritmos de "Beat Detection" para o modo dança.

---
## 📅 CRONOGRAMA DE EVOLUÇÃO SEMANAL

| **SEMANA** | **FOCO: HARDWARE 🏗️** | **FOCO: FRONT-END 🎨** | **FOCO: BACK-END 🧠** |
| :---: | :--- | :--- | :--- |
| **W1** | Compra e teste de componentes. | Estudo de proporções do rosto. | Setup do OS (Raspberry Pi). |
| **W2** | Primeiro protótipo de carcaça. | "Script de 'piscar' funcional." | Integração de microfone/áudio. |
| **W3** | Soldagem dos botões principais. | Menu inicial de seleção. | Script base de Chat (IA). |
| **W4** | Montagem interna (Bancada). | Animações de fala (Lip Sync). | "Lógica de 'Beat Detection'." |
| **W5** | Ajustes de ventilação/calor. | "Animações do 'Modo Dança'." | Desenvolvimento do Jogo 01. |
| **W6** | Pintura e acabamento final. | UI de sistema (Volume/Bateria). | Integração total (Face + IA). |

---
## Estruturas de Pastas
  Para manter o GitHub organizado:
   - **/hardware**: Arquivos .STL para impressão 3D e esquemas elétricos.
   - **/software**: Código fonte em Python (IA, Dança, Jogos).
   - **/assets**: Imagens, GIFs do rosto e efeitos sonoros.
   - **/docs**: Fotos do progresso e manuais.

---
##Hardware Base 
 - **CÉREBRO**: Raspberry Pi 4 ou Zero 2 W.
 - **VISÃO**: Display LCD IPS (3.5" a 5").
 - **ENERGIA**: Bateria LiPo + Módulo PowerBoost 1000C.
 - **SOM**: Mini Alto-falante (3W) + Amplificador PAM8403.

---
##Tecnologias que talvez seja interessante
 - **Linguagem Principal**: Python (Pela facilidade com GPIO e bibliotecas de IA).
 - **Interface/Animação**: Pygame ou Tkinter (Para o rosto e jogos próprios).
 - **Inteligência Artificial**: OpenAI API ou ChatterBot (Para conversação).
 - **Processamento de Som**: Librosa (Para detectar batidas e fazer ele dançar).

---
## Backlog de Funcionalidades
  [ ] Expressões Dinâmicas: Mudar o rosto conforme o estado de humor.
  
  [ ] Modo Dança: Detectar frequências sonoras e animar o rosto no ritmo.
  
  [ ] Conversa Ativa: Responder perguntas usando Inteligência Artificial.
  
  [ ] Biblioteca de Jogos: Criar e integrar jogos autorais desenvolvidos pelo time.
  
  [ ] Sistema de Som: Emitir efeitos sonoros clássicos do desenho.
