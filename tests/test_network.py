"""The network protocol, sessions and discovery (network.py), without Kivy."""

import json
import socket

import pytest

import network
from network import (
    Announcer, Browser, ClientSession, Decoder, HostSession, ProtocolError,
    check, encode, parse_address,
)


# ---- codec ------------------------------------------------------------------

SLOT = [0, ['keys', 0], 'ready', 'Desk']
VALID = [
    {'t': 'hello', 'proto': 1, 'name': 'Pixel 8'},
    {'t': 'welcome', 'peer': 2, 'phase': 'game', 'name': 'TV'},
    {'t': 'refuse', 'reason': 'full'},
    {'t': 'lobby', 'slots': [SLOT, None, [3, ['pad', 7], 'out', 'Tab'], None],
     'colors': ['blue', 'green', 'red', 'yellow'],
     'flash': [True, False, False, False], 'name': 'TV', 'free': 2,
     'phase': 'lobby'},
    {'t': 'act', 'device': ['touch', 'left'], 'action': 'fire'},
    {'t': 'touch', 'side': 'top', 'slot': None, 'button': None},
    {'t': 'touch', 'side': None, 'slot': 2, 'button': 'ready'},
    {'t': 'start', 'slots': [SLOT, None, None, None],
     'colors': ['blue', 'green', 'red', 'yellow'], 'field': [800, 600],
     'elapsed': 12.5},
    {'t': 'denied', 'device': ['pad', 0], 'reason': 'out'},
    {'t': 'ctl', 'slot': 1, 'thrust': 0.5, 'turn': -1},
    {'t': 'fire', 'slot': 3},
    {'t': 'snap', 'field': [800, 600], 'elapsed': 3.25,
     'ships': [[0, 10.5, 20, 90, 1, 3, 7]], 'ast': [[4, 1, 2, 33.3]],
     'shots': [[9, 5, 6]], 'boom': [[1, 1]]},
    {'t': 'pause'},
    {'t': 'resume'},
    {'t': 'over', 'game': 'ab12', 'results': [[0, 'blue', 5, 31.5]]},
    {'t': 'lb', 'entries': [['00ff', 'Ann', 30, 61]]},
    {'t': 'save', 'game': 'ab12', 'name': 'Ann'},
    {'t': 'saved', 'game': 'ab12', 'by': 'Pixel 8'},
    {'t': 'bye', 'reason': 'host-ended'},
]


@pytest.mark.parametrize('message', VALID, ids=lambda m: m['t'])
def test_codec_round_trip(message):
    [back] = Decoder().feed(encode(message))
    assert back['t'] == message['t']
    if message['t'] == 'lb':        # entries come back as the game keeps them
        back['entries'] = [[e['id'], e['name'], e['points'], e['seconds']]
                           for e in back['entries']]
    assert json.loads(encode(back)) == json.loads(encode(message))


def test_codec_devices_and_slots_become_tuples():
    [lobby] = Decoder().feed(encode(VALID[3]))
    assert lobby['slots'][0] == (0, ('keys', 0), 'ready', 'Desk')
    assert lobby['slots'][1] is None
    [act] = Decoder().feed(encode(VALID[4]))
    assert act['device'] == ('touch', 'left')


def test_codec_optional_fields_default_to_none():
    [bye] = Decoder().feed(b'{"t":"bye"}\n')
    assert bye == {'t': 'bye', 'reason': None}


def test_codec_line_split_in_two_chunks():
    data = encode(VALID[0]) + encode(VALID[9])
    decoder = Decoder()
    assert decoder.feed(data[:7]) == []
    first, second = decoder.feed(data[7:])
    assert first['t'] == 'hello' and second['t'] == 'ctl'


def test_codec_oversized_line_is_rejected():
    decoder = Decoder()
    with pytest.raises(ProtocolError):
        decoder.feed(b'{"t":"hello","name":"' + b'x' * network.MAX_LINE)
    with pytest.raises(ProtocolError):
        encode({'t': 'hello', 'proto': 1, 'name': 'x' * network.MAX_LINE})


