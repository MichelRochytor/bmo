"""Single source of runtime settings shared by the UI and every minigame."""

import os
from pathlib import Path

from dotenv import load_dotenv


SOFTWARE_DIR = Path(__file__).resolve().parent
load_dotenv(SOFTWARE_DIR / ".env")


def env_int(name, default, minimum=1):
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def env_float(name, default, minimum=0.0):
    try:
        return max(minimum, float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def env_color(name, default=(0, 0, 0)):
    try:
        values = tuple(max(0, min(255, int(v.strip()))) for v in os.environ[name].split(","))
        return values if len(values) == 3 else default
    except (KeyError, TypeError, ValueError):
        return default


# Logical BMO canvas. On a 1920x1080 fullscreen desktop, Pygame.SCALED keeps
# this aspect ratio and SDL fills the unused 448 px on each side with black.
LOGICAL_WIDTH = env_int("BMO_LOGICAL_WIDTH", 1024)
LOGICAL_HEIGHT = env_int("BMO_LOGICAL_HEIGHT", 1080)
DISPLAY_WIDTH = env_int("BMO_DISPLAY_WIDTH", 1920)
DISPLAY_HEIGHT = env_int("BMO_DISPLAY_HEIGHT", 1080)
FULLSCREEN = env_bool("BMO_FULLSCREEN", True)
FPS = env_int("BMO_FPS", 60)
BAR_COLOR = env_color("BMO_BAR_COLOR", (0, 0, 0))

# Game pace. These defaults are deliberately calmer for a public event.
SNAKE_FPS = env_int("BMO_SNAKE_FPS", 6)
SNAKE_CELL_SIZE = env_int("BMO_SNAKE_CELL_SIZE", 60, minimum=20)
SPACE_PLAYER_SPEED = env_float("BMO_SPACE_PLAYER_SPEED", 9.0)
SPACE_ENEMY_SPEED_FACTOR = env_float("BMO_SPACE_ENEMY_SPEED_FACTOR", 0.55)
SPACE_MOTHERSHIP_SPEED = env_float("BMO_SPACE_MOTHERSHIP_SPEED", 1.8)
SPACE_SPAWN_FRAMES = env_int("BMO_SPACE_SPAWN_FRAMES", 90)


def pygame_display_flags(pygame):
    flags = pygame.SCALED if hasattr(pygame, "SCALED") else 0
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
    return flags
