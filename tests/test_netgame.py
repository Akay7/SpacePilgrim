"""Network games: a host and its clients as SpacePilgrimGames in one
process, talking over localhost. Announcements and the game search are
faked; the TCP sessions are real."""

import json
import socket

import pytest
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp

import main
import network
from main import SpacePilgrimGame

KEY_SPACE, KEY_ENTER, KEY_ESC, KEY_DOWN = 32, 13, 27, 274
KEY_A, KEY_D = ord('a'), ord('d')
SC_A, SC_D = 4, 7


class FakeAnnouncer:
    def __init__(self, name, port):
        self.name, self.port = name, port
        self.ticks = []
        self.closed = False

    def tick(self, players, playing):
        self.ticks.append((players, playing))

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self):
        self.games = []
        self.closed = False

    def poll(self):
        return list(self.games)

    def close(self):
        self.closed = True


class Env:
    def __init__(self):
        self.games = []
        self.announcers = []
        self.browser = FakeBrowser()

    def new_game(self):
        game = SpacePilgrimGame()
        game.game_stop()
        self.games.append(game)
        return game

    def host(self):
        game = self.new_game()
        game.show_network()
        game.host_game()
        assert game.select_active
        return game

    def client(self, host):
        game = self.new_game()
        game.show_network()
        game.join_game('127.0.0.1', host.net.session.port, 'TV')
        self.pump()
        return game

    def pump(self, rounds=20):
        for _ in range(rounds):
            for game in self.games:
                if game.net is not None:
                    game.net.poll()

    def frames(self, host, count=1):
        """The host plays `count` frames; everybody gets the news."""
        for _ in range(count):
            host.update(1 / 60)
            self.pump(3)


@pytest.fixture
def env(monkeypatch):
    Builder.load_file('spacepilgrim.kv')
    names = iter(['TV', 'Pixel 8', 'Tab', 'Laptop', 'Desk'])
    monkeypatch.setattr(main, 'device_name', lambda: next(names))
    monkeypatch.setattr(main, 'make_host_session', lambda name: network.HostSession(
        name, port=0, tries=1, address='127.0.0.1'))
    e = Env()

    def announcer(name, port):
        e.announcers.append(FakeAnnouncer(name, port))
        return e.announcers[-1]
    monkeypatch.setattr(main, 'make_announcer', announcer)
    monkeypatch.setattr(main, 'make_browser', lambda: e.browser)
    monkeypatch.setattr(network, 'local_address', lambda: '192.168.1.20')
    yield e
    for game in e.games:
        game.net_end()
        game.frame_schedule.cancel()
        game.asteroid_schedule.cancel()
    Builder.unload_file('spacepilgrim.kv')


def press(game, key, scancode=None):
    game._on_key_down(None, key, scancode)
    game._on_key_up(None, key, scancode)


def pad_fire(game, stick=0):
    game._on_joy_button_down(None, stick, 0)
    game._on_joy_button_up(None, stick, 0)


def started(env, players=('host', 'client')):
    """A running two-player network game: keyboard set 1 on the host as
    player 1 and keyboard set 1 on a client as player 2."""
    host = env.host()
    client = env.client(host)
    for _ in range(2):            # join, then ready
        press(host, KEY_SPACE)
        press(client, KEY_SPACE)
        env.pump()
    assert host.in_net_game and client.in_net_game
    env.frames(host)
    return host, client


# ---- menu ---------------------------------------------------------------------

def test_menu_has_network_game_and_fits_a_phone(env):
    game = env.new_game()
    assert [b.text for b in game.menu.buttons] == [
        'Single player', 'Multiplayer', 'Network game', 'Leaderboard',
        'Settings', 'Exit']
    menu = game.menu
    assert menu.height <= dp(360) - dp(10)
    for message in ('', 'The host ended the game'):
        menu.ids.message.text = message
        menu.do_layout()
        assert all(b.height >= dp(44) for b in menu.buttons)
        assert all(menu.y <= b.y and b.top <= menu.top for b in menu.buttons)


# ---- network screen -----------------------------------------------------------

def _labels(screen):
    return [b.text for b in screen.buttons]


