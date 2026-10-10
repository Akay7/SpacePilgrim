import pytest

import main
from main import Asteroid, Shot, Spaceship, SpacePilgrimGame


def test_sounds_loaded_at_import():
    # SoundLoader.load returns None when decoding fails; every class that
    # plays a sound would then crash on first use.
    assert main.Explosion.sound is not None
    assert main.Shot.sound is not None
    assert main.Spaceship.sound is not None


def test_thrust_accelerates_and_drag_slows():
    ship = Spaceship()
    ship.thrust_on()
    ship.update(0)
    assert ship.speed == 3
    ship.thrust_off()
    ship.update(0)
    assert ship.speed == pytest.approx(3 * 0.98)


def test_rotation_controls():
    ship = Spaceship()
    ship.turn_left()
    ship.update(0)
    assert ship.angle == 3
    ship.turn_right()
    ship.update(0)
    assert ship.angle == 0
    ship.stop_rotation()
    assert ship.angle_rotation == 0


def test_asteroid_moves_along_angle():
    asteroid = Asteroid(speed=5, angle=90)
    asteroid.pos = (100, 100)
    asteroid.update(0)
    assert asteroid.pos[0] == pytest.approx(100)
    assert asteroid.pos[1] == pytest.approx(105)


def test_shot_moves_along_angle():
    shot = Shot(speed=4, angle=0)
    shot.pos = (10, 10)
    shot.update(0)
    assert shot.pos == [14, 10]


@pytest.fixture
def game():
    g = SpacePilgrimGame()
    g.game_stop()
    g.game_start()
    yield g
    g.frame_schedule.cancel()
    g.asteroid_schedule.cancel()


def test_game_start_adds_spaceship(game):
    assert len(game.spaceships) == 1
    assert game.menu not in game.children


def test_shoot_adds_shot(game):
    game.spaceships[0].shot()
    assert len(game.shots) == 1


def test_shot_destroys_asteroid_and_scores(game):
    ship = game.spaceships[0]
    ship.shot()
    shot = game.shots[0]
    # move the ship away so only the shot touches the asteroid
    ship.pos = (shot.x + 500, shot.y + 500)
    asteroid = Asteroid()
    asteroid.pos = shot.pos
    game.add_widget(asteroid)
    game.asteroids.append(asteroid)

    game.update(0)

    assert asteroid not in game.asteroids
    assert shot not in game.shots
    assert ship.points == 1
    assert len(game.explosions) == 1


def test_asteroid_hit_costs_life_then_game_over(game):
    ship = game.spaceships[0]
    for expected in (2, 1, 0):
        asteroid = Asteroid()
        asteroid.pos = ship.pos
        game.add_widget(asteroid)
        game.asteroids.append(asteroid)
        game.update(0)
        assert ship.lives == expected

    assert game.spaceships == []
    assert game.menu in game.children


# ---- input: keyboard, gamepad, touch buttons, menu navigation ------------

KEY_UP, KEY_LEFT, KEY_RIGHT, KEY_SPACE, KEY_ENTER, KEY_ESC = (
    273, 276, 275, 32, 13, 27)


def test_keyboard_drives_ship(game):
    ship = game.spaceships[0]
    game._on_key_down(None, KEY_UP)
    assert ship.thrust
    game._on_key_up(None, KEY_UP)
    assert not ship.thrust

    game._on_key_down(None, KEY_LEFT)
    assert ship.angle_rotation == 3
    game._on_key_up(None, KEY_LEFT)
    assert ship.angle_rotation == 0

    game._on_key_down(None, KEY_SPACE)
    assert len(game.shots) == 1


def test_wasd_works_like_arrows(game):
    ship = game.spaceships[0]
    game._on_key_down(None, ord('d'))
    assert ship.angle_rotation == -3
    game._on_key_up(None, ord('d'))
    game._on_key_down(None, ord('w'))
    assert ship.thrust


