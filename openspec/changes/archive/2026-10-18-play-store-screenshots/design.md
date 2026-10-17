# Design

## Context

See proposal.md for motivation. Constraints observed in the project:

- The game is pure Kivy: `main.py` + `spacepilgrim.kv`, assets in `images/`, fonts from Kivy's `data/fonts`. On Android it runs fullscreen with no system bars, so a frame rendered by desktop Kivy at the same size and density is the same image as on a device (confirmed earlier by comparing desktop renders with screenshots from the Android TV emulator).
- Layout depends on `Window.size` (kv rules and code read `Window.width/height`) and on Kivy metrics (`dp`, `cm`), which are fixed when Kivy starts (`KIVY_METRICS_DENSITY`, `KIVY_DPI`, `Config` `graphics` width/height). One process can therefore render only one form factor.
- The game is random and animated: asteroids spawn on a 2 s clock at random places, the debris background scrolls, explosions animate their texture. Fixed scenes need those stopped and objects placed by hand.
- Both Kivy's `Window.screenshot` and `adb screencap` write RGBA PNGs; Google Play rejects alpha. Pillow is not installed in the venv; ImageMagick is installed on this machine but is not a project dependency.
- `buildozer.spec` has `source.dir = .`, `include_exts = py,png,...` and excludes only `android/`, so any new `.py` or `.png` in the repository ends up in the APK.
- Running the real app on this desktop needs `SDL_AUDIODRIVER=dummy` (otherwise it hangs at audio init) and the project `.venv`.

## Goals / Non-Goals

**Goals:**
- One command, no manual steps, same composition on every run.
- Images that pass the Play Console rules by construction and are checked after writing.
- Scene setup kept close to the game code so that API changes break a test, not silently the screenshots.

**Non-Goals:**
- Pixel-identical output between runs (the nebula texture and font hinting are stable, but this is not asserted); headless/CI rendering; device frames or captions.

## Decisions

1. **Render with desktop Kivy, not on emulators.**
   - `tools/play_listing.py` imports `main`, builds the real `SpacePilgrimGame` with `spacepilgrim.kv` and sets up each scene through the game's own objects.
   - Alternative: drive the APK on phone/tablet/TV emulators with `adb input` and `adb screencap`. Rejected: needs an x86 build per change, minutes of emulator boot per form factor, and random asteroid placement makes scenes differ every run. One TV-emulator screenshot is still compared by eye once (task) to confirm the desktop render matches a device.

2. **One child process per form factor, driven by a parent.**
   - The parent (`python tools/play_listing.py [phone|tablet-7|tablet-10|tv|tv-banner]...`, default all) starts itself once per form factor with the profile's environment (`KIVY_METRICS_DENSITY`, `KIVY_DPI`, `SDL_AUDIODRIVER=dummy`, `KIVY_NO_ARGS=1`) and window size, then validates everything it wrote.
   - Profiles (landscape, 16:9):

     | Form factor | Pixels | Density | DPI | Height in dp | Like |
     |---|---|---|---|---|---|
     | phone | 1920x1080 | 2.625 | 420 | ~411 | a 1080p phone in landscape |
     | tablet-7 | 1920x1080 | 1.8 | 288 | 600 | a 7" tablet |
     | tablet-10 | 2560x1440 | 1.8 | 288 | 800 | a 10" tablet |
     | tv | 1920x1080 | 2.0 | 320 | 540 | Android TV (as reported by the TV emulator) |
     | tv-banner | 1280x720 | 2.0 | 320 | 360 | listing banner |

   - Alternative: one process that changes `Window.size` between form factors. Rejected: metrics (`dp`, `cm`) cannot change after start, and touch-control sizes are in `cm`.

3. **Capture through an off-screen buffer at the exact size.**
   - After setting up a scene, the child waits two frames (Kivy lays out new widgets on the next frame), then renders the root widget into an `Fbo` of the profile size (`export_as_image`) and reads its pixels. The window itself is made the profile size; if the compositor gives it a different `Window.size` (screen smaller than 2560x1440, HiDPI scaling), the child stops with a clear error instead of writing a wrongly laid-out image.
   - Alternative: `Window.screenshot`. Rejected: it reads the visible framebuffer, which depends on the window being fully on screen and unscaled.

4. **Write 24-bit PNG with the standard library.**
   - The RGBA pixels are flipped to top-down rows, alpha is dropped, and the file is written with `zlib` + `struct` (IHDR colour type 2, bit depth 8). No Pillow/ImageMagick dependency.
   - The validator reads the PNG signature and `IHDR` (width, height, bit depth, colour type) of every written file, the same way, so it also catches images edited by hand.

