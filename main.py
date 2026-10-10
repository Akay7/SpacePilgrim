__version__ = "0.2.1"

import colorsys
import json
import os
from functools import partial
from random import randint, choice

from kivy.utils import platform
from kivy.animation import Animation
from kivy.core.window import Window, Keyboard
from kivy.core.audio import SoundLoader
from kivy.app import App
from kivy.uix.widget import Widget
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
# Two players: player 1 on WASD + Space, player 2 on IJKL.
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
PLAYERS = len(DEFAULT_PLAYER_KEYS)
# Used when a migrated player 1 set already took a default of player 2.
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
    """Configurable keyboard bindings for two players (player -> action ->
    scancodes), optionally persisted as JSON."""

    VERSION = 3   # 2: one set for one player; 1: layout dependent key codes

    def __init__(self, path=None):
        self.path = path
        self.keys = self._defaults()
        self.load()

    @staticmethod
    def _defaults():
        return [{a: list(k) for a, k in player.items()}
                for player in DEFAULT_PLAYER_KEYS]

    def label(self, action, player=0):
        return ', '.join(
            scancode_name(sc) for sc in self.keys[player][action])

    def lookup(self, key, scancode=None):
        """(player, action) of a key press; (None, action) for keys that
        belong to no player (Escape), (None, None) for unbound keys. Arrow
        keys and Enter are reserved for the menus and steer player 1."""
        sc = scancode_for(key, scancode)
        for player, actions in enumerate(self.keys):
            for action, scancodes in actions.items():
                if sc in scancodes:
                    return player, action
        action = RESERVED_KEY_ACTIONS.get(key)
        if action in (None, 'back'):
            return None, action
        return 0, action

    def action_for(self, key, scancode=None):
        return self.lookup(key, scancode)[1]

    def rebind(self, action, key, scancode=None, player=0):
        """Bind the physical key to `action` of `player`. Returns None on
        success or a message saying why the key was refused (the old binding
        is kept)."""
        sc = scancode_for(key, scancode)
        if sc is None:
            return 'That key can not be used'
        if key in RESERVED_KEY_ACTIONS or sc in RESERVED_SCANCODES:
            return 'That key is reserved'
        for other_player, actions in enumerate(self.keys):
            for other, scancodes in actions.items():
                if (other_player, other) != (player, action) and sc in scancodes:
                    who = ('' if other_player == player
                           else 'Player {} '.format(other_player + 1))
                    return 'Already used for {}{}'.format(
                        who, ACTION_LABELS[other])
        self.keys[player][action] = [sc]
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
        """Version 2 file: its set is player 1, player 2 gets the defaults
        (or free keys where player 1 already uses a default)."""
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
        if not isinstance(players, list) or len(players) != PLAYERS:
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
# Left stick and D-pad steer.
JOY_BUTTON_ACTIONS = {
    0: 'fire', 2: 'fire',
    1: 'up', 3: 'up',
    6: 'back', 7: 'back',
}
JOY_AXIS_DEADZONE = 0.5


# Cabin colours: name -> hue in degrees. The sprite's canopy is blue (~210).
CABIN_COLORS = {
    'blue': 210, 'green': 120, 'red': 0, 'yellow': 55,
    'purple': 285, 'orange': 28,
}
CABIN_NAMES = list(CABIN_COLORS)
DEFAULT_CABINS = ['blue', 'green']
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
    """Cabin colour chosen by each player, optionally persisted as JSON."""

    def __init__(self, path=None):
        self.path = path
        self.colors = list(DEFAULT_CABINS)
        self.load()

    def cycle(self, player, step, players=PLAYERS):
        """Next (step 1) / previous colour for `player`, skipping colours
        another player of this game already has."""
        taken = {c for i, c in enumerate(self.colors[:players]) if i != player}
        index = CABIN_NAMES.index(self.colors[player])
        for _ in CABIN_NAMES:
            index = (index + step) % len(CABIN_NAMES)
            if CABIN_NAMES[index] not in taken:
                self.colors[player] = CABIN_NAMES[index]
                return

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        colors = data.get('colors') if isinstance(data, dict) else None
        if (isinstance(colors, list) and len(colors) == PLAYERS
                and all(c in CABIN_COLORS for c in colors)
                and len(set(colors)) == PLAYERS):
            self.colors = list(colors)

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'colors': self.colors}, f)
        except OSError:
            pass  # keep the in-memory choice for this session


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
        Clock.schedule_interval(
            partial(self.parent.remove_shot, shot), shot.lifetime)
        self.parent.add_widget(shot)


