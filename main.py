__version__ = "0.6.0"

import colorsys
import itertools
import json
import math
import os
import socket
import sys
import uuid
from collections import namedtuple
from functools import partial
from random import randint, choice
from weakref import WeakSet

# Mix every sound in-app with SDL2_mixer. Kivy's Android default gives each
# sound its own MediaPlayer, and some Android TV devices let only one of them
# be heard at a time (engine and gun cut each other off). Must be set before
# the first kivy import.
os.environ.setdefault('KIVY_AUDIO', 'sdl2')

from kivy.utils import platform

if platform == 'android':
    # Kivy's clock asks ctypes.util for libc to sleep with usleep, and
    # python-for-android answers that with Java reflection (3 s on a slow
    # TV). With the lookup failing, the clock falls back to time.sleep.
    sys.modules['ctypes.util'] = None
    import kivy.clock  # noqa: F401
    del sys.modules['ctypes.util']


def x_resources():
    """The X server's resource database as text (what `xrdb -query`
    prints), read through libX11; '' when there is no X display."""
    import ctypes
    x11 = ctypes.CDLL('libX11.so.6')
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XResourceManagerString.argtypes = [ctypes.c_void_p]
    x11.XResourceManagerString.restype = ctypes.c_char_p   # copied to bytes
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        return ''
    try:
        text = x11.XResourceManagerString(display)
    finally:
        x11.XCloseDisplay(display)
    return text.decode('utf-8', 'replace') if text else ''


def desktop_scale(query=x_resources):
    """The desktop's scale on Linux: Xft.dpi / 96. Kivy draws through X11
    (XWayland on a Wayland desktop), where KDE and GNOME leave the scaling
    to the app and only say it in Xft.dpi; Kivy itself assumes 96 dpi, so
    on a 200% screen every text and button would be half its size."""
    try:
        lines = query().splitlines()
    except (OSError, AttributeError):    # no libX11, or a missing function
        return 1.0
    for line in lines:
        if line.startswith('Xft.dpi:'):
            try:
                dpi = float(line.split(':', 1)[1])
            except ValueError:
                return 1.0
            return round(dpi / 96, 2) if 96 <= dpi <= 480 else 1.0
    return 1.0


# Before the first kivy.metrics or window import: the density is read once.
# KIVY_METRICS_DENSITY set by hand wins.
if (platform == 'linux' and os.environ.get('DISPLAY')
        and 'KIVY_METRICS_DENSITY' not in os.environ):
    _scale = desktop_scale()
    if _scale != 1.0:
        from kivy.config import Config as _Config
        os.environ['KIVY_METRICS_DENSITY'] = '{:g}'.format(_scale)
        os.environ.setdefault('KIVY_DPI', '{:g}'.format(96 * _scale))
        # the window keeps its size on screen too
        for _key in ('width', 'height'):
            _Config.set('graphics', _key, str(round(
                _Config.getint('graphics', _key) * _scale)))

from kivy.animation import Animation
from kivy.core.window import Window, Keyboard
from kivy.core.audio import SoundLoader
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty, StringProperty,
    ListProperty,
)
from kivy.graphics import (
    Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle,
    Rotate, Scale, Translate, Triangle,
)
from kivy.metrics import Metrics, dp, cm
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.logger import Logger

from kivy.core.image import Image
from kivy.graphics.texture import Texture

import network


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
TOUCH_SIDES = ('left', 'right')   # touch seats on a phone, one per side
TALL_SIDES = ('top', 'bottom')    # the same, on a phone held upright
# on a screen big enough (see four_seat_screen) a seat at every edge
FOUR_SEATS = TOUCH_SIDES + ('top', 'bottom')
FOUR_SEAT_MIN_CM = (15, 10)   # landscape width x height for four seats
# turn of what belongs to a seat (labels, joystick) to read from that seat
SEAT_ANGLES = {'bottom': 0, 'right': 90, 'top': 180, 'left': -90}
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
#
# Thrust and fire are rebindable per gamepad (Settings > Gamepad buttons);
# JOY_DEFAULT_BUTTONS are what a gamepad has until then. Back/Start and
# the Android D-pad buttons are fixed and can not be bound: they drive the
# menus and leaving the game, so no binding can lock the player out.
JOY_DEFAULT_BUTTONS = {
    'fire': [0, 2],
    'up': [1, 3],
}
JOY_FIXED_ACTIONS_DESKTOP = {6: 'back', 7: 'back'}
JOY_FIXED_ACTIONS_ANDROID = {
    4: 'back', 6: 'back',
    11: 'up', 12: 'down', 13: 'left', 14: 'right',
}


def _joy_actions(fixed):
    actions = {b: a for a, buttons in JOY_DEFAULT_BUTTONS.items()
               for b in buttons}
    actions.update(fixed)
    return actions


JOY_BUTTON_ACTIONS_DESKTOP = _joy_actions(JOY_FIXED_ACTIONS_DESKTOP)
JOY_BUTTON_ACTIONS_ANDROID = _joy_actions(JOY_FIXED_ACTIONS_ANDROID)
JOY_FIXED_ACTIONS = (JOY_FIXED_ACTIONS_ANDROID if platform == 'android'
                     else JOY_FIXED_ACTIONS_DESKTOP)
JOY_BUTTON_ACTIONS = (JOY_BUTTON_ACTIONS_ANDROID if platform == 'android'
                      else JOY_BUTTON_ACTIONS_DESKTOP)
JOY_AXIS_DEADZONE = 0.5
JOY_STICK_AXES = (0, 1)   # the left stick steers; not a thrust trigger
PAD_ACTIONS = ('up', 'fire')   # the rebindable ones, in page order
PAD_ACTION_LABELS = {'up': 'Thrust', 'fire': 'Fire'}
PAD_BUTTON_NAMES = {0: 'A', 1: 'B', 2: 'X', 3: 'Y'}
# A trigger counts as pulled when it moved this far from rest while its
# binding waits, and its first TRIGGER_DEADZONE of travel gives no thrust.
TRIGGER_CAPTURE_TRAVEL = 0.5
TRIGGER_DEADZONE = 0.1


# A stick (the on-screen one or a gamepad's) starts to thrust when pushed
# this far (share of its range) and reaches full power at the end.
STICK_THRUST_START = 0.35


def stick_level(push):
    """Thrust power 0..1 of a stick pushed `push` (0..1) towards "up"."""
    if push <= STICK_THRUST_START:
        return 0.0
    return min(1.0, (push - STICK_THRUST_START) / (1 - STICK_THRUST_START))


def pad_button_name(button):
    return PAD_BUTTON_NAMES.get(button, 'Button {}'.format(button))


def trigger_level(trigger, value):
    """Thrust power 0..1 of a trigger at axis `value` (-1..1): how far it
    is from its resting value towards the end of its travel."""
    span = trigger['full'] - trigger['rest']
    travel = (value - trigger['rest']) / span if span else 0.0
    travel = min(1.0, max(0.0, travel))
    if travel <= TRIGGER_DEADZONE:
        return 0.0
    return (travel - TRIGGER_DEADZONE) / (1 - TRIGGER_DEADZONE)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class GamepadBindings:
    """Thrust and fire buttons and the optional thrust trigger of every
    gamepad model, optionally persisted as JSON. A layout is kept per pad
    identity (see PadIdentity), so pads of the same model share one and
    different models have their own. `None` stands for a pad that could
    not be identified: it uses the defaults and its changes are kept for
    the session only."""

    VERSION = 1

    def __init__(self, path=None):
        self.path = path
        self.pads = {}        # identity -> profile, as saved
        self.session = None   # profile of unidentified pads (never saved)
        self.load()

    @staticmethod
    def _default_profile():
        return {'buttons': {a: list(b) for a, b in JOY_DEFAULT_BUTTONS.items()},
                'trigger': None}

    def profile(self, identity):
        """The layout of a pad (the defaults for one never changed). Do
        not modify the result."""
        stored = self.session if identity is None else self.pads.get(identity)
        return stored or self._default_profile()

    def _editable(self, identity):
        """The stored profile of a pad, created from the defaults."""
        if identity is None:
            if self.session is None:
                self.session = self._default_profile()
            return self.session
        return self.pads.setdefault(identity, self._default_profile())

    def _changed(self, identity):
        if identity is not None:      # unidentified pads: this session only
            self.save()

    def action_for(self, identity, button):
        """'fire', 'up', ... of a button of a pad; None for an unbound one.
        Fixed buttons (Back, Android D-pad) come first and mean the same on
        every pad. A bound trigger replaces the thrust buttons."""
        fixed = JOY_FIXED_ACTIONS.get(button)
        if fixed:
            return fixed
        profile = self.profile(identity)
        for action, buttons in profile['buttons'].items():
            if button in buttons:
                if action == 'up' and profile['trigger']:
                    return None
                return action

    def label(self, identity, action):
        """What is bound to `action`: its buttons, or for thrust the trigger."""
        profile = self.profile(identity)
        if action == 'up' and profile['trigger']:
            return 'trigger (axis {})'.format(profile['trigger']['axis'])
        return ', '.join(pad_button_name(b) for b in profile['buttons'][action])

    def rebind(self, identity, action, button):
        """Bind `button` to `action` of a pad. Returns None on success or a
        message saying why the button was refused (the old one is kept)."""
        if not isinstance(button, int) or isinstance(button, bool):
            return 'That button can not be used'
        if button in JOY_FIXED_ACTIONS:
            return 'That button is reserved'
        profile = self.profile(identity)
        for other, buttons in profile['buttons'].items():
            # the thrust buttons mean nothing while a trigger thrusts
            if other == 'up' and profile['trigger']:
                continue
            if other != action and button in buttons:
                return 'Already used for {}'.format(PAD_ACTION_LABELS[other])
        edit = self._editable(identity)
        edit['buttons'][action] = [button]
        if action == 'up':
            edit['trigger'] = None     # a button replaces the trigger
        self._changed(identity)

    def bind_trigger(self, identity, axis, rest, full):
        """Make `axis` (resting at `rest`, fully pulled at `full`) the thrust
        of a pad, in place of its thrust buttons. Returns None or a message
        saying why not."""
        if axis in JOY_STICK_AXES:
            return 'The stick is reserved'
        if rest == full:
            return 'That axis can not be used'
        self._editable(identity)['trigger'] = {
            'axis': axis, 'rest': rest, 'full': full}
        self._changed(identity)

    def reset(self, identity):
        """Back to the defaults for one pad; other pads are untouched."""
        if identity is None:
            self.session = None
        else:
            self.pads.pop(identity, None)
        self._changed(identity)

    @staticmethod
    def _valid_trigger(trigger):
        if trigger is None:
            return True
        return (isinstance(trigger, dict)
                and set(trigger) == {'axis', 'rest', 'full'}
                and isinstance(trigger['axis'], int)
                and not isinstance(trigger['axis'], bool)
                and trigger['axis'] not in JOY_STICK_AXES
                and _is_number(trigger['rest']) and _is_number(trigger['full'])
                and abs(trigger['rest']) <= 1 and abs(trigger['full']) <= 1
                and trigger['rest'] != trigger['full'])

    @classmethod
    def _valid_profile(cls, profile):
        if not isinstance(profile, dict) or set(profile) != {'buttons', 'trigger'}:
            return False
        buttons = profile['buttons']
        if not isinstance(buttons, dict) or set(buttons) != set(PAD_ACTIONS):
            return False
        seen = set()
        for ids in buttons.values():
            if not isinstance(ids, list) or not ids:
                return False
            for button in ids:
                if (not isinstance(button, int) or isinstance(button, bool)
                        or button in JOY_FIXED_ACTIONS or button in seen):
                    return False
                seen.add(button)
        return cls._valid_trigger(profile['trigger'])

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict) or data.get('version') != self.VERSION:
            return
        pads = data.get('pads')
        if not isinstance(pads, dict):
            return
        for identity, profile in pads.items():
            if self._valid_profile(profile):
                self.pads[identity] = {
                    'buttons': {a: list(profile['buttons'][a])
                                for a in PAD_ACTIONS},
                    'trigger': (None if profile['trigger'] is None
                                else dict(profile['trigger']))}

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'version': self.VERSION, 'pads': self.pads}, f)
        except OSError:
            pass  # keep the in-memory bindings for this session


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


# machine: in a network game the player's machine (0 the host, else the
# client's peer id), so only that machine offers to save the top score
PlayerResult = namedtuple('PlayerResult', 'slot color points survived machine',
                          defaults=(None,))
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
    """The best games, as JSON: one entry per saved game with an id, the
    player's nickname, points (the rating) and the seconds survived
    (information, only breaks ties); also the last nickname used on this
    device. Best first, at most LEADERBOARD_SIZE entries. Devices of a
    network game exchange their entries (`merge`); the ids keep an entry
    from being counted twice."""

    VERSION = 2

    def __init__(self, path=None):
        self.path = path
        self.entries = []
        self.last_name = ''
        self.load()

    @staticmethod
    def _rank(entry):
        return (-entry['points'], -entry['seconds'])

    @staticmethod
    def new_id():
        return uuid.uuid4().hex[:16]

    @classmethod
    def new_entry(cls, points, seconds, name=DEFAULT_NAME):
        return {'id': cls.new_id(), 'name': clean_name(name),
                'points': int(points), 'seconds': int(seconds)}

    @staticmethod
    def valid_id(ident):
        return (isinstance(ident, str) and 0 < len(ident) <= 32
                and all(c in '0123456789abcdef' for c in ident))

    @classmethod
    def _valid(cls, entry, keep_id=True):
        """The entry as stored, None if it can not be one. Without a valid
        id (files of version 1) it gets a new one."""
        if not (isinstance(entry, dict)
                and all(type(entry.get(k)) is int and entry[k] >= 0
                        for k in ('points', 'seconds'))):
            return None
        ident = entry.get('id')
        if not cls.valid_id(ident):
            if keep_id is False:
                return None
            ident = cls.new_id()
        name = entry.get('name', DEFAULT_NAME)
        if not isinstance(name, str):
            return None
        return {'id': ident, 'name': clean_name(name),
                'points': entry['points'], 'seconds': entry['seconds']}

    def _keep_best(self):
        self.entries.sort(key=self._rank)
        del self.entries[LEADERBOARD_SIZE:]

    def add(self, points, seconds, name=DEFAULT_NAME):
        """Keep the game in the top entries and write the file. False when
        the file could not be written (the entry stays for this session)."""
        entry = self.new_entry(points, seconds, name)
        self.last_name = entry['name']
        self.entries.append(entry)
        self._keep_best()
        return self.save()

    def merge(self, entries):
        """Take the entries of another device that are not here yet (by
        id), keep the best and write the file. True if the list changed."""
        known = {e['id'] for e in self.entries}
        new = []
        for entry in entries:
            entry = self._valid(entry, keep_id=False)
            if entry is not None and entry['id'] not in known:
                known.add(entry['id'])
                new.append(entry)
        if not new:
            return False
        before = [e['id'] for e in self.entries]
        self.entries += new
        self._keep_best()
        if [e['id'] for e in self.entries] == before:
            return False
        self.save()
        return True

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
        valid, seen = [], set()
        for entry in entries:
            entry = self._valid(entry)
            if entry is not None:
                if entry['id'] in seen:
                    entry['id'] = self.new_id()
                seen.add(entry['id'])
                valid.append(entry)
        self.entries = valid
        self._keep_best()
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


_java_declared = False


def declare_java_classes():
    """Android: declare the few Java methods the game calls.

    pyjnius's autoclass reflects every method of a class and of all its
    parents, and does that again for the declared type of each object a
    call returns. getDecorView() returns a View, thousands of methods: that
    took 24 s on a slow TV, blocking its UI thread (no input, no frames).
    autoclass and returned objects use a class declared here instead.

    That holds for every caller, Kivy and python-for-android too, so only
    types they do not call into at run time are declared here."""
    global _java_declared
    if _java_declared:
        return
    from jnius import (
        JavaClass, MetaJavaClass, JavaMethod, JavaStaticField,
        JavaStaticMethod,
    )
    from android import api_version

    class PackageManager(JavaClass, metaclass=MetaJavaClass):
        __javaclass__ = 'android/content/pm/PackageManager'
        hasSystemFeature = JavaMethod('(Ljava/lang/String;)Z')

    class Window(JavaClass, metaclass=MetaJavaClass):
        __javaclass__ = 'android/view/Window'
        getDecorView = JavaMethod('()Landroid/view/View;')
        getInsetsController = JavaMethod(
            '()Landroid/view/WindowInsetsController;')

    class View(JavaClass, metaclass=MetaJavaClass):
        __javaclass__ = 'android/view/View'
        setSystemUiVisibility = JavaMethod('(I)V')

    class Build(JavaClass, metaclass=MetaJavaClass):
        __javaclass__ = 'android/os/Build'
        MODEL = JavaStaticField('Ljava/lang/String;')

    class WifiManager(JavaClass, metaclass=MetaJavaClass):
        __javaclass__ = 'android/net/wifi/WifiManager'
        createMulticastLock = JavaMethod(
            '(Ljava/lang/String;)Landroid/net/wifi/WifiManager$MulticastLock;')

    class MulticastLock(JavaClass, metaclass=MetaJavaClass):
        __javaclass__ = 'android/net/wifi/WifiManager$MulticastLock'
        acquire = JavaMethod('()V')
        release = JavaMethod('()V')
        setReferenceCounted = JavaMethod('(Z)V')

    if api_version >= 30:   # a class missing on older Android would raise
        class WindowInsetsController(JavaClass, metaclass=MetaJavaClass):
            __javaclass__ = 'android/view/WindowInsetsController'
            hide = JavaMethod('(I)V')
            setSystemBarsBehavior = JavaMethod('(I)V')

        class WindowInsetsType(JavaClass, metaclass=MetaJavaClass):
            __javaclass__ = 'android/view/WindowInsets$Type'
            systemBars = JavaStaticMethod('()I')

    _java_declared = True


