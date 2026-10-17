import os
import struct
import sys
import zlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'tools'))
import play_listing as pl  # noqa: E402


def stub_png(path, width, height, depth=8, color=2):
    """A PNG with only the header: all the validator reads."""
    header = struct.pack('>IIBBBBB', width, height, depth, color, 0, 0, 0)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(pl.PNG_SIGNATURE + pl._chunk(b'IHDR', header))


def decode_rgb(path):
    """Pixel rows of a PNG written by write_png (filter 0, one IDAT)."""
    data = open(path, 'rb').read()
    width, height, depth, color = pl.png_header(path)
    idat = data.index(b'IDAT')
    length = struct.unpack('>I', data[idat - 4:idat])[0]
    raw = zlib.decompress(data[idat + 4:idat + 4 + length])
    stride = width * 3 + 1
    return [raw[y * stride + 1:(y + 1) * stride] for y in range(height)]


def test_write_png_drops_alpha_and_flips_rows(tmp_path):
    path = str(tmp_path / 'a.png')
    # 2x2, bottom row first as OpenGL reads it: red, green / blue, white
    rgba = bytes([255, 0, 0, 10, 0, 255, 0, 20,
                  0, 0, 255, 30, 255, 255, 255, 40])
    pl.write_png(path, 2, 2, rgba)
    assert pl.png_header(path) == (2, 2, 8, pl.COLOR_RGB)
    top, bottom = decode_rgb(path)
    assert top == bytes([0, 0, 255, 255, 255, 255])
    assert bottom == bytes([255, 0, 0, 0, 255, 0])
    assert pl.image_problems(path)               # 2x2 is too small, but...
    assert not [p for p in pl.image_problems(path) if 'colour type' in p]


def test_write_png_rejects_wrong_buffer(tmp_path):
    with pytest.raises(ValueError):
        pl.write_png(str(tmp_path / 'a.png'), 2, 2, b'\x00' * 12)


@pytest.mark.parametrize('size', [(1920, 1080), (2560, 1440), (3840, 2160)])
def test_valid_screenshot_sizes(tmp_path, size):
    path = str(tmp_path / 'ok.png')
    stub_png(path, *size)
    assert pl.image_problems(path) == []


@pytest.mark.parametrize('size, color, depth, words', [
    ((1920, 1080), 6, 8, 'alpha'),          # RGBA
    ((1920, 1080), 2, 16, 'alpha'),         # 48-bit
    ((1920, 1200), 2, 8, '16:9'),
    ((1080, 1920), 2, 8, '16:9'),           # portrait
    ((1600, 900), 2, 8, 'at least'),
    ((7680, 4320), 2, 8, 'at most'),
])
def test_screenshot_rule_violations(tmp_path, size, color, depth, words):
    path = str(tmp_path / 'bad.png')
    stub_png(path, *size, depth=depth, color=color)
    problems = pl.image_problems(path)
    assert any(words in p and 'bad.png' in p for p in problems), problems


def test_not_a_png(tmp_path):
    path = tmp_path / 'x.png'
    path.write_bytes(b'GIF89a......................')
    assert 'not a PNG' in pl.image_problems(str(path))[0]


def test_banner_rules(tmp_path):
    path = str(tmp_path / 'tv-banner.png')
    stub_png(path, 1280, 720)
    assert pl.image_problems(path, banner=True) == []
    stub_png(path, 1920, 1080)
    assert '1280x720' in pl.image_problems(path, banner=True)[0]
    stub_png(path, 1280, 720, color=6)
    assert 'alpha' in pl.image_problems(path, banner=True)[0]


def test_check_listing_counts_and_banner(tmp_path):
    out = str(tmp_path)
    for name, n in (('phone', 5), ('tablet-7', 4), ('tablet-10', 8),
                    ('tv', 3)):
        for i in range(n):
            stub_png(os.path.join(out, name, '{:02}-x.png'.format(i)),
                     1920, 1080)
    problems, counts = pl.check_listing(out)
    assert counts == {'phone': 5, 'tablet-7': 4, 'tablet-10': 8, 'tv': 3}
    assert len(problems) == 2
    assert any('tv' in p and 'has 3' in p for p in problems)
    assert any('tv-banner.png: missing' in p for p in problems)
    stub_png(os.path.join(out, 'tv', '03-x.png'), 1920, 1080)
    stub_png(os.path.join(out, 'tv-banner.png'), 1280, 720)
    problems, counts = pl.check_listing(out)
    assert problems == [] and counts['tv'] == 4 and counts['tv-banner'] == 1
    problems, counts = pl.check_listing(out, names=('tv',))
    assert counts == {'tv': 4}


