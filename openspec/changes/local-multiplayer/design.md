# Design

## Context

See proposal.md for motivation. Current state (observed in `main.py` / `spacepilgrim.kv`, including the uncommitted `improve-touch-controls` work this builds on):

- One `Spaceship` per game; `SpacePilgrimGame.spaceships` is already a list and `update`, `generate_asteroid` and collision code already loop over it, but `game_start` creates one ship and `update` calls `game_stop` as soon as one ship reaches `lives == 0`, ending the whole game.
- `ControlsManager` turns abstract actions (`up`, `left`, `right`, `fire`) into commands of **one** ship. Keyboard (`KeyBindings.action_for`), gamepad (`_on_joy_*`) and the touch overlay (`ScreenButtonsLayout` with `Joystick` + `FireButton`) all call `_input(source, action, pressed)` / `ControlsManager.press/release`.
- `KeyBindings` maps `action -> [scancodes]` (JSON `version: 2`); reserved keys (arrows, Enter, Esc) drive menus.
- `Spaceship` is drawn from `images/ship_stop.png` / `ship_fly.png` (91x90 pixel art); the cabin is a blue canopy near the nose.
- Menu has a disabled "Multiplayer" button; settings are `ButtonColumn` pages routed through `SpacePilgrimGame.settings`.

## Goals / Non-Goals

**Goals:**
- Two ships controllable at the same time from any mix of keyboard sets, gamepads and touch, without touching the single-player feel.
- Reuse the existing action model and widgets; no new image assets.

**Non-Goals:**
- A generic N-player model. Code is written with a `player` index (0/1) so a third player is not blocked, but the UI, defaults and layout target two.
- Ship-vs-ship damage, networked play, controller hot-plug UI.

## Decisions

1. **One `ControlsManager` per player; the game routes `(player, action)`.**
   - `game_start(players=1|2)` creates a `Spaceship` and a `ControlsManager` for each player; `self.controls = [ControlsManager, ...]`. Input handlers resolve a *source* to a player index and then call `controls[player].press/release(action)`.
   - `spaceship_controls` stays as an alias of player 1's manager so existing tests and single-player code paths keep working.
   - Alternative: one manager holding per-player `held` sets. Rejected: `ControlsManager` is already small and per-ship; duplicating it is simpler than parameterising every method.

2. **Key bindings per player: `KeyBindings.keys[player][action]`, file version 3.**
   - `action_for(key, scancode)` returns `(player, action)` or `(None, reserved_action)`; reserved arrow/Enter/Esc keys are unchanged and still belong to menus (and to *no* player in game, as today). Note that player 1's current defaults include the arrow keys through `RESERVED_KEY_ACTIONS` in-game; that behaviour is kept for player 1 only so single-player is unchanged.
   - Player 2 defaults: I / J / L / K (all outside the reserved set and not WASD/Space).
   - Conflict check spans both players (a physical key can belong to exactly one action).
   - Persistence: `{"version": 3, "players": [{...}, {...}]}`. A version 2 file is migrated: its keys become player 1, player 2 gets defaults. Any other invalid shape falls back to defaults, as now.
   - The in-game reserved arrow keys driving player 1 would make the arrows unusable for player 2; they therefore only drive player 1, and player 2 uses a rebindable set. That is the one asymmetry and it is documented in the README.

3. **Gamepad -> player by order of first input.**
   - `_on_joy_*` receive the SDL `stick` id. A dict `stick -> player` is filled when a stick first sends a *meaningful* input (button in `JOY_BUTTON_ACTIONS`, axis/hat beyond the dead zone) in a game: first stick -> player 0, second -> player 1, further sticks are ignored. In single player every stick maps to player 0. The map is cleared on `game_stop`.
   - In menus and settings every stick navigates (the player id is irrelevant), as today.
   - Alternative: assign by `stick` id number (0 -> P1, 1 -> P2). Rejected: ids on Android/SDL are not stable or dense when pads reconnect.

