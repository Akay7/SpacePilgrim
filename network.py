"""Local network play: the wire protocol, TCP sessions of a host and its
clients, and the UDP broadcast that announces hosted games.

Standard library only and no Kivy, so it can be tested on its own. Nothing
here blocks or starts a thread: the game calls `poll()` from its clock and
gets back a list of events.

A message is one JSON object per line, `{"t": <type>, ...}`. Every message
that arrives is checked against `SCHEMAS`; anything else closes the
connection it came on."""

import errno
import json
import re
import socket
import time

NET_PROTOCOL = 1
GAME_PORT = 47400          # TCP; the host takes the first free of PORT_TRIES
PORT_TRIES = 10
DISCOVERY_PORT = 47401     # UDP broadcast of hosted games
MAX_LINE = 64 * 1024       # bytes of one message
MAX_OUTBOX = 1024 * 1024   # bytes waiting for a client that does not read
MAX_CLIENTS = 8
CONNECT_TIMEOUT = 5.0      # seconds to set up a connection; no idle limit
ANNOUNCE_INTERVAL = 1.0
HOST_EXPIRY = 3.0          # a host not heard for this long leaves the list
SLOTS = 4
NAME_LIMIT = 64            # machine names
NICK_LIMIT = 12            # leaderboard nicknames
GAME_MAGIC = 'spacepilgrim'

SIDES = ('left', 'right', 'top', 'bottom')
ACTIONS = ('up', 'down', 'left', 'right', 'fire', 'back')
PANEL_BUTTONS = ('prev', 'next', 'ready', 'leave')
SLOT_STATES = ('joined', 'ready', 'playing', 'out')
PHASES = ('lobby', 'game', 'results')


class ProtocolError(ValueError):
    """A message that breaks the protocol: the connection is closed."""


# ---- message checks ----------------------------------------------------------
# A check is a function returning the value as the game uses it (or raising
# ProtocolError), or a tuple of the values allowed.

def _fail(what):
    raise ProtocolError(what)


def _valid(test, value):
    if isinstance(test, tuple):    # same type too: True is not 1, 1.0 not 1
        if not any(type(value) is type(v) and value == v for v in test):
            _fail('unknown value')
        return value
    return test(value)


def _int(low=0, high=None):
    def check(value):
        if (type(value) is not int or value < low
                or (high is not None and value > high)):
            _fail('bad integer')
        return value
    return check


def _num(low=None, high=None):
    def check(value):
        if (type(value) not in (int, float) or value != value      # NaN
                or (low is not None and value < low)
                or (high is not None and value > high)):
            _fail('bad number')
        return value
    return check


def _str(limit=NAME_LIMIT):
    def check(value):
        if not isinstance(value, str) or len(value) > limit:
            _fail('bad string')
        return value
    return check


def _list(item, length=None, limit=1000):
    def check(value):
        if (not isinstance(value, list) or len(value) > limit
                or (length is not None and len(value) != length)):
            _fail('bad list')
        return [_valid(item, v) for v in value]
    return check


def _row(*items):
    """A fixed-length list, each place with its own check; a tuple."""
    def check(value):
        if not isinstance(value, list) or len(value) != len(items):
            _fail('bad row')
        return tuple(_valid(item, v) for item, v in zip(items, value))
    return check


def _dict(value):
    """Checked by the receiver (leaderboard entries: Leaderboard.merge)."""
    return value if isinstance(value, dict) else _fail('not an object')


def device(value):
    """A device of the sending machine, as the game uses it: ('keys', set),
    ('pad', stick) or ('touch', side)."""
    kind, key = _row(('keys', 'pad', 'touch'), lambda v: v)(value)
    _valid({'keys': (0, 1), 'pad': _int(0, 0xffff), 'touch': SIDES}[kind], key)
    return (kind, key)


