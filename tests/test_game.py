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


def test_android_back_in_game_is_consumed_after_returning_to_menu(game, monkeypatch):
    # Kivy sends on_keyboard right after on_key_down; Back must not also
    # pause the app on Android just because the menu is now showing.
    import main
    monkeypatch.setattr(main, 'platform', 'android')
    game._on_key_down(None, KEY_ESC)
    assert game.menu_active
    assert game._on_keyboard(None, KEY_ESC) is True
    # a second Back, now from the menu itself, is left to Android
    game._on_key_up(None, KEY_ESC)
    game._on_key_down(None, KEY_ESC)
    assert game._on_keyboard(None, KEY_ESC) is None


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
    assert labels == ['Single player', 'Multiplayer', 'Settings', 'Exit']
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


def test_second_player_defaults():
    kb = main.KeyBindings()
    assert kb.lookup(ord('w')) == (0, 'up')
    assert kb.lookup(ord('i')) == (1, 'up')
    assert kb.lookup(ord('j')) == (1, 'left')
    assert kb.lookup(ord('l')) == (1, 'right')
    assert kb.lookup(ord('k')) == (1, 'fire')
    assert kb.lookup(KEY_UP) == (0, 'up')       # arrows steer player 1
    assert kb.lookup(KEY_ESC) == (None, 'back')
    assert kb.lookup(ord('q')) == (None, None)
    assert kb.label('fire', 1) == 'K'


def test_rebind_is_per_player_and_conflicts_span_players():
    kb = main.KeyBindings()
    assert kb.rebind('left', ord('u'), player=1) is None
    assert kb.lookup(ord('u')) == (1, 'left')
    assert kb.lookup(ord('j')) == (None, None)
    assert kb.action_for(ord('a')) == 'left'     # player 1 unchanged
    message = kb.rebind('up', ord('w'), player=1)
    assert 'Player 1' in message and 'Thrust' in message
    assert kb.lookup(ord('i')) == (1, 'up')      # kept
    assert 'Player 2' in kb.rebind('fire', ord('i'))
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


def test_player_bindings_round_trip(tmp_path):
    path = str(tmp_path / 'keys.json')
    kb = main.KeyBindings(path)
    kb.rebind('fire', ord('h'), player=1)
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
    _press(game, 274)                    # down to "Touch controls"
    _press(game, KEY_ENTER)
    assert isinstance(game.settings, main.TouchSettingsScreen)


def test_settings_hub_and_back(kv_game):
    game = kv_game
    assert not [b for b in game.menu.buttons if b.text == 'Settings'][0].disabled
    _open_settings(game)
    assert game.menu not in game.children
    assert [b.text for b in game.settings.buttons] == [
        'Keyboard layout', 'Touch controls', 'Back']
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
    game.menu.move(-2)                   # back to "Single player"
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
    assert layout.fire.width == pytest.approx(main.cm(2) * 1.5)
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
    margin = main.cm(main.MARGIN_CM)
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
        assert layout.stick.width == pytest.approx(main.cm(3.4) * 1.5)
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


def test_keyboard_page_switches_player(kv_game):
    game = kv_game
    game.bindings.path = None
    _open_keyboard(game)
    page = game.settings
    assert page.ids.btn_player.text == 'Keys of: Player 1'
    page.switch_player()
    assert page.ids.btn_player.text == 'Keys of: Player 2'
    assert [b.text for b in page.buttons][:4] == [
        'Thrust: I', 'Turn left: J', 'Turn right: L', 'Fire: K']
    page.begin_rebind('left')
    game._on_key_down(None, ord('u'))
    game._on_key_up(None, ord('u'))
    assert page.ids.btn_player.text == 'Keys of: Player 2'
    assert game.bindings.lookup(ord('u')) == (1, 'left')
    assert game.bindings.action_for(ord('a')) == 'left'
    assert game.bindings.label('left', 0) == 'A'
    page.begin_rebind('up')                       # W is player 1's key
    game._on_key_down(None, ord('w'))
    game._on_key_up(None, ord('w'))
    assert 'Player 1' in page.ids.message.text
    page.switch_player()
    assert page.buttons[0].text == 'Thrust: W'


def test_two_player_start_has_two_ships_and_own_controls(game2):
    assert len(game2.spaceships) == 2
    a, b = game2.spaceships
    assert a.pos != b.pos
    assert len(game2.controls) == 2
    assert game2.spaceship_controls is game2.controls[0]
    assert game2.controls[0].spaceship is a and game2.controls[1].spaceship is b
    assert [c.touch_buttons.side for c in game2.controls] == ['left', 'right']
    assert a.cabin != b.cabin


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