def is_android_tv():
    if platform != 'android':
        return False
    try:
        declare_java_classes()
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
        declare_java_classes()
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
    appear later (a Bluetooth pad switched on in the menu, or a reconnect,
    on Android and on the desktop alike),
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


def start_pad_watcher(sdl):
    """Start opening newly connected gamepads (see PadWatcher). Returns the
    Clock event, or None when it is not possible."""
    try:
        watcher = PadWatcher(sdl)
        watcher.poll()
        # a plain function: the Clock holds a bound method weakly, and the
        # watcher would be collected, silently ending the polling
        return Clock.schedule_interval(lambda dt: watcher.poll(dt), 0.25)
    except Exception:
        return None


def watch_gamepads():
    """Keep opening newly connected gamepads, on every platform: Kivy only
    opens the ones present at start-up, so a pad that is switched on later
    or unplugged and plugged in again would stay silent. Returns the Clock
    event, or None where SDL can not be reached."""
    sdl = load_sdl()
    return None if sdl is None else start_pad_watcher(sdl)


def load_sdl():
    """The SDL2 library Kivy already runs on, for ctypes; None when it can
    not be found."""
    import ctypes
    try:
        if platform == 'android':
            return ctypes.CDLL('libSDL2.so')
        import glob
        import kivy
        root = os.path.join(os.path.dirname(kivy.__file__), '..')
        for pattern in ('Kivy.libs/libSDL2-2*', 'kivy/.dylibs/libSDL2-2*'):
            for path in sorted(glob.glob(os.path.join(root, pattern))):
                return ctypes.CDLL(path)
        for name in ('libSDL2.so', 'SDL2.dll'):
            try:
                return ctypes.CDLL(name)
            except OSError:
                continue
    except Exception:
        pass
    return None


class PadIdentity:
    """Tells gamepads apart by name and GUID, so that a layout belongs to
    a pad model and is found again after a restart or reconnect. Kivy only
    reports the SDL instance id of a stick, so the name and GUID are asked
    from SDL. Everything it cannot find out is answered with None, an
    empty list or an empty dict: such a pad is "unidentified"."""

    def __init__(self, sdl=None):
        self.sdl = sdl
        if sdl is None:
            return
        import ctypes

        class GUID(ctypes.Structure):
            _fields_ = [('data', ctypes.c_uint8 * 16)]

        try:
            sdl.SDL_NumJoysticks.restype = ctypes.c_int
            sdl.SDL_JoystickGetDeviceInstanceID.argtypes = [ctypes.c_int]
            sdl.SDL_JoystickGetDeviceInstanceID.restype = ctypes.c_int32
            sdl.SDL_JoystickNameForIndex.argtypes = [ctypes.c_int]
            sdl.SDL_JoystickNameForIndex.restype = ctypes.c_char_p
            sdl.SDL_JoystickGetDeviceGUID.argtypes = [ctypes.c_int]
            sdl.SDL_JoystickGetDeviceGUID.restype = GUID
            sdl.SDL_JoystickFromInstanceID.argtypes = [ctypes.c_int32]
            sdl.SDL_JoystickFromInstanceID.restype = ctypes.c_void_p
            sdl.SDL_JoystickNumAxes.argtypes = [ctypes.c_void_p]
            sdl.SDL_JoystickNumAxes.restype = ctypes.c_int
            sdl.SDL_JoystickGetAxis.argtypes = [ctypes.c_void_p, ctypes.c_int]
            sdl.SDL_JoystickGetAxis.restype = ctypes.c_int16
        except AttributeError:
            self.sdl = None   # an SDL without these calls: no identities

    def _devices(self):
        """[(instance id, identity, name)] of the connected pads."""
        sdl = self.sdl
        if sdl is None:
            return []
        try:
            found = []
            for index in range(sdl.SDL_NumJoysticks()):
                name = (sdl.SDL_JoystickNameForIndex(index) or b'').decode(
                    'utf-8', 'replace')
                guid = bytes(sdl.SDL_JoystickGetDeviceGUID(index).data).hex()
                found.append((sdl.SDL_JoystickGetDeviceInstanceID(index),
                              '{}|{}'.format(guid, name), name or 'Gamepad'))
            return found
        except Exception:
            return []

    def _axis_values(self, instance):
        """{axis: value -1..1} of an open pad."""
        sdl = self.sdl
        try:
            handle = sdl.SDL_JoystickFromInstanceID(instance)
            if not handle:
                return {}
            return {axis: sdl.SDL_JoystickGetAxis(handle, axis) / 32767
                    for axis in range(sdl.SDL_JoystickNumAxes(handle))}
        except Exception:
            return {}

    def identity(self, stick):
        """(identity, name) of the pad whose events carry id `stick`."""
        for instance, identity, name in self._devices():
            if instance == stick:
                return identity, name

    def connected(self):
        """[(identity, name)] of the connected pads, one per model."""
        pads = {}
        for _, identity, name in self._devices():
            pads.setdefault(identity, name)
        return list(pads.items())

    def axes(self, identity):
        """Current value of every axis of a connected pad of this model."""
        for instance, other, _ in self._devices():
            if other == identity:
                return self._axis_values(instance)
        return {}


def make_pad_identity():
    try:
        return PadIdentity(load_sdl())
    except Exception:
        return PadIdentity(None)


def has_touchscreen():
    """Whether the device has a touchscreen. Android TV usually has none;
    on desktops a mouse click arrives as a touch, so count it as one."""
    if platform != 'android':
        return True
    try:
        declare_java_classes()
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        return bool(activity.getPackageManager().hasSystemFeature(
            'android.hardware.touchscreen'))
    except Exception:
        return True


def screen_dpi():
    """(x, y) dots per inch of the screen. Kivy's dpi on Android is the
    density bucket, which can be 20% or more off the real one, so ask
    Android for the measured value there."""
    if platform == 'android':
        try:
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = activity.getResources().getDisplayMetrics()
            xdpi, ydpi = float(metrics.xdpi), float(metrics.ydpi)
            # some devices report nonsense: trust it only near the bucket
            bucket = float(metrics.densityDpi)
            if all(bucket / 2 < d < bucket * 2 for d in (xdpi, ydpi)):
                return xdpi, ydpi
        except Exception:
            pass
    return Metrics.dpi, Metrics.dpi


def four_seat_screen(size=None, dpi=None):
    """Whether the screen is big enough (a tablet, not a phone) for four
    touch players, one at each edge."""
    width, height = size or Window.size
    xdpi, ydpi = dpi or screen_dpi()
    width_cm, height_cm = width / xdpi * 2.54, height / ydpi * 2.54
    min_w, min_h = FOUR_SEAT_MIN_CM
    return (max(width_cm, height_cm) >= min_w
            and min(width_cm, height_cm) >= min_h)


def touch_seats(size=None):
    """The seats of touch players on this screen: one per edge on a big
    one; else the two short edges of the window (`size`, default the
    window's), so each player holds a short end: left and right when it
    is wide, top and bottom when it is tall."""
    if four_seat_screen():
        return FOUR_SEATS
    width, height = size or Window.size
    return TOUCH_SIDES if width >= height else TALL_SIDES


def client_seats(size=None):
    """The touch seats of a device joining another device's game (a phone
    joining a TV): as touch_seats, and on a phone held horizontally also
    the bottom edge, for one player holding it with the joystick and FIRE
    under the thumbs."""
    seats = touch_seats(size)
    return seats + ('bottom',) if seats == TOUCH_SIDES else seats


class SoundPool:
    """A few copies of one sound effect, so that it can overlap itself.
    A Kivy Sound restarts when played again, which cuts off the previous
    shot or explosion (another player's, too). Copies are used in turn;
    together with the engine they stay within SDL_mixer's 8 channels."""

    def __init__(self, source, copies):
        self.sounds = [SoundLoader.load(source) for _ in range(copies)]
        if None in self.sounds:
            raise IOError('can not load sound %s' % source)
        self.next = 0

    def play(self):
        self.sounds[self.next].play()
        self.next = (self.next + 1) % len(self.sounds)


class Explosion(Widget):
    frame = NumericProperty(0)
    texture = ObjectProperty()
    sound = SoundPool('sounds/explosion.ogg', 3)

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


NET_IDS = itertools.count(1)   # ids of asteroids and shots in snapshots


