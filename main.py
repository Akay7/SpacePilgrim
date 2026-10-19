__version__ = "0.3.4"

import colorsys
import json
import math
import os
from collections import namedtuple
from functools import partial
from random import randint, choice

from kivy.utils import platform
from kivy.animation import Animation
from kivy.core.window import Window, Keyboard
from kivy.core.audio import SoundLoader
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty, StringProperty,
    ListProperty,
)
from kivy.graphics import (
    Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle,
    Rotate, Triangle,
)
from kivy.metrics import dp, cm
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.logger import Logger

from kivy.core.image import Image
from kivy.graphics.texture import Texture


# Window key codes (SDL2) -> actions. Android TV remote D-pad and a gamepad
# D-pad delivered as keys arrive as the arrow keys; 1073741943 is
# SDL_SCANCODE_SELECT which Android sends for the D-pad centre button.
# These keys are fixed: they drive the menus and leaving the game, so they
# can not be rebound and a bad binding can never lock the player out.
RESERVED_KEY_ACTIONS = {
    273: 'up', 274: 'down', 276: 'left', 275: 'right',   # arrow keys
    13: 'fire', 271: 'fire', 1073741943: 'fire',         # Enter, KP Enter, Select
    27: 'back',                                          # Escape / Android Back
}

# Rebindable gameplay keys are stored as SDL scancodes: the physical key,
# independent of the keyboard layout (W stays W on a Russian layout).
# Two keyboard sets (at most two players share one keyboard): set 1 on
# WASD + Space, set 2 on IJKL. A set drives whoever joined with it.
DEFAULT_KEY_BINDINGS = {
    'up': [26],       # W
    'left': [4],      # A
    'right': [7],     # D
    'fire': [44],     # Space
}
DEFAULT_KEY_BINDINGS_P2 = {
    'up': [12],       # I
    'left': [13],     # J
    'right': [15],    # L
    'fire': [14],     # K
}
DEFAULT_PLAYER_KEYS = [DEFAULT_KEY_BINDINGS, DEFAULT_KEY_BINDINGS_P2]
KEY_SETS = len(DEFAULT_PLAYER_KEYS)
MAX_PLAYERS = 4   # join slots of a multiplayer game
TOUCH_SIDES = ('left', 'right')   # at most two touch players, one per side
START_OFFSETS = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # per slot, in ships
# Used when a migrated set 1 already took a default of set 2.
FALLBACK_SCANCODES = [92, 93, 94, 96, 89, 90, 91, 95, 97]  # keypad 4 5 6 8 ...
RESERVED_SCANCODES = {79, 80, 81, 82, 40, 88, 41}  # arrows, Enter, KP Enter, Esc
ACTION_LABELS = {
    'up': 'Thrust',
    'left': 'Turn left',
    'right': 'Turn right',
    'fire': 'Fire',
}

# SDL scancode -> latin name shown in the settings screen.
SCANCODE_NAMES = {
    **{4 + i: chr(ord('A') + i) for i in range(26)},       # A-Z
    **{30 + i: str(i + 1) for i in range(9)}, 39: '0',      # 1-9, 0
    **{58 + i: 'F{}'.format(i + 1) for i in range(12)},     # F1-F12
    44: 'Space', 45: '-', 46: '=', 47: '[', 48: ']', 49: '\\', 51: ';',
    52: "'", 53: '`', 54: ',', 55: '.', 56: '/',
    42: 'Backspace', 43: 'Tab', 57: 'CapsLock',
    73: 'Insert', 74: 'Home', 75: 'PageUp', 76: 'Delete', 77: 'End',
    78: 'PageDown', 79: 'Right', 80: 'Left', 81: 'Down', 82: 'Up',
    **{89 + i: 'Num{}'.format(i + 1) for i in range(9)}, 98: 'Num0',
    224: 'LCtrl', 225: 'LShift', 226: 'LAlt',
    228: 'RCtrl', 229: 'RShift', 230: 'RAlt',
}


def scancode_name(scancode):
    return SCANCODE_NAMES.get(scancode, 'Key {}'.format(scancode))


def scancode_for(key, scancode=None):
    """The physical key. Kivy passes the SDL scancode with key events; when
    it is missing, derive it for plain ASCII keys."""
    if scancode:
        return scancode
    if 97 <= key <= 122:
        return key - 97 + 4
    if 49 <= key <= 57:
        return key - 49 + 30
    return {48: 39, 32: 44}.get(key)


class KeyBindings:
    """Configurable keyboard bindings for two keyboard sets (set -> action ->
    scancodes), optionally persisted as JSON."""

    VERSION = 3   # 2: one set; 1: layout dependent key codes

    def __init__(self, path=None):
        self.path = path
        self.keys = self._defaults()
        self.load()

    @staticmethod
    def _defaults():
        return [{a: list(k) for a, k in keys.items()}
                for keys in DEFAULT_PLAYER_KEYS]

    def label(self, action, key_set=0):
        return ', '.join(
            scancode_name(sc) for sc in self.keys[key_set][action])

    def lookup(self, key, scancode=None):
        """(set, action) of a key press; (None, action) for keys that
        belong to no set (Escape), (None, None) for unbound keys. Arrow
        keys and Enter are reserved for the menus and count as set 1."""
        sc = scancode_for(key, scancode)
        for key_set, actions in enumerate(self.keys):
            for action, scancodes in actions.items():
                if sc in scancodes:
                    return key_set, action
        action = RESERVED_KEY_ACTIONS.get(key)
        if action in (None, 'back'):
            return None, action
        return 0, action

    def action_for(self, key, scancode=None):
        return self.lookup(key, scancode)[1]

    def rebind(self, action, key, scancode=None, key_set=0):
        """Bind the physical key to `action` of `key_set`. Returns None on
        success or a message saying why the key was refused (the old binding
        is kept)."""
        sc = scancode_for(key, scancode)
        if sc is None:
            return 'That key can not be used'
        if key in RESERVED_KEY_ACTIONS or sc in RESERVED_SCANCODES:
            return 'That key is reserved'
        for other_set, actions in enumerate(self.keys):
            for other, scancodes in actions.items():
                if (other_set, other) != (key_set, action) and sc in scancodes:
                    who = ('' if other_set == key_set
                           else 'Set {} '.format(other_set + 1))
                    return 'Already used for {}{}'.format(
                        who, ACTION_LABELS[other])
        self.keys[key_set][action] = [sc]
        self.save()

    def reset(self):
        self.keys = self._defaults()
        self.save()

    @staticmethod
    def _valid_set(keys, seen):
        if not isinstance(keys, dict) or set(keys) != set(DEFAULT_KEY_BINDINGS):
            return False
        for scancodes in keys.values():
            if not isinstance(scancodes, list) or not scancodes:
                return False
            for sc in scancodes:
                if (not isinstance(sc, int) or isinstance(sc, bool)
                        or sc in RESERVED_SCANCODES or sc in seen):
                    return False
                seen.add(sc)
        return True

    def _migrated(self, keys):
        """Version 2 file: its set is set 1, set 2 gets the defaults
        (or free keys where set 1 already uses a default)."""
        seen = set()
        if not self._valid_set(keys, seen):
            return None
        spare = [sc for sc in FALLBACK_SCANCODES if sc not in seen]
        second = {}
        for action, scancodes in DEFAULT_KEY_BINDINGS_P2.items():
            if scancodes[0] in seen:
                if not spare:
                    return None
                second[action] = [spare.pop(0)]
            else:
                second[action] = list(scancodes)
        return [{a: list(k) for a, k in keys.items()}, second]

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        if data.get('version') == 2:
            keys = self._migrated(data.get('keys'))
            if keys:
                self.keys = keys
            return
        if data.get('version') != self.VERSION:
            return
        players = data.get('players')
        if not isinstance(players, list) or len(players) != KEY_SETS:
            return
        seen = set()
        if all(self._valid_set(p, seen) for p in players):
            self.keys = [
                {a: list(p[a]) for a in DEFAULT_KEY_BINDINGS} for p in players]

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'version': self.VERSION, 'players': self.keys}, f)
        except OSError:
            pass  # keep the in-memory bindings for this session


class TouchSettings:
    """Whether the on-screen touch controls are shown: 'auto' (shown on
    touch, hidden while a keyboard or gamepad is used), 'on' or 'off'.
    Optionally persisted as JSON."""

    MODES = ('auto', 'on', 'off')
    MIN_SCALE, MAX_SCALE, SCALE_STEP = 0.5, 4.0, 0.05  # size of the controls

    def __init__(self, path=None):
        self.path = path
        self.mode = 'auto'
        self.scale = 1.0
        self.load()

    def cycle(self):
        self.mode = self.MODES[(self.MODES.index(self.mode) + 1) % 3]
        self.save()

    def set_scale(self, value, save=True):
        value = min(max(float(value), self.MIN_SCALE), self.MAX_SCALE)
        self.scale = round(value / self.SCALE_STEP) * self.SCALE_STEP
        if save:
            self.save()

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        if data.get('mode') in self.MODES:
            self.mode = data['mode']
        scale = data.get('scale')
        if (isinstance(scale, (int, float)) and not isinstance(scale, bool)
                and self.MIN_SCALE <= scale <= self.MAX_SCALE):
            self.set_scale(scale, save=False)

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'mode': self.mode, 'scale': self.scale}, f)
        except OSError:
            pass  # keep the in-memory setting for this session


# Default gamepad layout (SDL joystick button ids, Xbox-style pad):
# A / X fire, B / Y thrust, Back / Start return to the menu.
# Left stick and D-pad steer. The ids differ by platform: on desktop the
# pad's buttons come in the order of the driver (6 Back, 7 Start); on
# Android SDL numbers them like a game controller: A B X Y, 4 Back (View),
# 5 Guide, 6 Start, 7 / 8 stick clicks (must not leave the game), 9 / 10
# shoulders, 11-14 D-pad.
JOY_BUTTON_ACTIONS_DESKTOP = {
    0: 'fire', 2: 'fire',
    1: 'up', 3: 'up',
    6: 'back', 7: 'back',
}
JOY_BUTTON_ACTIONS_ANDROID = {
    0: 'fire', 2: 'fire',
    1: 'up', 3: 'up',
    4: 'back', 6: 'back',
    11: 'up', 12: 'down', 13: 'left', 14: 'right',
}
JOY_BUTTON_ACTIONS = (JOY_BUTTON_ACTIONS_ANDROID if platform == 'android'
                      else JOY_BUTTON_ACTIONS_DESKTOP)
