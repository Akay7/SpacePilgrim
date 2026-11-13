"""The game on any window shape: touch seats at the short edges, screens
that fit and follow the window, the Pause button with the controls and
text boxes above the on-screen keyboard (change large-screen-support).

The test window has density 1, so dp are pixels."""

from contextlib import contextmanager

import pytest
from kivy.core.window import Window
from kivy.lang import Builder

import main
from main import SpacePilgrimGame

KEY_SPACE = 32


@contextmanager
def window(width, height):
    old = Window.size
    Window.size = (width, height)
    try:
        yield
    finally:
        Window.size = old


def turn(width, height):
    Window.size = (width, height)


@pytest.fixture
def game():
    Builder.load_file('spacepilgrim.kv')
    g = SpacePilgrimGame()
    g.game_stop()
    g.ship_colors.path = None
    yield g
    g.frame_schedule.cancel()
    g.asteroid_schedule.cancel()
    if hasattr(g, 'select'):
        g.remove_widget(g.select)     # stops following the window
    Builder.unload_file('spacepilgrim.kv')


def lay_out(widget):
    """Lay out a widget tree now instead of on the next frames."""
    for _ in range(3):
        stack = [widget]
        while stack:
            w = stack.pop()
            if hasattr(w, 'do_layout'):
                w.do_layout()
            stack.extend(w.children)


def box(w):
    x, y = w.to_window(*w.pos)
    return x, y, x + w.width, y + w.height


def inside(w, slack=0.5):
    x0, y0, x1, y1 = box(w)
    return (x0 >= -slack and y0 >= -slack and x1 <= Window.width + slack
            and y1 <= Window.height + slack)


def pad_down(game, stick=0):
    game._on_joy_hat(None, stick, 0, (0, -1))
    game._on_joy_hat(None, stick, 0, (0, 0))


# ---- touch seats at the short edges ---------------------------------------------

def test_phone_seats_upright_are_top_and_bottom(game):
    with window(360, 800):
        game.show_ship_select(2)
        select = game.select
        assert select.seats == ('top', 'bottom')
        assert set(select.side_buttons) == {'top', 'bottom'}
        select.side_buttons['top'].dispatch('on_press')
        assert select.slots[0] == ('touch', 'top')
        assert select.panels[0]['device'].text == 'Touch · top side'


def test_empty_seats_follow_a_turn(game):
    with window(800, 360):
        game.show_ship_select(2)
        select = game.select
        assert select.seats == ('left', 'right')
        turn(360, 800)
        assert select.seats == ('top', 'bottom')
        lay_out(select)
        top, bottom = select.side_buttons['top'], select.side_buttons['bottom']
        assert box(top)[3] > Window.height - 10 and box(bottom)[1] < 10
        assert top.width > top.height
        turn(800, 360)
        assert select.seats == ('left', 'right')


def test_seated_player_keeps_the_edge_on_a_turn(game):
    with window(800, 360):
        game.show_ship_select(2)
        select = game.select
        select.join_touch('left')
        turn(360, 800)
        assert select.seats == ('left', 'right')
        assert select.slots[0] == ('touch', 'left')
        lay_out(select)
        assert box(select.side_buttons['left'])[0] < 10
        assert inside(select)


# ---- the join screen follows the window -------------------------------------------

def _set_up_join(game):
    """Keyboard set 1 joined, a touch player seated, a pad on the bottom
    row (on the device-name box) and that box focused."""
    game.show_ship_select(2)
    select = game.select
    game._on_key_down(None, KEY_SPACE)
    game._on_key_up(None, KEY_SPACE)
    select.join_touch(select.seats[0])
    pad_down(game)                        # the bottom row, on Back
    game._on_joy_hat(None, 0, 0, (1, 0))  # right: the device-name box
    game._on_joy_hat(None, 0, 0, (0, 0))
    select.name_field.focus = True
    return select


