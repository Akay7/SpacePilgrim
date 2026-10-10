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
    # Multiplayer is disabled, so navigation skips it
    labels = [b.text for b in game.menu.buttons]
    assert labels == ['Single player', 'Settings', 'Exit']
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


# ---- configurable key bindings -------------------------------------------

import json

KEY_F, KEY_I, KEY_Q = ord('f'), ord('i'), ord('q')


def test_default_bindings():
    kb = main.KeyBindings()
    assert kb.action_for(ord('w')) == 'up'
    assert kb.action_for(KEY_SPACE) == 'fire'
    assert kb.action_for(KEY_UP) == 'up'      # arrows are reserved
    assert kb.action_for(KEY_ENTER) == 'fire'
    assert kb.action_for(KEY_ESC) == 'back'


def test_rebind_replaces_old_keys():
    kb = main.KeyBindings()
    assert kb.rebind('fire', KEY_F) is None
    assert kb.action_for(KEY_F) == 'fire'
    assert kb.action_for(KEY_SPACE) is None


def test_rebind_rejects_conflict_and_reserved():
    kb = main.KeyBindings()
    assert 'Fire' in kb.rebind('left', KEY_SPACE)
    assert kb.rebind('left', KEY_ESC)
    assert kb.rebind('left', KEY_ENTER)
    assert kb.rebind('left', KEY_UP)
    assert kb.action_for(ord('a')) == 'left'
    assert kb.action_for(KEY_SPACE) == 'fire'


def test_bindings_round_trip_and_reset(tmp_path):
    path = str(tmp_path / 'sub' / 'keys.json')
    kb = main.KeyBindings(path)
    kb.rebind('up', KEY_I)
    assert main.KeyBindings(path).action_for(KEY_I) == 'up'
    kb.reset()
    assert main.KeyBindings(path).action_for(KEY_I) is None
    assert main.KeyBindings(path).action_for(ord('w')) == 'up'


@pytest.mark.parametrize('content', [
    'not json', '[]', '{"version": 2, "keys": {"up": [26]}}',
    '{"version": 2, "keys": {"up": [41], "left": [4], "right": [7], "fire": [44]}}',
    '{"version": 2, "keys": {"up": [5], "left": [5], "right": [7], "fire": [44]}}',
    '{"version": 2, "keys": {"up": ["w"], "left": [4], "right": [7], "fire": [44]}}',
])
def test_invalid_saved_bindings_fall_back(tmp_path, content):
    path = tmp_path / 'keys.json'
    path.write_text(content)
    kb = main.KeyBindings(str(path))
    assert kb.keys == main.DEFAULT_KEY_BINDINGS


def test_missing_and_unwritable_path(tmp_path):
    kb = main.KeyBindings(str(tmp_path / 'missing.json'))
    assert kb.keys == main.DEFAULT_KEY_BINDINGS
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    kb = main.KeyBindings(str(blocker / 'keys.json'))  # parent is a file
    assert kb.rebind('up', KEY_I) is None              # no exception
    assert kb.action_for(KEY_I) == 'up'


def test_rebound_key_drives_ship(game):
    ship = game.spaceships[0]
    game.bindings.rebind('up', KEY_I)
    game._on_key_down(None, KEY_I)
    assert ship.thrust
    game._on_key_up(None, KEY_I)
    game._on_key_down(None, ord('w'))
    assert not ship.thrust


def _open_settings(game):
    game._on_key_down(None, 274)   # down to Settings
    game._on_key_up(None, 274)
    game._on_key_down(None, KEY_ENTER)
    game._on_key_up(None, KEY_ENTER)
    assert game.settings_active


def test_settings_open_and_back(kv_game):
    game = kv_game
    assert not [b for b in game.menu.buttons if b.text == 'Settings'][0].disabled
    _open_settings(game)
    assert game.menu not in game.children
    labels = [b.text for b in game.settings.buttons]
    assert labels[:4] == ['Thrust: W', 'Turn left: A', 'Turn right: D',
                          'Fire: Space']
    assert labels[-2:] == ['Reset to defaults', 'Back']
    game._on_key_down(None, KEY_ESC)    # Escape goes back to the menu
    assert not game.settings_active
    assert game.menu in game.children


def test_settings_rebind_fire_in_game(kv_game):
    game = kv_game
    game.bindings.path = None
    _open_settings(game)
    game.settings.begin_rebind('fire')
    game._on_key_down(None, KEY_F)
    game._on_key_up(None, KEY_F)
    assert game.settings.bindings.action_for(KEY_F) == 'fire'
    assert game.settings.buttons[3].text == 'Fire: F'
    assert game.settings.waiting == ''
    game.close_settings()
    game.menu.move(-1)                   # back to "Single player"
    game._on_key_down(None, KEY_ENTER)   # start the game
    game._on_key_up(None, KEY_ENTER)
    game._on_key_down(None, KEY_F)
    assert len(game.shots) == 1
    game._on_key_up(None, KEY_F)
    game._on_key_down(None, KEY_SPACE)
    assert len(game.shots) == 1


def test_settings_conflict_message_and_cancel(kv_game):
    game = kv_game
    game.bindings.path = None
    _open_settings(game)
    game.settings.begin_rebind('left')
    game._on_key_down(None, KEY_SPACE)
    game._on_key_up(None, KEY_SPACE)
    assert 'Fire' in game.settings.ids.message.text
    assert game.bindings.action_for(ord('a')) == 'left'

    game.settings.begin_rebind('left')
    game._on_key_down(None, KEY_ESC)    # cancels, stays in settings
    game._on_key_up(None, KEY_ESC)
    assert game.settings_active
    assert game.settings.waiting == ''
    assert game.bindings.action_for(ord('a')) == 'left'


def test_settings_reset(kv_game):
    game = kv_game
    game.bindings.path = None
    game.bindings.rebind('fire', KEY_F)
    _open_settings(game)
    game.settings.reset()
    assert game.bindings.action_for(KEY_SPACE) == 'fire'
    assert game.bindings.action_for(KEY_F) is None
    assert game.settings.buttons[3].text == 'Fire: Space'


def test_bindings_follow_physical_key_not_layout():
    kb = main.KeyBindings()
    # Cyrillic layout: the W key (scancode 26) reports the code of "ц"
    assert kb.action_for(1094, 26) == 'up'
    assert kb.rebind('up', 1096, 12) is None        # physical I key, "ш"
    assert kb.action_for(ord('i'), 12) == 'up'      # same key, latin layout
    assert kb.action_for(1096, 12) == 'up'
    assert kb.label('up') == 'I'


def test_key_labels_are_latin():
    assert main.scancode_name(26) == 'W'
    assert main.scancode_name(58) == 'F1'
    assert main.scancode_name(500) == 'Key 500'


def test_old_format_file_is_ignored(tmp_path):
    path = tmp_path / 'keys.json'
    path.write_text(json.dumps(
        {'up': [105], 'left': [97], 'right': [100], 'fire': [32]}))
    assert main.KeyBindings(str(path)).keys == main.DEFAULT_KEY_BINDINGS