JOY_AXIS_DEADZONE = 0.5


# Cabin colours: name -> hue in degrees. The sprite's canopy is blue (~210).
CABIN_COLORS = {
    'blue': 210, 'green': 120, 'red': 0, 'yellow': 55,
    'purple': 285, 'orange': 28,
}
CABIN_NAMES = list(CABIN_COLORS)
DEFAULT_CABINS = ['blue', 'green', 'red', 'yellow']
CABIN_SOURCE_HUE = 210
SHIP_IMAGES = ('images/ship_stop.png', 'images/ship_fly.png')


def cabin_rgb(name):
    """Colour used for HUD text and previews of a cabin colour."""
    return colorsys.hsv_to_rgb(CABIN_COLORS[name] / 360, 0.7, 1)


def recolor_cabin(rgba, hue):
    """RGBA bytes with the blue canopy shifted to `hue` (degrees); hull,
    wings and engine flame keep their colours."""
    shift = (hue - CABIN_SOURCE_HUE) / 360
    out = bytearray(rgba)
    if not shift:
        return bytes(out)
    for i in range(0, len(out), 4):
        if out[i + 3] < 16:
            continue
        h, sat, val = colorsys.rgb_to_hsv(
            out[i] / 255, out[i + 1] / 255, out[i + 2] / 255)
        if 0.5 < h < 0.7 and sat > 0.35 and val > 0.3:
            r, g, b = colorsys.hsv_to_rgb((h + shift) % 1, sat, val)
            out[i:i + 3] = bytes((round(r * 255), round(g * 255), round(b * 255)))
    return bytes(out)


_cabin_textures = {}


def cabin_textures(name):
    """(stopped, flying) textures of the ship with the given cabin colour,
    made once and cached."""
    if name not in _cabin_textures:
        pair = []
        for path in SHIP_IMAGES:
            image = Image(path, keep_data=True)
            data = image.image._data[0]
            if data.fmt != 'rgba' or name == 'blue':
                pair.append(image.texture)
                continue
            pixels = recolor_cabin(data.data, CABIN_COLORS[name])
            texture = Texture.create(size=(data.width, data.height))
            texture.blit_buffer(pixels, colorfmt='rgba', bufferfmt='ubyte')
            texture.flip_vertical()
            pair.append(texture)
        _cabin_textures[name] = tuple(pair)
    return _cabin_textures[name]


class ShipColors:
    """Cabin colour remembered for each player slot, optionally persisted as
    JSON. Colours only have to differ between the players of one game."""

    def __init__(self, path=None):
        self.path = path
        self.colors = list(DEFAULT_CABINS)
        self.load()

    def cycle(self, player, step, players=MAX_PLAYERS, active=None):
        """Next (step 1) / previous colour for `player`, skipping colours
        another player of this game (the `active` slots, by default the
        first `players`) already has."""
        taken = self._taken(player, range(players) if active is None else active)
        index = CABIN_NAMES.index(self.colors[player])
        for _ in CABIN_NAMES:
            index = (index + step) % len(CABIN_NAMES)
            if CABIN_NAMES[index] not in taken:
                self.colors[player] = CABIN_NAMES[index]
                return

    def claim(self, player, active):
        """`player` joins the game of the `active` slots: keep the saved
        colour when it is free, else take the first free one."""
        taken = self._taken(player, active)
        if self.colors[player] in taken:
            self.colors[player] = next(
                c for c in CABIN_NAMES if c not in taken)

    def _taken(self, player, active):
        return {self.colors[i] for i in active if i != player}

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        colors = data.get('colors') if isinstance(data, dict) else None
        # two entries: saved before games had four players
        if (isinstance(colors, list) and len(colors) in (2, MAX_PLAYERS)
                and all(c in CABIN_COLORS for c in colors)):
            self.colors = list(colors) + DEFAULT_CABINS[len(colors):]

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'colors': self.colors}, f)
        except OSError:
            pass  # keep the in-memory choice for this session


PlayerResult = namedtuple('PlayerResult', 'slot color points survived')
LEADERBOARD_SIZE = 10
NAME_LENGTH = 12
DEFAULT_NAME = 'Player'


def clean_name(text):
    """A nickname as stored: trimmed, at most NAME_LENGTH characters."""
    return str(text).strip()[:NAME_LENGTH].strip() or DEFAULT_NAME


def top_result(results):
    """The best player of a game: most points, then longest survival."""
    return max(results, key=lambda r: (r.points, r.survived))


class Leaderboard:
    """The best games played on this device, as JSON: one entry per saved
    game with the player's nickname, points (the rating) and the seconds
    survived (information, only breaks ties); also the last nickname used. Best first, at most LEADERBOARD_SIZE entries."""

    VERSION = 1

    def __init__(self, path=None):
        self.path = path
        self.entries = []
        self.last_name = ''
        self.load()

    @staticmethod
    def _rank(entry):
        return (-entry['points'], -entry['seconds'])

    def add(self, points, seconds, name=DEFAULT_NAME):
        """Keep the game in the top entries and write the file. False when
        the file could not be written (the entry stays for this session)."""
        name = clean_name(name)
        self.last_name = name
        self.entries.append({'name': name, 'points': int(points),
                             'seconds': int(seconds)})
        self.entries.sort(key=self._rank)
        del self.entries[LEADERBOARD_SIZE:]
        return self.save()

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        entries = data.get('entries') if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return
        valid = [{'name': clean_name(e.get('name', DEFAULT_NAME)),
                  'points': e['points'], 'seconds': e['seconds']}
                 for e in entries
                 if isinstance(e, dict)
                 and all(type(e.get(k)) is int and e[k] >= 0
                         for k in ('points', 'seconds'))]
        valid.sort(key=self._rank)
        self.entries = valid[:LEADERBOARD_SIZE]
        if isinstance(data.get('last_name'), str):
            self.last_name = clean_name(data['last_name'])

    def save(self):
        if not self.path:
            return True
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'version': self.VERSION, 'last_name': self.last_name,
                           'entries': self.entries}, f)
        except OSError:
            return False
        return True


def is_android_tv():
    if platform != 'android':
        return False
    try:
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        package_manager = activity.getPackageManager()
        return bool(
            package_manager.hasSystemFeature('android.software.leanback') or
            package_manager.hasSystemFeature('android.hardware.type.television')
        )
    except Exception:
        return False


def hide_system_bars():
    """Android: hide the status and navigation bars (swipe from the edge
    shows them for a moment), so they do not cover the touch controls."""
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread

        @run_on_ui_thread
        def hide():
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            window = activity.getWindow()
            decor = window.getDecorView()
            # IMMERSIVE_STICKY | HIDE_NAVIGATION | FULLSCREEN | LAYOUT_*
            decor.setSystemUiVisibility(0x1000 | 0x2 | 0x4 | 0x100 | 0x200 | 0x400)
            controller = window.getInsetsController()
            if controller is not None:       # Android 11+
                bars = autoclass('android.view.WindowInsets$Type').systemBars()
                controller.hide(bars)
                controller.setSystemBarsBehavior(2)  # transient by swipe
        hide()
    except Exception:
        pass


class PadWatcher:
    """Opens gamepads that connect after the app has started.

    Kivy opens the joysticks SDL knows at start-up and never the ones that
    appear later (a Bluetooth pad switched on in the menu, or a reconnect),
    and SDL sends no stick or D-pad events for a joystick that is not open:
    only the buttons arrive, as plain keys. This looks for new ones four
    times a second and opens them, so that sticks, D-pad and buttons reach the game
    as joystick events. `sdl` is the loaded SDL2 library."""

    def __init__(self, sdl):
        import ctypes
        self.sdl = sdl
        sdl.SDL_NumJoysticks.restype = ctypes.c_int
        sdl.SDL_JoystickOpen.argtypes = [ctypes.c_int]
        sdl.SDL_JoystickOpen.restype = ctypes.c_void_p
        sdl.SDL_JoystickClose.argtypes = [ctypes.c_void_p]
        sdl.SDL_JoystickGetDeviceInstanceID.argtypes = [ctypes.c_int]
        sdl.SDL_JoystickGetDeviceInstanceID.restype = ctypes.c_int32
        self.open = {}      # SDL instance id -> joystick handle

    def poll(self, dt=0):
        sdl = self.sdl
        present = {}
        for index in range(sdl.SDL_NumJoysticks()):
            present[sdl.SDL_JoystickGetDeviceInstanceID(index)] = index
        for instance, index in present.items():
            if instance not in self.open:
                handle = sdl.SDL_JoystickOpen(index)
                if handle:
                    self.open[instance] = handle
                    Logger.info('Pads: opened joystick %s', instance)
        for instance in [i for i in self.open if i not in present]:
            sdl.SDL_JoystickClose(self.open.pop(instance))


def watch_gamepads():
    """Android: keep opening newly connected gamepads (see PadWatcher).
    Returns the Clock event, or None where it is not needed or possible."""
    if platform != 'android':
        return None
    try:
        import ctypes
        watcher = PadWatcher(ctypes.CDLL('libSDL2.so'))
        watcher.poll()
        return Clock.schedule_interval(watcher.poll, 0.25)
    except Exception:
        return None


def has_touchscreen():
    """Whether the device has a touchscreen. Android TV usually has none;
    on desktops a mouse click arrives as a touch, so count it as one."""
    if platform != 'android':
        return True
    try:
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        return bool(activity.getPackageManager().hasSystemFeature(
            'android.hardware.touchscreen'))
    except Exception:
        return True


class Explosion(Widget):
    frame = NumericProperty(0)
    texture = ObjectProperty()
    sound = SoundLoader.load('sounds/explosion.ogg')

    def __init__(self, **kwargs):
        super(Explosion, self).__init__(**kwargs)
        self.sound.play()
        texture = Image('images/explosion.png').texture
        self.textures = [texture.get_region(i*128, 0, 128, 128) for i in range(23)]
        self.texture = self.textures[self.frame]

        self.bind(frame=self.change_texture)
        self.animation = Animation(
            frame=22, t='linear', duration=0.6
        )
        self.animation.start(self)
        self.animation.bind(on_complete=self.remove_from_parent)

    def pause(self):
        self.animation.cancel(self)

    def resume(self):
        left = (22 - self.frame) / 22 * 0.6
        self.animation = Animation(frame=22, t='linear', duration=left)
        self.animation.bind(on_complete=self.remove_from_parent)
        self.animation.start(self)

    def change_texture(self, called_by, value):
        self.texture = self.textures[int(value)]

    def remove_from_parent(self, called_by, value):
        self.parent.remove_widget(self)


