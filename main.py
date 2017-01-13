from functools import partial
from random import randint, choice

from kivy.utils import platform
from kivy.animation import Animation
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

from kivy.core.image import Image


class Explosion(Widget):
    frame = NumericProperty(0)
    texture = ObjectProperty()
    sound = SoundLoader.load('sounds/explosion.ogg')

    def __init__(self, *args, **kwargs):
        super(Explosion, self).__init__()
        self.sound.play()
        texture = Image('images/explosion.png').texture
        self.textures = [texture.get_region(i*128, 0, 128, 128) for i in range(23)]
        self.texture = self.textures[self.frame]

    def update(self, dt):
        self.texture = self.textures[self.frame]
        self.frame += 1
        self.property('texture').dispatch(self)


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


class Splash(Button):
    pass


class ScreenButtonsLayout(Widget):
    pass


class ControlsManager(Widget):
    spaceship = ObjectProperty()

    def __init__(self, **kwargs):
        super(ControlsManager, self).__init__(**kwargs)

        self._keyboard = Window.request_keyboard(
            self._keyboard_closed, self, 'text')
        if self._keyboard.widget:
            # If it exists, this widget is a VKeyboard object which you can use
            # to change the keyboard layout.
            pass
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self._keyboard.bind(on_key_up=self._on_keyboard_up)

        if platform == 'android':
            Window.release_all_keyboards()
            self.add_widget(ScreenButtonsLayout())

        self.mapping = {
            "up": {
                "down": self.spaceship.thrust_on,
                "up": self.spaceship.thrust_off
            },
            "right": {
                "down": self.spaceship.turn_right,
                "up": self.spaceship.stop_rotation
            },
            "left": {
                "down": self.spaceship.turn_left,
                "up": self.spaceship.stop_rotation
            },
            "spacebar": {
                "down": self.spaceship.shot
            }
        }

    def _keyboard_closed(self):
        print('My keyboard have been closed!')
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard.unbind(on_key_up=self._on_keyboard_up)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if self.mapping.get(keycode[1], {}).has_key('down'):
            self.mapping[keycode[1]]['down']()
        return True

    def _on_keyboard_up(self, keyboard, keycode):
        if self.mapping.get(keycode[1], {}).has_key('up'):
            self.mapping[keycode[1]]['up']()


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


class RiceRocksGame(Widget):
    shots = ListProperty()
    spaceships = ListProperty()
    asteroids = ListProperty()
    explosions = ListProperty()

    def __init__(self, **kwargs):
        super(RiceRocksGame, self).__init__(**kwargs)

        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

    def game_start(self):
        # reset game status
        [self.remove_shot(shot) for shot in self.shots]
        [self.remove_asteroid(asteroid) for asteroid in self.asteroids]

        # start schedule
        self.frame_schedule = Clock.schedule_interval(self.update, 1.0/60.0)
        self.asteroid_schedule = Clock.schedule_interval(self.generate_asteroid, 2)

        self.remove_widget(self.splash)
        spaceship = self.add_spaceship()

        self.spaceship_status = SpaceshipStatus(spaceship=spaceship)
        self.add_widget(self.spaceship_status)
        self.spaceship_controls = ControlsManager(spaceship=spaceship)
        self.add_widget(self.spaceship_controls)

    def game_stop(self):
        self.frame_schedule.cancel()
        self.asteroid_schedule.cancel()
        # create splash screen and centering it
        self.splash = Splash()
        self.add_widget(self.splash)

        if hasattr(self, 'spaceship_status'):
            self.remove_widget(self.spaceship_status)
        if hasattr(self, 'spaceship_controls'):
            self.remove_widget(self.spaceship_controls)
            Window.release_all_keyboards()

    def update(self, dt):
        [spaceship.update(dt) for spaceship in self.spaceships]
        [shot.update(dt) for shot in self.shots]
        [asteroid.update(dt) for asteroid in self.asteroids]
        [exp.update(dt) for exp in self.explosions]
        [self.remove_explosion(exp) for exp in self.explosions
         if exp.frame + 1 > len(exp.textures)]

        for asteroid in self.asteroids:
            for spaceship in self.spaceships:
                if asteroid.collide_widget(spaceship):
                    self.remove_asteroid(asteroid)
                    spaceship.lives -= 1
                    if spaceship.lives == 0:
                        self.game_stop()
                        self.remove_spaceship(spaceship)
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
        position = choice(positions.values())

        if (
            len(self.asteroids) < 3 and self.spaceships and
            min(map(lambda s: position.distance(s.pos), self.spaceships)) > 200
        ):
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
