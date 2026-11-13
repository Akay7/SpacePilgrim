# Design

## Context

See proposal.md for motivation and `specs/lan-multiplayer/spec.md` for the behaviour. Current state, as observed in `main.py` (3447 lines) and `spacepilgrim.kv`:

- **One widget is the whole game.** `SpacePilgrimGame` owns the world lists (`spaceships`, `asteroids`, `shots`, `explosions`) and every screen (menu, join, pause, results). `update(dt)` runs at 60 Hz from `Clock` and moves everything.
- **Physics is in window pixels, per frame.** For example, a ship flies at `speed = 3 * thrust_level` px/frame. Ships, asteroids and shots wrap at `Window.size`, and `generate_asteroid` uses `randint` over `Window.size`. The simulation is therefore not deterministic across devices with different window sizes.
- **Input is already abstract.** Keyboard, gamepad (buttons, triggers, stick thrust) and touch all end in `_input(source, action, pressed, device)` or `ControlsManager.set_thrust`. A device is a tuple: `('keys', set)`, `('pad', stick)` or `('touch', seat)`. In a game, `_controls_of(device)` maps it to the slot's `ControlsManager`. That manager drives one `Spaceship` only through `thrust_on/off`, `thrust_level`, `thrust`, `turn_left/right`, `stop_rotation` and `shot`.
- **The join screen owns the slot table.** `JoinScreen` keeps `slots[4]` (device or `None`), `ready[4]` and colours (`ShipColors`). Every device action goes through `handle(device, action)`. `game_start(players, colors, slots)` builds one ship, status block and `ControlsManager` per filled slot. The slot table only exists while the join screen is open, and players are fixed once a game starts.
- **The leaderboard is local only.** `Leaderboard` stores `{name, points, seconds}` entries (top 10) and `last_name` in `leaderboard.json` (`VERSION = 1`). Entries have no identity, so two equal scores cannot be told apart.
- **Packaging.** Buildozer packages every `*.py` in the project root (`source.include_exts`), and `android.permissions` is unset. `declare_java_classes()` is the existing pattern for cheap `jnius` access on slow TVs.
- **Tests.** Tests run headless (`KIVY_GL_BACKEND=mock`, dummy audio), drive `SpacePilgrimGame` directly, and fake gamepads and screen size through fixtures in `tests/conftest.py`.

## Goals / Non-Goals

**Goals:**
- Reuse the existing input pipeline, `ControlsManager`, `JoinScreen`, the status blocks and the screens. The network adds remote devices and a remote ship. It does not add a second copy of the input code.
- Keep single player and same-screen multiplayer exactly as they are. The host's simulation is the current code path.
- Let players join and leave during a network game.
- Use only the standard library, and run everything on Kivy's main thread.
- Make the protocol testable in one process over localhost.

**Non-Goals:**
- Play over the internet, NAT traversal, relay servers or accounts.
- Encryption or authentication. Trust is the local network.
- Client-side prediction or lag compensation.
- Host migration: the game ends when the host leaves.
- Detecting dead devices by silence: no heartbeats and no idle timeouts.
- Joining or leaving during a same-screen (non-network) game.
- Rejoining after one's own ship was destroyed in the same game.
- Making the physics resolution-independent. The host's window defines the field.

## Decisions

1. **The host runs the game; clients send input and draw snapshots.**
   - The host runs the unchanged simulation in its own window and sends the world state to each client every frame. A client never simulates: it forwards its players' control state and draws what the host sends.
   - Alternative: deterministic lockstep, where each device simulates and only input is exchanged. Rejected: the physics depends on `Window.size`, float pixel maths, `random` and `Clock` frame timing. Lockstep would also make joining during a game much harder, because a new device would need the full simulation state in sync.
   - Alternative: peer-to-peer. Rejected: with four players at most, a star around one host is simpler, and there is one source of truth for collisions, points and slots.

