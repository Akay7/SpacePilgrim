# Design

## Context

See proposal.md for motivation. Current state (observed in `main.py` / `spacepilgrim.kv`, including the uncommitted `improve-touch-controls` work this builds on and the first two-player iteration of this change):

- `SpacePilgrimGame.spaceships` is a list; `update`, `generate_asteroid` and collision code loop over it. `game_start(players, colors)` creates a `Spaceship`, `SpaceshipStatus` and `ControlsManager` per player; a ship at 0 lives leaves and the game ends when none is left.
- `ControlsManager` turns abstract actions (`up`, `left`, `right`, `fire`) into commands of **one** ship. Keyboard (`KeyBindings.lookup`), gamepad (`_on_joy_*`) and the touch overlay (`ScreenButtonsLayout` with `Joystick` + `FireButton`) all call `_input(source, action, pressed, player)` / `ControlsManager.press/release`.
- The first iteration tied inputs to players by a fixed rule: keyboard set *n* is player *n*, gamepads go to players in the order of their first input, both touch sets are always shown. On the selection screen the same rule decides which panel a key moves, so a player cannot see or choose which device drives which ship. This design replaces that rule with joining.
- `KeyBindings` holds `keys[set][action] -> [scancodes]` for two sets (JSON `version: 3`); reserved keys (arrows, Enter, Esc) drive menus.
- `Spaceship` is drawn from `images/ship_stop.png` / `ship_fly.png` (91x90 pixel art); the cabin is a blue canopy near the nose.

## Goals / Non-Goals

**Goals:**
- Two to four ships controllable at the same time from any mix of keyboard sets, gamepads and touch, without touching the single-player feel.
- Every player can see which device drives which ship before the game starts, and several players can set up at the same time.
- Reuse the existing action model and widgets; no new image assets.

**Non-Goals:**
- More than four players, ship-vs-ship damage, networked play, controller hot-plug UI.

## Decisions

1. **Players are slots 0–3 that a device joins; the game routes `device -> slot`.**
   - A *device* is a keyboard set (`('keys', n)`), a gamepad (`('pad', stick_id)`) or touch (`('touch', slot)`). The join screen keeps `slots = [device or None] * 4`; the game keeps the same list and a reverse map `device -> slot`.
   - `game_start(slots, colors)` creates a `Spaceship`, a `SpaceshipStatus` and a `ControlsManager` for every filled slot; `self.controls[slot]` is `None` for empty or finished slots. `game_start(1)` / `spaceship_controls` stay for single player and existing tests.
   - Input handlers resolve the raw event to a device, the device to a slot and call `controls[slot].press/release(action)`. Input of a device that did not join is ignored in game, except Back.
   - Alternative kept from the first iteration: fixed device order (set *n* = player *n*, pads by first input). Rejected: on a shared screen nobody can tell which input drives which ship, and a player cannot pick their device.

2. **Join screen (Multiplayer).**
   - Four panels in a row, one per slot, titled "Player N". An empty panel says "Press FIRE on a keyboard set or gamepad". Two tall "Tap to join by touch" strips sit at the left and right edges of the join screen, their labels turned toward that seat (−90° / 90°), so a touch player sees where they will sit before joining.
   - FIRE from a keyboard set or a gamepad that has not joined takes the **first free slot**; a side strip also takes the **first free slot**, as a touch player on that side. A keyboard set or pad can hold one slot only; each side strip one slot, so touch holds at most two slots; a taken side's strip is disabled and names the player on it. With two keyboard sets this also limits the keyboard to two players.
   - A joined panel shows the device ("Keys W A D ␣", "Gamepad 2", "Touch") in the cabin colour, the ship preview, `<` / `>` for the colour, Ready and Leave buttons, and a short hint with that device's keys. The panel border flashes when its device sends input, so players can check that "my keys move this side".
   - Inside a slot the device's own actions apply only to that slot: left/right change the colour, fire toggles ready, **leave** frees the slot (keyboard set: its thrust key; gamepad: Back/Start; touch: the Leave button). A ready player cannot change colour.
   - Escape returns to the menu and cancels the join; a gamepad Back/Start from a pad that has not joined does the same.
   - The game starts when **at least two** slots are filled and all filled slots are ready, so one ready player does not start the game while a friend is still picking up a pad. The new game keeps the slots and their seats; empty slots are skipped.
   - Single player keeps today's one-panel selection screen where any input drives the panel and the game.

