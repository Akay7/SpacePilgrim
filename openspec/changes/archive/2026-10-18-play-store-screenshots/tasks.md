# Tasks

## 1. Image writing and rules

- [x] 1.1 Add `tools/play_listing.py` with the Play rules table (form factors, sizes, 4–8 count, banner 1280x720), an RGBA→24-bit PNG writer using only `zlib`/`struct`, and a validator that reads PNG `IHDR` and reports violations per file; verify with `tests/test_play_listing.py` (writer output has colour type 2 and the right size; validator flags alpha, wrong aspect, too small/large, wrong banner size and bad counts; accepts a valid set) — no Kivy window needed
- [x] 1.2 Exclude the tooling and output from the APK (`buildozer.spec` `source.exclude_dirs = android, tools, store`); verify by checking the setting and, after group 3, that a debug build's `assets/private.tar`/`private.mp3` lists no `tools/` or `store/` entries

## 2. Rendering a form factor

- [x] 2.1 Parent/child runner: the parent starts one child per requested form factor with the profile's window size, `KIVY_METRICS_DENSITY`, `KIVY_DPI`, `SDL_AUDIODRIVER=dummy`; the child builds the game with `spacepilgrim.kv`, checks `Window.size` against the profile (fails with a clear message otherwise), empties its output folder, and captures the root widget off-screen after two frames; verify by running `tools/play_listing.py tv` with a trivial scene and checking the file size/alpha with the validator
- [x] 2.2 Freeze helpers: stop asteroid spawning and frame updates, stop the background scroll at a fixed offset, place asteroids/shots/explosions at window fractions, freeze explosions on one frame; verify with a test that after the helpers run, a `Clock.tick()` moves nothing and spawns no asteroid

## 3. Scenes

- [x] 3.1 Scene builders `gameplay`, `multiplayer`, `join`, `ship-select`, `menu` with the phone/tablet and TV variants from design decision 5 (touch controls on phone/tablet, none on TV; two touch players at the sides on phone/tablet; keyboard/gamepad players on TV); verify with a test that runs every builder for both variants on the headless game (mock GL) and checks touch overlay visibility, number of ships, distinct cabin colours and joined slots
- [x] 3.2 Render all four sets (`tools/play_listing.py`), look at every image and adjust positions until each scene reads well at its density (no control covering the HUD, ship and explosion clearly visible, gameplay first); verify by the run exiting 0 with "5 images" per form factor and by viewing the images
- [x] 3.3 Compare the TV `01-gameplay` render with an Android TV emulator screenshot of a similar moment (x86 debug APK) and fix any difference in the scene setup; verify by viewing both side by side

## 4. TV listing banner

- [x] 4.1 Banner scene at 1280x720 (nebula background, bold "Space Pilgrim" title on the left, two asteroids, ship with thrust flying right), written as `store/play/tv-banner.png`; verify with the validator (exactly 1280x720, no alpha) and by comparing it with `android/res/drawable/banner.png`

## 4b. Game fixes found by the screenshots

- [x] 4b.1 Place a touch player's status block next to their touch controls (`SpaceshipStatus.inset` bound to the player's stick column, kv uses it for left/right) instead of the fixed `cm(2.7)`; verify with a test that at a phone-like size and at 100% and 300% touch size the turned label's horizontal extent does not overlap the stick or FIRE of that side, and by the phone/tablet multiplayer screenshots
- [x] 4b.2 Show the join screen's "Tap to join by touch" strips only while the game knows of a touchscreen (`has_touch`: Android touchscreen feature, true elsewhere, set by the first touch, refreshes an open join screen); the TV listing scenes use `has_touch = False`; verify with tests that strips are hidden without touch, appear on the first touch, and that existing join tests still pass, and by the TV join screenshot
- [x] 4b.3 Update the README multiplayer section for both behaviours; verify the text matches the code

## 5. Repository and docs

- [x] 5.1 Add `store/play/` to `.gitignore`, generate the final set, and update the README (how to run `tools/play_listing.py`, what it produces, that the images are regenerated rather than committed, the display/venv requirements, and point the Android TV "upload 1920x1080 TV screenshots" checklist item at `store/play/tv/`); verify by following the README command from a clean shell, getting exit status 0, and `git status` not listing `store/play/`
- [x] 5.2 Run the full test suite (`.venv/bin/python -m pytest tests`) and verify it passes
