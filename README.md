# Space Pilgrim
(previously Rice Rocks)

You control a little spaceship that is opposed to the cosmic asteroids.

## Idea

This game is remake of Rice Rocks the final project of [An Introduction to Interactive Programming in Python](https://www.coursera.org/learn/interactive-python-2) course on Coursera from Rice University.


## How to start play

You have two choices:

- Download in [Play Market](https://play.google.com/store/apps/details?id=pro.crazyrussian.games.spacepilgrim) for your Android device.

- You can start it from source code for this you need installing python and Kivy. [Here](https://kivy.org/docs/installation/installation-windows.html#install-win-dist) instructions for Windows users.

- I'm also planing share binary file for MS Windows systems, but it not ready yet.

## Development

### ToDo

1. Gamepad button remapping.
2. Allow multiplayer game on multiple devices.
3. Ship on Android TV: emulator and real device testing remains (see below).

#### Android TV

The game already runs as a landscape Kivy app and handles arrow keys + space, which a TV remote D-pad and gamepad send as key events.

- [x] Manifest: `android.intent.category.LEANBACK_LAUNCHER` intent filter (`android/intent_filters.xml`) so the app appears in the TV launcher.
- [x] Manifest: `android.hardware.touchscreen`, `android.software.leanback` and `android.hardware.gamepad` declared `required="false"` (`android/extra_manifest.xml`).
- [x] 320x180 px TV banner (`android/res/drawable/banner.png`) referenced as `android:banner` (`android/application_args.xml`).
- [x] Controls: on-screen touch controls shown at start only on Android phones/tablets (not TV), on any device once touched; hidden once a keyboard or gamepad is used. Can be forced on/off in Settings.
- [x] Controls: D-pad centre / Enter / gamepad A / Space shoot (D-pad centre keycode is unverified on a real TV).
- [x] Controls: main menu is navigable with D-pad / stick and Enter / A.
- [x] Controls: Back / Escape returns to the main menu; from the menu it exits (desktop) or pauses the app (Android).
- [x] Gamepad left stick, D-pad and buttons via SDL joystick events (button ids are Xbox-style defaults, untested on hardware).
- [ ] Check HUD and object sizes on 1080p and 4K TV emulators.
- [ ] Test on the Android Studio "Android TV (1080p)" emulator (done: launches from the TV launcher, menu/settings navigable with the remote, Back returns to the menu) and a real device (Chromecast with Google TV, Nvidia Shield).
- [ ] Play Console: opt in to the Android TV form factor, upload 1920x1080 TV screenshots; the app must be fully playable with D-pad / gamepad only.

To verify a build (manifest verified with `aapt2 dump badging`; emulator/device testing still to do):

1. `buildozer android debug`, then check `.buildozer/android/platform/build-*/dists/spacepilgrim/src/main/AndroidManifest.xml` for the `LEANBACK_LAUNCHER` filter, `android:banner` and the three `uses-feature` entries.
2. Create an "Android TV (1080p)" AVD (and a 4K one), `adb install bin/*.apk`, and play using only the emulator remote.

### Controls

| Action | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Turn | Left / Right or A / D | Left stick or D-pad | Stick left / right |
| Thrust | Up or W | Stick up, D-pad up, B / Y | Stick up |
| Fire | Space or Enter | A / X | FIRE button |
| Menu | Escape / Back | Back / Start | - |

Android TV remote D-pad arrives as arrow keys, centre button fires.

### Multiplayer

**Multiplayer** in the main menu starts a local two-player co-op game on one screen: both ships fly in the same field and shoot the same asteroids, each with its own lives and points (shown in the colour of its cabin, player 1 on the left, player 2 on the right). A ship that loses its last life leaves the field; the game ends when both are out. Before every game (single player too) a selection screen shows the ships so each player can pick a cabin colour with `<` / `>` (turn keys on the keyboard) and press *Ready* (fire). Two players cannot pick the same colour; the choice is saved in `ship_colors.json`.

| | Player 1 | Player 2 |
|---|---|---|
| Keyboard (defaults) | W / A / D + Space (arrow keys and Enter also work) | I / J / L + K |
| Gamepad | first gamepad that sends input | second gamepad |
| Touch | left edge: stick at the top, FIRE in the bottom corner | right edge: FIRE at the top, stick in the bottom corner |

With the touch controls the two players sit on opposite sides of the device with the screen between them: each has the stick under the left hand and FIRE under the right hand from their seat: one control in the bottom corner and the other at the top of their side, the two sides being the same shape turned half a circle.

Both keyboard sets work at the same time (very cheap keyboards may not report six held keys at once; the keys are rebindable). One gamepad drives player 1 only, so player 2 can use the keyboard or the touchscreen while player 1 uses the gamepad. In a single-player game any gamepad drives the ship and the second keyboard set is ignored.

Touch controls are a joystick overlay (draggable stick bottom-left: up thrusts, left / right turn, in-between positions combine them; square red FIRE button bottom-right). They appear on any device as soon as the screen is touched and hide again when a keyboard key or gamepad input is used, so keyboard, gamepad and touch can be mixed freely. **Settings > Touch controls** switches between Auto (default), On (always shown) and Off, and sets the size of the controls with a slider (50-400%, left / right keys also work; applied to the next game and limited to what fits on screen); the choices are saved in `touch_ui.json` in the app's user data directory.

Keyboard keys for thrust, turn left, turn right and fire can be changed in **Settings > Keyboard layout** in the main menu: pick an action, then press the new key (Escape cancels). The *Keys of: Player* button switches between the sets of player 1 (defaults W / A / D / Space) and player 2 (I / J / L / K); **Reset to defaults** restores both. Arrow keys, Enter and Escape are fixed (arrows and Enter always steer / fire player 1) so the menus always stay reachable, and a key already used by any action of either player is refused. Bindings of both players are saved in `keybindings.json` (physical keys, so they work on any keyboard layout; files from versions with one set are read as player 1) in the app's user data directory.

### Build for Android

Build and run
```bash
buildozer android debug deploy run
```

View logs
```bash
adb logcat | grep -i python
```

Remove
```bash
adb shell pm uninstall pro.crazyrussian.games.spacepilgrim
```

Release
```bash
buildozer android release
```

## History versions

### 0.1.1

- first version on Play Market

- stable work on python 2.7

### 0.2.0

- public version on Play Market

- stable work on python 3

- renamed from Rice Rocks to Space Pilgrim

### Next version

- main menu with Single player, Multiplayer, Settings and Exit instead of the splash screen

- Android TV support: TV launcher entry and banner, touchscreen / gamepad optional, menus and game playable with the remote D-pad or a gamepad

- gamepad support (left stick, D-pad and buttons)

- configurable keyboard keys (Settings > Keyboard layout), saved between launches

- on-screen touch controls: joystick and a red FIRE button instead of four square buttons, shown on any device once touched and hidden while a keyboard or gamepad is used; Settings > Touch controls has Auto / On / Off and a size slider (50-400%)

- local multiplayer for two players on one device: shared asteroids, separate lives and points, keyboard sets, two gamepads or two touch control sets, one on each side of the screen with texts turned toward the players

- ship selection screen before every game with a cabin colour (blue, green, red, yellow, purple, orange) and a preview of the ship

- second keyboard set (I / J / L / K) and per-player key bindings; saved bindings of older versions are kept for player 1

## Copyright and License

Copyright 2016 - 2017, 2024 Egor Poderiagin.

All source code released under MIT license, more details in LICENSE file.

All sound effects taken from http://www.freesfx.co.uk and remastered in Audacity, if you will reuse it, you must credit www.freesfx.co.uk in your project.

Some of images had taken from final project of "An Introduction to Interactive Programming in Python" course on Coursera from Rice Univercity and can used for not commercial purposes.