class Asteroid(Widget):
    speed = NumericProperty(4)
    angle = NumericProperty(0)

    def update(self, dt):
        for i in [0, 1]:
            if self.pos[i] < 0:
                self.pos[i] = Window.size[i]
            elif self.pos[i] > Window.size[i]:
                self.pos[i] = 0

        self.pos = Vector(self.speed, 0).rotate(self.angle) + self.pos


class Shot(Widget):
    lifetime = NumericProperty(1)
    speed = NumericProperty(4)
    angle = NumericProperty(0)
    sound = SoundLoader.load('sounds/gun.ogg')
    spaceship = ObjectProperty()

    def __init__(self, **kwargs):
        super(Shot, self).__init__(**kwargs)
        self.sound.play()

    def update(self, dt):
        for i in [0, 1]:
            if self.pos[i] < 0:
                self.pos[i] = Window.size[i]
            elif self.pos[i] > Window.size[i]:
                self.pos[i] = 0

        self.pos = Vector(self.speed, 0).rotate(self.angle) + self.pos


class Spaceship(Widget):
    lives = NumericProperty(3)
    points = NumericProperty(0)
    speed = NumericProperty(0)
    thrust = BooleanProperty(False)
    angle = NumericProperty(0)
    angle_rotation = NumericProperty(0)
    rotate = StringProperty()
    cabin = StringProperty('blue')
    texture_stop = ObjectProperty(None, allownone=True)
    texture_fly = ObjectProperty(None, allownone=True)
    sound = SoundLoader.load('sounds/engine.ogg')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(cabin=self._set_cabin)
        self._set_cabin()

    def _set_cabin(self, *args):
        name = self.cabin if self.cabin in CABIN_COLORS else 'blue'
        self.texture_stop, self.texture_fly = cabin_textures(name)

    def update(self, dt):
        for i in [0, 1]:
            if self.pos[i] < 0:
                self.pos[i] = Window.size[i]
            elif self.pos[i] > Window.size[i]:
                self.pos[i] = 0

        self.angle += self.angle_rotation
        if self.thrust:
            self.speed = 3
        else:
            self.speed *= 0.98

        self.pos = Vector(self.speed, 0).rotate(self.angle) + self.pos

    def thrust_on(self):
        if not self.thrust:
            self.sound.play()
        self.thrust = True

    def thrust_off(self):
        self.thrust = False
        self.sound.stop()

    def turn_left(self):
        self.angle_rotation = 3

    def turn_right(self):
        self.angle_rotation = -3

    def stop_rotation(self):
        self.angle_rotation = 0

    def shot(self):
        shot = Shot(spaceship=self)
        shot.pos = (
            Vector(*self.size)/2 - Vector(*shot.size)/2 +
            self.pos + Vector(self.size[0] / 2, 0).rotate(self.angle)
        )
        shot.angle = self.angle
        shot.speed += self.speed

        self.parent.shots.append(shot)
        self.parent.expire_shot(shot)
        self.parent.add_widget(shot)


class PauseButton(Button):
    """Touch players have no Back key: this pauses the game. It is square,
    so that it can be turned with its player's status block."""


class SpaceshipStatus(Widget):
    spaceship = ObjectProperty()
    show_menu = BooleanProperty(False)  # touch player: show the Pause button
    # '' one player (top right); multiplayer: 'left' / 'right' for a touch
    # player's side, 'top' for keyboard and gamepad players
    side = StringProperty('')
    column = NumericProperty(0)         # 'top': the player's slot
    # 'left' / 'right': distance from that screen edge to the inner side of
    # the player's touch controls; the block sits just inside it
    inset = NumericProperty(0)

    def follow(self, touch_buttons):
        """Keep the block next to the touch controls of its player, whatever
        their size: the joystick is the widest control of the column."""
        stick = touch_buttons.stick

        def place(*args):
            gap = dp(8)
            if self.side == 'left':
                self.inset = stick.right - touch_buttons.x + gap
            else:
                self.inset = touch_buttons.right - stick.x + gap
        stick.bind(pos=place, size=place)
        touch_buttons.bind(pos=place, size=place)
        place()
    color = ListProperty([1, 1, 1, 1])  # tint of the text: the cabin colour


class ButtonColumn(BoxLayout):
    """Vertical list of buttons that can be navigated with the keyboard."""
    selected = NumericProperty(0)
    waiting = ''   # action waiting for a key (settings pages that rebind)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.highlight()

    def refresh(self, message=''):
        pass

    def adjust(self, step):
        """Left / right on a page with a slider."""

    @property
    def buttons(self):
        # children are stored bottom to top, the menu reads top to bottom
        return [b for b in reversed(self.children)
                if isinstance(b, Button) and not b.disabled]

    def highlight(self):
        buttons = self.buttons
        for button in buttons:
            button.background_color = (1, 1, 1, 1)
        if buttons:
            buttons[self.selected % len(buttons)].background_color = (
                0.3, 0.7, 1, 1)

    def move(self, step):
        self.selected = (self.selected + step) % len(self.buttons)
        self.highlight()

    def activate(self):
        self.buttons[self.selected % len(self.buttons)].dispatch('on_press')


class Menu(ButtonColumn):
    pass


class ResultsScreen(ButtonColumn):
    """Shown when the last ship is lost: what each player got, and what to
    do next. The points are the rating; the time is for information."""
    # ignore presses for a moment: players are still pressing FIRE
    GUARD = 1.0

    def __init__(self, results, **kwargs):
        super().__init__(**kwargs)
        self.results = results
        self.saved = False
        self.armed_at = Clock.get_time() + self.GUARD
        longest = max(r.survived for r in results)
        for result in results:
            self.ids.rows.add_widget(self._row(
                result, len(results) > 1,
                len(results) > 1 and result.survived == longest))

    @staticmethod
    def _row(result, multi, longest):
        name = 'Player {}  '.format(result.slot + 1) if multi else ''
        return Label(
            text='{}Time {:>3} s   Points {:>3}{}'.format(
                name, int(result.survived), result.points,
                '   longest' if longest else ''),
            color=(*cabin_rgb(result.color), 1),
            font_size='17dp', font_name='data/fonts/RobotoMono-Regular.ttf')

    def activate(self):
        if Clock.get_time() >= self.armed_at:
            super().activate()

    def save_score(self):
        """Ask for a nickname; the score is stored by `store_score`."""
        if self.saved or Clock.get_time() < self.armed_at:
            return
        self.parent.show_name_entry()

    def store_score(self, name):
        best = top_result(self.results)
        ok = self.parent.leaderboard.add(best.points, best.survived, name)
        self.saved = True
        self.ids.btn_save.text = 'Saved'
        self.ids.btn_save.disabled = True
        self.ids.message.text = ('' if ok else
                                 'Could not write the file; kept until exit')
        self.selected = 0
        self.highlight()

    def play_again(self):
        if Clock.get_time() >= self.armed_at:
            self.parent.play_again()

    def go_menu(self):
        self.parent.show_menu()


class PauseScreen(ButtonColumn):
    """Shown over the frozen world: carry on, or leave for the main menu."""

    def resume(self):
        self.parent.resume()

    def go_menu(self):
        self.parent.confirm_leave()


class ConfirmScreen(ButtonColumn):
    """Asks before the running game is thrown away. Starts on "No" so a
    stray fire press keeps the game."""

    def __init__(self, kind, **kwargs):
        # kind: 'leave' (game to main menu) or 'exit' (quit the app)
        self.kind = kind
        kwargs.setdefault('selected', 1)
        super().__init__(**kwargs)

    def yes(self):
        if self.kind == 'exit':
            App.get_running_app().stop()
        else:
            self.parent.game_stop()

    def no(self):
        self.parent.leave_cancel()


class NameScreen(ButtonColumn):
    """Nickname for a score to save. Pads and remotes cannot type: they
    accept the prefilled nickname with Save."""

    def __init__(self, name, top, **kwargs):
        super().__init__(**kwargs)
        self.ids.title.text = ('Your nickname' if top is None else
                               'Nickname of player {}'.format(top + 1))
        field = self.ids.field
        field.text = name
        field.focus = True

    def accept(self):
        self.parent.name_done(self.ids.field.text)

    def cancel(self):
        self.parent.name_done(None)


class LeaderboardScreen(ButtonColumn):
    def __init__(self, entries, **kwargs):
        super().__init__(**kwargs)
        if not entries:
            self.ids.rows.add_widget(Label(text='No scores saved yet'))
        for i, entry in enumerate(entries, 1):
            self.ids.rows.add_widget(Label(
                text='{:>2}. {:<12} {:>3} pts {:>4} s'.format(
                    i, entry['name'], entry['points'], entry['seconds']),
                font_size='16dp', font_name='data/fonts/RobotoMono-Regular.ttf'))


class SettingsScreen(ButtonColumn):
    """Settings hub: Keyboard layout / Touch controls."""

    def go_back(self):
        self.parent.close_settings()


class TouchSettingsScreen(ButtonColumn):
    """Touch controls: when they are shown and how big they are."""
    touch_settings = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh()

    def refresh(self, message=''):
        ids = self.ids
        if self.touch_settings is None or 'slider_scale' not in ids:
            return
        ids['btn_mode'].text = 'Touch controls: {}'.format(
            self.touch_settings.mode.capitalize())
        percent = round(self.touch_settings.scale * 100)
        ids['lbl_scale'].text = 'Size: {}%'.format(percent)
        slider = ids['slider_scale']
        if abs(slider.value - self.touch_settings.scale) > 1e-6:
            slider.value = self.touch_settings.scale

    def set_scale(self, value):
        """Slider moved: remember in memory, saved when the finger lifts."""
        if self.touch_settings is None:
            return
        self.touch_settings.set_scale(value, save=False)
        self.refresh()

    def save_scale(self):
        if self.touch_settings is not None:
            self.touch_settings.save()

    def adjust(self, step):
        if self.touch_settings is None:
            return
        self.touch_settings.set_scale(
            self.touch_settings.scale + step * 0.1)
        self.refresh()

    def go_back(self):
        self.parent.show_settings()