def test_network_screen_opens_by_keyboard_and_lists_actions(env):
    game = env.new_game()
    press(game, KEY_DOWN)
    press(game, KEY_DOWN)
    press(game, KEY_ENTER)
    assert game.network_active and not game.menu_active
    screen = game.network_screen
    assert _labels(screen) == ['Host a game', 'Enter address', 'Back']
    assert screen.selected == 0
    texts = [c.text for c in screen.children if isinstance(c, main.Label)]
    assert 'Searching for games on this Wi-Fi…' in texts


def test_network_screen_opens_with_a_gamepad(env):
    game = env.new_game()
    game.menu.move(2)
    game._on_joy_button_down(None, 0, 0)
    game._on_joy_button_up(None, 0, 0)
    assert game.network_active


def test_network_screen_lists_found_games(env):
    game = env.new_game()
    game.show_network()
    screen = game.network_screen
    found = [
        network.FoundGame('10.0.0.5', 47400, 'Pixel 8', 2, False, 1, 0),
        network.FoundGame('10.0.0.6', 47400, 'TV', 3, True, 1, 0),
        network.FoundGame('10.0.0.7', 47400, 'Old', 1, False, 0, 0),
    ]
    env.browser.games = found
    screen.poll()
    assert _labels(screen) == ['Host a game', 'Pixel 8 · 2/4',
                               'TV · in game · 3/4', 'Enter address', 'Back']
    old = [c for c in screen.children if getattr(c, 'text', '') ==
           'Old · other version']
    assert old and old[0].disabled
    old[0].dispatch('on_press')          # cannot be joined
    assert game.net is None
    screen.move(2)                        # keeps the selection on "TV"
    env.browser.games = found[1:]
    screen.poll()
    assert _labels(screen) == ['Host a game', 'TV · in game · 3/4',
                               'Enter address', 'Back']
    assert screen.buttons[screen.selected].text == 'TV · in game · 3/4'


def test_network_screen_escape_returns_to_menu(env):
    game = env.new_game()
    game.show_network()
    press(game, KEY_ESC)
    assert game.menu_active and not game.network_active
    assert env.browser.closed


# ---- address ------------------------------------------------------------------

def _enter_address(game, text):
    game.show_network()
    game.network_screen.move(1)
    press(game, KEY_ENTER)                # "Enter address"
    assert game.address_active
    game.address_screen.ids.field.text = text
    game.address_screen.accept()
    assert game.network_active


def test_address_prefilled_from_own_network_then_last(env, tmp_path):
    game = env.new_game()
    game.show_network()
    game.show_address()
    assert game.address_screen.ids.field.text == '192.168.1.'
    game.address_screen.cancel()
    assert game.network_active and game.net is None
    game.network_settings = main.NetworkSettings(str(tmp_path / 'net.json'))
    game.show_address()
    game.address_screen.ids.field.text = '10.0.0.9:5000'
    game.address_screen.accept()
    assert main.NetworkSettings(str(tmp_path / 'net.json')).last_address == \
        '10.0.0.9:5000'
    game.net_end()
    game.show_address()
    assert game.address_screen.ids.field.text == '10.0.0.9:5000'


def test_address_corrupt_settings_fall_back(tmp_path):
    path = tmp_path / 'net.json'
    path.write_text('{nope')
    assert main.NetworkSettings(str(path)).last_address == ''
    path.write_text(json.dumps({'last_address': 5}))
    assert main.NetworkSettings(str(path)).last_address == ''


def test_address_that_cannot_be_parsed(env):
    game = env.new_game()
    _enter_address(game, '192.168.1.')
    assert game.net is None
    assert game.network_screen.message.text == 'Not an address: 192.168.1.'


def test_address_nobody_there(env):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    game = env.new_game()
    _enter_address(game, '127.0.0.1:{}'.format(port))
    env.pump()
    assert game.net is None and game.network_active
    assert game.network_screen.message.text.startswith(
        'Could not reach the host')


@pytest.mark.parametrize('reason, text', [
    ('version', 'The game versions differ'), ('full', 'The game is full')])
def test_address_refused(env, reason, text):
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    game = env.new_game()
    _enter_address(game, '127.0.0.1:{}'.format(listener.getsockname()[1]))
    env.pump(3)
    conn, _ = listener.accept()
    conn.sendall(network.encode({'t': 'refuse', 'reason': reason}))
    env.pump()
    assert game.net is None and game.network_active
    assert game.network_screen.message.text == text
    conn.close()
    listener.close()