_slot = _int(0, SLOTS - 1)
_point = _list(_num(), 2)
_colors = _list(_str(16), SLOTS)
_taken = _row(_int(), device, SLOT_STATES, _str())   # peer, device, state, name
_slots = _list(lambda v: None if v is None else _taken(v), SLOTS)

SCHEMAS = {
    'hello': {'proto': _int(), 'name': _str()},
    'welcome': {'peer': _int(), 'phase': PHASES, 'name': _str()},
    'refuse': {'reason': ('version', 'full')},
    'lobby': {'slots': _slots, 'colors': _colors,
              'flash': _list((True, False), SLOTS), 'name': _str(),
              'free': _int(0, SLOTS), 'phase': PHASES},
    'act': {'device': device, 'action': ACTIONS},
    'touch': {'side': SIDES},                       # a touch strip: join
    'panel': {'slot': _slot, 'button': PANEL_BUTTONS},
    'start': {'slots': _slots, 'colors': _colors, 'field': _point,
              'elapsed': _num(0)},
    'denied': {'device': device, 'reason': ('full', 'out')},
    'ctl': {'slot': _slot, 'thrust': _num(0, 1), 'turn': (-1, 0, 1)},
    'fire': {'slot': _slot},
    'snap': {'field': _point, 'elapsed': _num(0),
             # slot, x, y, angle, thrust, lives, points
             'ships': _list(_row(_slot, _num(), _num(), _num(), _num(0, 1),
                                 _int(), _int()), limit=SLOTS),
             'ast': _list(_row(_int(), _num(), _num(), _num())),  # id x y angle
             'shots': _list(_row(_int(), _num(), _num())),        # id x y
             'boom': _list(_point)},
    'pause': {},
    'resume': {},
    'over': {'game': _str(32), 'saver': _int(-1),   # -1: nobody may save
             # slot, colour, points, survived
             'results': _list(_row(_slot, _str(16), _int(), _num(0)),
                              limit=100)},
    'lb': {'entries': _list(_dict, limit=100)},
    'save': {'game': _str(32), 'name': _str(NICK_LIMIT)},
    'saved': {'game': _str(32), 'by': _str()},
    'bye': {'reason': ('menu', 'host-ended')},
}


def check(message):
    """The message as the game uses it (tuples for devices and slots), or
    ProtocolError."""
    kind = message.get('t') if isinstance(message, dict) else None
    schema = SCHEMAS.get(kind) if isinstance(kind, str) else None
    if schema is None:
        _fail('unknown message type')
    checked = {'t': kind}
    for field, test in schema.items():
        if field not in message:
            _fail('missing ' + field)
        checked[field] = _valid(test, message[field])
    return checked


def encode(message):
    """One message as bytes on the wire (tuples become lists)."""
    data = json.dumps(message, separators=(',', ':'),
                      allow_nan=False).encode('utf-8') + b'\n'
    if len(data) > MAX_LINE:
        raise ProtocolError('message too long')
    return data


class Decoder:
    """Splits the incoming byte stream into checked messages."""

    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer += data
        messages = []
        while True:
            end = self.buffer.find(b'\n')
            if end < 0 and len(self.buffer) <= MAX_LINE:
                return messages
            if end < 0 or end >= MAX_LINE:
                raise ProtocolError('line too long')
            line = bytes(self.buffer[:end])
            del self.buffer[:end + 1]
            try:
                message = json.loads(line.decode('utf-8'))
            except (UnicodeDecodeError, ValueError):
                raise ProtocolError('not JSON')
            messages.append(check(message))


# ---- connections -------------------------------------------------------------