@pytest.mark.parametrize('line', [
    b'not json\n',
    b'[1,2]\n',
    b'{"proto":1}\n',                                   # no type
    b'{"t":"launch"}\n',                                # unknown type
    b'{"t":"hello","name":"x"}\n',                      # missing field
    b'{"t":"hello","proto":"1","name":"x"}\n',          # wrong type
    b'{"t":"ctl","slot":4,"thrust":0,"turn":0}\n',      # slot out of range
    b'{"t":"ctl","slot":0,"thrust":2,"turn":0}\n',      # thrust above 1
    b'{"t":"ctl","slot":0,"thrust":0,"turn":5}\n',      # bad turn
    b'{"t":"ctl","slot":true,"thrust":0,"turn":0}\n',   # bool is not int
    b'{"t":"act","device":["mouse",0],"action":"fire"}\n',
    b'{"t":"act","device":["keys",2],"action":"fire"}\n',
    b'{"t":"act","device":["touch","middle"],"action":"fire"}\n',
    b'{"t":"act","device":["pad",0],"action":"jump"}\n',
    b'{"t":"lobby","slots":[],"colors":[],"flash":[],"name":"x","free":0,'
    b'"phase":"lobby"}\n',
    b'{"t":"snap","field":[1,2],"elapsed":0,"ships":[[0,1,2]],'
    b'"ast":[],"shots":[],"boom":[]}\n',
    b'\xff\xfe\n',
])
def test_codec_rejects_bad_messages(line):
    with pytest.raises(ProtocolError):
        Decoder().feed(line)


def test_codec_skips_invalid_leaderboard_entries():
    [lb] = Decoder().feed(encode({'t': 'lb', 'entries': [
        ['ab', 'Ann', 30, 61],
        ['XYZ!', 'Bad id', 1, 1],
        ['cd', '', 1, 1],
        ['ef', 'Neg', -1, 1],
        ['01', 'x' * 13, 1, 1],
        'junk',
    ]}))
    assert lb['entries'] == [
        {'id': 'ab', 'name': 'Ann', 'points': 30, 'seconds': 61}]


# ---- sessions ---------------------------------------------------------------

class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def pump(*parties, rounds=50):
    """Poll everything a few times; the events each party got."""
    got = [[] for _ in parties]
    for _ in range(rounds):
        for i, party in enumerate(parties):
            got[i] += party.poll()
    return got


@pytest.fixture
def host():
    h = HostSession('Host', port=0, tries=1, address='127.0.0.1')
    yield h
    h.close()


def connect(host, name='Phone', clock=None):
    kwargs = {'clock': clock} if clock else {}
    return ClientSession('127.0.0.1', host.port, name, **kwargs)


def test_session_handshake(host):
    client = connect(host)
    host_events, client_events = pump(host, client)
    assert ('connect', 1, 'Phone') in host_events
    [(kind, welcome)] = client_events
    assert kind == 'welcome'
    assert welcome['peer'] == 1 and welcome['phase'] == 'lobby'
    assert welcome['name'] == 'Host'
    assert client.peer == 1 and client.state == 'ready'
    client.send({'t': 'fire', 'slot': 2})
    host.send(1, {'t': 'pause'})
    host_events, client_events = pump(host, client)
    assert host_events == [('message', 1, {'t': 'fire', 'slot': 2})]
    assert client_events == [('message', {'t': 'pause'})]
    client.close()


def test_session_phase_is_told_in_welcome(host):
    host.phase = 'game'
    client = connect(host)
    _, events = pump(host, client)
    assert events[0][1]['phase'] == 'game'
    client.close()


