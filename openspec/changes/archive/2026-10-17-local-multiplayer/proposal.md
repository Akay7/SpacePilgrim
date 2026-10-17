# Proposal

## Why

SpacePilgrim is single player only: the main menu has a disabled "Multiplayer" button, and the whole input layer (`ControlsManager`, key bindings, joystick overlay, gamepad routing) assumes one ship. Two to four people in the same room, on one TV or one tablet, cannot play together even though the game is small enough to be a good couch game.

## What Changes

- Enable the "Multiplayer" menu entry: a local co-op game for **two to four players** on one screen. All ships fly in the same field, share the asteroids, and each has its own lives and points. The game ends when every ship is out of lives.
- Players **join** a game on a **join screen** with four slots instead of being assigned to inputs by a fixed order. Whoever presses FIRE on a keyboard set or a gamepad takes the next free slot with that device, and a touch player joins by tapping the "Tap to join by touch" strip at the left or right edge of the screen, the side where they will sit. The slot shows the device that joined it, so everyone sees which keys or pad belong to which ship, and several players can set up at the same time without disturbing each other. A player can **leave** the slot again (their thrust key, the pad's Back/Start, or the Leave button). The game starts when at least two players have joined and all of them are ready.
- On the join screen each player picks the cabin colour of their ship and sees a live preview of it. Players cannot pick the same colour. Single player keeps a one-ship selection screen driven by any input.
- **Keyboard**: at most **two players on one keyboard**, with two rebindable keyboard sets (W A D Space and I J L K). A set belongs to whoever joined with it; the arrow keys and Enter belong to set 1. The Keyboard layout settings page lets each set be rebound, with conflicts rejected across both sets.
- **Gamepads**: each gamepad drives the player who joined with it; up to four pads. In single player any pad drives the ship, as before.
- **Touch**: at most **two players on the touch screen**. They sit at the left and right sides of the screen, facing each other, on the side whose join strip they tapped. A touch player's joystick and FIRE are at the two ends of their side, joystick under the left hand and FIRE under the right hand as seen from their seat, and they stay shown during the game. The joystick is turned toward the seat: pushing it away from the player (toward the screen centre) thrusts, and pushing it to the player's own left or right turns. Players on other devices get no touch controls.
- Each touch player's lives and points are shown in the middle of their side, tinted with their cabin colour and turned to read upright from their seat. Keyboard and gamepad players sit in front of the screen; their status blocks run upright along the top edge in player order.
- Recolour the ship's cabin (the blue canopy of the existing sprite) per player.
- Update the README controls section.

## Capabilities

### New Capabilities
- `local-multiplayer`: Local game mode for two to four players: starting it from the menu, joining and leaving with a device, the limits of two keyboard and two touch players, touch seats, per-player lives/points and game end, and how keyboard sets, gamepads and touch controls drive the player who joined with them.
- `ship-appearance`: The selectable cabin colours of a ship and the pre-game selection with a live preview.

### Modified Capabilities
- `key-bindings`: bindings become two independent keyboard sets, with separate defaults, cross-set conflict checks, persistence and reset.

## Impact

- `main.py`: one `ControlsManager` per player; input routing maps a *device* (keyboard set, gamepad stick id, touch) to the slot it joined; `KeyBindings` gains a set dimension and a new file version; `ScreenButtonsLayout` gets a left and a right touch layout; `Spaceship` gets a cabin colour; one `SpaceshipStatus` per player; new join screen; `game_start` / `game_stop` / collision logic handle up to four ships.
- `spacepilgrim.kv`: enable the Multiplayer button, per-player HUD (side blocks for touch players, a top row for the others), a set switch on the keyboard settings page.
- `images/`: no new art assets; the cabin recolour shifts the hue of the blue canopy pixels at load time.
- `tests/test_game.py`: tests for joining/leaving, device routing, four ships, seats, colours, game end, bindings migration.
- `README.md`: controls table and multiplayer notes.
- **Depends on** the in-flight `improve-touch-controls` change (joystick, FIRE button, touch settings and size scale) which this change extends; it should be applied/archived first, or both are applied in this order.
- Out of scope: online/network play, more than four players, more than two players on one keyboard or on the touch screen, top/bottom touch seats, versus mode (ships damaging each other), AI players, per-player touch size settings, gamepad remapping, gamepad hot-plug handling beyond ignoring a missing pad, new sprites, and any change to Android packaging.