class Asteroid(Widget):
    speed = NumericProperty(4)
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.net_id = next(NET_IDS)

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
    sound = SoundPool('sounds/gun.ogg', 4)   # one per player
    spaceship = ObjectProperty()

    def __init__(self, **kwargs):
        super(Shot, self).__init__(**kwargs)
        self.net_id = next(NET_IDS)
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
    thrust_level = NumericProperty(1)   # power 0..1 while `thrust` is on
    angle = NumericProperty(0)
    angle_rotation = NumericProperty(0)
    rotate = StringProperty()
    cabin = StringProperty('blue')
    texture_stop = ObjectProperty(None, allownone=True)
    texture_fly = ObjectProperty(None, allownone=True)
    sound = SoundLoader.load('sounds/engine.ogg')
    sound.loop = True   # thrust is often held longer than the 13 s sample
    # All ships share the one engine sound: it plays while any of them
    # thrusts, so one player letting go must not silence the others.
    thrusting = WeakSet()

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
            self.speed = 3 * self.thrust_level
        else:
            self.speed *= 0.98

        self.pos = Vector(self.speed, 0).rotate(self.angle) + self.pos

    def thrust_on(self):
        if not Spaceship.thrusting:
            self.sound.play()
        Spaceship.thrusting.add(self)
        self.thrust = True

    def thrust_off(self):
        self.thrust = False
        Spaceship.thrusting.discard(self)
        if not Spaceship.thrusting:
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
    # '' one player (top right). Multiplayer: a touch player's seat ('left',
    # 'right', 'top', 'bottom'); keyboard and gamepad players 'row' (a column
    # of the top row) or, when touch players sit at the top or bottom edge,
    # 'corner' (a corner of the screen), or on a two-seat screen held
    # upright 'flank' (beside the middle of a free side), all by `column`
    side = StringProperty('')
    column = NumericProperty(0)         # 'row' and 'corner': the player's slot
    # touch seat: distance from that screen edge to the inner side of the
    # player's touch controls; the block sits just inside it
    inset = NumericProperty(0)
    color = ListProperty([1, 1, 1, 1])  # tint of the text: the cabin colour
    # centre of the Pause button between the player's joystick and FIRE,
    # or [] to keep it next to the lives and points (see place_pause)
    pause_spot = ListProperty([])
    # a client's touch player whose field leaves room at the two ends of
    # their edge: the controls in its corners, the lives and points beside
    # the joystick and Pause beside FIRE, toward the middle of the edge
    ends = BooleanProperty(False)
    along = NumericProperty(-1)         # with `ends`: the joystick's middle
    # a client's other players: [x, y, dx, dy], a corner of the block at
    # (x, y), the block lying toward dx, dy (see Game._band_spots); [] else
    spot = ListProperty([])

    # toward the screen edge of a touch player's seat
    PAUSE_DIRECTIONS = {'left': (-1, 0), 'right': (1, 0), 'top': (0, 1),
                        'bottom': (0, -1)}

    PAUSE_GAP = dp(8)   # room kept between Pause and the controls

    def follow(self, touch_buttons):
        """Keep the block next to the touch controls of its player, whatever
        their size: the joystick is the deepest control of the seat. The
        Pause button goes between the joystick and FIRE."""
        stick, fire = touch_buttons.stick, touch_buttons.fire

        def place(*args):
            if self.side in SEAT_ANGLES:
                self.inset = self.PAUSE_GAP + {
                    'left': stick.right - touch_buttons.x,
                    'right': touch_buttons.right - stick.x,
                    'top': touch_buttons.top - stick.y,
                    'bottom': stick.top - touch_buttons.y,
                }[self.side]
            pause = self.ids.get('pause')
            size = pause.size if pause is not None else (dp(44), dp(44))
            if self.ends and self.side in SEAT_ANGLES:
                self.along = (stick.center_y if self.side in ('left', 'right')
                              else stick.center_x)
                self.pause_spot = self.beside_fire(fire, self.side, size)
            else:
                self.along = -1
                self.pause_spot = self.place_pause(stick, fire, self.side,
                                                   size)
        for widget in (stick, fire, touch_buttons):
            widget.bind(pos=place, size=place)
        self.bind(ends=place)
        place()

    def beside_fire(self, fire, side, size):
        """Centre of the Pause button next to FIRE on the inner side, away
        from the seat's edge (with `ends`)."""
        reach = self.PAUSE_GAP + max(size) / 2
        if side == 'left':
            return [fire.right + reach, fire.center_y]
        if side == 'right':
            return [fire.x - reach, fire.center_y]
        if side == 'top':
            return [fire.center_x, fire.y - reach]
        return [fire.center_x, fire.top + reach]

    def place_pause(self, stick, fire, side, size):
        """Centre of the Pause button: midway between the joystick and FIRE
        along the player's edge (the bottom in single player), its outer
        side (its bottom as the player reads it) on the joystick's outer
        side. [] when the gap between them is too small for it."""
        p = max(size)
        along_y = side in ('left', 'right')
        a, b = sorted((stick, fire),
                      key=lambda w: w.center_y if along_y else w.center_x)
        gap = (b.y - a.top) if along_y else (b.x - a.right)
        if gap < p + 2 * self.PAUSE_GAP:
            return []
        mid = ((stick.center_y + fire.center_y) / 2 if along_y
               else (stick.center_x + fire.center_x) / 2)
        if side == 'left':
            return [stick.x + p / 2, mid]
        if side == 'right':
            return [stick.right - p / 2, mid]
        if side == 'top':
            return [mid, stick.top - p / 2]
        return [mid, stick.y + p / 2]          # bottom, or single player

    @staticmethod
    def angle_of(side):
        """Turn of the text and Pause button: upright from the seat."""
        return SEAT_ANGLES.get(side, 0)

    def screen_boxes(self):
        """Screen boxes of the lives and points (turned with the seat) and,
        while shown, of the Pause button."""
        label = self.ids.get('text_label')
        if label is None:
            return []
        tw, th = label.texture_size
        if self.side in ('left', 'right'):
            tw, th = th, tw
        cx, cy = label.to_window(*label.center)
        boxes = [(cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2)]
        pause = self.ids.get('pause')
        if pause is not None and self.show_menu:
            x, y = pause.to_window(*pause.pos)
            boxes.append((x, y, x + pause.width, y + pause.height))
        return boxes

    @staticmethod
    def two_lines(side, window_width, banded=False):
        """Lives above points: in a corner, beside a side, in the top row
        of a narrow window, or beside a client's field (`banded`)."""
        return (banded or side in ('corner', 'flank')
                or (side == 'row' and window_width < dp(COMPACT_DP)))

    @staticmethod
    def spot_center(text_size, spot):
        """Centre of a block with a corner at `spot` (see `spot`)."""
        x, y, dx, dy = spot
        return x + dx * text_size[0] / 2, y + dy * text_size[1] / 2

    def label_center(self, text_size, window_size, side, inset, column,
                     along=-1):
        """Centre of the lives and points (`text_size` is the unturned
        texture size: turned a quarter, its height runs across the edge).
        A touch player's block is at the middle of their edge, or with
        `along` given beside their joystick."""
        w, h = window_size
        across = text_size[1] / 2
        if side == 'left':
            return inset + across, h / 2 if along < 0 else along
        if side == 'right':
            return w - inset - across, h / 2 if along < 0 else along
        if side == 'top':
            return w / 2 if along < 0 else along, h - inset - across
        if side == 'bottom':
            return w / 2 if along < 0 else along, inset + across
        if side == 'row':
            if w < dp(COMPACT_DP):
                # narrow: two lines, two per row in slot order
                return (w * (column % 2 + 0.5) / 2,
                        h - dp(32) - (column // 2) * dp(52))
            return w * (column + 0.5) / 4, h - dp(ROW_DP)
        if side == 'flank':
            # beside the middle of the left and right edges, in slot order:
            # left above, right above, left below, right below
            half = dp(CORNER_DP) / 2
            return (half if column % 2 == 0 else w - half,
                    h / 2 + (1 if column < 2 else -1) * dp(45))
        if side == 'corner':
            # the middle of the free corner square, in slot order: top-left,
            # top-right, bottom-left, bottom-right
            half = dp(CORNER_DP) / 2
            return (half if column % 2 == 0 else w - half,
                    h - half if column < 2 else half)
        return w - dp(210), h - 50

    def pause_center(self, label_center, text_size, side):
        """Where Pause goes when there is no room between the controls
        (see place_pause): under the lives and points in single player;
        for a touch player on the screen-centre side of the text, away from
        their controls, which leave no room on the edge side."""
        dx, dy = self.PAUSE_DIRECTIONS.get(side, (0, 1))
        offset = text_size[1] / 2 + dp(28)
        return label_center[0] - dx * offset, label_center[1] - dy * offset


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

    def __init__(self, results, network=None, can_save=True, **kwargs):
        super().__init__(**kwargs)
        self.results = results
        self.network = network     # None, 'host' or 'client'
        # a network game's score is saved on the top player's device only
        self.can_save = can_save
        # kv ids are weak: keep the button even while it is not shown
        self.save_button = self.ids.btn_save.__self__
        if not can_save:
            self.remove_widget(self.save_button)
        self.saved = False
        if network == 'client':    # only the host starts the next game
            self.ids.btn_again.text = 'Waiting for the host'
            self.ids.btn_again.disabled = True
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
        if self.saved or not self.can_save or Clock.get_time() < self.armed_at:
            return
        self.parent.show_name_entry()

    def store_score(self, name):
        if self.saved or not self.can_save:
            return
        if self.network is not None:
            # stored once for every device of the network game, by the host
            self.saved = True
            self.ids.btn_save.text = 'Saving…'
            self.ids.btn_save.disabled = True
            self.selected = 0
            self.highlight()
            self.parent.net.save_score(name)
            return
        best = top_result(self.results)
        ok = self.parent.leaderboard.add(best.points, best.survived, name)
        self.saved = True
        self.ids.btn_save.text = 'Saved'
        self.ids.btn_save.disabled = True
        self.ids.message.text = ('' if ok else
                                 'Could not write the file; kept until exit')
        self.selected = 0
        self.highlight()

    def mark_saved(self, by):
        """A network game's score was saved, here or on device `by`."""
        self.saved = True
        self.save_button.text = 'Saved on {}'.format(by)
        self.save_button.disabled = True
        # devices without the button say it in the message line
        self.ids.message.text = '' if self.can_save else \
            'Score saved on {}'.format(by)
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
    """Settings hub: Keyboard layout / Gamepad buttons / Touch controls."""

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


class GamepadSettings(ButtonColumn):
    """Gamepad buttons: choose a pad, then pick thrust or fire and press the
    new button on that pad; thrust can also be given to a trigger by pulling
    it."""
    bindings = ObjectProperty()                # GamepadBindings
    pad_list = ObjectProperty(None)            # () -> [(identity, name)]
    axis_rest = ObjectProperty(None)           # identity -> {axis: value}
    waiting = StringProperty('')               # 'up', 'fire' or ''
    pad = ObjectProperty(None, allownone=True)   # identity being edited
    has_pad = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rest = {}       # axis -> resting value while thrust is awaited
        self.names = {}      # identity -> name
        self.refresh()

    def _choose(self, step=0):
        """Re-read the connected pads and keep (or move) the edited one."""
        pads = list(self.pad_list()) if self.pad_list else []
        self.names = dict(pads)
        identities = [identity for identity, _ in pads]
        before = self.pad
        self.has_pad = bool(identities)
        if not identities:
            self.pad = None
        elif self.pad in identities:
            self.pad = identities[
                (identities.index(self.pad) + step) % len(identities)]
        else:
            self.pad = identities[0]
        if self.pad != before or not self.has_pad:
            self.waiting = ''   # the pad that was waited for is gone

    def refresh(self, message=''):
        ids = self.ids
        if 'message' not in ids:
            return
        self._choose()
        pad = self.pad
        for key in ('btn_pad', 'btn_up', 'btn_fire'):
            ids[key].disabled = not self.has_pad
        if self.has_pad:
            ids['btn_pad'].text = 'Gamepad: {}'.format(self.names[pad])
            for action in PAD_ACTIONS:
                if self.waiting == action:
                    value = ('button or trigger...' if action == 'up'
                             else 'press a button...')
                else:
                    value = self.bindings.label(pad, action)
                ids['btn_' + action].text = '{}: {}'.format(
                    PAD_ACTION_LABELS[action], value)
        else:
            ids['btn_pad'].text = 'Gamepad: none connected'
            for action in PAD_ACTIONS:
                ids['btn_' + action].text = PAD_ACTION_LABELS[action]
        ids['message'].text = message or (
            '' if self.has_pad else 'No gamepad connected')
        self.highlight()

    def switch_pad(self):
        self.waiting = ''
        self._choose(1)
        self.refresh()

    def go_back(self):
        self.parent.show_settings()

    def begin_rebind(self, action):
        """Wait for a button; for thrust also for a pulled trigger."""
        if not self.has_pad:
            return
        self.waiting = action
        if action == 'up':
            # where each axis rests, to tell a pulled trigger from a still one
            self.rest = (
                self.axis_rest(self.pad) if self.axis_rest else {}) or {}
        self.refresh()

    def cancel_rebind(self):
        self.waiting = ''
        self.refresh()

    def handle_key(self, key, scancode=None):
        """Keys while waiting: Escape cancels, others change nothing."""
        if not self.waiting:
            return False
        if key == 27:
            self.cancel_rebind()
        return True

    def handle_button(self, identity, button):
        """A gamepad button while waiting. Always consumed; only a button of
        the pad being edited counts: Back cancels, others are bound."""
        if not self.waiting or identity != self.pad:
            return self.waiting != ''
        if JOY_FIXED_ACTIONS.get(button) == 'back':
            self.cancel_rebind()
        else:
            action, self.waiting = self.waiting, ''
            self.refresh(self.bindings.rebind(identity, action, button) or '')
        return True

    def handle_axis(self, identity, axis, value):
        """An axis while waiting for thrust: the first one pulled far
        enough from its rest is bound as its trigger. Returns True if it was
        consumed."""
        if self.waiting != 'up' or identity != self.pad:
            return False
        if axis in JOY_STICK_AXES:
            return False         # the stick steers: never a trigger
        rest = self.rest.get(axis, 0.0)
        if abs(value - rest) <= TRIGGER_CAPTURE_TRAVEL:
            return False
        self.waiting = ''
        error = self.bindings.bind_trigger(
            identity, axis, rest, 1.0 if value > rest else -1.0)
        self.refresh(error or '')
        return True

    def reset(self):
        self.waiting = ''
        if self.has_pad:
            self.bindings.reset(self.pad)
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
# four-seat layout with keyboard or gamepad players: free corner squares
# this big hold their lives and points
CORNER_DP = 140
ROW_DP = 50       # the one-line top row's middle below the top edge
# narrower windows put keyboard and gamepad players' lives and points two
# per row, in two lines (SpaceshipStatus.label_center)
COMPACT_DP = 600
PAUSE_DP = 44     # the Pause button between a touch player's two controls
STATUS_DP = 44    # a touch player's lives and points across, with the gap


class Joystick(Widget):
    """Virtual stick: drag the knob up (thrust), left or right; positions in
    between press two actions at once. Down and the centre do nothing.
    `angle` turns these directions toward a player seated at a side of the
    screen: up is then away from the player."""
    THRESHOLD = 0.35        # share of the radius needed to trigger an action
    knob = ListProperty([0.0, 0.0])   # offset from the centre, -1..1
    angle = NumericProperty(0)        # seat, see SEAT_ANGLES

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
        self._apply(wanted)
        # thrust has a power: how far up the knob is pushed
        self.parent.thrust(stick_level(dy))

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
        if self.parent is not None:
            self.parent.thrust(0.0)
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
    side = StringProperty('')    # '' whole screen; else the seat's edge
    # a top or bottom seat is taken: every edge has a seat (_layout_edge)
    edges = BooleanProperty(False)
    # the edges of the touch seats taken on this screen; empty: all four
    seats = ListProperty([])
    # the corners holding keyboard and gamepad players' lives and points:
    # 0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right
    corners = ListProperty([])
    # their lives and points sit beside the middle of the left and right edges
    flank = BooleanProperty(False)
    # the slots whose lives and points are in the row along the top
    rows = ListProperty([])
    # a client's field leaves room at the two ends of this seat's edge: the
    # controls go into its corners, whatever else is on screen
    ends = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scale = 1.0
        self.stick = Joystick(size=(dp(STICK_DP), dp(STICK_DP)), size_hint=(None, None))
        self.add_widget(self.stick)
        self.fire = FireButton(size=(dp(FIRE_DP), dp(FIRE_DP)), size_hint=(None, None))
        self.add_widget(self.fire)
        self.bind(size=self._layout, edges=self._layout, seats=self._layout,
                  corners=self._layout, flank=self._layout, rows=self._layout,
                  ends=self._layout)
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
            self.fire.text_angle = self.stick.angle = SEAT_ANGLES[self.side]
            if self.edges:
                self._layout_edge(margin)
            else:
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
        top_room = self._top_room()
        stick, fire = (size * self.scale for size in self._base_sizes())
        room_h = max(self.height - margin - top_room - gap, cm(2))
        shrink = min(1.0, room_h / (stick + fire))
        room_w = max(self.width / 2 - margin * 2, cm(1))
        stick = max(min(stick * shrink, room_w), cm(1))
        fire = max(min(fire * shrink, room_w), cm(1))
        self.stick.size = (stick, stick)
        self.fire.size = (fire, fire)
        top = self.height - top_room
        if self.side == 'left':
            x = margin
            self.stick.pos = (x, top - stick)
            self.fire.pos = (x + (stick - fire) / 2, margin)
        else:
            x = self.width - margin - stick
            self.stick.pos = (x, margin)
            self.fire.pos = (x + (stick - fire) / 2, top - fire)

    CORNER_ENDS = {'top': (0, 1), 'bottom': (2, 3), 'left': (0, 2),
                   'right': (1, 3)}

    def _reach(self, side, stick, margin, gap):
        """How far from the middle of the `side` edge its controls reach.
        They go into the corners unless something else needs them: a seat
        at a long edge keeps clear of the column (controls, then lives and
        points) of a seat at a short edge, or of lives and points beside the
        middle of the left and right edges, and goes as far as the short
        edges' controls (left and right in landscape, top and bottom in
        portrait); a corner holding a keyboard or gamepad player's lives
        and points stays free."""
        w, h = self.size
        along = w if side in ('top', 'bottom') else h
        if self.ends:
            return along / 2 - margin
        taken = set(self.seats) | {side} if self.seats else set(SEAT_ANGLES)
        if self.flank:
            taken |= {'left', 'right'}
        across = ({'left', 'right'} if side in ('top', 'bottom')
                  else {'top', 'bottom'})
        if taken & across:
            # every edge the same distance apart
            short, long = sorted(self.size)
            column = margin + stick + dp(STATUS_DP)
            half = min(short / 2 - margin, long / 2 - column - gap)
            span = short
        else:
            half = along / 2 - margin
            span = along
        if any(corner in self.corners for corner in self.CORNER_ENDS[side]):
            half = min(half, span / 2 - dp(CORNER_DP) - gap)
        return half

    def _top_room(self):
        """Room at the top of a side kept for the row of keyboard and
        gamepad players' lives and points (see SpaceshipStatus.label_center):
        on a narrow window two lines, two per row; else one line. With
        `ends` the joystick goes into the corner."""
        if self.ends:
            return dp(MARGIN_DP)
        if not self.rows:
            return dp(40)
        if self.width < dp(COMPACT_DP):
            lowest = dp(32) + max(c // 2 for c in self.rows) * dp(52)
            return lowest + dp(22) + dp(6)
        return dp(ROW_DP) + dp(12) + dp(6)

    def _edge_sizes(self, margin, gap):
        """Joystick and FIRE size of the edge layout and how far from the
        middle of this seat's edge its controls reach: one size for every
        seat, the controls made smaller until each half of every taken
        edge holds the bigger control and half the Pause button."""
        stick, fire = (size * self.scale for size in self._base_sizes())
        pause = dp(PAUSE_DP) + 2 * gap
        seats = set(self.seats) | {self.side} if self.seats else SEAT_ANGLES

        def fits(k):
            # the lives, points and Pause sit at the middle of the edge
            return all(self._reach(seat, stick * k, margin, gap)
                       >= k * max(stick, fire) + pause / 2 for seat in seats)
        k = 1.0
        if not fits(k):      # the biggest share that fits
            low, high = 0.0, 1.0
            for _ in range(30):
                mid = (low + high) / 2
                low, high = (mid, high) if fits(mid) else (low, mid)
            k = low
        stick, fire = max(stick * k, cm(1)), max(fire * k, cm(1))
        # on a very small window the controls keep their order, side by side
        return stick, fire, max(self._reach(self.side, stick, margin, gap),
                                max(stick, fire) + gap / 2)

    def _layout_edge(self, margin):
        """Up to four players sit one at each edge, facing the centre. Each
        has the two controls on either side of the middle of their edge,
        joystick under the left hand and FIRE under the right hand as seen
        from the seat: left side joystick top, FIRE bottom; right side FIRE
        top, joystick bottom; bottom joystick left, FIRE right; top FIRE
        left, joystick right, as far apart as the screen allows (_reach):
        in the corners when nothing else needs them, else the same distance
        apart on every edge, with the controls of the short edges in the
        corners. FIRE is centred in the band of the joystick, the deepest
        control."""
        gap = cm(0.3)
        stick, fire, half = self._edge_sizes(margin, gap)
        self.stick.size = (stick, stick)
        self.fire.size = (fire, fire)
        w, h = self.size
        inner = margin + (stick - fire) / 2   # FIRE from the edge
        side = self.side
        if side in ('left', 'right'):
            low, high = h / 2 - half, h / 2 + half
        else:
            low, high = w / 2 - half, w / 2 + half
        if side == 'left':
            self.stick.pos = (margin, high - stick)
            self.fire.pos = (inner, low)
        elif side == 'right':
            self.stick.pos = (w - margin - stick, low)
            self.fire.pos = (w - inner - fire, high - fire)
        elif side == 'bottom':
            self.stick.pos = (low, margin)
            self.fire.pos = (high - fire, inner)
        else:
            self.stick.pos = (high - stick, h - margin - stick)
            self.fire.pos = (low, h - inner - fire)

    def press(self, action):
        if self.parent is not None:
            self.parent.press(action)

    def release(self, action):
        if self.parent is not None:
            self.parent.release(action)

    def thrust(self, level):
        """Thrust power of the joystick, 0..1."""
        if self.parent is not None:
            self.parent.set_thrust(level, 'stick')

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
    side = StringProperty('')   # touch controls: '' or the seat's edge
    edges = BooleanProperty(False)          # see ScreenButtonsLayout
    # 'auto': shown by the touch setting (single player); 'on' for a player
    # who joined by touch; 'off' for keyboard and gamepad players
    touch = StringProperty('auto')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.held = set()
        self.analog = {}     # source ('stick', 'trigger') -> thrust power 0..1
        self.touch_buttons = ScreenButtonsLayout(side=self.side,
                                                 edges=self.edges)
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

    def set_thrust(self, level, source='trigger'):
        """Thrust with power `level` (0..1) from an analog `source` (a
        trigger or a stick); the strongest source wins, and a held thrust
        key or button still thrusts at full power."""
        if level > 0:
            self.analog[source] = level
        else:
            self.analog.pop(source, None)
        self._apply()

    def _apply(self):
        spaceship = self.spaceship
        level = 1.0 if 'up' in self.held else max(
            self.analog.values(), default=0.0)
        if level > 0:
            spaceship.thrust_level = level
        if (level > 0) != spaceship.thrust:
            if level > 0:
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
        self.bind(size=self._center, parent=self._attach)
        self._attach()
        self.refresh()

    def _attach(self, *args):
        """Stay centred in the window while shown."""
        Window.unbind(size=self._center)
        if self.parent is not None:
            Window.bind(size=self._center)
        self._center()

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


def is_remote(device):
    """A device of another machine of a network game: ('net', peer, device)."""
    return bool(device) and device[0] == 'net'


def local_device(device):
    """The device as its own machine names it."""
    return device[2] if is_remote(device) else device


def device_kind(device):
    """'keys', 'pad' or 'touch' for a device of the join screen (also for a
    device of another machine)."""
    device = local_device(device)
    return device[0] if device else None


def touch_seat(device):
    """The seat of a touch player on this machine's screen, else ''."""
    if device and not is_remote(device) and device[0] == 'touch':
        return device[1]
    return ''


class Lobby:
    """The player slots of a multiplayer game: which device holds each of
    the MAX_PLAYERS slots, who is ready, and the colours (ShipColors). A
    device is ('keys', set), ('pad', stick), ('touch', seat) or, in a
    network game, ('net', peer, device) for a device of another machine.

    A same-screen game's lobby lives as long as its join screen; a network
    host keeps one for the whole session, so players can also join and
    leave while a game runs. `out` marks a slot whose ship was destroyed
    (it stays out until the game ends)."""

    def __init__(self, colors):
        self.ship_colors = colors
        self.slots = [None] * MAX_PLAYERS
        self.ready = [False] * MAX_PLAYERS
        self.out = [False] * MAX_PLAYERS
        self.in_game = False
        self.names = {}       # network: peer -> machine name

    @property
    def joined(self):
        return [i for i, device in enumerate(self.slots) if device]

    @property
    def free(self):
        return self.slots.count(None)

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
        self.out[slot] = False
        self.ship_colors.claim(slot, self.joined)
        return slot

    def leave(self, slot):
        self.slots[slot] = None
        self.ready[slot] = False
        self.out[slot] = False

    def change(self, slot, step):
        """Next / previous colour for `slot`, until the player is ready."""
        if self.slots[slot] is None or self.ready[slot]:
            return False
        self.ship_colors.cycle(slot, step, active=self.joined)
        return True

    def toggle_ready(self, slot):
        if self.slots[slot] is None:
            return False
        self.ready[slot] = not self.ready[slot]
        return True

    def state(self, slot):
        """How the slot is shown to the other machines."""
        if self.slots[slot] is None:
            return None
        if self.out[slot]:
            return 'out'
        if self.in_game:
            return 'playing'
        return 'ready' if self.ready[slot] else 'joined'

    def peer_slots(self, peer):
        return [i for i, d in enumerate(self.slots)
                if is_remote(d) and d[1] == peer]


class SideJoinButton(ButtonBehavior, Widget):
    """Strip along an edge of the join screen (tall at the left and right,
    wide at the top and bottom): tapping it joins a touch player who sits
    at that edge. The label is turned to read from that seat, like the FIRE
    label in the game."""
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
        if self.side in ('left', 'right'):
            w, h = h, w                # turned a quarter: runs along the strip
        label.size = (w, h)
        label.text_size = (w - dp(16), h)
        label.center = center
        self._turn.origin = center
        self._turn.angle = SEAT_ANGLES[self.side]


class JoinScreen(BoxLayout):
    """Multiplayer: each player joins a slot with the device they play with
    (FIRE on a keyboard set or gamepad, or the touch strip at the edge of
    the screen where they sit), then picks a colour and gets ready with
    that device. The slot shows the
    device and lights up on its input, so everyone sees which keys or pad
    drive which ship. A device is (kind, id): ('keys', set),
    ('pad', stick id) or ('touch', seat) with a seat of `seats`."""
    FLASH_TIME = 0.25

    STRIP_WIDTH = dp(64)

    def __init__(self, colors, bindings, touch=True, seats=TOUCH_SIDES,
                 lobby=None, net=None, name='', default_name='',
                 seats_for=touch_seats, **kwargs):
        super().__init__(spacing=dp(10), **kwargs)
        self.ship_colors = colors
        self.bindings = bindings
        self.touch = touch      # offer joining by touch (side strips)
        self.seats = seats      # touch seats: two short edges, or every edge
        self.seats_for = seats_for  # the seats for the window's shape
        self.lobby = lobby if lobby is not None else Lobby(colors)
        # network game: the host's or client's session glue. A client only
        # shows the host's slots; its devices ask the host to change them.
        self.net = net
        self.mirror = net if net is not None and net.role == 'client' else None
        self.on_change = None   # called after every change (host: tell all)
        self.flashing = [False] * MAX_PLAYERS
        self.middle = middle = BoxLayout(
            orientation='vertical', spacing=dp(10), size_hint_x=None,
            pos_hint={'center_x': 0.5})
        self.panels = []
        # four across, or two rows of two on a narrow window (see _fit)
        self.grid = GridLayout(cols=MAX_PLAYERS, spacing=dp(10))
        for slot in range(MAX_PLAYERS):
            self.grid.add_widget(self._panel(slot))
        # above the panels: where the game is hosted, and what is missing
        top = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(10))
        self.info = Label(font_size='14dp', shorten=True)
        self.message = Label(font_size='14dp', shorten=True)
        for label in (self.info, self.message):
            label.bind(width=lambda l, w: setattr(l, 'text_size', (w, None)))
            top.add_widget(label)
        middle.add_widget(top)
        middle.add_widget(self.grid)
        # below them: Back, and (unless this is another machine's game) the
        # local network toggle and joining a game of another device; one
        # line, or two on a narrow window
        self.bottom = bottom = GridLayout(
            cols=4, size_hint_y=None, height=dp(48), spacing=dp(10))
        self.back_button = Button(
            text='Back', size_hint_x=0.25, on_press=lambda *a: self.go_back())
        self.network_button = Button(
            size_hint_x=0.4, on_press=lambda *a: self.toggle_network())
        self.join_network_button = Button(
            text='Join a network game', size_hint_x=0.3,
            on_press=lambda *a: self.join_network())
        # how the other devices see this one; empty: `default_name`
        self.name_field = TextInput(
            text=name, hint_text=default_name, multiline=False,
            write_tab=False, font_size='14dp', padding=(dp(6), dp(5)),
            input_filter=lambda text, undo: text[
                :max(0, DEVICE_NAME_LIMIT - len(self.name_field.text))])
        self.name_field.bind(focus=self._name_focus)
        # one line: a moment of being shorter than the line while the
        # screen re-fits must not leave the text scrolled out of the box
        self.name_field.bind(size=lambda f, s: setattr(f, 'scroll_y', 0))
        name_box = BoxLayout(orientation='vertical', size_hint_x=0.25)
        name_box.add_widget(Label(text='Device name', font_size='11dp',
                                  size_hint_y=None, height=dp(14)))
        name_box.add_widget(self.name_field)
        self.bar = [self.back_button]
        if self.mirror is None:
            self.back_button.size_hint_x = 0.17
            self.network_button.size_hint_x = 0.28
            self.bar += [self.name_field, self.network_button,
                         self.join_network_button]
        for widget in self.bar:
            bottom.add_widget(name_box if widget is self.name_field
                              else widget)
        if self.mirror is not None:
            bottom.cols = 2
            bottom.add_widget(Widget(size_hint_x=0.75))
        middle.add_widget(bottom)
        self.bar_device = None   # the device moving along the bottom row
        self.bar_index = 0
        self.side_buttons = {}
        self._place_strips()
        self.bind(size=self._center, parent=self._attach)
        self._attach()
        self.refresh()

    # ---- fitting the window ----------------------------------------------

    PANEL_MIN = dp(150)          # narrowest slot panel of four across
    WIDE_BAR = dp(560)           # narrowest middle for a one-line bottom row

    def _strip(self, side):
        across = 'x' if side in ('left', 'right') else 'y'
        return SideJoinButton(
            side=side, on_press=lambda b: self.join_touch(b.side),
            **{'size_hint_' + across: None,
               ('width' if across == 'x' else 'height'): self.STRIP_WIDTH})

    def _place_strips(self):
        """A strip at every seat: left and right beside the panels, top
        and bottom above and below them."""
        self.clear_widgets()
        column = self.middle.parent
        if column is not None:
            column.remove_widget(self.middle)
        self.side_buttons = {side: self._strip(side) for side in self.seats}
        strips = self.side_buttons
        column = BoxLayout(orientation='vertical', spacing=dp(10))
        # with a top or bottom strip, room above and below the panels
        tall = 'top' in strips or 'bottom' in strips
        fillers = (Widget(), Widget()) if tall else (None, None)
        for widget in (strips.get('top'), fillers[0], self.middle,
                       fillers[1], strips.get('bottom')):
            if widget is not None:
                column.add_widget(widget)
        for widget in (strips.get('left'), column, strips.get('right')):
            if widget is not None:
                self.add_widget(widget)
        self._fit()

    def _attach(self, *args):
        """Follow the window while shown."""
        Window.unbind(size=self._on_window)
        if self.parent is not None:
            Window.bind(size=self._on_window)
            self._on_window()

    def _on_window(self, *args):
        """The window changed: empty seats move to the short edges of a
        two-seat screen (a seated touch player keeps theirs), then
        everything fits the new size."""
        if set(self.seats) != set(FOUR_SEATS):
            seated = any(self.slot_of(('touch', side)) is not None
                         for side in self.seats)
            seats = self.seats_for()
            if not seated and seats != self.seats:
                self.seats = seats
                self._place_strips()
                self.refresh()
                return
        self._fit()

    def _fit(self):
        """The whole window width (and with a top or bottom seat its
        height), so the touch strips are at the screen edges; the panels
        four across or two by two, the bottom row in one line or two."""
        strips = self.side_buttons
        tall = 'top' in strips or 'bottom' in strips
        panels_height = min(dp(450), Window.height - dp(10))
        self.size = (Window.width - dp(10),
                     Window.height - dp(10) if tall else panels_height)
        sides = sum(side in strips for side in ('left', 'right'))
        free = self.width - sides * (self.STRIP_WIDTH + dp(10))
        width = min(dp(190) * MAX_PLAYERS + dp(30), free)
        self.middle.width = width
        four = width >= self.PANEL_MIN * MAX_PLAYERS + dp(30)
        self.grid.cols = MAX_PLAYERS if four else 2
        wide = width >= self.WIDE_BAR or self.mirror is not None
        self.bottom.cols = (2 if self.mirror is not None
                            else 4 if wide else 2)
        self.bottom.height = dp(48) if wide else dp(106)
        if tall:
            ends = sum(side in strips for side in ('top', 'bottom'))
            room = self.height - ends * (self.STRIP_WIDTH + dp(10))
            self.middle.size_hint_y = None
            self.middle.height = min(
                panels_height if four else dp(700), room)
        else:
            self.middle.size_hint_y = 1
        self._center()

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
            'device': Label(size_hint_y=None, height=dp(24), shorten=True,
                            shorten_from='right'),
            'preview': ShipPreview(),
            'name': name, 'prev': prev, 'next': nxt,
            'colour_row': row(prev, name, nxt),
            'ready': ready, 'leave': leave,
            'action_row': row(ready, leave),
            'hint': Label(size_hint_y=None, height=dp(34), font_size='12dp',
                          halign='center'),
            'empty': Label(halign='center', valign='middle'),
        }
        empty = widgets['empty']
        empty.bind(size=lambda label, size: setattr(label, 'text_size', size))
        widgets['device'].bind(
            width=lambda label, width: setattr(label, 'text_size', (width, None)))
        self.panels.append(widgets)
        return panel

    def _draw_border(self, panel, *args):
        for widgets in self.panels:
            if widgets['panel'] is panel:
                widgets['border'].rectangle = (*panel.pos, *panel.size)

    # ---- state ---------------------------------------------------------

    @property
    def slots(self):
        return self.lobby.slots

    @property
    def ready(self):
        return self.lobby.ready

    @property
    def joined(self):
        return self.lobby.joined

    def slot_of(self, device):
        return self.lobby.slot_of(device)

    @property
    def can_start(self):
        return self.lobby.can_start

    def join(self, device, slot=None):
        """`device` takes `slot` (default: the first free one). Returns the
        slot, or None when the device already plays or nothing is free."""
        slot = self.lobby.join(device, slot)
        if slot is not None:
            self.refresh()
        return slot

    def join_touch(self, side):
        """A touch player sits at the `side` whose strip they tapped and
        takes the first free slot; one per side, and only at the seats of
        this screen."""
        if side not in self.seats:
            return None
        if self.mirror:
            self.mirror.touch(side)
            return None
        return self.join(('touch', side))

    def leave(self, slot):
        if self.mirror:
            self.mirror.panel(slot, 'leave')
            return
        self.lobby.leave(slot)
        self.refresh()
        self._maybe_start()

    def change(self, slot, step):
        """Next / previous colour for `slot`, until the player is ready."""
        if self.mirror:
            self.mirror.panel(slot, 'prev' if step < 0 else 'next')
            return
        if self.lobby.change(slot, step):
            self.refresh()

    def toggle_ready(self, slot):
        if self.mirror:
            self.mirror.panel(slot, 'ready')
            return
        if self.lobby.toggle_ready(slot):
            self.refresh()
            self._maybe_start()

    def _maybe_start(self):
        if self.can_start and self.parent is not None and not self.mirror:
            self.parent.start_joined()

    def handle(self, device, action):
        """A press of `action` from `device` (None: Escape)."""
        slot = self.slot_of(device)
        if device is not None and (device == self.bar_device or (
                action == 'down' and slot is None)):
            self._bar_action(device, action)
            return
        if self.mirror:
            # the host decides; the client only lights up its own slot
            if slot is None and action == 'back':
                self.go_back()
                return
            if slot is not None:
                self.flash(slot)
            if device is not None:
                self.mirror.act(device, action)
            return
        if slot is None:
            if action == 'back':
                if not is_remote(device):
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

    # ---- the bottom row: Back, local network, join a network game --------

    def _bar_action(self, device, action):
        """A device that has not joined pressed Down: it moves along the
        bottom row (Left / Right), presses a button (FIRE) or goes back up
        to joining (Up)."""
        if self.bar_device is None:
            self.bar_device, self.bar_index = device, 0
        elif action in ('left', 'right'):
            step = -1 if action == 'left' else 1
            self.bar_index = (self.bar_index + step) % len(self.bar)
        elif action == 'fire':
            button = self.bar[self.bar_index]
            self._leave_bar()
            if button is self.name_field:
                button.focus = not button.disabled
            else:
                button.dispatch('on_press')
            return
        elif action == 'up':
            self._leave_bar()
            return
        elif action == 'back':
            self._leave_bar()
            self.go_back()
            return
        self._highlight_bar()

    def _leave_bar(self):
        self.bar_device = None
        self._highlight_bar()

    def _highlight_bar(self):
        for i, button in enumerate(self.bar):
            on = self.bar_device is not None and i == self.bar_index
            # a lighter blue on the name box keeps its text readable
            lit = ((0.6, 0.85, 1, 1) if button is self.name_field
                   else (0.3, 0.7, 1, 1))
            button.background_color = lit if on else (1, 1, 1, 1)

    @property
    def typing(self):
        return self.name_field.focus

    @property
    def typed_name(self):
        """The device name typed in ('' for the default), or None on a
        client's screen, which has no name box."""
        return self.name_field.text.strip() if self.mirror is None else None

    def _name_focus(self, field, focus):
        if not focus and self.parent is not None:
            self.parent.remember_name()

    def toggle_network(self):
        """Open the game to the local network, or close it again."""
        if self.parent is not None:
            self.parent.set_hosting(self.net is None)

    def join_network(self):
        if self.parent is not None:
            self.parent.show_network()

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
        remote = is_remote(device)
        kind, key = local_device(device)
        if kind == 'keys':
            # a network game names the machine instead of the keys (another
            # machine's keys may be bound differently; the hint lists ours)
            text = ('Keys set {}'.format(key + 1) if self.net is not None else
                    'Keys ' + ' '.join(self.bindings.label(a, key)
                                       for a in ('up', 'left', 'right', 'fire')))
        elif kind == 'pad':
            text = 'Gamepad {}'.format(key + 1)
        else:
            text = 'Touch · {} side'.format(key)
        if self.net is not None:
            text += ' · ' + (self.lobby.names.get(device[1], '?') if remote
                             else 'this device')
        return text

    def device_hint(self, device):
        if is_remote(device):
            return 'Plays on that device'
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
                        '\n\nor tap {} of the screen to play by touch '
                        'there'.format('an edge' if 'top' in self.seats
                                       else 'a side')
                        if self.touch else ''))
                panel.add_widget(w['empty'])
                continue
            color = self.ship_colors.colors[slot]
            rgb = cabin_rgb(color)
            w['title'].color = (*rgb, 1)
            w['border_color'].rgba = (*rgb, 1 if self.flashing[slot] else 0.6)
            w['border'].width = dp(4) if self.flashing[slot] else dp(1.5)
            w['device'].text = self.device_label(device)
            if self.net is not None:
                w['device'].font_size = '13dp'
            w['device'].color = (*rgb, 1)
            w['preview'].texture = cabin_textures(color)[0]
            w['name'].text = color.capitalize()
            w['ready'].text = 'Ready!' if self.ready[slot] else 'Ready?'
            # only the machine of a player changes that player's slot
            for name in ('prev', 'next', 'ready', 'leave'):
                w[name].disabled = is_remote(device)
            w['hint'].text = self.device_hint(device)
            for name in ('device', 'preview', 'colour_row', 'action_row',
                         'hint'):
                panel.add_widget(w[name])
        self.name_field.disabled = self.net is not None
        self.network_button.text = 'Local network: {}'.format(
            'On' if self.net is not None else 'Off')
        if self.net is None:
            self.info.text = ''
        joined = self.joined
        if not joined:
            self.message.text = 'Press FIRE to join'
        elif len(joined) < 2:
            self.message.text = 'At least two players join to start'
        else:
            self.message.text = 'Starts when everyone is ready'
        if self.on_change is not None:
            self.on_change()


