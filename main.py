__version__ = "0.2.1"

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
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty, StringProperty,
    ListProperty,
)
from kivy.vector import Vector
from kivy.clock import Clock

from kivy.core.image import Image


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
DEFAULT_KEY_BINDINGS = {
    'up': [26],       # W
    'left': [4],      # A
    'right': [7],     # D
    'fire': [44],     # Space
}
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
    """Configurable keyboard bindings (action -> scancodes), optionally
    persisted as JSON."""

    VERSION = 2   # version 1 stored layout dependent key codes

    def __init__(self, path=None):
        self.path = path
        self.keys = {a: list(k) for a, k in DEFAULT_KEY_BINDINGS.items()}
        self.load()

    def label(self, action):
        return ', '.join(scancode_name(sc) for sc in self.keys[action])

    def action_for(self, key, scancode=None):
        sc = scancode_for(key, scancode)
        for action, scancodes in self.keys.items():
            if sc in scancodes:
                return action
        return RESERVED_KEY_ACTIONS.get(key)

    def rebind(self, action, key, scancode=None):
        """Bind the physical key to `action`. Returns None on success or a
        message saying why the key was refused (the old binding is kept)."""
        sc = scancode_for(key, scancode)
        if sc is None:
            return 'That key can not be used'
        if key in RESERVED_KEY_ACTIONS or sc in RESERVED_SCANCODES:
            return 'That key is reserved'
        for other, scancodes in self.keys.items():
            if other != action and sc in scancodes:
                return 'Already used for {}'.format(ACTION_LABELS[other])
        self.keys[action] = [sc]
        self.save()

    def reset(self):
        self.keys = {a: list(k) for a, k in DEFAULT_KEY_BINDINGS.items()}
        self.save()

    def _valid(self, data):
        if not isinstance(data, dict) or data.get('version') != self.VERSION:
            return False
        keys = data.get('keys')
        if not isinstance(keys, dict) or set(keys) != set(DEFAULT_KEY_BINDINGS):
            return False
        seen = set()
        for scancodes in keys.values():
            if not isinstance(scancodes, list) or not scancodes:
                return False
            for sc in scancodes:
                if (not isinstance(sc, int) or isinstance(sc, bool)
                        or sc in RESERVED_SCANCODES or sc in seen):
                    return False
                seen.add(sc)
        return True

    def load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if self._valid(data):
            self.keys = {a: list(data['keys'][a]) for a in DEFAULT_KEY_BINDINGS}

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump({'version': self.VERSION, 'keys': self.keys}, f)
        except OSError:
            pass  # keep the in-memory bindings for this session


# Default gamepad layout (SDL joystick button ids, Xbox-style pad):
# A / X fire, B / Y thrust, Back / Start return to the menu.
# Left stick and D-pad steer.
JOY_BUTTON_ACTIONS = {
    0: 'fire', 2: 'fire',
    1: 'up', 3: 'up',
    6: 'back', 7: 'back',
}
JOY_AXIS_DEADZONE = 0.5


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
    sound = SoundLoader.load('sounds/engine.ogg')

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


class ButtonColumn(BoxLayout):
    """Vertical list of buttons that can be navigated with the keyboard."""
    selected = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.highlight()

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
    """Controls settings: pick an action, then press the new key."""
    bindings = ObjectProperty()
    waiting = StringProperty('')   # action waiting for a key, '' if none

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
                value = self.bindings.label(action)
            ids['btn_' + action].text = '{}: {}'.format(label, value)
        ids['message'].text = message

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
            error = self.bindings.rebind(action, key, scancode)
            self.refresh(error or '')
        return True

    def reset(self):
        self.waiting = ''
        self.bindings.reset()
        self.refresh()


class ScreenButtonsLayout(Widget):
    pass