class KeyboardSettings(ButtonColumn):
    """Keyboard layout: pick an action, then press the new key."""
    bindings = ObjectProperty()
    waiting = StringProperty('')   # action waiting for a key, '' if none
    key_set = NumericProperty(0)   # keyboard set listed and rebound

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh()

    def refresh(self, message=''):
        ids = self.ids
        if 'message' not in ids:
            return
        for action, label in ACTION_LABELS.items():
            if self.waiting == action:
                value = 'press a key...'
            else:
                value = self.bindings.label(action, self.key_set)
            ids['btn_' + action].text = '{}: {}'.format(label, value)
        ids['btn_set'].text = 'Keys of: Set {}'.format(self.key_set + 1)
        ids['message'].text = message

    def switch_set(self):
        self.waiting = ''
        self.key_set = (self.key_set + 1) % KEY_SETS
        self.refresh()

    def go_back(self):
        self.parent.show_settings()

    def begin_rebind(self, action):
        self.waiting = action
        self.refresh()

    def cancel_rebind(self):
        self.waiting = ''
        self.refresh()

    def handle_key(self, key, scancode=None):
        """Consume `key` while waiting for a new binding. Returns True if the
        key was consumed."""
        if not self.waiting:
            return False
        action, self.waiting = self.waiting, ''
        if key == 27:
            self.refresh()
        else:
            error = self.bindings.rebind(
                action, key, scancode, key_set=self.key_set)
            self.refresh(error or '')
        return True

    def reset(self):
        self.waiting = ''
        self.bindings.reset()
        self.refresh()


class FireButton(Widget):
    """Square red button labelled FIRE, like on arcade shooters."""
    action = StringProperty('fire')
    pressed = BooleanProperty(False)
    text_angle = NumericProperty(0)   # turns the label toward the player

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touches = set()
        with self.canvas:
            self._fill_color = Color(0.85, 0.1, 0.1, 0.6)
            self._fill = RoundedRectangle(radius=[dp(10)])
            Color(1, 1, 1, 0.85)
            self._border = Line(width=dp(1.5))
        self._label = Label(
            text='FIRE', bold=True, color=(1, 1, 1, 1), size_hint=(None, None))
        with self._label.canvas.before:
            PushMatrix()
            self._label_turn = Rotate()
        with self._label.canvas.after:
            PopMatrix()
        self.add_widget(self._label)
        self.bind(pos=self._redraw, size=self._redraw, pressed=self._redraw,
                  text_angle=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        self._fill_color.a = 0.9 if self.pressed else 0.6
        self._fill.pos, self._fill.size = self.pos, self.size
        self._border.rounded_rectangle = (x, y, w, h, dp(10))
        self._label.size = self.size
        self._label.pos = self.pos
        self._label.font_size = max(w * 0.26, dp(10))
        self._label_turn.origin = self.center
        self._label_turn.angle = self.text_angle

    def _grab(self, touch):
        touch.grab(self)
        self._touches.add(touch.uid)
        if len(self._touches) == 1:
            self.pressed = True
            self.parent.press(self.action)

    def _drop(self, touch):
        if touch.uid not in self._touches:
            return
        touch.ungrab(self)
        self._touches.discard(touch.uid)
        if not self._touches:
            self.pressed = False
            self.parent.release(self.action)

    def cancel(self):
        """Release the button, e.g. when the overlay is hidden mid-press."""
        if self._touches:
            self._touches.clear()
            self.pressed = False
            self.parent.release(self.action)

    def on_touch_down(self, touch):
        if not self.parent.active or not self.collide_point(*touch.pos):
            return False
        self._grab(touch)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self and not self.collide_point(*touch.pos):
            self._drop(touch)
        return touch.grab_current is self

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            self._drop(touch)
            return True
        return False


# Touch controls at 100%, in dp so that they follow the device's own density
# (the screen DPI Kivy measures is unreliable on Android): about a thumb.
STICK_DP = 110
FIRE_DP = 76
MARGIN_DP = 30    # space between the touch controls and the screen edges


class Joystick(Widget):
    """Virtual stick: drag the knob up (thrust), left or right; positions in
    between press two actions at once. Down and the centre do nothing.
    `angle` turns these directions toward a player seated at a side of the
    screen: up is then away from the player."""
    THRESHOLD = 0.35        # share of the radius needed to trigger an action
    knob = ListProperty([0.0, 0.0])   # offset from the centre, -1..1
    angle = NumericProperty(0)        # seat: -90 left side, 90 right side

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch = None
        self._held = set()
        with self.canvas:
            Color(1, 1, 1, 0.15)
            self._base = Ellipse()
            Color(1, 1, 1, 0.6)
            self._ring = Line(width=dp(1.5))
            Color(1, 1, 1, 0.45)
            self._marks = [Triangle() for _ in range(3)]
            self._knob_color = Color(1, 1, 1, 0.35)
            self._knob = Ellipse()
            Color(1, 1, 1, 0.9)
            self._knob_ring = Line(width=dp(1.5))
        self.bind(pos=self._redraw, size=self._redraw, knob=self._redraw,
                  angle=self._redraw)
        self._redraw()

    def _turn(self, dx, dy, angle):
        """(dx, dy) turned counter-clockwise by `angle` degrees."""
        a = math.radians(angle)
        return (dx * math.cos(a) - dy * math.sin(a),
                dx * math.sin(a) + dy * math.cos(a))

    @property
    def knob_size(self):
        return self.width * 0.42

    def _redraw(self, *args):
        cx, cy = self.center
        r = self.width / 2
        self._base.pos, self._base.size = self.pos, self.size
        self._ring.circle = (cx, cy, r - dp(1))
        k = r * 0.1
        for mark, seat_dir in zip(self._marks, ((0, 1), (-1, 0), (1, 0))):
            dx, dy = self._turn(*seat_dir, self.angle)   # up, left, right
            mx, my = cx + dx * r * 0.82, cy + dy * r * 0.82
            px, py = -dy, dx          # perpendicular
            mark.points = [
                mx + dx * k, my + dy * k,
                mx - dx * k + px * k, my - dy * k + py * k,
                mx - dx * k - px * k, my - dy * k - py * k,
            ]
        reach = r - self.knob_size / 2
        kx = cx + self.knob[0] * reach
        ky = cy + self.knob[1] * reach
        self._knob_color.a = 0.55 if self._touch is not None else 0.35
        self._knob.size = (self.knob_size, self.knob_size)
        self._knob.pos = (kx - self.knob_size / 2, ky - self.knob_size / 2)
        self._knob_ring.circle = (kx, ky, self.knob_size / 2 - dp(1))

    def collide_point(self, x, y):
        r = self.width / 2
        return (x - self.center_x) ** 2 + (y - self.center_y) ** 2 <= r * r

    def _follow(self, pos):
        r = max(self.width / 2, 1)
        dx = (pos[0] - self.center_x) / r
        dy = (pos[1] - self.center_y) / r
        length = (dx * dx + dy * dy) ** 0.5
        if length > 1:
            dx, dy = dx / length, dy / length
        self.knob = [dx, dy]
        dx, dy = self._turn(dx, dy, -self.angle)   # as seen from the seat
        t = self.THRESHOLD
        wanted = set()
        if dx < -t:
            wanted.add('left')
        if dx > t:
            wanted.add('right')
        if dy > t:
            wanted.add('up')
        self._apply(wanted)

    def _apply(self, wanted):
        for action in self._held - wanted:
            self.parent.release(action)
        for action in wanted - self._held:
            self.parent.press(action)
        self._held = wanted

    def cancel(self):
        """Recentre and release everything, e.g. when the pad is hidden."""
        if self._touch is not None:
            self._touch.ungrab(self)
            self._touch = None
        self._apply(set())
        self.knob = [0.0, 0.0]

    def on_touch_down(self, touch):
        if (self._touch is not None or not self.parent.active
                or not self.collide_point(*touch.pos)):
            return False
        touch.grab(self)
        self._touch = touch
        self._follow(touch.pos)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self and touch is self._touch:
            self._follow(touch.pos)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self and touch is self._touch:
            self.cancel()
            return True
        return False


class ScreenButtonsLayout(Widget):
    """Touch overlay: joystick bottom-left, fire bottom-right. A hidden
    layout lets all touches through."""
    active = BooleanProperty(True)
    side = StringProperty('')    # '' whole screen; 'left' / 'right' half

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scale = 1.0
        self.stick = Joystick(size=(dp(STICK_DP), dp(STICK_DP)), size_hint=(None, None))
        self.add_widget(self.stick)
        self.fire = FireButton(size=(dp(FIRE_DP), dp(FIRE_DP)), size_hint=(None, None))
        self.add_widget(self.fire)
        self.bind(size=self._layout)
        self._layout()

    def set_scale(self, scale):
        self.scale = scale
        self._layout()

    def _base_sizes(self):
        """Joystick and FIRE size at 100%, but on a small screen no more
        than 40% and 25% of its height."""
        return (min(dp(STICK_DP), self.height * 0.4),
                min(dp(FIRE_DP), self.height * 0.25))

    def _layout(self, *args):
        # keep a margin to the screen edges; controls are never larger than
        # the window height and half its width allow, so they do not overlap
        margin = dp(MARGIN_DP)
        if self.side:
            self._layout_side(margin)
            return
        limit = max(min(self.height - margin - cm(0.5),
                        self.width / 2 - margin * 1.5), cm(1))
        stick, fire = self._base_sizes()
        side = min(stick * self.scale, limit)
        self.stick.size = (side, side)
        side = min(fire * self.scale, limit)
        self.fire.size = (side, side)
        self.stick.pos = (margin, margin)
        self.fire.pos = (self.width - margin - self.fire.width, margin)

    def _layout_side(self, margin):
        """Two players sit on opposite sides with the screen between them:
        each has the two controls at the two ends of their own side of the
        screen, joystick under the left hand and FIRE under the right hand
        as seen from their seat. Player 1 (left side, facing right) has the
        joystick at the top and FIRE in the bottom corner; player 2 (right
        side, facing left) FIRE at the top and the joystick in the bottom
        corner, so the two sides are the same turned half a circle. The top
        control sits just below the top row of status text."""
        gap = cm(0.3)
        top_room = dp(40)
        stick, fire = (size * self.scale for size in self._base_sizes())
        room_h = max(self.height - margin - top_room - gap, cm(2))
        shrink = min(1.0, room_h / (stick + fire))
        room_w = max(self.width / 2 - margin * 2, cm(1))
        stick = max(min(stick * shrink, room_w), cm(1))
        fire = max(min(fire * shrink, room_w), cm(1))
        self.stick.size = (stick, stick)
        self.fire.size = (fire, fire)
        top = self.height - top_room
        # the FIRE label reads upright from the player's seat, and the stick
        # pushes away from the player for thrust
        self.fire.text_angle = -90 if self.side == 'left' else 90
        self.stick.angle = self.fire.text_angle
        if self.side == 'left':
            x = margin
            self.stick.pos = (x, top - stick)
            self.fire.pos = (x + (stick - fire) / 2, margin)
        else:
            x = self.width - margin - stick
            self.stick.pos = (x, margin)
            self.fire.pos = (x + (stick - fire) / 2, top - fire)

    def press(self, action):
        if self.parent is not None:
            self.parent.press(action)

    def release(self, action):
        if self.parent is not None:
            self.parent.release(action)

    def set_active(self, active):
        self.active = active
        self.opacity = 1 if active else 0
        if not active:
            self.stick.cancel()
            self.fire.cancel()

    def on_touch_down(self, touch):
        if not self.active:
            return False
        return super().on_touch_down(touch)


class ControlsManager(Widget):
    """Turns abstract actions (up, left, right, fire) into spaceship
    commands. Actions come from keyboard, gamepad and on-screen buttons."""
    spaceship = ObjectProperty()
    side = StringProperty('')   # touch controls: '', 'left' or 'right' half
    # 'auto': shown by the touch setting (single player); 'on' for a player
    # who joined by touch; 'off' for keyboard and gamepad players
    touch = StringProperty('auto')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.held = set()
        self.touch_buttons = ScreenButtonsLayout(side=self.side)
        self.add_widget(self.touch_buttons)

    def show_touch_buttons(self, visible):
        self.touch_buttons.set_active(visible)

    def press(self, action):
        if action in self.held:
            return
        self.held.add(action)
        if action == 'fire':
            self.spaceship.shot()
        self._apply()

    def release(self, action):
        self.held.discard(action)
        self._apply()

    def _apply(self):
        spaceship = self.spaceship
        if ('up' in self.held) != spaceship.thrust:
            if 'up' in self.held:
                spaceship.thrust_on()
            else:
                spaceship.thrust_off()

        left, right = 'left' in self.held, 'right' in self.held
        if left and not right:
            spaceship.turn_left()
        elif right and not left:
            spaceship.turn_right()
        else:
            spaceship.stop_rotation()


class ShipPreview(Widget):
    """The ship of a player, drawn large, in the chosen cabin colour."""
    texture = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._redraw, size=self._redraw, texture=self._redraw)

    def _redraw(self, *args):
        side = min(self.size)
        self._rect.texture = self.texture
        self._rect.size = (side, side)
        self._rect.pos = (self.center_x - side / 2, self.center_y - side / 2)