# ---- network game ------------------------------------------------------------

NET_POLL = 1 / 30     # seconds between polls of the network outside a frame
DEVICE_NAME_LIMIT = 24   # characters of a device name typed in


def make_browser():
    return network.Browser()


def make_host_session(name):
    return network.HostSession(name)


def make_announcer(name, port):
    return network.Announcer(name, port)


def make_client_session(host, port, name):
    return network.ClientSession(host, port, name)


def device_name():
    """How other players see this machine: the model on Android, else the
    host name."""
    if platform == 'android':
        try:
            declare_java_classes()
            from jnius import autoclass
            model = autoclass('android.os.Build').MODEL
            if model:
                return str(model)[:network.NAME_LIMIT]
        except Exception as e:   # noqa: BLE001 - any jnius failure
            Logger.warning('SpacePilgrim: no device model: %s', e)
    try:
        name = socket.gethostname()
    except OSError:
        name = ''
    return (name or 'SpacePilgrim')[:network.NAME_LIMIT]


class MulticastLock:
    """Android: many Wi-Fi drivers drop broadcasts to apps that do not hold
    a multicast lock, so the network screen holds one while it searches
    for games. Nothing to do elsewhere."""

    def __init__(self):
        self.lock = None

    def acquire(self):
        if platform != 'android' or self.lock is not None:
            return False
        try:
            declare_java_classes()
            from jnius import autoclass, cast
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            wifi = cast('android.net.wifi.WifiManager',
                        activity.getSystemService('wifi'))
            lock = wifi.createMulticastLock('spacepilgrim')
            lock.setReferenceCounted(False)
            lock.acquire()
            self.lock = lock
            return True
        except Exception as e:   # noqa: BLE001 - any jnius failure
            Logger.warning('SpacePilgrim: no multicast lock: %s', e)
            return False

    def release(self):
        if self.lock is not None:
            try:
                self.lock.release()
            except Exception:   # noqa: BLE001
                pass
            self.lock = None


