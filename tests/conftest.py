import os
import sys
from pathlib import Path

# Must be set before any kivy import: headless window/GL, no CLI parsing,
# dummy SDL audio device (the real SDL2_mixer ogg decoder is still used).
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
os.environ.setdefault("KIVY_GL_BACKEND", "mock")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)  # main.py loads assets using paths relative to the project
sys.path.insert(0, str(ROOT))