2. **TCP per client for game traffic, UDP broadcast only for discovery.**
   - Each client holds one TCP connection to the host, with `TCP_NODELAY`. On a LAN the round trip is a few milliseconds. Reliable, ordered delivery removes sequence and retransmit logic for lobby, pause, results and leaderboard messages. TCP also tells either side when the other closes the connection: the app quits, the session ends, or the OS resets the socket. That is the only leave signal the spec allows.
   - Discovery: from "Host a game" until the host leaves the network game (join screen, running game and results), the host sends a small JSON datagram to `255.255.255.255:47401` once a second, for example `{"game": "spacepilgrim", "proto": 1, "name": "Pixel 8", "port": 47400, "players": 2, "playing": true}`. The network screen listens on UDP `47401` with `SO_REUSEADDR`, and `SO_REUSEPORT` where it exists, so two instances on one PC can test. The host's IP is the datagram's source address. The browser drops a host after 3 s without an announcement. This affects only the list of found games, never a connection.
   - The game port is TCP `47400`. If it is taken, the host tries the next 9 ports and announces the one it got. The manual address defaults to `47400`.
   - Alternative: UDP for snapshots. Rejected for the first version because it is more code (sequencing, a reliable channel for everything else) for little gain on a LAN. The snapshot backpressure rule (decision 4) avoids the main TCP drawback, a growing backlog.
   - Alternative: mDNS / Zeroconf. Rejected because it needs a dependency (or a hand-written mDNS stack) and Android NSD through `jnius`.

3. **No threads: non-blocking sockets polled from the Kivy clock.**
   - A `NetSession` (host or client) owns non-blocking sockets and a `selectors.DefaultSelector`. `poll()` accepts connections, reads into per-connection buffers, splits complete messages, dispatches them to the game, flushes outboxes and reports closed connections (EOF, `ECONNRESET` and other socket errors).
   - In a game, the host polls at the start and end of `update()`, so snapshots go out right after the frame. Elsewhere (network screen, join screen, pause, results), one `Clock.schedule_interval(poll, 1/30)` runs while a session or listener exists, and it is cancelled when they close.
   - Alternative: a network thread with queues, or `asyncio`. Rejected: Kivy widgets must be touched on the main thread, so every message would be queued back anyway.

4. **Wire format: newline-delimited JSON, with snapshots that are dropped when a client falls behind.**
   - Each message is one UTF-8 JSON object per line: `{"t": "<type>", ...}`. A line over 64 KiB, invalid JSON, a missing or unknown `t`, or a field of the wrong type closes that connection (spec: robust against bad data). Lists arriving where the game uses tuples, such as devices, are converted back and validated against the known kinds. Invalid leaderboard entries inside an otherwise valid message are skipped.
   - Each connection has a reliable outbox (all message types except snapshots) and a single *latest snapshot* slot. The host writes the snapshot only when the reliable outbox has drained and the socket is writable. A slow Wi-Fi client therefore skips frames instead of falling further behind. If a client stops reading altogether, it just stops getting snapshots; its outbox is capped at 1 MiB, and going over closes the connection, which counts as leaving.
   - Message types (`NET_PROTOCOL = 1`):

     | Direction | `t` | Content |
     |---|---|---|
     | C→H | `hello` | `proto`, device `name` |
     | H→C | `welcome` / `refuse` | `peer` id, `phase` (`lobby`, `game`, `results`) / `reason`: `version`, `full` |
     | H→C | `lobby` | slots as `[peer, device, state, machine name]` or null (state: `joined`, `ready`, `playing`, `out`), `colors`, `flash`, host name, `free` count, `phase` (`lobby`, `game`, `results`) |
     | C→H | `act` | `device`, `action`: an action of a client device that has not joined or holds a slot (join screen, or join during a game) |
     | C→H | `touch` | `side`: tapped join strip or *Tap to join*; `slot`, `button`: a panel button (`<`, `>`, Ready, Leave) |
     | H→C | `start` | `slots`, `colors`, `field` `[w, h]`, `elapsed`: a new game, or the running game for a client that connects during it |
     | H→C | `denied` | `device`, `reason` (`full`, `out`): a join during the game was refused |
     | C→H | `ctl` | `slot`, `thrust` (0..1), `turn` (-1/0/1), sent on change |
     | C→H | `fire` | `slot` |
     | H→C | `snap` | `field`, `elapsed`, `ships` `[[slot, x, y, angle, thrust, lives, points]]`, `ast` `[[id, x, y, angle]]`, `shots` `[[id, x, y]]`, `boom` `[[x, y]]` (new since last snap) |
     | both | `pause` / `resume` | a request from a client, an order from the host |
     | H→C | `over` | `game` id, `results` `[[slot, color, points, survived]]` |
     | both | `lb` | `entries` `[[id, name, points, seconds]]` |
     | C→H | `save` | `game` id, `name` |
     | H→C | `saved` | `game` id, `by` (machine name) |
     | both | `bye` | `reason` (`menu`, `host-ended`) |

   - There is no `ping`, because the protocol never relies on silence (decision 9).
   - There are no separate messages for players joining or leaving during a game. Clients work them out from `lobby`, which the host sends after every change, and from the slots in each `snap` (decision 8).
   - Coordinates are rounded to 0.1 px and angles to 0.1°. A full four-ship snapshot with about 8 asteroids and 40 shots is about 2–3 KB, which is roughly 150 KB/s per client at 60 Hz. That is fine on Wi-Fi.
   - The host gives asteroids and shots a stable `net_id` from a counter when they are created. Clients diff the id sets to create and remove their mirror widgets.