def test_key_repeat_does_not_machine_gun(game):
    game._on_key_down(None, KEY_SPACE)
    game._on_key_down(None, KEY_SPACE)
    assert len(game.shots) == 1
    game._on_key_up(None, KEY_SPACE)
    game._on_key_down(None, KEY_SPACE)
    assert len(game.shots) == 2


def test_releasing_one_turn_key_keeps_other_turn(game):
    ship = game.spaceships[0]
    game._on_key_down(None, KEY_LEFT)
    game._on_key_down(None, KEY_RIGHT)
    assert ship.angle_rotation == 0
    game._on_key_up(None, KEY_LEFT)
    assert ship.angle_rotation == -3


def test_gamepad_stick_and_buttons(game):
    ship = game.spaceships[0]
    game._on_joy_axis(None, 0, 0, -32767)
    assert ship.angle_rotation == 3
    game._on_joy_axis(None, 0, 0, 1000)  # inside the deadzone
    assert ship.angle_rotation == 0

    game._on_joy_axis(None, 0, 1, -32767)  # stick up
    assert ship.thrust
    game._on_joy_axis(None, 0, 1, 0)
    assert not ship.thrust

    game._on_joy_button_down(None, 0, 0)  # A
    assert len(game.shots) == 1
    game._on_joy_button_up(None, 0, 0)


def test_gamepad_hat(game):
    ship = game.spaceships[0]
    game._on_joy_hat(None, 0, 0, (1, 0))
    assert ship.angle_rotation == -3
    game._on_joy_hat(None, 0, 0, (0, 1))
    assert ship.angle_rotation == 0
    assert ship.thrust


def test_touch_buttons_use_same_actions(game):
    ship = game.spaceships[0]
    controls = game.spaceship_controls
    controls.press('left')
    assert ship.angle_rotation == 3
    controls.release('left')
    assert ship.angle_rotation == 0


def test_back_returns_to_menu(game):
    game._on_key_down(None, KEY_ESC)
    assert game.menu in game.children
    assert not hasattr(game, 'spaceship_controls')


@pytest.fixture
def kv_game(game):
    # the menu buttons and touch buttons are declared in spacepilgrim.kv
    from kivy.lang import Builder
    Builder.load_file('spacepilgrim.kv')
    game.game_stop()
    yield game
    Builder.unload_file('spacepilgrim.kv')


def test_menu_keyboard_navigation(kv_game):
    game = kv_game
    assert game.menu.selected == 0
    game._on_key_down(None, 274)  # down
    # Multiplayer / Settings are disabled, so navigation skips them
    labels = [b.text for b in game.menu.buttons]
    assert labels == ['Single player', 'Exit']
    assert game.menu.selected == 1
    game._on_key_up(None, 274)
    game._on_key_down(None, 273)  # up wraps back
    game._on_key_up(None, 273)
    game._on_key_down(None, KEY_ENTER)  # activate Single player
    assert game.menu not in game.children
    assert len(game.spaceships) == 1


def test_gamepad_a_starts_game_from_menu(kv_game):
    game = kv_game
    game._on_joy_button_down(None, 0, 0)
    assert game.menu not in game.children


def test_kv_does_not_create_a_second_game():
    # A root `SpacePilgrimGame:` rule in the kv file makes the App build a
    # second game that never shows a menu but still listens to the keyboard,
    # which crashed on the first key press.
    from kivy.lang import Builder
    try:
        assert Builder.load_file('spacepilgrim.kv') is None
    finally:
        Builder.unload_file('spacepilgrim.kv')


def test_input_without_menu_or_controls_is_ignored():
    g = SpacePilgrimGame()  # no game_stop(): neither menu nor controls
    try:
        g._on_key_down(None, KEY_UP)
        g._on_key_up(None, KEY_UP)
        g._on_joy_button_down(None, 0, 0)
    finally:
        g.frame_schedule.cancel()
        g.asteroid_schedule.cancel()