class ShipSelectScreen(BoxLayout):
    """Pick the cabin colour of each player's ship and see it before the
    game starts. Everyone presses ready to begin."""

    def __init__(self, colors, players=1, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(10), **kwargs)
        self.ship_colors = colors
        self.players = players
        self.ready = [False] * players
        self.size = (dp(260) * players + dp(20), dp(330))
        self.panels = []
        row = BoxLayout(spacing=dp(10))
        for player in range(players):
            row.add_widget(self._panel(player))
        self.add_widget(row)
        self.back_button = Button(
            text='Back', size_hint_y=None, height=dp(48),
            on_press=lambda *a: self.go_back())
        self.add_widget(self.back_button)
        self.bind(size=self._center, parent=self._center)
        self._center()
        self.refresh()

    def _center(self, *args):
        self.pos = ((Window.width - self.width) / 2,
                    (Window.height - self.height) / 2)

    def _panel(self, player):
        panel = BoxLayout(orientation='vertical', spacing=dp(6))
        title = Label(text='Player {}'.format(player + 1), size_hint_y=None,
                      height=dp(30), bold=True)
        preview = ShipPreview()
        name = Label(size_hint_y=None, height=dp(28))
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        prev = Button(text='<', size_hint_x=0.25,
                      on_press=lambda *a: self.change(player, -1))
        ready = Button(on_press=lambda *a: self.toggle_ready(player))
        nxt = Button(text='>', size_hint_x=0.25,
                     on_press=lambda *a: self.change(player, 1))
        for widget in (prev, ready, nxt):
            buttons.add_widget(widget)
        for widget in (title, preview, name, buttons):
            panel.add_widget(widget)
        self.panels.append({
            'title': title, 'preview': preview, 'name': name,
            'ready': ready, 'prev': prev, 'next': nxt})
        return panel

    def refresh(self):
        for player, panel in enumerate(self.panels):
            color = self.ship_colors.colors[player]
            panel['preview'].texture = cabin_textures(color)[0]
            panel['title'].color = (*cabin_rgb(color), 1)
            panel['name'].text = color.capitalize()
            panel['ready'].text = 'Ready!' if self.ready[player] else 'Ready?'

    def change(self, player, step):
        """Next / previous colour for `player`, until they are ready."""
        if self.ready[player]:
            return
        self.ship_colors.cycle(player, step, self.players)
        self.refresh()

    def toggle_ready(self, player):
        self.ready[player] = not self.ready[player]
        self.refresh()
        if all(self.ready) and self.parent is not None:
            self.parent.start_selected()

    def handle(self, device, action):
        """A press from any keyboard set or gamepad: one player only."""
        if action == 'back':
            self.go_back()
        elif action in ('left', 'right'):
            self.change(0, -1 if action == 'left' else 1)
        elif action == 'fire':
            self.toggle_ready(0)

    def go_back(self):
        if self.parent is not None:
            self.parent.close_ship_select()


def device_kind(device):
    """'keys', 'pad' or 'touch' for a device of the join screen."""
    return device[0] if device else None