def test_session_version_refused(host, monkeypatch):
    client = connect(host)
    monkeypatch.setattr(network, 'NET_PROTOCOL', 0)   # the client is older
    while client.state == 'connecting':
        client.poll()
    monkeypatch.undo()
    host_events, client_events = pump(host, client)
    assert client_events == [('fail', 'version')]
    assert host_events == [] and host.clients == {}


def test_session_ninth_client_refused(host):
    clients = [connect(host, 'C{}'.format(i)) for i in range(9)]
    events = pump(host, *clients)
    assert len(host.clients) == 8
    outcomes = sorted(e[0][0] for e in events[1:])
    assert outcomes == ['fail'] + ['welcome'] * 8
    assert [('fail', 'full')] in events[1:]
    for client in clients:
        client.close()


def test_session_garbage_connection_closed_others_stay(host):
    client = connect(host)
    pump(host, client)
    raw = socket.create_connection(('127.0.0.1', host.port))
    raw.sendall(b'\x00garbage\xff\n')
    pump(host, client)
    raw.settimeout(2)
    assert raw.recv(100) == b''          # closed by the host
    raw.close()
    assert list(host.clients) == [1]
    client.send({'t': 'pause'})
    assert pump(host, client)[0] == [('message', 1, {'t': 'pause'})]
    client.close()


def test_session_bad_message_from_client_closes_it(host):
    client = connect(host)
    pump(host, client)
    client.conn.outbox += b'{"t":"ctl","slot":9,"thrust":0,"turn":0}\n'
    host_events, client_events = pump(host, client)
    assert host_events == [('close', 1)]
    assert client_events == [('close',)]


def test_session_client_closing_is_reported_to_host(host):
    client = connect(host)
    pump(host, client)
    client.conn.sock.close()             # app killed: no goodbye
    client.conn.closed = True
    assert pump(host)[0] == [('close', 1)]


def test_session_host_closing_is_reported_to_client(host):
    client = connect(host)
    pump(host, client)
    host.listener.close()
    for conn in host.clients.values():
        conn.sock.close()
    host.listener = None
    host.clients = {}
    assert pump(client)[0] == [('close',)]


def test_session_goodbye_from_host(host):
    client = connect(host)
    pump(host, client)
    host.close()
    events = pump(client)[0]
    assert events == [('message', {'t': 'bye', 'reason': 'host-ended'}),
                      ('close',)]


def test_session_idle_connection_stays_open(host):
    clock = Clock()
    client = connect(host, clock=clock)
    pump(host, client)
    clock.now += 30          # no pings, no idle limit
    host_events, client_events = pump(host, client)
    assert host_events == [] and client_events == []
    assert client.state == 'ready' and 1 in host.clients
    client.close()


def test_session_slow_reader_gets_only_newest_snapshot(host):
    client = connect(host)
    pump(host, client)
    conn = host.clients[1]
    for n in range(5):
        host.snapshot({'t': 'snap', 'field': [1, 1], 'elapsed': n,
                       'ships': [], 'ast': [], 'shots': [], 'boom': []})
    host.send(1, {'t': 'pause'})
    assert conn.snapshot is not None and len(conn.outbox) > 0
    host_events, client_events = pump(host, client)
    kinds = [(m['t'], m.get('elapsed')) for _, m in client_events]
    assert kinds == [('pause', None), ('snap', 4)]
    client.close()


def test_session_outbox_overflow_closes_connection(host):
    client = connect(host)
    pump(host, client)
    conn = host.clients[1]
    conn.outbox += b'x' * network.MAX_OUTBOX
    host.send(1, {'t': 'pause'})
    assert conn.closed
    assert pump(host)[0] == [('close', 1)]


def test_session_unreachable_by_refusal():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()                         # nobody listens there
    client = ClientSession('127.0.0.1', port, 'Phone')
    assert pump(client)[0] == [('fail', 'unreachable')]


