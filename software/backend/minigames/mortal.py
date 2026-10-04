"""
mortal.py
============================================
Script wrapper para iniciar o jogo Mortal (UTFPR Arena)
a partir do BMO.
============================================
"""

import os
import sys
import subprocess

def main():
    # Caminho atual (esta pasta: backend/minigames)
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Pasta raiz do projeto Mortal: ../../mortal
    pasta_mortal = os.path.normpath(os.path.join(pasta_atual, "mortal"))
    script_mortal = os.path.join(pasta_mortal, "main.py")
    
    if os.path.exists(script_mortal):
        # Executa o main.py do Mortal como um processo filho que domina essa thread temporária
        # Definimos 'cwd' para a pasta 'mortal' para garantir que os assets do jogo
        # (imagens/fontes) sejam carregados corretamente.
        resultado = subprocess.run([sys.executable, script_mortal], cwd=pasta_mortal)
        sys.exit(resultado.returncode)
    else:
        print(f"Erro: Jogo Mortal não encontrado no caminho {script_mortal}")
        sys.exit(1)

if __name__ == "__main__":
    main()
