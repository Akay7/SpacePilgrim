# Proposal

## Why

Multiplayer today means two to four people around one screen. The README's first ToDo is "Allow multiplayer game on multiple devices": friends on the same Wi-Fi should be able to play together with each person looking at their own phone, tablet, PC or TV, which also lifts the "two players per keyboard, two touch players per phone" limit of a shared screen.

## What Changes

- A new **Network game** entry in the main menu (between *Multiplayer* and *Leaderboard*) opens a network screen, operable by touch, keyboard, gamepad and TV remote, with:
  - **Host a game**: opens this device's join screen as a network game. It is announced on the local network and shows the host's address.
  - a live list of the network games found on the local network (name of the host device, players joined, and whether a game is running, for example "Pixel 8 · in game · 2/4"). Activating one joins it.
  - **Enter address**: join a host by typing its `IP` or `IP:port`, for networks that block broadcast.
- **Shared field, own screen**: one device (the host) runs the game. Every other device (a client) sends its players' input to the host and draws the host's field, scaled to fit its screen (letterboxed when the aspect ratios differ), with its own sounds, explosions and scrolling background.
- **Local and remote players mixed in the four slots**: the host's join screen works as today for its own keyboard sets, gamepads and touch seats. Each connected client sees the same four slots and its own devices join free slots in the same way (FIRE, or its touch strips). A slot shows which device on which machine drives it. The first game starts when at least two players have joined and all are ready, as in local multiplayer. A host with no players of its own is allowed, for example a TV used as the shared display.
- **Join during a game**: the host keeps announcing a running game. A device can connect at any time and sees the field at once. Any device that has not joined, on any connected machine, takes a free slot with FIRE (or a *Tap to join* button on touch devices). The new ship starts with full lives and no points, away from asteroids. A player whose ship was destroyed stays out until the game ends.
- **Leave during a game**: a client device leaves through *Main menu* (from pause) or by closing the app. Its ships are taken out of the game and recorded in the results, its slots become free for others, and the rest play on. The host leaving ends the game for everyone.
- In a network game, each device's own touch players get their controls and *Pause* button on that device. Status blocks show every player's lives and points on every device.
- **Pause** from any player freezes the shared game for everybody and shows the pause screen on every device. *Continue* on any device resumes.
- **No silence timeouts**: only a closed connection counts as leaving. A device that goes silent keeps its slot, and its ship keeps the last input it sent until the asteroids destroy it. A client that loses the host's connection shows a message and returns to the main menu.
- **Shared leaderboard**: connected devices exchange their leaderboards, and every device keeps the combined top 10, so the best players can come from another device. In a network game, the score is saved once per game from any device and is stored on every connected device.
- **Game over**: every device shows the results screen. *Play again* on the host restarts with the players still connected, and clients follow. On a client, *Play again* is replaced by a "Waiting for the host" message.
- A host and a client running different protocol versions refuse to connect, with a clear message.
- **Android**: the app requests the network permissions it needs (`INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE`, `CHANGE_WIFI_MULTICAST_STATE`). It holds a Wi-Fi multicast lock only while it searches for games, so the broadcasts that announce games reach it.
- Single player and same-screen multiplayer do not change.

## Capabilities

### New Capabilities

- `lan-multiplayer`: hosting, finding and joining a game on the local network, the shared join screen across devices, joining and leaving during a game, the host-run shared field drawn on every device, network pause and game over, closed connections, version handling, and leaderboard sharing between connected devices.

### Modified Capabilities

- `game-results`:
  - Survival time counts from when a player joined, for players who join during a network game.
  - The leaderboard is no longer device-only: it is shared with connected devices, and a network game's score is saved once for all devices.
  - *Play again* in a network game is only offered on the host; it restarts with the players still connected and the clients follow it.

## Impact

- `main.py`:
  - A new network layer: discovery broadcast and listener, and host and client sessions over TCP with newline-delimited JSON, polled from the Kivy clock without threads.
  - New screens: `NetworkScreen` and address entry.
  - The join screen's slot table becomes a model that outlives the join screen, so players can join during a game. Remote device ids are stored in the slots, and a ship can be added mid-game.
  - A client-side proxy ship, so the existing `ControlsManager` and the keyboard, gamepad and touch input code drive remote ships unchanged.
  - A client world view that mirrors the host's snapshots, scaled.
  - Network branches in pause, results and `game_over`.
  - `Leaderboard` entries get ids, with merging and file version 2 (old files migrate on load).
  - Android `jnius` declarations for `WifiManager.MulticastLock` and the device model name.
- `spacepilgrim.kv`: a *Network game* menu entry, the layout of the network screen, and the in-game join prompt.
- `buildozer.spec`: `android.permissions`. Adding network access changes the Play Console data-safety answers. `PRIVACY.md` must say that game data and leaderboard entries (nicknames, points, times) go only to devices on the local network.
- `tests/`: new `tests/test_network.py` for the protocol, sessions and discovery, and `tests/test_netgame.py` with host and client games in one process over localhost sockets. Leaderboard migration and merge tests are added, and existing tests stay green.
- `README.md`: a Network game section, an update to the ToDo list, and the leaderboard text, which currently says entries never leave the device.
- No new Python dependencies (standard-library `socket`, `json`, `selectors`, `uuid`).