def _check_join_fits(select, seat):
    lay_out(select)
    assert inside(select)
    rows = MAX_ROWS[select.grid.cols]
    for w in select.panels:
        assert inside(w['panel']), box(w['panel'])
        # the panels share the height left by the rows above and below
        assert w['panel'].height >= (select.middle.height - 200) / rows
    for widget in (select.back_button, select.network_button,
                   select.join_network_button, select.name_field):
        assert inside(widget), box(widget)
    # kept: slots, seat, focus and the bottom-row highlight
    assert select.slots[0] == ('keys', 0)
    assert select.slots[1] == ('touch', seat)
    assert select.name_field.focus
    assert select.bar[select.bar_index] is select.name_field
    assert select.bar_device == ('pad', 0)


MAX_ROWS = {4: 1, 2: 2}


@pytest.mark.parametrize('size, cols, bar_cols', [
    ((360, 800), 2, 2),
    ((360, 640), 2, 2),
    ((800, 360), 4, 4),
])
def test_join_screen_follows_the_window(game, size, cols, bar_cols):
    with window(1280, 800):
        select = _set_up_join(game)
        seat = select.seats[0]
        turn(*size)
        assert select.grid.cols == cols
        assert select.bottom.cols == bar_cols
        _check_join_fits(select, seat)


def test_join_screen_follows_a_turned_tablet(game, monkeypatch):
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(1280, 800):
        select = _set_up_join(game)
        assert select.seats == main.FOUR_SEATS
        turn(800, 1280)
        _check_join_fits(select, 'left')
        strips = select.side_buttons
        assert box(strips['left'])[0] < 10
        assert box(strips['right'])[2] > Window.width - 10
        assert box(strips['top'])[3] > Window.height - 10
        assert box(strips['bottom'])[1] < 10


@pytest.mark.parametrize('size', [(800, 360), (1280, 800)])
def test_join_screen_opened_in_landscape_fills_its_height(game, size):
    with window(*size):
        game.show_ship_select(2)
        select = game.select
        lay_out(select)
        assert select.middle.height == pytest.approx(select.height)
        for w in select.panels:
            assert w['panel'].height > select.height - 100 - 48


def test_join_screen_on_an_upright_phone_is_readable(game):
    with window(360, 800):
        game.show_ship_select(2)
        select = game.select
        lay_out(select)
        assert select.grid.cols == 2 and select.bottom.cols == 2
        for w in select.panels:
            assert w['panel'].width >= 150 and inside(w['panel'])


def test_join_screen_stops_following_once_closed(game):
    with window(800, 360):
        game.show_ship_select(2)
        select = game.select
        game.close_ship_select()
        turn(360, 800)
        assert select.seats == ('left', 'right')


# ---- a touch game on a phone held upright ------------------------------------------

def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _status_boxes(status):
    """Screen boxes of the turned lives and points and of the Pause button."""
    label = status.ids.text_label
    label.texture_update()
    tw, th = label.texture_size
    if status.side in ('left', 'right'):
        tw, th = th, tw
    cx, cy = label.center
    pause = status.ids.pause
    return ((cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2),
            box(pause))


def _pads(game):
    """Boxes of the touch controls on screen (hidden ones do not count)."""
    return [box(pad) for c in game.controls
            if c and c.touch_buttons.active and c.touch_buttons.opacity
            for pad in (c.touch_buttons.stick, c.touch_buttons.fire)]


def test_tall_phone_game_top_and_bottom_players(game):
    with window(360, 800):
        game.game_start(slots=[('touch', 'top'), ('touch', 'bottom')])
        w, h = Window.size
        top, bottom = (c.touch_buttons for c in game.controls)
        margin = main.dp(main.MARGIN_DP)
        # the short edges' controls reach the corners, under each player's
        # left hand the joystick: bottom left / right, top right / left
        assert bottom.stick.x == pytest.approx(margin)
        assert bottom.fire.right == pytest.approx(w - margin)
        assert top.stick.right == pytest.approx(w - margin)
        assert top.fire.x == pytest.approx(margin)
        assert bottom.stick.angle == 0 and top.stick.angle == 180
        assert top.fire.text_angle == 180
        pads = _pads(game)
        for i, a in enumerate(pads):
            assert 0 < a[0] and a[2] < w and 0 < a[1] and a[3] < h
            for b in pads[i + 1:]:
                assert not _overlap(a, b)
        for status in game.statuses:
            assert status.angle_of(status.side) == main.SEAT_ANGLES[status.side]
            for b in _status_boxes(status):
                assert 0 <= b[0] and b[2] <= w and 0 <= b[1] and b[3] <= h
                for pad in pads:
                    assert not _overlap(b, pad), status.side


