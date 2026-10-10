# Proposal

## Why

SpacePilgrim is single player only: the main menu has a disabled "Multiplayer" button, and the whole input layer (`ControlsManager`, key bindings, joystick overlay, gamepad routing) assumes one ship. Two people in the same room, on one TV or one tablet, cannot play together even though the game is small enough to be a good couch game.

## What Changes

- Enable the "Multiplayer" menu entry: a local two-player co-op game on one screen. Both ships fly in the same field, share the asteroids, and each has its own lives and points. The game ends when both ships are out of lives.
- Add a short **ship selection screen** before the game starts where each player picks the cabin colour of their ship and sees a live preview of it. Players cannot pick the same colour. Single player gets the same screen (player 1 only).
- Make the **keyboard** configurable per player: player 1 keeps W/A/D + Space, player 2 gets a second default set; the Keyboard layout settings page lets each player's keys be rebound separately, with conflicts rejected across both players.
- **Gamepads**: the first connected gamepad drives player 1 and the second drives player 2 in a two-player game; a single gamepad drives player 1.
- **Touch**: in a two-player game each player's on-screen controls are on their own side of the screen, for two players sitting on opposite sides: joystick under the left hand and FIRE under the right hand from their seat, one in the bottom corner and the other at the top of the side (player 1: joystick on top; player 2: FIRE on top).
- Recolour the ship's cabin (the blue canopy of the existing sprite) per player.
- Update the README controls section.

## Capabilities

### New Capabilities
- `local-multiplayer`: Two-player local game mode — starting it from the menu, how players are told apart, per-player lives/points and game end, how keyboard sets, gamepads and touch controls are assigned to each player.
- `ship-appearance`: The selectable cabin colours of a ship and the pre-game selection screen with a live preview.

### Modified Capabilities
- `key-bindings`: bindings become per player (two independent sets), with separate defaults, cross-player conflict checks, persistence and reset.

## Impact

- `main.py`: `ControlsManager` becomes one instance per player (or is parameterised by player); input routing (`_on_key_down/_up`, joystick handlers, `_input`) maps source -> player; `KeyBindings` gains a player dimension and a new file version; `ScreenButtonsLayout` gets a two-player layout; `Spaceship` gets a cabin colour; `SpaceshipStatus` shows both players; new selection screen; `game_start` / `game_stop` / collision logic handle multiple ships.
- `spacepilgrim.kv`: enable the Multiplayer button, add the ship selection rule, per-player HUD, a player switch on the keyboard settings page.
- `images/`: no new art assets required if the cabin recolour is done by shifting the hue of the blue canopy pixels at load time.
- `tests/test_game.py`: new tests for per-player routing, colours, game end, bindings migration.
- `README.md`: controls table and multiplayer notes.
- **Depends on** the in-flight `improve-touch-controls` change (joystick, FIRE button, touch settings and size scale) which this change extends; it should be applied/archived first, or both are applied in this order.
- Out of scope: online/network play, more than two players, versus mode (ships damaging each other), AI players, per-player touch size settings, gamepad remapping, new sprites, and any change to Android packaging.
