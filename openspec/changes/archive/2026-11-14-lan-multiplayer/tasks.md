# Tasks

## 1. Protocol and sockets (`network.py`)

- [x] 1.1 Create `network.py` (standard library only, no Kivy) with `NET_PROTOCOL = 1`, the default ports (TCP 47400, UDP 47401), and `encode(msg)` / `Decoder.feed(bytes) -> [msg]` for newline-delimited JSON.
  - The decoder rejects lines over 64 KiB, invalid JSON, a missing or unknown `t`, and wrongly typed fields, using a schema per message type from the table in design decision 4.
  - It validates devices (`['keys', 0|1]`, `['pad', int]`, `['touch', side]`) and skips invalid leaderboard entries inside `lb`.
  - Add `tests/test_network.py` with round-trip and rejection tests for every message type, including a split line fed in two chunks and an oversized line.
  - Verify with `.venv/bin/python -m pytest tests/test_network.py -k codec`.
- [x] 1.2 Add `Connection`, `HostSession` and `ClientSession`, all driven by `poll()` through `selectors`, reporting events (message, closed) through callbacks.
  - `Connection`: a non-blocking socket with a read buffer, a reliable outbox capped at 1 MiB, and a latest-snapshot slot written only when the outbox is empty.
  - `HostSession`: listens on the first free port of 47400–47409, accepts at most 8 clients, and answers `hello` with `welcome` (with phase) or `refuse` for `version` and `full`.
  - `ClientSession`: non-blocking connect with a 5 s limit on setting up the connection, `hello`, and `welcome` / `refuse` handling.
  - There are no pings and no idle timeouts.
  - Test over `127.0.0.1` with port 0:
    - handshake, version refusal and ninth-client refusal
    - a garbage connection closed while the other client stays
    - a peer closing its socket reported as closed on the other side, for both directions
    - an idle connection staying open for 30 s of faked clock
    - a slow reader getting only the newest snapshot
    - outbox overflow closing the connection
  - Verify with `pytest tests/test_network.py -k session`.
- [x] 1.3 Add `Announcer`, `Browser`, `local_address()` and `parse_address('a.b.c.d[:port]')`.
  - `Announcer`: a broadcast datagram to `255.255.255.255:47401` once a second with name, proto, port, players and playing. The target address can be injected for tests.
  - `Browser`: bound with `SO_REUSEADDR` / `SO_REUSEPORT`. It builds the list of hosts by source IP, drops entries after 3 s, flags a protocol mismatch, and ignores foreign or malformed datagrams.
  - `local_address()`: the UDP-connect trick with a fallback.
  - Test the announcer-to-browser path over loopback, expiry with a faked clock, mismatch flagging, the `playing` flag, garbage datagrams, and address parsing including bad input.
  - Verify with `pytest tests/test_network.py -k "browse or address"`.

## 2. Leaderboard ids and merging

- [x] 2.1 Move `Leaderboard` to file `VERSION = 2`.
  - Each entry gets an `id` (16 hex characters from `uuid4`): `new_entry()` builds one, and `add()` keeps returning whether the file was written.
  - Version 1 files get ids on load, with order and content unchanged.
  - `merge(entries)` adds unknown ids (validated like `load()`), sorts, keeps the top 10, saves, and returns whether anything changed. `last_name` is untouched.
  - Test a version 1 file migrating with the same order, that merging the same list twice adds nothing, that merging a better entry puts it first and is kept after a reload, that invalid merged entries are skipped, and that an older reader (the version 1 `load()` logic) still reads a version 2 file.
  - Update the README leaderboard text, which says entries never leave the device.
  - Verify with `pytest -k leaderboard`.

## 3. Menu, network screen and address entry