# ---- every other screen follows the window -------------------------------------

class FakeBrowser:
    def poll(self):
        return []

    def close(self):
        pass


def _open(game, name, monkeypatch):
    """Open the screen `name`; returns the screen widget."""
    monkeypatch.setattr(main, 'make_browser', FakeBrowser)
    if name == 'ship selection':
        game.show_ship_select(1)
        return game.select
    if name == 'menu':
        return game.menu
    if name in ('settings', 'keyboard', 'gamepad', 'touch'):
        {'settings': game.show_settings,
         'keyboard': game.show_keyboard_settings,
         'gamepad': game.show_gamepad_settings,
         'touch': game.show_touch_settings}[name]()
        return game.settings
    if name == 'leaderboard':
        game.show_leaderboard()
        return game.leaderboard_screen
    game.remove_widget(game.menu)
    if name in ('pause', 'results', 'nickname'):
        game.game_start()
        if name == 'pause':
            game.pause()
            return game.pause_screen
        for ship in list(game.spaceships):    # the last ship is lost
            ship.lives = 0
            game.lose_spaceship(ship)
        if name == 'results':
            return game.results_screen
        game.show_name_entry()
        return game.name_screen
    game.show_network()
    if name == 'network list':
        return game.network_screen
    game.show_address()
    return game.address_screen


SCREENS = ['ship selection', 'menu', 'settings', 'keyboard', 'gamepad',
           'touch', 'leaderboard', 'pause', 'results', 'nickname',
           'network list', 'address']


def _centred(screen):
    x0, y0, x1, y1 = box(screen)
    return ((x0 + x1) / 2 == pytest.approx(Window.width / 2, abs=1)
            and (y0 + y1) / 2 == pytest.approx(Window.height / 2, abs=1))


@pytest.mark.parametrize('name', SCREENS)
def test_screens_follow_the_window(game, monkeypatch, name):
    with window(1280, 800):
        screen = _open(game, name, monkeypatch)
        choice = getattr(screen, 'selected', None)
        colour = (game.ship_colors.colors[0] if name == 'ship selection'
                  else None)
        for size in ((800, 1280), (360, 800), (800, 360)):
            turn(*size)
            lay_out(screen)
            assert inside(screen), (size, box(screen))
            assert _centred(screen), (size, box(screen))
        assert getattr(screen, 'selected', None) == choice
        if colour is not None:
            assert game.ship_colors.colors[0] == colour
    if name == 'network list':
        game._drop_network_screen()


@pytest.mark.parametrize('name', SCREENS)
def test_screens_follow_on_an_upright_phone(game, monkeypatch, name):
    with window(360, 800):
        screen = _open(game, name, monkeypatch)
        lay_out(screen)
        assert inside(screen), box(screen)
    if name in ('network list', 'address'):
        game._drop_network_screen()


# ---- a running game follows the window -------------------------------------------

TOUCH4 = [('touch', 'left'), ('touch', 'right'), ('touch', 'top'),
          ('touch', 'bottom')]


@pytest.mark.parametrize('start, end', [((800, 1280), (1280, 800)),
                                        ((1280, 800), (800, 1280))])
def test_game_follows_window_with_four_touch_players(game, monkeypatch,
                                                     start, end):
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(*start):
        game.game_start(slots=TOUCH4)
        turn(*end)
        game.update(1 / 60)                 # the game goes on
        assert len(game.spaceships) == 4 and not game.paused
        w, h = Window.size
        margin = main.dp(main.MARGIN_DP)
        pads = _pads(game)
        for control, status in zip(game.controls, game.statuses):
            layout = control.touch_buttons
            stick = box(layout.stick)
            outer = {'left': stick[0], 'right': w - stick[2],
                     'top': h - stick[3], 'bottom': stick[1]}[status.side]
            assert outer == pytest.approx(margin), status.side
            for b in (box(layout.stick), box(layout.fire),
                      *_status_boxes(status)):
                assert 0 <= b[0] and b[2] <= w and 0 <= b[1] and b[3] <= h
            for b in _status_boxes(status):
                for pad in pads:
                    assert not _overlap(b, pad), status.side