5. **Fixed scenes built from game objects.**
   - Common setup: cancel the asteroid spawn and frame clocks so nothing moves or appears, stop the background `Animation` and set a fixed debris offset, give ships fixed angles, and place `Asteroid`, `Shot` and `Explosion` widgets at positions given as fractions of the window (so the same composition works on every size). Explosions are frozen on one texture frame.
   - Touch controls: single-player scenes on phone/tablet turn the touch overlay on (`_set_touch_ui(True)`); multiplayer touch players are joined slots `('touch', 'left'/'right')`, which always show their controls.
   - Scene list (file names `NN-<scene>.png`):

     | # | Phone / tablets | TV |
     |---|---|---|
     | 01 | `gameplay`: single player, firing, two asteroids hit/near, explosion, HUD, joystick + FIRE | `gameplay`: same, no touch controls |
     | 02 | `multiplayer`: two touch players (left/right) in different colours + one gamepad player in the top HUD row | `multiplayer`: three players (keyboard, two gamepads), HUD row at the top |
     | 03 | `join`: keyboard set 1, touch (right side) and a gamepad joined, one slot empty, one player ready | `join`: keyboard set 1 and two gamepads joined, one ready |
     | 04 | `ship-select`: single-player preview in a non-default colour | same |
     | 05 | `menu` | same |

   - The scene builders live in the tool, take the game object, and are also run by a test under the headless mock-GL setup the test suite already uses, so a rename in `main.py` breaks the test.
   - Alternative: add a "showcase mode" to `main.py`. Rejected: it would ship in the APK for no player benefit.

6. **TV listing banner as its own scene.** A 1280x720 child renders the nebula background, the title "Space Pilgrim" (bold, white, left), two asteroids and the ship with the thrust texture flying right, matching the 320x180 launcher banner. Alternative: upscale the 320x180 banner. Rejected: blurry at 4x.

7. **Output layout and packaging.** `store/play/{phone,tablet-7,tablet-10,tv}/NN-<scene>.png` and `store/play/tv-banner.png`. Before rendering a form factor its folder is emptied, so removed scenes do not linger and counts stay right. `buildozer.spec` `source.exclude_dirs = android, tools, store`.
   - The images are **not committed** (`store/play/` in `.gitignore`): a full set is about 64 MB of PNG (the noisy nebula compresses poorly), every regeneration would add that to the history again, and the script recreates the set in about 10 seconds. Alternatives: PNG row filtering (~40% smaller, still ~37 MB per regeneration) or JPEG (~10 MB, needs Pillow and a spec change). Rejected in favour of regeneration.

8. **Touch player status next to their controls.** The status block of a touch player is placed from the actual touch layout instead of a fixed `cm(2.7)`: `SpaceshipStatus` gets an `inset` (distance from its screen edge to the inner edge of that player's joystick column plus a gap), which the game binds to the size and position of the player's `ScreenButtonsLayout.stick`; the kv rule centres the turned label at `inset + line height / 2` from the edge. So it follows the touch size setting and the screen size and never overlaps. Alternative: shrink the font or move the controls. Rejected: controls are sized for thumbs, and the text stays readable.

9. **Touch strips only with touch.** The game keeps `has_touch`: on Android from `PackageManager.hasSystemFeature('android.hardware.touchscreen')` (false on Android TV), elsewhere true (a mouse click is a touch in Kivy); a received touch sets it to true and refreshes an open join screen. `JoinScreen` shows the side strips only while `has_touch` is true. The listing's TV scenes set `has_touch = False`, as on a real TV. Alternative: hide the strips when `is_android_tv()`. Rejected: some TVs and boxes do have touch input, and the requirement is about touch, not device type.

10. **Validation and exit status.** After all children finish, the parent checks every file: PNG, colour type 2 (no alpha), bit depth 8, 16:9 landscape, 1920 ≤ width ≤ 3840 (banner exactly 1280x720), and 4–8 screenshots per form factor. It prints one line per violation with the file name and exits non-zero on any violation or failed child; otherwise it prints the counts per form factor.

## Risks / Trade-offs

- [The display is smaller than 2560x1440 or uses fractional scaling, so the window cannot have the profile size] → the child checks `Window.size` and fails with a message; a hidden window (`window_state = hidden`) is tried first, since SDL honours the requested size for it.
- [Desktop render differs from a device in some detail] → one-time comparison with the TV emulator screenshot of the same scene; differences are fixed in the scene setup, not by editing images.
- [Scene builders depend on private game details such as `_set_touch_ui`] → covered by the test that runs every scene builder headless.
- [Large committed PNGs grow the repository] → five 1080p–1440p PNGs per form factor (a few MB each set); regenerated only when the look changes.
- [Play Console rules change] → the rules live in one table in the tool and in the spec; the validator makes a mismatch visible on the next run.