- [x] 3.1 Add the "Network game" entry to `<Menu>` in `spacepilgrim.kv` between Multiplayer and Leaderboard, keeping the menu inside a 360 dp landscape height (buttons of at least 44 dp). Add a test that the menu has six buttons in the new order and fits a 640×360 dp window (in `tests/test_netgame.py`), and that the existing menu navigation tests still pass. Verify with `pytest tests -k menu`.
- [x] 3.2 Add `NetworkScreen`, a `ButtonColumn`.
  - Contents: "Host a game"; one button per found game, such as "Pixel 8 · 2/4" or "Pixel 8 · in game · 3/4", with "Pixel 8 · other version" disabled; a "Searching for games on this Wi-Fi…" label when the list is empty; "Enter address"; "Back"; and a message line for errors.
  - It owns a `Browser`, polled at 30 Hz while open, and rebuilds its buttons without losing the selection.
  - Wire it into `SpacePilgrimGame`: `show_network`, and `network_active` routing in `_input`, with Back returning to the menu.
  - Test that the screen opens from the menu with keyboard and gamepad actions, that a fake browser result adds and removes entries with the right labels, that a mismatched entry cannot be activated, and that Escape returns to the menu.
  - Verify with `pytest -k network_screen`.
- [x] 3.3 Add `AddressScreen`, using the `NameScreen` layout.
  - It is prefilled from `network.json`, or with the first three octets of `local_address()`, and saves the last address used.
  - On accept it parses the address and starts a `ClientSession`.
  - Parse errors, connect failures and refusals return to the network screen with the reason shown: "Could not reach the host (same Wi-Fi? firewall?)", "The game versions differ", or "The game is full".
  - Test each outcome with a local `HostSession` or a closed port, and test that a corrupt `network.json` falls back to the default.
  - Verify with `pytest -k address`.
- [x] 3.4 Android:
  - Add the permissions line to `buildozer.spec`.
  - Declare `WifiManager` / `MulticastLock` and `Build.MODEL` in `declare_java_classes()`.
  - Take the multicast lock when `NetworkScreen` opens and release it when it closes.
  - Add `device_name()`, which returns `Build.MODEL` or `socket.gethostname()`.
  - On desktop, test that `device_name()` returns a non-empty string and that the lock helpers do nothing outside Android.
  - Verify with `pytest -k device_name`, then with `buildozer android debug` and `aapt2 dump permissions` listing the four permissions.

## 4. Lobby, hosting and the shared join screen

- [x] 4.1 Extract a `Lobby` model (slots, per-slot state `joined` / `ready` / `playing` / `out`, colours, `join`, `leave`, `change`, `toggle_ready`, `can_start`) from `JoinScreen`, and make `JoinScreen` a view and controller of a `Lobby` it is given or creates. This is a refactor with no behaviour change: verify that every existing join-screen and local multiplayer test passes unchanged with `pytest tests/test_game.py -k "join or multiplayer or seat"`, then the full `pytest tests`.
- [x] 4.2 Host side of the join screen.
  - "Host a game" opens a `JoinScreen` on a host `Lobby` with a `HostSession` and an `Announcer`, and shows "Hosting on <ip>:<port>" in the message line.
  - Remote devices are `('net', peer, device)`. `device_kind`, `device_label` (with " · <machine name>") and `device_hint` look through the wrapper.
  - Client `act` / `touch` messages go to `handle`, `join` and the panel methods, only for slots of that peer. Every `Lobby` change sends `lobby` to all clients.
  - A closed client connection or `bye` frees that peer's slots. Leaving the join screen sends `bye: host-ended` and closes the session and the announcer.
  - Test with an in-process client:
    - a client gamepad joins slot 2 after a host keyboard joins slot 1
    - keyboard set 1 on both machines gets two slots
    - a client cannot change another peer's slot
    - closing the client socket frees its slot
    - Escape on the host closes everything
  - Verify with `pytest -k host_join`.
- [x] 4.3 Give `JoinScreen` a client mirror mode.
  - Local device actions, touch strips and panel buttons send `act` / `touch` instead of changing state.
  - `refresh()` draws the latest `lobby`. The client's own slots say " · this device", and touch strips use the client's own `touch_seats()`.
  - Escape sends `bye` and shows the menu. Connecting from `NetworkScreen` (a found game or an address) in the `lobby` phase opens this screen.
  - On both the host's and the client's join screen, the panel buttons of a slot held by another machine are disabled, and keyboard sets show as "Keyboard N · <machine>".
  - Also test that each screen's own panel buttons are enabled and the other machine's are disabled.
  - Test with an in-process host: the client's lobby matches the host's within one poll cycle, colour and ready changes on the client show on both, a flash on the host shows on the client, and Escape on the client frees its slot on the host.
  - Verify with `pytest -k client_join`.
