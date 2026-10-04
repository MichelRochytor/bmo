"""Mortal UTFPR - local fighting game using the user's original character art."""
from __future__ import annotations

import ctypes
import math
import os
import random
import sys
from array import array
from pathlib import Path

# A local dependency folder is supported so the project can be tested without
# changing the system-wide Python installation.
ROOT = Path(__file__).resolve().parent
LOCAL_DEPS = ROOT / ".deps"
RUNTIME_DEPS = ROOT / ".runtime-deps"
if RUNTIME_DEPS.exists():
    sys.path.insert(0, str(RUNTIME_DEPS))
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ranking
import config
import pygame

try:
    from pygame._sdl2 import controller as sdl_controller
except (ImportError, AttributeError):
    sdl_controller = None

from characters import ROSTER, FighterSpec

try:
    import numpy as np
except ImportError:
    np = None


# The combat HUD and arena coordinates were designed on this virtual canvas.
# Pygame scales it to the actual display resolution below (for example,
# 1920x1080) so the entire composition grows together.
WIDTH, HEIGHT = 1280, 720
GROUND_Y = 608
FPS = config.FPS
DEFAULT_ART_ROOT = Path.home() / "Downloads" / "Mortal_UTFPR_AP"
ART_ROOT = Path(os.environ.get("MORTAL_UTFPR_ART", DEFAULT_ART_ROOT))
BUILTIN_ART_ROOT = ROOT / "assets" / "fighters"
SOUND_ROOT = ROOT / "assets" / "sounds"

BG = (7, 9, 18)
PANEL = (15, 19, 34)
INK = (238, 241, 255)
MUTED = (139, 151, 181)

# SDL's controller layer normalizes Xbox and PlayStation layouts to the same
# logical A/B/X/Y, shoulder, trigger and D-pad controls.
CONTROLLER_BUTTONS = {
    "a": 0, "b": 1, "x": 2, "y": 3, "back": 4, "start": 6,
    "leftstick": 7, "rightstick": 8, "leftshoulder": 9,
    "rightshoulder": 10, "dpad_up": 11, "dpad_down": 12,
    "dpad_left": 13, "dpad_right": 14,
}
CONTROLLER_AXES = {"leftx": 0, "lefty": 1, "triggerleft": 4, "triggerright": 5}

CHARACTER_HIT_SOUNDS = {
    "caecomp": ("hit_caecomp",),
    "caetx": ("hit_caetx",),
    "caec": ("hit_caec", "hit_caec_alt"),
    "caliq": ("hit_caliq",),
    "roboap": ("hit_roboap",),
    "pantherion": ("hit_pantherion",),
    "caeq": ("hit_caeq", "hit_caeq_alt"),
    "codificadoras": ("hit_codificadoras",),
    "cael": ("hit_cael",),
    "cadem": ("hit_cadem", "hit_cadem_alt"),
}


def clamp(value, low, high):
    return max(low, min(high, value))


class SoundBank:
    """Sound effects for the game.

    Drop real audio files into assets/sounds/ named after the events below
    (hit_light.wav, hit_heavy.ogg, block.mp3, ...) and they'll be used
    automatically -- .wav, .ogg and .mp3 are all supported. Anything that
    isn't provided is synthesized on the fly instead, so the game always
    has sound even before real SFX are recorded or sourced.
    """

    EVENTS = ("hit_light", "hit_heavy", "hit_kick", "block", "jump", "land",
              "special", "throw", "fatality", "fatality_roboap",
              "victory", "game_over", "select", "move", "round_start",
              "background_music", "timer_warning", "hit_caecomp", "hit_caetx",
              "hit_caec", "hit_caliq", "hit_roboap", "hit_pantherion",
              "hit_caeq", "hit_codificadoras", "hit_cael", "hit_cadem",
              "hit_caec_alt", "hit_caeq_alt", "hit_cadem_alt")

    def __init__(self):
        self.enabled = False
        self.cache: dict[str, "pygame.mixer.Sound"] = {}
        # Try a few driver configurations: the default from pre_init first,
        # then a couple of safer fallbacks for machines where 44.1kHz stereo
        # isn't available. We only report a warning if every attempt fails,
        # so the game keeps working (silently) either way.
        attempts = [None, (44100, -16, 2, 512), (44100, -16, 1, 512), (22050, -16, 2, 512)]
        try:
            init = pygame.mixer.get_init()
        except NotImplementedError as exc:
            init = None
            last_error = exc
        else:
            last_error = None
        for attempt in attempts:
            if init:
                break
            try:
                if attempt is None:
                    pygame.mixer.init()
                else:
                    pygame.mixer.init(*attempt)
                init = pygame.mixer.get_init()
            except (pygame.error, NotImplementedError) as exc:
                last_error = exc
        if not init:
            print(f"[audio] Não foi possível inicializar o áudio ({last_error}). O jogo vai rodar sem som.")
            return
        self.enabled = True
        self.sample_rate = init[0] if init[0] > 0 else 44100
        self.channels = init[2]
        pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
        pygame.mixer.set_reserved(2)
        self.loop_channels = {
            "background_music": pygame.mixer.Channel(0),
            "timer_warning": pygame.mixer.Channel(1),
        }
        missing = []
        for name in self.EVENTS:
            sound = self._load(name)
            if sound is None:
                sound = self._synth(name)
            if sound is not None:
                self.cache[name] = sound
            else:
                missing.append(name)
        if missing:
            print(f"[audio] Sons não carregados: {', '.join(missing)}")

    def _load(self, name: str):
        if not SOUND_ROOT.exists():
            return None
        for ext in (".wav", ".ogg", ".mp3"):
            path = SOUND_ROOT / f"{name}{ext}"
            if path.exists():
                try:
                    return pygame.mixer.Sound(str(path))
                except pygame.error:
                    pass
        return None

    def _synth(self, name: str):
        """Procedurally generates a short placeholder sound so every action
        has feedback immediately, without needing any audio assets."""
        if np is None:
            return self._synth_without_numpy(name)
        sr = self.sample_rate

        def tone(freq, dur, wave="sine", decay=6.0, vol=1.0, sweep=0.0):
            t = np.linspace(0, dur, max(1, int(sr * dur)), False)
            f = freq + sweep * t
            if wave == "square":
                w = np.sign(np.sin(2 * np.pi * f * t))
            else:
                w = np.sin(2 * np.pi * f * t)
            env = np.exp(-decay * t / max(dur, 1e-6))
            return w * env * vol

        def noise(dur, decay=10.0, vol=1.0, smooth=1):
            t = np.linspace(0, dur, max(1, int(sr * dur)), False)
            w = np.random.uniform(-1, 1, t.shape)
            if smooth > 1:
                kernel = np.ones(smooth) / smooth
                w = np.convolve(w, kernel, mode="same")
            env = np.exp(-decay * t / max(dur, 1e-6))
            return w * env * vol

        def notes(pairs):
            parts = [tone(f, d, "sine", 3.2, 0.5) for f, d in pairs]
            return np.concatenate(parts)

        def mix(*parts):
            length = max(p.shape[0] for p in parts)
            out = np.zeros(length)
            for p in parts:
                out[: p.shape[0]] += p
            return out

        if name == "hit_light":
            wave = mix(noise(0.09, 14, 0.75, 2), tone(190, 0.09, "square", 10, 0.3))
        elif name == "hit_heavy":
            wave = mix(noise(0.20, 7, 0.9, 6), tone(85, 0.20, "sine", 4.5, 0.6))
        elif name == "hit_kick":
            wave = mix(noise(0.14, 9, 0.85, 4), tone(130, 0.14, "square", 6.5, 0.4))
        elif name == "block":
            wave = mix(tone(520, 0.08, "square", 14, 0.45), noise(0.06, 18, 0.25, 3))
        elif name == "jump":
            wave = tone(260, 0.14, "sine", 5, 0.4, sweep=900)
        elif name == "land":
            wave = mix(noise(0.08, 16, 0.5, 3), tone(70, 0.08, "sine", 10, 0.3))
        elif name == "special":
            wave = tone(700, 0.35, "sine", 3, 0.5, sweep=-500)
        elif name == "throw":
            wave = mix(tone(420, 0.22, "sine", 4, 0.5, sweep=-260), noise(0.10, 12, 0.3, 3))
        elif name == "fatality":
            wave = mix(tone(130, 0.9, "sine", 2, 0.65, sweep=-70), noise(0.9, 3, 0.35, 10))
        elif name == "victory":
            wave = notes([(523, 0.12), (659, 0.12), (784, 0.30)])
        elif name == "select":
            wave = tone(700, 0.05, "square", 16, 0.35)
        elif name == "move":
            wave = tone(400, 0.035, "square", 20, 0.25)
        elif name == "round_start":
            wave = notes([(392, 0.10), (392, 0.10), (523, 0.30)])
        else:
            wave = tone(440, 0.1, "sine", 8, 0.3)

        wave = np.clip(wave, -1, 1)
        pcm = (wave * 32767).astype(np.int16)
        if self.channels == 2:
            pcm = np.column_stack([pcm, pcm])
        try:
            return pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
        except Exception as exc:
            print(f"[audio] Falha ao gerar som '{name}': {exc}")
            return None

    def _synth_without_numpy(self, name: str):
        """Generate event sounds with only Python/Pygame (no NumPy required)."""
        presets = {
            "hit_light": (0.09, 190, "square", 11.0, 0.46, 0),
            "hit_heavy": (0.20, 85, "sine", 5.0, 0.68, -25),
            "hit_kick": (0.14, 130, "square", 7.0, 0.58, -35),
            "block": (0.08, 520, "square", 13.0, 0.40, -80),
            "jump": (0.14, 260, "sine", 5.0, 0.38, 900),
            "land": (0.09, 72, "sine", 11.0, 0.48, -20),
            "special": (0.35, 700, "sine", 3.0, 0.52, -500),
            "throw": (0.22, 420, "sine", 4.0, 0.55, -260),
            "fatality": (0.90, 130, "sine", 2.0, 0.68, -70),
            "victory": (0.42, 523, "sine", 2.4, 0.44, 330),
            "select": (0.05, 700, "square", 16.0, 0.34, 0),
            "move": (0.035, 400, "square", 20.0, 0.24, 0),
        }
        duration, frequency, wave, decay, volume, sweep = presets.get(
            name, (0.10, 440, "sine", 8.0, 0.30, 0)
        )
        pcm = array("h")
        for index in range(max(1, int(self.sample_rate * duration))):
            t = index / self.sample_rate
            phase = 2 * math.pi * (frequency * t + 0.5 * sweep * t * t)
            signal = math.sin(phase)
            if wave == "square":
                signal = 1.0 if signal >= 0 else -1.0
            # A little noise gives impacts weight without requiring audio files.
            noise_amount = 0.32 if name.startswith("hit_") or name in ("block", "land") else 0.0
            signal = signal * (1 - noise_amount) + random.uniform(-1, 1) * noise_amount
            envelope = math.exp(-decay * t / max(duration, 1e-6))
            sample = int(clamp(signal * envelope * volume, -1.0, 1.0) * 32767)
            if self.channels == 2:
                pcm.extend((sample, sample))
            else:
                pcm.append(sample)
        try:
            return pygame.mixer.Sound(buffer=pcm.tobytes())
        except pygame.error as exc:
            print(f"[audio] Falha ao gerar som '{name}': {exc}")
            return None

    def play(self, name: str, volume: float = 1.0, maxtime: int = 0):
        if not self.enabled:
            return
        sound = self.cache.get(name)
        if sound is not None:
            sound.set_volume(clamp(volume, 0.0, 1.0))
            sound.play(maxtime=max(0, maxtime))

    def play_loop(self, name: str, volume: float = 1.0, fade_ms: int = 0):
        """Play long ambience/alerts once and keep looping on their own channel."""
        if not self.enabled:
            return
        sound = self.cache.get(name)
        channel = self.loop_channels.get(name)
        if sound is not None and channel is not None and not channel.get_busy():
            channel.set_volume(clamp(volume, 0.0, 1.0))
            channel.play(sound, loops=-1, fade_ms=fade_ms)

    def stop_loop(self, name: str, fade_ms: int = 0):
        if not self.enabled:
            return
        channel = self.loop_channels.get(name)
        if channel is not None:
            channel.fadeout(fade_ms) if fade_ms else channel.stop()

    def stop_battle_audio(self):
        self.stop_loop("timer_warning", 150)
        self.stop_loop("background_music", 350)