5. **A `Lobby` model owns the slots for the whole network session. Remote devices are `('net', peer, device)`.**
   - The slot table (`slots`, per-slot state `joined` / `ready` / `playing` / `out`, colours) moves out of `JoinScreen` into a small `Lobby` class. `JoinScreen` becomes a view and controller of a `Lobby`. A local multiplayer join screen creates its own `Lobby` and behaves exactly as now. A network host keeps one `Lobby` from "Host a game" until it leaves, so the slots survive the join screen, the game and the results screen. This is what allows joining and leaving during a game. Alternative: keep `JoinScreen.slots` and copy them into the game. Rejected, because the game would then need its own copy of the join rules (first free slot, one slot per device, colour claim).
   - On the host, a client device becomes the tuple `('net', peer_id, ('pad', 0))` and is stored in the `Lobby` like a local device. A client `act` message calls the same `handle(('net', peer, device), action)` path as a local device. A `touch` message calls the touch join, or the panel method for a slot that peer holds. The existing rules (first free slot, one slot per device, colours, ready, two players to start the first game) therefore apply to remote devices for free. Keyboard set 1 on two machines are different devices.
   - `device_kind` and the labels look through the `'net'` wrapper. `device_label` appends ` · <machine name>`, or ` · this device` when shown on that machine. In a network game a keyboard set is named "Keys set N" rather than by its keys, in a 13 dp font, so the machine name fits on the panel: another machine's keys may be bound differently, and the hint under the panel still lists this machine's keys. After every `Lobby` change the host sends `lobby` to all clients.
   - The panel buttons (`<`, `>`, Ready, Leave) of a slot held by another machine are disabled on every screen, so only a player's own machine changes that slot.
   - A client keeps a `JoinScreen` in *mirror* mode. Its `handle`, `join_touch` and panel buttons send `act` or `touch` instead of changing state, and `refresh()` draws the last `lobby`. Touch seats stay per machine: the strips and seats are the client's own (`touch_seats()`). On the host, a remote touch player is laid out as a non-touch player, a status block in the row or corner.

6. **Joining and leaving during a game.**
   - **Join:** in a network game on the host, `_input` sends FIRE from a local device that has not joined to `Lobby.join` instead of dropping it. A client sends `act` with `fire` for its unjoined devices, or `touch` for *Tap to join*. A successful join calls a new `add_player(slot, device)`, which is the per-slot part of `game_start` factored out: ship, status block and `ControlsManager`. The host then sends `lobby`; the new ship reaches the clients in the next `snap`. When no slot is free, or the device's own ship is `out`, the host sends `denied`, and the device shows "The game is full" or ignores it.
   - **Safe start point:** `add_player` tries the slot's start position (`START_OFFSETS`) and then points on growing rings around it, every 45° and 50 px apart. It picks the first point at least 200 px from every asteroid, which is the same distance `generate_asteroid` keeps from ships. If none is found within the field, it falls back to the start position.
   - **Survival time:** `PlayerResult.survived` is `elapsed` at loss minus `elapsed` at join; the join time is recorded per slot.
   - **Leave:** when a client's connection closes or it sends `bye`, the host removes that peer's ships with a variant of `lose_spaceship` that records the result. The variant does not count as the last loss while other ships remain, and it plays no explosion. The host frees the peer's slots in the `Lobby` and sends `lobby`; the ships are gone from the next `snap`. A freed slot can then be joined like any free slot. A slot whose ship was destroyed stays `out` until the game ends, and its device is refused with `denied: out`.
   - **Watching client:** a client that connects during a game receives `start` with the current slots and `elapsed`, builds the mirror world and the status blocks, and shows a join prompt: "Press FIRE to join · N slots free", plus *Tap to join* buttons at its free touch seats if it has touch. The prompt hides while the client holds a playing slot and comes back if all its slots end.
   - The host's own local devices get the same prompt and behaviour on the host screen.