- [x] 4.4 Update the README Multiplayer section with a "Network game" subsection: hosting, finding and joining, address entry, mixing local and remote players, joining and leaving during a game, the shared leaderboard, firewall ports (TCP 47400–47409, UDP 47401), and the same-Wi-Fi note. Update the ToDo entry "Allow multiplayer game on multiple devices". Verify that the README renders and that the ports match `network.py`.

## 5. Running the game over the network

- [x] 5.1 Host side of a running game.
  - Give asteroids and shots a `net_id` when created, and record new explosions.
  - At the end of `update()`, build and queue a `snap` (rounded per design decision 4) for every client. Poll the session at the start of `update()`.
  - Apply `ctl` (thrust level, thrust, rotation) and `fire` to the ship of a slot only if that slot belongs to the sending peer, and keep the last `ctl` until a new one arrives.
  - In `game_start`, lay out remote players as non-touch players (row or corner, no overlay on the host), and allow a host with no local players. Send `start` with slots, colours, field and `elapsed` to every client when the joined game starts.
  - Test:
    - a `ctl` from the right peer turns and thrusts the ship, and one from another peer is ignored
    - `fire` spawns a shot with the shooter's slot
    - a snapshot contains every ship, asteroid and shot with consistent ids
    - a ship keeps thrusting after its client goes silent
    - a host game with two remote players and no local players starts
  - Verify with `pytest -k host_game`.
- [x] 5.2 Add `RemoteShip`, with the control surface of `Spaceship`; it sends `ctl` on change and `fire` on `shot()`. In a client game, each local slot gets a normal `ControlsManager` with a `RemoteShip`, so keyboard, gamepad (buttons, trigger, stick thrust) and touch all work, while every other slot gets a status block only. Test that a held turn key, a half-pulled bound trigger and a touch joystick push on the client produce the matching `ctl` messages and change the host ship. Verify with `pytest -k remote_ship`.
- [x] 5.3 Add `FieldView` and the client mirror world.
  - `FieldView` is a plain widget whose canvas translates and scales its children (scale `min(W/w, H/h)`, centred), with a field outline and `to_screen()`.
  - `snap` creates, moves and removes `Spaceship`, `Asteroid` and `Shot` widgets by slot or id. `boom` creates an `Explosion`. A change in a ship's thrust drives `thrust_on/off`. Lives and points go into the mirror ships, so `SpaceshipStatus` updates.
  - The client never calls `update()` on mirror widgets.
  - Test:
    - a host ship at x = w/4 is drawn at field-left + s·w/4 on a client window of a different aspect ratio
    - the whole field is inside the window
    - shots and asteroids appear and disappear by id, and sounds are triggered on creation
    - the client's lives and points match the host's after a hit
  - Verify with `pytest -k field_view`.
- [x] 5.4 Run a host and a client as two desktop instances on one PC (`SDL_AUDIODRIVER=dummy`; see the screenshot notes) and play a two-player game: keyboard on the host, a gamepad or keyboard on the client. Take screenshots of both windows mid-game at different window sizes and check that positions match, that the field outline is visible on the letterboxed side, and that controls feel responsive.

## 6. Joining and leaving during a game

- [x] 6.1 Factor the per-slot part of `game_start` into `add_player(slot, device)`.
  - The safe start point is the slot's start position, or the first point on rings around it (45° steps, 50 px apart) that is at least 200 px from every asteroid, with a fallback to the start position. Record the join time per slot, and compute `survived` from it.
  - In a network game, FIRE from an unjoined local host device, a client `act` `fire`, or a client `touch` *Tap to join* goes to `Lobby.join` and then `add_player`, followed by `lobby`. The host sends `denied: full` when no slot is free and `denied: out` for a device whose ship was destroyed.
  - Test:
    - a client gamepad joins a running two-player game as player 3 without changing the other ships' lives, points or positions
    - a host keyboard joins a game of two client players
    - with an asteroid at the start position, the ship appears at least 200 px away with 3 lives and 0 points
    - a fifth device gets `denied: full`
    - a destroyed player's gamepad gets `denied: out`
    - a player joining at 30 s and lost at 50 s has `survived == 20`
  - Verify with `pytest -k late_join`.