class NetworkSettings:
    """The host address typed last and the device name chosen ('' for the
    default), as JSON."""

    def __init__(self, path=None):
        self.path = path
        self.last_address = ''
        self.device_name = ''
        self.load()

    def default_address(self):
        """The last address, or the start of this device's own one (the
        host is usually on the same /24 network)."""
        if self.last_address:
            return self.last_address
        parts = network.local_address().split('.')
        return '.'.join(parts[:3]) + '.' if len(parts) == 4 else ''

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
        address = data.get('last_address')
        if isinstance(address, str) and len(address) <= 64:
            self.last_address = address
        name = data.get('device_name')
        if isinstance(name, str) and len(name) <= DEVICE_NAME_LIMIT:
            self.device_name = name.strip()

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'last_address': self.last_address,
                           'device_name': self.device_name}, f)
        except OSError:
            pass


class NetworkScreen(ButtonColumn):
    """Join a network game: one announced on this Wi-Fi, or a host given by
    its address. The list follows the announcements as they come."""
    ROW = dp(44)

    def __init__(self, browser, message='', **kwargs):
        self.browser = browser      # None when the network can not be read
        self.games = []
        self._signature = None
        self.message_text = message
        super().__init__(orientation='vertical', spacing=dp(8),
                         size_hint=(None, None), **kwargs)
        self.rebuild()
        self.event = Clock.schedule_interval(self.poll, NET_POLL)
        Window.bind(size=self._place)

    def poll(self, dt=0):
        games = self.browser.poll() if self.browser is not None else []
        signature = [(g.key, g.name, g.players, g.playing, g.compatible)
                     for g in games]
        if signature != self._signature:
            self._signature = signature
            self.games = games
            self.rebuild()

    @staticmethod
    def game_label(game):
        if not game.compatible:
            return '{} · other version'.format(game.name)
        return '{} · {}{}/{}'.format(game.name,
                                     'in game · ' if game.playing else '',
                                     game.players, MAX_PLAYERS)

    def _button(self, key, text, on_press, disabled=False):
        button = Button(text=text, size_hint_y=None, height=self.ROW,
                        disabled=disabled, shorten=True,
                        on_press=lambda *a: on_press())
        button.bind(width=lambda b, w: setattr(b, 'text_size', (w - dp(16), None)))
        button.key = key
        return button

    def rebuild(self):
        buttons = self.buttons
        chosen = (buttons[self.selected % len(buttons)].key
                  if buttons else None)
        self.clear_widgets()
        game = lambda: self.parent       # noqa: E731 - the SpacePilgrimGame
        widgets = [Label(text='Join a network game', font_size='24dp',
                         size_hint_y=None, height=dp(36))]
        for found in self.games:
            widgets.append(self._button(
                ('game',) + found.key, self.game_label(found),
                partial(self._join, found), disabled=not found.compatible))
        if not self.games:
            widgets.append(Label(text='Searching for games on this Wi-Fi…',
                                 font_size='14dp', size_hint_y=None,
                                 height=dp(28)))
        widgets += [self._button('address', 'Enter address',
                                 lambda: game().show_address()),
                    self._button('back', 'Back', lambda: game().close_network())]
        self.message = Label(text=self.message_text, font_size='14dp',
                             size_hint_y=None, height=dp(40), halign='center',
                             valign='middle')
        self.message.bind(size=lambda l, s: setattr(l, 'text_size', s))
        widgets.append(self.message)
        for widget in widgets:
            self.add_widget(widget)
        keys = [b.key for b in self.buttons]
        self.selected = keys.index(chosen) if chosen in keys else 0
        self._place()
        self.highlight()

    def _join(self, found):
        if self.parent is not None and found.compatible:
            self.parent.join_game(found.address, found.port, found.name)

    def _place(self, *args):
        height = (sum(c.height for c in self.children)
                  + self.spacing * (len(self.children) - 1))
        self.size = (dp(340), min(height, Window.height - dp(10)))
        self.pos = ((Window.width - self.width) / 2,
                    (Window.height - self.height) / 2)

    def set_message(self, text):
        self.message_text = text
        self.message.text = text

    def close(self):
        self.event.cancel()
        Window.unbind(size=self._place)
        if self.browser is not None:
            self.browser.close()
            self.browser = None


class AddressScreen(ButtonColumn):
    """The host's address typed in (IP or IP:port), for networks where the
    announcements do not arrive."""

    def __init__(self, address, **kwargs):
        super().__init__(**kwargs)
        field = self.ids.field
        field.text = address
        field.focus = True

    def accept(self):
        self.parent.address_done(self.ids.field.text)

    def cancel(self):
        self.parent.address_done(None)


class FieldView(Widget):
    """A client's view of the host's field: the host's window scaled to fit
    this one, keeping its proportions, with a faint outline where the field
    ends. Children are placed in the host's coordinates. The field is turned
    a quarter when that shows it bigger (a wide host on a phone held
    upright); steering is relative to the ship, so the turn changes nothing
    in play. The field always shows as big as the window allows. This
    device's controls and lives and points go into the room beside it
    (`bands` is told along which axis that room is), and the field moves
    away from them (`hud`: a function giving their screen boxes), so they
    sit outside it where they fit; where they do not, they cover its edge.
    Without them it is centred. The field has its own nebula and scrolling debris, so the
    background covers the field only, as on the host; outside it the screen
    is black."""

    def __init__(self, field, hud=None, bands=None, **kwargs):
        super().__init__(**kwargs)
        self.field = tuple(field)
        self.hud = hud
        self.bands = bands
        self.scale = 1.0
        self.offset = (0.0, 0.0)
        self.turned = False
        self.size_on_screen = (0.0, 0.0)
        with self.canvas.before:
            PushMatrix()
            self._translate = Translate()
            self._rotate = Rotate(angle=0, origin=(0, 0))
            self._scale = Scale()
        with self.canvas.after:
            Color(1, 1, 1, 0.3)
            self._outline = Line(width=1)
            PopMatrix()
        self.nebula = Nebula()
        self.debris = AnimatedBackground()
        self.add_widget(self.nebula)
        self.add_widget(self.debris)
        # once more on the next frame, after the controls and the lives and
        # points have followed the window
        self.refit = Clock.create_trigger(self._fit)
        Window.bind(size=self._fit)
        Window.bind(size=self.refit)
        self._fit()

    def set_field(self, field):
        field = tuple(field)
        if field != self.field:
            self.field = field
            self._fit()

    @staticmethod
    def _place(slack, low, high):
        """Where the field starts along an axis with `slack` to spare and
        `low` and `high` wanted free before and after it: centred when that
        leaves both free, else as near the centre as leaves them free, else
        the slack shared in their proportion."""
        if low + high <= max(slack, 0):   # (rounding leaves -0.0001)
            return min(max(slack / 2, low), slack - high)
        return slack * low / (low + high)

    def _room(self, across, slack):
        """How much this device's controls and lives and points want free
        before and after the field along the x (`across`) or y axis: a box
        on one half of the window that starts within the `slack` from its
        edge wants the space up to its far side."""
        size = Window.width if across else Window.height
        low = high = 0.0
        for x0, y0, x1, y1 in (self.hud() if self.hud else ()):
            a, b = (x0, x1) if across else (y0, y1)
            if b <= size / 2 and a < slack:
                low = max(low, b)
            elif a >= size / 2 and size - b < slack:
                high = max(high, size - a)
        return low, high

    def _fit(self, *args):
        width, height = Window.size
        w, h = (max(1, v) for v in self.field)
        flat = min(width / w, height / h)
        turned = min(width / h, height / w)
        self.turned = turned > flat * 1.001
        s = turned if self.turned else flat
        fw, fh = (h * s, w * s) if self.turned else (w * s, h * s)
        if self.bands is not None:
            self.bands('x' if width - fw >= height - fh else 'y')
        self.offset = (
            self._place(width - fw, *self._room(True, width - fw)),
            self._place(height - fh, *self._room(False, height - fh)))
        self.scale = s
        self.size_on_screen = (fw, fh)
        # turned a quarter to the left: the field's bottom edge runs up the
        # right side of its place on screen
        self._translate.xy = (self.offset[0] + (fw if self.turned else 0),
                              self.offset[1])
        self._rotate.angle = 90 if self.turned else 0
        self._scale.xyz = (s, s, 1)
        self._outline.width = max(1.0, dp(1)) / s
        self._outline.rectangle = (0, 0, w, h)
        self.nebula.size = self.debris.size = (w, h)

    def to_screen(self, x, y):
        ox, oy = self.offset
        s = self.scale
        if self.turned:
            return ox + self.size_on_screen[0] - s * y, oy + s * x
        return ox + s * x, oy + s * y

    def detach(self):
        Window.unbind(size=self._fit)
        Window.unbind(size=self.refit)
        self.refit.cancel()
        self.debris.pause()


class RemoteShip:
    """What a client's ControlsManager drives instead of a ship: the
    control state of one player, sent to the host when it changes."""

    def __init__(self, slot, net):
        self.slot = slot
        self.net = net
        self.thrust = False
        self._level = 1.0
        self.turn = 0
        self._sent = (0.0, 0)

    @property
    def thrust_level(self):
        return self._level

    @thrust_level.setter
    def thrust_level(self, level):
        self._level = level
        self._sync()

    def thrust_on(self):
        self.thrust = True
        self._sync()

    def thrust_off(self):
        self.thrust = False
        self._sync()

    def turn_left(self):
        self.turn = -1
        self._sync()

    def turn_right(self):
        self.turn = 1
        self._sync()

    def stop_rotation(self):
        self.turn = 0
        self._sync()

    def shot(self):
        self.net.send({'t': 'fire', 'slot': self.slot})

    def _sync(self):
        state = (round(min(max(self._level, 0.0), 1.0), 3)
                 if self.thrust else 0.0, self.turn)
        if state != self._sent:
            self._sent = state
            self.net.send({'t': 'ctl', 'slot': self.slot,
                           'thrust': state[0], 'turn': state[1]})


class JoinPrompt(Widget):
    """Watching a network game: how to join, and "Tap to join" strips at
    the free touch seats of this device."""
    FULL_TIME = 2.0

    def __init__(self, seats, on_touch_join, seats_for=None, **kwargs):
        super().__init__(**kwargs)
        self.label = Label(font_size='18dp', halign='center',
                           size_hint=(None, None))
        self.label.bind(texture_size=self._layout)
        self.add_widget(self.label)
        self.on_touch_join = on_touch_join
        self.seats_for = seats_for   # the seats follow the window's shape
        self.strips = {}
        self._made = {}
        self._make_strips(seats)
        self.visible = False
        self._full_until = 0
        self._shown = (False, 0, False, ())
        self.show(False)
        Window.bind(size=self._layout)
        self._layout()

    def _make_strips(self, seats):
        """The strips of `seats`; a strip made once is kept (hidden while
        its seat is not offered) for when the window turns back."""
        for side, strip in self._made.items():
            if side not in seats:
                strip.opacity = 0
                strip.disabled = True
        self.strips = {}
        for side in seats:
            strip = self._made.get(side)
            if strip is None:
                strip = SideJoinButton(side=side, text='Tap to join',
                                       size_hint=(None, None))
                strip.bind(on_press=lambda b: self.on_touch_join(b.side))
                self._made[side] = strip
                self.add_widget(strip)
            self.strips[side] = strip

    def _layout(self, *args):
        if self.seats_for is not None:
            seats = tuple(self.seats_for())
            if seats != tuple(self.strips):
                self._make_strips(seats)
                self.show(*self._shown)
        width, height = Window.size
        across = dp(64)
        for side, strip in self.strips.items():
            if side in ('left', 'right'):
                strip.size = (across, height / 2)
                strip.pos = (0 if side == 'left' else width - across,
                             height / 4)
            else:
                strip.size = (width / 2, across)
                strip.pos = (width / 4,
                             0 if side == 'bottom' else height - across)
        self.label.size = self.label.texture_size
        self.label.center = (width / 2, height * 0.3)

    def show(self, visible, free=0, touch=False, taken=()):
        self._shown = (visible, free, touch, taken)
        self.visible = visible
        if Clock.get_time() < self._full_until:
            text = 'The game is full'
        elif free:
            text = 'Press FIRE to join · {} slot{} free'.format(
                free, '' if free == 1 else 's')
        else:
            text = 'The game is full'
        self.label.text = text
        self.label.opacity = 1 if visible else 0
        for side, strip in self.strips.items():
            on = visible and touch and free > 0 and side not in taken
            strip.opacity = 1 if on else 0
            strip.disabled = not on

    def full(self):
        self._full_until = Clock.get_time() + self.FULL_TIME

    def detach(self):
        Window.unbind(size=self._layout)


