"""Fixed scenes of the game for the Google Play listing images.

Each scene builder takes the running `SpacePilgrimGame` and sets up one
screen with nothing moving and nothing random, so every run gives the same
composition. Positions are fractions of the window, so the same scene works
on every form factor. `touch` selects the phone/tablet variant (on-screen
controls, touch players) over the TV one (keyboard and gamepads).

Used by tools/play_listing.py (one process per form factor) and by
tests/test_play_listing.py (headless, to catch game API changes).
"""
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.vector import Vector

from main import (
    AnimatedBackground, Asteroid, Explosion, JoinScreen, Shot, Spaceship,
    ShipSelectScreen,
)

BACKGROUND_OFFSET = 0.35   # debris scroll position, as a share of its width
EXPLOSION_FRAME = 7        # a full fireball, not the first spark
COLORS = ['blue', 'orange', 'green', 'purple']


# ---- helpers -------------------------------------------------------------

def prepare(game):
    """Defaults instead of the developer's saved settings, and no saving."""
    game.touch_settings.path = None
    game.touch_settings.mode = 'auto'
    game.touch_settings.scale = 1.0
    game.ship_colors.path = None
    game.ship_colors.colors = list(COLORS)
    game.bindings.path = None
    game.bindings.reset()


def at(fx, fy):
    """Window position of the fractions (fx, fy)."""
    return (Window.width * fx, Window.height * fy)


def freeze(game):
    """Stop everything that moves or spawns: the game clocks, the scrolling
    debris and running animations."""
    game.frame_schedule.cancel()
    game.asteroid_schedule.cancel()
    for child in game.children:
        if isinstance(child, AnimatedBackground):
            Animation.cancel_all(child)
            if child.animation is not None:
                child.animation.unbind(on_complete=child.animate)
            child.uv_pos_x_px = child.background.size[0] * BACKGROUND_OFFSET


def clear_objects(game):
    for shot in list(game.shots):
        game.remove_shot(shot)
    for asteroid in list(game.asteroids):
        game.remove_asteroid(asteroid)
    for explosion in list(game.explosions):
        Animation.cancel_all(explosion)
        game.remove_explosion(explosion)


def reset(game):
    """Back to the main menu with an empty field."""
    if game.settings_active:
        game.close_settings()
    if game.select_active:
        game.close_ship_select()
    if not game.menu_active:
        game.game_stop()
    clear_objects(game)
    game.menu.selected = 0
    game.menu.highlight()
    freeze(game)


def asteroid(game, fx, fy, angle=0, size=None):
    rock = Asteroid(angle=angle)
    if size is not None:
        rock.size = (size, size)
    rock.center = at(fx, fy)
    game.add_widget(rock)
    game.asteroids.append(rock)
    return rock


def shot(game, ship, distance):
    """A shot of `ship`, `distance` ship lengths in front of its nose."""
    bullet = Shot(spaceship=ship, angle=ship.angle)
    ahead = Vector(ship.width * (0.5 + distance), 0).rotate(ship.angle)
    bullet.center = Vector(*ship.center) + ahead
    game.add_widget(bullet)
    game.shots.append(bullet)
    return bullet


def explosion(game, fx, fy):
    blast = Explosion()
    Animation.cancel_all(blast)
    blast.frame = EXPLOSION_FRAME
    blast.center = at(fx, fy)
    game.add_widget(blast)
    game.explosions.append(blast)
    return blast


def pose(ship, fx, fy, angle, thrust=True):
    ship.center = at(fx, fy)
    ship.angle = angle
    ship.thrust = thrust      # the flame sprite, without the engine sound


def start(game, touch, slots=None):
    """A game frozen right after it started. Single player when `slots` is
    None, else the joined slots (see JoinScreen)."""
    reset(game)
    if slots is None:
        game.game_start(1, colors=list(COLORS))
    else:
        game.game_start(slots=slots, colors=list(COLORS))
    freeze(game)
    # touch players always see their controls; the single player only on
    # a touch device (the Auto setting after a touch)
    game._set_touch_ui(touch, force=True)


# ---- scenes ----------------------------------------------------------------

def gameplay(game, touch):
    """Single player firing at an asteroid that just exploded."""
    start(game, touch)
    ship = game.spaceships[0]
    pose(ship, 0.40, 0.52, 18)
    ship.lives, ship.points = 2, 27
    for distance in (0.6, 1.6, 2.6):
        shot(game, ship, distance)
    explosion(game, 0.63, 0.66)
    asteroid(game, 0.72, 0.30, 140)
    asteroid(game, 0.20, 0.78, 300)
    asteroid(game, 0.86, 0.80, 210)


def multiplayer(game, touch):
    """Three players sharing the field."""
    if touch:   # two players at the sides of a tablet, one with a gamepad
        slots = [('touch', 'left'), ('touch', 'right'), ('pad', 0), None]
    else:       # on the sofa: keyboard and two gamepads
        slots = [('keys', 0), ('pad', 0), ('pad', 1), None]
    start(game, touch, slots)
    one, two, three = game.spaceships
    pose(one, 0.33, 0.62, -20)
    pose(two, 0.66, 0.40, 160)
    pose(three, 0.52, 0.22, 75, thrust=False)
    for ship, lives, points in ((one, 3, 14), (two, 2, 19), (three, 3, 8)):
        ship.lives, ship.points = lives, points
    shot(game, one, 0.7)
    shot(game, one, 1.7)
    shot(game, two, 1.0)
    explosion(game, 0.52, 0.72)
    asteroid(game, 0.80, 0.70, 200)
    asteroid(game, 0.24, 0.30, 30)


def join(game, touch):
    """The multiplayer join screen with three players, one ready."""
    reset(game)
    game.has_touch = touch      # a TV has no touchscreen: no touch strips
    game.show_ship_select(2)
    screen = game.select
    assert isinstance(screen, JoinScreen)
    screen.join(('keys', 0))
    if touch:
        screen.join_touch('right')
    else:
        screen.join(('pad', 1))
    screen.join(('pad', 0))
    screen.change(1, 1)
    screen.toggle_ready(0)


def ship_select(game, touch):
    """Single player picking a cabin colour."""
    reset(game)
    game.show_ship_select(1)
    screen = game.select
    assert isinstance(screen, ShipSelectScreen)
    screen.change(0, 1)     # orange: not the default blue
    screen.change(0, 1)


def menu(game, touch):
    reset(game)


SCENES = [
    ('gameplay', gameplay),
    ('multiplayer', multiplayer),
    ('join', join),
    ('ship-select', ship_select),
    ('menu', menu),
]


def banner(game, touch=False):
    """The Android TV listing banner: the title over the nebula with two
    asteroids and the ship flying right, like the launcher banner."""
    reset(game)
    game.remove_widget(game.menu)
    title = Label(
        text='Space\nPilgrim', bold=True, font_size=dp(64), halign='left',
        valign='middle', color=(1, 1, 1, 1), outline_width=dp(2),
        outline_color=(0, 0, 0, 1), size_hint=(None, None))
    title.size = at(0.48, 0.6)
    title.text_size = title.size
    title.pos = at(0.06, 0.2)
    game.add_widget(title)
    asteroid(game, 0.80, 0.76, size=Window.height * 0.3)
    asteroid(game, 0.14, 0.10, size=Window.height * 0.2)
    ship = Spaceship(cabin='blue')
    game.add_widget(ship)
    ship.size = (Window.height * 0.42, Window.height * 0.42)
    pose(ship, 0.74, 0.34, 0)
