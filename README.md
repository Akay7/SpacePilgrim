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

1. Allow multiplayer game on multiple devices.
2. Ship on Android TV: HUD size check and Play Console steps remain (see below).

#### Android TV

The game runs on Android TV (TV launcher entry and banner, optional touchscreen / gamepad, menus and game playable with the D-pad or a gamepad), tested on the emulator and a real device. Still to do:

- [ ] Check HUD and object sizes on 1080p and 4K TV emulators.
- [x] Test on the Android Studio "Android TV (1080p)" emulator (launches from the TV launcher, menu/settings navigable with the remote, Back returns to the menu) and a real device.
- [ ] Play Console: opt in to the Android TV form factor, upload the 1920x1080 TV screenshots from `store/play/tv/` and the 1280x720 TV banner `store/play/tv-banner.png` (see [Google Play listing images](#google-play-listing-images)); the app must be fully playable with D-pad / gamepad only.

To verify a build (manifest verified with `aapt2 dump badging`):

1. `buildozer android debug`, then check `.buildozer/android/platform/build-*/dists/spacepilgrim/src/main/AndroidManifest.xml` for the `LEANBACK_LAUNCHER` filter, `android:banner` and the three `uses-feature` entries.
2. Create an "Android TV (1080p)" AVD (and a 4K one), `adb install bin/*.apk`, and play using only the emulator remote.

### Controls

| Action | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Turn | Left / Right or A / D | Left stick or D-pad | Stick left / right |
| Thrust | Up or W | Stick up (power follows the push), D-pad up, B / Y, or a trigger (variable power) | Stick up (power follows the push) |
| Fire | Space or Enter | A / X (rebindable) | FIRE button |
| Pause | Escape / Back | Back / Start | Pause button |

Android TV remote D-pad arrives as arrow keys, centre button fires. The gamepad buttons for thrust and fire are the defaults and can be changed per gamepad (see below).

### Multiplayer

**Multiplayer** in the main menu opens a join screen for a local co-op game of two to four players on one screen: all ships fly in the same field and shoot the same asteroids, each with its own lives and points. A ship that loses its last life leaves the field; the game ends when all are out.

On the join screen every player takes a slot with the device they will play with:

| Device | Join | Colour | Ready | Leave |
|---|---|---|---|---|
| Keyboard set 1 (W / A / D + Space; arrow keys and Enter also count as set 1) | Space | A / D | Space | W |
| Keyboard set 2 (I / J / L + K) | K | J / L | K | I |
| Gamepad | A / X (fire) | stick or D-pad left / right | A / X | Back / Start |
| Touch | *Tap to join by touch* strip at the edge where you sit: left or right, and on a tablet also top or bottom (shown on devices with a touchscreen, or after the first touch) | `<` / `>` | *Ready* | *Leave* |

Every device, a side strip included, takes the first free slot; a strip is greyed out while a touch player sits at its edge. Each slot shows the device that joined it and lights up when that device is used, so everyone sees which keys or pad belong to which ship, and players can set up at the same time. At most two players share the keyboard (two sets) and at most two play by touch on a phone, or four on a screen of at least 15 x 10 cm (a tablet, checked automatically from the screen's physical size); further players use gamepads (up to four players). The game starts when at least two players have joined and all of them are *Ready*. Escape, or Back / Start on a pad that has not joined, returns to the menu. Players cannot pick the same cabin colour; the choice of each slot is saved in `ship_colors.json`. Single player keeps a one-ship selection screen that any keyboard set or gamepad drives.

In the game each device drives only the ship it joined with; devices that did not join are ignored except Back / Escape, which pauses the game. Touch players sit at the edges of the device, facing the middle, at the edge whose strip they tapped: each has the stick under the left hand and FIRE under the right hand from their seat. With only left and right players, one control is in the bottom corner and the other at the top of their side; once someone sits at the top or bottom edge, every player has their two controls the same distance apart around the middle of their edge, as far apart as the screen allows (the players at the short edges keep theirs in the corners: left and right on a wide screen, top and bottom on a tall one; with a keyboard or gamepad player the corners are kept for their lives and points; smaller controls if the screen needs it). Their stick is turned toward them: push it away from you (toward the middle of the screen) to thrust, and to your own left / right to turn. Their controls stay shown for the whole game, whatever the touch setting; keyboard and gamepad players get none. A touch player's lives and points are at the middle of their edge, just inside their own touch controls (they move with the controls' size setting and never cover them), turned toward them; keyboard and gamepad players sit in front of the screen and their lives and points run along the top in player order, or sit in the free corners (player 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right) when a touch player is at the top or bottom edge. Each block is in the colour of the player's cabin.

Both keyboard sets work at the same time (very cheap keyboards may not report six held keys at once; the keys are rebindable). In a single-player game any keyboard set and any gamepad drives the ship.

Touch controls are a joystick overlay (draggable stick bottom-left: up thrusts, harder the further up the knob is, left / right turn, in-between positions combine them; square red FIRE button bottom-right). They appear on any device as soon as the screen is touched and hide again when a keyboard key or gamepad input is used, so keyboard, gamepad and touch can be mixed freely. **Settings > Touch controls** switches between Auto (default), On (always shown) and Off, and sets the size of the controls with a slider (50-400%, left / right keys also work; applied to the next game and limited to what fits on screen); the choices are saved in `touch_ui.json` in the app's user data directory.

Keyboard keys for thrust, turn left, turn right and fire can be changed in **Settings > Keyboard layout** in the main menu: pick an action, then press the new key (Escape cancels). The *Keys of: Set* button switches between keyboard set 1 (defaults W / A / D / Space) and set 2 (I / J / L / K); **Reset to defaults** restores both. Arrow keys, Enter and Escape are fixed (arrows and Enter always count as set 1) so the menus always stay reachable, and a key already used by any action of either set is refused. Bindings of both sets are saved in `keybindings.json` (physical keys, so they work on any keyboard layout; files from versions with one set are read as set 1) in the app's user data directory.

The gamepad buttons for thrust and fire can be changed in **Settings > Gamepad buttons**: the first entry chooses the gamepad to edit (the connected pads, by name), then pick *Thrust* or *Fire* and press the new button on that pad (Back / Start or Escape cancels); the new button replaces the old ones (the defaults are A / X for fire and B / Y for thrust). Every gamepad model has its own layout, found again after a restart or reconnect by the pad's name and GUID, so two different pads in one multiplayer game can have different buttons; two pads of the same model share one layout. A pad that cannot be identified uses the defaults and its changes last for the session only.

*Thrust* takes a trigger as well as a button: select it, then press a button or pull a trigger of the pad (any axis except the left stick; it works whether the trigger rests at -1 or 0), whichever you use is bound. A trigger is then the pad's thrust (its thrust buttons do nothing) and the more you pull, the faster the ship flies; binding a button to Thrust again replaces the trigger. The left stick, D-pad and Back / Start are fixed, and a button already used by the other action is refused. The layouts apply only while a game runs: menus, the join screen, popups and settings always use the standard buttons (A / X confirm, B / Y move up), so remapping never changes how you navigate. **Reset to defaults** resets only the chosen pad. The layouts are saved in `gamepad_buttons.json` in the app's user data directory.

### Pause

In a game, Escape / Back (or a gamepad's Back / Start) pauses; touch players also have a **Pause** button under their lives and points (it goes away once their ship is lost). It freezes the whole game (ships, asteroids, shots, explosions, the scrolling background, the clock) behind a dimmed pause screen with **Continue** and **Main menu**; the pause screen also works with the keyboard and gamepads, and Back / Escape on it continues. **Main menu** leaves the game without the results screen.

### Game over and leaderboard

When the last ship is lost, a results screen shows each player's time survived (seconds) and points; the points are the rating, and in multiplayer the longest survivor is marked. **Save to leaderboard** asks for a nickname (up to 12 characters, prefilled with the last one used; on a gamepad or remote just accept it with Save) and stores the game's top player (the only player, or the one with most points) with their nickname, points and time in `leaderboard.json` in the app's user data directory; it never leaves the device. **Play again** restarts with the same players, devices and cabin colours, and **Main menu** (or Back / Escape) returns to the menu. The **Leaderboard** entry of the main menu lists the best ten, ordered by points (the time only breaks ties). Leaving a game through the pause screen skips the results screen.

### Google Play listing images

The store listing images are rendered from the game itself, so they never need to be taken by hand:

```bash
.venv/bin/python tools/play_listing.py        # everything
.venv/bin/python tools/play_listing.py tv     # one set
```

It writes five 16:9 screenshots each for `phone` (1920x1080), `tablet-7` (1920x1080), `tablet-10` (2560x1440) and `tv` (1920x1080), plus the Android TV listing banner `tv-banner.png` (1280x720), into `store/play/`, and checks every file against the Play Console rules (24-bit PNG without alpha, 16:9, 1920-3840 px, 4-8 per set); it exits with an error naming the file if one breaks a rule. The scenes (gameplay first, multiplayer, join screen, ship selection, menu) are fixed in `tools/listing_scenes.py` and use the real game widgets at each device's size and screen density, with touch controls on phone/tablet and keyboard/gamepad players on TV. Rerun it after any visual change. The images are not committed (`store/play/` is in `.gitignore`, a full set is ~60 MB) and, like the script, are not packaged into the APK. It needs a desktop session with a display (it renders in hidden windows, so a locked screen is fine) and takes about 10 seconds.

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

## Copyright and License

Copyright 2016 - 2017, 2024, 2026 Egor Poderiagin.

All source code released under MIT license, more details in LICENSE file.

All sound effects taken from http://www.freesfx.co.uk and remastered in Audacity, if you will reuse it, you must credit www.freesfx.co.uk in your project.

Some of images had taken from final project of "An Introduction to Interactive Programming in Python" course on Coursera from Rice Univercity and can used for not commercial purposes.
