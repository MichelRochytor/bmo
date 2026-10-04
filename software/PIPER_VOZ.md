# Configuração da voz Piper

Piper é TTS: ele transforma texto em áudio. Portanto, `BMO_VOZ_PIPER` deve apontar para o modelo da voz com extensão `.onnx`; não aponte para `.wav`, `.mp3` ou um áudio gravado.

Com os arquivos incluídos neste projeto, não é preciso configurar nada. O BMO usará automaticamente:

```text
software/backend/vozes/dii_pt-BR.onnx
software/backend/vozes/dii_pt-BR.onnx.json
```

Se a voz estiver em outro local, adicione ao `.env`:

```dotenv
BMO_VOZ_PIPER=vozes/dii_pt-BR.onnx
```

Um caminho relativo é resolvido a partir de `software/backend/`. Ao iniciar, o BMO agora mostra um erro claro para caminho vazio, arquivo inexistente, extensão errada ou arquivo `.onnx.json` ausente.
