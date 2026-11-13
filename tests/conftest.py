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
# Sizes in tests are at density 1, whatever the scale of this desktop.
os.environ.setdefault("KIVY_METRICS_DENSITY", "1")

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


@pytest.fixture(autouse=True)
def no_real_gamepads(monkeypatch):
    """Games ask SDL which gamepads exist (this machine may have some, or a
    keyboard that calls itself one); tests use the unidentified default or
    their own FakePads."""
    import main
    monkeypatch.setattr(main, 'make_pad_identity',
                        lambda: main.PadIdentity(None))


@pytest.fixture(autouse=True)
def no_pad_watcher(monkeypatch):
    """Games do not poll the machine's real joysticks."""
    import main
    monkeypatch.setattr(main, 'watch_gamepads', lambda: None)


def _window_observers(window, name):
    """uids of the fbind bindings and the callbacks bound with bind."""
    uids, callbacks = set(), []
    for callback, _, _, is_ref, uid in window.get_property_observers(
            name, args=True):
        if uid:
            uids.add(uid)
        else:
            callbacks.append(callback() if is_ref else callback)
    return uids, callbacks


@pytest.fixture(autouse=True)
def forget_the_tests_widgets():
    """Games, screens and widgets of a test are not used again, but they
    stay bound to the one window of the session (sizes, kv rules, keys)
    and keep their clock events, so every later window resize lays them
    out again. After each test, unbind from the window what the test
    bound and cancel the clock events it scheduled."""
    from kivy.clock import Clock
    from kivy.core.window import Window
    names = list(Window.properties()) + list(Window.events())
    before = {name: _window_observers(Window, name) for name in names}
    events = set(Clock.get_events())
    yield
    for name in names:
        uids, callbacks = before[name]
        for callback, _, _, is_ref, uid in Window.get_property_observers(
                name, args=True):
            if uid:
                if uid not in uids:
                    Window.unbind_uid(name, uid)
                continue
            callback = callback() if is_ref else callback
            if callback is not None and callback not in callbacks:
                Window.unbind(**{name: callback})
    for event in Clock.get_events():
        if event not in events:
            event.cancel()