3. **Two keyboard sets: `KeyBindings.keys[set][action]`, file version 3 (unchanged).**
   - At most two players share one keyboard, so the two sets of the first iteration stay: set 1 W/A/D/Space, set 2 I/J/L/K, same file format and v2 migration. What changes is the meaning: `lookup(key, scancode)` returns `(set, action)` and the set is a *device* that belongs to whoever joined with it, not a fixed player. The arrow keys and Enter return set 1 (they join and steer as set 1 and still drive the menus); Escape returns `(None, 'back')`.
   - The settings page switch is relabelled "Keys of: Set 1 / Set 2", since a set is no longer tied to player 1 or 2.
   - Alternative: four sets for four players on one keyboard. Rejected: too cramped and limited by keyboard ghosting; the third and fourth players use gamepads.

4. **Gamepads join like keyboards.** FIRE from a pad that has not joined takes the first free slot on the join screen; in game the pad drives that slot only. Up to four pads. In single player every pad drives the ship, as before. Pads that send nothing are never assigned, so a resting pad cannot take a slot.

5. **Touch seats: at most two touch players, left and right.**
   - Touch players sit at the left and right sides of the screen facing each other, as in the first iteration. The seat belongs to the touch device, not the slot number: a touch player takes the side whose strip they tapped. The joined panel shows it ("Touch · left side"). Keyboard and gamepad players have no seat; they sit in front of the screen.
   - Only touch players get an overlay, and it is shown for the whole game regardless of the Auto/On/Off touch setting (joining by touch is an explicit choice); the size scale applies. Non-touch players get none, so a keyboard press no longer hides someone else's touch controls.
   - Layout per side is the first iteration's `ScreenButtonsLayout(side=...)` unchanged: left seat joystick at the top, FIRE in the bottom corner; right seat FIRE at the top, joystick in the bottom corner; FIRE label turned −90° / 90°.
   - The joystick is turned toward the seat (`Joystick.angle`: left seat −90°, right seat 90°): pushing it away from the player, toward the screen centre, thrusts; pushing it to the player's own left / right turns left / right. The finger position is turned back by the seat angle before the thresholds are applied, and the direction marks on the ring are drawn turned too. Turning keeps its meaning (a rotation looks the same from every seat), so only the stick frame changes.
   - Alternative kept from the first iteration: screen-space stick (up = thrust for everyone). Rejected after trying it: a player at the side has to push the stick sideways from their point of view to fly forward.
   - Single player keeps today's layout (joystick bottom-left, FIRE bottom-right) and the Auto/On/Off rules.
   - Alternative: four seats including bottom and top. Rejected: four touch sets do not fit a phone and the corners collide; more players use gamepads.

6. **Cabin colour by recolouring the sprite once, not per frame.** Unchanged from the first iteration: six colours, a texture pair per colour cached at first use, `Spaceship.cabin` selects it. Colours persist per slot in `ship_colors.json` (four entries; defaults blue, green, red, yellow; a two-entry file keeps its two and gets defaults for the rest, skipping colours already used). On joining, a slot gets its saved colour if no other joined slot has it, else the first free colour.

7. **Game over, HUD and start positions.**
   - A ship with `lives == 0` leaves and its controls are released; the game ends when no ship is left. Back/Escape or a joined pad's Back/Start ends the game for everyone.
   - One `SpaceshipStatus` per ship, tinted with the cabin colour. A touch player's block sits in the middle of their side, turned to read from the seat (left −90°, right 90°), as in the first iteration. Keyboard and gamepad players' blocks run upright along the top edge, one column per slot in player order, so they never collide with the side blocks. Single player keeps the top-right position.
   - Start positions are spread around the centre, one per slot, so ships do not overlap.

## Risks / Trade-offs

- [Keyboard ghosting with two sets on one keyboard] → Sets are on separate keyboard regions; README notes it and sets are rebindable.
- [Leaving with the thrust key on the join screen can happen by accident] → It only frees the slot; joining again is one FIRE press.
- [Three or four players need gamepads] → Accepted: the limits keep the keyboard and touch layouts usable.
- [Keybinding file format] → unchanged (v3); v2 files are still migrated.
- [The first iteration's fixed device order is replaced] → Its tests are rewritten to join first; single-player behaviour and tests stay.
- [Depends on uncommitted `improve-touch-controls`] → Apply in order.

## Migration Plan

A two-entry `ship_colors.json` is read and upgraded on the next save (above); `keybindings.json` keeps version 3. No rollback needed: older app versions ignore a four-entry colours file and use defaults.

## Open Questions

- None.