7. **Client input goes through the existing `ControlsManager` into a `RemoteShip` proxy.**
   - In a client game, each local player's slot gets a normal `ControlsManager` (touch overlay, seats, Pause button and all). Its `spaceship` is a `RemoteShip`. That object has the same control surface (`thrust`, `thrust_level`, `thrust_on/off`, `turn_left/right`, `stop_rotation`, `shot`), records the intended state and sends `ctl` when it changes, or `fire` on `shot()`. On the host, a `ctl` message sets the real ship's thrust level, thrust and rotation for that slot, if the slot belongs to the sending peer. A ship keeps the last `ctl` it got, so a silent client's ship flies on with its last input.
   - All existing input, including keyboard bindings, gamepad remaps, triggers, stick thrust and the rotated touch joystick, therefore works for remote players with no change.
   - Alternative: send raw device events to the host. Rejected because the host would need the client's key bindings, gamepad profiles, seat angles and touch scale.

8. **The client draws a mirror world in a scaled field view.**
   - A client game builds a `FieldView`: a plain widget whose canvas translates and scales its children (`PushMatrix`, `Translate`, `Scale` before them, `PopMatrix` after). Its scale is `s = min(W/w, H/h)` for client window `W×H` and host field `w×h`, and it is centred; `to_screen(x, y)` gives the window position of a field point. A faint outline marks the field edges. The `AnimatedBackground` stays full-screen behind it. Alternative: a `Scatter` with user transforms disabled. Rejected because a plain widget never takes touches meant for the touch controls, and needs no touch-transform bookkeeping.
   - Inside the view the client creates ordinary `Spaceship`, `Asteroid`, `Shot` and `Explosion` widgets and never calls their `update()`. Each `snap` sets positions and angles, creates or removes ships, asteroids and shots by slot or id, and creates an `Explosion` for each `boom` entry. Creating a `Shot` or `Explosion` plays its sound, as on the host. A change in a ship's `thrust` calls `thrust_on/off`, so the shared engine sound follows. Lives and points go into the mirror ships, so the existing `SpaceshipStatus` blocks bind to them unchanged.
   - Joins and leaves come from the snapshots and the lobby. A slot that appears in a `snap` creates its mirror ship and status block through `add_player`, and controls with a `RemoteShip` when the slot is held by one of this machine's devices. A client's own player therefore gets controls with the first snapshot that shows their ship. A slot that disappears from the `snap` removes the mirror ship and the controls. Its status block stays, with no lives, when the lobby marks the slot `out`, and is removed when the player left. A slot whose device changed in the lobby (a freed slot taken by someone else) starts over with a new mirror ship.
   - Status blocks and touch controls stay in screen coordinates, outside the view. On a client, the client's own touch players get their seat, and every other player is placed as a non-touch player (row or corner), using the same placement code as `game_start`.
   - The client shows the latest snapshot without interpolation. Interpolation between the last two snapshots is a possible follow-up if Wi-Fi jitter shows (see Risks).

9. **Session lifetime: closed connections only, no silence timeouts.**
   - Neither side sends keep-alives or measures silence. A connection ends only on `bye`, EOF or a socket error, a protocol violation (decision 4), or the outbox cap. The host treats every one of these as the client leaving (decision 6). A client treats a closed host connection as "Connection to the host lost", and `bye: host-ended` as "The host ended the game".
   - A silent client keeps its slots. Its ship keeps its last input until the asteroids destroy it. A silent host leaves its clients on a frozen field. They can still pause locally (decision 10) and leave through *Main menu*.
   - The one remaining time limit is setting up a connection: a non-blocking connect that has not finished after 5 s fails with "Could not reach the host". Without it, a typed wrong address would wait for the OS limit, which can be minutes.
   - The host refuses with `full` when eight clients are connected, and with `version` on a protocol mismatch. A client may connect in any phase: lobby, game or results.
   - The host session lives from "Host a game" until the host goes to the main menu (from the join screen, the pause screen or the results screen). The client session lives from connecting until it leaves or the connection closes.

