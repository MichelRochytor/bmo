# BMO — Backend de voz (`bmo.py`)

Requisitos para rodar a versão atual do backend do BMO: reconhecimento de fala e
agente conversacional via Groq (Whisper + LLM) e síntese de voz via Piper TTS.

## 1. Dependências

### Pacotes Python (pip)

```bash
pip install --break-system-packages SpeechRecognition pyaudio groq python-dotenv piper-tts
```

| Pacote | Para quê |
|---|---|
| `SpeechRecognition` | Captura o áudio do microfone (`sr.Microphone`, `sr.Recognizer`) |
| `pyaudio` | Saída de áudio (toca os `.wav`, pré-gravados ou gerados) |
| `groq` | Cliente da API da Groq — STT (Whisper) e o agente conversacional (LLM) |
| `python-dotenv` | Lê a `GROQ_API_KEY` do arquivo `.env` |
| `piper-tts` | TTS neural local — gera a voz do BMO a partir do texto |

### Pacotes de sistema (apt — Raspberry Pi OS / Debian / Ubuntu)

```bash
sudo apt update
sudo apt install portaudio19-dev ffmpeg
```

- **`portaudio19-dev`** — necessário para instalar/compilar o `pyaudio`.
- **`ffmpeg`** — usado para ajustar o tom (pitch) da voz gerada pelo Piper, via filtro
  `rubberband`. Confirme que o pacote instalado tem esse filtro:
  ```bash
  ffmpeg -filters | grep rubberband
  ```
  Se não aparecer nada, essa versão do `ffmpeg` não tem `librubberband` compilada e o
  ajuste de pitch vai falhar (o áudio ainda toca, só sai sem o ajuste de tom).

> Não é preciso instalar `espeak-ng` separadamente — o `piper-tts` já vem com os
> dados de fonemização embutidos no próprio pacote pip.

### Modelo de voz do Piper (download manual — não vem pelo pip)

Baixe os dois arquivos da voz (modelo + configuração) e coloque em
`software/backend/vozes/`:

```bash
mkdir -p software/backend/vozes
cd software/backend/vozes
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json
```

Para testar outras vozes em português, troque `faber` por `jeff`, `cadu` ou
`edresson` (essa última é qualidade "low", as outras são "medium") nos dois
comandos acima, e atualize `CAMINHO_MODELO_VOZ` em `bmo.py` se for trocar
permanentemente.

### Chave de API da Groq

Crie uma conta em [console.groq.com](https://console.groq.com) e gere uma API
key — ela é necessária tanto para o reconhecimento de fala (Whisper) quanto
para o agente conversacional (LLM). Ver seção 2 para onde colocá-la.

### Áudios pré-gravados

As respostas fixas (saudação, despedida, "tudo bem", jogos, etc.) esperam os
arquivos `.wav` já existentes em `software/backend/audios/`. Se algum estiver
faltando, `bmo.py` avisa no console ao iniciar, mas continua funcionando (cai
no TTS do Piper para aquela resposta).

## 2. Organização do `.env`

**Local exato:** `software/.env` — uma pasta **acima** de `backend/`. O
`bmo.py` sobe um nível a partir de onde ele mesmo está para encontrar o
arquivo, então o `.env` não pode ficar dentro de `backend/`:

```
software/
├── .env                  ← o arquivo fica aqui
├── backend/
│   ├── bmo.py
│   └── vozes/
│       ├── pt_BR-faber-medium.onnx
│       └── pt_BR-faber-medium.onnx.json
└── frontend/
```

**Conteúdo do arquivo** — uma linha, sem aspas e sem espaço em volta do `=`:

```env
GROQ_API_KEY=sua_chave_aqui
```

**Segurança:** nunca comite esse arquivo com a chave preenchida.
- Confirme que `.env` está no `.gitignore` do repositório.
- Se quiser, deixe um `software/.env.example` versionado (com
  `GROQ_API_KEY=` vazio) para quem clonar o projeto saber o que criar.