def test_second_set_ignored_in_single_player(game):
    ship = game.spaceships[0]
    game._on_key_down(None, ord('i'))
    game._on_key_down(None, ord('k'))
    assert not ship.thrust and game.shots == []


def test_two_gamepads_one_per_player(game2):
    one, two = game2.spaceships
    game2._on_joy_button_down(None, 7, 0)       # first pad: stick id 7
    assert [s.spaceship for s in game2.shots] == [one]
    game2._on_joy_button_down(None, 3, 0)       # second pad
    assert [s.spaceship for s in game2.shots] == [one, two]
    game2._on_joy_axis(None, 3, 1, -32767)      # second pad stick up
    assert two.thrust and not one.thrust
    game2._on_joy_hat(None, 7, 0, (-1, 0))
    assert one.angle_rotation == 3 and two.angle_rotation == 0
    game2._on_joy_button_down(None, 9, 0)       # a third pad does nothing
    assert len(game2.shots) == 2


def test_single_gamepad_and_keyboard_set(game2):
    one, two = game2.spaceships
    game2._on_joy_axis(None, 0, 1, -32767)
    game2._on_key_down(None, ord('l'))
    assert one.thrust and two.angle_rotation == -3


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


def test_game_ends_when_both_ships_are_out(game2):
    one, two = game2.spaceships
    for _ in range(3):
        _hit(game2, one)
    for _ in range(3):
        _hit(game2, two)
    assert game2.spaceships == []
    assert game2.menu in game2.children
    assert game2.controls == []


def test_back_from_any_player_ends_two_player_game(game2):
    game2._on_joy_button_down(None, 1, 6)
    assert game2.menu in game2.children


def test_one_status_block_per_ship(game2, game):
    assert len(game2.statuses) == 2
    left, right = game2.statuses
    assert (left.side, right.side) == ('left', 'right')
    assert left.spaceship is game2.spaceships[0]
    assert tuple(left.color[:3]) == pytest.approx(
        main.cabin_rgb(game2.spaceships[0].cabin))
    assert len(game.statuses) == 1 and game.statuses[0].side == ''


def _touch_layouts(game):
    layouts = [c.touch_buttons for c in game.controls]
    for layout in layouts:
        layout.size = (1000, 600)
    return layouts


@pytest.mark.parametrize('size', [(800, 480), (1000, 600), (1920, 1080)])
@pytest.mark.parametrize('scale', [1.0, 4.0])
def test_two_touch_sets_are_columns_on_each_side(game2, scale, size):
    margin = main.cm(main.MARGIN_CM)
    left, right = [c.touch_buttons for c in game2.controls]
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
    top = h - main.cm(2)
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


def test_touch_sets_steer_their_own_ship(game2):
    game2._on_window_touch(None, None)
    one, two = game2.spaceships
    left, right = _touch_layouts(game2)
    stick, consumed = _touch_down(left, _stick_pos(left, -0.9, 0))
    assert consumed and one.angle_rotation == 3
    fire, consumed = _touch_down(right, _fire_pos(right))
    assert consumed
    assert [s.spaceship for s in game2.shots] == [two]
    assert one.angle_rotation == 3 and two.angle_rotation == 0
    _release(fire, right.fire)
    _release(stick, left.stick)
    assert one.angle_rotation == 0


def test_touch_pads_ignore_the_other_half(game2):
    game2._on_window_touch(None, None)
    left, right = _touch_layouts(game2)
    _, consumed = _touch_down(left, _fire_pos(right))
    assert not consumed


def test_lost_ship_removes_its_touch_set(game2):
    game2._on_window_touch(None, None)
    one, two = game2.spaceships
    left, right = _touch_layouts(game2)
    stick, _ = _touch_down(left, _stick_pos(left, 0, 0.9))
    assert one.thrust
    for _ in range(3):
        _hit(game2, one)
    assert left.parent.parent is None and right.parent.parent is not None
    assert not one.thrust


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
    assert colors.colors == ['blue', 'green']
    colors.cycle(0, 1)
    assert colors.colors[0] == 'red'                # green is taken
    colors.cycle(1, -1)
    assert colors.colors[1] == 'blue'               # red taken, back to blue
    colors.cycle(0, 1, players=1)                   # only one player: free
    assert colors.colors[0] == 'yellow'
    for _ in range(20):
        colors.cycle(0, 1)
        assert colors.colors[0] != colors.colors[1]