class SideJoinButton(ButtonBehavior, Widget):
    """Tall strip at the left or right edge of the join screen: tapping it
    joins a touch player who sits on that side. The label is turned to read
    from that seat, like the FIRE label in the game."""
    side = StringProperty('left')
    text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fill_color = Color(1, 1, 1, 0.12)
            self._fill = RoundedRectangle(radius=[dp(10)])
            self._border_color = Color(0.3, 0.6, 1, 1)
            self._border = Line(width=dp(1.5))
        self._label = Label(halign='center', valign='middle',
                            size_hint=(None, None))
        with self._label.canvas.before:
            PushMatrix()
            self._turn = Rotate()
        with self._label.canvas.after:
            PopMatrix()
        self.add_widget(self._label)
        self.bind(pos=self._redraw, size=self._redraw, text=self._redraw,
                  side=self._redraw, disabled=self._redraw,
                  state=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        self._fill.pos, self._fill.size = self.pos, self.size
        self._border.rounded_rectangle = (x, y, w, h, dp(10))
        self._fill_color.a = 0.3 if self.state == 'down' else 0.12
        self._border_color.a = 0.3 if self.disabled else 1
        label = self._label
        label.text = self.text
        label.color = (1, 1, 1, 0.5 if self.disabled else 1)
        # from pos and size: `center` can still be stale while resizing
        center = (x + w / 2, y + h / 2)
        label.size = (h, w)            # turned a quarter: runs along the strip
        label.text_size = (h - dp(16), w)
        label.center = center
        self._turn.origin = center
        self._turn.angle = -90 if self.side == 'left' else 90


class JoinScreen(BoxLayout):
    """Multiplayer: each player joins a slot with the device they play with
    (FIRE on a keyboard set or gamepad, or the touch strip at the side of
    the screen where they sit), then picks a colour and gets ready with
    that device. The slot shows the
    device and lights up on its input, so everyone sees which keys or pad
    drive which ship. A device is (kind, id): ('keys', set),
    ('pad', stick id) or ('touch', 'left' / 'right')."""
    FLASH_TIME = 0.25

    STRIP_WIDTH = dp(64)

    def __init__(self, colors, bindings, touch=True, **kwargs):
        super().__init__(spacing=dp(10), **kwargs)
        self.ship_colors = colors
        self.bindings = bindings
        self.touch = touch      # offer joining by touch (side strips)
        self.slots = [None] * MAX_PLAYERS
        self.ready = [False] * MAX_PLAYERS
        self.flashing = [False] * MAX_PLAYERS
        # the whole window width, so the touch strips are at the screen
        # edges; fits small phones (about 360dp high in landscape) and TVs
        self.size = (Window.width - dp(10),
                     min(dp(450), Window.height - dp(10)))
        self.side_buttons = {
            side: SideJoinButton(
                side=side, size_hint_x=None, width=self.STRIP_WIDTH,
                on_press=lambda b: self.join_touch(b.side))
            for side in TOUCH_SIDES}
        middle = BoxLayout(
            orientation='vertical', spacing=dp(10), size_hint_x=None,
            width=min(dp(190) * MAX_PLAYERS + dp(30),
                      self.width - 2 * (self.STRIP_WIDTH + dp(10))))
        self.panels = []
        row = BoxLayout(spacing=dp(10))
        for slot in range(MAX_PLAYERS):
            row.add_widget(self._panel(slot))
        middle.add_widget(row)
        bottom = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.back_button = Button(
            text='Back', size_hint_x=0.3, on_press=lambda *a: self.go_back())
        self.message = Label()
        bottom.add_widget(self.back_button)
        bottom.add_widget(self.message)
        middle.add_widget(bottom)
        for widget in (self.side_buttons['left'], Widget(), middle, Widget(),
                       self.side_buttons['right']):
            self.add_widget(widget)
        self.bind(size=self._center, parent=self._center)
        self._center()
        self.refresh()

    def _center(self, *args):
        self.pos = ((Window.width - self.width) / 2,
                    (Window.height - self.height) / 2)

    def _panel(self, slot):
        panel = BoxLayout(orientation='vertical', spacing=dp(6),
                          padding=dp(8))
        with panel.canvas.before:
            border_color = Color(1, 1, 1, 0.3)
            border = Line(width=dp(1.5))
        panel.bind(pos=self._draw_border, size=self._draw_border)

        def row(*children):
            box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            for child in children:
                box.add_widget(child)
            return box

        prev = Button(text='<', size_hint_x=0.3,
                      on_press=lambda *a: self.change(slot, -1))
        nxt = Button(text='>', size_hint_x=0.3,
                     on_press=lambda *a: self.change(slot, 1))
        name = Label()
        ready = Button(on_press=lambda *a: self.toggle_ready(slot))
        leave = Button(text='Leave', size_hint_x=0.7,
                       on_press=lambda *a: self.leave(slot))
        widgets = {
            'panel': panel, 'border': border, 'border_color': border_color,
            'title': Label(text='Player {}'.format(slot + 1), bold=True,
                           size_hint_y=None, height=dp(28)),
            'device': Label(size_hint_y=None, height=dp(24)),
            'preview': ShipPreview(),
            'name': name, 'prev': prev, 'next': nxt,
            'colour_row': row(prev, name, nxt),
            'ready': ready, 'leave': leave,
            'action_row': row(ready, leave),
            'hint': Label(size_hint_y=None, height=dp(34), font_size='12dp',
                          halign='center'),
            'empty': Label(text='Press FIRE on a keyboard set or gamepad'
                                '\n\nor tap a side of the screen to play '
                                'by touch there',
                           halign='center', valign='middle'),
        }
        empty = widgets['empty']
        empty.bind(size=lambda label, size: setattr(label, 'text_size', size))
        self.panels.append(widgets)
        return panel

    def _draw_border(self, panel, *args):
        for widgets in self.panels:
            if widgets['panel'] is panel:
                widgets['border'].rectangle = (*panel.pos, *panel.size)

    # ---- state ---------------------------------------------------------

    @property
    def joined(self):
        return [i for i, device in enumerate(self.slots) if device]

    def slot_of(self, device):
        if device is None or device not in self.slots:
            return None
        return self.slots.index(device)

    @property
    def can_start(self):
        joined = self.joined
        return len(joined) >= 2 and all(self.ready[i] for i in joined)

    def join(self, device, slot=None):
        """`device` takes `slot` (default: the first free one). Returns the
        slot, or None when the device already plays or nothing is free."""
        if device is None or device in self.slots:
            return None
        if slot is None:
            slot = next((i for i, d in enumerate(self.slots) if d is None),
                        None)
        if slot is None or self.slots[slot] is not None:
            return None
        self.slots[slot] = device
        self.ready[slot] = False
        self.ship_colors.claim(slot, self.joined)
        self.refresh()
        return slot

    def join_touch(self, side):
        """A touch player sits at the `side` whose strip they tapped and
        takes the first free slot; one per side."""
        return self.join(('touch', side))

    def leave(self, slot):
        self.slots[slot] = None
        self.ready[slot] = False
        self.refresh()
        self._maybe_start()

    def change(self, slot, step):
        """Next / previous colour for `slot`, until the player is ready."""
        if self.slots[slot] is None or self.ready[slot]:
            return
        self.ship_colors.cycle(slot, step, active=self.joined)
        self.refresh()

    def toggle_ready(self, slot):
        if self.slots[slot] is None:
            return
        self.ready[slot] = not self.ready[slot]
        self.refresh()
        self._maybe_start()

    def _maybe_start(self):
        if self.can_start and self.parent is not None:
            self.parent.start_joined()

    def handle(self, device, action):
        """A press of `action` from `device` (None: Escape)."""
        slot = self.slot_of(device)
        if slot is None:
            if action == 'back':
                self.go_back()     # Escape, or a pad that has not joined
            elif action == 'fire' and device_kind(device) in ('keys', 'pad'):
                slot = self.join(device)
                if slot is not None:
                    self.flash(slot)
            return
        self.flash(slot)
        kind = device_kind(device)
        if action in ('left', 'right'):
            self.change(slot, -1 if action == 'left' else 1)
        elif action == 'fire':
            self.toggle_ready(slot)
        elif ((kind == 'keys' and action == 'up')
              or (kind == 'pad' and action == 'back')):
            self.leave(slot)

    def flash(self, slot):
        """Light up the slot of the device that was just used."""
        self.flashing[slot] = True
        self.refresh()
        Clock.schedule_once(lambda dt: self._unflash(slot), self.FLASH_TIME)

    def _unflash(self, slot):
        self.flashing[slot] = False
        self.refresh()

    def go_back(self):
        if self.parent is not None:
            self.parent.close_ship_select()

    def allow_touch(self):
        """A touch arrived on a device thought to have no touchscreen."""
        if not self.touch:
            self.touch = True
            self.refresh()

    # ---- drawing -------------------------------------------------------

    def device_label(self, device):
        kind, key = device
        if kind == 'keys':
            return 'Keys ' + ' '.join(
                self.bindings.label(a, key) for a in ('up', 'left', 'right', 'fire'))
        if kind == 'pad':
            return 'Gamepad {}'.format(key + 1)
        return 'Touch · {} side'.format(key)

    def device_hint(self, device):
        kind, key = device
        if kind == 'keys':
            label = partial(self.bindings.label, key_set=key)
            return '{} / {} colour · {} ready\n{} leave'.format(
                label('left'), label('right'), label('fire'), label('up'))
        if kind == 'pad':
            return 'Stick colour · A ready\nBack leave'
        return 'Tap the buttons above'

    def refresh(self):
        for side, strip in self.side_buttons.items():
            slot = self.slot_of(('touch', side))
            strip.opacity = 1 if self.touch else 0
            strip.disabled = slot is not None or not self.touch
            strip.text = ('Tap to join by touch' if slot is None
                          else 'Player {} · touch'.format(slot + 1))
        for slot, w in enumerate(self.panels):
            panel, device = w['panel'], self.slots[slot]
            panel.clear_widgets()
            panel.add_widget(w['title'])
            if device is None:
                w['title'].color = (1, 1, 1, 0.6)
                w['border_color'].rgba = (1, 1, 1, 0.3)
                w['empty'].text = (
                    'Press FIRE on a keyboard set or gamepad' + (
                        '\n\nor tap a side of the screen to play by touch '
                        'there' if self.touch else ''))
                panel.add_widget(w['empty'])
                continue
            color = self.ship_colors.colors[slot]
            rgb = cabin_rgb(color)
            w['title'].color = (*rgb, 1)
            w['border_color'].rgba = (*rgb, 1 if self.flashing[slot] else 0.6)
            w['border'].width = dp(4) if self.flashing[slot] else dp(1.5)
            w['device'].text = self.device_label(device)
            w['device'].color = (*rgb, 1)
            w['preview'].texture = cabin_textures(color)[0]
            w['name'].text = color.capitalize()
            w['ready'].text = 'Ready!' if self.ready[slot] else 'Ready?'
            w['hint'].text = self.device_hint(device)
            for name in ('device', 'preview', 'colour_row', 'action_row',
                         'hint'):
                panel.add_widget(w[name])
        joined = self.joined
        if not joined:
            self.message.text = 'Press FIRE to join'
        elif len(joined) < 2:
            self.message.text = 'At least two players join to start'
        else:
            self.message.text = 'Starts when everyone is ready'


class AnimatedBackground(Widget):
    background = ObjectProperty()
    uv_pos_x_px = NumericProperty()

    def __init__(self, **kwargs):
        super(AnimatedBackground, self).__init__(**kwargs)
        # ToDo: move link to image to kv file
        texture = Image('images/debris.png').texture
        texture.wrap = 'repeat'
        setattr(self, 'background', texture)
        self.animate()
        self.bind(uv_pos_x_px=self.change_uv_pos)

    def change_uv_pos(self, called_by, value):
        self.background.uvpos = (
            value / self.background.size[0],
            self.background.uvpos[1]
        )
        self.property('background').dispatch(self)

    DURATION = 15   # seconds for one trip over the picture

    def animate(self, *args):
        self.uv_pos_x_px = 0
        self._scroll(self.DURATION)

    def _scroll(self, duration):
        self.animation = Animation(
            uv_pos_x_px=self.background.size[0], t='linear',
            duration=duration)
        self.animation.bind(on_complete=self.animate)
        self.animation.start(self)

    def pause(self):
        self.animation.cancel(self)

    def resume(self):
        """Go on from where the picture stopped."""
        width = self.background.size[0]
        self._scroll(self.DURATION * (1 - self.uv_pos_x_px / width))


class SpacePilgrimGame(Widget):
    shots = ListProperty()
    spaceships = ListProperty()
    asteroids = ListProperty()
    explosions = ListProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

        # On-screen controls: shown at start only on Android phones/tablets,
        # on any device as soon as it is touched, and hidden again when a
        # keyboard or gamepad is used. Settings can force them on or off.
        app = App.get_running_app()
        self.touch_settings = TouchSettings(
            os.path.join(app.user_data_dir, 'touch_ui.json')
            if app else None)
        self.touch_ui = self._touch_visibility(
            platform == 'android' and not is_android_tv())
        self._inputs_down = set()
        # join by touch is offered only where touch exists (not on most
        # Android TVs) or once a touch has arrived
        self.has_touch = has_touchscreen()
        self.bindings = KeyBindings(
            os.path.join(app.user_data_dir, 'keybindings.json')
            if app else None)
        self.ship_colors = ShipColors(
            os.path.join(app.user_data_dir, 'ship_colors.json')
            if app else None)
        self.leaderboard = Leaderboard(
            os.path.join(app.user_data_dir, 'leaderboard.json')
            if app else None)
        self.paused = False
        self.elapsed = 0.0   # seconds of the running game
        self.results = []    # PlayerResult of the ships lost so far
        self.last_config = None   # (players, colors, slots) of the game
        self.num_players = 1
        self.controls = []   # one ControlsManager per slot, None if empty/out
        self.slots = None    # multiplayer: slot -> device; None: one player
        self.pad_watch = watch_gamepads()
        Window.bind(
            on_key_down=self._on_key_down,
            on_key_up=self._on_key_up,
            on_keyboard=self._on_keyboard,
            on_joy_axis=self._on_joy_axis,
            on_joy_hat=self._on_joy_hat,
            on_joy_button_down=self._on_joy_button_down,
            on_joy_button_up=self._on_joy_button_up,
            on_touch_down=self._on_window_touch,
        )

    def game_start(self, players=1, colors=None, slots=None):
        """Start a game. Single player by default; a multiplayer game has
        `slots` (slot -> device or None, see JoinScreen); `players` > 1
        without slots is that many players on the keyboard sets and pads.
        Cabin colours are per slot (default: the saved choice)."""
        # reset game status
        [self.remove_shot(shot) for shot in self.shots]
        [self.remove_asteroid(asteroid) for asteroid in self.asteroids]

        # start schedule
        self.frame_schedule.cancel()
        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule.cancel()
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

        for name in ('menu', 'results_screen', 'leaderboard_screen'):
            if hasattr(self, name):
                self.remove_widget(getattr(self, name))
        if self.select_active:
            self.remove_widget(self.select)
            del self.select
        if slots is None and players > 1:
            slots = [('keys', 0), ('keys', 1), ('pad', 0), ('pad', 1)][:players]
        self.slots = list(slots) if slots is not None else None
        colors = list(colors or self.ship_colors.colors)
        self.last_config = (
            players, list(colors), list(slots) if slots is not None else None)
        self.elapsed = 0.0
        self.results = []
        entries = ([(0, None)] if slots is None
                   else [(i, d) for i, d in enumerate(slots) if d])
        self.num_players = len(entries)

        self.statuses = []
        self.controls = [None] * (len(slots) if slots is not None else 1)
        for slot, device in entries:
            kind = device_kind(device)
            touch_side = device[1] if kind == 'touch' else ''
            spaceship = self.add_spaceship(
                slot, 1 if slots is None else MAX_PLAYERS, colors[slot])
            if slots is None:
                side = ''
            else:
                side = touch_side or 'top'
            status = SpaceshipStatus(
                spaceship=spaceship, side=side, column=slot,
                color=(*cabin_rgb(colors[slot]), 1))
            self.add_widget(status)
            self.statuses.append(status)
            touch = ('auto' if slots is None
                     else 'on' if kind == 'touch' else 'off')
            controls = ControlsManager(
                spaceship=spaceship, side=touch_side, touch=touch)
            controls.touch_buttons.set_scale(self.touch_settings.scale)
            if touch_side:
                status.follow(controls.touch_buttons)
            self.add_widget(controls)
            self.controls[slot] = controls
        self.spaceship_status = self.statuses[0]
        self.spaceship_controls = next(c for c in self.controls if c)
        self._show_touch_controls()
        self._inputs_down.clear()

    # ---- input routing -------------------------------------------------

    def _touch_visibility(self, auto_visible):
        mode = self.touch_settings.mode
        if mode == 'auto':
            return auto_visible
        return mode == 'on'

    def cycle_touch_mode(self):
        self.touch_settings.cycle()
        self._set_touch_ui(self.touch_ui, force=True)
        if self.settings_active:
            self.settings.refresh()

    def _set_touch_ui(self, visible, force=False):
        visible = self._touch_visibility(visible)
        if force or visible != self.touch_ui:
            self.touch_ui = visible
            self._show_touch_controls()

    def _show_touch_controls(self):
        """Touch players always see their controls, keyboard and gamepad
        players never; in single player the touch setting decides."""
        if self.paused:
            return
        for controls in self.controls:
            if controls is not None:
                visible = (self.touch_ui if controls.touch == 'auto'
                           else controls.touch == 'on')
                controls.show_touch_buttons(visible)
                # touch play has no Back key: the player's status block
                # offers the pause screen, which leads back to the menu
                for status in self.statuses:
                    if status.spaceship is controls.spaceship:
                        status.show_menu = visible

    def _on_window_touch(self, window, touch):
        self._set_touch_ui(True)
        if not self.has_touch:
            self.has_touch = True
            if self.select_active and isinstance(self.select, JoinScreen):
                self.select.allow_touch()

    def _input(self, source, action, pressed, device=None):
        """Send a press/release of `action` coming from `source` (a hashable
        id of the physical key/button/axis) of `device` (('keys', set) or
        ('pad', stick); None for keys of no set) to the menu or the game."""
        in_game = not (self.settings_active or self.menu_active
                       or self.select_active or self.results_active
                       or self.leaderboard_active or self.name_active
                       or self.paused or hasattr(self, 'confirm_screen'))
        controls = None
        if in_game and action != 'back':
            controls = self._controls_of(device)
            if controls is None:
                return    # a device that did not join this game

        if pressed:
            if source in self._inputs_down:
                return  # key auto-repeat
            self._inputs_down.add(source)
            self._set_touch_ui(False)
        else:
            if source not in self._inputs_down:
                return
            self._inputs_down.discard(source)

        confirm = getattr(self, 'confirm_screen', None)
        if confirm or self.paused:
            if not pressed:
                return
            screen = confirm or self.pause_screen
            if action == 'up':
                screen.move(-1)
            elif action == 'down':
                screen.move(1)
            elif action == 'fire':
                screen.activate()
            elif action == 'back':
                if confirm:
                    self.leave_cancel()
                else:
                    self.resume()
        elif self.settings_active:
            if not pressed or self.settings.waiting:
                return
            if action == 'up':
                self.settings.move(-1)
            elif action == 'down':
                self.settings.move(1)
            elif action == 'left':
                self.settings.adjust(-1)
            elif action == 'right':
                self.settings.adjust(1)
            elif action == 'fire':
                self.settings.activate()
            elif action == 'back':
                self.settings.go_back()
        elif self.select_active:
            if pressed:
                self.select.handle(device, action)
        elif self.name_active:
            if not pressed:
                return
            if action == 'up':
                self.name_screen.move(-1)
            elif action == 'down':
                self.name_screen.move(1)
            elif action == 'fire':
                self.name_screen.activate()
            elif action == 'back':
                self.name_screen.cancel()
        elif self.results_active or self.leaderboard_active:
            if not pressed:
                return
            screen = (self.results_screen if self.results_active
                      else self.leaderboard_screen)
            if action == 'up':
                screen.move(-1)
            elif action == 'down':
                screen.move(1)
            elif action == 'fire':
                screen.activate()
            elif action == 'back':
                self.show_menu()
        elif self.menu_active:
            if not pressed:
                return
            if action == 'up':
                self.menu.move(-1)
            elif action == 'down':
                self.menu.move(1)
            elif action == 'fire':
                self.menu.activate()
            elif action == 'back' and platform != 'android':
                self.confirm_exit()
            # On Android the Back key is left to Kivy: it pauses the app.
        elif action == 'back':
            if pressed:
                self.pause()
        elif controls is not None:
            if pressed:
                controls.press(action)
            else:
                controls.release(action)

    def _controls_of(self, device):
        """Controls driven by `device`: in single player every keyboard set
        and gamepad drives the ship, in multiplayer only the joined slot."""
        if device is None:
            return None
        if self.slots is None:
            return self.controls[0] if self.controls else None
        if device in self.slots:
            return self.controls[self.slots.index(device)]
        return None

    @property
    def menu_active(self):
        return hasattr(self, 'menu') and self.menu in self.children

    @property
    def select_active(self):
        return hasattr(self, 'select') and self.select in self.children

    @property
    def name_active(self):
        return hasattr(self, 'name_screen') and self.name_screen in self.children

    @property
    def results_active(self):
        return (hasattr(self, 'results_screen')
                and self.results_screen in self.children)

    @property
    def leaderboard_active(self):
        return (hasattr(self, 'leaderboard_screen')
                and self.leaderboard_screen in self.children)

    @property
    def settings_active(self):
        return hasattr(self, 'settings') and self.settings in self.children

    def _show_settings_page(self, page):
        if self.settings_active:
            self.remove_widget(self.settings)
        else:
            self.remove_widget(self.menu)
        self.settings = page
        self.add_widget(page)

    def show_settings(self):
        self._show_settings_page(SettingsScreen())

    def show_keyboard_settings(self):
        self._show_settings_page(KeyboardSettings(bindings=self.bindings))

    def show_touch_settings(self):
        self._show_settings_page(
            TouchSettingsScreen(touch_settings=self.touch_settings))

    def show_ship_select(self, players):
        """Ship selection for single player (`players` 1), else the join
        screen of a multiplayer game."""
        self.remove_widget(self.menu)
        if players == 1:
            self.select = ShipSelectScreen(self.ship_colors, 1)
        else:
            self.select = JoinScreen(self.ship_colors, self.bindings,
                                     touch=self.has_touch)
        self.add_widget(self.select)

    def start_selected(self):
        self.ship_colors.save()
        self.game_start(1)

    def start_joined(self):
        self.ship_colors.save()
        self.game_start(slots=self.select.slots)

    def close_ship_select(self):
        self.remove_widget(self.select)
        del self.select
        self.add_widget(self.menu)
        self.menu.highlight()

    def close_settings(self):
        self.remove_widget(self.settings)
        del self.settings
        self.add_widget(self.menu)
        self.menu.highlight()

    def _on_key_down(self, window, key, scancode=None, *args):
        if self.settings_active and self.settings.waiting:
            # ignore auto-repeat of the key until it is released
            self._inputs_down.add(('key', key))
            self.settings.handle_key(key, scancode)
            return
        if self.name_active:
            # typing a nickname: only Escape (cancel) and Enter (in the
            # field) mean something, the game keys must not move the menu
            self._back_from_menu = False
            if key == 27:
                self.name_screen.cancel()
            return
        # Kivy dispatches on_keyboard right after this handler, by which time
        # Back may already have closed the game or settings; remember where
        # the key went down so _on_keyboard judges the screen it was meant for.
        self._back_from_menu = self.menu_active and not self.settings_active
        key_set, action = self.bindings.lookup(key, scancode)
        if action:
            self._input(('key', key), action, True, self._keys(key_set))

    def _on_key_up(self, window, key, scancode=None, *args):
        key_set, action = self.bindings.lookup(key, scancode)
        if action:
            self._input(('key', key), action, False, self._keys(key_set))
        else:
            self._inputs_down.discard(('key', key))

    def _on_keyboard(self, window, key, *args):
        # Stop Kivy from quitting on Escape / pausing on Android Back while
        # playing: Back returns to the menu instead.
        on_menu = getattr(self, '_back_from_menu', None)
        if on_menu is None:
            on_menu = self.menu_active
        self._back_from_menu = None
        if key == 27 and not (platform == 'android' and on_menu):
            return True

    @staticmethod
    def _keys(key_set):
        return None if key_set is None else ('keys', key_set)

    def _joy_input(self, stick, source, action, pressed):
        self._input(source, action, pressed, ('pad', stick))

    def _axis(self, stick, axis, value, negative, positive):
        self._joy_input(
            stick, ('axis', stick, axis, negative), negative,
            value < -JOY_AXIS_DEADZONE)
        self._joy_input(
            stick, ('axis', stick, axis, positive), positive,
            value > JOY_AXIS_DEADZONE)

    def _on_joy_axis(self, window, stick, axis, value):
        value = value / 32767
        if axis == 0:
            self._axis(stick, axis, value, 'left', 'right')
        elif axis == 1:
            self._axis(stick, axis, value, 'up', 'down')

    def _on_joy_hat(self, window, stick, hat, value):
        x, y = value
        self._axis(stick, ('hat', hat, 'x'), x, 'left', 'right')
        self._axis(stick, ('hat', hat, 'y'), -y, 'up', 'down')

    def _on_joy_button_down(self, window, stick, button):
        action = JOY_BUTTON_ACTIONS.get(button)
        if action:
            self._joy_input(stick, ('button', stick, button), action, True)

    def _on_joy_button_up(self, window, stick, button):
        action = JOY_BUTTON_ACTIONS.get(button)
        if action:
            self._joy_input(stick, ('button', stick, button), action, False)

    def game_stop(self):
        """Leave the game (or whatever is shown) for the main menu."""
        self.end_game()
        self.show_menu()

    def show_menu(self):
        for name in ('results_screen', 'leaderboard_screen', 'name_screen'):
            if hasattr(self, name):
                self.remove_widget(getattr(self, name))
                delattr(self, name)
        if hasattr(self, 'menu'):
            self.remove_widget(self.menu)
        self.menu = Menu()
        self.add_widget(self.menu)

    def show_name_entry(self):
        results = self.results_screen.results
        self.remove_widget(self.results_screen)
        top = top_result(results).slot if len(results) > 1 else None
        self.name_screen = NameScreen(
            self.leaderboard.last_name or DEFAULT_NAME, top)
        self.add_widget(self.name_screen)

    def name_done(self, name):
        """Nickname entered (`name`) or cancelled (None): back to results."""
        self.remove_widget(self.name_screen)
        del self.name_screen
        self.add_widget(self.results_screen)
        if name is not None:
            self.results_screen.store_score(name)
        self.results_screen.selected = 0
        self.results_screen.highlight()

    def show_leaderboard(self):
        self.remove_widget(self.menu)
        self.leaderboard_screen = LeaderboardScreen(self.leaderboard.entries)
        self.add_widget(self.leaderboard_screen)

    def game_over(self):
        """Every ship is lost: show how the players did."""
        results = sorted(self.results, key=lambda r: r.slot)
        self.end_game()
        self.results_screen = ResultsScreen(results)
        self.add_widget(self.results_screen)

    def play_again(self):
        self.game_start(*self.last_config)

    def expire_shot(self, shot):
        shot.expiry = Clock.schedule_interval(
            partial(self.remove_shot, shot), shot.lifetime)

    def background_widget(self):
        return next((c for c in self.children
                     if isinstance(c, AnimatedBackground)), None)

    def pause(self):
        """Freeze the world and show the pause screen."""
        if self.paused or not self.spaceships:
            return
        self.paused = True
        self.frame_schedule.cancel()
        self.asteroid_schedule.cancel()
        for shot in self.shots:
            shot.expiry.cancel()
        for explosion in self.explosions:
            if explosion.parent is not None:
                explosion.pause()
        background = self.background_widget()
        if background is not None:
            background.pause()
        Spaceship.sound.stop()
        # nothing may stay held while the touch controls are hidden
        for controls in self.controls:
            if controls is not None:
                controls.held.clear()
                controls._apply()
                controls.show_touch_buttons(False)
        for status in self.statuses:
            status.show_menu = False
        self._inputs_down.clear()
        self.pause_screen = PauseScreen()
        self.add_widget(self.pause_screen)

    def confirm_leave(self):
        """Ask before leaving a paused game for the main menu."""
        self.remove_widget(self.pause_screen)
        self.confirm_screen = ConfirmScreen('leave')
        self.add_widget(self.confirm_screen)

    def confirm_exit(self):
        """Ask before quitting the app from the main menu."""
        self.remove_widget(self.menu)
        self.confirm_screen = ConfirmScreen('exit')
        self.add_widget(self.confirm_screen)

    def leave_cancel(self):
        """Answer "No": back from the question to the screen it came from
        (the pause screen, or the main menu)."""
        exiting = self.confirm_screen.kind == 'exit'
        self._drop_confirm()
        if exiting:
            self.show_menu()
        else:
            self.pause_screen = PauseScreen()
            self.add_widget(self.pause_screen)

    def _drop_confirm(self):
        if hasattr(self, 'confirm_screen'):
            self.remove_widget(self.confirm_screen)
            del self.confirm_screen

    def _unfreeze(self):
        """Run the world again (the pause screen is already gone)."""
        self.paused = False
        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule = Clock.schedule_interval(
            self.generate_asteroid, 2)
        background = self.background_widget()
        if background is not None:
            background.resume()
        for shot in self.shots:
            self.expire_shot(shot)
        for explosion in self.explosions:
            if explosion.parent is not None:
                explosion.resume()
        if any(ship.thrust for ship in self.spaceships):
            Spaceship.sound.play()

    def resume(self):
        """Leave the pause screen: play on from the frozen state."""
        if not self.paused:
            return
        self.remove_widget(self.pause_screen)
        del self.pause_screen
        self._unfreeze()
        self._show_touch_controls()

    def end_game(self):
        if self.paused:
            self._drop_confirm()
            if hasattr(self, 'pause_screen'):
                self.remove_widget(self.pause_screen)
                del self.pause_screen
            self._unfreeze()
        for spaceship in list(self.spaceships):
            self.remove_spaceship(spaceship)

        for status in getattr(self, 'statuses', []):
            self.remove_widget(status)
        self.statuses = []
        for controls in self.controls:
            if controls is not None:
                self.remove_widget(controls)
        self.controls = []
        for name in ('spaceship_status', 'spaceship_controls'):
            if hasattr(self, name):
                delattr(self, name)
        self._inputs_down.clear()
        self.slots = None
        self.num_players = 1

    def update(self, dt):
        if self.spaceships:
            self.elapsed += dt
        [spaceship.update(dt) for spaceship in self.spaceships]
        [shot.update(dt) for shot in self.shots]
        [asteroid.update(dt) for asteroid in self.asteroids]

        for asteroid in list(self.asteroids):
            hit = next((spaceship for spaceship in self.spaceships
                        if asteroid.collide_widget(spaceship)), None)
            if hit is not None:
                self.remove_asteroid(asteroid)
                hit.lives -= 1
                self.add_explosion(asteroid.pos)
                if hit.lives <= 0:
                    self.lose_spaceship(hit)
                    if not self.spaceships:
                        return
                continue
            for shot in list(self.shots):
                if asteroid.collide_widget(shot):
                    self.remove_asteroid(asteroid)
                    shot.spaceship.points += 1
                    self.remove_shot(shot)

                    self.add_explosion(asteroid.pos)
                    break

    def lose_spaceship(self, spaceship):
        """A ship ran out of lives: it leaves the field, its controls stop.
        The game ends once no ship is left."""
        pos = spaceship.pos
        for player, controls in enumerate(self.controls):
            if controls is not None and controls.spaceship is spaceship:
                controls.show_touch_buttons(False)   # lets go of the stick
                self.remove_widget(controls)
                self.controls[player] = None
                self.results.append(PlayerResult(
                    player, spaceship.cabin, spaceship.points, self.elapsed))
        if len(self.spaceships) == 1:
            self.game_over()
        else:
            self.remove_spaceship(spaceship)
        self.add_explosion(pos)

    def add_spaceship(self, player=0, players=1, cabin='blue'):
        spaceship = Spaceship(cabin=cabin)
        spaceship.pos = Vector(*self.center) - Vector(*spaceship.size) / 2
        if players > 1:   # around the centre, a ship length apart
            dx, dy = START_OFFSETS[player]
            spaceship.pos = (Vector(dx, dy) * spaceship.width * 1.5
                             + spaceship.pos)
        self.spaceships.append(spaceship)
        self.add_widget(spaceship)
        return spaceship

    def remove_spaceship(self, spaceship):
        spaceship.thrust_off()
        self.spaceships.remove(spaceship)
        self.remove_widget(spaceship)

    def add_explosion(self, pos):
        explosion = Explosion()
        explosion.pos = pos
        self.add_widget(explosion)
        self.explosions.append(explosion)

    def remove_explosion(self, explosion):
        self.remove_widget(explosion)
        if explosion in self.explosions:
            self.explosions.remove(explosion)

    def remove_asteroid(self, asteroid):
        self.remove_widget(asteroid)
        if asteroid in self.asteroids:
            self.asteroids.remove(asteroid)

    def remove_shot(self, shot, *largs):
        self.remove_widget(shot)
        if shot in self.shots:
            self.shots.remove(shot)

    def generate_asteroid(self, dt):
        # use left, bottom positions because asteroids can fly around screen
        positions = {
            'left':   Vector(0, randint(0, Window.size[1])),
            'bottom': Vector(randint(0, Window.size[0]), 0),
        }
        position = choice(list(positions.values()))

        if (
            len(self.asteroids) < 2 + self.num_players and self.spaceships and
            min(map(lambda s: position.distance(s.pos), self.spaceships)) > 200
        ):
            asteroid = Asteroid()
            asteroid.pos = position
            asteroid.angle = randint(0, 360)
            self.add_widget(asteroid)
            self.asteroids.append(asteroid)


class SpacePilgrimApp(App):
    use_kivy_settings = False
    # Window icon on desktop; Android takes its icon from buildozer.spec.
    icon = 'data/icon.png'

    def build(self):
        hide_system_bars()
        game = SpacePilgrimGame()
        game.game_stop()
        return game

    def on_pause(self):
        return True

    def on_resume(self):
        hide_system_bars()

if __name__ == '__main__':
    SpacePilgrimApp().run()
