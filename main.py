from functools import partial
from random import randint

from kivy.core.window import Window
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty, StringProperty,
    ListProperty,
)
from kivy.vector import Vector
from kivy.clock import Clock


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

    def update(self, dt):
        for i in [0, 1]:
            if self.pos[i] < 0:
                self.pos[i] = Window.size[i]
            elif self.pos[i] > Window.size[i]:
                self.pos[i] = 0

        self.pos = Vector(self.speed, 0).rotate(self.angle) + self.pos


class Spaceship(Widget):
    lives = NumericProperty(3)
    speed = NumericProperty(0)
    thrust = BooleanProperty(False)
    angle = NumericProperty(0)
    angle_rotation = NumericProperty(0)
    rotate = StringProperty()

    def update(self, dt):
        for i in [0, 1]:
            if self.pos[i] < 0:
                self.pos[i] = Window.size[i]
            elif self.pos[i] > Window.size[i]:
                self.pos[i] = 0

        self.angle += self.angle_rotation
        self.angle_rotation *= 0.9
        if self.thrust:
            self.speed = 3
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

    def shot(self):
        shot = Shot()
        shot.pos = (
            Vector(*self.size)/2 - Vector(*shot.size)/2 +
            self.pos + Vector(self.size[0] / 2, 0).rotate(self.angle)
        )
        shot.angle = self.angle
        return shot


class RiceRocksGame(Widget):
    spaceship = ObjectProperty(None)
    shots = ListProperty()
    asteroids = ListProperty()

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

        if keycode[1] == 'spacebar':
            shot = self.spaceship.shot()
            self.shots.append(shot)
            Clock.schedule_interval(
                partial(self.remove_shot, shot), shot.lifetime)
            self.add_widget(shot)

        if keycode[1] == 'escape':
            keyboard.release()

        return True

    def _on_keyboard_up(self, keyboard, keycode):
        if keycode[1] == "up":
            self.spaceship.move(False)

        if keycode[1] in ["right", "left"]:
            self.spaceship.turn()

    def update(self, dt):
        self.spaceship.update(dt)
        if self.shots:
            for shot in self.shots:
                shot.update(dt)

        if self.asteroids:
            for asteroid in self.asteroids:
                asteroid.update(dt)
                if asteroid.collide_widget(self.spaceship):
                    self.remove_asteroid(asteroid)
                    self.spaceship.lives -= 1

    def remove_asteroid(self, asteroid):
        self.remove_widget(asteroid)
        self.asteroids.remove(asteroid)

    def remove_shot(self, shot, *largs):
        self.remove_widget(shot)
        if shot in self.shots:
            self.shots.remove(shot)

    def generate_asteroid(self, dt):
        position = Vector(randint(0, Window.size[0]), randint(0, Window.size[1]))
        if position.distance(self.spaceship.pos) > 50 and len(self.asteroids) < 3:
            asteroid = Asteroid()
            asteroid.pos = position
            asteroid.angle = randint(0, 360)
            self.add_widget(asteroid)
            self.asteroids.append(asteroid)


class RiceRocksApp(App):
    def build(self):
        game = RiceRocksGame()
        Clock.schedule_interval(game.update, 1.0/60.0)
        Clock.schedule_interval(game.generate_asteroid, 2)
        return game

    def on_pause(self):
        return True

if __name__ == '__main__':
    RiceRocksApp().run()