4. **Touch: two overlay sets, one per side, turned half a circle.**
   - `ScreenButtonsLayout` takes a `side`. In two-player mode two layouts are created: player 0 on the left edge and player 1 on the right edge. The players sit on opposite sides with the screen between them, so for each the joystick must be under the left hand and FIRE under the right hand *from their seat*. Each side uses its whole height: one control in the bottom corner and the other at the top just below the status text. Left player (facing right): joystick at the top, FIRE at the bottom; right player (facing left): FIRE at the top, joystick at the bottom. The two sides are the same shape rotated by 180°, so swapping the players changes nothing about how the game plays. Sizes shrink together when they would not fit between the HUD and the bottom margin, and are limited to their half's width.
   - Joystick directions stay in screen space (up = thrust, left/right = turn): ship rotation is screen based and a seat-relative stick would be confusing.
   - Visibility rules from `improve-touch-controls` (Auto/On/Off, hide on keyboard/gamepad use) apply to both overlays together.
   - Single player keeps today's layout (joystick bottom-left, FIRE bottom-right).
   - Alternatives rejected: both players' stick and FIRE in a row along the bottom (hands are not at the player's side), and the two controls stacked together in one bottom corner (not using the side, reviewed and rejected).

5. **Cabin colour by recolouring the sprite once, not per frame.**
   - At startup, build for each of N colours a texture pair (`stop`, `fly`) by copying the sprite and shifting hue/tint only for pixels in the cabin range (high blue relative to red/green and a saturated colour), using Pillow-free Kivy `Image`/`Texture.blit_buffer` over the RGBA bytes. Textures are cached in a `{colour: (stop, fly)}` dict; the `Spaceship` gets a `cabin` property selecting the pair and the kv rule uses `self.texture_stop/fly`.
   - Alternative: draw a coloured ellipse over the canopy. Rejected: a rotated overlay needs matching geometry and looks pasted on; recolouring keeps the pixel art.
   - Alternative: ship sprite tint (`Color`) for the whole hull. Rejected: user asked for the *cabin* colour; tinting the whole ship muddies the grey/red hull.
   - A small unit test asserts the pixels outside the cabin are unchanged and cabin pixels differ per colour.

6. **Ship selection is a new `ButtonColumn`-style screen shown from "Single player" and "Multiplayer".**
   - Shows one preview column per player (the recoloured sprite, enlarged), with `<` / `>` and a ready toggle for each player and a Back button. In two-player mode each player's keys drive their column: the turn-left/turn-right keys of their set (or gamepad left/right, or tapping the arrows) change the colour and fire confirms; the game starts when everyone is ready. Single player: any input drives column 1.
   - The pair of chosen colours is validated to be different: cycling skips the colour taken by the other column.
   - Colour choices persist in `ship_colors.json` in `user_data_dir` with defensive load/save (same pattern as `TouchSettings`).
   - Alternative: choose colours in Settings. Rejected: the request is to see the ship *before committing* to the game.

7. **Game over / lives per ship.**
   - `update` stops calling `game_stop` on the first death: a ship with `lives == 0` is removed (and its controls released); `game_stop` runs when `spaceships` becomes empty. Single player is a special case of that rule, so behaviour is the same.
   - Asteroid spawn distance check already uses `min` over all ships.
   - The HUD is one `SpaceshipStatus` per ship: in two-player mode each sits in the vertical middle of its player's side (between that player's joystick and FIRE button) and its text is tinted with the ship's cabin colour and rotated -90° (left player) / +90° (right player) so it reads upright from their seat; single player keeps today's top-right position.

## Risks / Trade-offs

- [Keyboard ghosting: some keyboards cannot report six held keys across both sets] → Defaults are placed on separate keyboard regions (WASD/Space vs IJKL); README notes it and the sets are rebindable.
- [Arrow keys drive only player 1 in game] → Documented; player 2 is intentionally on a rebindable set so layouts stay explicit.
- [Two touch columns are tall on small phones] → The pair shrinks together to stay under the HUD; check at 480 px height.
- [Recolour heuristic may miss anti-aliased cabin pixels] → Compare against the sprite by eye for each colour (task), tune the hue/saturation thresholds.
- [Keybinding file format change] → v2 files are migrated, never discarded.
- [Depends on uncommitted `improve-touch-controls`] → Apply in order; touch tasks here extend `ScreenButtonsLayout` from that change.

## Migration Plan

No data migration beyond reading `keybindings.json` v2 (above). No rollback needed: older app versions ignore a v3 file and use defaults.

## Open Questions

- Should the game also start with two ships when a second gamepad is detected on the main menu? (Assumed no: multiplayer is always chosen explicitly.)
