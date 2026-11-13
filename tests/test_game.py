import json
import os

import pytest

import main
from main import Asteroid, Shot, Spaceship, SpacePilgrimGame

# the real check: conftest makes every test a two-seat screen
four_seat_screen = main.four_seat_screen


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


def test_engine_sound_plays_while_any_ship_thrusts():
    one, two = Spaceship(), Spaceship()
    one.thrust_on()
    two.thrust_on()
    two.thrust_off()
    assert Spaceship.sound.state == 'play'
    one.thrust_off()
    assert Spaceship.sound.state == 'stop'


def mixer_channels_playing():
    # Kivy's own SDL_mixer (already loaded): how many sounds are heard
    import ctypes
    import glob
    import kivy
    lib = glob.glob(os.path.join(os.path.dirname(kivy.__file__),
                                 '..', 'Kivy.libs', 'libSDL2_mixer*'))
    if not lib:
        pytest.skip('no bundled SDL2_mixer to ask')
    return ctypes.CDLL(lib[0]).Mix_Playing(-1)


def test_shots_and_explosions_overlap():
    # two players fire (or blow up) at once: both sounds must be heard,
    # the second must not cut the first off
    Spaceship.sound.stop()
    before = mixer_channels_playing()
    Shot()
    Shot()
    assert mixer_channels_playing() == before + 2
    explosions = [main.Explosion(), main.Explosion()]
    assert mixer_channels_playing() == before + 4
    for explosion in explosions:   # never added to a game to leave
        explosion.pause()


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


def test_asteroid_hit_costs_life_then_game_over(game, kv):
    ship = game.spaceships[0]
    for expected in (2, 1, 0):
        asteroid = Asteroid()
        asteroid.pos = ship.pos
        game.add_widget(asteroid)
        game.asteroids.append(asteroid)
        game.update(0)
        assert ship.lives == expected

    assert game.spaceships == []
    assert game.results_active


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


def test_back_pauses_the_game(game):
    game._on_key_down(None, KEY_ESC)
    assert game.paused and game.menu not in game.children
    assert game.spaceships


def test_android_back_in_game_is_consumed(game, monkeypatch):
    # Kivy sends on_keyboard right after on_key_down; Back must not also
    # pause the app on Android: it pauses the game.
    import main
    monkeypatch.setattr(main, 'platform', 'android')
    game._on_key_down(None, KEY_ESC)
    assert game.paused
    assert game._on_keyboard(None, KEY_ESC) is True
    # from the main menu, Back is left to Android
    game.game_stop()
    game._on_key_up(None, KEY_ESC)
    game._on_key_down(None, KEY_ESC)
    assert game._on_keyboard(None, KEY_ESC) is None


@pytest.fixture
def kv():
    # results and leaderboard screens are declared in spacepilgrim.kv
    from kivy.lang import Builder
    Builder.load_file('spacepilgrim.kv')
    yield
    Builder.unload_file('spacepilgrim.kv')


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
    labels = [b.text for b in game.menu.buttons]
    assert labels == ['Single player', 'Multiplayer', 'Leaderboard',
                      'Settings', 'Exit']
    assert game.menu.selected == 1
    game._on_key_up(None, 274)
    game._on_key_down(None, 273)  # up wraps back
    game._on_key_up(None, 273)
    game._on_key_down(None, KEY_ENTER)  # activate Single player
    game._on_key_up(None, KEY_ENTER)
    assert game.menu not in game.children
    assert game.select_active            # ship selection comes first
    _press(game, KEY_ENTER)              # ready
    assert len(game.spaceships) == 1


def test_gamepad_a_opens_ship_selection_from_menu(kv_game):
    game = kv_game
    game._on_joy_button_down(None, 0, 0)
    assert game.menu not in game.children
    assert game.select_active
    game._on_joy_button_up(None, 0, 0)
    game._on_joy_button_down(None, 0, 0)    # ready: starts the game
    assert len(game.spaceships) == 1


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

KEY_F, KEY_Y, KEY_Q = ord('f'), ord('y'), ord('q')


def test_default_bindings():
    kb = main.KeyBindings()
    assert kb.action_for(ord('w')) == 'up'
    assert kb.action_for(KEY_SPACE) == 'fire'
    assert kb.action_for(KEY_UP) == 'up'      # arrows are reserved
    assert kb.action_for(KEY_ENTER) == 'fire'
    assert kb.action_for(KEY_ESC) == 'back'


def test_second_set_defaults():
    kb = main.KeyBindings()
    assert kb.lookup(ord('w')) == (0, 'up')
    assert kb.lookup(ord('i')) == (1, 'up')
    assert kb.lookup(ord('j')) == (1, 'left')
    assert kb.lookup(ord('l')) == (1, 'right')
    assert kb.lookup(ord('k')) == (1, 'fire')
    assert kb.lookup(KEY_UP) == (0, 'up')       # arrows count as set 1
    assert kb.lookup(KEY_ENTER) == (0, 'fire')
    assert kb.lookup(KEY_ESC) == (None, 'back')
    assert kb.lookup(ord('q')) == (None, None)
    assert kb.label('fire', 1) == 'K'


def test_rebind_is_per_set_and_conflicts_span_sets():
    kb = main.KeyBindings()
    assert kb.rebind('left', ord('u'), key_set=1) is None
    assert kb.lookup(ord('u')) == (1, 'left')
    assert kb.lookup(ord('j')) == (None, None)
    assert kb.action_for(ord('a')) == 'left'     # set 1 unchanged
    message = kb.rebind('up', ord('w'), key_set=1)
    assert 'Set 1' in message and 'Thrust' in message
    assert kb.lookup(ord('i')) == (1, 'up')      # kept
    assert 'Set 2' in kb.rebind('fire', ord('i'))
    assert kb.lookup(ord('k')) == (1, 'fire')


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
    kb.rebind('up', KEY_Y)
    assert main.KeyBindings(path).action_for(KEY_Y) == 'up'
    kb.reset()
    assert main.KeyBindings(path).action_for(KEY_Y) is None
    assert main.KeyBindings(path).action_for(ord('w')) == 'up'


@pytest.mark.parametrize('content', [
    'not json', '[]', '{"version": 2, "keys": {"up": [26]}}',
    '{"version": 2, "keys": {"up": [41], "left": [4], "right": [7], "fire": [44]}}',
    '{"version": 2, "keys": {"up": [5], "left": [5], "right": [7], "fire": [44]}}',
    '{"version": 2, "keys": {"up": ["w"], "left": [4], "right": [7], "fire": [44]}}',
    '{"version": 3, "players": []}',
    '{"version": 3, "players": [{"up": [26]}, {"up": [12]}]}',
    json.dumps({"version": 3, "players": [      # same key for both players
        {"up": [26], "left": [4], "right": [7], "fire": [44]},
        {"up": [26], "left": [13], "right": [15], "fire": [14]}]}),
])
def test_invalid_saved_bindings_fall_back(tmp_path, content):
    path = tmp_path / 'keys.json'
    path.write_text(content)
    kb = main.KeyBindings(str(path))
    assert kb.keys == main.DEFAULT_PLAYER_KEYS


def test_set_bindings_round_trip(tmp_path):
    path = str(tmp_path / 'keys.json')
    kb = main.KeyBindings(path)
    kb.rebind('fire', ord('h'), key_set=1)
    again = main.KeyBindings(path)
    assert again.lookup(ord('h')) == (1, 'fire')
    assert again.lookup(KEY_SPACE) == (0, 'fire')
    assert json.load(open(path))['version'] == 3
    again.reset()
    assert main.KeyBindings(path).keys == main.DEFAULT_PLAYER_KEYS


def test_version_2_file_becomes_player_1(tmp_path):
    path = tmp_path / 'keys.json'
    path.write_text(json.dumps({'version': 2, 'keys': {
        'up': [26], 'left': [4], 'right': [7], 'fire': [9]}}))   # fire on F
    kb = main.KeyBindings(str(path))
    assert kb.lookup(ord('f')) == (0, 'fire')
    assert kb.lookup(KEY_SPACE) == (None, None)
    assert kb.keys[1] == main.DEFAULT_KEY_BINDINGS_P2


def test_version_2_file_using_second_player_default_keeps_both_playable(tmp_path):
    path = tmp_path / 'keys.json'
    path.write_text(json.dumps({'version': 2, 'keys': {
        'up': [12], 'left': [4], 'right': [7], 'fire': [44]}}))  # up on I
    kb = main.KeyBindings(str(path))
    assert kb.lookup(ord('i')) == (0, 'up')
    scancodes = [sc for p in kb.keys for k in p.values() for sc in k]
    assert len(scancodes) == len(set(scancodes)) == 8


def test_missing_and_unwritable_path(tmp_path):
    kb = main.KeyBindings(str(tmp_path / 'missing.json'))
    assert kb.keys == main.DEFAULT_PLAYER_KEYS
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    kb = main.KeyBindings(str(blocker / 'keys.json'))  # parent is a file
    assert kb.rebind('up', KEY_Y) is None              # no exception
    assert kb.action_for(KEY_Y) == 'up'


def test_rebound_key_drives_ship(game):
    ship = game.spaceships[0]
    game.bindings.rebind('up', KEY_Y)
    game._on_key_down(None, KEY_Y)
    assert ship.thrust
    game._on_key_up(None, KEY_Y)
    game._on_key_down(None, ord('w'))
    assert not ship.thrust


def _open_settings(game):
    _press(game, 274)              # down to Multiplayer
    _press(game, 274)              # down to Leaderboard
    _press(game, 274)              # down to Settings
    game._on_key_down(None, KEY_ENTER)
    game._on_key_up(None, KEY_ENTER)
    assert game.settings_active


def _press(game, key):
    game._on_key_down(None, key)
    game._on_key_up(None, key)


def _open_keyboard(game):
    _open_settings(game)
    _press(game, KEY_ENTER)              # "Keyboard layout" is first
    assert isinstance(game.settings, main.KeyboardSettings)


def _open_touch(game):
    _open_settings(game)
    _press(game, 274)                    # down to "Gamepad buttons"
    _press(game, 274)                    # down to "Touch controls"
    _press(game, KEY_ENTER)
    assert isinstance(game.settings, main.TouchSettingsScreen)


def test_settings_hub_and_back(kv_game):
    game = kv_game
    assert not [b for b in game.menu.buttons if b.text == 'Settings'][0].disabled
    _open_settings(game)
    assert game.menu not in game.children
    assert [b.text for b in game.settings.buttons] == [
        'Keyboard layout', 'Gamepad buttons', 'Touch controls', 'Back']
    game._on_key_down(None, KEY_ESC)    # Escape goes back to the menu
    assert not game.settings_active
    assert game.menu in game.children


def test_keyboard_page_lists_keys_and_goes_back_to_hub(kv_game):
    game = kv_game
    _open_keyboard(game)
    labels = [b.text for b in game.settings.buttons]
    assert labels[:4] == ['Thrust: W', 'Turn left: A', 'Turn right: D',
                          'Fire: Space']
    assert labels[-2:] == ['Reset to defaults', 'Back']
    _press(game, KEY_ESC)
    assert isinstance(game.settings, main.SettingsScreen)
    _press(game, KEY_ESC)
    assert game.menu in game.children


def test_settings_rebind_fire_in_game(kv_game):
    game = kv_game
    game.bindings.path = None
    _open_keyboard(game)
    game.settings.begin_rebind('fire')
    game._on_key_down(None, KEY_F)
    game._on_key_up(None, KEY_F)
    assert game.settings.bindings.action_for(KEY_F) == 'fire'
    assert game.settings.buttons[3].text == 'Fire: F'
    assert game.settings.waiting == ''
    game.close_settings()
    game.menu.move(-3)                   # back to "Single player"
    _press(game, KEY_ENTER)              # ship selection
    _press(game, KEY_ENTER)              # ready: start the game
    game._on_key_down(None, KEY_F)
    assert len(game.shots) == 1
    game._on_key_up(None, KEY_F)
    game._on_key_down(None, KEY_SPACE)
    assert len(game.shots) == 1


def test_settings_conflict_message_and_cancel(kv_game):
    game = kv_game
    game.bindings.path = None
    _open_keyboard(game)
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
    _open_keyboard(game)
    game.settings.reset()
    assert game.bindings.action_for(KEY_SPACE) == 'fire'
    assert game.bindings.action_for(KEY_F) is None
    assert game.settings.buttons[3].text == 'Fire: Space'


def test_bindings_follow_physical_key_not_layout():
    kb = main.KeyBindings()
    # Cyrillic layout: the W key (scancode 26) reports the code of "ц"
    assert kb.action_for(1094, 26) == 'up'
    assert kb.rebind('up', 1085, 28) is None        # physical Y key, "н"
    assert kb.action_for(ord('y'), 28) == 'up'      # same key, latin layout
    assert kb.action_for(1085, 28) == 'up'
    assert kb.label('up') == 'Y'


def test_key_labels_are_latin():
    assert main.scancode_name(26) == 'W'
    assert main.scancode_name(58) == 'F1'
    assert main.scancode_name(500) == 'Key 500'


def test_old_format_file_is_ignored(tmp_path):
    path = tmp_path / 'keys.json'
    path.write_text(json.dumps(
        {'up': [105], 'left': [97], 'right': [100], 'fire': [32]}))
    assert main.KeyBindings(str(path)).keys == main.DEFAULT_PLAYER_KEYS


# ---- touch controls ------------------------------------------------------

class FakeTouch:
    _uid = 0

    def __init__(self, pos):
        FakeTouch._uid += 1
        self.uid = FakeTouch._uid
        self.pos = pos
        self.grab_current = None

    def grab(self, widget):
        pass

    def ungrab(self, widget):
        pass

    def dispatch(self, widget, event):
        self.grab_current = widget
        try:
            return getattr(widget, event)(self)
        finally:
            self.grab_current = None


def _touch_down(layout, pos):
    layout.size = (1000, 600)   # kv (Window.size) is not loaded in `game`
    touch = FakeTouch(pos)
    return touch, layout.on_touch_down(touch)


def _fire_pos(layout):
    layout.size = (1000, 600)
    return layout.fire.center


def _stick_pos(layout, dx, dy):
    """Position of the finger: dx, dy in stick radii from its centre."""
    layout.size = (1000, 600)
    stick = layout.stick
    r = stick.width / 2
    return (stick.center_x + dx * r, stick.center_y + dy * r)


def _move(layout, touch, pos):
    touch.pos = pos
    touch.grab_current = layout.stick
    layout.stick.on_touch_move(touch)
    touch.grab_current = None


def _release(touch, widget):
    touch.grab_current = widget
    widget.on_touch_up(touch)
    touch.grab_current = None


def test_touch_settings_default_round_trip_and_corrupt(tmp_path):
    path = tmp_path / 'sub' / 'touch_ui.json'
    ts = main.TouchSettings(str(path))
    assert ts.mode == 'auto'
    ts.cycle()
    assert ts.mode == 'on'
    assert main.TouchSettings(str(path)).mode == 'on'
    ts.cycle()
    ts.cycle()
    assert ts.mode == 'auto'
    for content in ('not json', '[]', '{"mode": "maybe"}'):
        path.write_text(content)
        assert main.TouchSettings(str(path)).mode == 'auto'


def test_touch_shows_controls_on_any_device(game):
    # desktop / device detected as TV: hidden at start, a touch shows them
    assert game.touch_settings.mode == 'auto'
    assert not game.touch_ui
    assert not game.spaceship_controls.touch_buttons.active
    game._on_window_touch(None, None)
    assert game.touch_ui
    assert game.spaceship_controls.touch_buttons.active


def test_keyboard_hides_and_touch_shows_again(game):
    game._on_window_touch(None, None)
    game._on_key_down(None, KEY_UP)
    assert not game.touch_ui
    game._on_key_up(None, KEY_UP)
    game._on_window_touch(None, None)
    assert game.touch_ui
    game._on_key_down(None, KEY_SPACE)   # keyboard still works
    assert len(game.shots) == 1


def test_mode_on_keeps_controls_visible(game):
    game.touch_settings.mode = 'on'
    game._set_touch_ui(False, force=True)
    assert game.touch_ui
    game._on_key_down(None, KEY_UP)
    assert game.touch_ui
    assert game.spaceship_controls.touch_buttons.active


def test_mode_off_never_shows_controls(game):
    game.touch_settings.mode = 'off'
    game._on_window_touch(None, None)
    assert not game.touch_ui
    assert not game.spaceship_controls.touch_buttons.active


def test_cycle_touch_mode_applies_immediately(game):
    game.cycle_touch_mode()              # auto -> on
    assert game.touch_settings.mode == 'on'
    assert game.touch_ui
    game.cycle_touch_mode()              # on -> off
    assert not game.touch_ui