10. **Pause and results go through the host.**
    - A client's Back (or Pause button) shows its own `PauseScreen` and freezes its mirror at once, then sends `pause`. The host runs its normal `pause()` and broadcasts. A client's *Continue* sends `resume`. A client receiving `resume` closes its pause screen and any open leave confirmation, and clears held controls as `pause()` already does. If the host ignores a client's pause, for example because it is silent, the client stays on its own pause screen, from which *Main menu* still works offline.
    - A client's *Main menu* (after `ConfirmScreen`) sends `bye`, closes the session and shows the menu. The host's *Main menu* sends `bye: host-ended` to all clients and closes the session.
    - On the host, `game_over()` gives the game a random `game` id and sends `over` with the results of every player, leavers included, before showing its `ResultsScreen`. A client shows `ResultsScreen(results, network='client')`, where the *Play again* button becomes a disabled "Waiting for the host" label. The host's *Play again* resets the `Lobby` (`out` and `playing` back to `playing`, empty slots skipped) and calls `game_start` with the slots still held, then sends `start`. With fewer than two players it reopens the hosting join screen with the remaining slots. Its `lobby` then has `phase: lobby`, which moves clients still on their results screen to the mirror join screen.

11. **Shared leaderboard: entry ids, union merge, one save per game.**
    - `Leaderboard` file `VERSION = 2`: each entry gets `id`, 16 random hex characters from `uuid4`. When a version 1 file is loaded, its entries get new ids and the file is rewritten on the next save. Order and content are unchanged (spec: older leaderboard file). `merge(entries)` adds the entries whose id is not yet present, validates name, points and seconds as `load()` does, sorts, keeps the top 10, saves, and returns whether anything changed. `last_name` stays per device and is never shared.
    - Exchange: after `welcome`, the client sends `lb` with its entries. The host merges them and sends `lb` with its merged list to every client. Each client merges what it receives. All connected devices then hold the same top 10, and later exchanges change nothing because ids are already present.
    - Save in a network game: *Save to leaderboard* on a client sends `save` (`game` id, nickname). On the host it is handled locally. The host accepts only the first save for a `game` id: it builds the entry for the top result, merges it, and broadcasts `lb` and `saved` (`by`: the machine name). Every results screen then shows "Saved on <machine>", and the button is disabled. A second save for the same game is ignored, which covers two devices saving at once. A client whose save is ignored still gets `saved`.
    - Alternative: a live combined view only while connected. Rejected in favour of keeping the entries, as the user chose.

12. **Network code in a new module `network.py`; UI glue in `main.py`.**
    - `network.py` holds only the standard library: framing and validation, `Connection`, `HostSession`, `ClientSession`, `Announcer`, `Browser`, `local_address()` and port selection. Kivy is not imported there, so the protocol can be unit-tested in isolation. `main.py` adds `Lobby`, `NetworkScreen`, `AddressScreen`, the mirror mode of `JoinScreen`, `RemoteShip`, `FieldView`, `add_player`, the join prompt, and the network branches in `game_start`, `pause`, `resume`, `game_over`, `play_again` and `Leaderboard`.
    - `local_address()` uses the UDP-connect trick: it connects a UDP socket to a private address, which sends nothing, and reads `getsockname()`. It falls back to `gethostbyname(gethostname())`. The device name is `android.os.Build.MODEL` on Android (a declared `jnius` class) and `socket.gethostname()` elsewhere.

13. **Android specifics.**
    - `buildozer.spec`: `android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, CHANGE_WIFI_MULTICAST_STATE`.
    - While the network screen is open, the client acquires a `WifiManager.MulticastLock`, declared in `declare_java_classes()` like the other Java classes. It releases the lock when the screen closes. Many Android Wi-Fi drivers drop incoming broadcasts without the lock. The host does not need it, because it only sends broadcasts.
    - `on_pause` on Android suspends Python without closing sockets. A backgrounded client is therefore silent: its ship flies on with its last input, and it is dropped only if Android kills the app. A backgrounded host freezes its clients' fields until it returns.