class Connection:
    """One TCP connection: reads checked messages, queues reliable messages,
    and keeps only the newest snapshot (`snapshot`, set by the host) for a
    reader that falls behind."""

    def __init__(self, sock):
        self.sock = sock
        sock.setblocking(False)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self.decoder = Decoder()
        self.outbox = bytearray()
        self.snapshot = None     # newest snapshot not yet started
        self.closing = False     # close once the outbox is sent
        self.closed = False
        self.eof = False         # the peer closed its side
        self.peer = None         # host side: the client's id after hello

    def send(self, message):
        if self.closed:
            return
        data = encode(message)
        if len(self.outbox) + len(data) > MAX_OUTBOX:
            self.close()          # a peer that stopped reading long ago
            return
        self.outbox += data

    def read(self):
        """Messages that arrived. Sets `eof` when the peer closed after
        them; ProtocolError or OSError when the peer broke the protocol or
        the connection."""
        messages = []
        while not self.eof:
            try:
                data = self.sock.recv(65536)
            except (BlockingIOError, InterruptedError):
                break
            if not data:
                self.eof = True
                break
            messages += self.decoder.feed(data)
        return messages

    def flush(self):
        """Send what the socket takes now. OSError if the connection broke."""
        while not self.closed:
            if not self.outbox and self.snapshot is not None:
                self.outbox, self.snapshot = bytearray(self.snapshot), None
            if not self.outbox:
                if self.closing:
                    self.close()
                return
            try:
                sent = self.sock.send(self.outbox)
            except (BlockingIOError, InterruptedError):
                return
            del self.outbox[:sent]

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.sock.close()
            except OSError:
                pass


class HostSession:
    """The listening side. `poll()` returns events:
    ('connect', peer, name), ('message', peer, msg), ('close', peer).
    With at most MAX_CLIENTS + a few sockets, `poll()` simply tries each."""

    def __init__(self, name, port=GAME_PORT, tries=PORT_TRIES, address=''):
        self.name = name
        self.phase = 'lobby'    # sent in `welcome`; set by the game
        self.listener = None
        for candidate in range(port, port + max(tries, 1)):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((address, candidate))
                sock.listen(MAX_CLIENTS + 2)
            except OSError:
                sock.close()
                if candidate == 0:
                    raise
                continue
            self.listener = sock
            break
        if self.listener is None:
            raise OSError('no free port from {}'.format(port))
        self.listener.setblocking(False)
        self.port = self.listener.getsockname()[1]
        self.pending = []       # connections that have not said hello
        self.clients = {}       # peer -> Connection
        self._next_peer = 1     # 0 is the host itself

    def _hello(self, conn, message, events):
        if message['t'] != 'hello':
            raise ProtocolError('hello expected')
        # a refused connection stays pending until the refusal is sent
        if message['proto'] != NET_PROTOCOL:
            conn.send({'t': 'refuse', 'reason': 'version'})
            conn.closing = True
            return
        if len(self.clients) >= MAX_CLIENTS:
            conn.send({'t': 'refuse', 'reason': 'full'})
            conn.closing = True
            return
        self.pending.remove(conn)
        peer = conn.peer = self._next_peer
        self._next_peer += 1
        self.clients[peer] = conn
        conn.send({'t': 'welcome', 'peer': peer, 'phase': self.phase,
                   'name': self.name})
        events.append(('connect', peer, message['name']))

    def _drop(self, conn, events):
        conn.close()
        if conn in self.pending:
            self.pending.remove(conn)
        if conn.peer is not None and self.clients.get(conn.peer) is conn:
            del self.clients[conn.peer]
            events.append(('close', conn.peer))

    def poll(self):
        events = []
        if self.listener is None:
            return events
        while True:
            try:
                sock, _ = self.listener.accept()
            except OSError:      # BlockingIOError: nobody is waiting
                break
            self.pending.append(Connection(sock))
        for conn in self.pending + list(self.clients.values()):
            try:
                for message in conn.read():
                    if conn.closing:
                        break
                    if conn.peer is None:
                        self._hello(conn, message, events)
                    else:
                        events.append(('message', conn.peer, message))
                if not conn.eof:
                    conn.flush()
            except (ProtocolError, OSError):
                conn.close()
            if conn.eof or conn.closed:
                self._drop(conn, events)
        return events

    def send(self, peer, message):
        conn = self.clients.get(peer)
        if conn is not None:
            conn.send(message)

    def broadcast(self, message):
        for conn in self.clients.values():
            conn.send(message)

    def snapshot(self, message):
        data = None
        for conn in self.clients.values():
            if not conn.closed:
                data = data or encode(message)
                conn.snapshot = data

    def disconnect(self, peer):
        """Close one client's connection (no 'close' event)."""
        conn = self.clients.pop(peer, None)
        if conn is not None:
            conn.close()

    def close(self, reason='host-ended'):
        """Say goodbye to every client and stop listening."""
        for conn in list(self.clients.values()):
            conn.send({'t': 'bye', 'reason': reason})
            try:
                conn.flush()
            except OSError:
                pass
            conn.close()
        for conn in self.pending:
            conn.close()
        self.clients, self.pending = {}, []
        if self.listener is not None:
            self.listener.close()
            self.listener = None