def test_game_follows_window_ship_outside_wraps(game):
    with window(1280, 800):
        game.game_start()
        ship = game.spaceships[0]
        ship.pos = (1200, 100)
        turn(800, 1280)
        game.update(1 / 60)
        assert 0 <= ship.x <= 800


# ---- the Pause button sits with the controls ---------------------------------------

def _pause_between(status, layout):
    """Pause midway between joystick and FIRE, its outer side on the
    joystick's outer side."""
    pause, stick, fire = status.ids.pause, layout.stick, layout.fire
    side = status.side or 'bottom'
    if side in ('left', 'right'):
        assert pause.center_y == pytest.approx(
            (stick.center_y + fire.center_y) / 2)
        low, high = sorted((stick, fire), key=lambda w: w.y)
        assert low.top < pause.y and pause.top < high.y
    else:
        assert pause.center_x == pytest.approx(
            (stick.center_x + fire.center_x) / 2)
        low, high = sorted((stick, fire), key=lambda w: w.x)
        assert low.right < pause.x and pause.right < high.x
    outer = {'left': pause.x - stick.x, 'right': stick.right - pause.right,
             'top': stick.top - pause.top, 'bottom': pause.y - stick.y}
    assert outer[side] == pytest.approx(0)


@pytest.mark.parametrize('size', [(800, 360), (360, 800)])
def test_pause_button_single_player_bottom_middle(game, size):
    with window(*size):
        game.game_start()
        game._on_window_touch(None, None)        # touch controls shown
        status = game.spaceship_status
        assert status.show_menu
        _pause_between(status, game.controls[0].touch_buttons)


@pytest.mark.parametrize('size, seats', [((800, 360), ('left', 'right')),
                                         ((360, 800), ('top', 'bottom'))])
def test_pause_button_two_touch_players(game, size, seats):
    with window(*size):
        game.game_start(slots=[('touch', s) for s in seats])
        for status, control in zip(game.statuses, game.controls):
            _pause_between(status, control.touch_buttons)


@pytest.mark.parametrize('scale', [1.0, 4.0])
def test_pause_button_four_touch_players(game, monkeypatch, scale):
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(945, 630):                       # 15 x 10 cm at 160 dpi
        game.touch_settings.scale = scale
        game.game_start(slots=TOUCH4)
        pads = _pads(game)
        fallbacks = 0
        for status, control in zip(game.statuses, game.controls):
            if status.pause_spot:
                _pause_between(status, control.touch_buttons)
            else:
                fallbacks += 1
            text, pause = _status_boxes(status)
            for pad in pads:
                assert not _overlap(pause, pad), (scale, status.side)
                assert not _overlap(text, pad), (scale, status.side)
        assert fallbacks == 0          # the edge layout leaves room


def test_pause_button_player_out_of_lives(game):
    with window(800, 360):
        game.game_start(slots=[('touch', 'left'), ('touch', 'right')])
        ship = game.spaceships[0]
        ship.lives = 0
        game.lose_spaceship(ship)
        left, right = game.statuses
        assert not left.show_menu and left.ids.pause.opacity == 0
        assert right.show_menu