def test_profiles_meet_the_rules():
    for name in pl.FORM_FACTORS:
        w, h = pl.PROFILES[name]['size']
        assert w * 9 == h * 16 and w >= 1920 and max(w, h) <= pl.MAX_SIDE
    assert pl.PROFILES[pl.BANNER]['size'] == pl.BANNER_SIZE
    assert [n for n in pl.FORM_FACTORS if pl.PROFILES[n]['touch']] == [
        'phone', 'tablet-7', 'tablet-10']


# ---- scenes (headless game, mock GL) ---------------------------------------

@pytest.fixture
def scene_game():
    from kivy.lang import Builder
    from main import SpacePilgrimGame
    import listing_scenes
    Builder.load_file('spacepilgrim.kv')
    game = SpacePilgrimGame()
    game.game_stop()
    listing_scenes.prepare(game)
    yield game
    game.frame_schedule.cancel()
    game.asteroid_schedule.cancel()
    Builder.unload_file('spacepilgrim.kv')


def test_prepare_ignores_saved_settings(scene_game):
    assert scene_game.ship_colors.path is None
    assert scene_game.touch_settings.path is None
    assert scene_game.touch_settings.mode == 'auto'
    assert scene_game.bindings.path is None


def test_frozen_scene_does_not_move(scene_game):
    from kivy.clock import Clock
    import listing_scenes as ls
    ls.gameplay(scene_game, True)
    things = scene_game.spaceships + scene_game.asteroids + scene_game.shots
    before = [tuple(w.pos) for w in things]
    background = [c for c in scene_game.children
                  if isinstance(c, __import__('main').AnimatedBackground)][0]
    uv = background.uv_pos_x_px
    frame = scene_game.explosions[0].frame
    for _ in range(5):
        Clock.tick()
    assert [tuple(w.pos) for w in things] == before
    assert len(scene_game.asteroids) == 3
    assert background.uv_pos_x_px == uv
    assert scene_game.explosions[0].frame == frame == ls.EXPLOSION_FRAME


@pytest.mark.parametrize('touch', [True, False])
def test_scene_builders(scene_game, touch):
    import listing_scenes as ls
    import main
    game = scene_game
    assert [name for name, _ in ls.SCENES] == [
        'gameplay', 'multiplayer', 'join', 'ship-select', 'menu']

    ls.gameplay(game, touch)
    assert len(game.spaceships) == 1 and len(game.shots) == 3
    assert game.spaceship_controls.touch_buttons.active == touch

    ls.multiplayer(game, touch)
    ships = game.spaceships
    assert len(ships) == 3 and len({s.cabin for s in ships}) == 3
    shown = [c.touch_buttons.side for c in game.controls
             if c is not None and c.touch_buttons.active]
    assert shown == (['left', 'right'] if touch else [])

    ls.join(game, touch)
    assert isinstance(game.select, main.JoinScreen)
    kinds = [d[0] for d in game.select.slots if d]
    assert len(kinds) == 3 and ('touch' in kinds) == touch
    assert game.select.ready[0]
    strips = game.select.side_buttons.values()
    assert all(s.opacity == (1 if touch else 0) for s in strips)

    ls.ship_select(game, touch)
    assert isinstance(game.select, main.ShipSelectScreen)
    assert game.ship_colors.colors[0] != 'blue'

    ls.menu(game, touch)
    assert game.menu_active and not game.select_active
    assert game.spaceships == [] and game.asteroids == []


def test_banner_scene(scene_game):
    import listing_scenes as ls
    ls.banner(scene_game)
    assert not scene_game.menu_active
    texts = [w.text for w in scene_game.children if hasattr(w, 'text')]
    assert 'Space\nPilgrim' in texts
    assert len(scene_game.asteroids) == 2
