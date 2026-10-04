# Fluxo de voz do BMO para evento

O ciclo agora é: calibração curta do ambiente, captura cancelável, redução de ruído, Whisper com indicadores de incerteza, segunda tentativa pelo áudio original quando necessário, conversa, TTS.

## Comportamento esperado

- O microfone só fica ativo na tela `Rosto / Conversar`.
- `ESC` cancela a captura em andamento e interrompe uma fala imediatamente.
- Resultado de STT ou IA que chegar depois de sair da tela é descartado.
- Uma fala de baixa confiança é transcrita novamente. Se as leituras continuarem incertas ou divergirem, BMO pede para a pessoa repetir em vez de inventar.
- As transcrições ficam em `backend/logs/transcricoes.jsonl`. O áudio não é armazenado. Defina `BMO_SALVAR_TRANSCRICOES=0` para desativar o registro.

## Calibração no local

1. Descubra o índice correto com `python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"` e configure `BMO_MIC_INDEX`.
2. Deixe o microfone na posição final e entre na tela de conversa durante o ruído normal do evento.
3. Se BMO começar a ouvir o público distante, aumente `BMO_ENERGIA_MINIMA` em passos de 100.
4. Se ignorar pessoas próximas, diminua `BMO_ENERGIA_MINIMA` ou aumente `BMO_ENERGIA_MAXIMA`.
5. Use microfone cardioide próximo ao visitante e mantenha o alto-falante afastado e apontado para outra direção. O filtro ajuda com ruído constante, mas posicionamento físico continua sendo o maior ganho.

Copie `.env.example` para `.env`, preserve a chave real apenas no equipamento e nunca distribua o arquivo `.env`.
