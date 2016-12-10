from functools import partial
from random import randint

from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty, StringProperty,
    ListProperty,
)
from kivy.vector import Vector
from kivy.clock import Clock


class Explosion(Widget):
    sound = SoundLoader.load('sounds/explosion.ogg')

    def __init__(self):
        super(Explosion, self).__init__()
        self.sound.play()


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

    def __init__(self):
        super(Shot, self).__init__()
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
        if not self.thrust and thrust:
            self.sound.play()
        elif self.thrust and not thrust:
            self.sound.stop()
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


class Splash(Button):
    pass


class RiceRocksGame(Widget):
    spaceship = ObjectProperty(None)
    splash = ObjectProperty(None)
    shots = ListProperty()
    asteroids = ListProperty()
    points = NumericProperty(0)

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

        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

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

    def game_start(self):
        # reset game status
        [self.remove_shot(shot) for shot in self.shots]
        [self.remove_asteroid(asteroid) for asteroid in self.asteroids]
        self.spaceship.lives = 3
        self.points = 0

        # start schedule
        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)
        self.remove_widget(self.splash)

    def game_stop(self):
        self.frame_schedule.cancel()
        self.asteroid_schedule.cancel()
        self.splash = Splash()
        self.add_widget(self.splash)

    def update(self, dt):
        self.spaceship.update(dt)
        [shot.update(dt) for shot in self.shots]
        [asteroid.update(dt) for asteroid in self.asteroids]

        for asteroid in self.asteroids:
            if asteroid.collide_widget(self.spaceship):
                self.remove_asteroid(asteroid)
                self.spaceship.lives -= 1
                if self.spaceship.lives == 0:
                    self.game_stop()
            for shot in self.shots:
                if asteroid.collide_widget(shot):
                    self.remove_asteroid(asteroid)
                    self.remove_shot(shot)
                    self.points += 1
                    Explosion()

    def remove_asteroid(self, asteroid):
        self.remove_widget(asteroid)
        if asteroid in self.asteroids:
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
        game.game_stop()
        return game

    def on_pause(self):
        return True

if __name__ == '__main__':
    RiceRocksApp().run()