class SpaceshipStatus(Widget):
    spaceship = ObjectProperty()
    side = StringProperty('')           # two players: 'left' / 'right'
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
    player = NumericProperty(0)    # whose keys are listed and rebound

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
                value = self.bindings.label(action, self.player)
            ids['btn_' + action].text = '{}: {}'.format(label, value)
        ids['btn_player'].text = 'Keys of: Player {}'.format(self.player + 1)
        ids['message'].text = message

    def switch_player(self):
        self.waiting = ''
        self.player = (self.player + 1) % PLAYERS
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
                action, key, scancode, player=self.player)
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


MARGIN_CM = 1.0   # space between the touch controls and the screen edges


class Joystick(Widget):
    """Virtual stick: drag the knob up (thrust), left or right; positions in
    between press two actions at once. Down and the centre do nothing."""
    THRESHOLD = 0.35        # share of the radius needed to trigger an action
    knob = ListProperty([0.0, 0.0])   # offset from the centre, -1..1

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
        self.bind(pos=self._redraw, size=self._redraw, knob=self._redraw)
        self._redraw()

    @property
    def knob_size(self):
        return self.width * 0.42

    def _redraw(self, *args):
        cx, cy = self.center
        r = self.width / 2
        self._base.pos, self._base.size = self.pos, self.size
        self._ring.circle = (cx, cy, r - dp(1))
        k = r * 0.1
        for mark, (dx, dy) in zip(self._marks, ((0, 1), (-1, 0), (1, 0))):
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
        self.stick = Joystick(size=(cm(3.4), cm(3.4)), size_hint=(None, None))
        self.add_widget(self.stick)
        self.fire = FireButton(size=(cm(2), cm(2)), size_hint=(None, None))
        self.add_widget(self.fire)
        self.bind(size=self._layout)
        self._layout()

    def set_scale(self, scale):
        self.scale = scale
        self._layout()

    def _layout(self, *args):
        # keep a margin to the screen edges; controls are never larger than
        # the window height and half its width allow, so they do not overlap
        margin = cm(MARGIN_CM)
        if self.side:
            self._layout_side(margin)
            return
        limit = max(min(self.height - margin - cm(0.5),
                        self.width / 2 - margin * 1.5), cm(1))
        side = min(cm(3.4) * self.scale, limit)
        self.stick.size = (side, side)
        side = min(cm(2) * self.scale, limit)
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
        control sits just below the status text."""
        gap = cm(0.3)
        top_room = cm(2)
        stick, fire = cm(3.4) * self.scale, cm(2) * self.scale
        room_h = max(self.height - margin - top_room - gap, cm(2))
        shrink = min(1.0, room_h / (stick + fire))
        room_w = max(self.width / 2 - margin * 2, cm(1))
        stick = max(min(stick * shrink, room_w), cm(1))
        fire = max(min(fire * shrink, room_w), cm(1))
        self.stick.size = (stick, stick)
        self.fire.size = (fire, fire)
        top = self.height - top_room
        # the FIRE label reads upright from the player's seat
        self.fire.text_angle = -90 if self.side == 'left' else 90
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

    def go_back(self):
        if self.parent is not None:
            self.parent.close_ship_select()


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

    def animate(self, *args):
        self.uv_pos_x_px = 0
        self.animation = Animation(
            uv_pos_x_px=self.background.size[0], t='linear', duration=15
        )
        self.animation.bind(on_complete=self.animate)
        self.animation.start(self)


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
        self.bindings = KeyBindings(
            os.path.join(app.user_data_dir, 'keybindings.json')
            if app else None)
        self.ship_colors = ShipColors(
            os.path.join(app.user_data_dir, 'ship_colors.json')
            if app else None)
        self.num_players = 1
        self.controls = []   # one ControlsManager per player, None once out
        self._pads = {}      # gamepad (SDL stick id) -> player
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

    def game_start(self, players=1, colors=None):
        """Start a game of `players` ships with the given cabin colours
        (default: the saved choice)."""
        # reset game status
        [self.remove_shot(shot) for shot in self.shots]
        [self.remove_asteroid(asteroid) for asteroid in self.asteroids]

        # start schedule
        self.frame_schedule.cancel()
        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule.cancel()
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

        self.remove_widget(self.menu)
        if self.select_active:
            self.remove_widget(self.select)
            del self.select
        colors = list(colors or self.ship_colors.colors)[:players]
        self.num_players = players

        self.statuses = []
        self.controls = []
        for player in range(players):
            spaceship = self.add_spaceship(player, players, colors[player])
            status = SpaceshipStatus(
                spaceship=spaceship,
                side=('left', 'right')[player] if players > 1 else '',
                color=(*cabin_rgb(colors[player]), 1))
            self.add_widget(status)
            self.statuses.append(status)
            controls = ControlsManager(
                spaceship=spaceship,
                side=('left', 'right')[player] if players > 1 else '')
            controls.touch_buttons.set_scale(self.touch_settings.scale)
            controls.show_touch_buttons(self.touch_ui)
            self.add_widget(controls)
            self.controls.append(controls)
        self.spaceship_status = self.statuses[0]
        self.spaceship_controls = self.controls[0]
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
            for controls in self.controls:
                if controls is not None:
                    controls.show_touch_buttons(visible)

    def _on_window_touch(self, window, touch):
        self._set_touch_ui(True)

    def _input(self, source, action, pressed, player=None):
        """Send a press/release of `action` coming from `source` (a hashable
        id of the physical key/button/axis) of `player` (None: unknown or
        not tied to a player) to the menu or the game."""
        in_game = not (self.settings_active or self.menu_active
                       or self.select_active)
        controls = None
        if in_game and action != 'back':
            controls = self._controls_of(player)
            if controls is None:
                return    # a key of a second player in a one player game

        if pressed:
            if source in self._inputs_down:
                return  # key auto-repeat
            self._inputs_down.add(source)
            self._set_touch_ui(False)
        else:
            if source not in self._inputs_down:
                return
            self._inputs_down.discard(source)

        if self.settings_active:
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
            if not pressed:
                return
            if self.select.players == 1:
                player = 0
            if action == 'back':
                self.select.go_back()
            elif player is not None and player < self.select.players:
                if action == 'left':
                    self.select.change(player, -1)
                elif action == 'right':
                    self.select.change(player, 1)
                elif action == 'fire':
                    self.select.toggle_ready(player)
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
                App.get_running_app().stop()
            # On Android the Back key is left to Kivy: it pauses the app.
        elif action == 'back':
            if pressed:
                self.game_stop()
        elif controls is not None:
            if pressed:
                controls.press(action)
            else:
                controls.release(action)

    def _controls_of(self, player):
        if player is None or player >= len(self.controls):
            return None
        return self.controls[player]

    def _joy_player(self, stick, assign=True):
        """Player of a gamepad: with two players the first pad that sends
        input is player 1 and the second one player 2; with one player every
        pad drives the ship. None for any further pad."""
        if self.num_players == 1:
            return 0
        if stick not in self._pads and assign and len(self._pads) < PLAYERS:
            self._pads[stick] = len(self._pads)
        return self._pads.get(stick)

    @property
    def menu_active(self):
        return hasattr(self, 'menu') and self.menu in self.children

    @property
    def select_active(self):
        return hasattr(self, 'select') and self.select in self.children

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
        """Ship selection before a game of `players` ships."""
        self.num_players = players
        self._pads.clear()
        self.remove_widget(self.menu)
        self.select = ShipSelectScreen(self.ship_colors, players)
        self.add_widget(self.select)

    def start_selected(self):
        self.ship_colors.save()
        players = self.select.players
        self.game_start(players, self.ship_colors.colors[:players])

    def close_ship_select(self):
        self.remove_widget(self.select)
        del self.select
        self.add_widget(self.menu)
        self.menu.highlight()
        self._pads.clear()
        self.num_players = 1

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
        # Kivy dispatches on_keyboard right after this handler, by which time
        # Back may already have closed the game or settings; remember where
        # the key went down so _on_keyboard judges the screen it was meant for.
        self._back_from_menu = self.menu_active and not self.settings_active
        player, action = self.bindings.lookup(key, scancode)
        if action:
            self._input(('key', key), action, True, player)

    def _on_key_up(self, window, key, scancode=None, *args):
        player, action = self.bindings.lookup(key, scancode)
        if action:
            self._input(('key', key), action, False, player)
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

    def _joy_input(self, stick, source, action, pressed):
        player = self._joy_player(stick, assign=pressed)
        self._input(source, action, pressed, player)

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
        self.menu = Menu()
        self.add_widget(self.menu)

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
        self._pads.clear()
        self.num_players = 1

    def update(self, dt):
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
        if len(self.spaceships) == 1:
            self.game_stop()
        else:
            self.remove_spaceship(spaceship)
        self.add_explosion(pos)

    def add_spaceship(self, player=0, players=1, cabin='blue'):
        spaceship = Spaceship(cabin=cabin)
        spaceship.pos = Vector(*self.center) - Vector(*spaceship.size) / 2
        if players > 1:   # side by side, a ship length apart
            offset = spaceship.width * 1.5 * (1 if player else -1)
            spaceship.pos = Vector(offset, 0) + spaceship.pos
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

    def build(self):
        game = SpacePilgrimGame()
        game.game_stop()
        return game

    def on_pause(self):
        return True

if __name__ == '__main__':
    SpacePilgrimApp().run()
