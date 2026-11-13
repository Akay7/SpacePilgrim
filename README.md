# Space Pilgrim
(previously Rice Rocks)

You control a little spaceship that is opposed to the cosmic asteroids. Play alone, with up to four players on one screen, or on several phones, tablets, PCs and TVs over the local Wi-Fi.

## Idea

This game is a remake of Rice Rocks, the final project of the [An Introduction to Interactive Programming in Python](https://www.coursera.org/learn/interactive-python-2) course on Coursera from Rice University.


## How to start playing

- Install it from [Google Play](https://play.google.com/store/apps/details?id=pro.crazyrussian.games.spacepilgrim) on an Android phone, tablet or Android TV.

- Run it from the source code: install Python 3 and Kivy ([installation instructions](https://kivy.org/doc/stable/gettingstarted/installation.html)), then run `python main.py`. On Linux, menus and buttons follow the display scaling set in your desktop settings (for example 200% on a high-resolution laptop screen). To turn that off, start it with `KIVY_METRICS_DENSITY=1 python main.py`.

## How to play

### Controls

| Action | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Turn | Left / Right or A / D | Left stick or D-pad | Stick left / right |
| Thrust | Up or W | Stick up (power follows the push), D-pad up, B / Y, or a trigger | Stick up (power follows the push) |
| Fire | Space or Enter | A / X | FIRE button |
| Pause | Escape / Back | Back / Start | Pause button |

The Android TV remote's D-pad works as the arrow keys and its centre button fires. Touch controls (a joystick bottom-left, FIRE bottom-right and **Pause** between them) appear when the screen is touched and hide when a keyboard or gamepad is used.

The game can be played in portrait or landscape on every device and turns with it; the system's rotation lock keeps it as it is. Turning the device during a touch game moves the players' controls to other edges, so turn the rotation lock on before playing around a tablet.

### Settings

- **Keyboard layout**: rebind thrust, turn and fire for keyboard set 1 (W / A / D / Space) and set 2 (I / J / L / K). Arrow keys, Enter and Escape stay fixed so the menus are always reachable.
- **Gamepad buttons**: choose the thrust and fire buttons for each gamepad model (found again by its name). Thrust also takes a trigger, which then thrusts harder the further it is pulled. Menus always use the standard buttons (A / X confirm, B / Y up).
- **Touch controls**: Auto (default), On or Off, and their size (50-400%).

Settings, cabin colours, the leaderboard and the device name are saved in the app's user data directory (`keybindings.json`, `gamepad_buttons.json`, `touch_ui.json`, `ship_colors.json`, `leaderboard.json`, `network.json`).

### Multiplayer

**Multiplayer** opens a join screen for two to four players. All ships fly in the same field and shoot the same asteroids, each with its own lives and points; the game ends when every ship is lost.

Each player takes a slot with the device they play with, picks a cabin colour and gets ready:

| Device | Join and ready | Colour | Leave |
|---|---|---|---|
| Keyboard set 1 (W / A / D + Space; arrows and Enter too) | Space | A / D | W |
| Keyboard set 2 (I / J / L + K) | K | J / L | I |
| Gamepad | A / X | stick or D-pad left / right | Back / Start |
| Touch | *Tap to join by touch* strip at your edge of the screen | `<` / `>` | *Leave* |

The game starts when at least two players have joined and all are ready. Up to two players share the keyboard, and up to two play by touch on a phone or four on a tablet (one at each edge); further players use gamepads. On a phone the two touch players sit at its short ends: left and right in landscape, top and bottom in portrait. Touch players get their joystick, FIRE and **Pause** at their own edge, turned toward them. Escape, or Back / Start on a pad that has not joined, returns to the menu.

### Network game

Several devices on the same Wi-Fi can play one game, each player looking at their own screen. A keyboard set, gamepad or TV remote that has not joined reaches the row under the slots with Down:

- **Device name**: how the other devices see this one. Empty means the phone's model or the computer's name. It is kept between runs.
- **Local network: On** hosts the game: the players already joined keep their slots, the screen shows the address (for example `Hosting on 192.168.1.20:47400`), and other devices can find the game.
- **Join a network game** lists the games found on the Wi-Fi; pick one to join. **Enter address** joins by `IP` or `IP:port` when the list stays empty (some networks block broadcasts).

The host runs the game and the other devices show its field, scaled to fit their screen and turned when that shows it bigger (a TV's field on a phone held upright); their own controls and lives and points sit beside it where there is room. Every device joins players with its own keyboard sets, gamepads and touch strips, and each slot shows which device it is on (`Gamepad 1 · Pixel 8`). The host does not need a player of its own, so a TV can be the shared screen.

- **Joining and leaving during a game**: a device can connect at any time. A device with no player in the game takes a free slot with FIRE or *Tap to join*. A device that has a player adds no more until the game ends, and a destroyed player stays out. *Main menu* on the pause screen, or closing the app, leaves the game; when the host leaves, the game ends for everybody.
- **Pause** on any device pauses every device, and *Continue* on any device resumes.
- **No timeouts**: a device that goes silent keeps its slot, and its ship flies on until the asteroids get it.
- **Leaderboard**: connected devices share their leaderboards and keep the combined top ten. After a game, only the top player's device offers *Save to leaderboard*, and the score goes into every device's leaderboard. *Play again* is on the host.

Nothing is sent to the internet (see [PRIVACY.md](PRIVACY.md)). On a desktop, allow TCP ports 47400-47409 and UDP port 47401 in the firewall, for example `firewall-cmd --add-port=47400-47409/tcp --add-port=47401/udp`.

### Pause, results and leaderboard

Escape / Back, Back / Start on a gamepad, or a touch player's **Pause** button (between their joystick and FIRE) freezes the game; the pause screen has **Continue** and **Main menu**.

When the last ship is lost, the results show each player's time survived and points. **Save to leaderboard** stores the top player with a nickname (up to 12 characters). **Play again** restarts with the same players, devices and colours. **Leaderboard** in the main menu lists the best ten by points (the time only breaks ties).

## Development

### ToDo

1. Share a ready-to-run binary for Windows.

### Tests

```bash
.venv/bin/python -m pytest tests
```

The network code is in `network.py` (standard library only); `tests/test_network.py` and `tests/test_netgame.py` play host and clients over localhost.

### Build for Android

```bash
buildozer android debug deploy run                     # build and run
adb logcat | grep -i python                            # logs
adb shell pm uninstall pro.crazyrussian.games.spacepilgrim
buildozer android release                              # release build
```

To check an Android TV build, look in `.buildozer/android/platform/build-*/dists/spacepilgrim/src/main/AndroidManifest.xml` for the `LEANBACK_LAUNCHER` filter, `android:banner` and the three `uses-feature` entries, then install it on an "Android TV (1080p)" emulator and play with the remote only.

### Google Play listing images

```bash
.venv/bin/python tools/play_listing.py        # everything
.venv/bin/python tools/play_listing.py tv     # one set
```

This renders the store screenshots from the game itself into `store/play/`: five 16:9 images each for `phone`, `tablet-7`, `tablet-10` and `tv`, plus the 1280x720 Android TV banner. It checks every file against the Play Console rules and fails naming the file that breaks one. The scenes are in `tools/listing_scenes.py`. Rerun it after any visual change; it needs a desktop session (hidden windows, so a locked screen is fine). The images are not committed.

## History versions

### 0.1.1

- first version on Play Market

- stable work on python 2.7

### 0.2.0

- public version on Play Market

- stable work on python 3

- renamed from Rice Rocks to Space Pilgrim

### 0.3.0

- main menu with Single player, Multiplayer, Settings and Exit instead of the splash screen

- Android TV support: TV launcher entry and banner, touchscreen / gamepad optional, menus and game playable with the remote D-pad or a gamepad

- gamepad support (left stick, D-pad and buttons)

- configurable keyboard keys (Settings > Keyboard layout), saved between launches

- on-screen touch controls: joystick and a red FIRE button instead of four square buttons, shown on any device once touched and hidden while a keyboard or gamepad is used; Settings > Touch controls has Auto / On / Off and a size slider (50-400%)

- local multiplayer for two to four players on one device: a join screen where each player joins and leaves with their own device (one of two keyboard sets, a gamepad, or touch for up to two players at the sides of the screen), shared asteroids, separate lives and points

- cabin colour (blue, green, red, yellow, purple, orange) with a preview of the ship before every game

- second keyboard set (I / J / L / K) with its own key bindings; saved bindings of older versions are kept for set 1

### 0.3.1

- Android: the system status and navigation bars are hidden while playing (swipe from the screen edge shows them), so they no longer cover the touch controls

- a Menu button returns from a touch game to the main menu (touch has no Back key)

- touch controls are sized in dp instead of cm, so a wrongly reported screen DPI no longer makes them huge, and never take more than 40% / 25% of the screen height on small screens

### 0.3.2

- smaller, finger-sized touch controls by default (joystick 110 dp, FIRE 76 dp)

- two touch players on a small screen: joystick and FIRE sit in the corners of each side instead of being pushed toward the middle

- the Menu button sits under the lives and points text: below it for one player, at the middle of the side (between the two controls) for each touch player, so it is not pressed by mistake

### 0.3.3

- Android / Android TV: a gamepad that connects after the app has started (Bluetooth) is now opened, so its stick and D-pad steer and navigate the menus, not only its buttons

- Android: gamepad button numbers follow Android's layout, so clicking the left stick while steering no longer leaves the game (Back / View and Start do); the pad is picked up within a quarter of a second of connecting

### 0.3.4

- pause: Escape / Back / Start (or a Pause button for touch players) freezes the game behind a pause screen with Continue and Main menu, instead of ending it

- game over results screen with each player's time survived and points, Play again, and a local leaderboard of the best ten (nickname, points, time) in the main menu

- Android: black presplash screen

### 0.4.0

- up to four touch players on a tablet: on a screen of at least 15 x 10 cm (checked automatically from its physical size) the join screen also has *Tap to join by touch* strips at the top and bottom edges, so four players can sit around the device, one at each edge; phones keep the two side seats

- every touch player's joystick and FIRE, lives, points and Pause button are turned to read from their own edge, and pushing the joystick toward the middle of the screen thrusts

- with a player at the top or bottom edge, every player has their joystick and FIRE the same distance apart around the middle of their edge, as far apart as the screen allows (the players at the short edges keep them in the corners), and the controls shrink together when the screen is tight; keyboard and gamepad players' lives and points then move to the screen corners

### 0.4.1

- Android / Android TV: all sounds are mixed in the game (SDL2 mixer), so the engine, shots and explosions are heard together; on some TVs only one of them was heard at a time

- multiplayer: the engine sound plays while any ship thrusts, so one player letting go no longer silences the others, and it keeps playing when thrust is held longer than the 13 s sample

- shots and explosions of several players overlap instead of cutting each other off

- Android: faster start (about 2 s less on a slow TV), and no more freeze of up to 24 s right after the menu appears on slow devices, when the game ignored the remote and gamepads and the screen stopped updating

### 0.5.0

- Settings > Gamepad buttons: choose which buttons thrust and fire, separately for every gamepad model (found again by name and GUID), saved in `gamepad_buttons.json`; Back / Start, the left stick and the D-pad stay fixed, and menus, popups and settings keep the standard buttons (A / X confirm, B / Y up) whatever the layout

- Thrust takes a button or a trigger through the same entry: a trigger thrusts with power that follows how far it is pulled, and a button replaces it again

- multiplayer: a touch player's Pause button disappears once their ship is lost (their lives and points stay)

- thrust power on the sticks: pushing the on-screen joystick or the gamepad's left stick up thrusts harder the further it goes (D-pad, thrust buttons and keys stay full power)

- desktop: a gamepad that is switched on or plugged in again while the game runs is picked up (it was only opened at start-up before); Android already did this

### 0.6.0

- network game: one game on several phones, tablets, PCs and TVs on the same Wi-Fi, each player looking at their own screen; the host runs the game and the other devices show its field, scaled and turned to fit

- *Local network: On* on the Multiplayer join screen hosts the game; *Join a network game* finds games on the local network, or joins one by address when broadcasts are blocked

- *Device name* on the Multiplayer join screen sets how the other devices see this one (the model or computer name by default)

- local and remote players share the four slots; devices can join and leave during a game, and a device that already has a player in the game adds no more until it ends

- pause on any device pauses every device; *Play again* on the host restarts the game for everybody still connected

- shared leaderboard: connected devices exchange their leaderboards and keep the combined top ten; after a network game only the top player's device saves the score, into every device's leaderboard

- the game turns with the device on phones, tablets, foldables and Chromebooks, in portrait and landscape, with no orientation or resizing restriction (Google Play asked for this for large screens)

- every screen fits a phone held upright and follows the window when it turns or is resized; the Multiplayer join screen shows its slots two by two on a narrow screen

- on a phone held upright the two touch players sit at the top and bottom

- keyboard and gamepad players' lives and points fit a phone held upright: two per row at the top, or beside the left and right edges when touch players sit at the top and bottom

- the Pause button sits between the touch player's joystick and FIRE, on their bottom line, in single player and multiplayer

- the scrolling debris keeps its own proportions instead of stretching on wide and tall screens

- Linux desktop: menus and buttons follow the desktop's display scaling (they were half size at 200%)

- Android: the nickname, address and device-name boxes stay above the on-screen keyboard while typing

- Android: network permissions (`INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE`, `CHANGE_WIFI_MULTICAST_STATE`) for the network game

## Copyright and License

Copyright 2016 - 2017, 2024, 2026 Egor Poderiagin.

All source code released under MIT license, more details in LICENSE file.

All sound effects were taken from http://www.freesfx.co.uk and remastered in Audacity; if you reuse them, you must credit www.freesfx.co.uk in your project.

Some of the images were taken from the final project of the "An Introduction to Interactive Programming in Python" course on Coursera from Rice University and can be used for non-commercial purposes only.