class ControlsManager(Widget):
    """Turns abstract actions (up, left, right, fire) into spaceship
    commands. Actions come from keyboard, gamepad and on-screen buttons."""
    spaceship = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.held = set()
        self.touch_buttons = ScreenButtonsLayout()
        self.add_widget(self.touch_buttons)

    def show_touch_buttons(self, visible):
        self.touch_buttons.opacity = 1 if visible else 0
        self.touch_buttons.disabled = not visible

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

        # On-screen buttons only for touch devices (not TV); they hide as soon
        # as a keyboard or gamepad is used and come back on the next touch.
        self.touchscreen = platform == 'android' and not is_android_tv()
        self.touch_ui = self.touchscreen
        self._inputs_down = set()
        app = App.get_running_app()
        self.bindings = KeyBindings(
            os.path.join(app.user_data_dir, 'keybindings.json')
            if app else None)
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

    def game_start(self):
        # reset game status
        [self.remove_shot(shot) for shot in self.shots]
        [self.remove_asteroid(asteroid) for asteroid in self.asteroids]

        # start schedule
        self.frame_schedule.cancel()
        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule.cancel()
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

        self.remove_widget(self.menu)
        spaceship = self.add_spaceship()

        self.spaceship_status = SpaceshipStatus(spaceship=spaceship)
        self.add_widget(self.spaceship_status)
        self.spaceship_controls = ControlsManager(spaceship=spaceship)
        self.spaceship_controls.show_touch_buttons(self.touch_ui)
        self.add_widget(self.spaceship_controls)
        self._inputs_down.clear()

    # ---- input routing -------------------------------------------------

    def _set_touch_ui(self, visible):
        visible = visible and self.touchscreen
        if visible != self.touch_ui:
            self.touch_ui = visible
            controls = getattr(self, 'spaceship_controls', None)
            if controls is not None:
                controls.show_touch_buttons(visible)

    def _on_window_touch(self, window, touch):
        self._set_touch_ui(True)

    def _input(self, source, action, pressed):
        """Send a press/release of `action` coming from `source` (a hashable
        id of the physical key/button/axis) to the menu or the game."""
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
            elif action == 'fire':
                self.settings.activate()
            elif action == 'back':
                self.close_settings()
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
        else:
            controls = getattr(self, 'spaceship_controls', None)
            if controls is None:
                return
            if pressed:
                controls.press(action)
            else:
                controls.release(action)

    @property
    def menu_active(self):
        return hasattr(self, 'menu') and self.menu in self.children

    @property
    def settings_active(self):
        return hasattr(self, 'settings') and self.settings in self.children

    def show_settings(self):
        self.remove_widget(self.menu)
        self.settings = SettingsScreen(bindings=self.bindings)
        self.add_widget(self.settings)

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
        action = self.bindings.action_for(key, scancode)
        if action:
            self._input(('key', key), action, True)

    def _on_key_up(self, window, key, scancode=None, *args):
        action = self.bindings.action_for(key, scancode)
        if action:
            self._input(('key', key), action, False)
        else:
            self._inputs_down.discard(('key', key))

    def _on_keyboard(self, window, key, *args):
        # Stop Kivy from quitting on Escape / pausing on Android Back while
        # playing: Back returns to the menu instead.
        if key == 27 and not (platform == 'android' and self.menu_active):
            return True

    def _axis(self, stick, axis, value, negative, positive):
        self._input(
            ('axis', stick, axis, negative), negative,
            value < -JOY_AXIS_DEADZONE)
        self._input(
            ('axis', stick, axis, positive), positive,
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
            self._input(('button', stick, button), action, True)

    def _on_joy_button_up(self, window, stick, button):
        action = JOY_BUTTON_ACTIONS.get(button)
        if action:
            self._input(('button', stick, button), action, False)

    def game_stop(self):
        self.menu = Menu()
        self.add_widget(self.menu)

        for spaceship in list(self.spaceships):
            self.remove_spaceship(spaceship)

        if hasattr(self, 'spaceship_status'):
            self.remove_widget(self.spaceship_status)
        if hasattr(self, 'spaceship_controls'):
            self.remove_widget(self.spaceship_controls)
            del self.spaceship_controls
        self._inputs_down.clear()

    def update(self, dt):
        [spaceship.update(dt) for spaceship in self.spaceships]
        [shot.update(dt) for shot in self.shots]
        [asteroid.update(dt) for asteroid in self.asteroids]

        for asteroid in self.asteroids:
            for spaceship in self.spaceships:
                if asteroid.collide_widget(spaceship):
                    self.remove_asteroid(asteroid)
                    spaceship.lives -= 1
                    self.add_explosion(asteroid.pos)
                    if spaceship.lives == 0:
                        self.game_stop()
                        self.add_explosion(spaceship.pos)
            for shot in self.shots:
                if asteroid.collide_widget(shot):
                    self.remove_asteroid(asteroid)
                    shot.spaceship.points += 1
                    self.remove_shot(shot)

                    self.add_explosion(asteroid.pos)

    def add_spaceship(self):
        spaceship = Spaceship()
        spaceship.pos = Vector(*self.center) - Vector(*spaceship.size) / 2
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
            len(self.asteroids) < 3 and self.spaceships and
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