def test_touch_page_mode_and_slider(kv_game):
    game = kv_game
    game.touch_settings.path = None
    _open_touch(game)
    page = game.settings
    mode, slider = page.ids.btn_mode, page.ids.slider_scale
    assert mode.text == 'Touch controls: Auto'
    assert page.ids.lbl_scale.text == 'Size: 100%'
    assert slider.max == 4 and slider.value == 1
    mode.dispatch('on_press')            # same path as a tap
    assert mode.text == 'Touch controls: On'
    assert game.touch_settings.mode == 'on'
    slider.value = 4                     # same path as dragging
    assert game.touch_settings.scale == 4.0
    assert page.ids.lbl_scale.text == 'Size: 400%'
    _press(game, KEY_ESC)                # back to the hub, then the keyboard
    assert isinstance(game.settings, main.SettingsScreen)
    game.show_keyboard_settings()
    game.settings.reset()                # reset only touches key bindings
    assert game.touch_settings.mode == 'on'
    assert game.touch_settings.scale == 4.0


def test_slider_keyboard_adjust(kv_game):
    game = kv_game
    game.touch_settings.path = None
    _open_touch(game)
    _press(game, KEY_RIGHT)
    assert game.touch_settings.scale == pytest.approx(1.1)
    assert game.settings.ids.slider_scale.value == pytest.approx(1.1)
    _press(game, KEY_LEFT)
    _press(game, KEY_LEFT)
    assert game.touch_settings.scale == pytest.approx(0.9)
    for _ in range(30):
        _press(game, KEY_LEFT)
    assert game.touch_settings.scale == 0.5


def test_scale_persists_and_validates(tmp_path):
    path = str(tmp_path / 'touch_ui.json')
    ts = main.TouchSettings(path)
    assert ts.scale == 1.0
    ts.set_scale(3.33)
    assert ts.scale == pytest.approx(3.35)
    assert main.TouchSettings(path).scale == pytest.approx(3.35)
    ts.set_scale(10)
    assert ts.scale == 4.0
    for bad in ('99', '"big"', 'true', '0.1'):
        with open(path, 'w') as f:
            f.write('{"mode": "on", "scale": %s}' % bad)
        loaded = main.TouchSettings(path)
        assert (loaded.mode, loaded.scale) == ('on', 1.0)


def test_scale_changes_control_size(game):
    layout = game.spaceship_controls.touch_buttons
    layout.size = (1000, 600)
    base = layout.stick.width
    layout.set_scale(1.5)
    assert layout.stick.width == pytest.approx(base * 1.5)
    assert layout.fire.width == pytest.approx(main.dp(main.FIRE_DP) * 1.5)
    assert layout.fire.right <= 1000


def test_huge_scale_stays_on_screen(game):
    layout = game.spaceship_controls.touch_buttons
    layout.size = (800, 480)
    layout.set_scale(4.0)
    for pad in (layout.stick, layout.fire):
        assert pad.width <= layout.height
        assert pad.x >= 0 and pad.y >= 0
        assert pad.right <= layout.width and pad.top <= layout.height
    assert layout.stick.right <= layout.fire.x   # no overlap


def test_controls_keep_margin_from_screen_edges(game):
    layout = game.spaceship_controls.touch_buttons
    layout.size = (1000, 600)
    margin = main.dp(main.MARGIN_DP)
    assert layout.stick.x == pytest.approx(margin)
    assert layout.stick.y == pytest.approx(margin)
    assert layout.fire.y == pytest.approx(margin)
    assert 1000 - layout.fire.right == pytest.approx(margin)