- [x] 6.2 Watching client and join prompt.
  - A client connecting in the `game` phase receives `start` with the current state, builds the mirror world and status blocks, and shows "Press FIRE to join · N slots free", plus *Tap to join* buttons at its free touch seats when it has touch. A `denied: full` shows "The game is full".
  - The prompt hides while the client holds a playing slot and returns when it has none. The same prompt is shown on the host for its unjoined local devices.
  - Slots appearing in or disappearing from a `snap` add or remove mirror ships and status blocks and, for the client's own slots, local controls; a lost player's block stays.
  - Test that a client connecting to a running game shows both ships with their lives and points and "2 slots free", that tapping *Tap to join* at the left seat gives a left-seat touch player, and that the prompt hides after joining.
  - Verify with `pytest -k watch`.
- [x] 6.3 Leaving during a game.
  - A client's `bye` or closed connection removes that peer's ships from the field with their results recorded and no last-loss game over while other ships remain. It frees their slots and sends `lobby`; the ships are gone from the next `snap`.
  - The host's *Main menu* sends `bye: host-ended`, and clients show "The host ended the game" and the menu. A closed host connection on a client shows "Connection to the host lost" and the menu.
  - Test:
    - in a three-player game, the client of player 3 leaves: players 1 and 2 play on, slot 3 is free, and another device can take it with a new ship
    - closing a client socket mid-game has the same effect
    - the leaver appears in the final results with their time and points at leaving
    - the host leaving shows the right message on the client
    - closing the host socket shows "Connection to the host lost"
  - Verify with `pytest -k net_leave`.

## 7. Pause, results and the shared leaderboard

- [x] 7.1 Pause.
  - A client's Back or Pause button shows its own pause screen and freezes its mirror at once, then sends `pause`; the host pauses and broadcasts.
  - *Continue* on any device sends or applies `resume`. On `resume` a client closes its pause screen and any open leave confirmation and clears held controls.
  - Test:
    - a client pause freezes the host world and shows the pause screen on both
    - *Continue* on the host resumes both
    - a key held through the pause does not keep a ship thrusting
    - with a host that never answers, the client's pause screen still opens and *Main menu* leaves
  - Verify with `pytest -k net_pause`.
- [x] 7.2 Results.
  - The host's `game_over` creates a `game` id and sends `over` with every player's result, leavers included. The client shows `ResultsScreen` in client mode, with "Waiting for the host" instead of *Play again*.
  - The host's *Play again* resets the `Lobby` slot states, restarts with the slots still held, and sends `start`; clients on their results screen follow. With fewer than two players left, the host reopens its hosting join screen with the remaining slots.
  - *Main menu* on the results screen closes the session as in 6.3.
  - Update the game-results tests for the new branch, and add tests for the scenarios in `specs/game-results/spec.md`, including survival time from joining.
  - Verify with `pytest -k "net_results or play_again or survival"`.
- [x] 7.3 Shared leaderboard.
  - After `welcome` the client sends `lb`. The host merges it and sends its merged `lb` to all clients, which merge it.
  - A client's *Save to leaderboard* sends `save` (game id, nickname). The host accepts the first save per game id, merges the entry, and broadcasts `lb` and `saved`. Every results screen then shows "Saved on <machine>" with the button disabled.
  - Test:
    - a phone's 30-point entry lands first in the host's leaderboard and stays after disconnect and reload
    - reconnecting adds no duplicates
    - a client save appears on host and all clients
    - simultaneous saves from host and client add exactly one entry everywhere
    - a single-player save sends nothing, because no session exists
  - Verify with `pytest -k shared_leaderboard`.
- [x] 7.4 Update `PRIVACY.md`: network games exchange game data and leaderboard entries (nicknames, points, times) only with devices on the same local network, and nothing is sent to the internet. Add a README note on the Android permissions and the Play Console data-safety answer. Verify that both files state it.

## 8. Integration

