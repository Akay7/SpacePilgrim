# Proposal

## Why

Touch players have a "Menu" button in their status block that drops them straight into the main menu and ends the game. A tap in the wrong place loses the whole run, and there is no way to stop the action for a moment (a call, a drink) without quitting.

## What Changes

- The in-game touch button "Menu" becomes "Pause"; it keeps the transparent inside with the rounded blue outline and its place and turning for each touch player.
- Pressing it freezes the world: ships, asteroids, shots, explosions, the game clock and the spawning of new asteroids stop, and ship sounds are silenced.
- A pause screen appears over the frozen world, which stays visible together with every player's lives and points. It offers "Continue" (resume exactly where the game stopped) and "Main menu" (end the game and show the main menu).
- The pause screen is operable by touch, keyboard and gamepad; Back/Escape on it continues the game.
- Back/Escape and a gamepad's Back/Start during play pause the game instead of leaving it (leaving is "Main menu" on the pause screen).
- Works in single player and in multiplayer games (any touch player's Pause button pauses everybody).

## Capabilities

### New Capabilities
- `pause`: pausing a running game from the touch Pause button, the frozen state, and the pause screen with Continue / Main menu.

### Modified Capabilities
- `local-multiplayer`: Back/Escape no longer ends a multiplayer game, it pauses it.

## Impact

- `main.py`: `MenuButton` becomes the pause button, new pause screen widget, pause/resume in `SpacePilgrimGame` (frame and asteroid schedules, running animations, engine sound), input routing while paused.
- `spacepilgrim.kv`: button label, new `<PauseScreen>` rule.
- `tests/test_game.py`: pause/resume tests; README controls note.