def test_address_joins_a_host(env):
    host = env.host()
    client = env.new_game()
    _enter_address(client, '127.0.0.1:{}'.format(host.net.session.port))
    env.pump()
    assert client.select_active and client.select.mirror
    assert client.select.info.text == 'Game hosted by TV'


def test_device_name_and_multicast_lock_on_desktop():
    assert main.device_name()
    lock = main.MulticastLock()
    assert lock.acquire() is False
    lock.release()
    assert lock.lock is None


# ---- hosting and the shared join screen ---------------------------------------

def test_host_join_shows_address_and_announces(env):
    host = env.host()
    assert host.select.info.text == 'Hosting on 192.168.1.20:{}'.format(
        host.net.session.port)
    host.net.poll()
    assert env.announcers[0].ticks[-1] == (0, False)
    press(host, KEY_SPACE)
    host.net.poll()
    assert host.select.slots[0] == ('keys', 0)
    assert env.announcers[0].ticks[-1] == (1, False)


def test_host_join_client_gamepad_takes_the_next_slot(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    pad_fire(client)
    env.pump()
    assert host.net.lobby.slots[:2] == [('keys', 0), ('net', 1, ('pad', 0))]
    assert host.select.device_label(host.net.lobby.slots[1]) == \
        'Gamepad 1 · Pixel 8'
    assert client.net.lobby.slots[1] == ('pad', 0)
    assert client.select.device_label(('pad', 0)) == \
        'Gamepad 1 · this device'
    assert client.select.device_label(client.net.lobby.slots[0]) == \
        'Keys set 1 · TV'


def test_host_join_keyboard_set_1_on_both_machines(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    press(client, KEY_SPACE)
    env.pump()
    assert host.net.lobby.slots[:2] == [('keys', 0), ('net', 1, ('keys', 0))]
    press(client, KEY_D, SC_D)           # the client's set: its own slot
    env.pump()
    assert host.ship_colors.colors[:2] == ['blue', 'red']


def test_host_join_client_cannot_change_another_slot(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    env.pump()
    client.net.touch(slot=0, button='next')
    client.net.touch(slot=0, button='leave')
    env.pump()
    assert host.net.lobby.slots[0] == ('keys', 0)
    assert host.ship_colors.colors[0] == 'blue'


def test_host_join_disconnect_frees_the_slot(env):
    host = env.host()
    client = env.client(host)
    pad_fire(client)
    env.pump()
    assert host.net.lobby.slots[0] == ('net', 1, ('pad', 0))
    client.net.session.conn.sock.close()     # the app is gone
    client.net.closed = True
    client.net = None
    env.pump()
    assert host.net.lobby.slots == [None] * 4


def test_host_join_escape_closes_everything(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_ESC)
    assert host.menu_active and host.net is None
    assert env.announcers[0].closed
    env.pump()
    assert client.menu_active and client.net is None
    assert client.menu.ids.message.text == 'The host ended the game'


# ---- the client's join screen -------------------------------------------------

def test_client_join_mirrors_the_host(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    env.pump()
    assert client.net.lobby.slots[0] == ('net', 0, ('keys', 0))
    assert client.select.flashing[0]          # the host's flash shows too
    press(client, KEY_SPACE)
    env.pump()
    press(client, KEY_D, SC_D)                # colour
    env.pump()
    press(client, KEY_SPACE)                  # ready
    env.pump()
    assert host.net.lobby.ready[1] and client.net.lobby.ready[1]
    assert host.ship_colors.colors[1] == client.net.colors.colors[1]
    assert client.select.panels[1]['ready'].text == 'Ready!'


def test_client_join_panel_buttons_ask_the_host(env):
    host = env.host()
    client = env.client(host)
    client.select.join_touch('left')
    env.pump()
    assert host.net.lobby.slots[0] == ('net', 1, ('touch', 'left'))
    assert client.select.side_buttons['left'].disabled
    client.select.change(0, 1)
    env.pump()
    assert host.ship_colors.colors[0] != 'blue'
    client.select.toggle_ready(0)
    env.pump()
    assert host.net.lobby.ready[0]
    client.select.leave(0)
    env.pump()
    assert host.net.lobby.slots[0] is None


def test_join_panel_buttons_only_for_own_players(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    press(client, KEY_SPACE)
    env.pump()
    for game, own, other in ((host, 0, 1), (client, 1, 0)):
        panels = game.select.panels
        assert not any(panels[own][b].disabled
                       for b in ('prev', 'next', 'ready', 'leave'))
        assert all(panels[other][b].disabled
                   for b in ('prev', 'next', 'ready', 'leave'))


def test_client_join_escape_frees_its_slot(env):
    host = env.host()
    client = env.client(host)
    pad_fire(client)
    env.pump()
    press(client, KEY_ESC)
    assert client.menu_active and client.net is None
    env.pump()
    assert host.net.lobby.slots == [None] * 4 and host.select_active


# ---- the running game ---------------------------------------------------------

def test_host_game_starts_on_both_devices(env):
    host, client = started(env)
    assert len(host.spaceships) == 2
    assert sorted(client.mirror_ships) == [0, 1]
    assert client.controls[0] is None              # the host's player
    assert isinstance(client.controls[1].spaceship, main.RemoteShip)
    assert host.net.lobby.state(0) == 'playing'


def test_host_game_client_control_and_fire(env):
    host, client = started(env)
    ship = host.controls[1].spaceship
    client.net.send({'t': 'ctl', 'slot': 1, 'thrust': 0.5, 'turn': -1})
    client.net.send({'t': 'fire', 'slot': 1})
    env.pump()
    assert ship.thrust and ship.thrust_level == 0.5
    assert ship.angle_rotation == 3
    assert [s.spaceship for s in host.shots] == [ship]
    client.net.send({'t': 'ctl', 'slot': 0, 'thrust': 1, 'turn': 1})
    env.pump()                                     # not the client's slot
    assert not host.controls[0].spaceship.thrust


def test_host_game_snapshot_has_the_world(env):
    host, client = started(env)
    host.generate_asteroid(0)
    host.spaceships[0].shot()
    sent = []
    host.net.session.snapshot = sent.append
    host.update(1 / 60)
    [snap] = sent
    assert [s[0] for s in snap['ships']] == [0, 1]
    assert [a[0] for a in snap['ast']] == [a.net_id for a in host.asteroids]
    assert [s[0] for s in snap['shots']] == [s.net_id for s in host.shots]
    network.check(json.loads(network.encode(snap)))


def test_host_game_silent_client_keeps_its_last_input(env):
    host, client = started(env)
    client._on_key_down(None, ord('w'), 26)          # thrust, then silence
    env.pump()
    ship = host.controls[1].spaceship
    for _ in range(30):
        host.update(1 / 60)
    assert ship.thrust and ship.speed == 3


def test_host_game_with_only_client_players(env):
    host = env.host()
    client = env.client(host)
    press(client, KEY_SPACE)
    pad_fire(client)
    env.pump()
    press(client, KEY_SPACE)
    pad_fire(client)
    env.pump()
    assert host.in_net_game and len(host.spaceships) == 2
    assert all(c.touch == 'off' for c in host.controls if c)
    env.frames(host)
    assert sorted(client.mirror_ships) == [0, 1]


def test_remote_ship_keys_turn_the_host_ship(env):
    host, client = started(env)
    client._on_key_down(None, KEY_A, SC_A)
    env.pump()
    assert host.controls[1].spaceship.angle_rotation == 3
    assert host.controls[0].spaceship.angle_rotation == 0
    client._on_key_up(None, KEY_A, SC_A)
    env.pump()
    assert host.controls[1].spaceship.angle_rotation == 0


def test_remote_ship_trigger_gives_half_thrust(env):
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    pad_fire(client)
    env.pump()
    press(host, KEY_SPACE)
    pad_fire(client)
    env.pump()
    env.frames(host)                              # the ships arrive
    client.pad_bindings.bind_trigger(None, 5, -1.0, 1.0)
    client._on_joy_axis(None, 0, 5, 0)            # half way from -1 to 1
    env.pump()
    ship = host.controls[1].spaceship
    half = main.trigger_level(client.pad_bindings.profile(None)['trigger'], 0)
    assert 0.4 < half < 0.6                        # half power, after the dead zone
    assert ship.thrust and ship.thrust_level == pytest.approx(half, abs=1e-3)


def test_remote_ship_touch_joystick(env):
    import test_game as tg
    host = env.host()
    client = env.client(host)
    press(host, KEY_SPACE)
    client.select.join_touch('left')
    env.pump()
    press(host, KEY_SPACE)
    client.select.toggle_ready(1)
    env.pump()
    env.frames(host)
    layout = client.controls[1].touch_buttons
    assert layout.active and client.controls[1].touch == 'on'
    touch, _ = tg._touch_down(layout, tg._stick_pos(layout, 1, 0))
    env.pump()
    remote = client.controls[1].spaceship
    ship = host.controls[1].spaceship
    assert remote.thrust and ship.thrust
    tg._release(touch, layout.stick)
    env.pump()
    assert not ship.thrust


def test_remote_ship_sends_only_changes():
    sent = []

    class Net:
        def send(self, message):
            sent.append(message)
    ship = main.RemoteShip(2, Net())
    ship.turn_left()
    ship.turn_left()
    ship.thrust_level = 1
    ship.thrust_on()
    ship.thrust_level = 0.4
    ship.shot()
    assert sent == [
        {'t': 'ctl', 'slot': 2, 'thrust': 0.0, 'turn': -1},
        {'t': 'ctl', 'slot': 2, 'thrust': 1.0, 'turn': -1},
        {'t': 'ctl', 'slot': 2, 'thrust': 0.4, 'turn': -1},
        {'t': 'fire', 'slot': 2}]


def test_field_view_scales_and_centres(env, monkeypatch):
    view = main.FieldView((1600, 900))
    width, height = Window.size
    s = min(width / 1600, height / 900)
    assert view.scale == pytest.approx(s)
    left, bottom = view.to_screen(0, 0)
    right, top = view.to_screen(1600, 900)
    assert left >= -0.01 and bottom >= -0.01
    assert right <= width + 0.01 and top <= height + 0.01
    assert view.to_screen(400, 0)[0] == pytest.approx(left + s * 400)
    # a 4:3 field in a wider window: bars at the sides, whole field shown
    view.set_field((800, 600))
    s = min(width / 800, height / 600)
    assert view.scale == pytest.approx(s)
    assert view.to_screen(400, 300) == pytest.approx((width / 2, height / 2))
    view.detach()


def test_field_view_mirrors_ships_shots_asteroids_and_sounds(env):
    host, client = started(env)
    host.generate_asteroid(0)
    while not host.asteroids:
        host.generate_asteroid(0)
    host.spaceships[0].shot()
    env.frames(host)
    assert sorted(client.mirror_asteroids) == [a.net_id for a in host.asteroids]
    assert sorted(client.mirror_shots) == [s.net_id for s in host.shots]
    for slot, ship in client.mirror_ships.items():
        assert tuple(ship.pos) == pytest.approx(tuple(host.spaceships[slot].pos), abs=0.1)
    host.remove_shot(host.shots[0])
    host.asteroids[0].pos = host.spaceships[1].pos     # a hit
    env.frames(host)
    assert client.mirror_shots == {}
    assert client.mirror_ships[1].lives == host.spaceships[1].lives == 2
    assert any(e.parent is client.field_view for e in client.explosions)
    status = [s for s in client.statuses if s.column == 1][0]
    assert status.spaceship.lives == 2


def test_field_view_engine_sound_follows_thrust(env):
    host, client = started(env)
    host.controls[0].press('up')
    env.frames(host)
    assert client.mirror_ships[0].thrust
    assert main.Spaceship.thrusting
    host.controls[0].release('up')
    env.frames(host)
    assert not client.mirror_ships[0].thrust


# ---- joining and leaving a running game ---------------------------------------

def test_late_join_client_gamepad_as_player_3(env):
    host, client = started(env)
    before = [(tuple(s.pos), s.lives, s.points) for s in host.spaceships]
    pad_fire(client)                       # a pad on the watching client
    env.pump()
    assert host.net.lobby.slots[2] == ('net', 1, ('pad', 0))
    assert len(host.spaceships) == 3
    assert [(tuple(s.pos), s.lives, s.points)
            for s in host.spaceships[:2]] == before
    env.frames(host)
    assert sorted(client.mirror_ships) == [0, 1, 2]
    assert client.controls[2] is not None


def test_late_join_host_keyboard(env):
    host = env.host()
    client = env.client(host)
    press(client, KEY_SPACE)
    pad_fire(client)
    env.pump()
    press(client, KEY_SPACE)
    pad_fire(client)
    env.pump()
    assert host.in_net_game and host.prompt.visible
    press(host, KEY_SPACE)
    assert host.net.lobby.slots[2] == ('keys', 0)
    assert len(host.spaceships) == 3 and not host.prompt.visible


def test_late_join_starts_away_from_asteroids(env):
    host, client = started(env)
    asteroid = main.Asteroid()
    # right where player 3 starts (main.START_OFFSETS: below the centre)
    start = (main.Vector(*host.center) - main.Vector(45, 45)
             + main.Vector(*main.START_OFFSETS[2]) * 90 * 1.5)
    asteroid.pos = tuple(start)
    host.add_widget(asteroid)
    host.asteroids.append(asteroid)
    pad_fire(client)
    env.pump()
    ship = host.spaceships[2]
    assert main.Vector(*ship.pos).distance(asteroid.pos) >= 200
    assert ship.lives == 3 and ship.points == 0


def test_late_join_full_and_out(env):
    host, client = started(env)
    pad_fire(client, 0)
    pad_fire(client, 1)
    env.pump()
    assert len(host.spaceships) == 4
    other = env.client(host)                 # a third machine watches
    env.frames(host)
    pad_fire(other)
    env.pump()
    assert len(host.spaceships) == 4
    assert other.prompt.label.text == 'The game is full'
    ship = host.controls[2].spaceship        # client's pad 0 loses its ship
    ship.lives = 0
    host.lose_spaceship(ship)
    env.pump()
    assert host.net.lobby.out[2]
    pad_fire(client, 0)                       # out until the game ends
    env.pump()
    assert host.net.lobby.slots[2] == ('net', 1, ('pad', 0))
    assert len(host.spaceships) == 3


def test_late_join_prompt_returns_when_own_ship_is_out(env):
    host, client = started(env)
    assert not host.prompt.visible
    ship = host.controls[0].spaceship
    ship.lives = 0
    host.lose_spaceship(ship)
    assert host.prompt.visible
    assert host.prompt.label.text == 'Press FIRE to join · 2 slots free'


def test_late_join_survival_counts_from_joining(env):
    host, client = started(env)
    host.elapsed = 30
    pad_fire(client)
    env.pump()
    host.elapsed = 50
    ship = host.controls[2].spaceship
    ship.lives = 0
    host.lose_spaceship(ship)
    result = [r for r in host.results if r.slot == 2][0]
    assert result.survived == pytest.approx(20)


def test_watch_on_connect_shows_the_game_and_the_prompt(env):
    host, client = started(env)
    watcher = env.client(host)
    assert watcher.in_net_game and not watcher.network_active
    env.frames(host)
    assert sorted(watcher.mirror_ships) == [0, 1]
    assert len(watcher.statuses) == 2
    assert watcher.prompt.visible
    assert watcher.prompt.label.text == 'Press FIRE to join · 2 slots free'
    assert all(c is None for c in watcher.controls)


def test_watch_tap_to_join_at_the_left_seat(env):
    host, client = started(env)
    watcher = env.client(host)
    watcher.has_touch = True
    env.frames(host)
    strip = watcher.prompt.strips['left']
    assert strip.opacity == 1 and not strip.disabled
    strip.dispatch('on_press')
    env.pump()
    assert host.net.lobby.slots[2] == ('net', 2, ('touch', 'left'))
    env.frames(host)
    controls = watcher.controls[2]
    assert controls.side == 'left' and controls.touch_buttons.active
    assert not watcher.prompt.visible


def test_net_leave_client_leaves_others_play_on(env):
    host, client = started(env)
    third = env.client(host)
    pad_fire(third)
    env.pump()
    env.frames(host)
    assert len(host.spaceships) == 3
    host.spaceships[2].points = 4
    third.pause()
    third.confirm_leave()
    third.confirm_screen.yes()            # "Main menu", confirmed
    env.pump()
    assert third.menu_active and third.net is None
    assert host.in_net_game and len(host.spaceships) == 2
    assert host.net.lobby.slots[2] is None
    assert [r.points for r in host.results if r.slot == 2] == [4]
    host.resume()                          # the leaver had paused the game
    env.frames(host)
    assert sorted(client.mirror_ships) == [0, 1]
    pad_fire(client)                       # the free slot is taken again
    env.pump()
    assert host.net.lobby.slots[2] == ('net', 1, ('pad', 0))


def test_net_leave_client_app_closed(env):
    host, client = started(env)
    client.net.session.conn.sock.close()
    client.net.closed = True
    client.net = None
    env.pump()
    assert len(host.spaceships) == 1 and host.net.lobby.slots[1] is None
    assert host.in_net_game


def test_net_leave_last_ship_leaving_ends_the_game(env):
    host = env.host()
    client = env.client(host)
    press(client, KEY_SPACE)
    pad_fire(client)
    env.pump()
    press(client, KEY_SPACE)
    pad_fire(client)
    env.pump()
    client.net.session.conn.sock.close()
    client.net.closed = True
    client.net = None
    env.pump()
    assert host.results_active
    assert sorted(r.slot for r in host.results_screen.results) == [0, 1]


def test_net_leave_host_ends_the_game(env):
    host, client = started(env)
    host.pause()
    env.pump()
    host.confirm_leave()
    host.confirm_screen.yes()
    env.pump()
    assert client.menu_active
    assert client.menu.ids.message.text == 'The host ended the game'


def test_net_leave_host_connection_lost(env):
    host, client = started(env)
    for conn in host.net.session.clients.values():
        conn.sock.close()
    host.net.session.clients = {}
    env.pump()
    assert client.menu_active and client.net is None
    assert client.menu.ids.message.text == 'Connection to the host lost'


# ---- pause --------------------------------------------------------------------

def test_net_pause_from_client_and_continue_on_host(env):
    host, client = started(env)
    client._on_key_down(None, ord('w'), 26)      # held through the pause
    env.pump()
    press(client, KEY_ESC)
    assert client.paused                          # at once, on the client
    env.pump()
    assert host.paused and hasattr(host, 'pause_screen')
    ship = host.controls[1].spaceship
    assert not ship.thrust
    host.pause_screen.resume()
    env.pump()
    assert not host.paused and not client.paused
    client._on_key_up(None, ord('w'), 26)
    env.pump()
    for _ in range(5):
        host.update(1 / 60)
    assert not ship.thrust


def test_net_pause_with_a_silent_host(env):
    host, client = started(env)
    host.net.event.cancel()
    host.net.closed = True                       # the host stops answering
    press(client, KEY_ESC)
    assert client.paused and hasattr(client, 'pause_screen')
    client.confirm_leave()
    client.confirm_screen.yes()
    assert client.menu_active and client.net is None


def test_net_pause_resume_closes_the_leave_question(env):
    host, client = started(env)
    press(host, KEY_ESC)
    env.pump()
    client.confirm_leave()
    host.pause_screen.resume()
    env.pump()
    assert not client.paused and not hasattr(client, 'confirm_screen')


# ---- results and the shared leaderboard ---------------------------------------

def _end(env, host):
    for ship in list(host.spaceships):
        ship.lives = 0
        host.lose_spaceship(ship)
    env.pump()


def test_net_results_on_every_device(env):
    host, client = started(env)
    host.spaceships[1].points = 6
    _end(env, host)
    assert host.results_active and client.results_active
    assert [(r.slot, r.points) for r in client.results_screen.results] == \
        [(0, 0), (1, 6)]
    again = client.results_screen.ids.btn_again
    assert again.text == 'Waiting for the host' and again.disabled
    assert again not in client.results_screen.buttons
    assert host.results_screen.ids.btn_again.text == 'Play again'


def test_play_again_network_game(env):
    host, client = started(env)
    _end(env, host)
    host.results_screen.armed_at = 0
    host.results_screen.play_again()
    env.pump()
    assert host.in_net_game and client.in_net_game
    assert len(host.spaceships) == 2
    assert host.net.lobby.slots[:2] == [('keys', 0), ('net', 1, ('keys', 0))]


def test_play_again_too_few_players(env):
    host, client = started(env)
    _end(env, host)
    client.results_screen.go_menu()  # the client leaves after the game
    env.pump()
    host.results_screen.armed_at = 0
    host.results_screen.play_again()
    assert host.select_active and isinstance(host.select, main.JoinScreen)
    assert host.net is not None and host.select.slots[0] == ('keys', 0)
    assert host.net.phase == 'lobby'


def test_play_again_client_back_on_join_screen(env):
    host, client = started(env)
    third = env.client(host)
    _end(env, host)
    client.results_screen.go_menu()
    env.pump()
    host.results_screen.armed_at = 0
    host.results_screen.play_again()
    env.pump()
    assert third.select_active and third.select.mirror


def test_survival_time_of_a_leaver(env):
    host, client = started(env)
    host.elapsed = 12
    client.game_stop()                     # leaves through the pause screen
    env.pump()
    assert [round(r.survived) for r in host.results if r.slot == 1] == [12]


def test_shared_leaderboard_on_connect(env):
    host = env.host()
    host.leaderboard.add(12, 20, 'Host')
    phone = env.new_game()
    phone.leaderboard.add(30, 61, 'Ann')
    phone.show_network()
    phone.join_game('127.0.0.1', host.net.session.port, 'TV')
    env.pump()
    assert [e['name'] for e in host.leaderboard.entries] == ['Ann', 'Host']
    assert [e['name'] for e in phone.leaderboard.entries] == ['Ann', 'Host']
    phone.show_menu()
    phone.show_network()
    phone.join_game('127.0.0.1', host.net.session.port, 'TV')
    env.pump()
    assert len(host.leaderboard.entries) == 2
    assert len(phone.leaderboard.entries) == 2


def test_shared_leaderboard_kept_after_disconnect(env, tmp_path):
    host = env.host()
    host.leaderboard = main.Leaderboard(str(tmp_path / 'host.json'))
    phone = env.new_game()
    phone.leaderboard.add(30, 61, 'Ann')
    phone.show_network()
    phone.join_game('127.0.0.1', host.net.session.port, 'TV')
    env.pump()
    phone.show_menu()
    env.pump()
    again = main.Leaderboard(str(tmp_path / 'host.json'))
    assert [e['name'] for e in again.entries] == ['Ann']


def test_shared_leaderboard_save_on_a_client(env):
    host, client = started(env)
    third = env.client(host)
    host.spaceships[1].points = 6
    host.elapsed = 33
    _end(env, host)
    screen = client.results_screen
    screen.armed_at = 0
    screen.save_score()
    client.name_screen.ids.field.text = 'Ann'
    client.name_screen.accept()
    env.pump()
    for game in (host, client, third):
        assert [(e['name'], e['points'], e['seconds'])
                for e in game.leaderboard.entries] == [('Ann', 6, 33)]
        button = game.results_screen.ids.btn_save
        assert button.text == 'Saved on Pixel 8' and button.disabled
    assert client.leaderboard.last_name == 'Ann'
    assert host.leaderboard.last_name == ''


def test_shared_leaderboard_two_saves_at_once(env):
    host, client = started(env)
    _end(env, host)
    for game, name in ((host, 'Hal'), (client, 'Ann')):
        game.results_screen.armed_at = 0
        game.results_screen.save_score()
        game.name_screen.ids.field.text = name
        game.name_screen.accept()
    env.pump()
    assert len(host.leaderboard.entries) == 1
    assert client.leaderboard.entries == host.leaderboard.entries
    assert host.leaderboard.entries[0]['name'] == 'Hal'


def test_shared_leaderboard_single_player_sends_nothing(env, monkeypatch):
    game = env.new_game()
    sent = []
    monkeypatch.setattr(network.Connection, 'send',
                        lambda self, m: sent.append(m))
    game.game_start()
    game.spaceships[0].lives = 0
    game.lose_spaceship(game.spaceships[0])
    game.results_screen.store_score('Solo')
    assert game.net is None and sent == []
    assert game.leaderboard.entries[0]['name'] == 'Solo'