- [x] 8.1 Run the full suite (`.venv/bin/python -m pytest tests`) and `openspec validate lan-multiplayer --strict`. Both must pass, with the single-player and local multiplayer tests unchanged.
- [x] 8.2 Build the APK (`buildozer android debug`) and play network games between a phone and the Android TV (see the TV debugging notes), and between a phone and the desktop. Check that:
  - discovery finds the host within 2 s with the multicast lock held
  - the TV remote can host and join
  - a phone can join a running game and leave it while the others play on
  - a touch player on the phone has their controls only on the phone
  - pause behaves as specified
  - closing the app on the host ends the game on the client
  - the leaderboards of both devices match after a game
  - on a desktop with UDP 47401 and TCP 47400–47409 allowed in the firewall, the found-games list shows a host on the same Wi-Fi

  Note any jitter seen to decide the open question on interpolation.

  Result (2026-11-14): marked done on the user's word that most of these checks work on devices, possibly not all. Confirmed: the TV can host and join, and a phone can connect.

## 9. One multiplayer screen, one player per machine mid-game, field background

- [x] 9.1 Merge *Network game* into *Multiplayer*.
  - The menu goes back to five entries.
  - The join screen gets a line above the panels (`info` and the message) and a bottom row: *Back*, *Local network: Off / On* (`set_hosting`, keeping the join screen's `Lobby` and players) and *Join a network game*. A client's mirror join screen has only *Back*.
  - The bottom row is reached with Down by a device that has not joined; Left / Right, FIRE and Up as in design decision 15.
  - `NetworkScreen` loses *Host a game*; its *Back* returns to the join screen.
  - Test with keyboard arrows and a gamepad hat (toggle on without joining, Up and FIRE joins again), that the toggle keeps the joined players and, turned off, frees the client's slot and tells the client, that a host error is shown, and that the client's row has only *Back*. Verify with `pytest tests -k "bottom_row or host_toggle or network_screen or client_join_screen"`.
- [x] 9.2 During a running network game, refuse a join (`denied: out`) from any machine that already holds a slot, playing or out, the host included, and show the join prompt only on machines that hold none. Test that a client with a player and the host with a player cannot add one, that a destroyed client player cannot rejoin while a watcher still can, and that late joins from watchers work as before. Verify with `pytest tests -k late_join`.
- [x] 9.3 Give `FieldView` its own `Nebula` (the picture stretched over the widget, also used for the full-screen background instead of the kv `Background`) and debris sized to the field, hide and pause the game's full-screen background during a client game and restore it afterwards, and let `background_widget()` return the field's debris. Test the sizes, the hidden and restored screen background, and that the host's background is untouched; check a screenshot of a 4:3 client of a 16:9 host (black bars above and below). Verify with `pytest tests -k field_view`.
- [x] 9.4 Update the README: one *Multiplayer* entry with the *Local network* toggle and *Join a network game*, the bottom row by keyboard, gamepad and remote, one player per machine during a running game, and the field background on clients. Verify that it no longer mentions a *Network game* menu entry or *Host a game*.

- [x] 9.5 Offer *Save to leaderboard* in a network game only on the top player's device: record each result's `machine`, send `saver` in `over` (-1 when that machine has left), leave the button out on the other devices (they say "Score saved on <machine>" once saved), and let the host accept saves only from `saver`. Test the top player's client saving for everybody, the host's and a watcher's screens without the button, a save from another client being ignored, and a top player who left. Verify with `pytest tests -k shared_leaderboard`.
- [x] 9.6 Tile the scrolling debris at its own 640 x 480 px instead of stretching it (scrolling moves the rectangle's own texture coordinates, not the shared texture's `uvpos`); the nebula stays stretched. Test the repeat counts, the scroll shift and two independent debris layers; check a 1600 x 720 menu screenshot. Verify with `pytest tests -k debris`.
- [x] 9.7 Add a *Device name* box to the join screen's bottom row (between *Back* and *Local network*; reachable with Down/Right and FIRE, which focuses it). Empty uses the model or host name, shown as the hint. Save it as `device_name` in `network.json`, use it when hosting starts or a client connects, disable it while hosting, and ignore game keys while it has focus (Escape leaves it). Test the default, a typed name for hosting and joining, persistence, the bottom row and typing. Verify with `pytest tests -k device_name`.

## Workflow follow-up

- [x] Bump `__version__` to 0.6.0 and add a README history entry.
- Update the Play Console data-safety form for the new network permissions and the shared nicknames before publishing.
- Archive the change after review so the delta specs merge into `openspec/specs/`.
