from kivy.core.window import Window
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, NumericProperty, BooleanProperty, StringProperty
from kivy.vector import Vector
from kivy.clock import Clock


class Spaceship(Widget):
    speed = NumericProperty(0)
    thrust = BooleanProperty(False)
    angle = NumericProperty(45)
    angle_rotation = NumericProperty(0)
    rotate = StringProperty()

    def update(self):
        self.angle += self.angle_rotation
        self.angle_rotation *= 0.9
        if self.thrust:
            self.speed = 2
        else:
            self.speed *= 0.9

        if self.rotate == "left":
            self.angle_rotation = 3
        elif self.rotate == "right":
            self.angle_rotation = -3
        else:
            self.angle_rotation *= 0.9
        self.pos = Vector(self.speed, 0).rotate(self.angle) + self.pos

    def move(self, thrust):
        self.thrust = thrust

    def turn(self, rotate=""):
        self.rotate = rotate


class RiceRocksGame(Widget):
    spaceship = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(RiceRocksGame, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(
            self._keyboard_closed, self, 'text')
        if self._keyboard.widget:
            # If it exists, this widget is a VKeyboard object which you can use
            # to change the keyboard layout.
            pass
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self._keyboard.bind(on_key_up=self._on_keyboard_up)

    def _keyboard_closed(self):
        print('My keyboard have been closed!')
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard.unbind(on_key_up=self._on_keyboard_up)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == "up":
            self.spaceship.move(True)

        if keycode[1] in ["right", "left"]:
            self.spaceship.turn(keycode[1])

        if keycode[1] == 'escape':
            keyboard.release()

        return True

    def _on_keyboard_up(self, keyboard, keycode):
        if keycode[1] == "up":
            self.spaceship.move(False)

        if keycode[1] in ["right", "left"]:
            self.spaceship.turn()

    def update(self, dt):
        self.spaceship.update()


class RiceRocksApp(App):
    def build(self):
        game = RiceRocksGame()
        Clock.schedule_interval(game.update, 1.0/60.0)
        return game

    def on_pause(self):
        return True

if __name__ == '__main__':
    RiceRocksApp().run()
