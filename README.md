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

1. Update game for two players on one device.
2. Draw normal joystick on screen instead buttons.
3. Gamepad button remapping.
4. Allow multiplayer game on multiple devices.
5. Implement the Multiplayer menu entry (currently disabled).
6. Ship on Android TV (see below).

#### Android TV

The game already runs as a landscape Kivy app and handles arrow keys + space, which a TV remote D-pad and gamepad send as key events.

- [x] Manifest: `android.intent.category.LEANBACK_LAUNCHER` intent filter (`android/intent_filters.xml`) so the app appears in the TV launcher.
- [x] Manifest: `android.hardware.touchscreen`, `android.software.leanback` and `android.hardware.gamepad` declared `required="false"` (`android/extra_manifest.xml`).
- [x] 320x180 px TV banner (`android/res/drawable/banner.png`) referenced as `android:banner` (`android/application_args.xml`).
- [x] Controls: on-screen touch buttons only on Android phones/tablets (not TV); hidden once a keyboard or gamepad is used, shown again on touch.
- [x] Controls: D-pad centre / Enter / gamepad A / Space shoot (D-pad centre keycode is unverified on a real TV).
- [x] Controls: main menu is navigable with D-pad / stick and Enter / A.
- [x] Controls: Back / Escape returns to the main menu; from the menu it exits (desktop) or pauses the app (Android).
- [x] Gamepad left stick, D-pad and buttons via SDL joystick events (button ids are Xbox-style defaults, untested on hardware).
- [ ] Check HUD and object sizes on 1080p and 4K TV emulators.
- [ ] Test on the Android Studio "Android TV (1080p)" emulator and a real device (Chromecast with Google TV, Nvidia Shield).
- [ ] Play Console: opt in to the Android TV form factor, upload 1920x1080 TV screenshots; the app must be fully playable with D-pad / gamepad only.

To verify a build (not yet done, needs a JDK and the Android Studio emulator):

1. `buildozer android debug`, then check `.buildozer/android/platform/build-*/dists/spacepilgrim/src/main/AndroidManifest.xml` for the `LEANBACK_LAUNCHER` filter, `android:banner` and the three `uses-feature` entries.
2. Create an "Android TV (1080p)" AVD (and a 4K one), `adb install bin/*.apk`, and play using only the emulator remote.

### Controls

| Action | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Turn | Left / Right or A / D | Left stick or D-pad | Left / Right buttons |
| Thrust | Up or W | Stick up, D-pad up, B / Y | Up button |
| Fire | Space or Enter | A / X | Fire button |
| Menu | Escape / Back | Back / Start | - |

Android TV remote D-pad arrives as arrow keys, centre button fires.

Keyboard keys for thrust, turn left, turn right and fire can be changed in **Settings** in the main menu: pick an action, then press the new key (Escape cancels). Defaults are W / A / D / Space; **Reset to defaults** restores them. Arrow keys, Enter and Escape are fixed so the menus always stay reachable, and a key already used by another action is refused. Bindings are saved in `keybindings.json` (physical keys, so they work on any keyboard layout) in the app's user data directory.

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

## Copyright and License

Copyright 2016 - 2017, 2024 Egor Poderiagin.

All source code released under MIT license, more details in LICENSE file.

All sound effects taken from http://www.freesfx.co.uk and remastered in Audacity, if you will reuse it, you must credit www.freesfx.co.uk in your project.

Some of images had taken from final project of "An Introduction to Interactive Programming in Python" course on Coursera from Rice Univercity and can used for not commercial purposes.