@pytest.mark.parametrize('scale', [2.0, 3.0, 4.0])
def test_pause_button_falls_back_when_controls_leave_no_room(game, scale):
    """Two touch players on a small phone with large controls: no room
    between joystick and FIRE, so Pause goes on the screen-centre side of
    the lives and points, clear of every control."""
    with window(640, 360):
        game.touch_settings.scale = scale
        game.game_start(slots=[('touch', 'left'), ('touch', 'right')])
        pads = _pads(game)
        blocks = []
        for status in game.statuses:
            assert status.pause_spot == [] and status.show_menu
            label, button = status.ids.text_label, status.ids.pause
            dx, dy = status.PAUSE_DIRECTIONS[status.side]
            assert ((button.center_x - label.center_x) * dx
                    + (button.center_y - label.center_y) * dy) < 0
            text, pause = _status_boxes(status)
            assert 0 <= pause[0] and pause[2] <= 640
            assert 0 <= pause[1] and pause[3] <= 360
            for pad in pads:
                assert not _overlap(pause, pad), (scale, status.side)
            blocks += [text, pause]
        for i, a in enumerate(blocks):
            for b in blocks[i + 1:]:
                assert not _overlap(a, b), scale


def test_pause_button_single_player_falls_back_under_the_text(game):
    with window(640, 360):
        game.touch_settings.scale = 4.0
        game.game_start()
        game._on_window_touch(None, None)
        status = game.spaceship_status
        assert status.pause_spot == []
        label, button = status.ids.text_label, status.ids.pause
        assert button.center_x == pytest.approx(label.center_x)
        assert button.center_y < label.center_y


# ---- text boxes above the on-screen keyboard ------------------------------------------

def test_softinput_pans_to_the_text_box(game, monkeypatch):
    assert Window.softinput_mode == 'below_target'
    # the three boxes are plain focusable TextInputs, so Kivy hands each
    # one's rectangle to SDL when the keyboard opens
    boxes = [_open(game, 'nickname', monkeypatch).ids.field]
    game.show_ship_select(2)
    boxes.append(game.select.name_field)
    boxes.append(_open(game, 'address', monkeypatch).ids.field)
    game._drop_network_screen()
    for field in boxes:
        assert isinstance(field, main.TextInput)
        assert field.is_focusable and not field.multiline


# ---- keyboard and gamepad players' lives and points on any window -------------------

def _text_boxes(game):
    boxes = []
    for status in game.statuses:
        status.spaceship.points = 12345        # the longest text in practice
    for status in game.statuses:
        boxes.append(_status_boxes(status)[0])
    return boxes


def _no_overlaps(boxes, w, h):
    for i, a in enumerate(boxes):
        assert 0 <= a[0] and a[2] <= w and 0 <= a[1] and a[3] <= h, a
        for b in boxes[i + 1:]:
            assert not _overlap(a, b), (a, b)


@pytest.mark.parametrize('slots', [
    [('pad', 0), ('pad', 1)],
    [('pad', 0), ('pad', 1), ('keys', 0), ('keys', 1)],
    [None, ('pad', 0), None, ('keys', 1)],
])
def test_status_two_per_row_on_a_narrow_window(game, slots):
    with window(360, 800):
        game.game_start(slots=slots)
        for status in game.statuses:
            assert status.side == 'row'
            assert status.ids.text_label.text.count('\n') == 1
            assert status.ids.text_label.center_y > Window.height - 140
        _no_overlaps(_text_boxes(game), *Window.size)


def test_status_one_line_quarters_on_a_wide_window(game):
    with window(800, 360):
        game.game_start(slots=[('pad', 0), ('pad', 1), ('keys', 0),
                               ('keys', 1)])
        for slot, status in enumerate(game.statuses):
            label = status.ids.text_label
            assert '\n' not in label.text
            assert label.center_x == pytest.approx(800 * (slot + 0.5) / 4)


def test_status_follows_a_turn_to_a_narrow_window(game):
    with window(800, 360):
        game.game_start(slots=[('pad', 0), ('pad', 1), ('keys', 0)])
        turn(360, 800)
        for status in game.statuses:
            assert '\n' in status.ids.text_label.text
        _no_overlaps(_text_boxes(game), *Window.size)