class NetHost:
    """Hosting a network game: the session with the clients, the
    announcement, and the lobby kept for the whole session."""
    role = 'host'

    def __init__(self, game, session, announcer, address, lobby=None):
        self.game = game
        self.session = session
        self.announcer = announcer
        self.address = address
        self.name = session.name
        # the join screen's players stay when it opens to the network
        self.lobby = lobby if lobby is not None else Lobby(game.ship_colors)
        self.lobby.names[0] = self.name
        self.phase = 'lobby'
        self.game_id = None
        self.results = []
        self.saver = -1          # the machine that may save the top score
        self.saved = {}          # game id -> machine that saved its score
        self.booms = []          # explosions since the last snapshot
        self.closed = False
        self.event = Clock.schedule_interval(self.poll, NET_POLL)

    @property
    def info(self):
        return 'Hosting on {}:{}'.format(self.address, self.session.port)

    def set_phase(self, phase):
        self.phase = self.session.phase = phase
        self.lobby.in_game = phase == 'game'

    def send(self, message):
        if not self.closed:
            self.session.broadcast(message)

    # ---- network events --------------------------------------------------

    def poll(self, dt=0):
        if self.closed:
            return
        for event in self.session.poll():
            if event[0] == 'connect':
                self._connected(event[1], event[2])
            elif event[0] == 'close':
                self.drop(event[1])
            else:
                self._message(event[1], event[2])
            if self.closed:
                return
        self.announcer.tick(len(self.lobby.joined), self.phase == 'game')

    def _connected(self, peer, name):
        self.lobby.names[peer] = name.strip() or 'Device {}'.format(peer)
        self.session.send(peer, self.lobby_message())
        if self.phase == 'game':
            self.session.send(peer, self.start_message())
            if self.game.paused:
                self.session.send(peer, {'t': 'pause'})
        elif self.phase == 'results':
            self.session.send(peer, self.over_message())
            if self.game_id in self.saved:
                self.session.send(peer, {'t': 'saved', 'game': self.game_id,
                                         'by': self.saved[self.game_id]})

    def _message(self, peer, message):
        kind = message['t']
        game = self.game
        if kind == 'bye':
            self.session.disconnect(peer)
            self.drop(peer)
        elif kind == 'lb':
            game.leaderboard.merge(message['entries'])
            self.send(self.lb_message())
        elif kind == 'act':
            self.device_action(('net', peer, message['device']),
                               message['action'])
        elif kind == 'touch':
            self.touch(peer, message['side'])
        elif kind == 'panel':
            self.panel(peer, message['slot'], message['button'])
        elif kind in ('ctl', 'fire'):
            game.net_control(peer, message)
        elif kind == 'pause':
            if self.phase == 'game':
                game.pause()
        elif kind == 'resume':
            if self.phase == 'game':
                game.resume()
        elif kind == 'save':
            self.save(message['game'], message['name'],
                      self.lobby.names.get(peer, ''), peer)
        # the other types only go from the host to the clients

    def join_screen(self):
        game = self.game
        if game.select_active and isinstance(game.select, JoinScreen):
            return game.select
        return None

    def device_action(self, device, action):
        """A press of a client's device."""
        if self.phase == 'lobby':
            select = self.join_screen()
            if select is not None:
                select.handle(device, action)
        elif self.phase == 'game' and action == 'fire':
            self.game.net_join(device)

    def touch(self, peer, side):
        """A client's touch player tapped the strip at `side`: join."""
        device = ('net', peer, ('touch', side))
        if self.phase == 'game':
            self.game.net_join(device)
            return
        select = self.join_screen()
        if self.phase == 'lobby' and select is not None:
            slot = select.join(device)
            if slot is not None:
                select.flash(slot)

    def panel(self, peer, slot, button):
        """A panel button of a slot of the client's."""
        select = self.join_screen()
        if (self.phase != 'lobby' or select is None
                or slot not in self.lobby.peer_slots(peer)):
            return
        select.flash(slot)
        if button in ('prev', 'next'):
            select.change(slot, -1 if button == 'prev' else 1)
        elif button == 'ready':
            select.toggle_ready(slot)
        else:
            select.leave(slot)

    def drop(self, peer):
        """A client left, or its connection closed."""
        slots = self.lobby.peer_slots(peer)
        if self.phase == 'game':
            for slot in slots:
                self.game.remove_player(slot)
        else:
            for slot in slots:
                self.lobby.leave(slot)
            select = self.join_screen()
            if select is not None:
                select.refresh()
                select._maybe_start()
        self.lobby.names.pop(peer, None)
        self.send_lobby()

    # ---- messages ----------------------------------------------------------

    def lobby_message(self):
        lobby = self.lobby
        slots = []
        for slot, device in enumerate(lobby.slots):
            if device is None:
                slots.append(None)
                continue
            peer, own = ((device[1], device[2]) if is_remote(device)
                         else (0, device))
            slots.append([peer, own, lobby.state(slot),
                          lobby.names.get(peer, '')])
        select = self.join_screen()
        return {'t': 'lobby', 'slots': slots,
                'colors': list(lobby.ship_colors.colors),
                'flash': list(select.flashing) if select else
                [False] * MAX_PLAYERS,
                'name': self.name, 'free': lobby.free, 'phase': self.phase}

    def send_lobby(self):
        self.send(self.lobby_message())

    def start_message(self):
        lobby = self.lobby_message()
        return {'t': 'start', 'slots': lobby['slots'],
                'colors': lobby['colors'], 'field': list(Window.size),
                'elapsed': self.game.elapsed}

    def over_message(self):
        return {'t': 'over', 'game': self.game_id, 'saver': self.saver,
                'results': [[r.slot, r.color, int(r.points),
                             round(max(r.survived, 0), 2)]
                            for r in self.results]}

    def lb_message(self):
        return {'t': 'lb', 'entries': self.game.leaderboard.entries}

    # ---- the game ------------------------------------------------------------

    def start_game(self):
        """Everybody on the join screen is ready (or Play again)."""
        lobby = self.lobby
        self.game.ship_colors.save()
        for slot in range(MAX_PLAYERS):
            lobby.ready[slot] = lobby.out[slot] = False
        self.set_phase('game')
        self.booms = []
        self.game.game_start(slots=lobby.slots)
        self.send(self.start_message())
        self.send_lobby()

    def after_frame(self):
        """The world after a frame, to every client (the newest only)."""
        booms, self.booms = self.booms, []
        if self.phase != 'game' or self.closed or not self.session.clients:
            return
        game = self.game
        self.session.snapshot({
            't': 'snap', 'field': list(Window.size),
            'elapsed': round(game.elapsed, 2),
            'ships': [[ship.slot, round(ship.x, 1), round(ship.y, 1),
                       round(ship.angle % 360, 1),
                       round(min(ship.thrust_level, 1), 3) if ship.thrust
                       else 0, max(int(ship.lives), 0), int(ship.points)]
                      for ship in game.spaceships],
            'ast': [[a.net_id, round(a.x, 1), round(a.y, 1),
                     round(a.angle % 360, 1)] for a in game.asteroids],
            'shots': [[s.net_id, round(s.x, 1), round(s.y, 1)]
                      for s in game.shots],
            'boom': [[round(x, 1), round(y, 1)] for x, y in booms],
        })

    def paused(self, paused):
        self.send({'t': 'pause' if paused else 'resume'})

    def game_over(self, results):
        self.results = list(results)
        self.game_id = uuid.uuid4().hex[:12]
        # only the machine of the top player saves the score (none when
        # that player's machine has left)
        best = top_result(self.results).machine
        here = best == 0 or best in self.session.clients
        self.saver = best if best is not None and here else -1
        self.set_phase('results')
        self.send(self.over_message())
        self.send_lobby()

    def play_again(self):
        """Again with the players still here, or back to the join screen
        when fewer than two are left."""
        lobby = self.lobby
        for slot in range(MAX_PLAYERS):
            lobby.ready[slot] = lobby.out[slot] = False
        if len(lobby.joined) >= 2:
            self.start_game()
        else:
            self.set_phase('lobby')
            self.game.show_host_join()
            self.send_lobby()

    def save_score(self, name):
        """The host's own "Save to leaderboard"."""
        board = self.game.leaderboard
        board.last_name = clean_name(name)
        board.save()
        self.save(self.game_id, name, self.name, 0)

    def save(self, game_id, name, by, peer):
        """Store the game's top player once, on every device; only the
        machine of that player (`peer`, 0 the host) may."""
        if (game_id != self.game_id or self.phase != 'results'
                or peer != self.saver):
            return
        if game_id not in self.saved:
            best = top_result(self.results)
            entry = Leaderboard.new_entry(best.points, best.survived, name)
            self.game.leaderboard.merge([entry])
            self.saved[game_id] = by
            self.send(self.lb_message())
            self.game.score_saved(game_id, by)
        self.send({'t': 'saved', 'game': game_id, 'by': self.saved[game_id]})

    def close(self):
        if not self.closed:
            self.closed = True
            self.event.cancel()
            self.session.close('host-ended')
            self.announcer.close()


class NetClient:
    """Playing in a game hosted by another machine: the session with the
    host and the host's lobby, seen from here (this machine's devices are
    plain devices, the others ('net', peer, device))."""
    role = 'client'

    def __init__(self, game, session, label):
        self.game = game
        self.session = session
        self.host_name = label
        self.peer = None
        self.phase = None
        self.colors = ShipColors()   # the host's colours, never saved here
        self.lobby = Lobby(self.colors)
        self.flash = [False] * MAX_PLAYERS
        self.game_id = None
        self.snap = None             # the newest snapshot not yet shown
        self.closed = False
        self.event = Clock.schedule_interval(self.poll, NET_POLL)

    @property
    def info(self):
        return 'Game hosted by {}'.format(self.host_name)

    def send(self, message):
        if not self.closed:
            self.session.send(message)

    def poll(self, dt=0):
        if self.closed:
            return
        for event in self.session.poll():
            if event[0] == 'welcome':
                self._welcome(event[1])
            elif event[0] == 'fail':
                self._stop()
                self.game.net_failed(event[1])
                return
            elif event[0] == 'close':
                self._lost('Connection to the host lost')
                return
            else:
                self._message(event[1])
            if self.closed:
                return
        if self.snap is not None and self.phase == 'game':
            snap, self.snap = self.snap, None
            self.game.client_snap(snap)

    def _welcome(self, message):
        self.peer = message['peer']
        self.host_name = message['name']
        self.phase = message['phase']
        self.send({'t': 'lb', 'entries': self.game.leaderboard.entries})
        if self.phase == 'game':
            self.game.net_waiting('Joining the game…')
        else:
            self.game.show_client_join()

    def _message(self, message):
        kind = message['t']
        game = self.game
        if kind == 'lobby':
            self._lobby(message)
        elif kind == 'start':
            self.phase = 'game'
            self.lobby.in_game = True
            self.snap = None
            game.client_start(message)
        elif kind == 'snap':
            self.snap = message
        elif kind == 'denied':
            game.net_denied(message['device'], message['reason'])
        elif kind == 'pause':
            if self.phase == 'game':
                game.pause(from_net=True)
        elif kind == 'resume':
            if self.phase == 'game':
                game.net_resume()
        elif kind == 'over':
            self.phase = 'results'
            self.lobby.in_game = False
            self.game_id = message['game']
            game.client_over(message)
        elif kind == 'lb':
            game.leaderboard.merge(message['entries'])
        elif kind == 'saved':
            if message['game'] == self.game_id:
                game.score_saved(message['game'], message['by'])
        elif kind == 'bye':
            self._lost('The host ended the game')

    def _lobby(self, message):
        lobby = self.lobby
        lobby.names = {}
        for slot, entry in enumerate(message['slots']):
            if entry is None:
                lobby.slots[slot] = None
                lobby.ready[slot] = lobby.out[slot] = False
                continue
            peer, device, state, name = entry
            lobby.names[peer] = name
            lobby.slots[slot] = (device if peer == self.peer
                                 else ('net', peer, device))
            lobby.ready[slot] = state == 'ready'
            lobby.out[slot] = state == 'out'
        self.colors.colors = [c if c in CABIN_COLORS else 'blue'
                              for c in message['colors']]
        self.flash = list(message['flash'])
        self.host_name = message['name']
        before, self.phase = self.phase, message['phase']
        lobby.in_game = self.phase == 'game'
        self.game.client_lobby(before)

    # ---- what this machine's players do -------------------------------------

    def act(self, device, action):
        self.send({'t': 'act', 'device': device, 'action': action})

    def touch(self, side):
        self.send({'t': 'touch', 'side': side})

    def panel(self, slot, button):
        self.send({'t': 'panel', 'slot': slot, 'button': button})

    def paused(self, paused):
        self.send({'t': 'pause' if paused else 'resume'})

    def save_score(self, name):
        board = self.game.leaderboard
        board.last_name = clean_name(name)
        board.save()
        self.send({'t': 'save', 'game': self.game_id or '',
                   'name': clean_name(name)})

    def _stop(self):
        self.closed = True
        self.event.cancel()

    def _lost(self, message):
        self.close()
        self.game.net_lost(message)

    def close(self):
        if not self.closed:
            self._stop()
            self.session.close('menu')


class Nebula(Widget):
    """The nebula picture stretched over the whole widget."""
    SOURCE = 'images/nebula_blue.png'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(source=self.SOURCE)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        self._rect.pos, self._rect.size = self.pos, self.size