14. **Address entry.** `AddressScreen` reuses the `NameScreen` layout (a `TextInput` with *Join* and *Back*). It is prefilled with the last address used, or with the first three octets of the device's own address (`192.168.1.`), so usually only the last number needs typing. The last address is saved in `network.json` in the user data directory. Parsing accepts `a.b.c.d` or `a.b.c.d:port` and also hostnames. Errors are shown on the network screen.

## Risks / Trade-offs

- [Wi-Fi jitter or packet loss makes remote ships stutter, because TCP head-of-line blocking delays snapshots] → `TCP_NODELAY`, snapshots dropped rather than queued (decision 4). If it is still visible on real devices, add interpolation between the last two snapshots on the client as a follow-up.
- [Input latency for client players is about one round trip plus up to one frame] → On a LAN this is under about 30 ms, which is acceptable at this game's pace. Host players have no added latency, which is a known asymmetry.
- [Without timeouts, a client that drops off Wi-Fi without the OS noticing keeps its slot. Its ship flies on until the asteroids destroy it, and the slot stays `out` until the game ends] → This is the intended behaviour. The slot is freed only when the connection closes: the client returns and leaves, the app is killed, or the OS resets the socket. Until then, *Play again* keeps the silent player too, and their new ship again flies on until it is destroyed. The host can always start a fresh lobby from the main menu.
- [Without timeouts, a silent host leaves clients on a frozen field] → The client's pause screen opens at once without the host, and *Main menu* there leaves (decision 10).
- [A player joining mid-game can spawn into trouble] → The 200 px safe start point. Ships do not collide with each other, so placing it next to another ship is fine.
- [A desktop firewall drops the UDP announcements] → Seen in the two-instance desktop run: the announcements never reached the listener on UDP 47401, while direct UDP to the machine's own address did, most likely because the firewall on the development PC drops them (not confirmed). The client found nothing and joined by typed address. The README names the ports to open, and the manual address always works.
- [Guest or corporate Wi-Fi with client isolation, or networks that block broadcast] → Discovery fails, so the manual address is offered. With full client isolation, nothing works. The network screen's empty-list text says the devices must be on the same Wi-Fi.
- [Desktop firewalls block incoming connections to the host (firewalld, the Windows Defender prompt)] → The README explains how to allow TCP 47400–47409 and UDP 47401. The client error message mentions the firewall.
- [Different screen shapes waste space on a client (letterbox)] → Accepted, and the field outline makes the wrap edges clear.
- [A host on a small phone gives a small field, which a big client screen shows scaled up] → Accepted. Hosting on the biggest screen is the natural use (a TV as the shared display).
- [A peer on the LAN can push made-up leaderboard entries] → Entries are validated (types, non-negative values, a 12-character name), and only the top 10 are kept. This is accepted as the cost of sharing with trusted friends' devices. A future option could add a "Clear leaderboard" action.
- [Nicknames now leave the device] → They go only to devices of a network game the player joined. `PRIVACY.md`, the README and the Play data-safety answers say so.
- [`main.py` keeps growing] → The new socket and protocol code goes into `network.py`, and only the UI glue and `Lobby` are added to `main.py`.
- [Remote input from a hostile LAN peer] → Messages are validated, a client can only drive slots its peer holds, the client count is capped, and malformed data drops the connection. No file system or settings are reachable through the protocol, except leaderboard entries, which are validated.
- [Adding the `INTERNET` permission changes the Play listing] → Update the data-safety form and `PRIVACY.md` in the same release.

## Migration Plan

- `leaderboard.json` moves from version 1 to version 2 (entry ids), migrated in place on load. It stays readable as before, and nothing is dropped. An older app version reading a version 2 file ignores the extra `id` field, because `load()` only reads `name`, `points` and `seconds`.
- `network.json` is new and optional.
- Release as a new minor version (`__version__` 0.6.0) with `NET_PROTOCOL = 1`. Later protocol changes bump `NET_PROTOCOL`, and the version check keeps mixed installs from connecting.
- Rollback: if the feature misbehaves, removing the *Network game* menu entry disables it without affecting anything else. Leaderboard ids are harmless without it.

## Open Questions

- Whether snapshot interpolation is needed is to be decided after trying it on a phone and a TV on real Wi-Fi. It does not change the protocol.
- The exact port numbers (47400/47401) can change before release if they clash with something common on home networks.
