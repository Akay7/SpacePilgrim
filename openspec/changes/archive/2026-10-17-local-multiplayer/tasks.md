# Tasks

## 1. Player-aware key bindings

- [x] 1.1 Make `KeyBindings` two-player (defaults P1 W/A/D/Space, P2 I/J/L/K; `action_for` returns player and action; rebind/reset per player; cross-player conflict check) and verify with unit tests for defaults, conflict across players, reserved keys and reset
- [x] 1.2 Persist as file version 3 and migrate version 2 files (old set becomes player 1); verify with tests for round-trip, v2 migration, corrupt and unwritable path
- [x] 1.3 Add a player switch to the keyboard layout settings page (kv + `KeyboardSettings`) listing and rebinding the chosen player's keys; verify with tests that open the page, switch to player 2, rebind and see P1 unchanged
- [x] 1.4 Update the README keyboard/controls section for the second player keys and verify the text matches the defaults in code

## 2. Two ships and input routing

- [x] 2.1 Make `game_start` take a player count and create a `Spaceship` and `ControlsManager` per player at different start positions; keep `spaceship_controls` as the player 1 alias; verify with a test that a two-player start has two ships and single-player behaviour is unchanged
- [x] 2.2 Route keyboard input to the player resolved by `KeyBindings.action_for`, keeping arrow keys for player 1 only and menus untouched; verify with tests that both sets drive their own ship at the same time and the second set is ignored in single player
- [x] 2.3 Assign gamepads to players by first meaningful input (first -> P1, second -> P2, one pad -> P1, every pad -> P1 in single player; any pad navigates menus); verify with tests simulating `on_joy_*` from two stick ids
- [x] 2.4 Per-ship game end: remove a ship at 0 lives and end the game only when no ship is left; verify with tests for one ship out / both out and scoring by shooter
- [x] 2.5 Per-player HUD tinted with the cabin colour (left/right); verify with a test that two status widgets exist in multiplayer and one in single player

## 3. Touch controls for two players

- [x] 3.1 Add a per-player `ScreenButtonsLayout` on the left/right side (left: joystick at the top, FIRE in the bottom corner; right: FIRE at the top, joystick in the bottom corner) with size clamping and the existing visibility/size settings applied to both; verify with tests that the two sets do not overlap, stay on screen and keep margins at 100 % and 400 % scale
- [x] 3.2 Route each overlay's press/release to its own player's `ControlsManager`; verify with a test where player 1 holds the stick left while player 2 presses FIRE
- [x] 3.3 Check by eye on desktop (mouse/touch emulation) at a phone-landscape and a 1080p size that both sets fit and do not hide the HUD, and tune sizes if needed

## 4. Cabin colours and ship selection

- [x] 4.1 Implement the cabin recolouring (six colours, textures cached for stopped and flying sprites) and a `cabin` property on `Spaceship` used by the kv rule; verify with a test that only cabin pixels change and each colour differs, and by eye on a contact sheet of all colours
- [x] 4.2 Add colour persistence (`ship_colors.json`, defaults blue/green, defensive load/save); verify with tests for round-trip, corrupt file and unique colours
- [x] 4.3 Build the ship selection screen (preview per player, next/previous colour skipping the other player's colour, ready/confirm, Back) shown after "Single player" and "Multiplayer", operable by touch, keyboard sets and gamepads; verify with tests for preview change, skip taken colour, per-player keys and Back returning to the menu
- [x] 4.4 Enable the "Multiplayer" button in the menu and wire both entries to the selection screen and `game_start(players=N)`; verify with a test that Multiplayer starts a two-ship game with the chosen colours

## 6. Join screen and up to four players

Sections 1–4 built the first two-player iteration with a fixed device order; the tasks below rework it to joining and four slots (see design decisions 1–5).

- [x] 6.1 Treat the two keyboard sets as devices: `lookup` returns `(set, action)` with arrows/Enter as set 1, and the keyboard page switch reads "Keys of: Set 1 / Set 2"; verify with the existing bindings tests adapted to set wording and a test for the relabelled switch
- [x] 6.2 Extend `ShipColors` to four slots (defaults blue/green/red/yellow, two-entry file kept, unique colours among joined slots, saved colour or first free on join); verify with tests for round-trip, two-entry migration, corrupt file and joining with a taken colour
- [x] 6.3 Replace the multiplayer selection with the join screen: four slots, join by FIRE (keyboard set / pad, first free slot) or "Tap to join by touch" (that slot, offered while fewer than two touch players joined; takes the free side, left first), device label with the touch side and input highlight, colour/ready/leave per device, Escape or an unjoined pad's Back to the menu, start with at least two joined and all ready; single player keeps its one-panel screen; verify with tests for joining in order, touch slot choice and side, the two-touch limit, a device joining once, simultaneous setup, each way to leave, the two-player minimum and Escape
- [x] 6.4 Route game input by device -> slot (`game_start` with the joined slots; set/pad/touch drive only their slot; unjoined devices ignored except Back; single player unchanged); verify with tests for swapped keyboard sets, an unjoined set, two pads, a joined pad's Back ending the game, a four-player start (four ships, no overlap) and single-player routing
- [x] 6.5 HUD for up to four players: touch players' blocks in the middle of their side turned −90/90, keyboard and gamepad players' blocks upright along the top in player order; verify with a test for a mixed game (two touch, one keyboard, one pad) checking positions, angles and colours
- [x] 6.6 Touch overlays only for touch players, on the side they joined, always shown in game whatever the touch setting; verify with tests that a non-touch player has no overlay, that a keyboard press by another player does not hide a touch player's controls, and that the two sides keep the existing layout checks
- [x] 6.7 Update the README for joining/leaving, the two-keyboard and two-touch limits, gamepads for players 3–4 and the HUD, and verify it matches the code
- [x] 6.8 Move joining by touch to two side strips at the left and right edges of the join screen (labels turned toward the seat; a strip takes the first free slot as a touch player on its side; disabled and naming the player while its side is taken); remove the per-slot touch button; verify with tests for joining from each side, a taken side, leaving freeing the side, and keys still joining
- [x] 6.9 Turn a touch player's joystick toward their seat (`Joystick.angle` −90 / 90 from the side; thrust away from the player, turn to their left / right; marks turned); single player unchanged; verify with tests for forward and both turns on each side and the single-player stick, and update the README

## 5. Integration

- [x] 5.1 Update the README (multiplayer mode, per-player keyboard sets, gamepad assignment, two-player touch layout, ship colours) and verify the controls table and notes match the behaviour
- [ ] 5.2 Run the full test suite (`pytest tests`) and verify it passes; play a two-player game on desktop with keyboard + gamepad and check touch with two fingers on a device if available
