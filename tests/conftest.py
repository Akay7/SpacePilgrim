import os
import sys
from pathlib import Path

# Must be set before any kivy import: headless window/GL, no CLI parsing,
# dummy SDL audio device (the real SDL2_mixer ogg decoder is still used).
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
os.environ.setdefault("KIVY_GL_BACKEND", "mock")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# A hidden window: creating a visible one blocks while a Wayland session is
# locked, and nothing needs to be seen.
os.environ.setdefault("KCFG_GRAPHICS_WINDOW_STATE", "hidden")

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)  # main.py loads assets using paths relative to the project
sys.path.insert(0, str(ROOT))


import pytest


@pytest.fixture(autouse=True)
def two_touch_seats(monkeypatch):
    """Tests run on a phone-sized screen with two touch seats, whatever the
    dpi of the machine; tests of four seats patch this back."""
    import main
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a, **k: False)