@pytest.mark.parametrize('slots', [
    [('touch', 'top'), ('pad', 0)],
    [('pad', 0), ('touch', 'bottom'), ('keys', 0)],
    [('touch', 'top'), ('touch', 'bottom'), ('pad', 0), ('keys', 1)],
    [('pad', 0), ('touch', 'top'), ('keys', 0), ('keys', 1)],
])
@pytest.mark.parametrize('size', [(360, 800), (800, 360)])
def test_status_beside_the_sides_on_a_phone(game, slots, size):
    """Touch players at the top or bottom of a phone (seated while it was
    held upright, then maybe turned) keep their whole edge; the others'
    lives and points sit beside the middle of the left and right edges,
    and nothing overlaps."""
    with window(*size):
        game.game_start(slots=slots)
        w, h = Window.size
        margin = main.dp(main.MARGIN_DP)
        for status, control in zip(game.statuses, game.controls):
            if status.side in ('top', 'bottom'):
                layout = control.touch_buttons
                assert not layout.corners
                assert not _overlap(box(layout.stick), box(layout.fire))
                if w < h:          # upright: the controls reach the corners
                    low, high = sorted((layout.stick, layout.fire),
                                       key=lambda b: b.x)
                    assert low.x == pytest.approx(margin)
                    assert high.right == pytest.approx(w - margin)
            else:
                assert status.side == 'flank'
                assert '\n' in status.ids.text_label.text
        texts = _text_boxes(game)
        pauses = [_status_boxes(s)[1] for s in game.statuses if s.show_menu]
        _no_overlaps(texts + pauses + _pads(game), w, h)


def test_status_corners_stay_on_a_four_seat_tablet(game, monkeypatch):
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(800, 1280):
        game.game_start(slots=[('touch', 'top'), ('pad', 0)])
        assert game.statuses[1].side == 'corner'


# ---- touch controls in the free corners ------------------------------------------

def _ends(layout):
    """The control nearer the start and the one nearer the end of the
    layout's edge."""
    across = layout.side in ('top', 'bottom')
    return sorted((layout.stick, layout.fire),
                  key=lambda b: b.x if across else b.y)


def _in_corners(layout, w, h):
    margin = main.dp(main.MARGIN_DP)
    low, high = _ends(layout)
    if layout.side in ('top', 'bottom'):
        return (low.x == pytest.approx(margin)
                and high.right == pytest.approx(w - margin))
    return (low.y == pytest.approx(margin)
            and high.top == pytest.approx(h - margin))


def _whole_screen_clear(game, w, h):
    texts = _text_boxes(game)
    pauses = [_status_boxes(s)[1] for s in game.statuses
              if s.show_menu and s.pause_spot]
    _no_overlaps(texts + pauses + _pads(game), w, h)


@pytest.mark.parametrize('size', [(1280, 800), (800, 1280)])
@pytest.mark.parametrize('slots', [
    [('keys', 0), ('touch', 'bottom')],          # top-left corner taken
    [None, None, ('pad', 0), ('touch', 'top')],   # bottom-left corner
    [('touch', 'bottom'), ('touch', 'top')],
    [('touch', 'bottom')] + [None] * 3,
])
def test_touch_controls_reach_the_free_corners(game, monkeypatch, slots,
                                               size):
    """With nobody at the crossing edges, a touch player's joystick and FIRE
    go into the corners of their edge when no lives and points are there,
    the Pause button between them, and nothing overlaps."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(*size):
        game.game_start(slots=slots)
        w, h = Window.size
        for status in game.statuses:
            if status.side in ('top', 'bottom'):
                layout = game.controls[status.column].touch_buttons
                assert _in_corners(layout, w, h), (status.side, slots)
                assert status.pause_spot          # room between the controls
        _whole_screen_clear(game, w, h)


@pytest.mark.parametrize('slots, corner_side', [
    ([('touch', 'bottom'), ('keys', 0), ('pad', 0)], 'bottom'),   # 3: BL
    ([('pad', 0), ('pad', 1), ('keys', 0), ('touch', 'top')], 'top'),
])
def test_touch_controls_leave_corners_with_lives_and_points(
        game, monkeypatch, slots, corner_side):
    """A keyboard or gamepad player's lives and points in a corner of the
    edge keep the touch controls out of that corner."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(1280, 800):
        game.game_start(slots=slots)
        w, h = Window.size
        corner = main.dp(main.CORNER_DP)
        layout = next(c.touch_buttons for c in game.controls
                      if c is not None and c.side == corner_side)
        low, high = _ends(layout)
        assert low.x >= corner and high.right <= w - corner
        _whole_screen_clear(game, w, h)


