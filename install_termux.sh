#!/data/data/com.termux/files/usr/bin/bash

echo "========================================"
echo "  Instalador de Dependências do Termux"
echo "  Projeto BMO"
echo "========================================"
echo ""

# 1. Atualizar pacotes
echo "⏳ [1/5] Atualizando pacotes do Termux..."
pkg update -y && pkg upgrade -y

# 2. Instalar dependências básicas de compilação e ferramentas
echo "⏳ [2/5] Instalando dependências do sistema e compiladores..."
pkg install -y clang make pkg-config binutils libffi openssl libjpeg-turbo git

# 3. Instalar Python e bibliotecas necessárias (Áudio, SDL para Pygame, etc)
echo "⏳ [3/5] Instalando Python, PortAudio (Microfone) e SDL (Pygame)..."
pkg install -y python python-pip \
    portaudio \
    freetype sdl2 sdl2-image sdl2-mixer sdl2-ttf

# Instala repositório TUR para pacotes Python pré-compilados do Termux
pkg install -y tur-repo

# 4. Instalar bibliotecas complexas via gerenciador de pacotes do Termux (evita falhas de compilação do pip)
echo "⏳ [4/5] Instalando Numpy via pkg do Termux (mais rápido e seguro)..."
pkg install -y python-numpy python-pillow

# 5. Atualizar PIP e instalar dependências do Python
echo "⏳ [5/5] Atualizando o pip e instalando dependências do software..."
pip install --upgrade pip setuptools wheel

# Entra na pasta software para achar o requirements.txt
cd software || { echo "❌ Pasta software não encontrada!"; exit 1; }

# Instala as dependências restantes (PyAudio, Pygame, SpeechRecognition, etc)
# CFLAGS/LDFLAGS podem ser necessários para PyAudio achar o portaudio no Termux
echo "Instalando módulos Python (pode demorar alguns minutos)..."
CFLAGS="-I/data/data/com.termux/files/usr/include" LDFLAGS="-L/data/data/com.termux/files/usr/lib" pip install -r requirements.txt

echo ""
echo "========================================"
echo "✅ Instalação das dependências finalizada!"
echo "========================================"
echo "Nota: O Termux utiliza uma biblioteca C (Bionic) diferente do Linux padrão (Glibc)."
echo "Se algum pacote específico como 'piper-tts' ou 'onnxruntime' falhar,"
echo "pode ser necessário instalá-los compilando da fonte ou usar um proot-distro (Ubuntu no Termux)."