class ArtBank:
    """Finds the supplied PNGs even when early folders use inconsistent filenames."""

    KEYWORDS = {
        "idle": ("idle", "select", "standing", "walk_forward", "walk"),
        "walk": ("walk_forward", "walk", "idle", "select"),
        "jump": ("jump", "air", "idle"),
        "crouch": ("crouch", "fall", "idle"),
        "block": ("block", "defense", "idle"),
        "hit": ("hit", "fall", "idle"),
        "light": ("combo_1", "basic_combo_1", "combo", "attack", "idle"),
        "heavy": ("combo_2", "basic_combo_2", "combo", "attack", "idle"),
        "kick": ("combo_3", "basic_combo_3", "combo", "attack", "idle"),
        "throw": ("combo_2", "basic_combo_2", "grab", "throw", "hit", "idle"),
        "special1": ("special", "idle"),
        "special2": ("special", "idle"),
        "special3": ("special", "idle"),
        "victory": ("victory", "idle"),
        "fatality": ("fatality_finish", "fatality_complete", "fatality", "victory", "idle"),
        "portrait": ("portrait", "select", "idle"),
    }

    # Each character's three special moves have their own uniquely named
    # artwork (e.g. cael_choque_eletrico.png), but the filenames don't follow
    # one shared convention across characters (some are in Portuguese, some
    # in English, ordering varies). A generic keyword search can't reliably
    # tell them apart, so we pin each character's special1/2/3 to the exact
    # file that matches that character's own move names, in order.
    SPECIAL_ART = {
        "caecomp": ("kernel_panic", "overclock", "packet_storm"),
        "caetx": ("trama_secreta", "fibra_imparavel", "tecido_protetor"),
        "caec": ("fundacao_inabalavel", "construcao_perfeita", "estrutura_suprema"),
        "caliq": ("chain_reaction", "toxic_solution", "transformation_green"),
        "roboap": ("protocolo_alfa", "sistema_robotico", "upgrade_total"),
        "pantherion": ("sharp_claw", "deadly_elegance_1", "dominant_comfort"),
        "caeq": ("sintese_precisa_shot", "pressure_control", "elemento_surpresa_frio"),
        "codificadoras": ("code_attack", "firewall", "system_break"),
        "cael": ("choque_eletrico", "circuito_sobrecarregado", "campo_eletromagnetico"),
        "cadem": ("precise_cut", "deadly_stitch", "unique_style"),
    }

    # A couple of characters don't have combo_1/2/3-style files at all, so
    # the light/heavy/kick fallback keywords have nothing to find and all
    # three collapse onto the same picture. Pin those to specific files too.
    NORMAL_ART = {
        "caecomp": ("packet_projectile", "tentacle_attack", "combat_idle"),
    }

    # Order in which a character's fatality stills should play as a mini
    # cutscene, when a folder provides several fatality-tagged frames.
    FATALITY_ORDER = ("lock", "scan", "disassembly", "aftermath", "complete", "finish")

    def __init__(self):
        self.files: dict[str, list[Path]] = {}
        self.cache: dict[tuple[str, int, bool], pygame.Surface | None] = {}
        for fighter in ROSTER:
            bundled = BUILTIN_ART_ROOT / fighter.folder
            folder = bundled if bundled.exists() else ART_ROOT / fighter.folder
            if folder.exists():
                self.files[fighter.key] = sorted(folder.glob("*.png"))
            else:
                self.files[fighter.key] = []

    def _pick(self, fighter: FighterSpec, state: str) -> Path | None:
        files = self.files.get(fighter.key, [])
        if not files:
            return None
        if state in ("special1", "special2", "special3"):
            override = self.SPECIAL_ART.get(fighter.key)
            if override:
                target = override[int(state[-1]) - 1]
                for file in files:
                    if target.lower() in file.stem.lower():
                        return file
        if state in ("light", "heavy", "kick"):
            override = self.NORMAL_ART.get(fighter.key)
            if override:
                target = override[("light", "heavy", "kick").index(state)]
                for file in files:
                    if target.lower() in file.stem.lower():
                        return file
        for word in self.KEYWORDS.get(state, (state, "idle")):
            for file in files:
                if word.lower() in file.stem.lower():
                    return file
        return files[0]

    def _load(self, source: Path, height: int, flip: bool) -> pygame.Surface | None:
        """Load a PNG, crop it to its actual visible pixels, then scale to
        ``height``. Cropping first means every character ends up the same
        real height on screen, regardless of how much transparent padding
        the original artwork happened to have around the body."""
        key = (str(source), height, flip)
        if key in self.cache:
            return self.cache[key]
        try:
            raw = pygame.image.load(str(source)).convert_alpha()
            rects = pygame.mask.from_surface(raw).get_bounding_rects()
            if rects:
                bbox = rects[0].unionall(rects[1:])
            else:
                bbox = raw.get_rect()
            pad = max(2, int(bbox.height * 0.015))
            crop = bbox.inflate(pad * 2, pad * 2).clip(raw.get_rect())
            cropped = raw.subsurface(crop).copy()
            scale = height / max(1, cropped.get_height())
            image = pygame.transform.smoothscale(cropped, (max(1, int(cropped.get_width() * scale)), height))
            if flip:
                image = pygame.transform.flip(image, True, False)
            self.cache[key] = image
            return image
        except pygame.error:
            self.cache[key] = None
            return None

    def image(self, fighter: FighterSpec, state: str, height: int, flip: bool) -> pygame.Surface | None:
        source = self._pick(fighter, state)
        if source is None:
            return None
        return self._load(source, height, flip)

    def _is_scene(self, source: Path) -> bool:
        """True when a fatality still already has its own baked-in
        background (near-fully opaque), as opposed to an isolated character
        on a transparent background. Those need to be displayed full-screen
        instead of floating like a small card over the arena."""
        try:
            raw = pygame.image.load(str(source)).convert_alpha()
            filled = pygame.mask.from_surface(raw).count()
            total = raw.get_width() * raw.get_height()
            return total > 0 and filled / total > 0.92
        except pygame.error:
            return False

    def fatality_frames(self, fighter: FighterSpec, height: int, flip: bool) -> list[tuple[pygame.Surface, bool]]:
        """Return the full fatality still sequence for a character, ordered
        as a mini cutscene (lock-on -> scan -> finisher -> aftermath), so the
        move plays out instead of showing a single frozen frame. Each entry
        is (surface, is_scene) -- scene stills already have a background and
        are pre-scaled to the screen's full height (no cropping, so nothing
        important like the character's head gets cut off) instead of the
        smaller floating-character treatment used for the other stills.
        Any leftover space is filled with black rather than the arena, so it
        doesn't look like the picture is floating over the wrong scene."""
        files = self.files.get(fighter.key, [])
        tagged = [f for f in files if "fatality" in f.stem.lower()]

        def rank(f: Path) -> int:
            stem = f.stem.lower()
            for index, word in enumerate(self.FATALITY_ORDER):
                if word in stem:
                    return index
            return len(self.FATALITY_ORDER)

        tagged.sort(key=rank)
        if not tagged:
            single = self._pick(fighter, "fatality")
            tagged = [single] if single else []
        frames: list[tuple[pygame.Surface, bool]] = []
        for path in tagged:
            is_scene = self._is_scene(path)
            frame = self._load(path, HEIGHT if is_scene else height, flip)
            if frame:
                frames.append((frame, is_scene))
        return frames