def test_ship_colors_persist_and_fall_back(tmp_path):
    path = str(tmp_path / 'colors.json')
    colors = main.ShipColors(path)
    colors.colors = ['red', 'yellow']
    colors.save()
    assert main.ShipColors(path).colors == ['red', 'yellow']
    for bad in ('nope', '[]', '{"colors": ["red"]}',
                '{"colors": ["red", "red"]}', '{"colors": ["red", "pink"]}'):
        with open(path, 'w') as f:
            f.write(bad)
        assert main.ShipColors(path).colors == ['blue', 'green']
    assert main.ShipColors(str(tmp_path / 'missing.json')).colors == [
        'blue', 'green']


def test_selection_preview_updates_before_the_game(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(2)
    select = game.select
    before = select.panels[0]['preview'].texture
    game._on_key_down(None, ord('d'))               # player 1: next colour
    game._on_key_up(None, ord('d'))
    assert game.ship_colors.colors == ['red', 'green']
    assert select.panels[0]['preview'].texture is not before
    assert select.panels[0]['name'].text == 'Red'
    assert game.spaceships == []                    # not started yet


def test_selection_player_two_uses_own_keys_and_confirm(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(2)
    _press(game, ord('l'))                          # player 2: next colour
    assert game.ship_colors.colors == ['blue', 'red']
    _press(game, KEY_SPACE)                         # player 1 ready
    assert game.select_active and len(game.spaceships) == 0
    _press(game, ord('k'))                          # player 2 ready
    assert not game.select_active
    assert [s.cabin for s in game.spaceships] == ['blue', 'red']
    assert len(game.controls) == 2


def test_selection_ready_blocks_changes_and_back_cancels(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(2)
    _press(game, KEY_SPACE)
    _press(game, ord('d'))                          # ready: ignored
    assert game.ship_colors.colors == ['blue', 'green']
    _press(game, KEY_ESC)
    assert game.menu in game.children and not game.select_active
    assert game.spaceships == []


def test_selection_by_touch_buttons(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(2)
    panels = game.select.panels
    panels[1]['next'].dispatch('on_press')
    assert game.ship_colors.colors[1] == 'red'
    panels[0]['ready'].dispatch('on_press')
    panels[1]['ready'].dispatch('on_press')
    assert len(game.spaceships) == 2


def test_selection_single_player_any_input_and_second_pad(kv_game):
    game = kv_game
    game.ship_colors.path = None
    game.show_ship_select(1)
    assert len(game.select.panels) == 1
    _press(game, ord('l'))                          # P2 key still picks
    assert game.ship_colors.colors[0] == 'green'    # free: nobody else plays
    game._on_joy_button_down(None, 5, 0)
    assert len(game.spaceships) == 1 and game.spaceships[0].cabin == 'green'


def test_multiplayer_menu_entry_leads_to_two_ships(kv_game):
    game = kv_game
    game.ship_colors.path = None
    _press(game, 274)                               # Multiplayer
    _press(game, KEY_ENTER)
    assert game.select.players == 2
    game.select.toggle_ready(0)
    game.select.toggle_ready(1)
    assert len(game.spaceships) == 2
    assert game.num_players == 2


def test_second_gamepad_navigates_menu(kv_game):
    game = kv_game
    game._on_joy_axis(None, 0, 1, 32767)            # pad 0: down
    game._on_joy_axis(None, 0, 1, 0)
    game._on_joy_button_down(None, 1, 0)            # pad 1: activate
    assert game.select_active and game.select.players == 2


def test_status_text_is_turned_toward_each_player(kv_game):
    from kivy.graphics import Rotate
    game = kv_game
    game.ship_colors.path = None
    game.game_start(2)

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


def test_fire_label_is_turned_toward_each_player(game, game2):
    one, two = [c.touch_buttons for c in game2.controls]
    for layout in (one, two):
        layout.size = (1000, 600)
    assert one.fire.text_angle == -90 and one.fire._label_turn.angle == -90
    assert two.fire.text_angle == 90 and two.fire._label_turn.angle == 90
    single = game.controls[0].touch_buttons
    single.size = (1000, 600)
    assert single.fire.text_angle == 0 and single.fire._label_turn.angle == 0
    assert tuple(one.fire._label_turn.origin[:2]) == pytest.approx(
        tuple(one.fire.center))
