#!/data/data/com.termux/files/usr/bin/bash

echo "========================================"
echo "    Iniciando BMO (Interface Gráfica)   "
echo "========================================"

# Verifica se o servidor Termux:X11 está instalado
if ! command -v termux-x11 &> /dev/null; then
    echo "❌ O pacote termux-x11 não foi encontrado!"
    echo "Para instalar, execute os dois comandos abaixo primeiro:"
    echo "  pkg install x11-repo -y"
    echo "  pkg install termux-x11-nightly -y"
    exit 1
fi

# Configura a variável de ambiente para que o Pygame encontre a tela
export DISPLAY=:1

# Verifica se o servidor X11 já está rodando, se não, inicia em segundo plano
if ! pgrep -f "termux-x11 :1" > /dev/null; then
    echo "🚀 Iniciando o servidor de vídeo Termux:X11 em segundo plano..."
    termux-x11 :1 &
    sleep 2 # Aguarda 2 segundos para o servidor ligar completamente
fi

# Abre o aplicativo do Termux:X11 automaticamente na tela do celular
echo "📱 Trocando para o app Termux:X11..."
am start -n com.termux.x11/com.termux.x11.MainActivity > /dev/null 2>&1

echo "🤖 Carregando o BMO..."

# Navega para a pasta do código e executa
cd software || { echo "❌ Pasta software não encontrada!"; exit 1; }
python main.py

echo "🏁 BMO foi encerrado."