class Fighter:
    def __init__(self, spec: FighterSpec, side: int, is_cpu: bool = False):
        self.spec, self.side, self.is_cpu = spec, side, is_cpu
        self.x = 300 if side == 1 else WIDTH - 300
        self.y = GROUND_Y
        self.vy = 0.0
        self.health = 100.0
        self.meter = 20.0
        self.state = "idle"
        self.facing = 1 if side == 1 else -1
        self.attack: str | None = None
        self.attack_timer = 0.0
        self.cooldown = 0.0
        self.hit_stun = 0.0
        self.blocking = False
        self.combo = 0
        self.combo_window = 0.0
        self.ai_timer = 0.0
        self.last_damage = 0.0
        self._reach = 0.0
        self._vrange = 130
        self._connected = True
        self._is_air_attack = False
        self._was_airborne = False
        self.just_landed = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x - 52), int(self.y - 228), 104, 228)

    @property
    def airborne(self):
        return self.y < GROUND_Y - 1

    def reset_round(self, side: int):
        self.side = side
        self.x = 300 if side == 1 else WIDTH - 300
        self.y = GROUND_Y
        self.vy = 0
        self.health, self.meter = 100.0, 20.0
        self.state, self.attack = "idle", None
        self.attack_timer = self.cooldown = self.hit_stun = 0.0
        self.blocking = False
        self.combo = 0
        self.combo_window = 0

    def update(self, dt: float):
        self.cooldown = max(0.0, self.cooldown - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.hit_stun = max(0.0, self.hit_stun - dt)
        self.combo_window = max(0.0, self.combo_window - dt)
        if self.combo_window == 0:
            self.combo = 0
        if self.attack_timer == 0 and self.attack:
            self.attack = None
            if not self.airborne and self.hit_stun == 0:
                self.state = "idle"
        self.vy += 1620 * dt
        self.y += self.vy * dt
        if self.y >= GROUND_Y:
            self.y, self.vy = GROUND_Y, 0
        now_airborne = self.airborne
        self.just_landed = self._was_airborne and not now_airborne
        if self.just_landed and self._is_air_attack:
            # Landing recovery: committing to an air attack leaves a short
            # window of vulnerability on landing, like a real jump-in risk.
            self.cooldown = max(self.cooldown, 0.25)
            self._is_air_attack = False
        self._was_airborne = now_airborne
        if self.hit_stun == 0 and not self.attack and not self.blocking and not self.airborne:
            self.state = "idle"

    def move(self, direction: int, dt: float):
        if self.hit_stun > 0 or self.attack or self.blocking:
            return
        speed = 250 + self.spec.speed * 1.55
        self.x = clamp(self.x + direction * speed * dt, 70, WIDTH - 70)
        if not self.airborne:
            self.state = "walk"

    def jump(self) -> bool:
        if not self.airborne and self.hit_stun == 0 and not self.attack:
            self.vy = -690
            self.state = "jump"
            return True
        return False

    def crouch(self, enabled: bool):
        if not self.airborne and self.hit_stun == 0 and not self.attack:
            self.state = "crouch" if enabled else "idle"

    def block(self, enabled: bool):
        if not self.airborne and self.hit_stun == 0 and not self.attack:
            self.blocking = enabled
            self.state = "block" if enabled else "idle"

    def start_attack(self, kind: str) -> bool:
        if self.cooldown > 0 or self.hit_stun > 0 or self.attack or self.blocking:
            return False
        values = {
            "light": (7, 175, 0.27, 0.20, "light", 130),
            "heavy": (13, 195, 0.45, 0.36, "heavy", 130),
            "kick": (10, 210, 0.35, 0.28, "kick", 130),
            "special1": (15, 240, 0.55, 0.52, "special1", 150),
            "special2": (11, 205, 0.46, 0.48, "special2", 150),
            "special3": (20, 270, 0.70, 0.72, "special3", 150),
            "fatality": (42, 260, 1.1, 1.1, "fatality", 200),
        }
        # Jump-ins hit differently than grounded normals: quicker, a bit
        # more reach to catch approaching opponents, and a taller hit window
        # since the attacker is descending diagonally rather than standing
        # still. The trade-off is the landing recovery applied in update().
        air_values = {
            "light": (9, 180, 0.22, 0.30, "light", 175),
            "heavy": (15, 200, 0.38, 0.50, "heavy", 175),
            "kick": (13, 210, 0.30, 0.42, "kick", 175),
        }
        is_air = self.airborne and kind in air_values
        damage, reach, duration, cooldown, art_state, vrange = air_values[kind] if is_air else values[kind]
        if kind.startswith("special") and self.meter < 18:
            return False
        if kind.startswith("special"):
            self.meter -= 18
        self.attack = kind
        self.attack_timer = duration
        self.cooldown = cooldown
        self.state = art_state
        self.last_damage = damage + self.spec.power * 0.055 + (self.spec.technique - 70) * (0.05 if kind.startswith("special") else 0)
        self._reach = reach
        self._vrange = vrange
        self._connected = False
        self._is_air_attack = is_air
        return True

    def start_throw(self, enemy: "Fighter") -> bool:
        """Instant grab: ignores blocking entirely, so an opponent who just
        holds block forever can still be broken open, like a throw in a real
        fighting game. Only works at point-blank range, grounded, and can't
        be used while the enemy is already reeling from something else."""
        if self.cooldown > 0 or self.hit_stun > 0 or self.attack or self.airborne:
            return False
        if enemy.airborne or enemy.hit_stun > 0 or enemy.attack == "throw":
            return False
        if abs(enemy.x - self.x) > 165 or abs(enemy.y - self.y) > 40:
            return False
        damage = 12 + self.spec.power * 0.05
        enemy.health = max(0.0, enemy.health - damage)
        enemy.blocking = False
        enemy.hit_stun = 0.55
        enemy.state = "hit"
        enemy.combo = 0
        enemy.combo_window = 0.0
        direction = 1 if self.x < enemy.x else -1
        enemy.x = clamp(enemy.x + direction * 130, 65, WIDTH - 65)
        self.x = clamp(self.x - direction * 10, 65, WIDTH - 65)
        self.meter = clamp(self.meter + 6, 0, 100)
        enemy.meter = clamp(enemy.meter + 4, 0, 100)
        self.attack = "throw"
        self.attack_timer = 0.3
        self.cooldown = 0.55
        self.state = "throw"
        self._connected = True
        self._reach = 0.0
        return True

    def can_hit(self, enemy: "Fighter") -> bool:
        return bool(self.attack and not self._connected and abs(enemy.x - self.x) < self._reach and abs(enemy.y - self.y) < self._vrange)

    def hit(self, damage: float, attacker: "Fighter"):
        blocked = self.blocking and ((attacker.x < self.x and self.facing == -1) or (attacker.x > self.x and self.facing == 1))
        mitigation = self.spec.defense * 0.0032 + (0.48 if blocked else 0)
        # Combo damage scaling: each successive hit in an ongoing combo does
        # less, MK-style, so landing one clean hit matters more than mashing.
        combo_count = attacker.combo if attacker.combo_window > 0 else 0
        scaling = max(0.4, 1 - 0.15 * combo_count)
        actual = max(1.0, damage * (1 - mitigation) * scaling)
        self.health = max(0, self.health - actual)
        self.meter = clamp(self.meter + 8 + actual * 0.15, 0, 100)
        if not blocked:
            self.hit_stun = 0.20 + actual * 0.006
            self.state = "hit"
            self.x = clamp(self.x + (1 if attacker.x < self.x else -1) * (12 + actual), 65, WIDTH - 65)
        else:
            # Small chip pushback so blocking still creates spacing, instead
            # of the defender staying glued in place.
            push_dir = 1 if attacker.x < self.x else -1
            self.x = clamp(self.x + push_dir * 10, 65, WIDTH - 65)
            attacker.x = clamp(attacker.x - push_dir * 6, 65, WIDTH - 65)
        attacker.meter = clamp(attacker.meter + 5 + actual * 0.18, 0, 100)
        attacker.combo = attacker.combo + 1 if attacker.combo_window > 0 else 1
        attacker.combo_window = 1.3
        return actual, blocked


class Game:
    def __init__(self):
        # pre_init must run before pygame.init() to reliably control the
        # audio device settings across platforms; pygame.init() alone tends
        # to silently pick defaults that don't always work.
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except (pygame.error, NotImplementedError):
            pass
        pygame.init()
        pygame.display.set_caption("MORTAL UTFPR — Arena dos Cursos")
        # Mortal keeps its original 1280x720 design canvas, then composes it
        # inside the shared 1024x1080 BMO canvas. This prevents hundreds of old
        # arena coordinates from stretching while every window follows .env.
        self.display = pygame.display.set_mode(
            (config.LARGURA, config.ALTURA), config.display_flags(pygame)
        )
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 16, bold=True)
        self.tiny = pygame.font.SysFont("arial", 12, bold=True)
        self.big = pygame.font.SysFont("impact", 62)
        self.huge = pygame.font.SysFont("impact", 92)
        self.art = ArtBank()
        self.sfx = SoundBank()
        # The arena ambience begins with the game and stays deliberately low
        # beneath menu voices and combat effects.
        self.sfx.play_loop("background_music", 0.05, 800)
        self.scene = "title"
        self.mode = "cpu"
        self.selection = [0, 1]
        self.selecting_player = 0
        self.p1: Fighter | None = None
        self.p2: Fighter | None = None
        self.round_over = 0.0
        self.winner: Fighter | None = None
        self.notice = ""
        self.notice_timer = 0.0
        self.particles: list[dict] = []
        self.menu_index = 0
        self.match_time = 90.0
        self.fatality_winner: Fighter | None = None
        self.finish_target: Fighter | None = None
        self.finisher: Fighter | None = None

        self.finish_timer = 0.0
        self.hitstop = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.fatality_playing = False
        self.fatality_frames_list: list[pygame.Surface] = []
        self.fatality_stage = 0
        self.fatality_stage_time = 0.0
        self.timer_warning_started = False
        self.game_over_played = False
        self.controllers = []
        self.controller_latches: dict[tuple[int, str], bool] = {}
        self.joysticks = config.init_joystick()
        self.refresh_controllers()
        self.ui = {}
        for key, name in (("title", "utfpr_entrada.png"), ("arena", "utfpr_arena.png"), ("select", "selecao.png")):
            try:
                image = pygame.image.load(str(ROOT / "assets" / "ui" / name)).convert()
                self.ui[key] = pygame.transform.smoothscale(image, (WIDTH, HEIGHT))
            except (pygame.error, FileNotFoundError):
                self.ui[key] = None

    def present(self):
        """Center the legacy arena in the configured logical BMO screen."""
        self.display.fill(config.BARRA_COR)
        escala = min(config.LARGURA / WIDTH, config.ALTURA / HEIGHT)
        tamanho = (max(1, round(WIDTH * escala)), max(1, round(HEIGHT * escala)))
        quadro = pygame.transform.scale(self.screen, tamanho)
        destino = ((config.LARGURA - tamanho[0]) // 2, (config.ALTURA - tamanho[1]) // 2)
        self.display.blit(quadro, destino)
        pygame.display.flip()

    def bring_window_to_front(self):
        """Place this game's window above the BMO launcher on Windows."""
        if sys.platform != "win32":
            return

        try:
            hwnd = pygame.display.get_wm_info()["window"]
            HWND_TOPMOST = -1
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040

            ctypes.windll.user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW,
            )
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except (AttributeError, KeyError, OSError):
            pass

    def refresh_controllers(self):
        """Open every SDL-compatible PS4/Xbox-style controller currently attached."""
        self.controllers = []
        if sdl_controller is not None:
            try:
                if not sdl_controller.get_init():
                    sdl_controller.init()
                for index in range(sdl_controller.get_count()):
                    if sdl_controller.is_controller(index):
                        self.controllers.append(sdl_controller.Controller(index))
            except (pygame.error, AttributeError) as exc:
                print(f"[controle] Não foi possível iniciar os controles SDL ({exc}).")
        
        # Fallback to standard Pygame joysticks for generic controllers (e.g. PS2 USB adapter)
        if not self.controllers and hasattr(self, 'joysticks') and self.joysticks:
            self.controllers = list(self.joysticks)

        self.controller_latches.clear()
        if self.controllers:
            names = [pad.get_name() if not hasattr(pad, 'as_joystick') else (pad.as_joystick().get_name() or "Controle") for pad in self.controllers]
            print(f"[controle] Conectados: {', '.join(names)}")

    def controller_button(self, pad, name: str) -> bool:
        if not hasattr(pad, 'as_joystick'):
            try:
                if name == "a": return pad.get_button(2) or pad.get_button(0)
                if name == "b": return pad.get_button(1)
                if name == "x": return pad.get_button(3)
                if name == "y": return pad.get_button(0)
                if name == "leftshoulder": return pad.get_button(4) or pad.get_button(6)
                if name == "rightshoulder": return pad.get_button(5) or pad.get_button(7)
                if name == "back": return pad.get_button(8) or pad.get_button(6)
                if name == "start": return pad.get_button(9) or pad.get_button(7)
                if name == "leftstick": return pad.get_button(10)
                if name == "rightstick": return pad.get_button(11)
                if name == "dpad_up": return pad.get_hat(0)[1] == 1 if pad.get_numhats() > 0 else False
                if name == "dpad_down": return pad.get_hat(0)[1] == -1 if pad.get_numhats() > 0 else False
                if name == "dpad_left": return pad.get_hat(0)[0] == -1 if pad.get_numhats() > 0 else False
                if name == "dpad_right": return pad.get_hat(0)[0] == 1 if pad.get_numhats() > 0 else False
            except (pygame.error, IndexError):
                pass
            return False
        try:
            return bool(pad.get_button(CONTROLLER_BUTTONS[name]))
        except (pygame.error, KeyError):
            return False

    def controller_axis(self, pad, name: str) -> int:
        if not hasattr(pad, 'as_joystick'):
            try:
                if name == "leftx" and pad.get_numaxes() > 0: return int(pad.get_axis(0) * 32767)
                if name == "lefty" and pad.get_numaxes() > 1: return int(pad.get_axis(1) * 32767)
                if name == "triggerleft" and pad.get_numaxes() > 2: return int(pad.get_axis(2) * 32767)
                if name == "triggerright" and pad.get_numaxes() > 3: return int(pad.get_axis(3) * 32767)
            except pygame.error:
                pass
            return 0
        try:
            return int(pad.get_axis(CONTROLLER_AXES[name]))
        except (pygame.error, KeyError):
            return 0

    def controller_edge(self, player: int, name: str, active: bool) -> bool:
        key = (player, name)
        previous = self.controller_latches.get(key, False)
        self.controller_latches[key] = active
        return active and not previous

    def controller_for_player(self, player: int):
        if not self.controllers:
            return None
        if player < len(self.controllers):
            return self.controllers[player]
        # One controller can still operate both selection steps; during a
        # two-player fight P2 needs the second connected controller.
        return self.controllers[0] if self.scene != "battle" else None

    def controller_direction(self, pad) -> tuple[int, bool]:
        axis_x = self.controller_axis(pad, "leftx")
        left = self.controller_button(pad, "dpad_left") or axis_x < -12000
        right = self.controller_button(pad, "dpad_right") or axis_x > 12000
        down = self.controller_button(pad, "dpad_down") or self.controller_axis(pad, "lefty") > 12000
        return (int(right) - int(left), down)

    def controller_action_states(self, pad) -> dict[str, bool]:
        return {
            "jump": self.controller_button(pad, "a"),
            "kick": self.controller_button(pad, "b"),
            "light": self.controller_button(pad, "x"),
            "heavy": self.controller_button(pad, "y"),
            "special1": self.controller_button(pad, "leftshoulder"),
            "special2": self.controller_button(pad, "rightshoulder"),
            "throw": self.controller_button(pad, "leftstick") or self.controller_axis(pad, "triggerleft") > 16000,
            "special3": self.controller_button(pad, "rightstick") or self.controller_axis(pad, "triggerright") > 16000,
        }

    def confirm_selection(self):
        self.sfx.play("select")
        if self.selecting_player == 0:
            self.selecting_player = 1
            if self.mode == "cpu":
                choices = [i for i in range(len(ROSTER)) if i != self.selection[0]]
                self.selection[1] = random.choice(choices)
        else:
            self.start_match()

    def prime_selection_latches(self):
        """Prevent a held menu button from confirming twice across scenes."""
        for player, pad in enumerate(self.controllers[:2]):
            self.controller_latches[(player, "select_confirm")] = self.controller_button(pad, "a")
            self.controller_latches[(player, "select_back")] = self.controller_button(pad, "b")

    def gamepad_battle_action(self, player: int, action: str):
        if not self.p1 or not self.p2 or (player == 1 and self.mode == "cpu"):
            return
        fighter = self.p1 if player == 0 else self.p2
        enemy = self.p2 if player == 0 else self.p1
        if self.round_over:
            if action == "jump" or action == "start":
                score = int(self.p1.health * 10) if self.winner == self.p1 else 0
                ranking.mostrar_ranking_e_salvar(
                    self.screen, self.clock, "mortal", score, presenter=self.present
                )
                self.start_match()
            return
        if self.finish_target:
            if fighter is self.finisher and action == "special3":
                if abs(fighter.x - self.finish_target.x) < 220:
                    fighter.start_attack("fatality")
                else:
                    self.notice, self.notice_timer = "CHEGUE MAIS PERTO!", .7
            return
        if action == "jump":
            if fighter.jump():
                self.sfx.play("jump")
        elif action == "throw":
            if fighter.start_throw(enemy):
                self.sfx.play("throw")
        else:
            if fighter.start_attack(action):
                if action.startswith("special"):
                    self.sfx.play("special")
            elif action.startswith("special"):
                self.notice, self.notice_timer = "ENERGIA INSUFICIENTE", .8

    def poll_controllers(self):
        if not self.controllers:
            return
        if self.scene == "title":
            pad = self.controllers[0]
            up = self.controller_button(pad, "dpad_up") or self.controller_axis(pad, "lefty") < -12000
            down = self.controller_button(pad, "dpad_down") or self.controller_axis(pad, "lefty") > 12000
            if self.controller_edge(0, "menu_vertical", up or down):
                self.menu_index = 1 - self.menu_index
                self.sfx.play("move")
            if self.controller_edge(0, "menu_confirm", self.controller_button(pad, "a")):
                self.sfx.play("select")
                self.mode = "cpu" if self.menu_index == 0 else "p2"
                self.selecting_player, self.scene = 0, "select"
                self.prime_selection_latches()
            return
        if self.scene == "select":
            pad_index = self.selecting_player if self.mode == "p2" else 0
            pad = self.controller_for_player(pad_index)
            if pad is None:
                return
            left = self.controller_button(pad, "dpad_left") or self.controller_axis(pad, "leftx") < -12000
            right = self.controller_button(pad, "dpad_right") or self.controller_axis(pad, "leftx") > 12000
            up = self.controller_button(pad, "dpad_up") or self.controller_axis(pad, "lefty") < -12000
            down = self.controller_button(pad, "dpad_down") or self.controller_axis(pad, "lefty") > 12000
            moves = (("select_left", left, -1), ("select_right", right, 1),
                     ("select_up", up, -5), ("select_down", down, 5))
            for token, active, offset in moves:
                if self.controller_edge(pad_index, token, active):
                    self.selection[self.selecting_player] = (self.selection[self.selecting_player] + offset) % len(ROSTER)
                    self.sfx.play("move")
            if self.controller_edge(pad_index, "select_confirm", self.controller_button(pad, "a")):
                self.confirm_selection()
            if self.controller_edge(pad_index, "select_back", self.controller_button(pad, "b")):
                self.scene = "title"
            return
        for player in range(2 if self.mode == "p2" else 1):
            pad = self.controller_for_player(player)
            if pad is None:
                continue
            actions = self.controller_action_states(pad)
            for action, active in actions.items():
                if self.controller_edge(player, f"battle_{action}", active):
                    self.gamepad_battle_action(player, action)
            if self.controller_edge(player, "battle_back", self.controller_button(pad, "back")):
                self.sfx.stop_loop("timer_warning", 150)
                self.scene = "select"

    def text(self, surface, value, font, color, pos, center=False):
        image = font.render(value, True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        surface.blit(image, rect)
        return rect

    def glow(self, surface, color, center, radius):
        layer = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*color, 26), (radius * 2, radius * 2), radius * 2)
        pygame.draw.circle(layer, (*color, 55), (radius * 2, radius * 2), radius)
        surface.blit(layer, (center[0] - radius * 2, center[1] - radius * 2))

    def background(self):
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            pygame.draw.line(self.screen, (int(5 + ratio * 11), int(8 + ratio * 7), int(18 + ratio * 22)), (0, y), (WIDTH, y))
        for x in range(-100, WIDTH + 120, 70):
            pygame.draw.line(self.screen, (22, 29, 51), (x, GROUND_Y), (x + 180, HEIGHT), 1)
        pygame.draw.line(self.screen, (88, 117, 169), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        pygame.draw.rect(self.screen, (6, 8, 14), (0, GROUND_Y + 3, WIDTH, HEIGHT - GROUND_Y))

    def image_background(self, key, darkness=0):
        image = self.ui.get(key)
        if image:
            self.screen.blit(image, (0, 0))
            if darkness:
                shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                shade.fill((0, 0, 0, darkness))
                self.screen.blit(shade, (0, 0))
        else:
            self.background()

    def draw_title(self):
        self.image_background("title")
        # The supplied artwork already contains the complete title composition;
        # only the live selection frame and control hint are drawn on top.
        choices = (pygame.Rect(427, 421, 421, 53), pygame.Rect(427, 486, 421, 53))
        for index, rect in enumerate(choices):
            color = (255, 184, 25) if index == self.menu_index else (80, 73, 61)
            pygame.draw.rect(self.screen, color, rect, 3)
        hint = pygame.Surface((430, 28), pygame.SRCALPHA)
        hint.fill((0, 0, 0, 170))
        self.screen.blit(hint, (425, 676))
        self.text(self.screen, "Direcional/analógico selecionar  •  A/X confirmar", self.small, INK, (WIDTH // 2, 690), True)

    def card(self, index, rect, active, player_label):
        fighter = ROSTER[index]
        color = fighter.accent if active else fighter.color
        pygame.draw.rect(self.screen, (22, 27, 47), rect, border_radius=12)
        pygame.draw.rect(self.screen, color, rect, 4 if active else 1, border_radius=12)
        compact = rect.width < 120
        image = self.art.image(fighter, "portrait" if compact else "idle", 86 if compact else 136, False)
        if image:
            self.screen.blit(image, (rect.x + (rect.width - image.get_width()) // 2, rect.y + (4 if compact else -15)))
        else:
            pygame.draw.circle(self.screen, fighter.color, (rect.centerx, rect.y + 65), 38)
        self.text(self.screen, fighter.name, self.tiny if compact else self.font, INK, (rect.centerx, rect.bottom - 17 if compact else rect.y + 142), True)
        if active:
            self.text(self.screen, player_label, self.small, color, (rect.centerx, rect.y - 14 if compact else rect.y + 168), True)

    def draw_select(self):
        self.image_background("select")
        label = "P1" if self.selecting_player == 0 else ("CPU" if self.mode == "cpu" else "P2")
        for side, index in enumerate(self.selection):
            fighter = ROSTER[index]
            image = self.art.image(fighter, "idle", 300, side == 1)
            center = 227 if side == 0 else 1053
            if image:
                self.screen.blit(image, (center - image.get_width() // 2, 91))
            self.text(self.screen, fighter.name, self.font, fighter.accent, (center, 386), True)
            self.text(self.screen, fighter.area, self.small, INK, (center, 414), True)
        for i in range(len(ROSTER)):
            rect = pygame.Rect(79 + i * 113, 455, 94, 112)
            self.card(i, rect, i == self.selection[self.selecting_player], label)
        current = ROSTER[self.selection[self.selecting_player]]
        self.text(self.screen, f"{label}: {current.name} — {current.area}", self.font, current.accent, (WIDTH // 2, 620), True)
        self.text(self.screen, "Direcional/analógico escolher  •  A/X confirmar  •  B/Círculo voltar", self.small, INK, (WIDTH // 2, 683), True)

    def start_match(self):
        self.p1 = Fighter(ROSTER[self.selection[0]], 1)
        self.p2 = Fighter(ROSTER[self.selection[1]], 2, self.mode == "cpu")
        self.scene = "battle"
        self.round_over, self.winner, self.notice = 0, None, "ROUND 1 — FIGHT!"
        self.notice_timer = 1.5
        self.match_time = 90.0
        self.fatality_winner = None
        self.finish_target = None
        self.finisher = None
        self.finish_timer = 0.0
        self.hitstop = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.fatality_playing = False
        self.fatality_frames_list = []
        self.fatality_stage = 0
        self.fatality_stage_time = 0.0
        self.timer_warning_started = False
        self.game_over_played = False
        self.sfx.stop_loop("timer_warning")
        self.sfx.play_loop("background_music", 0.05, 500)
        self.sfx.play("round_start")
        # Confirming a character with A/Cross must not make that fighter jump
        # on the first battle frame while the button is still held.
        for player in range(2 if self.mode == "p2" else 1):
            pad = self.controller_for_player(player)
            if pad is not None:
                for action, active in self.controller_action_states(pad).items():
                    self.controller_latches[(player, f"battle_{action}")] = active

    def play_game_over(self):
        """Ensure the supplied game-over sting is emitted only once per match."""
        if self.game_over_played:
            return
        self.game_over_played = True
        self.sfx.stop_loop("timer_warning", 120)
        self.sfx.play("game_over", 0.9)

    def draw_bar(self, fighter: Fighter, x: int, flip: bool):
        width = 440
        y = 34
        self.text(self.screen, fighter.spec.name, self.font, fighter.spec.accent, (x if not flip else x + width, y), flip)
        bar = pygame.Rect(x, y + 28, width, 23)
        pygame.draw.rect(self.screen, (45, 15, 24), bar, border_radius=6)
        fill = int(width * fighter.health / 100)
        fill_rect = pygame.Rect(bar.right - fill, bar.y, fill, bar.height) if flip else pygame.Rect(bar.x, bar.y, fill, bar.height)
        pygame.draw.rect(self.screen, fighter.spec.color, fill_rect, border_radius=6)
        pygame.draw.rect(self.screen, (230, 236, 255), bar, 2, border_radius=6)
        meter = pygame.Rect(x, y + 58, width, 7)
        pygame.draw.rect(self.screen, (33, 38, 55), meter, border_radius=3)
        mfill = int(width * fighter.meter / 100)
        pygame.draw.rect(self.screen, fighter.spec.accent, (meter.right - mfill if flip else meter.x, meter.y, mfill, meter.height), border_radius=3)

    def draw_fighter(self, fighter: Fighter):
        assert fighter is not None
        state = fighter.state
        image = self.art.image(fighter.spec, state, 350 if state != "crouch" else 280, fighter.facing == -1)
        if image:
            x = int(fighter.x - image.get_width() / 2)
            y = int(fighter.y - image.get_height())
            self.glow(self.screen, fighter.spec.color, (int(fighter.x), int(fighter.y - 120)), 75)
            self.screen.blit(image, (x, y))
        else:
            pygame.draw.ellipse(self.screen, fighter.spec.color, (fighter.x - 52, fighter.y - 220, 104, 220))
        if fighter.blocking:
            pygame.draw.arc(self.screen, fighter.spec.accent, (fighter.x - 84, fighter.y - 205, 168, 190), math.pi * 1.1, math.pi * 1.9, 5)

    def burst(self, position, color, count=13):
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(55, 210)
            self.particles.append({"x": position[0], "y": position[1], "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed - 35, "life": random.uniform(.28, .72), "color": color})

    def draw_particles(self, dt):
        kept = []
        for particle in self.particles:
            particle["life"] -= dt
            if particle["life"] <= 0:
                continue
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += 300 * dt
            alpha = int(255 * min(1, particle["life"] * 2))
            pygame.draw.circle(self.screen, (*particle["color"], alpha), (int(particle["x"]), int(particle["y"])), max(2, int(7 * particle["life"])))
            kept.append(particle)
        self.particles = kept

    def attack_label(self, fighter: Fighter):
        labels = {"light": "GOLPE RÁPIDO", "heavy": "GOLPE FORTE", "kick": "CHUTE", "special1": fighter.spec.specials[0], "special2": fighter.spec.specials[1], "special3": fighter.spec.specials[2], "fatality": "FATALITY", "throw": "ARREMESSO"}
        label = labels.get(fighter.attack, "")
        if fighter._is_air_attack and fighter.attack in ("light", "heavy", "kick"):
            label += " (AÉREO)"
        return label

    def draw_fatality_cutscene(self):
        """Renders the current fatality still with a slow push-in zoom, so
        the sequence reads as a mini cutscene. Stills that already come with
        their own background (is_scene) fill the whole screen instead, since
        they're full illustrated scenes rather than a floating character."""
        frames = self.fatality_frames_list
        stage = clamp(self.fatality_stage, 0, len(frames) - 1)
        image, is_scene = frames[stage]
        if is_scene:
            self.screen.fill((0, 0, 0))
            rect = image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(image, rect)
            return
        is_last = stage == len(frames) - 1
        progress = 1 - clamp(self.fatality_stage_time / (0.85 if is_last else 0.45), 0, 1)
        zoom = 1.0 + 0.10 * progress
        w, h = int(image.get_width() * zoom), int(image.get_height() * zoom)
        zoomed = pygame.transform.smoothscale(image, (max(1, w), max(1, h)))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 0, 0, 130))
        self.screen.blit(veil, (0, 0))
        rect = zoomed.get_rect(midbottom=(WIDTH // 2, GROUND_Y + 30))
        self.screen.blit(zoomed, rect)

    def draw_battle(self, dt):
        # Everything is drawn onto an offscreen buffer first so a screen
        # shake can nudge the whole scene by a few pixels without leaving
        # gaps at the edges.
        real_screen = self.screen
        shaking = self.shake > 0.5
        self.screen = pygame.Surface((WIDTH, HEIGHT)) if shaking else real_screen

        self.image_background("arena", 75)
        assert self.p1 and self.p2
        if self.fatality_playing and self.fatality_frames_list:
            self.draw_fatality_cutscene()
        else:
            self.draw_bar(self.p1, 42, False)
            self.draw_bar(self.p2, WIDTH - 482, True)
            self.text(self.screen, str(max(0, int(self.match_time + .99))), self.big, (247, 190, 54), (WIDTH // 2, 50), True)
            self.text(self.screen, "P1", self.small, MUTED, (42, 82))
            self.text(self.screen, "CPU" if self.mode == "cpu" else "P2", self.small, MUTED, (WIDTH - 42, 82), True)
            if self.fatality_winner:
                self.draw_fighter(self.fatality_winner)
            else:
                self.draw_fighter(self.p1)
                self.draw_fighter(self.p2)
                for fighter in (self.p1, self.p2):
                    if fighter.attack:
                        self.text(self.screen, self.attack_label(fighter), self.small, fighter.spec.accent, (fighter.x, fighter.y - 320), True)
                    if fighter.combo > 1:
                        self.text(self.screen, f"{fighter.combo} HITS", self.font, fighter.spec.accent, (fighter.x, fighter.y - 350), True)
            self.draw_particles(dt)
            if self.notice_timer > 0:
                self.text(self.screen, self.notice, self.big, (255, 215, 104), (WIDTH // 2, 174), True)
            if self.finish_target and not self.fatality_winner:
                pulse = 190 + int(65 * abs(math.sin(pygame.time.get_ticks() * .008)))
                self.text(self.screen, "FINISH!", self.huge, (pulse, 24, 24), (WIDTH // 2, 205), True)
                key = "R" if self.finisher is self.p1 else "P"
                self.text(self.screen, f"APROXIME-SE E PRESSIONE {key}", self.font, INK, (WIDTH // 2, 276), True)
                self.text(self.screen, f"{self.finish_timer:.1f}", self.font, (247, 190, 54), (WIDTH // 2, 309), True)
            if self.round_over > 0:
                if self.fatality_winner:
                    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    veil.fill((35, 0, 0, 75))
                    self.screen.blit(veil, (0, 0))
                    self.text(self.screen, "FATALITY", self.huge, (205, 28, 28), (WIDTH // 2, 210), True)
                    self.text(self.screen, f"{self.fatality_winner.spec.name} FINALIZA!", self.big, (247, 190, 54), (WIDTH // 2, 300), True)
                self.text(self.screen, "ENTER: revanche  •  ESC: seleção", self.font, INK, (WIDTH // 2, 390), True)
            controls = "P1: A/D mover • W pular • S defender • F/G/H ataques • Q/E/R especiais • T arremesso"
            if self.mode == "cpu":
                controls += "   |   Ao aparecer FINISH: aproxime-se e use R"
            else:
                controls += "   |   P2: ←/→ • ↑ pular • ↓ defender • J/K/L ataques • U/O/P especiais • I arremesso"
            self.text(self.screen, controls, self.small, MUTED, (WIDTH // 2, 691), True)

        if shaking:
            buffer = self.screen
            self.screen = real_screen
            mag = int(self.shake)
            offset = (random.randint(-mag, mag), random.randint(-mag, mag))
            self.screen.fill((0, 0, 0))
            self.screen.blit(buffer, offset)

        if self.flash > 0.01:
            glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            glow.fill((255, 255, 255, int(clamp(self.flash, 0, 1) * 90)))
            self.screen.blit(glow, (0, 0))

    def resolve_attacks(self):
        assert self.p1 and self.p2
        for attacker, defender in ((self.p1, self.p2), (self.p2, self.p1)):
            if attacker.can_hit(defender):
                attacker._connected = True
                actual, blocked = defender.hit(attacker.last_damage, attacker)
                self.burst((defender.x, defender.y - 130), defender.spec.accent if blocked else attacker.spec.accent, 9 if blocked else 18)
                # Juice: brief freeze-frame + screen shake on impact, scaled
                # to how heavy the hit was, so hits actually feel like they
                # land instead of just ticking down a bar.
                if blocked:
                    self.hitstop, self.shake = 0.03, max(self.shake, 4)
                    self.sfx.play("block")
                else:
                    weight = {"light": 1, "kick": 1.3, "heavy": 1.7, "special1": 1.8, "special2": 1.6, "special3": 2.2}.get(attacker.attack, 1)
                    self.hitstop = max(self.hitstop, 0.045 * weight)
                    self.shake = max(self.shake, 5 * weight)
                    self.flash = max(self.flash, 0.12 * weight)
                    if attacker.attack != "fatality":
                        # Exactly one impact per connected attack. Each fighter
                        # has a dedicated supplied sound; the old voice-like
                        # `combat.mp3` is intentionally never played here.
                        self.sfx.play(
                            random.choice(CHARACTER_HIT_SOUNDS[attacker.spec.key]),
                            min(0.92, 0.62 + 0.10 * weight),
                            maxtime=650,
                        )
                if attacker.attack == "fatality":
                    defender.health = 0
                    self.fatality_winner = attacker
                    attacker.state = "fatality"
                    self.finish_target = None
                    self.finisher = None
                    self.winner = attacker
                    self.notice = ""
                    self.notice_timer = 0
                    # Play the character's fatality stills as a short
                    # cutscene instead of freezing on a single image.
                    self.fatality_frames_list = self.art.fatality_frames(attacker.spec, 620, attacker.facing == -1)
                    self.fatality_stage = 0
                    self.fatality_stage_time = 0.5
                    self.fatality_playing = bool(self.fatality_frames_list)
                    self.round_over = 0 if self.fatality_playing else 1
                    self.hitstop = 0.22
                    self.shake = 26
                    self.flash = 0.6
                    self.sfx.stop_loop("timer_warning", 100)
                    fatality_sound = "fatality_roboap" if attacker.spec.key == "roboap" else "fatality"
                    self.sfx.play(fatality_sound)
                if not blocked and attacker.attack != "fatality":
                    self.notice = f"{attacker.spec.name}: {self.attack_label(attacker)}!"
                    self.notice_timer = 0.55
                if defender.health <= 0 and attacker.attack != "fatality":
                    # Classic finish window: the loser remains standing briefly,
                    # vulnerable to the dedicated fatality command.
                    defender.health = 1
                    defender.attack = None
                    defender.blocking = False
                    defender.hit_stun = 99
                    defender.state = "hit"
                    attacker.attack = None
                    attacker.cooldown = 0
                    attacker.state = "idle"
                    self.finish_target = defender
                    self.finisher = attacker
                    self.finish_timer = 6.0
                    self.sfx.stop_loop("timer_warning", 100)
                    self.notice = ""
                    self.notice_timer = 0

    def cpu(self, dt):
        assert self.p1 and self.p2
        cpu, target = self.p2, self.p1
        if cpu.hit_stun > 0 or cpu.attack:
            return
        distance = abs(cpu.x - target.x)

        # Reactive defense: react to the opponent actually attacking instead
        # of only deciding things on a fixed timer. This is what makes the
        # CPU feel like it's "looking" at the fight rather than rolling dice.
        if target.attack and distance < 210 and not cpu.blocking:
            if random.random() < 0.55:
                cpu.block(True)
                return

        # Punish a whiff: if the opponent just finished an attack and is
        # still in recovery (cooldown) right next to us, take the opening.
        if not target.attack and target.cooldown > 0.05 and distance < 210 and random.random() < 0.5:
            cpu.block(False)
            cpu.start_attack(random.choice(("light", "heavy", "kick")))
            return

        cpu.ai_timer -= dt
        if distance > 210:
            cpu.block(False)
            cpu.move(-1 if cpu.x > target.x else 1, dt)
            return
        if cpu.ai_timer <= 0:
            cpu.ai_timer = random.uniform(.3, .75)
            roll = random.random()
            if target.health <= 20 and cpu.meter >= 35 and roll > .82:
                cpu.block(False)
                cpu.start_attack("fatality")
            elif target.blocking and distance < 165 and roll > 0.45:
                # Opponent is turtling point-blank: break the guard with a throw.
                cpu.block(False)
                if cpu.start_throw(target):
                    self.sfx.play("throw")
            elif roll < .18:
                cpu.block(True)
            else:
                cpu.block(False)
                kind = random.choice(("light", "light", "heavy", "kick", "special1", "special2", "special3"))
                if cpu.start_attack(kind) and kind.startswith("special"):
                    self.sfx.play("special")

    def handle_battle_event(self, event):
        assert self.p1 and self.p2
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.sfx.stop_loop("timer_warning", 150)
                self.scene = "select"
                return
            if self.round_over and event.key == pygame.K_RETURN:
                score = int(self.p1.health * 10) if self.winner == self.p1 else 0
                ranking.mostrar_ranking_e_salvar(
                    self.screen, self.clock, "mortal", score, presenter=self.present
                )
                self.start_match()
                return
            if self.finish_target:
                fatal_key = pygame.K_r if self.finisher is self.p1 else pygame.K_p
                if event.key == fatal_key and abs(self.finisher.x - self.finish_target.x) < 220:
                    self.finisher.start_attack("fatality")
                elif event.key == fatal_key:
                    self.notice, self.notice_timer = "CHEGUE MAIS PERTO!", .7
                return
            p1_keys = {pygame.K_z: "light", pygame.K_x: "heavy", pygame.K_c: "kick", pygame.K_a: "special1", pygame.K_s: "special2", pygame.K_d: "special3"}
            p2_keys = {pygame.K_h: "light", pygame.K_j: "heavy", pygame.K_k: "kick", pygame.K_y: "special1", pygame.K_u: "special2", pygame.K_i: "special3"}
            if event.key in p1_keys:
                kind = p1_keys[event.key]
                if self.p1.start_attack(kind):
                    if kind.startswith("special"):
                        self.sfx.play("special")
                elif kind.startswith("special"):
                    self.notice, self.notice_timer = "ENERGIA INSUFICIENTE", .8
            if self.mode == "p2" and event.key in p2_keys:
                kind = p2_keys[event.key]
                if self.p2.start_attack(kind) and kind.startswith("special"):
                    self.sfx.play("special")
            if event.key == pygame.K_v and self.p1.start_throw(self.p2):
                self.sfx.play("throw")
            if self.mode == "p2" and event.key == pygame.K_o and self.p2.start_throw(self.p1):
                self.sfx.play("throw")

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_DOWN:
                self.p1.block(False)
            if self.mode == "p2" and event.key == pygame.K_s:
                self.p2.block(False)

    def movement(self, dt):
        assert self.p1 and self.p2
        keys = pygame.key.get_pressed()
        joy_state = config.get_joystick_state(self.joysticks) if hasattr(self, 'joysticks') else {'left': False, 'right': False, 'up': False, 'down': False}

        def player_input(player: int) -> tuple[int, bool]:
            if player == 0:
                direction = (1 if keys[pygame.K_RIGHT] or joy_state['right'] else 0) - (1 if keys[pygame.K_LEFT] or joy_state['left'] else 0)
                down = bool(keys[pygame.K_DOWN]) or joy_state['down']
            else:
                direction = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
                down = bool(keys[pygame.K_s])
            pad = self.controller_for_player(player)
            if pad is not None:
                pad_direction, pad_down = self.controller_direction(pad)
                if pad_direction:
                    direction = pad_direction
                down = down or pad_down
            return direction, down

        if not self.round_over:
            if self.finish_target:
                if self.finisher is self.p1:
                    self.p1.move(player_input(0)[0], dt)
                elif self.mode == "p2":
                    self.p2.move(player_input(1)[0], dt)
                return
            p1_direction, p1_down = player_input(0)
            self.p1.move(p1_direction, dt)
            self.p1.crouch(p1_down)
            self.p1.block(p1_down)
            if keys[pygame.K_UP] or joy_state['up']:
                if self.p1.jump():
                    self.sfx.play("jump")
            if self.mode == "p2":
                p2_direction, p2_down = player_input(1)
                self.p2.move(p2_direction, dt)
                self.p2.crouch(p2_down)
                self.p2.block(p2_down)
                if keys[pygame.K_w]:
                    if self.p2.jump():
                        self.sfx.play("jump")
            else:
                self.cpu(dt)

    def resolve_collision(self):
        """Fighters have solid bodies while grounded: they push each other
        apart and can't cross to the other side. While either one is
        jumping, though, the collision is skipped so a jump can clear the
        opponent entirely, like hopping over someone in Mortal Kombat."""
        assert self.p1 and self.p2
        if self.p1.airborne or self.p2.airborne:
            return
        min_gap = 148
        gap = self.p2.x - self.p1.x
        if abs(gap) < min_gap:
            direction = 1 if gap >= 0 else -1
            push = (min_gap - abs(gap)) / 2
            self.p1.x = clamp(self.p1.x - push * direction, 70, WIDTH - 70)
            self.p2.x = clamp(self.p2.x + push * direction, 70, WIDTH - 70)

    def update_battle(self, dt):
        assert self.p1 and self.p2
        self.shake = max(0.0, self.shake - dt * 70)
        self.flash = max(0.0, self.flash - dt * 2.4)
        if self.hitstop > 0:
            self.hitstop = max(0.0, self.hitstop - dt)
            dt = 0.0
        if self.fatality_playing:
            self.fatality_stage_time -= dt
            if self.fatality_stage_time <= 0:
                self.fatality_stage += 1
                if self.fatality_stage >= len(self.fatality_frames_list):
                    self.fatality_playing = False
                    self.fatality_stage = len(self.fatality_frames_list) - 1
                    self.round_over = 1
                    self.play_game_over()
                else:
                    is_last = self.fatality_stage == len(self.fatality_frames_list) - 1
                    self.fatality_stage_time = 0.85 if is_last else 0.45
                    self.shake = max(self.shake, 12)
            return
        self.notice_timer = max(0, self.notice_timer - dt)
        if not self.round_over:
            if self.finish_target:
                self.finish_timer = max(0.0, self.finish_timer - dt)
                if self.finisher is self.p2 and self.mode == "cpu":
                    distance = abs(self.p2.x - self.p1.x)
                    if distance >= 205:
                        self.p2.move(-1 if self.p2.x > self.p1.x else 1, dt)
                    elif not self.p2.attack:
                        self.p2.start_attack("fatality")
                if self.finish_timer <= 0:
                    self.winner = self.finisher
                    self.finish_target.health = 0
                    self.finish_target = None
                    self.finisher = None
                    self.round_over = 1
                    self.notice = f"{self.winner.spec.name} VENCEU"
                    self.notice_timer = 9
                    self.winner.state = "victory"
                    self.sfx.play("victory")
                    self.play_game_over()
            else:
                self.match_time = max(0.0, self.match_time - dt)
                if 0 < self.match_time <= 10 and not self.timer_warning_started:
                    self.timer_warning_started = True
                    self.sfx.play_loop("timer_warning", 0.55, 120)
            self.movement(dt)
            self.p1.facing = 1 if self.p2.x > self.p1.x else -1
            self.p2.facing = 1 if self.p1.x > self.p2.x else -1
            self.p1.update(dt)
            self.p2.update(dt)
            self.resolve_collision()
            if self.p1.just_landed:
                self.sfx.play("land", 0.5)
            if self.p2.just_landed:
                self.sfx.play("land", 0.5)
            self.resolve_attacks()
            if self.match_time <= 0 and not self.round_over:
                self.winner = self.p1 if self.p1.health >= self.p2.health else self.p2
                loser = self.p2 if self.winner is self.p1 else self.p1
                loser.health = 0
                self.round_over = 1
                self.notice = f"TEMPO! {self.winner.spec.name} VENCEU"
                self.notice_timer = 9
                self.winner.state = "victory"
                self.sfx.play("victory")
                self.play_game_over()
        else:
            self.p1.update(dt)
            self.p2.update(dt)

    def select_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.scene = "title"
            return
        selected = self.selection[self.selecting_player]
        if event.key in (pygame.K_LEFT, pygame.K_a):
            selected = (selected - 1) % len(ROSTER)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            selected = (selected + 1) % len(ROSTER)
        elif event.key in (pygame.K_UP, pygame.K_w):
            selected = (selected - 5) % len(ROSTER)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            selected = (selected + 5) % len(ROSTER)
        elif event.key == pygame.K_RETURN:
            self.confirm_selection()
            return
        if selected != self.selection[self.selecting_player]:
            self.sfx.play("move")
        self.selection[self.selecting_player] = selected

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000, .033)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type in (
                    getattr(pygame, "CONTROLLERDEVICEADDED", -1001),
                    getattr(pygame, "CONTROLLERDEVICEREMOVED", -1002),
                    getattr(pygame, "CONTROLLERDEVICEREMAPPED", -1003),
                ):
                    self.refresh_controllers()
                elif self.scene == "title" and event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        self.menu_index = 1 - self.menu_index
                        self.sfx.play("move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.sfx.play("select")
                        self.mode = "cpu" if self.menu_index == 0 else "p2"
                        self.selecting_player, self.scene = 0, "select"
                        self.prime_selection_latches()
                    elif event.key == pygame.K_1:
                        self.sfx.play("select")
                        self.mode, self.selecting_player, self.scene, self.menu_index = "cpu", 0, "select", 0
                        self.prime_selection_latches()
                    elif event.key == pygame.K_2:
                        self.sfx.play("select")
                        self.mode, self.selecting_player, self.scene, self.menu_index = "p2", 0, "select", 1
                        self.prime_selection_latches()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif self.scene == "select":
                    self.select_event(event)
                elif self.scene == "battle":
                    self.handle_battle_event(event)
            self.poll_controllers()
            if self.scene == "title":
                self.draw_title()
            elif self.scene == "select":
                self.draw_select()
            else:
                self.update_battle(dt)
                self.draw_battle(dt)
            self.present()
        pygame.quit()


if __name__ == "__main__":
    try:
        Game().run()
    except ModuleNotFoundError:
        print("Dependência ausente. Execute: python -m pip install -r requirements.txt")
        raise