def test_session_unreachable_after_connect_limit():
    clock = Clock()
    listener = socket.socket()           # accepts but never answers hello
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    client = ClientSession('127.0.0.1', listener.getsockname()[1], 'Phone',
                           clock=clock)
    assert pump(client)[0] == []
    clock.now += network.CONNECT_TIMEOUT + 0.1
    assert pump(client)[0] == [('fail', 'unreachable')]
    listener.close()


def test_session_takes_next_free_port():
    first = HostSession('A', port=0, tries=1, address='127.0.0.1')
    try:
        second = HostSession('B', port=first.port, tries=3,
                             address='127.0.0.1')
        assert first.port < second.port <= first.port + 2
        second.close()
    finally:
        first.close()


# ---- discovery and addresses ------------------------------------------------

@pytest.fixture
def browser():
    clock = Clock()
    b = Browser(port=0, clock=clock)
    b.clock_ = clock
    yield b
    b.close()


def announcer_to(browser, name='TV', port=47400):
    return Announcer(name, port, target=('127.0.0.1', browser.port),
                     clock=browser.clock_)


def wait_for(browser, count=1):
    import time
    for _ in range(100):
        games = browser.poll()
        if len(games) >= count:
            return games
        time.sleep(0.01)
    return browser.poll()


def test_browse_finds_announced_host(browser):
    announcer = announcer_to(browser)
    assert announcer.tick(2, False)
    [game] = wait_for(browser)
    assert (game.address, game.port, game.name) == ('127.0.0.1', 47400, 'TV')
    assert game.players == 2 and not game.playing and game.compatible
    announcer.close()


def test_browse_announces_once_a_second_and_playing_flag(browser):
    announcer = announcer_to(browser)
    assert announcer.tick(3, True)
    assert not announcer.tick(3, True)         # too soon
    browser.clock_.now += network.ANNOUNCE_INTERVAL
    assert announcer.tick(3, True)
    [game] = wait_for(browser)
    assert game.playing and game.players == 3
    announcer.close()


def test_browse_host_expires(browser):
    announcer = announcer_to(browser)
    announcer.tick(1, False)
    assert wait_for(browser)
    browser.clock_.now += network.HOST_EXPIRY + 0.1
    assert browser.poll() == []
    announcer.close()


def test_browse_flags_other_version(browser, monkeypatch):
    announcer = announcer_to(browser)
    monkeypatch.setattr(network, 'NET_PROTOCOL', 99)
    announcer.tick(1, False)
    monkeypatch.undo()
    [game] = wait_for(browser)
    assert not game.compatible
    announcer.close()


@pytest.mark.parametrize('data', [
    b'garbage', b'\xff', b'[]', b'{"game":"other","port":1}',
    b'{"game":"spacepilgrim","port":0,"name":"x","players":1,"proto":1}',
    b'{"game":"spacepilgrim","port":1,"name":"x","players":9,"proto":1}',
])
def test_browse_ignores_foreign_datagrams(browser, data):
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.sendto(data, ('127.0.0.1', browser.port))
    sender.close()
    import time
    time.sleep(0.05)
    assert browser.poll() == []


@pytest.mark.parametrize('text, expected', [
    ('192.168.1.20', ('192.168.1.20', 47400)),
    (' 10.0.0.2:5000 ', ('10.0.0.2', 5000)),
    ('tv.local', ('tv.local', 47400)),
    ('my-pc:47401', ('my-pc', 47401)),
])
def test_address_parsing(text, expected):
    assert parse_address(text) == expected


@pytest.mark.parametrize('text', [
    '', '192.168.1.', '192.168.1.300', '1.2.3', '1.2.3.4:', '1.2.3.4:0',
    '1.2.3.4:70000', '1.2.3.4:x', 'a b', 'host:1:2', '-bad.host',
])
def test_address_parsing_rejects(text):
    with pytest.raises(ValueError):
        parse_address(text)


def test_address_local_is_an_ipv4_address():
    address = network.local_address()
    parts = address.split('.')
    assert len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts)