class AnimatedBackground(Widget):
    """The debris picture at its own size and proportions (640 x 480 px),
    repeated over the widget from its bottom-left corner and scrolling
    left: never stretched, whatever the shape of the screen. `shift` is how
    many pixels the pattern has moved left."""
    SOURCE = 'images/debris.png'
    DURATION = 15   # seconds for one trip over the picture
    shift = NumericProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.texture = Image(self.SOURCE).texture
        self.texture.wrap = 'repeat'
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self.texture)
        self.bind(pos=self._redraw, size=self._redraw, shift=self._redraw)
        self._redraw()
        self.animate()

    def _redraw(self, *args):
        """Texture coordinates beyond the picture repeat it, in whichever
        direction the texture runs (image textures are stored upside down).
        The coordinates belong to this rectangle, so debris layers sharing
        the cached texture do not move each other."""
        width, height = self.texture.size
        u0, v0, _, _, u1, v1, _, _ = self.texture.tex_coords
        du, dv = (u1 - u0) / width, (v1 - v0) / height
        left = u0 + du * self.shift
        right = left + du * self.width
        top = v0 + dv * self.height
        self._rect.pos, self._rect.size = self.pos, self.size
        self._rect.tex_coords = (left, v0, right, v0, right, top, left, top)

    def animate(self, *args):
        self.shift = 0
        self._scroll(self.DURATION)

    def _scroll(self, duration):
        self.animation = Animation(
            shift=self.texture.width, t='linear', duration=duration)
        self.animation.bind(on_complete=self.animate)
        self.animation.start(self)

    def pause(self):
        self.animation.cancel(self)

    def resume(self):
        """Go on from where the picture stopped."""
        self._scroll(self.DURATION * (1 - self.shift / self.texture.width))


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
        self.pad_bindings = GamepadBindings(
            os.path.join(app.user_data_dir, 'gamepad_buttons.json')
            if app else None)
        self.pads = make_pad_identity()
        self._pad_ids = {}           # stick id -> identity of a known pad
        self._unknown_sticks = set()  # sticks that could not be identified
        self._button_down = {}       # (stick, button) -> action at press time
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
        self.joined_at = {}  # slot -> elapsed time when the player joined
        self._layout = (False, False)   # see _seat_layout
        # network game: NetHost or NetClient while hosting or joined
        self.net = None
        self.in_net_game = False
        self.mirror_ships, self.mirror_asteroids, self.mirror_shots = {}, {}, {}
        self.network_settings = NetworkSettings(
            os.path.join(app.user_data_dir, 'network.json') if app else None)
        self._default_name = None
        self.multicast = MulticastLock()
        # Android pans the picture so the text box being typed in (nickname,
        # address, device name) stays above the on-screen keyboard
        Window.softinput_mode = 'below_target'
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
        colors = list(colors or self.ship_colors.colors)
        self.last_config = (
            players, list(colors), list(slots) if slots is not None else None)
        entries = ([(0, None)] if slots is None
                   else [(i, d) for i, d in enumerate(slots) if d])
        self.num_players = len(entries)
        # a host plays on the lobby's own list: players join and leave
        # during the game
        self._begin_round(
            self.net.lobby.slots if self._hosting
            else list(slots) if slots is not None else None,
            [device for _, device in entries],
            len(slots) if slots is not None else 1, net=self._hosting)
        for slot, device in entries:
            self.add_player(slot, device, colors[slot])
            self.joined_at[slot] = 0.0
        self.spaceship_status = self.statuses[0]
        self.spaceship_controls = next(c for c in self.controls if c)
        self._inputs_down.clear()
        self.update_prompt()

    def _begin_round(self, slots, devices, controls, elapsed=0.0,
                     net=False):
        """What every game starts from, local, hosted or joined: `slots`
        (None in single player), the `devices` that play on it now, room
        for `controls` players and the game time so far."""
        self.slots = slots
        if net:
            self.in_net_game = True
        self.elapsed = elapsed
        self.results = []
        self.statuses = []
        self.controls = [None] * controls
        self.joined_at = {}
        self._layout = self._seat_layout(devices)
        self._band_axis = None

    @staticmethod
    def _seat_layout(devices):
        """(edges, flank): a touch player of this screen at the top or
        bottom edge means a seat at every edge, and the keyboard, gamepad
        and remote players' lives and points in the corners. A two-seat
        screen (a phone) has touch seats at the top and bottom only when it
        was held upright: their controls need those whole edges, so the
        other players' lives and points go beside the middle of the free
        left and right edges instead (flank), whichever way the phone is
        held now."""
        seats = [touch_seat(d) for d in devices]
        edges = any(seat in ('top', 'bottom') for seat in seats)
        sides = any(seat in ('left', 'right') for seat in seats)
        flank = edges and not sides and not four_seat_screen()
        return edges, flank

    def add_player(self, slot, device, color, ship=None, place=False):
        """The ship, lives and points block and controls of one player.
        A network client brings the mirror `ship` it draws and gets controls
        only for its own players; `place` keeps a ship that joins a running
        game away from the asteroids."""
        edges, flank = self._layout
        seat = touch_seat(device)
        if seat in ('top', 'bottom') and not edges:
            edges = True        # joined during the game at a new edge
        if ship is None:
            ship = self.add_spaceship(
                slot, 1 if self.slots is None else MAX_PLAYERS, color)
            if place:
                self._place_safely(ship)
        ship.slot = slot
        if self.slots is None:
            side = ''
        else:
            side = seat or ('flank' if flank else 'corner' if edges
                            else 'row')
        status = SpaceshipStatus(spaceship=ship, side=side, column=slot,
                                 color=(*cabin_rgb(color), 1))
        # a client's field keeps clear of the block wherever it goes
        label = status.ids.get('text_label')
        if label is not None:
            label.bind(center=self._refit_field,
                       texture_size=self._refit_field)
        status.bind(pause_spot=self._refit_field)
        self.add_widget(status)
        self.statuses.append(status)
        controls = None
        if not self._joined_client or not is_remote(device):
            touch = ('auto' if self.slots is None
                     else 'on' if seat else 'off')
            target = (RemoteShip(slot, self.net) if self._joined_client
                      else ship)
            controls = ControlsManager(
                spaceship=target, side=seat, touch=touch, edges=edges)
            controls.touch_buttons.set_scale(self.touch_settings.scale)
            if seat or self.slots is None:
                status.follow(controls.touch_buttons)
            self.add_widget(controls)
        while len(self.controls) <= slot:
            self.controls.append(None)
        self.controls[slot] = controls
        self._share_seats()
        self._show_touch_controls()
        return ship

    def _drop_player(self, slot, out):
        """The same for a local, host or client game: the controls of the
        player in `slot` go (the stick is let go). A player `out` of lives
        keeps the lives and points, without the Pause button, and the seat;
        a player who left loses the block and frees the seat."""
        controls = self.controls[slot] if slot < len(self.controls) else None
        if controls is not None:
            controls.show_touch_buttons(False)
            self.remove_widget(controls)
            self.controls[slot] = None
        for status in [st for st in self.statuses if st.column == slot]:
            if out:
                status.show_menu = False
            else:
                self.remove_widget(status)
                self.statuses.remove(status)
        self._share_seats()

    def _hud_boxes(self):
        """Screen boxes of this device's touch controls, lives and points
        and Pause buttons, which a client keeps outside the field."""
        boxes = []
        for status in self.statuses:
            boxes.extend(status.screen_boxes())
        for controls in self.controls:
            if controls is not None and controls.touch_buttons.active:
                for pad in (controls.touch_buttons.stick,
                            controls.touch_buttons.fire):
                    x, y = pad.to_window(*pad.pos)
                    boxes.append((x, y, x + pad.width, y + pad.height))
        return boxes

    def _share_seats(self):
        """Tell every touch player's controls which edges and corners the
        others use, so they reach into the free corners. A seat is taken
        while its lives and points are shown, also after the last life.
        A client's field then makes room for them again."""
        self._place_hud()
        self._refit_field()

    def _refit_field(self, *args):
        view = getattr(self, 'field_view', None)
        if view is not None:
            view.refit()

    def _field_bands(self, axis):
        """A client's field leaves its room beside it along the x or y
        `axis` (FieldView): the lives, points and controls go there."""
        self._band_axis = axis
        self._place_hud()

    def _place_hud(self):
        """Where the lives and points and the touch controls go. On a
        client with at most one touch player, beside the field: when the
        room is at the two ends of the player's edge (the bottom without a
        touch player), the controls go into its corners with the lives and
        points beside the joystick and Pause beside FIRE; either way the
        other players' blocks go to the top-left corner, or the corner
        farthest from the touch controls (_band_spots). Otherwise the blocks
        keep their places of a local game (row, corners, flank)."""
        axis = getattr(self, '_band_axis', None)
        if getattr(self, 'field_view', None) is None:
            axis = None
        own = [s for s in self.statuses if s.side in SEAT_ANGLES]
        banded = axis is not None and len(own) <= 1
        seat = own[0].side if own else 'bottom'
        ends = banded and (seat in ('top', 'bottom')) == (axis == 'x')
        others = sorted((s for s in self.statuses
                         if s.side not in SEAT_ANGLES),
                        key=lambda s: s.column)
        for status in own:
            status.ends = ends
        for controls in self.controls:
            if controls is not None and controls.side:
                controls.touch_buttons.ends = ends
        spots = (self._band_spots(seat, axis, len(others)) if banded
                 else [[]] * len(others))
        for status, spot in zip(others, spots):
            status.spot = spot
        seats = [s.side for s in own]
        kept = [s for s in others if not s.spot]
        corners = [s.column for s in kept if s.side == 'corner']
        rows = [s.column for s in kept if s.side == 'row']
        flank = any(s.side == 'flank' for s in kept)
        for controls in self.controls:
            if controls is not None and controls.side:
                buttons = controls.touch_buttons
                buttons.seats = seats
                buttons.corners = corners
                buttons.flank = flank
                buttons.rows = rows

    BAND_CELL = (130, 50)   # dp: room of one block beside a client's field

    def _band_spots(self, seat, axis, count):
        """Corners for `count` blocks beside a client's field, one after the
        other: from the top-left corner, or when the touch player's controls
        are there (a seat at the top or left edge) from the corner farthest
        from them, stacked into the room beside the field (down it when the
        room is along `axis` x, else across it), or the other way when that
        would reach the touch controls."""
        w, h = Window.size
        m = dp(MARGIN_DP) / 2
        x, y, dx, dy = {'top': (m, m, 1, 1),
                        'left': (w - m, h - m, -1, -1)}.get(
                            seat, (m, h - m, 1, -1))
        cell_w, cell_h = (dp(v) for v in self.BAND_CELL)

        def stack(down):
            return [[x, y + dy * k * cell_h, dx, dy] if down
                    else [x + dx * k * cell_w, y, dx, dy]
                    for k in range(count)]

        taken = []
        for status in self.statuses:
            if status.side in SEAT_ANGLES:
                taken.extend(status.screen_boxes())
        for controls in self.controls:
            if controls is not None and controls.side:
                for pad in (controls.touch_buttons.stick,
                            controls.touch_buttons.fire):
                    px, py = pad.to_window(*pad.pos)
                    taken.append((px, py, px + pad.width, py + pad.height))

        def clear(spots):
            for sx, sy, sdx, sdy in spots:
                box = (min(sx, sx + sdx * cell_w), min(sy, sy + sdy * cell_h),
                       max(sx, sx + sdx * cell_w), max(sy, sy + sdy * cell_h))
                if any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3]
                       and b[1] < box[3] for b in taken):
                    return False
            return True
        spots = stack(axis == 'x')
        if not clear(spots):
            other = stack(axis != 'x')
            if clear(other):
                spots = other
        return spots

    SAFE_DISTANCE = 200   # px from a late ship to every asteroid

    def _place_safely(self, ship):
        """Move a ship that joins a running game from its start position to
        the nearest point (on rings around it) far enough from every
        asteroid, if there is one on the field."""
        start = Vector(*ship.pos)
        width, height = Window.size
        step = 50
        for radius in range(0, int(max(width, height)) + step, step):
            for angle in (range(0, 360, 45) if radius else (0,)):
                point = start + Vector(radius, 0).rotate(angle)
                if not (0 <= point.x <= width and 0 <= point.y <= height):
                    continue
                if all(point.distance(a.pos) >= self.SAFE_DISTANCE
                       for a in self.asteroids):
                    ship.pos = tuple(point)
                    return

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
        for slot, controls in enumerate(self.controls):
            if controls is not None:
                visible = (self.touch_ui if controls.touch == 'auto'
                           else controls.touch == 'on')
                controls.show_touch_buttons(visible)
                # touch play has no Back key: the player's status block
                # offers the pause screen, which leads back to the menu
                for status in self.statuses:
                    if status.column == slot:
                        status.show_menu = visible
        view = getattr(self, 'field_view', None)
        if view is not None:
            view.refit()

    def _on_window_touch(self, window, touch):
        self._set_touch_ui(True)
        if not self.has_touch:
            self.has_touch = True
            if self.select_active and isinstance(self.select, JoinScreen):
                self.select.allow_touch()
            self.update_prompt()

    def _input(self, source, action, pressed, device=None):
        """Send a press/release of `action` coming from `source` (a hashable
        id of the physical key/button/axis) of `device` (('keys', set) or
        ('pad', stick); None for keys of no set) to the menu or the game."""
        in_game = self._in_game
        controls = None
        if in_game and action != 'back':
            controls = self._controls_of(device)
            if controls is None:
                # a device that did not join this game; in a network game
                # FIRE takes a free slot
                if (pressed and action == 'fire' and self.in_net_game
                        and device is not None):
                    self.net_join(device)
                return

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
        elif self.network_active:
            if not pressed:
                return
            screen = self.network_screen
            if action == 'up':
                screen.move(-1)
            elif action == 'down':
                screen.move(1)
            elif action == 'fire':
                screen.activate()
            elif action == 'back':
                self.close_network()
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

    @property
    def _in_game(self):
        """A game is running and neither a screen nor a popup is shown."""
        return not (self.settings_active or self.menu_active
                    or self.select_active or self.results_active
                    or self.leaderboard_active or self.name_active
                    or self.network_active or self.address_active
                    or self.paused or hasattr(self, 'confirm_screen'))

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

    @property
    def network_active(self):
        return (hasattr(self, 'network_screen')
                and self.network_screen in self.children)

    @property
    def address_active(self):
        return (hasattr(self, 'address_screen')
                and self.address_screen in self.children)

    @property
    def _hosting(self):
        return self.net is not None and self.net.role == 'host'

    @property
    def _joined_client(self):
        return self.net is not None and self.net.role == 'client'

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

    def show_gamepad_settings(self):
        self._show_settings_page(GamepadSettings(
            bindings=self.pad_bindings, pad_list=self._pad_list,
            axis_rest=self.pads.axes))

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
                                     touch=self.has_touch,
                                     seats=touch_seats(),
                                     **self._name_args())
        self.add_widget(self.select)

    def start_selected(self):
        self.ship_colors.save()
        self.game_start(1)

    def start_joined(self):
        if self._hosting:
            self.net.start_game()
            return
        self.ship_colors.save()
        self.game_start(slots=self.select.slots)

    def close_ship_select(self):
        self.remember_name()
        if self.net is not None:      # leaves (or ends) the network game
            self.remove_widget(self.select)
            del self.select
            self.show_menu()
            return
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
        if self.name_active or self.address_active:
            # typing a nickname or address: only Escape (cancel) and Enter
            # (in the field) mean something, the game keys must not move
            # the menu
            self._back_from_menu = False
            if key == 27:
                (self.name_screen if self.name_active
                 else self.address_screen).cancel()
            return
        if self.select_active and getattr(self.select, 'typing', False):
            # typing the device name: the keys must not join players;
            # Escape (like Enter) is done with it
            self._back_from_menu = False
            if key == 27:
                self.select.name_field.focus = False
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

    def _pad_identity(self, stick):
        """Identity of the gamepad behind a stick id, None if SDL can not
        say (such a pad uses the default layout)."""
        identity = self._pad_ids.get(stick)
        if identity is None:
            found = self.pads.identity(stick)
            if found is None:
                self._unknown_sticks.add(stick)
                return None
            identity = self._pad_ids[stick] = found[0]
            self._unknown_sticks.discard(stick)
        return identity

    def _pad_list(self):
        """[(identity, name)] of the gamepads the settings page can edit."""
        pads = list(self.pads.connected())
        if self._unknown_sticks:
            pads.append((None, 'Unidentified gamepad'))
        return pads

    def _waiting_pad_page(self):
        """The gamepad settings page while it waits for a button or trigger."""
        if (self.settings_active and self.settings.waiting
                and isinstance(self.settings, GamepadSettings)):
            return self.settings

    def _on_joy_axis(self, window, stick, axis, value):
        value = value / 32767
        identity = self._pad_identity(stick)
        page = self._waiting_pad_page()
        if page is not None and page.handle_axis(identity, axis, value):
            return
        if axis == 0:
            self._axis(stick, axis, value, 'left', 'right')
        elif axis == 1:
            if self._in_game:
                self._stick_thrust(stick, value)
            else:
                self._axis(stick, axis, value, 'up', 'down')
        else:
            self._trigger(stick, identity, axis, value)

    def _stick_thrust(self, stick, value):
        """In the game the stick pushed up thrusts with power: the further
        up, the stronger (menus keep reading it as up and down)."""
        for action in ('up', 'down'):
            self._inputs_down.discard(('axis', stick, 1, action))
        controls = self._controls_of(('pad', stick))
        if controls is None:
            return
        level = stick_level(-value)
        if level != controls.analog.get('stick', 0.0):
            if level > 0:
                self._set_touch_ui(False)
            controls.set_thrust(level, 'stick')

    def _trigger(self, stick, identity, axis, value):
        """A trigger bound to thrust: power follows how far it is pulled."""
        trigger = self.pad_bindings.profile(identity)['trigger']
        if not trigger or trigger['axis'] != axis or not self._in_game:
            return
        controls = self._controls_of(('pad', stick))
        if controls is not None:
            level = trigger_level(trigger, value)
            if level != controls.analog.get('trigger', 0.0):
                self._set_touch_ui(False)
                controls.set_thrust(level)

    def _on_joy_hat(self, window, stick, hat, value):
        x, y = value
        self._axis(stick, ('hat', hat, 'x'), x, 'left', 'right')
        self._axis(stick, ('hat', hat, 'y'), -y, 'up', 'down')

    def _on_joy_button_down(self, window, stick, button):
        identity = self._pad_identity(stick)
        page = self._waiting_pad_page()
        if page is not None:
            page.handle_button(identity, button)
            return
        # the layout of a pad applies in the game only; screens and popups
        # keep the standard buttons, whatever it is
        action = (self.pad_bindings.action_for(identity, button)
                  if self._in_game else JOY_BUTTON_ACTIONS.get(button))
        if action:
            # a rebind while the button is held must not strand the action
            self._button_down[(stick, button)] = action
            self._joy_input(stick, ('button', stick, button), action, True)

    def _on_joy_button_up(self, window, stick, button):
        action = self._button_down.pop((stick, button), None)
        if action:
            self._joy_input(stick, ('button', stick, button), action, False)

    # ---- network game ------------------------------------------------------

    def default_device_name(self):
        """The model (Android) or host name, looked up once."""
        if self._default_name is None:
            self._default_name = device_name()
        return self._default_name

    def device_name(self):
        """How the other devices of a network game see this one."""
        return (self.network_settings.device_name
                or self.default_device_name())

    def _name_args(self):
        return {'name': self.network_settings.device_name,
                'default_name': self.default_device_name()}

    def remember_name(self):
        """Keep the device name typed on the join screen."""
        select = getattr(self, 'select', None)
        typed = getattr(select, 'typed_name', None)
        if typed is not None and typed != self.network_settings.device_name:
            self.network_settings.device_name = typed
            self.network_settings.save()

    def show_network(self, message=''):
        """Join a network game: a found one or one given by its address. Its
        Back returns to the join screen."""
        self.remember_name()
        if self.menu_active:
            self.remove_widget(self.menu)
        self.net_end()
        for name in ('select', 'results_screen'):
            if hasattr(self, name):
                self.remove_widget(getattr(self, name))
                delattr(self, name)
        self._drop_network_screen()
        self.multicast.acquire()
        try:
            browser = make_browser()
        except OSError as e:
            Logger.warning('SpacePilgrim: no game search: %s', e)
            browser = None
        self.network_screen = NetworkScreen(browser, message=message)
        self.add_widget(self.network_screen)

    def _drop_network_screen(self):
        if hasattr(self, 'network_screen'):
            self.network_screen.close()
            self.remove_widget(self.network_screen)
            del self.network_screen
        self.multicast.release()

    def close_network(self):
        """Back from joining a network game: the multiplayer join screen."""
        self.net_end()
        self._drop_network_screen()
        self.show_ship_select(2)

    def set_hosting(self, on):
        """The join screen's "Local network" toggle: open the game to the
        devices of the local network (the players already joined stay), or
        close it again (players of other machines leave)."""
        select = self.select
        if on and self.net is None:
            select.name_field.focus = False
            self.remember_name()
            name = self.device_name()
            session = None
            try:
                session = make_host_session(name)
                announcer = make_announcer(name, session.port)
            except OSError as e:
                if session is not None:
                    session.close()
                select.message.text = 'Could not open to the network: {}'.format(
                    e.strerror or e)
                return
            self.net = NetHost(self, session, announcer,
                               network.local_address(), lobby=select.lobby)
            select.net = self.net
            select.info.text = self.net.info
            select.on_change = self.net.send_lobby
        elif not on and self._hosting:
            lobby = self.net.lobby
            self.net_end()
            for slot in range(MAX_PLAYERS):
                if is_remote(lobby.slots[slot]):
                    lobby.leave(slot)
            lobby.names = {}
            select.net = None
            select.on_change = None
        select.refresh()

    def show_host_join(self):
        self._drop_screens()
        self.select = JoinScreen(
            self.ship_colors, self.bindings, touch=self.has_touch,
            seats=touch_seats(), lobby=self.net.lobby, net=self.net,
            **self._name_args())
        self.select.info.text = self.net.info
        self.select.on_change = self.net.send_lobby
        self.add_widget(self.select)
        self.net.send_lobby()

    def show_address(self):
        self.remove_widget(self.network_screen)
        self.address_screen = AddressScreen(
            self.network_settings.default_address())
        self.add_widget(self.address_screen)

    def address_done(self, text):
        """The typed address (None: Back) and back to the network screen."""
        self.remove_widget(self.address_screen)
        del self.address_screen
        self.add_widget(self.network_screen)
        if text is None:
            return
        text = text.strip()
        try:
            host, port = network.parse_address(text)
        except ValueError:
            self.network_screen.set_message(
                'Not an address: {}'.format(text[:40]))
            return
        self.network_settings.last_address = text
        self.network_settings.save()
        self.join_game(host, port, text)

    def join_game(self, host, port, label):
        """Connect to a host; the network screen says how it goes."""
        if self.net is not None:
            return
        try:
            session = make_client_session(host, port, self.device_name())
        except OSError:
            self.net_failed('unreachable')
            return
        self.net = NetClient(self, session, label)
        self.net_waiting('Connecting to {}…'.format(label))

    def net_waiting(self, text):
        if self.network_active:
            self.network_screen.set_message(text)

    NET_FAILURES = {
        'version': 'The game versions differ',
        'full': 'The game is full',
    }

    def net_failed(self, reason):
        """A connection could not be set up."""
        self.net = None
        text = self.NET_FAILURES.get(
            reason, 'Could not reach the host (same Wi-Fi? firewall?)')
        if self.network_active:
            self.network_screen.set_message(text)
        else:
            self._drop_screens()
            if self.menu_active:
                self.remove_widget(self.menu)
            self.show_network(text)

    def net_end(self):
        """Leave the network game, if any (the host ends it for everyone)."""
        net, self.net = self.net, None
        if net is not None:
            net.close()

    def net_lost(self, message):
        """The host ended the game or the connection to it closed."""
        self.net = None
        self.end_game()
        self.show_menu(message)

    def show_client_join(self):
        """The host's join screen, as seen from this machine."""
        self.end_game()
        self._drop_screens()
        if self.menu_active:
            self.remove_widget(self.menu)
        net = self.net
        self.select = JoinScreen(
            net.colors, self.bindings, touch=self.has_touch,
            seats=client_seats(), seats_for=client_seats, lobby=net.lobby,
            net=net)
        self.select.flashing = list(net.flash)
        self.add_widget(self.select)
        self._client_join_info()

    def _client_join_info(self):
        net = self.net
        self.select.info.text = net.info + (
            ' · waiting for the next game' if net.phase == 'results' else '')
        self.select.refresh()

    def client_lobby(self, before):
        """A client got the host's lobby."""
        net = self.net
        if self.select_active and isinstance(self.select, JoinScreen):
            self.select.flashing = list(net.flash)
            self._client_join_info()
        elif net.phase == 'lobby' and before != 'lobby' and not self.in_net_game:
            self.show_client_join()     # the host went back to its join screen
        if self.in_net_game:
            self._sync_mirror_players()
            self.update_prompt()

    # ---- joining and leaving a running network game --------------------------

    def net_join(self, device):
        """A device that has not joined pressed FIRE during a network game."""
        if self._joined_client:
            if device[0] == 'touch':
                self.net.touch(device[1])
            else:
                self.net.act(device, 'fire')
            return
        if not self._hosting or self.net.phase != 'game':
            return
        lobby = self.net.lobby
        if lobby.slot_of(device) is not None:
            return                         # already plays (or played)
        if self._machine_slots(device):
            # a machine with a player in this game brings no more: whoever
            # joined alone plays alone, and a lost ship stays lost
            self._deny(device, 'out')
            return
        slot = lobby.join(device)
        if slot is None:
            self._deny(device, 'full')
            return
        self.add_player(slot, device, lobby.ship_colors.colors[slot],
                        place=True)
        self.joined_at[slot] = self.elapsed
        self.num_players = len(self.spaceships)
        self.net.send_lobby()
        self.update_prompt()

    def _machine_of(self, slot):
        """The host: the machine of the player in `slot` (0 for the host's
        own devices, else the client's peer id); None outside a network
        game."""
        if not self._hosting or self.slots is None or slot >= len(self.slots):
            return None
        device = self.slots[slot]
        if device is None:
            return None
        return device[1] if is_remote(device) else 0

    def _machine_slots(self, device):
        """The slots of this game held by the machine of `device`."""
        peer = device[1] if is_remote(device) else None
        return [i for i, d in enumerate(self.net.lobby.slots)
                if d is not None and (d[1] == peer if is_remote(d)
                                      else peer is None)]

    def _deny(self, device, reason):
        if is_remote(device):
            self.net.session.send(device[1], {
                't': 'denied', 'device': device[2], 'reason': reason})
        else:
            self.net_denied(device, reason)

    def net_denied(self, device, reason):
        if reason == 'full' and getattr(self, 'prompt', None) is not None:
            self.prompt.full()
            self.update_prompt()

    def remove_player(self, slot):
        """The host: the machine of the player in `slot` left the game. The
        ship leaves the field (its result is kept) and the slot is free."""
        ship = next((s for s in self.spaceships
                     if getattr(s, 'slot', None) == slot), None)
        self._drop_player(slot, out=False)
        if ship is not None:
            self.results.append(PlayerResult(
                slot, ship.cabin, ship.points,
                self.elapsed - self.joined_at.get(slot, 0.0),
                self._machine_of(slot)))
            self.remove_spaceship(ship)
        self.net.lobby.leave(slot)
        self.joined_at.pop(slot, None)
        self.num_players = len(self.spaceships)
        if self.in_net_game and not self.spaceships:
            self.game_over()
        else:
            self.update_prompt()

    def net_control(self, peer, message):
        """The host: a client's player steers, thrusts or fires."""
        slot = message['slot']
        device = self.slots[slot] if self.in_net_game else None
        controls = self.controls[slot] if slot < len(self.controls) else None
        if (not is_remote(device) or device[1] != peer or controls is None
                or self.paused):
            return
        ship = controls.spaceship
        if message['t'] == 'fire':
            ship.shot()
            return
        level = message['thrust']
        if level > 0:
            ship.thrust_level = level
            if not ship.thrust:
                ship.thrust_on()
        elif ship.thrust:
            ship.thrust_off()
        turn = message['turn']
        if turn < 0:
            ship.turn_left()
        elif turn > 0:
            ship.turn_right()
        else:
            ship.stop_rotation()

    def update_prompt(self):
        """Show how to join while this machine has no player in the game."""
        prompt = getattr(self, 'prompt', None)
        if not self.in_net_game or self.net is None:
            return
        if prompt is None:
            seats = client_seats if self._joined_client else touch_seats
            self.prompt = prompt = JoinPrompt(
                seats(), lambda side: self.net_join(('touch', side)),
                seats_for=seats)
            self.add_widget(prompt)
        lobby = self.net.lobby
        # only a machine without a player in this game may still join
        mine = any(d and not is_remote(d) for d in lobby.slots)
        prompt.show(not mine, free=lobby.free, touch=self.has_touch,
                    taken={touch_seat(d) for d in lobby.slots})

    # ---- a client's game: the host's world, drawn here ----------------------

    def client_start(self, message):
        """The host started a game (or this client came during one)."""
        self.end_game()               # also closes the pause screen
        self._drop_screens()
        if self.menu_active:
            self.remove_widget(self.menu)
        slots = self.net.lobby.slots
        self._begin_round(slots, slots, MAX_PLAYERS, message['elapsed'],
                          net=True)
        self.field_view = FieldView(message['field'], hud=self._hud_boxes,
                                    bands=self._field_bands)
        self._screen_background(False)
        self.add_widget(self.field_view)
        self._inputs_down.clear()
        self.update_prompt()

    def _mirror_device(self, slot):
        return self.slots[slot] if self.slots is not None else None

    def _drop_mirror_ship(self, slot):
        """A ship left the host's field: lost (its block stays) or left."""
        ship = self.mirror_ships.pop(slot)
        out = self.net is not None and self.net.lobby.out[slot]
        if out:
            ship.lives = 0
        self._drop_player(slot, out)
        self.remove_spaceship(ship)

    def _sync_mirror_players(self):
        """Ships whose slot changed hands are somebody else's now."""
        for slot, ship in list(self.mirror_ships.items()):
            if ship.device != self._mirror_device(slot):
                self._drop_mirror_ship(slot)

    def client_snap(self, message):
        """Show the host's world as it is in a snapshot."""
        view = getattr(self, 'field_view', None)
        if view is None or not self.in_net_game:
            return
        view.set_field(message['field'])
        self.elapsed = message['elapsed']
        colors = self.net.colors.colors
        seen = set()
        for slot, x, y, angle, thrust, lives, points in message['ships']:
            device = self._mirror_device(slot)
            ship = self.mirror_ships.get(slot)
            if ship is not None and ship.device != device:
                self._drop_mirror_ship(slot)
                ship = None
            if ship is None:
                if device is None:
                    continue       # the lobby with this player is on its way
                ship = Spaceship(cabin=colors[slot])
                ship.device = device
                view.add_widget(ship)
                self.spaceships.append(ship)
                self.mirror_ships[slot] = ship
                self._drop_player(slot, out=False)   # a lost ship's block
                self.add_player(slot, device, colors[slot], ship=ship)
            seen.add(slot)
            ship.pos = (x, y)
            ship.angle = angle
            ship.lives = lives
            ship.points = points
            if thrust > 0:
                ship.thrust_level = thrust
            if (thrust > 0) != ship.thrust:
                if thrust > 0:
                    ship.thrust_on()
                else:
                    ship.thrust_off()
        for slot in [s for s in self.mirror_ships if s not in seen]:
            self._drop_mirror_ship(slot)
        self._mirror(self.mirror_asteroids, message['ast'], Asteroid,
                     lambda a, item: setattr(a, 'angle', item[3]))
        self._mirror(self.mirror_shots, message['shots'], Shot)
        for pos in message['boom']:
            self.add_explosion(pos, parent=view)
        self.update_prompt()

    def _mirror(self, widgets, items, kind, extra=None):
        """Create, move and remove the mirror widgets of asteroids or shots
        by the host's ids."""
        view = self.field_view
        seen = set()
        for item in items:
            ident = item[0]
            seen.add(ident)
            widget = widgets.get(ident)
            if widget is None:
                widget = widgets[ident] = kind()   # a new shot plays its sound
                view.add_widget(widget)
            widget.pos = (item[1], item[2])
            if extra is not None:
                extra(widget, item)
        for ident in [i for i in widgets if i not in seen]:
            view.remove_widget(widgets.pop(ident))

    def client_over(self, message):
        """The host's game is over: its results, here too."""
        results = [PlayerResult(*r) for r in message['results']]
        self.end_game()
        self._drop_screens()
        self.results_screen = ResultsScreen(
            results, network='client',
            can_save=message['saver'] == self.net.peer)
        self.add_widget(self.results_screen)

    def score_saved(self, game_id, by):
        """The network game's score is in every leaderboard now."""
        screen = getattr(self, 'results_screen', None)
        if screen is not None:
            screen.mark_saved(by)

    def game_stop(self):
        """Leave the game (or whatever is shown) for the main menu."""
        self.end_game()
        self.show_menu()

    def show_menu(self, message=''):
        self.net_end()
        self._drop_screens()
        if hasattr(self, 'menu'):
            self.remove_widget(self.menu)
        self.menu = Menu()
        if 'message' in self.menu.ids:     # declared in spacepilgrim.kv
            self.menu.ids.message.text = message
        self.add_widget(self.menu)

    def _drop_screens(self):
        """Remove the menus and screens shown over the field."""
        self._drop_network_screen()
        for name in ('results_screen', 'leaderboard_screen', 'name_screen',
                     'address_screen', 'select'):
            if hasattr(self, name):
                self.remove_widget(getattr(self, name))
                delattr(self, name)

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
        if self._hosting:
            self.net.game_over(results)
        self.results_screen = ResultsScreen(
            results, network=self.net.role if self.net else None,
            can_save=not self._hosting or self.net.saver == 0)
        self.add_widget(self.results_screen)

    def play_again(self):
        if self._hosting:
            self.net.play_again()
        elif self.net is None:
            self.game_start(*self.last_config)

    def expire_shot(self, shot):
        shot.expiry = Clock.schedule_interval(
            partial(self.remove_shot, shot), shot.lifetime)

    def background_widget(self):
        """The scrolling debris: a client's is in its field view."""
        view = getattr(self, 'field_view', None)
        if view is not None:
            return view.debris
        return next((c for c in self.children
                     if isinstance(c, AnimatedBackground)), None)

    def _screen_background(self, shown):
        """The full-screen nebula and debris: hidden while a client draws
        the host's field (which has its own), shown again after."""
        for child in self.children:
            if isinstance(child, (Nebula, AnimatedBackground)):
                if child.opacity != (1 if shown else 0):
                    child.opacity = 1 if shown else 0
                    if isinstance(child, AnimatedBackground):
                        (child.resume if shown else child.pause)()

    def pause(self, from_net=False):
        """Freeze the world and show the pause screen. In a network game
        every device pauses (`from_net`: the pause came from the network)."""
        if self.paused or not (self.spaceships or self.in_net_game):
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
                controls.analog.clear()
                controls._apply()
                controls.show_touch_buttons(False)
        for status in self.statuses:
            status.show_menu = False
        self._inputs_down.clear()
        self.pause_screen = PauseScreen()
        self.add_widget(self.pause_screen)
        if self.net is not None and not from_net:
            self.net.paused(True)

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

    def resume(self, from_net=False):
        """Leave the pause screen: play on from the frozen state."""
        if not self.paused:
            return
        self.remove_widget(self.pause_screen)
        del self.pause_screen
        self._unfreeze()
        self._show_touch_controls()
        if self.net is not None and not from_net:
            self.net.paused(False)

    def net_resume(self):
        """Another device continued the network game."""
        if self.paused:
            self._drop_confirm()
            self.resume(from_net=True)

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
        self.in_net_game = False
        for name in ('field_view', 'prompt'):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.detach()
                self.remove_widget(widget)
                delattr(self, name)
        self._screen_background(True)
        self.mirror_ships, self.mirror_asteroids, self.mirror_shots = {}, {}, {}

    def update(self, dt):
        if self.net is not None:
            self.net.poll()
            if self._joined_client or self.net is None:
                return    # a client draws what the host sends
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
        if self._hosting:
            self.net.after_frame()

    def lose_spaceship(self, spaceship):
        """A ship ran out of lives: it leaves the field, its controls stop.
        The game ends once no ship is left."""
        pos = spaceship.pos
        for player, controls in enumerate(self.controls):
            if controls is not None and controls.spaceship is spaceship:
                self._drop_player(player, out=True)
                self.results.append(PlayerResult(
                    player, spaceship.cabin, spaceship.points,
                    self.elapsed - self.joined_at.get(player, 0.0),
                    self._machine_of(player)))
                if self._hosting:     # out until the game ends
                    self.net.lobby.out[player] = True
                    self.net.send_lobby()
                    self.update_prompt()
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
        if spaceship.parent is not None:     # a client's is in the field view
            spaceship.parent.remove_widget(spaceship)

    def add_explosion(self, pos, parent=None):
        explosion = Explosion()
        explosion.pos = pos
        (parent or self).add_widget(explosion)
        self.explosions.append(explosion)
        if self._hosting:
            self.net.booms.append(tuple(pos))

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
        if self._joined_client:
            return     # the host's asteroids arrive in the snapshots
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