# connect_ex results of a connection still being set up
_CONNECTING = {0, errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK,
               10035}   # WSAEWOULDBLOCK


class ClientSession:
    """The connecting side. `poll()` returns events: ('welcome', msg),
    ('fail', reason) with reason 'unreachable', 'version' or 'full',
    ('message', msg) and ('close',)."""

    def __init__(self, address, port, name, clock=time.monotonic):
        self.clock = clock
        self.name = name
        self.state = 'connecting'   # 'hello', 'ready', 'closed'
        self.peer = None
        self.conn = None
        self._started = clock()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setblocking(False)
        self._failed = None
        try:
            target = socket.getaddrinfo(address, port, socket.AF_INET,
                                        socket.SOCK_STREAM)[0][4]
            error = self._sock.connect_ex(target)
        except OSError:
            error = -1
        if error not in _CONNECTING:
            self._failed = 'unreachable'     # refused, no route, bad name

    def _fail(self, reason):
        self.state = 'closed'
        if self.conn is not None:
            self.conn.close()
        else:
            self._sock.close()
        return [('fail', reason)]

    def poll(self):
        if self.state == 'closed':
            return []
        if self._failed:
            return self._fail(self._failed)
        if self.state == 'connecting':
            error = self._sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error:
                return self._fail('unreachable')
            try:
                self._sock.getpeername()
            except OSError:
                if self.clock() - self._started > CONNECT_TIMEOUT:
                    return self._fail('unreachable')
                return []
            self.conn = Connection(self._sock)
            self.conn.send({'t': 'hello', 'proto': NET_PROTOCOL,
                            'name': self.name[:NAME_LIMIT]})
            self.state = 'hello'
        events = []
        try:
            for message in self.conn.read():
                if self.state == 'hello':
                    if message['t'] == 'refuse':
                        return self._fail(message['reason'])
                    if message['t'] != 'welcome':
                        raise ProtocolError('welcome expected')
                    self.peer = message['peer']
                    self.state = 'ready'
                    events.append(('welcome', message))
                else:
                    events.append(('message', message))
            if self.conn.eof:
                raise ConnectionResetError('closed by the host')
            self.conn.flush()
        except (ProtocolError, OSError):
            if self.state == 'hello':
                return events + self._fail('unreachable')
            self.state = 'closed'
            self.conn.close()
            events.append(('close',))
            return events
        if self.state == 'hello' and self.clock() - self._started > \
                CONNECT_TIMEOUT:
            return self._fail('unreachable')
        return events

    def send(self, message):
        if self.state in ('hello', 'ready'):
            self.conn.send(message)

    def close(self, reason='menu'):
        """Say goodbye and close."""
        if self.state == 'ready':
            self.conn.send({'t': 'bye', 'reason': reason})
            try:
                self.conn.flush()
            except OSError:
                pass
        if self.conn is not None:
            self.conn.close()
        else:
            self._sock.close()
        self.state = 'closed'


# ---- discovery ---------------------------------------------------------------