def test_joystick_directions(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    touch, consumed = _touch_down(layout, _stick_pos(layout, 0, 0))
    assert consumed and not ship.thrust and ship.angle_rotation == 0  # centre

    _move(layout, touch, _stick_pos(layout, 0, 0.9))       # up
    assert ship.thrust and ship.angle_rotation == 0
    _move(layout, touch, _stick_pos(layout, -0.9, 0))      # left
    assert not ship.thrust and ship.angle_rotation == 3
    _move(layout, touch, _stick_pos(layout, 0.9, 0))       # right
    assert ship.angle_rotation == -3
    _move(layout, touch, _stick_pos(layout, 0, -0.9))      # down: nothing
    assert not ship.thrust and ship.angle_rotation == 0


def test_joystick_between_positions(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    touch, _ = _touch_down(layout, _stick_pos(layout, -0.7, 0.7))
    assert ship.thrust and ship.angle_rotation == 3
    _move(layout, touch, _stick_pos(layout, 0.7, 0.7))
    assert ship.thrust and ship.angle_rotation == -3


def test_joystick_knob_follows_clamps_and_recentres(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    touch, _ = _touch_down(layout, _stick_pos(layout, 0.5, 0))
    assert layout.stick.knob == pytest.approx([0.5, 0])
    _move(layout, touch, _stick_pos(layout, -3, 0))        # far outside
    assert layout.stick.knob == pytest.approx([-1, 0])
    assert ship.angle_rotation == 3
    _release(touch, layout.stick)
    assert layout.stick.knob == [0.0, 0.0]
    assert ship.angle_rotation == 0 and not ship.thrust


def test_stick_and_fire_together(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    stick, _ = _touch_down(layout, _stick_pos(layout, -0.9, 0))
    assert ship.angle_rotation == 3
    fire, consumed = _touch_down(layout, _fire_pos(layout))
    assert consumed and len(game.shots) == 1
    assert ship.angle_rotation == 3      # still turning while firing
    _release(fire, layout.fire)
    _release(stick, layout.stick)
    assert ship.angle_rotation == 0
    assert not layout.fire.pressed


def test_fire_button_is_square_and_labelled(game):
    layout = game.spaceship_controls.touch_buttons
    layout.size = (1000, 600)
    fire = layout.fire
    assert fire.width == fire.height
    assert fire.collide_point(fire.x + 1, fire.y + 1)    # corner is part of it
    assert fire._label.text == 'FIRE'
    assert fire._fill_color.r > 0.7 and fire._fill_color.g < 0.3   # red


def test_hidden_controls_do_not_consume_touches(game):
    layout = game.spaceship_controls.touch_buttons
    assert not layout.active
    _, consumed = _touch_down(layout, _fire_pos(layout))
    assert not consumed
    assert game.shots == []
    _, consumed = _touch_down(layout, _stick_pos(layout, 0, 0))
    assert not consumed


def test_hiding_releases_held_stick(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    _touch_down(layout, _stick_pos(layout, 0, 0.9))
    assert ship.thrust
    game._on_key_down(None, KEY_SPACE)   # keyboard hides the pad
    assert not ship.thrust
    assert layout.stick.knob == [0.0, 0.0]


def test_game_start_applies_saved_scale():
    g = SpacePilgrimGame()
    try:
        g.touch_settings.scale = 1.5
        g.game_stop()
        g.game_start()
        layout = g.spaceship_controls.touch_buttons
        layout.size = (1000, 600)
        assert layout.stick.width == pytest.approx(main.dp(main.STICK_DP) * 1.5)
    finally:
        g.frame_schedule.cancel()
        g.asteroid_schedule.cancel()


# ---- local multiplayer ---------------------------------------------------

@pytest.fixture
def game2():
    g = SpacePilgrimGame()
    g.game_stop()
    g.game_start(2)
    yield g
    g.frame_schedule.cancel()
    g.asteroid_schedule.cancel()


TOUCH2 = [('touch', 'left'), ('touch', 'right')]


@pytest.fixture
def start_game():
    """Start games with given slots; their clocks stop after the test."""
    games = []

    def start(**kwargs):
        g = SpacePilgrimGame()
        g.game_stop()
        g.game_start(**kwargs)
        games.append(g)
        return g
    yield start
    for g in games:
        g.frame_schedule.cancel()
        g.asteroid_schedule.cancel()


@pytest.fixture
def touch2(start_game):
    return start_game(slots=TOUCH2)


def test_keyboard_page_switches_set(kv_game):
    game = kv_game
    game.bindings.path = None
    _open_keyboard(game)
    page = game.settings
    assert page.ids.btn_set.text == 'Keys of: Set 1'
    page.switch_set()
    assert page.ids.btn_set.text == 'Keys of: Set 2'
    assert [b.text for b in page.buttons][:4] == [
        'Thrust: I', 'Turn left: J', 'Turn right: L', 'Fire: K']
    page.begin_rebind('left')
    game._on_key_down(None, ord('u'))
    game._on_key_up(None, ord('u'))
    assert page.ids.btn_set.text == 'Keys of: Set 2'
    assert game.bindings.lookup(ord('u')) == (1, 'left')
    assert game.bindings.action_for(ord('a')) == 'left'
    assert game.bindings.label('left', 0) == 'A'
    page.begin_rebind('up')                       # W is player 1's key
    game._on_key_down(None, ord('w'))
    game._on_key_up(None, ord('w'))
    assert 'Set 1' in page.ids.message.text
    page.switch_set()
    assert page.ids.btn_set.text == 'Keys of: Set 1'
    assert page.buttons[0].text == 'Thrust: W'


def test_two_player_start_has_two_ships_and_own_controls(game2):
    assert len(game2.spaceships) == 2
    a, b = game2.spaceships
    assert a.pos != b.pos
    assert game2.slots == [('keys', 0), ('keys', 1)]
    assert len(game2.controls) == 2
    assert game2.spaceship_controls is game2.controls[0]
    assert game2.controls[0].spaceship is a and game2.controls[1].spaceship is b
    assert [c.touch for c in game2.controls] == ['off', 'off']
    assert not any(c.touch_buttons.active for c in game2.controls)
    assert a.cabin != b.cabin


def test_touch_players_get_controls_on_their_side(touch2):
    left, right = touch2.controls[:2]
    assert (left.touch_buttons.side, right.touch_buttons.side) == (
        'left', 'right')
    assert left.touch_buttons.active and right.touch_buttons.active


def test_single_player_start_unchanged(game):
    assert len(game.spaceships) == 1
    assert len(game.controls) == 1
    assert game.controls[0].touch_buttons.side == ''


def test_both_keyboard_sets_drive_their_own_ship(game2):
    one, two = game2.spaceships
    game2._on_key_down(None, ord('w'))
    game2._on_key_down(None, ord('a'))
    game2._on_key_down(None, ord('i'))
    assert one.thrust and one.angle_rotation == 3
    assert two.thrust and two.angle_rotation == 0
    game2._on_key_down(None, ord('l'))
    assert two.angle_rotation == -3 and one.angle_rotation == 3
    game2._on_key_down(None, ord('k'))
    assert len(game2.shots) == 1 and game2.shots[0].spaceship is two
    game2._on_key_down(None, KEY_SPACE)
    assert [s.spaceship for s in game2.shots] == [two, one]
    game2._on_key_up(None, ord('w'))
    assert not one.thrust and two.thrust


def test_arrow_keys_steer_player_one_only(game2):
    one, two = game2.spaceships
    game2._on_key_down(None, KEY_UP)
    assert one.thrust and not two.thrust


def test_any_keyboard_set_drives_single_ship(game):
    ship = game.spaceships[0]
    game._on_key_down(None, ord('i'))
    assert ship.thrust
    game._on_key_down(None, ord('k'))
    assert len(game.shots) == 1


def test_joined_gamepads_drive_their_own_ship(start_game):
    game = start_game(slots=[('pad', 7), ('pad', 3), None, None])
    one, two = game.spaceships
    game._on_joy_button_down(None, 7, 0)
    assert [s.spaceship for s in game.shots] == [one]
    game._on_joy_button_down(None, 3, 0)
    assert [s.spaceship for s in game.shots] == [one, two]
    game._on_joy_axis(None, 3, 1, -32767)       # pad 3 stick up
    assert two.thrust and not one.thrust
    game._on_joy_hat(None, 7, 0, (-1, 0))
    assert one.angle_rotation == 3 and two.angle_rotation == 0
    game._on_joy_button_down(None, 9, 0)        # a pad that did not join
    assert len(game.shots) == 2
    game._on_key_down(None, ord('w'))           # nor did the keyboard
    assert not one.thrust


def test_swapped_keyboard_sets_and_a_gamepad(start_game):
    game = start_game(slots=[('keys', 1), ('pad', 0), ('keys', 0), None])
    one, two, three = game.spaceships
    game._on_key_down(None, ord('i'))           # set 2 joined as player 1
    assert one.thrust and not three.thrust
    game._on_key_down(None, ord('a'))           # set 1 joined as player 3
    assert three.angle_rotation == 3 and one.angle_rotation == 0
    game._on_joy_axis(None, 0, 1, -32767)
    assert two.thrust


def test_four_player_start(start_game):
    game = start_game(slots=[('keys', 0), ('pad', 0), ('pad', 1), ('keys', 1)])
    ships = game.spaceships
    assert len(ships) == 4 and game.num_players == 4
    assert len({s.cabin for s in ships}) == 4
    for i, a in enumerate(ships):
        for b in ships[i + 1:]:
            assert not a.collide_widget(b)
    game._on_joy_button_down(None, 1, 0)
    assert game.shots[0].spaceship is ships[2]


def test_joined_pad_back_pauses_game(start_game):
    game = start_game(slots=[('pad', 0), ('keys', 0), None, None])
    game._on_joy_button_down(None, 0, 7)        # Start
    assert game.paused and game.spaceships


def test_any_gamepad_drives_single_ship(game):
    ship = game.spaceships[0]
    game._on_joy_axis(None, 4, 1, -32767)
    assert ship.thrust
    game._on_joy_axis(None, 4, 1, 0)
    game._on_joy_axis(None, 5, 0, -32767)
    assert ship.angle_rotation == 3


def _hit(game, ship):
    asteroid = Asteroid()
    asteroid.pos = ship.pos
    game.add_widget(asteroid)
    game.asteroids.append(asteroid)
    game.update(0)


def test_points_go_to_the_shooter(game2):
    one, two = game2.spaceships
    two.shot()
    shot = game2.shots[0]
    one.pos, two.pos = (5000, 5000), (6000, 6000)
    asteroid = Asteroid()
    asteroid.pos = shot.pos
    game2.add_widget(asteroid)
    game2.asteroids.append(asteroid)
    game2.update(0)
    assert two.points == 1 and one.points == 0


def test_one_ship_out_other_keeps_playing(game2):
    one, two = game2.spaceships
    for _ in range(3):
        _hit(game2, one)
    assert one.lives == 0
    assert game2.spaceships == [two]
    assert game2.menu not in game2.children
    assert game2.controls[0] is None and game2.controls[1] is not None
    game2._on_key_down(None, ord('w'))             # dead player's keys: ignored
    game2._on_key_down(None, ord('i'))
    assert two.thrust
    game2._on_key_down(None, ord('k'))
    assert game2.shots[0].spaceship is two


def test_game_ends_when_both_ships_are_out(game2, kv):
    one, two = game2.spaceships
    for _ in range(3):
        _hit(game2, one)
    for _ in range(3):
        _hit(game2, two)
    assert game2.spaceships == []
    assert game2.results_active
    assert game2.controls == []


def test_back_from_any_player_pauses_two_player_game(game2):
    game2._on_joy_button_down(None, 1, 6)
    assert game2.paused and game2.spaceships


def test_one_status_block_per_ship(game2, game):
    assert len(game2.statuses) == 2
    one, two = game2.statuses
    assert (one.side, two.side) == ('row', 'row')   # keyboard players
    assert (one.column, two.column) == (0, 1)
    assert one.spaceship is game2.spaceships[0]
    assert tuple(one.color[:3]) == pytest.approx(
        main.cabin_rgb(game2.spaceships[0].cabin))
    assert len(game.statuses) == 1 and game.statuses[0].side == ''


def _touch_layouts(game):
    layouts = [c.touch_buttons for c in game.controls]
    for layout in layouts:
        layout.size = (1000, 600)
    return layouts


@pytest.mark.parametrize('size', [(800, 480), (1000, 600), (1920, 1080)])
@pytest.mark.parametrize('scale', [1.0, 4.0])
def test_two_touch_sets_are_columns_on_each_side(touch2, scale, size):
    margin = main.dp(main.MARGIN_DP)
    left, right = [c.touch_buttons for c in touch2.controls]
    for layout in (left, right):
        layout.size = size
        layout.set_scale(scale)
    w, h = size
    for layout, (lo, hi) in ((left, (0, w / 2)), (right, (w / 2, w))):
        for pad in (layout.stick, layout.fire):
            assert pad.x >= lo and pad.right <= hi
            assert pad.y >= 0 and pad.top <= h
    # controls at the two ends of each side, under the status text at the
    # top; seen from their seats both have the stick under the left hand:
    # player 1 stick on top, player 2 stick at the bottom
    top = h - main.dp(40)
    assert left.fire.y == pytest.approx(margin)
    assert left.stick.top == pytest.approx(top)
    assert right.stick.y == pytest.approx(margin)
    assert right.fire.top == pytest.approx(top)
    assert left.stick.y >= left.fire.top and right.fire.y >= right.stick.top
    assert left.stick.width == pytest.approx(right.stick.width)
    assert left.fire.width == pytest.approx(right.fire.width)
    assert left.stick.x == pytest.approx(margin)          # left edge
    assert w - right.stick.right == pytest.approx(margin)  # right edge
    assert left.stick.center_x < w / 2 < right.stick.center_x
    assert left.fire.center_x < w / 2 < right.fire.center_x


def test_touch_sets_steer_their_own_ship(touch2):
    touch2._on_window_touch(None, None)
    one, two = touch2.spaceships
    left, right = _touch_layouts(touch2)
    stick, consumed = _touch_down(left, _stick_pos(left, 0, 0.9))
    assert consumed and one.angle_rotation == 3
    fire, consumed = _touch_down(right, _fire_pos(right))
    assert consumed
    assert [s.spaceship for s in touch2.shots] == [two]
    assert one.angle_rotation == 3 and two.angle_rotation == 0
    _release(fire, right.fire)
    _release(stick, left.stick)
    assert one.angle_rotation == 0


def test_touch_pads_ignore_the_other_half(touch2):
    touch2._on_window_touch(None, None)
    left, right = _touch_layouts(touch2)
    _, consumed = _touch_down(left, _fire_pos(right))
    assert not consumed


def test_lost_ship_removes_its_touch_set(touch2):
    touch2._on_window_touch(None, None)
    one, two = touch2.spaceships
    left, right = _touch_layouts(touch2)
    stick, _ = _touch_down(left, _stick_pos(left, 0.9, 0))
    assert one.thrust
    for _ in range(3):
        _hit(touch2, one)
    assert left.parent.parent is None and right.parent.parent is not None
    assert not one.thrust


@pytest.mark.parametrize('side, forward, left, right', [
    # screen directions (dx, dy) of "away from me", "my left", "my right"
    ('left', (0.9, 0), (0, 0.9), (0, -0.9)),
    ('right', (-0.9, 0), (0, -0.9), (0, 0.9)),
])
def test_side_stick_is_turned_toward_the_seat(touch2, side, forward, left,
                                               right):
    controls = touch2.controls[0 if side == 'left' else 1]
    layout, ship = controls.touch_buttons, controls.spaceship
    layout.size = (1000, 600)
    assert layout.stick.angle == (-90 if side == 'left' else 90)
    for pos, thrust, rotation in ((forward, True, 0), (left, False, 3),
                                  (right, False, -3)):
        touch, consumed = _touch_down(layout, _stick_pos(layout, *pos))
        assert consumed
        assert (ship.thrust, ship.angle_rotation) == (thrust, rotation), pos
        _release(touch, layout.stick)
        assert not ship.thrust and ship.angle_rotation == 0


def test_side_stick_marks_point_to_the_seat_directions(touch2):
    left = touch2.controls[0].touch_buttons
    left.size = (1000, 600)
    stick = left.stick
    up_mark = stick._marks[0].points            # the thrust mark
    tip_x = up_mark[0]
    assert tip_x > stick.center_x + stick.width * 0.3   # toward the centre
    assert abs(up_mark[1] - stick.center_y) < 1e-6


def test_single_player_stick_keeps_screen_directions(game):
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    game._on_window_touch(None, None)
    layout.size = (1000, 600)
    assert layout.stick.angle == 0
    touch, _ = _touch_down(layout, _stick_pos(layout, 0, 0.9))
    assert ship.thrust and ship.angle_rotation == 0
    _release(touch, layout.stick)


def test_touch_player_keeps_controls_while_others_use_keys(start_game):
    game = start_game(slots=[('touch', 'left'), ('keys', 0), None, None])
    touch, keys = game.controls[:2]
    game.touch_settings.mode = 'off'    # joining by touch wins over it
    game._set_touch_ui(False, force=True)
    assert touch.touch_buttons.active and not keys.touch_buttons.active
    game._on_key_down(None, ord('w'))
    assert game.spaceships[1].thrust
    assert touch.touch_buttons.active and not keys.touch_buttons.active
    game.touch_settings.mode = 'auto'
    game._on_window_touch(None, None)
    assert not keys.touch_buttons.active


# ---- ship appearance -----------------------------------------------------

def _sprite():
    image = main.Image('images/ship_stop.png', keep_data=True)
    data = image.image._data[0]
    return data.data, data.width, data.height


def test_recolor_changes_only_the_cabin():
    rgba, w, h = _sprite()
    seen = set()
    for name, hue in main.CABIN_COLORS.items():
        out = main.recolor_cabin(rgba, hue)
        assert len(out) == len(rgba)
        changed = [i // 4 for i in range(0, len(rgba), 4)
                   if out[i:i + 4] != rgba[i:i + 4]]
        if name == 'blue':
            assert changed == []
            continue
        assert 40 < len(changed) < 90          # the canopy, a few dozen px
        xs = [p % w for p in changed]
        ys = [p // w for p in changed]
        assert 25 <= min(xs) and max(xs) <= 75
        assert 35 <= min(ys) and max(ys) <= 55
        seen.add(out)
    assert len(seen) == len(main.CABIN_COLORS) - 1


def test_cabin_textures_are_cached_and_applied():
    stop, fly = main.cabin_textures('red')
    assert main.cabin_textures('red') == (stop, fly)
    ship = Spaceship(cabin='red')
    assert (ship.texture_stop, ship.texture_fly) == (stop, fly)
    ship.cabin = 'green'
    assert ship.texture_stop is main.cabin_textures('green')[0]
    ship.cabin = 'nonsense'
    assert ship.texture_stop is main.cabin_textures('blue')[0]


def test_ship_colors_default_cycle_and_skip_taken():
    colors = main.ShipColors()
    assert colors.colors == ['blue', 'green', 'red', 'yellow']
    colors.cycle(0, 1, players=2)
    assert colors.colors[0] == 'red'                # green is taken
    colors.cycle(1, -1, players=2)
    assert colors.colors[1] == 'blue'               # red taken, back to blue
    colors.cycle(0, 1, players=1)                   # only one player: free
    assert colors.colors[0] == 'yellow'
    for _ in range(20):
        colors.cycle(0, 1, players=2)
        assert colors.colors[0] != colors.colors[1]


def test_ship_colors_skip_every_joined_player():
    colors = main.ShipColors()
    colors.colors = ['red', 'blue', 'purple', 'yellow']
    seen = set()
    for _ in range(12):
        colors.cycle(1, 1, active=[0, 1, 2])        # slot 4 is empty
        seen.add(colors.colors[1])
    assert seen == {'blue', 'green', 'yellow', 'orange'}


def test_ship_colors_claim_keeps_free_colour_or_takes_first_free():
    colors = main.ShipColors()
    colors.colors = ['green', 'green', 'red', 'yellow']
    colors.claim(0, [0])
    assert colors.colors[0] == 'green'              # nobody else: kept
    colors.claim(1, [0, 1])
    assert colors.colors[1] == 'blue'               # green taken: first free
    colors.claim(3, [0, 1, 3])
    assert colors.colors[3] == 'yellow'


def test_ship_colors_persist_and_fall_back(tmp_path):
    path = str(tmp_path / 'colors.json')
    colors = main.ShipColors(path)
    colors.colors = ['red', 'yellow', 'purple', 'red']
    colors.save()
    assert main.ShipColors(path).colors == ['red', 'yellow', 'purple', 'red']
    with open(path, 'w') as f:
        f.write('{"colors": ["orange", "purple"]}')    # saved for two players
    assert main.ShipColors(path).colors == [
        'orange', 'purple', 'red', 'yellow']
    defaults = ['blue', 'green', 'red', 'yellow']
    for bad in ('nope', '[]', '{"colors": ["red"]}',
                '{"colors": ["red", "red", "red"]}',
                '{"colors": ["red", "pink"]}'):
        with open(path, 'w') as f:
            f.write(bad)
        assert main.ShipColors(path).colors == defaults
    assert main.ShipColors(str(tmp_path / 'missing.json')).colors == defaults


def _join(game):
    game.ship_colors.path = None
    game.show_ship_select(2)
    return game.select


def _pad(game, stick, button):
    game._on_joy_button_down(None, stick, button)
    game._on_joy_button_up(None, stick, button)


def test_join_by_fire_in_order_and_once(kv_game):
    join = _join(kv_game)
    assert isinstance(join, main.JoinScreen)
    assert join.slots == [None] * 4 and kv_game.spaceships == []
    _press(kv_game, ord('d'))                   # no slot yet: nothing
    assert join.slots == [None] * 4
    _press(kv_game, KEY_SPACE)                  # keyboard set 1
    assert join.slots[0] == ('keys', 0)
    assert join.panels[0]['device'].text == 'Keys W A D Space'
    _pad(kv_game, 1, 0)                         # a gamepad
    assert join.slots[1] == ('pad', 1)
    assert join.panels[1]['device'].text == 'Gamepad 2'
    _press(kv_game, KEY_ENTER)                  # set 1 again: ready
    assert join.slots[2] is None and join.ready[0]


def test_join_preview_updates_and_ready_blocks_changes(kv_game):
    join = _join(kv_game)
    _press(kv_game, KEY_SPACE)
    before = join.panels[0]['preview'].texture
    _press(kv_game, ord('d'))                   # next colour
    assert kv_game.ship_colors.colors[0] == 'green'   # free: alone
    assert join.panels[0]['preview'].texture is not before
    assert join.panels[0]['name'].text == 'Green'
    _press(kv_game, KEY_SPACE)                  # ready
    _press(kv_game, ord('d'))
    assert kv_game.ship_colors.colors[0] == 'green'
    assert kv_game.spaceships == []


def test_slots_light_up_and_players_set_up_together(kv_game):
    join = _join(kv_game)
    _press(kv_game, KEY_SPACE)                  # set 1 -> player 1
    _press(kv_game, ord('k'))                   # set 2 -> player 2
    _pad(kv_game, 1, 0)                         # pad -> player 3
    assert join.slots[:3] == [('keys', 0), ('keys', 1), ('pad', 1)]
    join.flashing = [False] * 4
    kv_game._on_key_down(None, ord('d'))        # player 1 colour...
    kv_game._on_joy_button_down(None, 1, 0)     # ...while player 3 is ready
    assert join.flashing == [True, False, True, False]
    assert kv_game.ship_colors.colors[:3] == ['yellow', 'green', 'red']
    assert join.ready == [False, False, True, False]
    assert join.panels[0]['border'].width > join.panels[1]['border'].width
    join._unflash(0)
    assert not join.flashing[0]


def test_each_way_to_leave(kv_game):
    join = _join(kv_game)
    _press(kv_game, KEY_SPACE)
    _pad(kv_game, 2, 0)
    join.side_buttons['left'].dispatch('on_press')
    assert join.slots == [('keys', 0), ('pad', 2), ('touch', 'left'), None]
    _press(kv_game, ord('w'))                   # set 1 thrust key leaves
    assert join.slots[0] is None
    _pad(kv_game, 2, 6)                         # the joined pad's Back
    assert join.slots[1] is None and kv_game.select_active
    join.panels[2]['leave'].dispatch('on_press')
    assert join.slots == [None] * 4
    _press(kv_game, KEY_SPACE)                  # free to join again
    assert join.slots[0] == ('keys', 0)


def test_escape_or_unjoined_pad_back_returns_to_menu(kv_game):
    _join(kv_game)
    _press(kv_game, KEY_SPACE)
    _press(kv_game, KEY_ESC)
    assert kv_game.menu in kv_game.children and not kv_game.select_active
    _join(kv_game)
    _pad(kv_game, 4, 7)                         # Start of a pad not joined
    assert kv_game.menu in kv_game.children
    assert kv_game.spaceships == []


def test_touch_joins_from_a_side_strip(kv_game):
    join = _join(kv_game)
    left, right = join.side_buttons['left'], join.side_buttons['right']
    assert left.text == right.text == 'Tap to join by touch'
    assert left._turn.angle == -90 and right._turn.angle == 90   # to the seat
    _press(kv_game, KEY_SPACE)                  # keyboard player 1
    right.dispatch('on_press')                  # first free slot, right side
    assert join.slots[:2] == [('keys', 0), ('touch', 'right')]
    assert join.panels[1]['device'].text == 'Touch · right side'
    assert right.disabled and right.text == 'Player 2 · touch'
    right.dispatch('on_press')                  # side taken: nothing
    assert join.slots[2] is None
    assert join.join_touch('right') is None
    left.dispatch('on_press')
    assert join.slots[2] == ('touch', 'left') and left.disabled
    _pad(kv_game, 0, 0)                         # pads still join
    assert join.slots[3] == ('pad', 0)
    join.leave(1)                               # right side free again
    assert not right.disabled and right.text == 'Tap to join by touch'
    right.dispatch('on_press')
    assert join.slots[1] == ('touch', 'right')


def test_side_strips_are_at_the_screen_edges(kv_game):
    from kivy.core.window import Window
    join = _join(kv_game)
    join.do_layout()
    left, right = join.side_buttons['left'], join.side_buttons['right']
    assert left.x < main.dp(10)
    assert right.right > Window.width - main.dp(10)
    assert left.height == join.height
    middle = join.panels[0]['panel'].parent.parent  # panels + Back row
    assert left.right < middle.x and right.x > middle.right


def test_start_needs_two_joined_players_all_ready(kv_game):
    join = _join(kv_game)
    _press(kv_game, KEY_SPACE)                  # join
    _press(kv_game, KEY_SPACE)                  # ready, but alone
    assert kv_game.select_active
    assert 'two players' in join.message.text
    _press(kv_game, ord('k'))                   # set 2 joins as player 2
    _press(kv_game, ord('l'))                   # next colour: red
    assert kv_game.select_active
    _press(kv_game, ord('k'))                   # ready: everyone is
    assert not kv_game.select_active
    assert [s.cabin for s in kv_game.spaceships] == ['blue', 'red']
    assert kv_game.slots == [('keys', 0), ('keys', 1), None, None]
    kv_game._on_key_down(None, ord('i'))
    assert kv_game.spaceships[1].thrust and not kv_game.spaceships[0].thrust


def test_join_by_touch_buttons_only(kv_game):
    join = _join(kv_game)
    panels = join.panels
    join.side_buttons['left'].dispatch('on_press')
    join.side_buttons['right'].dispatch('on_press')
    panels[1]['next'].dispatch('on_press')
    assert kv_game.ship_colors.colors[1] == 'red'
    panels[0]['ready'].dispatch('on_press')
    panels[1]['ready'].dispatch('on_press')
    assert len(kv_game.spaceships) == 2
    assert [c.touch_buttons.side for c in kv_game.controls[:2]] == [
        'left', 'right']


def test_selection_single_player_any_input_and_second_pad(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(1)
    assert len(game.select.panels) == 1
    _press(game, ord('l'))                          # P2 key still picks
    assert game.ship_colors.colors[0] == 'green'    # free: nobody else plays
    game._on_joy_button_down(None, 5, 0)
    assert len(game.spaceships) == 1 and game.spaceships[0].cabin == 'green'


def test_multiplayer_menu_entry_opens_join_screen(kv_game):
    game = kv_game
    game.ship_colors.path = None
    _press(game, 274)                           # Multiplayer
    _press(game, KEY_ENTER)
    assert isinstance(game.select, main.JoinScreen)
    assert game.select.slots == [None] * 4      # opening it joined nobody


def test_second_gamepad_navigates_menu(kv_game):
    game = kv_game
    game._on_joy_axis(None, 0, 1, 32767)            # pad 0: down
    game._on_joy_axis(None, 0, 1, 0)
    game._on_joy_button_down(None, 1, 0)            # pad 1: activate
    assert game.select_active and isinstance(game.select, main.JoinScreen)


def test_status_text_is_turned_toward_each_player(kv_game):
    from kivy.graphics import Rotate
    game = kv_game
    game.ship_colors.path = None
    game.game_start(slots=TOUCH2)

    def angle(status):
        label = status.children[0]
        return [i.angle for i in label.canvas.before.children
                if isinstance(i, Rotate)][0]

    left, right = game.statuses
    assert angle(left) == -90       # left player faces right: text up = right
    assert angle(right) == 90       # right player faces left: text up = left
    game.game_stop()
    game.game_start(1)
    assert angle(game.statuses[0]) == 0


def test_mixed_game_status_positions_angles_and_colours(kv_game):
    from kivy.core.window import Window
    from kivy.graphics import Rotate
    game = kv_game
    game.ship_colors.path = None
    game.game_start(slots=[('keys', 0), ('touch', 'left'), ('pad', 2),
                           ('touch', 'right')])
    keys, left, pad, right = game.statuses

    def label(status):
        return status.children[-1]

    def angle(status):
        return [i.angle for i in label(status).canvas.before.children
                if isinstance(i, Rotate)][0]

    assert [s.side for s in game.statuses] == ['row', 'left', 'row', 'right']
    assert [angle(s) for s in game.statuses] == [0, -90, 0, 90]
    for status, column in ((keys, 0), (pad, 2)):
        assert label(status).center_x == pytest.approx(
            Window.width * (column + 0.5) / 4)
        assert label(status).center_y == pytest.approx(Window.height - 50)
    # just inside the player's own controls, at the middle of the side
    left_stick = game.controls[1].touch_buttons.stick
    right_stick = game.controls[3].touch_buttons.stick
    assert label(left).center_x > left_stick.right
    assert label(right).center_x < right_stick.x
    assert label(left).center_y == pytest.approx(Window.height / 2)
    for status in game.statuses:
        assert tuple(status.color[:3]) == pytest.approx(
            main.cabin_rgb(status.spaceship.cabin))


@pytest.mark.parametrize('scale', [1.0, 3.0])
def test_touch_status_never_overlaps_its_controls(kv_game, scale):
    """The turned text is one line high across; its horizontal extent must
    stay clear of the joystick and FIRE column of the same side, also when
    the controls are made bigger in the settings."""
    game = kv_game
    game.touch_settings.scale = scale
    game.game_start(slots=[('touch', 'left'), ('touch', 'right')])
    for status, controls in zip(game.statuses, game.controls):
        layout = controls.touch_buttons
        label = status.children[-1]
        label.texture_update()      # text is otherwise rendered next frame
        half = label.texture_size[1] / 2
        text_left, text_right = label.center_x - half, label.center_x + half
        assert text_right - text_left > 0
        for pad in (layout.stick, layout.fire):
            if status.side == 'left':
                assert text_left >= pad.right, (scale, status.side)
            else:
                assert text_right <= pad.x, (scale, status.side)
        # and it follows a later size change
        layout.set_scale(scale * 1.2)
        half = label.texture_size[1] / 2
        if status.side == 'left':
            assert label.center_x - half >= layout.stick.right
        else:
            assert label.center_x + half <= layout.stick.x


def test_fire_label_is_turned_toward_each_player(game, touch2):
    one, two = [c.touch_buttons for c in touch2.controls]
    for layout in (one, two):
        layout.size = (1000, 600)
    assert one.fire.text_angle == -90 and one.fire._label_turn.angle == -90
    assert two.fire.text_angle == 90 and two.fire._label_turn.angle == 90
    single = game.controls[0].touch_buttons
    single.size = (1000, 600)
    assert single.fire.text_angle == 0 and single.fire._label_turn.angle == 0
    assert tuple(one.fire._label_turn.origin[:2]) == pytest.approx(
        tuple(one.fire.center))


def test_join_strips_hidden_without_touchscreen(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.has_touch = False                      # e.g. Android TV
    game.show_ship_select(2)
    join = game.select
    for strip in join.side_buttons.values():
        assert strip.opacity == 0 and strip.disabled
    assert 'tap a side' not in join.panels[0]['empty'].text
    _press(game, KEY_SPACE)                     # keys and pads still join
    assert join.slots[0] == ('keys', 0)


def test_first_touch_shows_join_strips(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.has_touch = False
    game.show_ship_select(2)
    join = game.select
    game._on_window_touch(None, None)
    assert game.has_touch
    for strip in join.side_buttons.values():
        assert strip.opacity == 1 and not strip.disabled
    assert 'tap a side' in join.panels[1]['empty'].text
    join.side_buttons['right'].dispatch('on_press')
    assert join.slots[0] == ('touch', 'right')


def test_has_touchscreen_off_android():
    assert main.has_touchscreen() is True       # desktop: mouse clicks


from kivy.core.window import Window


def _pause_button(status):
    return next(c for c in status.children if c.__class__.__name__ == 'PauseButton')


def test_pause_button_follows_touch_controls(kv_game):
    game = kv_game
    game.game_start()
    button = _pause_button(game.spaceship_status)
    # keyboard play: no way back needed on screen; a touch shows the button
    assert button.opacity == 0 and button.disabled
    game._on_window_touch(None, None)
    assert button.opacity == 1 and not button.disabled
    game._on_key_down(None, KEY_UP)
    assert button.opacity == 0 and button.disabled


def test_single_player_pause_button_is_under_the_points(kv_game):
    game = kv_game
    game.game_start()
    game._on_window_touch(None, None)
    status = game.spaceship_status
    button = _pause_button(status)
    label = status.children[-1]
    assert button.center_x == label.center_x
    assert button.top < label.center_y - label.texture_size[1] / 2


def test_pause_button_pauses_and_main_menu_leaves(kv_game):
    game = kv_game
    game.game_start()
    game._on_window_touch(None, None)
    _pause_button(game.spaceship_status).dispatch('on_press')
    assert game.paused and not game.menu_active
    game.pause_screen.go_menu()
    game.confirm_screen.yes()
    assert game.menu_active and not game.paused


def test_touch_players_pause_buttons_are_mid_side_under_the_text(
        kv_game, start_game):
    game = start_game(slots=TOUCH2)
    left, right = game.statuses
    for status, inner in ((left, 1), (right, -1)):
        button = _pause_button(status)
        label = status.children[-1]
        assert button.opacity == 1 and not button.disabled
        assert button.center_y == label.center_y == pytest.approx(
            Window.height / 2)
        assert (button.center_x - label.center_x) * inner < 0
    _pause_button(left).dispatch('on_press')
    assert game.paused


def test_touch_controls_are_capped_on_a_small_screen():
    layout = main.ScreenButtonsLayout(size=(900, 400))
    assert layout.stick.width <= 400 * 0.4 + 1e-6
    assert layout.fire.width <= 400 * 0.25 + 1e-6
    tall = main.ScreenButtonsLayout(size=(3000, 3000))
    assert tall.stick.width == pytest.approx(main.dp(main.STICK_DP))
    assert tall.fire.width == pytest.approx(main.dp(main.FIRE_DP))


class FakeSDL:
    """Just enough of the SDL2 joystick API for PadWatcher."""
    def __init__(self):
        self.devices = []        # instance ids, index = position
        self.opened = []
        self.closed = []
        self.SDL_NumJoysticks = lambda: len(self.devices)
        self.SDL_JoystickGetDeviceInstanceID = lambda i: self.devices[i]
        self.SDL_JoystickOpen = self._open
        self.SDL_JoystickClose = self.closed.append

    def _open(self, index):
        self.opened.append(self.devices[index])
        return 1000 + self.devices[index]


class Fn:
    """A function that accepts the ctypes attributes PadWatcher sets."""
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *args):
        return self.fn(*args)


def _fake_sdl():
    sdl = FakeSDL()
    for name in ('SDL_NumJoysticks', 'SDL_JoystickGetDeviceInstanceID',
                 'SDL_JoystickOpen', 'SDL_JoystickClose'):
        setattr(sdl, name, Fn(getattr(sdl, name)))
    return sdl


def test_pad_watcher_opens_pads_connected_later():
    sdl = _fake_sdl()
    watcher = main.PadWatcher(sdl)
    watcher.poll()
    assert sdl.opened == []
    sdl.devices.append(7)            # a Bluetooth pad is switched on
    watcher.poll()
    watcher.poll()
    assert sdl.opened == [7]         # opened once, not on every poll


def test_pad_watcher_closes_gone_pads_and_reopens_them():
    sdl = _fake_sdl()
    sdl.devices.append(3)
    watcher = main.PadWatcher(sdl)
    watcher.poll()
    sdl.devices.clear()
    watcher.poll()
    assert sdl.closed == [1003]
    sdl.devices.append(4)            # reconnects under a new id
    watcher.poll()
    assert sdl.opened == [3, 4]


def test_pad_watcher_runs_on_every_platform(monkeypatch):
    # a pad unplugged and plugged in again on the desktop must come back too
    sdl = _fake_sdl()
    scheduled = []
    monkeypatch.setattr(
        main.Clock, 'schedule_interval',
        lambda callback, interval: scheduled.append((callback, interval))
        or 'event')
    assert main.start_pad_watcher(sdl) == 'event'
    (poll, interval), = scheduled
    assert interval == 0.25
    sdl.devices.append(5)            # plugged in again
    poll(0.25)
    assert sdl.opened == [5]


def test_pad_watcher_survives_garbage_collection():
    # the Clock keeps bound methods weakly: the watcher must be kept alive
    import gc
    sdl = _fake_sdl()
    event = main.start_pad_watcher(sdl)
    try:
        gc.collect()
        callback = event.get_callback()
        assert callback is not None
        sdl.devices.append(6)
        callback(0.25)
        assert sdl.opened == [6]
    finally:
        event.cancel()


def test_pad_watcher_needs_sdl(monkeypatch):
    assert main.start_pad_watcher(object()) is None   # not an SDL: no watcher
    monkeypatch.undo()
    monkeypatch.setattr(main, 'load_sdl', lambda: None)
    assert main.watch_gamepads() is None


def test_android_gamepad_buttons_do_not_leave_the_game_on_a_stick_click():
    android = main.JOY_BUTTON_ACTIONS_ANDROID
    assert android[4] == 'back' and android[6] == 'back'   # View, Start
    assert 7 not in android and 8 not in android           # stick clicks
    assert [android[b] for b in (11, 12, 13, 14)] == [
        'up', 'down', 'left', 'right']
    # desktop numbering is unchanged
    assert main.JOY_BUTTON_ACTIONS_DESKTOP[6] == 'back'
    assert main.JOY_BUTTON_ACTIONS_DESKTOP[7] == 'back'


# ---- game over: results, leaderboard, replay --------------------------

def _lose_all(game):
    for ship in list(game.spaceships):
        ship.lives = 0
        game.lose_spaceship(ship)


def _armed(screen):
    screen.armed_at = 0   # skip the input guard


def test_game_over_shows_results_with_points_and_time(kv_game):
    game = kv_game
    game.game_start()
    game.spaceships[0].points = 7
    game.elapsed = 42.5
    _lose_all(game)
    assert game.results_active
    assert not game.menu_active
    assert [(r.points, int(r.survived)) for r in game.results_screen.results] \
        == [(7, 42)]


def test_leaving_from_pause_skips_results(kv_game):
    kv_game.game_start()
    kv_game._on_key_down(None, KEY_ESC)
    assert kv_game.paused
    kv_game.pause_screen.go_menu()
    kv_game.confirm_screen.yes()
    assert kv_game.menu_active
    assert not kv_game.results_active


def test_survival_time_per_ship(kv_game):
    game = kv_game
    game.game_start(2)
    first, second = game.spaceships
    game.elapsed = 20
    first.lives = 0
    game.lose_spaceship(first)
    game.elapsed = 55
    _lose_all(game)
    got = {r.slot: r.survived for r in game.results_screen.results}
    assert got == {0: 20, 1: 55}


def test_elapsed_counts_only_while_ships_fly(kv_game):
    game = kv_game
    game.game_start()
    game.update(0.5)
    game.update(0.25)
    assert game.elapsed == pytest.approx(0.75)


def _scores(entries):
    """Leaderboard entries without their ids."""
    return [{k: v for k, v in e.items() if k != 'id'} for e in entries]


def test_leaderboard_orders_caps_and_persists(tmp_path):
    path = str(tmp_path / 'lb.json')
    board = main.Leaderboard(path)
    for points, seconds in [(5, 10), (30, 40), (12, 20), (12, 50)]:
        assert board.add(points, seconds)
    assert [(e['points'], e['seconds']) for e in board.entries] == [
        (30, 40), (12, 50), (12, 20), (5, 10)]
    for i in range(20):
        board.add(100 + i, 1)
    assert len(board.entries) == main.LEADERBOARD_SIZE
    assert main.Leaderboard(path).entries == board.entries


def test_leaderboard_tolerates_corrupt_file(tmp_path):
    path = tmp_path / 'lb.json'
    path.write_text('{nope')
    assert _scores(main.Leaderboard(str(path)).entries) == []
    path.write_text('{"entries": [{"points": "x"}, {"points": 3, "seconds": 9}]}')
    assert _scores(main.Leaderboard(str(path)).entries) == [
        {'name': 'Player', 'points': 3, 'seconds': 9}]


def test_leaderboard_reports_unwritable_file(tmp_path):
    blocked = tmp_path / 'file'
    blocked.write_text('x')
    board = main.Leaderboard(str(blocked / 'lb.json'))
    assert board.add(1, 1) is False
    assert len(board.entries) == 1


def test_save_score_once_saves_top_player(kv_game, tmp_path):
    game = kv_game
    game.leaderboard = main.Leaderboard(str(tmp_path / 'lb.json'))
    game.game_start(slots=[('keys', 0), ('keys', 1), ('pad', 0), None])
    for ship, points in zip(game.spaceships, (3, 9, 4)):
        ship.points = points
    game.elapsed = 30
    _lose_all(game)
    screen = game.results_screen
    _armed(screen)
    screen.save_score()
    assert game.name_active and not game.results_active
    assert game.name_screen.ids.title.text == 'Nickname of player 2'
    game.name_screen.ids.field.text = '  Ann  '
    game.name_screen.accept()
    assert game.results_active and screen.saved
    screen.save_score()    # only once
    assert not game.name_active
    assert _scores(game.leaderboard.entries) == [
        {'name': 'Ann', 'points': 9, 'seconds': 30}]


def test_results_ignore_presses_right_after_game_over(kv_game):
    game = kv_game
    game.game_start()
    _lose_all(game)
    game.results_screen.play_again()
    assert game.results_active   # still guarded


def test_play_again_keeps_configuration(kv_game):
    game = kv_game
    slots = [('keys', 0), None, ('pad', 0), ('touch', 'left')]
    colors = ['red', 'green', 'blue', 'yellow']
    game.game_start(slots=slots, colors=colors)
    _lose_all(game)
    _armed(game.results_screen)
    game.results_screen.play_again()
    assert not game.results_active
    assert game.slots == slots
    assert [s.cabin for s in game.spaceships] == ['red', 'blue', 'yellow']
    assert len(game.spaceships) == 3


def test_results_main_menu_and_back(kv_game):
    game = kv_game
    game.game_start()
    _lose_all(game)
    _armed(game.results_screen)
    game.results_screen.go_menu()
    assert game.menu_active and not game.results_active
    game.game_start()
    _lose_all(game)
    game._on_key_down(None, KEY_ESC)
    assert game.menu_active and not game.results_active


def test_leaderboard_screen_from_menu(kv_game):
    game = kv_game
    game.leaderboard = main.Leaderboard()
    game.show_leaderboard()
    assert game.leaderboard_active
    game._on_key_down(None, KEY_ESC)
    assert game.menu_active and not game.leaderboard_active


# ---- pause ------------------------------------------------------------

def _asteroid(game, pos=(300, 300), angle=0):
    asteroid = Asteroid(angle=angle)
    asteroid.pos = pos
    game.add_widget(asteroid)
    game.asteroids.append(asteroid)
    return asteroid


def test_pause_freezes_the_world_and_resume_continues(kv_game):
    game = kv_game
    game.game_start()
    ship = game.spaceships[0]
    asteroid = _asteroid(game)
    ship.shot()
    shot = game.shots[0]
    game.pause()

    assert game.paused and game.pause_screen in game.children
    assert [b.text for b in game.pause_screen.buttons] == [
        'Continue', 'Main menu']
    seen = (tuple(asteroid.pos), tuple(shot.pos), game.elapsed)
    from kivy.clock import Clock
    for _ in range(5):
        Clock.tick()
    assert (tuple(asteroid.pos), tuple(shot.pos), game.elapsed) == seen

    game.resume()
    assert not game.paused and not hasattr(game, 'pause_screen')
    game.update(1 / 60)
    assert tuple(asteroid.pos) != seen[0]
    assert game.elapsed > seen[2]


def test_pause_stops_new_asteroids_and_ignores_ship_input(kv_game):
    game = kv_game
    game.game_start()
    game.pause()
    ship = game.spaceships[0]
    _press(game, 273)                  # up: moves the pause selection
    assert not ship.thrust
    assert not game.controls[0].held


def test_pause_keyboard_navigation_and_back_continues(kv_game):
    game = kv_game
    game.game_start()
    game.pause()
    _press(game, 274)                  # down: Main menu
    assert game.pause_screen.selected == 1
    _press(game, KEY_ESC)              # Back: Continue
    assert not game.paused and game.spaceships

    game.pause()
    _press(game, 274)
    _press(game, KEY_ENTER)            # Main menu: asks first
    assert game.paused and not game.menu_active
    _press(game, 273)                  # up: Yes
    _press(game, KEY_ENTER)
    assert game.menu_active and not game.paused
    assert game.spaceships == []
    assert not hasattr(game, 'pause_screen')


def test_resume_does_not_leave_a_ship_thrusting(kv_game):
    game = kv_game
    game.game_start()
    game.controls[0].press('up')
    assert game.spaceships[0].thrust
    game.pause()
    assert not game.spaceships[0].thrust
    game.resume()
    assert not game.spaceships[0].thrust


def test_touch_players_get_a_pause_button(kv_game):
    game = kv_game
    game.game_start(slots=[('touch', 'left'), ('touch', 'right')])
    game.update(0)
    assert all(s.show_menu for s in game.statuses)
    buttons = [w for s in game.statuses for w in s.children
               if type(w).__name__ == 'PauseButton']
    assert len(buttons) == 2 and all(b.text == 'Pause' for b in buttons)
    game.pause()
    assert not any(s.show_menu for s in game.statuses)
    game.resume()
    assert all(s.show_menu for s in game.statuses)


def test_pause_button_goes_away_with_its_dead_player(kv_game):
    game = kv_game
    game.game_start(slots=[('touch', 'left'), ('touch', 'right'),
                           ('keys', 0), None])
    game.update(0)
    dead, alive = game.spaceships[0], game.spaceships[1]
    status = {s.spaceship: s for s in game.statuses}
    assert status[dead].show_menu and status[alive].show_menu
    dead.lives = 0
    game.lose_spaceship(dead)
    assert not status[dead].show_menu          # the block stays, the button goes
    assert status[alive].show_menu
    game.pause()
    game.resume()
    assert not status[dead].show_menu and status[alive].show_menu


def _name_entry(game, tmp_path):
    game.leaderboard = main.Leaderboard(str(tmp_path / 'lb.json'))
    game.game_start()
    game.spaceships[0].points = 5
    _lose_all(game)
    _armed(game.results_screen)
    game.results_screen.save_score()
    assert game.name_active


def test_nickname_prefilled_remembered_and_limited(kv_game, tmp_path):
    game = kv_game
    _name_entry(game, tmp_path)
    assert game.name_screen.ids.field.text == 'Player'
    assert game.name_screen.ids.title.text == 'Your nickname'
    game.name_screen.ids.field.text = 'Anna'
    game.name_screen.accept()
    again = main.Leaderboard(str(tmp_path / 'lb.json'))
    assert again.last_name == 'Anna'
    assert main.clean_name('   ') == 'Player'
    assert main.clean_name('x' * 30) == 'x' * 12
    game.results_screen.saved = False
    game.results_screen.save_score()
    assert game.name_screen.ids.field.text == 'Anna'


def test_cancel_name_entry_keeps_score_unsaved(kv_game, tmp_path):
    game = kv_game
    _name_entry(game, tmp_path)
    game._on_key_down(None, KEY_ESC)
    assert game.results_active and not game.name_active
    assert not game.results_screen.saved
    assert game.leaderboard.entries == []


def test_game_keys_do_not_act_while_typing_nickname(kv_game, tmp_path):
    game = kv_game
    _name_entry(game, tmp_path)
    for key in (273, 274, 32, 13):    # up, down, space, enter
        game._on_key_down(None, key)
        game._on_key_up(None, key)
    assert game.name_active
    assert game.leaderboard.entries == []


def test_gamepad_saves_prefilled_nickname(kv_game, tmp_path):
    game = kv_game
    _name_entry(game, tmp_path)
    game._on_joy_button_down(None, 0, 0)     # A: Save is selected first
    game._on_joy_button_up(None, 0, 0)
    assert game.results_active
    assert _scores(game.leaderboard.entries) == [
        {'name': 'Player', 'points': 5, 'seconds': 0}]


def test_leaderboard_reads_files_without_names(tmp_path):
    path = tmp_path / 'lb.json'
    path.write_text('{"entries": [{"points": 3, "seconds": 9}]}')
    assert _scores(main.Leaderboard(str(path)).entries) == [
        {'name': 'Player', 'points': 3, 'seconds': 9}]


def test_leaderboard_version_1_file_gets_ids_same_order(tmp_path):
    path = tmp_path / 'lb.json'
    path.write_text(json.dumps({'version': 1, 'last_name': 'Ann', 'entries': [
        {'name': 'Ann', 'points': 30, 'seconds': 40},
        {'name': 'Bob', 'points': 12, 'seconds': 50},
        {'name': 'Cy', 'points': 12, 'seconds': 50}]}))
    board = main.Leaderboard(str(path))
    assert _scores(board.entries) == [
        {'name': 'Ann', 'points': 30, 'seconds': 40},
        {'name': 'Bob', 'points': 12, 'seconds': 50},
        {'name': 'Cy', 'points': 12, 'seconds': 50}]
    ids = [e['id'] for e in board.entries]
    assert len(set(ids)) == 3 and all(main.Leaderboard.valid_id(i) for i in ids)
    assert board.last_name == 'Ann'
    board.save()
    data = json.loads(path.read_text())
    assert data['version'] == 2
    assert [e['id'] for e in main.Leaderboard(str(path)).entries] == ids


def test_leaderboard_merge_adds_once_and_keeps_best(tmp_path):
    path = str(tmp_path / 'lb.json')
    board = main.Leaderboard(path)
    board.add(12, 20, 'Host')
    phone = [main.Leaderboard.new_entry(30, 61, 'Ann'),
             main.Leaderboard.new_entry(5, 9, 'Bob')]
    assert board.merge(phone)
    assert [e['name'] for e in board.entries] == ['Ann', 'Host', 'Bob']
    assert not board.merge(phone)               # same ids: nothing new
    assert not board.merge([dict(e) for e in board.entries])
    assert len(board.entries) == 3
    again = main.Leaderboard(path)              # kept after a restart
    assert [e['name'] for e in again.entries] == ['Ann', 'Host', 'Bob']
    assert again.last_name == 'Host'            # merging never changes it


def test_leaderboard_merge_skips_invalid_entries(tmp_path):
    board = main.Leaderboard(str(tmp_path / 'lb.json'))
    assert not board.merge([
        {'id': 'zz!', 'name': 'Bad', 'points': 1, 'seconds': 1},
        {'name': 'No id', 'points': 1, 'seconds': 1},
        {'id': 'ab', 'name': 'Neg', 'points': -1, 'seconds': 1},
        {'id': 'cd', 'name': 'Str', 'points': '9', 'seconds': 1},
        {'id': 'ce', 'name': 5, 'points': 1, 'seconds': 1},
        {'id': '0' * 40, 'name': 'Long id', 'points': 1, 'seconds': 1},
        'junk'])
    assert board.entries == []
    assert board.merge([{'id': 'ef', 'name': '  ' + 'x' * 20, 'points': 2,
                         'seconds': 3}])
    assert _scores(board.entries) == [
        {'name': 'x' * 12, 'points': 2, 'seconds': 3}]


def test_leaderboard_merge_beyond_ten_keeps_ten(tmp_path):
    board = main.Leaderboard(str(tmp_path / 'lb.json'))
    for i in range(10):
        board.add(100 + i, 1)
    assert not board.merge([main.Leaderboard.new_entry(1, 1, 'Low')])
    assert board.merge([main.Leaderboard.new_entry(500, 1, 'Top')])
    assert len(board.entries) == 10 and board.entries[0]['name'] == 'Top'


def test_leaderboard_version_2_file_readable_by_version_1_logic(tmp_path):
    # what the previous app version did with the file: only name, points
    # and seconds of each entry are read, extra fields are ignored
    path = tmp_path / 'lb.json'
    board = main.Leaderboard(str(path))
    board.add(7, 8, 'Ann')
    data = json.loads(path.read_text())
    old = [{'name': main.clean_name(e.get('name', main.DEFAULT_NAME)),
            'points': e['points'], 'seconds': e['seconds']}
           for e in data['entries'] if isinstance(e, dict)
           and all(type(e.get(k)) is int and e[k] >= 0
                   for k in ('points', 'seconds'))]
    assert old == [{'name': 'Ann', 'points': 7, 'seconds': 8}]


def test_pause_stops_the_scrolling_background(kv):
    from kivy.clock import Clock
    game = SpacePilgrimGame()    # built after the kv: it has the background
    try:
        game.game_stop()
        game.game_start()
        background = game.background_widget()
        assert background is not None
        Clock.tick()
        game.pause()
        at = background.shift
        for _ in range(5):
            Clock.tick()
        assert background.shift == at
        game.resume()
        assert background.animation is not None
    finally:
        game.frame_schedule.cancel()
        game.asteroid_schedule.cancel()


def _ask_to_leave(game):
    game.game_start()
    game.pause()
    game.pause_screen.go_menu()


def test_main_menu_asks_before_leaving(kv_game):
    game = kv_game
    _ask_to_leave(game)
    assert game.paused and game.spaceships and not game.menu_active
    assert game.confirm_screen in game.children
    assert game.pause_screen not in game.children
    assert [b.text for b in game.confirm_screen.buttons] == ['Yes', 'No']


def test_no_returns_to_pause_screen_with_game_kept(kv_game):
    game = kv_game
    _ask_to_leave(game)
    ships = list(game.spaceships)
    game.confirm_screen.no()
    assert not hasattr(game, 'confirm_screen')
    assert game.paused and game.pause_screen in game.children
    assert game.spaceships == ships and not game.menu_active


def test_escape_closes_only_the_popup(kv_game):
    game = kv_game
    _ask_to_leave(game)
    _press(game, KEY_ESC)
    assert game.paused and game.spaceships and not game.menu_active
    assert not hasattr(game, 'confirm_screen')
    assert game.pause_screen in game.children


def test_fire_on_default_keeps_the_game(kv_game):
    game = kv_game
    _ask_to_leave(game)
    _press(game, KEY_ENTER)
    assert game.paused and game.spaceships and not game.menu_active
    assert game.pause_screen in game.children


def test_yes_leaves_without_results(kv_game):
    game = kv_game
    _ask_to_leave(game)
    game.confirm_screen.yes()
    assert game.menu_active and not game.paused
    assert not game.results_active and not hasattr(game, 'confirm_screen')


def _press_exit(game):
    exit_button = [b for b in game.menu.buttons if b.text == 'Exit'][0]
    exit_button.dispatch('on_press')


def _fake_app(monkeypatch):
    stopped = []
    app = type('FakeApp', (), {'stop': lambda self: stopped.append(1)})()
    monkeypatch.setattr(main.App, 'get_running_app',
                        staticmethod(lambda: app))
    return stopped


def test_exit_asks_before_quitting(kv_game, monkeypatch):
    game = kv_game
    stopped = _fake_app(monkeypatch)
    _press_exit(game)
    assert not stopped and not game.menu_active
    assert game.confirm_screen.kind == 'exit'
    assert [b.text for b in game.confirm_screen.buttons] == ['Yes', 'No']
    _press(game, KEY_ENTER)            # default is No: back to the menu
    assert not stopped and game.menu_active
    assert not hasattr(game, 'confirm_screen')


def test_exit_escape_closes_popup_and_yes_quits(kv_game, monkeypatch):
    game = kv_game
    stopped = _fake_app(monkeypatch)
    _press_exit(game)
    _press(game, KEY_ESC)
    assert not stopped and game.menu_active and not game.spaceships
    _press_exit(game)
    _press(game, 273)                  # up: Yes
    _press(game, KEY_ENTER)
    assert stopped


# ---- four touch seats on a big screen ----------------------------------

def _px(width_cm, height_cm, dpi=160):
    return (width_cm / 2.54 * dpi, height_cm / 2.54 * dpi)


@pytest.mark.parametrize('cm_size, four', [
    ((21, 13), True),       # 10" tablet
    ((15, 10), True),       # just big enough
    ((15, 7), False),       # phone
    ((15.5, 8.7), False),   # 7" tablet
    ((14, 12), False),      # too narrow
])
@pytest.mark.parametrize('dpi', [160, 320])
def test_four_seats_need_a_big_screen(cm_size, four, dpi):
    size = _px(*cm_size, dpi)
    assert four_seat_screen(size, (dpi, dpi)) is four
    # also when the size arrives the other way round
    assert four_seat_screen(size[::-1], (dpi, dpi)) is four


def test_four_seats_measure_each_axis():
    # 21 x 13 cm in pixels but a screen twice as dense across: 21 x 6.5 cm
    assert not four_seat_screen(_px(21, 13), (160, 320))


def test_touch_seats_follow_the_screen(monkeypatch):
    assert main.touch_seats() == ('left', 'right')
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    assert main.touch_seats() == ('left', 'right', 'top', 'bottom')


def test_screen_dpi_off_android_is_kivys():
    assert main.screen_dpi() == (main.Metrics.dpi, main.Metrics.dpi)


TOUCH4 = [('touch', 'left'), ('touch', 'right'), ('touch', 'top'),
          ('touch', 'bottom')]


@pytest.fixture
def touch4(start_game):
    return start_game(slots=TOUCH4)


def _overlap(a, b):
    return (a.x < b.right and b.x < a.right and a.y < b.top and b.y < a.top)


@pytest.mark.parametrize('side, forward, left, right', [
    # screen directions (dx, dy) of "away from me", "my left", "my right"
    ('top', (0, -0.9), (0.9, 0), (-0.9, 0)),
    ('bottom', (0, 0.9), (-0.9, 0), (0.9, 0)),
    ('left', (0.9, 0), (0, 0.9), (0, -0.9)),
    ('right', (-0.9, 0), (0, -0.9), (0, 0.9)),
])
def test_edge_stick_is_turned_toward_the_seat(touch4, side, forward, left,
                                              right):
    controls = touch4.controls[[d[1] for d in TOUCH4].index(side)]
    layout, ship = controls.touch_buttons, controls.spaceship
    layout.size = (1000, 600)
    assert layout.stick.angle == main.SEAT_ANGLES[side]
    assert layout.fire.text_angle == main.SEAT_ANGLES[side]
    for pos, thrust, rotation in ((forward, True, 0), (left, False, 3),
                                  (right, False, -3)):
        touch, consumed = _touch_down(layout, _stick_pos(layout, *pos))
        assert consumed
        assert (ship.thrust, ship.angle_rotation) == (thrust, rotation), pos
        _release(touch, layout.stick)
        assert not ship.thrust and ship.angle_rotation == 0


def test_top_stick_marks_point_to_the_seat_directions(touch4):
    top = touch4.controls[2].touch_buttons
    top.size = (1000, 600)
    stick = top.stick
    up_mark = stick._marks[0].points            # the thrust mark
    assert up_mark[1] < stick.center_y - stick.width * 0.3   # toward the centre
    assert abs(up_mark[0] - stick.center_x) < 1e-6


@pytest.mark.parametrize('size', [_px(15, 10), _px(21, 13), (1920, 1080),
                                  _px(10, 15), (1080, 1920)])
@pytest.mark.parametrize('scale', [0.5, 1.0, 4.0])
@pytest.mark.parametrize('free_corners', [False, True])
def test_four_touch_sets_share_the_edges(touch4, scale, size, free_corners):
    layouts = [c.touch_buttons for c in touch4.controls]
    assert all(layout.edges for layout in layouts)
    for layout in layouts:
        layout.size = size
        layout.set_scale(scale)
        layout.free_corners = free_corners   # a keyboard player is in a corner
    w, h = size
    margin = main.dp(main.MARGIN_DP)
    corner = main.dp(main.CORNER_DP)
    pads = [pad for layout in layouts for pad in (layout.stick, layout.fire)]
    for pad in pads:
        assert pad.x >= margin - 1e-6 and pad.right <= w - margin + 1e-6
        assert pad.y >= margin - 1e-6 and pad.top <= h - margin + 1e-6
        if free_corners:
            assert not ((pad.x < corner or pad.right > w - corner)
                        and (pad.y < corner or pad.top > h - corner)), pad
    for i, a in enumerate(pads):
        for b in pads[i + 1:]:
            assert not _overlap(a, b), (scale, size)
    # one size for everybody
    assert len({round(layout.stick.width, 6) for layout in layouts}) == 1
    assert len({round(layout.fire.width, 6) for layout in layouts}) == 1
    # under the left hand the joystick, under the right hand FIRE
    left, right, top, bottom = layouts
    assert left.stick.y > left.fire.top and left.stick.x == pytest.approx(margin)
    assert right.fire.y > right.stick.top
    assert w - right.stick.right == pytest.approx(margin)
    assert top.fire.right < top.stick.x
    assert h - top.stick.top == pytest.approx(margin)
    assert bottom.stick.right < bottom.fire.x
    assert bottom.stick.y == pytest.approx(margin)
    # the same distance between the two controls on every edge, the same
    # span around the middle of the edge
    between = left.stick.y - left.fire.top
    assert right.fire.y - right.stick.top == pytest.approx(between)
    assert bottom.fire.x - bottom.stick.right == pytest.approx(between)
    assert top.stick.x - top.fire.right == pytest.approx(between)
    assert (left.fire.y + left.stick.top) / 2 == pytest.approx(h / 2)
    assert (bottom.stick.x + bottom.fire.right) / 2 == pytest.approx(w / 2)
    assert (top.fire.x + top.stick.right) / 2 == pytest.approx(w / 2)


def test_large_controls_shrink_to_fit_four_seats(touch4):
    layout = touch4.controls[0].touch_buttons
    layout.size = _px(15, 10)
    layout.set_scale(1.0)
    normal = layout.stick.width
    layout.set_scale(4.0)
    assert normal <= layout.stick.width < normal * 4


@pytest.mark.parametrize('size', [_px(21, 13), (1920, 1080)])
def test_wide_screen_puts_side_controls_in_the_corners(touch4, size):
    """The top and bottom pairs sit around the middle of the long edges, so
    on a wide screen the left and right ones reach the corners."""
    layouts = [c.touch_buttons for c in touch4.controls]
    for layout in layouts:
        layout.size = size
    left, right, top, bottom = layouts
    w, h = size
    margin = main.dp(main.MARGIN_DP)
    assert left.fire.y == pytest.approx(margin)
    assert left.stick.top == pytest.approx(h - margin)
    assert right.stick.y == pytest.approx(margin)
    assert right.fire.top == pytest.approx(h - margin)
    # the top and bottom pairs as far apart, around the middle of the edge
    assert bottom.stick.x == pytest.approx(w / 2 - (h / 2 - margin))
    assert top.fire.x == pytest.approx(w / 2 - (h / 2 - margin))


@pytest.mark.parametrize('size', [_px(13, 21), (1080, 1920)])
def test_tall_screen_puts_top_and_bottom_controls_in_the_corners(touch4,
                                                                 size):
    """Turned upright, the same as a wide screen turned a quarter: the top
    and bottom controls reach the corners, the left and right pairs sit
    around the middle of the long edges."""
    layouts = [c.touch_buttons for c in touch4.controls]
    for layout in layouts:
        layout.size = size
    left, right, top, bottom = layouts
    w, h = size
    margin = main.dp(main.MARGIN_DP)
    assert bottom.stick.x == pytest.approx(margin)
    assert bottom.fire.right == pytest.approx(w - margin)
    assert top.fire.x == pytest.approx(margin)
    assert top.stick.right == pytest.approx(w - margin)
    assert left.fire.y == pytest.approx(h / 2 - (w / 2 - margin))
    assert right.stick.y == pytest.approx(h / 2 - (w / 2 - margin))


def test_keyboard_player_keeps_a_corner_free(start_game):
    game = start_game(slots=[('touch', 'left'), ('touch', 'top'),
                             ('keys', 0), None])
    layout = game.controls[0].touch_buttons
    assert layout.free_corners
    layout.size = (1920, 1080)
    corner = main.dp(main.CORNER_DP)
    assert layout.fire.y >= corner and layout.stick.top <= 1080 - corner
    touch4 = start_game(slots=TOUCH4)
    assert not any(c.touch_buttons.free_corners for c in touch4.controls)


def test_left_and_right_touch_players_keep_the_corners(touch2):
    assert not any(c.touch_buttons.edges for c in touch2.controls)


@pytest.mark.parametrize('seat', ['top', 'bottom'])
def test_top_or_bottom_seat_frees_the_corners(start_game, seat):
    game = start_game(slots=[('touch', 'left'), ('touch', seat),
                             ('keys', 0), None])
    left, other, keys = game.controls[:3]
    assert left.touch_buttons.edges and other.touch_buttons.edges
    assert other.touch_buttons.side == seat
    assert keys.touch == 'off'


@pytest.fixture(params=['landscape', 'portrait'])
def window_15x10(request):
    """A 15 x 10 cm tablet screen (160 dpi, so dp are pixels), held either
    way round."""
    from kivy.core.window import Window
    old = Window.size
    size = tuple(round(v) for v in _px(15, 10))
    Window.size = size if request.param == 'landscape' else size[::-1]
    yield Window.size
    Window.size = old


def _box(center, width, height):
    cx, cy = center
    return (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)


def _boxes_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _pad_box(pad):
    return (pad.x, pad.y, pad.right, pad.top)


def _status_boxes(status):
    """Screen boxes of the turned lives and points and of the Pause button."""
    label = status.ids.text_label
    label.texture_update()      # text is otherwise rendered next frame
    tw, th = label.texture_size
    if status.side in ('left', 'right'):
        tw, th = th, tw
    pause = status.ids.pause
    return (_box(label.center, tw, th),
            _box(pause.center, pause.width, pause.height))


@pytest.mark.parametrize('scale', [0.5, 1.0, 3.0, 4.0])
def test_four_touch_status_blocks_overlap_nothing(kv_game, window_15x10,
                                                  scale):
    game = kv_game
    game.touch_settings.scale = scale
    game.game_start(slots=TOUCH4)
    w, h = window_15x10
    for status in game.statuses:
        status.spaceship.points = 12345        # the longest text in practice
    pads = [_pad_box(pad) for c in game.controls
            for pad in (c.touch_buttons.stick, c.touch_buttons.fire)]
    blocks = []
    for status, controls in zip(game.statuses, game.controls):
        text, pause = _status_boxes(status)
        stick = controls.touch_buttons.stick
        side = status.side
        assert status.show_menu
        # at the middle of the edge, just inside the player's controls, and
        # the Pause button on the edge side of the text
        label = status.ids.text_label
        if side in ('left', 'right'):
            assert label.center_y == pytest.approx(h / 2)
        else:
            assert label.center_x == pytest.approx(w / 2)
        inner = {'left': text[0] >= stick.right, 'right': text[2] <= stick.x,
                 'top': text[3] <= stick.y, 'bottom': text[1] >= stick.top}
        assert inner[side], (scale, side)
        dx, dy = status.PAUSE_DIRECTIONS[side]
        assert ((status.ids.pause.center_x - label.center_x) * dx
                + (status.ids.pause.center_y - label.center_y) * dy) > 0
        for box in (text, pause):
            assert 0 <= box[0] and box[2] <= w and 0 <= box[1] and box[3] <= h
            for pad in pads:
                assert not _boxes_overlap(box, pad), (scale, side)
        blocks += [text, pause]
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            assert not _boxes_overlap(a, b), scale


def test_top_and_bottom_status_follow_a_later_scale_change(kv_game,
                                                           window_15x10):
    game = kv_game
    game.game_start(slots=TOUCH4)
    for status, controls in list(zip(game.statuses, game.controls))[2:]:
        layout = controls.touch_buttons
        layout.set_scale(0.6)
        text, _ = _status_boxes(status)
        if status.side == 'top':
            assert text[3] <= layout.stick.y
            assert text[3] > layout.stick.y - main.dp(20)
        else:
            assert text[1] >= layout.stick.top
            assert text[1] < layout.stick.top + main.dp(20)


def test_top_and_bottom_status_read_from_their_seat(kv_game):
    from kivy.graphics import Rotate
    game = kv_game
    game.game_start(slots=TOUCH4)

    def angles(widget):
        return [i.angle for i in widget.canvas.before.children
                if isinstance(i, Rotate)]
    for status in game.statuses:
        expected = main.SEAT_ANGLES[status.side]
        assert angles(status.ids.text_label) == [expected]
        assert angles(status.ids.pause) == [expected]


@pytest.mark.parametrize('scale', [0.5, 1.0, 4.0])
def test_keyboard_player_with_a_top_seat_sits_in_a_corner(kv_game,
                                                          window_15x10,
                                                          scale):
    game = kv_game
    game.touch_settings.scale = scale
    game.game_start(slots=[('touch', 'top'), ('touch', 'left'), ('keys', 0),
                           None])
    top, left, keys = game.statuses
    assert keys.side == 'corner' and keys.column == 2
    assert not keys.show_menu
    keys.spaceship.points = 12345
    w, h = window_15x10
    text, _ = _status_boxes(keys)
    corner = main.dp(main.CORNER_DP)
    assert text[0] >= 0 and text[1] >= 0          # bottom-left corner
    assert text[2] <= corner and text[3] <= corner
    pads = [_pad_box(pad) for c in game.controls[:2]
            for pad in (c.touch_buttons.stick, c.touch_buttons.fire)]
    others = [box for s in (top, left) for box in _status_boxes(s)]
    for box in pads + others:
        assert not _boxes_overlap(text, box), scale


def test_keyboard_and_gamepad_corners_follow_player_order(kv_game,
                                                         window_15x10):
    game = kv_game
    game.game_start(slots=[('keys', 0), ('touch', 'bottom'), ('pad', 0),
                           ('keys', 1)])
    w, h = window_15x10
    one, _, three, four = game.statuses
    assert [s.side for s in game.statuses] == [
        'corner', 'bottom', 'corner', 'corner']
    half = main.dp(main.CORNER_DP) / 2
    assert tuple(one.ids.text_label.center) == pytest.approx((half, h - half))
    assert tuple(three.ids.text_label.center) == pytest.approx((half, half))
    assert tuple(four.ids.text_label.center) == pytest.approx((w - half, half))
    assert one.ids.text_label.text == 'Lives 3\nPoints 0'


@pytest.fixture
def join4(kv_game, window_15x10, monkeypatch):
    """The join screen of a big screen: a touch seat at every edge."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    join = _join(kv_game)
    join.do_layout()
    for child in join.children:
        if hasattr(child, 'do_layout'):
            child.do_layout()
    return join


def test_join_strip_labels_read_from_their_seat(join4):
    angles = {side: strip._turn.angle
              for side, strip in join4.side_buttons.items()}
    assert angles == {'left': -90, 'right': 90, 'top': 180, 'bottom': 0}
    top = join4.side_buttons['top']
    assert top._label.width > top._label.height      # runs along the strip
    left = join4.side_buttons['left']
    assert left._label.width > left._label.height    # turned a quarter


def test_four_join_strips_are_at_the_screen_edges(join4, window_15x10):
    w, h = window_15x10
    strips = join4.side_buttons
    assert set(strips) == {'left', 'right', 'top', 'bottom'}
    left, right, top, bottom = (strips[s] for s in
                                ('left', 'right', 'top', 'bottom'))
    assert left.x < main.dp(10) and right.right > w - main.dp(10)
    assert top.top > h - main.dp(10) and bottom.y < main.dp(10)
    assert left.height == join4.height and top.width > top.height
    # top and bottom between the side strips, the panels in the middle
    assert left.right < top.x and top.right < right.x
    middle = join4.panels[0]['panel'].parent.parent  # panels + Back row
    middle.parent.do_layout()
    assert bottom.top < middle.y and middle.top < top.y
    assert left.right < middle.x and middle.right < right.x
    assert 'tap an edge' in join4.panels[0]['empty'].text


def test_four_players_join_by_touch_and_start(join4):
    game = join4.parent
    for side in ('top', 'left', 'bottom', 'right'):
        join4.side_buttons[side].dispatch('on_press')
    assert join4.slots == [('touch', 'top'), ('touch', 'left'),
                           ('touch', 'bottom'), ('touch', 'right')]
    assert join4.panels[0]['device'].text == 'Touch · top side'
    assert join4.panels[2]['device'].text == 'Touch · bottom side'
    for strip in join4.side_buttons.values():
        assert strip.disabled and strip.text.endswith('· touch')
    assert join4.join_touch('top') is None
    for slot in range(4):
        join4.toggle_ready(slot)
    assert not game.select_active
    assert [c.touch_buttons.side for c in game.controls] == [
        'top', 'left', 'bottom', 'right']
    assert all(c.touch_buttons.edges and c.touch_buttons.active
               for c in game.controls)


def test_four_join_strips_hidden_without_touchscreen(kv_game, monkeypatch):
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    game = kv_game
    game.ship_colors.path = None
    game.has_touch = False
    game.show_ship_select(2)
    join = game.select
    assert len(join.side_buttons) == 4
    for strip in join.side_buttons.values():
        assert strip.opacity == 0 and strip.disabled
    game._on_window_touch(None, None)
    for strip in join.side_buttons.values():
        assert strip.opacity == 1 and not strip.disabled
    join.side_buttons['bottom'].dispatch('on_press')
    assert join.slots[0] == ('touch', 'bottom')


def test_phone_join_screen_keeps_two_strips(kv_game):
    join = _join(kv_game)
    assert set(join.side_buttons) == {'left', 'right'}
    assert 'tap a side' in join.panels[0]['empty'].text
    assert join.join_touch('top') is None and join.joined == []


# ---- gamepad button maps, per pad ------------------------------------------

class FakePads(main.PadIdentity):
    """Pads known to the game: stick id -> (identity, name, axis values)."""

    def __init__(self, pads):
        super().__init__(None)
        self.pads = pads

    def _devices(self):
        return [(stick, ident, name)
                for stick, (ident, name, _) in self.pads.items()]

    def _axis_values(self, instance):
        return dict(self.pads[instance][2])


PAD_X = ('guid-x|Pad X', 'Pad X')
PAD_Z = ('guid-z|Pad Z', 'Pad Z')


def fake_pads(**sticks):
    """fake_pads(s7=(PAD_X, {axes})) style helper: {stick: spec}."""
    return FakePads({int(k[1:]): (v[0][0], v[0][1], v[1])
                     for k, v in sticks.items()})


def test_joy_button_tables_split_default_and_fixed():
    android = main.JOY_BUTTON_ACTIONS_ANDROID
    desktop = main.JOY_BUTTON_ACTIONS_DESKTOP
    assert main.JOY_DEFAULT_BUTTONS == {'fire': [0, 2], 'up': [1, 3]}
    assert main.JOY_FIXED_ACTIONS_DESKTOP == {6: 'back', 7: 'back'}
    assert set(main.JOY_FIXED_ACTIONS_ANDROID) == {4, 6, 11, 12, 13, 14}
    assert desktop == {0: 'fire', 2: 'fire', 1: 'up', 3: 'up',
                       6: 'back', 7: 'back'}
    assert android[0] == 'fire' and android[13] == 'left'
    assert main.JOY_BUTTON_ACTIONS in (android, desktop)
    assert main.JOY_FIXED_ACTIONS in (main.JOY_FIXED_ACTIONS_ANDROID,
                                      main.JOY_FIXED_ACTIONS_DESKTOP)


def test_pad_button_names():
    assert [main.pad_button_name(b) for b in (0, 1, 2, 3)] == list('ABXY')
    assert main.pad_button_name(9) == 'Button 9'


def test_pad_identity_without_sdl_knows_nothing():
    pads = main.PadIdentity(None)
    assert pads.identity(0) is None
    assert pads.connected() == []
    assert pads.axes('anything') == {}


def test_pad_identity_answers_from_devices():
    pads = fake_pads(s7=(PAD_X, {4: -1.0}), s3=(PAD_Z, {}),
                     s8=(PAD_X, {4: 0.0}))
    assert pads.identity(7) == PAD_X
    assert pads.identity(3) == PAD_Z
    assert pads.identity(99) is None
    # one entry per model, in connection order
    assert pads.connected() == [PAD_X, PAD_Z]
    assert pads.axes(PAD_X[0]) == {4: -1.0}
    assert pads.axes('nope') == {}


def test_pad_identity_survives_a_broken_sdl():
    class Broken:
        def __getattr__(self, name):
            raise AttributeError(name)

    assert main.PadIdentity(Broken()).sdl is None

    pads = main.PadIdentity(None)
    pads.sdl = object()           # calls fail: nothing is known
    assert pads.connected() == []
    assert pads._axis_values(0) == {}


def test_pad_identity_on_the_real_sdl_does_not_crash():
    pads = main.PadIdentity(main.load_sdl())
    assert isinstance(pads.connected(), list)
    assert pads.identity(-12345) is None
    assert pads.axes('no such pad') == {}


def test_gamepad_defaults():
    pads = main.GamepadBindings()
    for button, action in {0: 'fire', 2: 'fire', 1: 'up', 3: 'up'}.items():
        assert pads.action_for('x', button) == action
    assert pads.action_for('x', 5) is None
    assert pads.label('x', 'fire') == 'A, X'
    assert pads.label('x', 'up') == 'B, Y'


def test_gamepad_back_and_dpad_are_fixed_for_every_pad():
    pads = main.GamepadBindings()
    for button, action in main.JOY_FIXED_ACTIONS.items():
        assert pads.action_for('x', button) == action
        assert pads.rebind('x', 'fire', button) == 'That button is reserved'
    assert pads.label('x', 'fire') == 'A, X'


def test_gamepad_rebind_replaces_the_old_buttons():
    pads = main.GamepadBindings()
    assert pads.rebind('x', 'fire', 9) is None
    assert pads.label('x', 'fire') == 'Button 9'
    assert pads.action_for('x', 9) == 'fire'
    assert pads.action_for('x', 0) is None and pads.action_for('x', 2) is None
    assert pads.action_for('x', 1) == 'up'


def test_gamepad_rebind_refuses_a_button_of_the_other_action():
    pads = main.GamepadBindings()
    assert pads.rebind('x', 'fire', 1) == 'Already used for Thrust'
    assert pads.rebind('x', 'up', 0) == 'Already used for Fire'
    assert pads.label('x', 'fire') == 'A, X'
    assert pads.rebind('x', 'fire', 0) is None        # its own button
    assert pads.rebind('x', 'fire', True) == 'That button can not be used'


def test_gamepad_layouts_are_per_pad():
    pads = main.GamepadBindings()
    pads.rebind('x', 'fire', 3 + 6)
    assert pads.action_for('z', 0) == 'fire'
    assert pads.action_for('x', 0) is None
    # the same button may mean something else on another pad
    assert pads.rebind('z', 'up', 9) is None
    assert pads.action_for('z', 9) == 'up' and pads.action_for('x', 9) == 'fire'


def test_gamepad_trigger_replaces_the_thrust_buttons():
    pads = main.GamepadBindings()
    assert pads.bind_trigger('x', 5, -1.0, 1.0) is None
    assert pads.label('x', 'up') == 'trigger (axis 5)'
    assert pads.action_for('x', 1) is None and pads.action_for('x', 3) is None
    assert pads.action_for('x', 0) == 'fire'
    assert pads.action_for('z', 1) == 'up'            # other pads unchanged


def test_binding_a_thrust_button_replaces_the_trigger():
    pads = main.GamepadBindings()
    pads.bind_trigger('x', 5, -1.0, 1.0)
    assert pads.rebind('x', 'up', 9) is None
    assert pads.label('x', 'up') == 'Button 9'
    assert pads.profile('x')['trigger'] is None
    assert pads.action_for('x', 9) == 'up' and pads.action_for('x', 1) is None
    pads.bind_trigger('x', 5, -1.0, 1.0)
    assert pads.rebind('x', 'fire', 9) is None        # the trigger frees it
    assert pads.rebind('x', 'up', 9) == 'Already used for Fire'


def test_buttons_of_a_pad_thrusting_by_trigger_are_free_for_fire():
    pads = main.GamepadBindings()
    pads.bind_trigger('x', 5, -1.0, 1.0)
    assert pads.rebind('x', 'fire', 1) is None        # was a thrust button
    assert pads.action_for('x', 1) == 'fire'


def test_gamepad_trigger_refuses_the_stick():
    pads = main.GamepadBindings()
    for axis in (0, 1):
        assert pads.bind_trigger('x', axis, 0.0, 1.0) == 'The stick is reserved'
    assert pads.bind_trigger('x', 4, 0.5, 0.5) == 'That axis can not be used'
    assert pads.label('x', 'up') == 'B, Y'


def test_gamepad_reset_is_per_pad():
    pads = main.GamepadBindings()
    for ident in ('x', 'z'):
        pads.rebind(ident, 'fire', 9)
        pads.bind_trigger(ident, 5, 0.0, 1.0)
    pads.reset('x')
    assert pads.label('x', 'fire') == 'A, X' and pads.label('x', 'up') == 'B, Y'
    assert pads.label('z', 'fire') == 'Button 9'
    assert pads.label('z', 'up') == 'trigger (axis 5)'


def test_trigger_level_follows_the_pull():
    rest_low = {'axis': 5, 'rest': -1.0, 'full': 1.0}
    rest_zero = {'axis': 5, 'rest': 0.0, 'full': 1.0}
    inverted = {'axis': 5, 'rest': 0.0, 'full': -1.0}
    for trigger, rest, half, full in (
            (rest_low, -1.0, 0.0, 1.0), (rest_zero, 0.0, 0.5, 1.0),
            (inverted, 0.0, -0.5, -1.0)):
        assert main.trigger_level(trigger, rest) == 0
        assert main.trigger_level(trigger, full) == pytest.approx(1)
        assert 0.4 < main.trigger_level(trigger, half) < 0.6
    assert main.trigger_level(rest_zero, 0.05) == 0          # dead zone
    assert main.trigger_level(rest_zero, -0.5) == 0          # wrong way
    assert main.trigger_level(rest_zero, 5.0) == pytest.approx(1)  # clamped
    assert (main.trigger_level(rest_zero, 0.3)
            < main.trigger_level(rest_zero, 0.6))


def test_gamepad_bindings_persist(tmp_path):
    path = str(tmp_path / 'sub' / 'pads.json')
    pads = main.GamepadBindings(path)
    pads.rebind('x', 'up', 9)
    pads.bind_trigger('x', 5, -1.0, 1.0)
    pads.rebind('z', 'fire', 8)
    again = main.GamepadBindings(path)
    assert again.profile('x')['buttons']['up'] == [9]
    assert again.action_for('x', 9) is None       # the trigger thrusts now
    assert again.label('x', 'up') == 'trigger (axis 5)'
    assert again.profile('x')['trigger'] == {'axis': 5, 'rest': -1.0, 'full': 1.0}
    assert again.action_for('z', 8) == 'fire'
    assert again.action_for('q', 0) == 'fire'                # unknown pad
    again.reset('x')
    assert main.GamepadBindings(path).label('x', 'up') == 'B, Y'
    assert main.GamepadBindings(path).label('z', 'fire') == 'Button 8'


def test_unidentified_pad_uses_defaults_and_is_not_saved(tmp_path):
    path = tmp_path / 'pads.json'
    pads = main.GamepadBindings(str(path))
    assert pads.rebind(None, 'fire', 9) is None
    assert pads.action_for(None, 9) == 'fire'
    assert pads.action_for(None, 0) is None
    assert pads.pads == {}
    assert main.GamepadBindings(str(path)).action_for(None, 0) == 'fire'
    pads.reset(None)
    assert pads.action_for(None, 0) == 'fire'


GOOD = {'buttons': {'up': [1, 3], 'fire': [0, 2]}, 'trigger': None}


@pytest.mark.parametrize('profile', [
    {'buttons': {'up': [1]}, 'trigger': None},                       # no fire
    {'buttons': {'up': [1], 'fire': [1]}, 'trigger': None},          # twice
    {'buttons': {'up': [], 'fire': [0]}, 'trigger': None},           # empty
    {'buttons': {'up': [True], 'fire': [0]}, 'trigger': None},       # bool
    {'buttons': {'up': ['1'], 'fire': [0]}, 'trigger': None},        # not int
    {'buttons': {'up': [1], 'fire': [6, 7]}, 'trigger': None} if main.platform != 'android'
    else {'buttons': {'up': [1], 'fire': [4]}, 'trigger': None},     # reserved
    {'buttons': {'up': [1], 'fire': [0], 'jump': [4]}, 'trigger': None},
    {'buttons': {'up': [1], 'fire': [0]},
     'trigger': {'axis': 0, 'rest': 0, 'full': 1}},                  # stick
    {'buttons': {'up': [1], 'fire': [0]},
     'trigger': {'axis': 5, 'rest': 1, 'full': 1}},                  # no travel
    {'buttons': {'up': [1], 'fire': [0]},
     'trigger': {'axis': 5, 'rest': 'a', 'full': 1}},                # text
    {'buttons': {'up': [1], 'fire': [0]}, 'trigger': 'axis 5'},
    'not a profile',
])
def test_invalid_gamepad_profile_is_dropped_the_rest_is_kept(tmp_path, profile):
    path = tmp_path / 'pads.json'
    path.write_text(json.dumps({
        'version': 1,
        'pads': {'bad': profile,
                 'good': {'buttons': {'up': [5], 'fire': [6 + 4]},
                          'trigger': None}}}))
    pads = main.GamepadBindings(str(path))
    assert 'bad' not in pads.pads
    assert pads.action_for('bad', 0) == 'fire'               # defaults
    assert pads.action_for('good', 5) == 'up'
    assert pads.action_for('good', 10) == 'fire'


@pytest.mark.parametrize('content', [
    '{broken', '[]', '"x"', '{"version": 2, "pads": {}}', '{"version": 1}',
    '{"version": 1, "pads": []}', ''])
def test_corrupt_gamepad_file_means_defaults(tmp_path, content):
    path = tmp_path / 'pads.json'
    path.write_text(content)
    pads = main.GamepadBindings(str(path))
    assert pads.pads == {}
    assert pads.action_for('x', 0) == 'fire'


def test_missing_and_unwritable_gamepad_file(tmp_path):
    assert main.GamepadBindings(str(tmp_path / 'none.json')).pads == {}
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    pads = main.GamepadBindings(str(blocker / 'pads.json'))   # parent is a file
    assert pads.rebind('x', 'fire', 9) is None                # save fails quietly
    assert pads.action_for('x', 9) == 'fire'


# ---- gamepad buttons in the game ------------------------------------------

def two_pads_game(start_game):
    game = start_game(slots=[('pad', 7), ('pad', 3), None, None])
    game.pads = fake_pads(s7=(PAD_X, {}), s3=(PAD_Z, {}))
    return game


def test_remapped_buttons_drive_only_their_own_pad(start_game):
    game = two_pads_game(start_game)
    one, two = game.spaceships
    game.pad_bindings.rebind(PAD_X[0], 'fire', 9)
    _pad(game, 7, 0)                       # old fire of pad X
    assert game.shots == []
    _pad(game, 7, 9)
    assert [s.spaceship for s in game.shots] == [one]
    _pad(game, 3, 9)                       # pad Z keeps its own layout
    assert len(game.shots) == 1
    _pad(game, 3, 0)
    assert [s.spaceship for s in game.shots] == [one, two]
    game.pad_bindings.rebind(PAD_Z[0], 'up', 10)
    game._on_joy_button_down(None, 3, 10)
    assert two.thrust and not one.thrust
    game._on_joy_button_up(None, 3, 10)
    game._on_joy_button_down(None, 3, 1)   # the old thrust button
    assert not two.thrust


def test_same_model_pads_share_a_layout(start_game):
    game = start_game(slots=[('pad', 7), ('pad', 8), None, None])
    game.pads = fake_pads(s7=(PAD_X, {}), s8=(PAD_X, {}))
    game.pad_bindings.rebind(PAD_X[0], 'fire', 9)
    _pad(game, 7, 9)
    _pad(game, 8, 9)
    assert len(game.shots) == 2
    _pad(game, 8, 0)
    assert len(game.shots) == 2


def test_rebind_while_a_button_is_held_does_not_strand_thrust(game):
    ship = game.spaceships[0]
    game._on_joy_button_down(None, 0, 1)
    assert ship.thrust
    game.pad_bindings.rebind(None, 'up', 9)
    game._on_joy_button_up(None, 0, 1)
    assert not ship.thrust


def test_back_and_dpad_buttons_stay_fixed(game, monkeypatch):
    monkeypatch.setattr(main, 'JOY_FIXED_ACTIONS', main.JOY_FIXED_ACTIONS_ANDROID)
    game.pad_bindings.rebind(None, 'fire', 9)
    game.pad_bindings.rebind(None, 'up', 10)
    ship = game.spaceships[0]
    game._on_joy_button_down(None, 0, 13)         # D-pad left
    assert ship.angle_rotation == 3
    game._on_joy_button_up(None, 0, 13)
    game._on_joy_button_down(None, 0, 4)          # View / Back
    assert game.paused


def test_remapped_fire_does_not_change_the_menu(kv_game):
    game = kv_game
    game.pad_bindings.rebind(None, 'fire', 9)
    _pad(game, 0, 9)                              # the remapped button
    assert game.menu_active
    _pad(game, 0, 0)                              # A still activates
    assert game.select_active and not game.menu_active


def test_menus_use_the_standard_buttons_with_any_layout(kv_game):
    game = kv_game
    game.pad_bindings.rebind(None, 'fire', 9)
    game.pad_bindings.rebind(None, 'up', 10)
    game.menu.selected = 2
    game.menu.highlight()
    _pad(game, 0, 1)                              # B moves up, as always
    assert game.menu.selected == 1
    _pad(game, 0, 10)                             # the remapped thrust: nothing
    assert game.menu.selected == 1


def test_remapped_fire_does_not_join_but_the_standard_button_does(kv_game):
    game = kv_game
    game.pad_bindings.rebind(None, 'fire', 9)
    join = _join(game)
    _pad(game, 4, 9)
    assert join.slots[0] is None
    _pad(game, 4, 0)
    assert join.slots[0] == ('pad', 4)
    _pad(game, 4, 0)
    assert join.ready[0]


def test_standard_buttons_in_pause_confirm_results_and_name(kv_game, tmp_path):
    game = kv_game
    game.pad_bindings.rebind(None, 'fire', 9)
    game.game_start()
    game.pause()
    _pad(game, 0, 9)                              # remapped: nothing
    assert game.paused
    _pad(game, 0, 0)                              # A: Continue
    assert not game.paused
    game.pause()
    game._on_joy_axis(None, 0, 1, 32767)          # down to Main menu
    game._on_joy_axis(None, 0, 1, 0)
    _pad(game, 0, 0)
    assert hasattr(game, 'confirm_screen')
    _pad(game, 0, 9)
    assert hasattr(game, 'confirm_screen')
    _pad(game, 0, 0)                              # "No" is the default
    assert game.paused and not hasattr(game, 'confirm_screen')
    game.resume()
    game.leaderboard = main.Leaderboard(str(tmp_path / 'lb.json'))
    game.spaceships[0].points = 5
    _lose_all(game)
    _armed(game.results_screen)
    _pad(game, 0, 9)
    assert game.results_active and not game.name_active
    _pad(game, 0, 0)                              # Save to leaderboard
    assert game.name_active
    _pad(game, 0, 0)                              # Save
    assert game.results_active
    assert len(game.leaderboard.entries) == 1


def test_remapped_buttons_play_the_game_after_the_menu(kv_game):
    game = kv_game
    game.pad_bindings.rebind(None, 'fire', 9)
    game.game_start()
    _pad(game, 0, 0)                              # A: no longer fires
    assert game.shots == []
    _pad(game, 0, 9)
    assert len(game.shots) == 1


def test_a_press_that_starts_the_game_does_not_fire_on_release(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(1)
    game._on_joy_button_down(None, 0, 0)          # A readies: the game starts
    assert game.spaceships and not game.select_active
    game._on_joy_button_up(None, 0, 0)
    assert game.shots == []


# ---- analog thrust --------------------------------------------------------

def test_thrust_level_scales_the_speed():
    ship = Spaceship()
    for level in (0.25, 0.5, 1):
        ship.thrust_level = level
        ship.thrust_on()
        ship.speed = 0
        ship.update(0)
        assert ship.speed == pytest.approx(3 * level)
        ship.thrust_off()


def test_set_thrust_drives_the_engine(game):
    ship, controls = game.spaceships[0], game.spaceship_controls
    Spaceship.thrusting.clear()          # ships of other tests may linger
    Spaceship.sound.stop()
    controls.set_thrust(0.5)
    assert ship.thrust and Spaceship.sound.state == 'play'
    ship.speed = 0
    ship.update(0)
    assert ship.speed == pytest.approx(1.5)
    controls.set_thrust(0.2)
    assert ship.thrust_level == pytest.approx(0.2)
    controls.set_thrust(0)
    assert not ship.thrust and Spaceship.sound.state == 'stop'
    ship.speed = 0
    ship.update(0)
    assert ship.speed == 0


def test_a_held_thrust_key_is_full_power_whatever_the_trigger_does(game):
    ship, controls = game.spaceships[0], game.spaceship_controls
    controls.set_thrust(0.3)
    controls.press('up')
    assert ship.thrust_level == 1
    controls.release('up')
    assert ship.thrust and ship.thrust_level == pytest.approx(0.3)
    controls.set_thrust(0)
    assert not ship.thrust


def test_keyboard_and_touch_thrust_stay_full_power(game):
    ship = game.spaceships[0]
    game._on_key_down(None, ord('w'))
    ship.speed = 0
    ship.update(0)
    assert ship.speed == 3


def test_analog_thrust_of_one_ship_leaves_the_others_alone(start_game):
    game = start_game(slots=[('pad', 7), ('keys', 0), None, None])
    game.pads = fake_pads(s7=(PAD_X, {}))
    game.pad_bindings.bind_trigger(PAD_X[0], 5, -1.0, 1.0)
    pad_ship, key_ship = game.spaceships
    game._on_joy_axis(None, 7, 5, 32767)
    game._on_key_down(None, ord('w'))
    assert pad_ship.thrust_level == pytest.approx(1)
    game._on_joy_axis(None, 7, 5, 0)                   # half pulled
    assert 0.3 < pad_ship.thrust_level < 0.6
    assert key_ship.thrust and key_ship.thrust_level == 1


def trigger_game(start_game, rest, **kw):
    game = start_game(slots=[('pad', 7), ('pad', 3), None, None])
    game.pads = fake_pads(s7=(PAD_X, {}), s3=(PAD_Z, {}))
    game.pad_bindings.bind_trigger(PAD_X[0], 5, rest, 1.0)
    return game


@pytest.mark.parametrize('rest, raw_rest, raw_half', [
    (-1.0, -32767, 0), (0.0, 0, 16383)])
def test_trigger_thrusts_with_the_pull(start_game, rest, raw_rest, raw_half):
    game = trigger_game(start_game, rest)
    one, two = game.spaceships
    game._on_joy_axis(None, 7, 5, raw_rest)
    assert not one.thrust
    game._on_joy_axis(None, 7, 5, raw_half)
    assert one.thrust and 0.3 < one.thrust_level < 0.6
    half = one.thrust_level
    game._on_joy_axis(None, 7, 5, 32767)
    assert one.thrust_level == pytest.approx(1) and one.thrust_level > half
    game._on_joy_axis(None, 7, 5, raw_rest)
    assert not one.thrust
    assert not two.thrust


def test_a_bound_trigger_replaces_the_thrust_buttons_of_that_pad(start_game):
    game = trigger_game(start_game, -1.0)
    one, two = game.spaceships
    game._on_joy_button_down(None, 7, 1)
    assert not one.thrust
    game._on_joy_button_down(None, 3, 1)               # pad Z has no trigger
    assert two.thrust
    game._on_joy_axis(None, 3, 5, 32767)               # not its trigger
    assert not one.thrust


def test_an_unbound_axis_does_nothing_and_the_stick_still_steers(start_game):
    game = trigger_game(start_game, -1.0)
    one, _ = game.spaceships
    game._on_joy_axis(None, 7, 4, 32767)
    assert not one.thrust
    game._on_joy_axis(None, 7, 0, -32767)
    assert one.angle_rotation == 3
    game._on_joy_axis(None, 7, 1, -32767)
    assert one.thrust and one.thrust_level == 1


def test_trigger_is_ignored_while_paused_and_pause_lets_go(start_game):
    game = trigger_game(start_game, -1.0)
    one, _ = game.spaceships
    game._on_joy_axis(None, 7, 5, 32767)
    assert one.thrust
    game.pause()
    assert not one.thrust
    game._on_joy_axis(None, 7, 5, 32767)
    assert not one.thrust
    game.resume()
    assert not one.thrust
    game._on_joy_axis(None, 7, 5, 32767)
    assert one.thrust


def test_trigger_of_a_pad_that_did_not_join_is_ignored(start_game):
    game = start_game(slots=[('pad', 7), ('keys', 0), None, None])
    game.pads = fake_pads(s7=(PAD_X, {}), s9=(PAD_Z, {}))
    game.pad_bindings.bind_trigger(PAD_Z[0], 5, -1.0, 1.0)
    game._on_joy_axis(None, 9, 5, 32767)
    assert not any(ship.thrust for ship in game.spaceships)


# ---- the gamepad buttons page --------------------------------------------

def _open_gamepad(game):
    _open_settings(game)
    _press(game, 274)                    # down to "Gamepad buttons"
    _press(game, KEY_ENTER)
    assert isinstance(game.settings, main.GamepadSettings)
    return game.settings


def _texts(page):
    ids = page.ids
    return [ids[k].text for k in
            ('btn_pad', 'btn_up', 'btn_fire')]


def test_settings_hub_opens_gamepad_page_and_goes_back(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}))
    page = _open_gamepad(game)
    assert _texts(page) == ['Gamepad: Pad X', 'Thrust: B, Y', 'Fire: A, X']
    assert [b.text for b in page.buttons] == [
        'Gamepad: Pad X', 'Thrust: B, Y', 'Fire: A, X',
        'Reset to defaults', 'Back']
    _press(game, KEY_ESC)
    assert isinstance(game.settings, main.SettingsScreen)
    _press(game, KEY_ESC)
    assert game.menu in game.children


def test_gamepad_page_with_no_gamepad(kv_game):
    game = kv_game
    page = _open_gamepad(game)
    assert page.ids.btn_pad.text == 'Gamepad: none connected'
    assert page.ids.message.text == 'No gamepad connected'
    assert [b.text for b in page.buttons] == ['Reset to defaults', 'Back']
    page.begin_rebind('fire')
    page.begin_rebind('up')
    assert page.waiting == ''


def test_gamepad_page_is_navigable_by_a_gamepad(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}))
    page = _open_gamepad(game)
    for _ in range(4):                      # down to "Back"
        game._on_joy_axis(None, 7, 1, 32767)
        game._on_joy_axis(None, 7, 1, 0)
    assert page.buttons[page.selected].text == 'Back'
    _pad(game, 7, 0)                        # fire button activates
    assert isinstance(game.settings, main.SettingsScreen)


def test_pad_selector_cycles_through_models(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}), s3=(PAD_Z, {}), s8=(PAD_X, {}))
    game.pad_bindings.rebind(PAD_Z[0], 'fire', 9)
    page = _open_gamepad(game)
    assert page.ids.btn_pad.text == 'Gamepad: Pad X'
    page.switch_pad()
    assert _texts(page)[0:3] == ['Gamepad: Pad Z', 'Thrust: B, Y',
                                 'Fire: Button 9']
    page.switch_pad()                       # two X pads count once
    assert page.ids.btn_pad.text == 'Gamepad: Pad X'


def test_rebind_on_the_page_edits_only_the_selected_pad(kv_game, tmp_path):
    game = kv_game
    game.pad_bindings.path = str(tmp_path / 'pads.json')
    game.pads = fake_pads(s7=(PAD_X, {}), s3=(PAD_Z, {}))
    page = _open_gamepad(game)
    page.begin_rebind('fire')
    assert page.ids.btn_fire.text == 'Fire: press a button...'
    game._on_joy_button_down(None, 7, 9)
    assert page.ids.btn_fire.text == 'Fire: Button 9' and page.waiting == ''
    assert game.pad_bindings.action_for(PAD_X[0], 9) == 'fire'
    assert game.pad_bindings.action_for(PAD_Z[0], 0) == 'fire'
    assert main.GamepadBindings(game.pad_bindings.path).label(
        PAD_X[0], 'fire') == 'Button 9'


def test_buttons_outside_waiting_change_nothing(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}))
    page = _open_gamepad(game)
    _pad(game, 7, 9)
    assert _texts(page)[1:3] == ['Thrust: B, Y', 'Fire: A, X']


def test_button_pressed_on_another_pad_is_ignored_while_waiting(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}), s3=(PAD_Z, {}))
    page = _open_gamepad(game)
    page.begin_rebind('up')
    game._on_joy_button_down(None, 3, 9)
    assert page.waiting == 'up'
    assert game.pad_bindings.label(PAD_Z[0], 'up') == 'B, Y'
    assert game.pad_bindings.label(PAD_X[0], 'up') == 'B, Y'
    game._on_joy_button_down(None, 7, 9)
    assert page.waiting == '' and page.ids.btn_up.text == 'Thrust: Button 9'


def test_conflicting_and_reserved_buttons_are_refused_with_a_message(
        kv_game, monkeypatch):
    # where the D-pad arrives as buttons (Android) they can not be bound
    monkeypatch.setattr(main, 'JOY_FIXED_ACTIONS', main.JOY_FIXED_ACTIONS_ANDROID)
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}))
    page = _open_gamepad(game)
    page.begin_rebind('fire')
    game._on_joy_button_down(None, 7, 1)             # a thrust button
    assert page.ids.message.text == 'Already used for Thrust'
    assert page.ids.btn_fire.text == 'Fire: A, X' and page.waiting == ''
    page.begin_rebind('up')
    game._on_joy_button_down(None, 7, 11)             # D-pad up
    assert page.ids.message.text == 'That button is reserved'
    assert page.ids.btn_up.text == 'Thrust: B, Y'


def test_back_button_or_escape_cancel_waiting_without_leaving(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}))
    page = _open_gamepad(game)
    back = next(b for b, a in main.JOY_FIXED_ACTIONS.items() if a == 'back')
    page.begin_rebind('fire')
    game._on_joy_button_down(None, 7, back)
    game._on_joy_button_up(None, 7, back)
    assert game.settings is page and game.settings_active and page.waiting == ''
    assert page.ids.btn_fire.text == 'Fire: A, X'
    page.begin_rebind('fire')
    _press(game, ord('a'))                            # other keys: still waiting
    assert page.waiting == 'fire'
    _press(game, KEY_ESC)
    assert game.settings is page and game.settings_active and page.waiting == ''


def test_the_press_that_selects_an_entry_does_not_bind_itself(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {}))
    page = _open_gamepad(game)
    game._on_joy_axis(None, 7, 1, 32767)              # down to "Thrust"
    game._on_joy_axis(None, 7, 1, 0)
    game._on_joy_button_down(None, 7, 0)              # A activates it
    assert page.waiting == 'up'
    game._on_joy_button_up(None, 7, 0)
    assert page.waiting == 'up'
    assert game.pad_bindings.label(PAD_X[0], 'up') == 'B, Y'
    game._on_joy_axis(None, 7, 0, 32767)              # stick is ignored
    assert page.waiting == 'up'


@pytest.mark.parametrize('rest, raw_rest, raw_pull', [
    (-1.0, -32767, 32767), (0.0, 0, 30000)])
def test_thrust_takes_a_pulled_trigger(kv_game, rest, raw_rest, raw_pull):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {4: rest, 5: rest}))
    page = _open_gamepad(game)
    page.begin_rebind('up')
    assert page.ids.btn_up.text == 'Thrust: button or trigger...'
    game._on_joy_axis(None, 7, 4, raw_rest)           # still: not bound
    assert page.waiting == 'up'
    game._on_joy_axis(None, 7, 5, raw_pull)
    assert page.waiting == '' and page.ids.btn_up.text == (
        'Thrust: trigger (axis 5)')
    assert game.pad_bindings.profile(PAD_X[0])['trigger'] == {
        'axis': 5, 'rest': rest, 'full': 1.0}


def test_thrust_takes_a_button_or_a_trigger_whichever_comes(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {5: -1.0}))
    page = _open_gamepad(game)
    page.begin_rebind('up')
    game._on_joy_button_down(None, 7, 9)
    assert page.ids.btn_up.text == 'Thrust: Button 9'
    page.begin_rebind('up')
    game._on_joy_axis(None, 7, 5, 32767)
    assert page.ids.btn_up.text == 'Thrust: trigger (axis 5)'
    page.begin_rebind('up')                           # and back to a button
    game._on_joy_button_down(None, 7, 3)
    assert page.ids.btn_up.text == 'Thrust: Y'
    assert game.pad_bindings.profile(PAD_X[0])['trigger'] is None


def test_fire_waits_for_a_button_only(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {5: -1.0}))
    page = _open_gamepad(game)
    page.begin_rebind('fire')
    game._on_joy_axis(None, 7, 5, 32767)              # a trigger: not for fire
    assert page.waiting == 'fire'
    assert game.pad_bindings.profile(PAD_X[0])['trigger'] is None


def test_trigger_capture_ignores_other_pads_and_the_stick(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {4: -1.0}), s3=(PAD_Z, {4: -1.0}))
    page = _open_gamepad(game)
    page.begin_rebind('up')
    game._on_joy_axis(None, 3, 4, 32767)              # pad Z's trigger
    assert page.waiting == 'up'
    game._on_joy_axis(None, 7, 0, 32767)              # the stick steers
    game._on_joy_axis(None, 7, 1, -32767)
    assert page.waiting == 'up'
    assert game.pad_bindings.profile(PAD_X[0])['trigger'] is None


def test_back_cancels_waiting_for_thrust_and_a_bound_trigger_is_shown(kv_game):
    game = kv_game
    game.pads = fake_pads(s7=(PAD_X, {4: -1.0}))
    game.pad_bindings.bind_trigger(PAD_X[0], 4, -1.0, 1.0)
    page = _open_gamepad(game)
    assert page.ids.btn_up.text == 'Thrust: trigger (axis 4)'
    page.begin_rebind('up')
    back = next(b for b, a in main.JOY_FIXED_ACTIONS.items() if a == 'back')
    game._on_joy_button_down(None, 7, back)
    assert page.waiting == '' and game.settings is page
    assert page.ids.btn_up.text == 'Thrust: trigger (axis 4)'


def test_reset_on_the_page_resets_one_pad_and_keeps_the_keyboard(kv_game):
    game = kv_game
    game.bindings.path = None
    game.pads = fake_pads(s7=(PAD_X, {}), s3=(PAD_Z, {}))
    game.bindings.rebind('fire', KEY_F)
    for ident in (PAD_X[0], PAD_Z[0]):
        game.pad_bindings.rebind(ident, 'fire', 9)
        game.pad_bindings.bind_trigger(ident, 5, 0.0, 1.0)
    page = _open_gamepad(game)
    page.reset()
    assert _texts(page)[1:] == ['Thrust: B, Y', 'Fire: A, X']
    assert game.pad_bindings.label(PAD_Z[0], 'fire') == 'Button 9'
    assert game.pad_bindings.label(PAD_Z[0], 'up') == 'trigger (axis 5)'
    assert game.bindings.label('fire') == 'F'


def test_unidentified_pad_can_be_edited_for_the_session(kv_game, tmp_path):
    game = kv_game
    game.pad_bindings.path = str(tmp_path / 'pads.json')
    _pad(game, 5, 9)                                  # a pad shows up
    page = _open_gamepad(game)
    assert page.ids.btn_pad.text == 'Gamepad: Unidentified gamepad'
    page.begin_rebind('fire')
    game._on_joy_button_down(None, 5, 9)
    assert page.ids.btn_fire.text == 'Fire: Button 9'
    assert not os.path.exists(game.pad_bindings.path)
    assert main.GamepadBindings(game.pad_bindings.path).label(
        None, 'fire') == 'A, X'


def test_gamepad_settings_refresh_before_the_kv_is_loaded():
    page = main.GamepadSettings(bindings=main.GamepadBindings())
    assert page.waiting == '' and not page.has_pad


# ---- thrust power of the sticks ------------------------------------------

def test_stick_level_grows_from_the_start_to_the_edge():
    assert main.stick_level(0) == 0
    assert main.stick_level(main.STICK_THRUST_START) == 0
    assert main.stick_level(1) == 1 and main.stick_level(7) == 1
    assert 0.4 < main.stick_level(0.675) < 0.6          # half way
    assert main.stick_level(0.5) < main.stick_level(0.8)
    assert main.stick_level(-1) == 0


def test_on_screen_joystick_thrusts_with_the_push(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    touch, _ = _touch_down(layout, _stick_pos(layout, 0, 0.2))
    assert not ship.thrust                              # inside the dead zone
    _move(layout, touch, _stick_pos(layout, 0, 0.675))
    assert ship.thrust and 0.4 < ship.thrust_level < 0.6
    half = ship.thrust_level
    _move(layout, touch, _stick_pos(layout, 0, 1.0))
    assert ship.thrust_level == pytest.approx(1) and ship.thrust_level > half
    ship.speed = 0
    ship.update(0)
    assert ship.speed == pytest.approx(3)
    _move(layout, touch, _stick_pos(layout, 0, 0.5))
    assert 0 < ship.thrust_level < 0.5
    _release(touch, layout.stick)
    assert not ship.thrust


def test_on_screen_joystick_turns_at_full_rate_while_thrusting_softly(game):
    game._on_window_touch(None, None)
    layout = game.spaceship_controls.touch_buttons
    ship = game.spaceships[0]
    _touch_down(layout, _stick_pos(layout, -0.5, 0.6))
    assert ship.angle_rotation == 3 and ship.thrust
    assert ship.thrust_level < 0.5


def test_gamepad_stick_thrusts_with_the_push(game):
    ship = game.spaceships[0]
    game._on_joy_axis(None, 0, 1, -int(0.2 * 32767))    # dead zone
    assert not ship.thrust
    game._on_joy_axis(None, 0, 1, -int(0.675 * 32767))
    assert ship.thrust and 0.4 < ship.thrust_level < 0.6
    game._on_joy_axis(None, 0, 1, -32767)
    assert ship.thrust_level == pytest.approx(1)
    game._on_joy_axis(None, 0, 1, 32767)                # down: nothing
    assert not ship.thrust
    game._on_joy_axis(None, 0, 1, -32767)
    game._on_joy_axis(None, 0, 1, 0)
    assert not ship.thrust


def test_gamepad_stick_thrust_belongs_to_the_joined_pad(start_game):
    game = start_game(slots=[('pad', 7), ('keys', 0), None, None])
    one, two = game.spaceships
    game._on_joy_axis(None, 7, 1, -32767)
    assert one.thrust and not two.thrust
    game._on_joy_axis(None, 9, 1, -32767)               # did not join
    assert not two.thrust


def test_gamepad_dpad_and_button_stay_full_power(game):
    ship = game.spaceships[0]
    game._on_joy_hat(None, 0, 0, (0, 1))                # D-pad up
    assert ship.thrust and ship.thrust_level == 1
    game._on_joy_hat(None, 0, 0, (0, 0))
    game._on_joy_axis(None, 0, 1, -int(0.7 * 32767))
    game._on_joy_button_down(None, 0, 1)                # Thrust button
    assert ship.thrust_level == 1
    game._on_joy_button_up(None, 0, 1)
    assert 0 < ship.thrust_level < 1                    # back to the stick


def test_stick_and_trigger_thrust_together_take_the_stronger(start_game):
    game = trigger_game(start_game, -1.0)
    one, _ = game.spaceships
    game._on_joy_axis(None, 7, 1, -int(0.7 * 32767))
    stick = one.thrust_level
    game._on_joy_axis(None, 7, 5, 32767)
    assert one.thrust_level == pytest.approx(1)
    game._on_joy_axis(None, 7, 5, -32767)
    assert one.thrust_level == pytest.approx(stick)
    game._on_joy_axis(None, 7, 1, 0)
    assert not one.thrust


def test_pause_lets_go_of_the_stick(game):
    ship = game.spaceships[0]
    game._on_joy_axis(None, 0, 1, -32767)
    assert ship.thrust
    game.pause()
    assert not ship.thrust
    game.resume()
    assert not ship.thrust


def test_stick_still_navigates_menus(kv_game):
    game = kv_game
    game._on_joy_axis(None, 0, 1, 32767)                # down
    game._on_joy_axis(None, 0, 1, 0)
    assert game.menu.selected == 1
    game._on_joy_axis(None, 0, 1, -32767)               # up
    game._on_joy_axis(None, 0, 1, 0)
    assert game.menu.selected == 0


# ---- desktop scale --------------------------------------------------------------

@pytest.mark.parametrize('output, scale', [
    ('Xft.dpi:\t192\nXft.antialias:\t1\n', 2.0),
    ('Xft.dpi:\t144\n', 1.5),
    ('Xft.dpi:\t96\n', 1.0),
    ('Xcursor.size:\t24\n', 1.0),           # no Xft.dpi
    ('Xft.dpi:\tlots\n', 1.0),
    ('Xft.dpi:\t9600\n', 1.0),              # nonsense
])
def test_desktop_scale_from_xft_dpi(output, scale):
    assert main.desktop_scale(lambda: output) == scale


def test_desktop_scale_without_libx11():
    def missing():
        raise OSError('libX11.so.6: cannot open shared object file')
    assert main.desktop_scale(missing) == 1.0


def test_x_resources_without_a_display(monkeypatch):
    monkeypatch.setenv('DISPLAY', ':4242')     # no such X server
    try:
        assert main.x_resources() == ''
    except OSError:
        pytest.skip('no libX11 here')
