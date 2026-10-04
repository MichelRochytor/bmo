#!/bin/bash

echo "="
echo "  Instalador Automatizado - Antigravity CLI    "
echo "="
echo ""

echo "⏳ [1/3] Atualizando os repositórios do Termux..."
pkg update -y && pkg upgrade -y

echo "⏳ [2/3] Instalando pacotes básicos (curl, bash)..."
pkg install curl bash -y

echo "⏳ [3/3] Baixando e instalando o Antigravity (com patch)..."

Executa o script da comunidade para aplicar a correção de memória no Android

curl -fsSL https://raw.githubusercontent.com/wallentx/antigravity-cli-termux/dev/install.sh | bash

echo ""
echo "="
echo " ✅ Instalação concluída com sucesso! "
echo "="
echo "ATENÇÃO: O executável 'agy' precisa ser autenticado."
echo "Para fazer o login na sua conta Google e liberar o uso,"
echo "digite o seguinte comando no terminal:"
echo ""
echo "  agy"
echo ""