@pytest.mark.parametrize('size', [(1280, 800), (800, 1280)])
def test_crossing_seat_takes_the_corners_of_the_short_edges(game,
                                                            monkeypatch, size):
    """A seat at a crossing edge: as before, only the short edges' controls
    reach the corners and every edge has them the same distance apart."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(*size):
        game.game_start(slots=[('touch', 'bottom'), ('touch', 'left')])
        w, h = Window.size
        bottom, left = (c.touch_buttons for c in game.controls[:2])
        short = left if w > h else bottom
        long = bottom if w > h else left
        assert _in_corners(short, w, h)
        assert not _in_corners(long, w, h)
        _whole_screen_clear(game, w, h)


def test_controls_leave_the_corners_for_a_new_seat(game, monkeypatch):
    """A touch player joining at a crossing edge during the game takes
    the corners back from the seat already there; one leaving frees them."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(1280, 800):
        game.game_start(slots=[('touch', 'bottom'), ('keys', 0)])
        bottom = game.controls[0].touch_buttons
        assert _in_corners(bottom, 1280, 800)
        game.add_player(2, ('touch', 'left'), game.ship_colors.colors[2])
        assert bottom.seats == ['bottom', 'left']
        assert not _in_corners(bottom, 1280, 800)
        _whole_screen_clear(game, 1280, 800)
        game._drop_player(2, out=False)          # left the game
        assert bottom.seats == ['bottom']
        assert _in_corners(bottom, 1280, 800)


def test_seat_stays_taken_after_the_last_life(game, monkeypatch):
    """A touch player out of lives keeps lives and points at their edge, so
    the other controls do not move into it; only Pause goes."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(1280, 800):
        game.game_start(slots=[('touch', 'bottom'), ('touch', 'left'),
                               ('keys', 0)])
        bottom = game.controls[0].touch_buttons
        before = (tuple(bottom.stick.pos), tuple(bottom.fire.pos))
        ship = game.controls[1].spaceship
        ship.lives = 0
        game.lose_spaceship(ship)
        assert game.controls[1] is None
        left = next(s for s in game.statuses if s.column == 1)
        assert not left.show_menu
        assert bottom.seats == ['bottom', 'left']
        assert (tuple(bottom.stick.pos), tuple(bottom.fire.pos)) == before


def test_corner_lives_and_points_limit_only_along_the_edge(game, monkeypatch):
    """A low, wide window: lives and points in a bottom corner keep the
    bottom controls only away from that corner, not squeezed by the
    window height."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(1280, 420):
        game.game_start(slots=[('touch', 'bottom'), ('pad', 0), ('keys', 0)])
        layout = game.controls[0].touch_buttons
        corner = main.dp(main.CORNER_DP)
        gap = main.cm(0.3)
        stick, fire = _ends(layout)
        assert stick is layout.stick
        assert stick.x == pytest.approx(corner + gap)
        assert fire.right == pytest.approx(1280 - corner - gap)
        _whole_screen_clear(game, 1280, 420)


@pytest.mark.parametrize('slots', [
    [('touch', 'bottom'), ('pad', 0), ('keys', 0)],
    [('touch', 'top'), ('pad', 0), ('keys', 0), ('keys', 1)],
])
def test_controls_keep_their_order_on_a_tiny_window(game, monkeypatch, slots):
    """No room between the corners: joystick and FIRE stay side by side in
    their order instead of swapping places."""
    monkeypatch.setattr(main, 'four_seat_screen', lambda *a: True)
    with window(400, 300):
        game.game_start(slots=slots)
        layout = game.controls[0].touch_buttons
        stick, fire = layout.stick, layout.fire
        if layout.side == 'bottom':
            assert stick.right < fire.x
        else:
            assert fire.right < stick.x
        assert not _overlap(box(stick), box(fire))