class Announcer:
    """The host's broadcast, about once a second: who hosts, on which port,
    with how many players."""

    def __init__(self, name, port, target=('255.255.255.255', DISCOVERY_PORT),
                 clock=time.monotonic):
        self.name, self.port, self.target, self.clock = name, port, target, clock
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(False)
        self._last = None

    def payload(self, players, playing):
        return json.dumps({
            'game': GAME_MAGIC, 'proto': NET_PROTOCOL, 'name': self.name,
            'port': self.port, 'players': players, 'playing': playing,
        }).encode('utf-8')

    def tick(self, players, playing):
        now = self.clock()
        if self._last is not None and now - self._last < ANNOUNCE_INTERVAL:
            return False
        self._last = now
        try:
            self.sock.sendto(self.payload(players, playing), self.target)
        except OSError:
            pass     # no network right now: try again next time
        return True

    def close(self):
        self.sock.close()


class FoundGame:
    """A host seen on the network."""

    def __init__(self, address, port, name, players, playing, proto, seen):
        self.address, self.port, self.name = address, port, name
        self.players, self.playing, self.proto = players, playing, proto
        self.seen = seen

    @property
    def compatible(self):
        return self.proto == NET_PROTOCOL

    @property
    def key(self):
        return (self.address, self.port)


class Browser:
    """Listens for announcements and keeps the list of hosts heard in the
    last HOST_EXPIRY seconds."""

    def __init__(self, port=DISCOVERY_PORT, clock=time.monotonic):
        self.clock = clock
        self.found = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        self.sock.setblocking(False)
        self.error = None
        try:
            self.sock.bind(('', port))
            self.port = self.sock.getsockname()[1]
        except OSError as e:
            self.error = e
            self.port = None

    @staticmethod
    def parse(data, address, seen):
        """A FoundGame for an announcement, None for anything else."""
        try:
            info = json.loads(data.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            return None
        if not isinstance(info, dict) or info.get('game') != GAME_MAGIC:
            return None
        try:
            return FoundGame(
                address, _int(1, 65535)(info.get('port')),
                _str()(info.get('name')).strip() or address,
                _int(0, SLOTS)(info.get('players')),
                bool(info.get('playing')), _int()(info.get('proto')), seen)
        except ProtocolError:
            return None

    def poll(self):
        """The hosts heard lately, sorted by name. Reads what arrived."""
        now = self.clock()
        if self.error is None:
            while True:
                try:
                    data, (address, _) = self.sock.recvfrom(4096)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    break
                game = self.parse(data, address, now)
                if game is not None:
                    self.found[game.key] = game
        for key, game in list(self.found.items()):
            if now - game.seen > HOST_EXPIRY:
                del self.found[key]
        return sorted(self.found.values(), key=lambda g: (g.name, g.key))

    def close(self):
        self.sock.close()


# ---- addresses ---------------------------------------------------------------

def local_address():
    """This device's address on the local network, as others reach it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('10.254.254.254', 1))   # sends nothing
        address = sock.getsockname()[0]
    except OSError:
        address = None
    finally:
        sock.close()
    if not address or address.startswith('0.'):
        try:
            address = socket.gethostbyname(socket.gethostname())
        except OSError:
            address = '127.0.0.1'
    return address


_HOSTNAME = re.compile(r'[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?'
                       r'(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*')


def parse_address(text, default_port=GAME_PORT):
    """(host, port) from 'a.b.c.d', 'a.b.c.d:port' or a host name, or
    ValueError."""
    text = str(text).strip()
    host, port = text, default_port
    if text.count(':') == 1:
        host, port_text = text.split(':')
        if not port_text.isdigit():
            raise ValueError('bad port')
        port = int(port_text)
    if not 0 < port < 65536:
        raise ValueError('bad port')
    if not host or len(host) > 253 or not _HOSTNAME.fullmatch(host):
        raise ValueError('bad host')
    parts = host.split('.')
    if all(p.isdigit() for p in parts):
        if len(parts) != 4 or any(int(p) > 255 for p in parts):
            raise ValueError('bad IP address')
    return host, port
