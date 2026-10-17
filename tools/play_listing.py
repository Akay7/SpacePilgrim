"""Google Play listing images: screenshots per form factor and the Android TV
banner, rendered from the game itself.

    SDL_AUDIODRIVER=dummy .venv/bin/python tools/play_listing.py [NAME...]

NAME is one or more of phone, tablet-7, tablet-10, tv, tv-banner (default:
all). Every image is written to store/play/ and checked against the Play
Console rules; the exit status is non-zero if any image breaks a rule.

This module only uses the standard library at import time: Kivy is started
in a child process per form factor (see `render`), because window size and
screen density are fixed once Kivy has started.
"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'store', 'play')

# Play Console rules (support.google.com/googleplay/android-developer/
# answer/9866151): 24-bit PNG without alpha; for games, landscape 16:9 of at
# least 1920x1080 to qualify for recommendations; at most 3840 on the long
# side; 4 to 8 screenshots for tablets (we keep every set to that); the
# Android TV banner is 1280x720.
MIN_SIZE = (1920, 1080)
MAX_SIDE = 3840
MIN_COUNT, MAX_COUNT = 4, 8
BANNER = 'tv-banner'
BANNER_SIZE = (1280, 720)
BANNER_FILE = BANNER + '.png'

# Window size in pixels, density (dp scale), dpi (for cm) and whether the
# device is played by touch. See design.md, decision 2.
PROFILES = {
    'phone': {'size': (1920, 1080), 'density': 2.625, 'dpi': 420,
              'touch': True},
    'tablet-7': {'size': (1920, 1080), 'density': 1.8, 'dpi': 288,
                 'touch': True},
    'tablet-10': {'size': (2560, 1440), 'density': 1.8, 'dpi': 288,
                  'touch': True},
    'tv': {'size': (1920, 1080), 'density': 2.0, 'dpi': 320,
           'touch': False},
    BANNER: {'size': BANNER_SIZE, 'density': 2.0, 'dpi': 320,
             'touch': False},
}
FORM_FACTORS = ('phone', 'tablet-7', 'tablet-10', 'tv')

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
COLOR_RGB = 2


# ---- PNG ----------------------------------------------------------------

def _chunk(kind, data):
    body = kind + data
    return (struct.pack('>I', len(data)) + body
            + struct.pack('>I', zlib.crc32(body) & 0xffffffff))


def write_png(path, width, height, rgba, bottom_up=True):
    """Write RGBA pixels as a 24-bit PNG without alpha. OpenGL reads rows
    bottom to top, hence `bottom_up`."""
    if len(rgba) != width * height * 4:
        raise ValueError('expected {} bytes of RGBA, got {}'.format(
            width * height * 4, len(rgba)))
    rgb = bytearray(width * height * 3)
    for channel in range(3):
        rgb[channel::3] = rgba[channel::4]
    stride = width * 3
    rows = range(height - 1, -1, -1) if bottom_up else range(height)
    raw = b''.join(b'\x00' + bytes(rgb[y * stride:(y + 1) * stride])
                   for y in rows)
    header = struct.pack('>IIBBBBB', width, height, 8, COLOR_RGB, 0, 0, 0)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'wb') as f:
        f.write(PNG_SIGNATURE + _chunk(b'IHDR', header)
                + _chunk(b'IDAT', zlib.compress(raw, 9)) + _chunk(b'IEND', b''))


def png_header(path):
    """(width, height, bit depth, colour type) of a PNG, or None if the file
    is not a PNG."""
    with open(path, 'rb') as f:
        head = f.read(8 + 8 + 13)
    if len(head) < 29 or head[:8] != PNG_SIGNATURE or head[12:16] != b'IHDR':
        return None
    width, height, depth, color = struct.unpack('>IIBB', head[16:26])
    return width, height, depth, color


# ---- rules ----------------------------------------------------------------

def image_problems(path, banner=False):
    """Rule violations of one image, as messages naming the file."""
    name = os.path.relpath(path, ROOT)
    header = png_header(path)
    if header is None:
        return ['{}: not a PNG file'.format(name)]
    width, height, depth, color = header
    problems = []
    if color != COLOR_RGB or depth != 8:
        problems.append('{}: must be 24-bit RGB without alpha (bit depth {}, '
                        'colour type {})'.format(name, depth, color))
    if banner:
        if (width, height) != BANNER_SIZE:
            problems.append('{}: TV banner must be {}x{}, is {}x{}'.format(
                name, *BANNER_SIZE, width, height))
        return problems
    if width * 9 != height * 16:
        problems.append('{}: must be landscape 16:9, is {}x{}'.format(
            name, width, height))
    if width < MIN_SIZE[0] or height < MIN_SIZE[1]:
        problems.append('{}: must be at least {}x{}, is {}x{}'.format(
            name, *MIN_SIZE, width, height))
    if max(width, height) > MAX_SIDE:
        problems.append('{}: must be at most {} px on the long side, is '
                        '{}x{}'.format(name, MAX_SIDE, width, height))
    return problems


def screenshots(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                  if f.lower().endswith('.png'))


def check_listing(out=OUT, names=FORM_FACTORS + (BANNER,)):
    """(problems, counts) of the listing images of `names` in `out`."""
    problems, counts = [], {}
    for name in names:
        if name == BANNER:
            path = os.path.join(out, BANNER_FILE)
            if not os.path.exists(path):
                problems.append('{}: missing'.format(
                    os.path.relpath(path, ROOT)))
                continue
            problems += image_problems(path, banner=True)
            counts[name] = 1
            continue
        files = screenshots(os.path.join(out, name))
        counts[name] = len(files)
        if not MIN_COUNT <= len(files) <= MAX_COUNT:
            problems.append('{}: needs {} to {} screenshots, has {}'.format(
                os.path.relpath(os.path.join(out, name), ROOT),
                MIN_COUNT, MAX_COUNT, len(files)))
        for path in files:
            problems += image_problems(path)
    return problems, counts


# ---- rendering (child process, one per form factor) -----------------------

def _child(name):
    """Render the images of one form factor. Runs in its own process: the
    window size and density below are fixed once Kivy has started."""
    profile = PROFILES[name]
    width, height = profile['size']
    from kivy.config import Config
    Config.set('graphics', 'width', str(width))
    Config.set('graphics', 'height', str(height))
    Config.set('graphics', 'resizable', '0')
    # a hidden window keeps the requested size even on smaller screens
    Config.set('graphics', 'window_state', 'hidden')
    Config.set('kivy', 'exit_on_escape', '0')
    os.chdir(ROOT)   # the game loads its assets by relative paths
    sys.path[:0] = [ROOT, os.path.dirname(os.path.abspath(__file__))]
    import main
    import listing_scenes
    from kivy.clock import Clock
    from kivy.core.window import Window

    if name == BANNER:
        jobs = [(os.path.join(OUT, BANNER_FILE), listing_scenes.banner)]
    else:
        folder = os.path.join(OUT, name)
        jobs = [(os.path.join(folder, '{:02}-{}.png'.format(i, scene)), build)
                for i, (scene, build) in enumerate(listing_scenes.SCENES, 1)]
    errors = []

    class ListingApp(main.SpacePilgrimApp):
        kv_file = os.path.join(ROOT, 'spacepilgrim.kv')

        def build(self):
            self.title = 'Space Pilgrim listing: ' + name
            self.game = super().build()
            listing_scenes.prepare(self.game)
            return self.game

        def on_start(self):
            Clock.schedule_once(self.begin, 0.5)

        def begin(self, dt):
            if tuple(Window.size) != (width, height):
                errors.append(
                    'window is {}x{} instead of {}x{}; the screen may be too '
                    'small or scaled'.format(*Window.size, width, height))
                return self.stop()
            if name != BANNER:
                os.makedirs(folder, exist_ok=True)
                for old in screenshots(folder):
                    os.remove(old)
            self.jobs = list(jobs)
            self.next_job()

        def next_job(self):
            if not self.jobs:
                return self.stop()
            path, build = self.jobs[0]
            build(self.game, profile['touch'])
            # new widgets are laid out on the next frame: wait two
            Clock.schedule_once(lambda dt: Clock.schedule_once(
                self.capture, 0), 0)

        def capture(self, dt):
            path, build = self.jobs.pop(0)
            image = self.game.export_as_image()
            texture = image.texture
            if tuple(texture.size) != (width, height):
                errors.append('{}: rendered {}x{}'.format(
                    path, *texture.size))
                return self.stop()
            # Kivy already returns the texture rows top to bottom
            write_png(path, width, height, texture.pixels, bottom_up=False)
            print('wrote', os.path.relpath(path, ROOT), flush=True)
            self.next_job()

    ListingApp().run()
    for error in errors:
        print('ERROR ({}): {}'.format(name, error), flush=True)
    return 1 if errors else 0


# ---- command line --------------------------------------------------------

def main(argv):
    import subprocess
    if argv[:1] == ['--child']:
        return _child(argv[1])
    names = argv or list(FORM_FACTORS) + [BANNER]
    unknown = [n for n in names if n not in PROFILES]
    if unknown:
        print('unknown: {}; choose from {}'.format(
            ', '.join(unknown), ', '.join(PROFILES)))
        return 2
    failed = []
    for name in names:
        profile = PROFILES[name]
        env = dict(os.environ,
                   KIVY_METRICS_DENSITY=str(profile['density']),
                   KIVY_DPI=str(profile['dpi']),
                   KIVY_NO_ARGS='1', KIVY_NO_CONSOLELOG='1',
                   SDL_AUDIODRIVER='dummy')
        print('==', name, '{}x{}'.format(*profile['size']), flush=True)
        code = subprocess.call(
            [sys.executable, os.path.abspath(__file__), '--child', name],
            env=env, cwd=ROOT)
        if code:
            failed.append(name)
    problems, counts = check_listing(names=tuple(names))
    for problem in problems:
        print('PROBLEM', problem)
    if failed:
        print('FAILED to render:', ', '.join(failed))
    if problems or failed:
        return 1
    print('OK:', ', '.join('{} {}'.format(n, c) for n, c in counts.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
