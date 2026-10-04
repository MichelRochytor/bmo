"""Single Python launcher for the Planeta do Tesouro C/Raylib game.

Run this file from BMO or with Python.  It builds the game automatically when
the executable is absent or older than a source file, then launches it with
the project's folder as its working directory so maps, sprites, and audio load.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


MINIGAMES_DIR = Path(__file__).resolve().parent
SOFTWARE_DIR = MINIGAMES_DIR.parents[1]
load_dotenv(SOFTWARE_DIR / ".env")

GAME_DIR = MINIGAMES_DIR / "PlanetaDoTesouro-master"
EXECUTABLE = GAME_DIR / "planetadotesouro.exe"
SOURCES = (
    "planetadotesouro.c",
    "manipulaArquivos.c",
    "logicaJogo.c",
    "inimigo.c",
    "desenhos.c",
    "audio.c",
)
WATCHED_FILES = SOURCES + ("includes/desenhos.h",)


def needs_build() -> bool:
    """Return True when no executable exists or sources were changed."""
    if not EXECUTABLE.exists():
        return True

    executable_time = EXECUTABLE.stat().st_mtime
    return any((GAME_DIR / source).stat().st_mtime > executable_time for source in WATCHED_FILES)


def find_make() -> str | None:
    """Accept both common Windows MinGW make command names."""
    return shutil.which("mingw32-make") or shutil.which("make")


def build_game() -> None:
    make = find_make()
    if make:
        command = [make]
    else:
        gcc = shutil.which("gcc")
        if not gcc:
            raise RuntimeError(
                "GCC/MinGW was not found. Install MinGW and add its bin folder to PATH."
            )
        command = [
            gcc,
            "-g",
            "-Wall",
            "-Wextra",
            "-std=c99",
            "-Iincludes",
            *SOURCES,
            "-o",
            EXECUTABLE.name,
            "-Llibwin",
            "-lraylib",
            "-lm",
            "-lopengl32",
            "-lgdi32",
            "-lwinmm",
        ]

    result = subprocess.run(command, cwd=GAME_DIR, check=False)
    if result.returncode != 0 or not EXECUTABLE.exists():
        raise RuntimeError("The game could not be compiled. Check the build messages above.")


def main() -> None:
    if needs_build():
        print("Building Planeta do Tesouro...")
        build_game()

    # cwd is essential: the C game loads recursos/ and mapas/ relatively.
    subprocess.run([str(EXECUTABLE)], cwd=GAME_DIR, check=False)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Launcher error: {error}")
        input("Press Enter to close...")
        sys.exit(1)
