# Tasks

## 1. Pause in the game

- [x] 1.1 Add `paused` state and `pause()` / `resume()` to `SpacePilgrimGame`: cancel and re-create the frame and asteroid schedules, stop and restart explosion animations, stop engine sounds, release held actions. Verify with a test that after `pause()` asteroids, shots and `elapsed` do not change across `Clock.tick`s and that `resume()` makes them move again.
- [x] 1.2 Make `game_stop()` and `game_over()` work while paused (clear the pause screen and state). Verify with a test that "Main menu" from pause shows the menu and a later `game_start` runs unpaused.

## 2. Pause screen and button

- [x] 2.1 Rename `MenuButton` to `PauseButton`, label "Pause", wired to `pause()`; keep the transparent inside and rounded blue outline. Verify the label in `test_game.py` and by screenshot in single and two-touch-player games.
- [x] 2.2 Add `PauseScreen` (Continue, Main menu) with a `<PauseScreen>` rule in `spacepilgrim.kv`; frozen world and status blocks stay visible. Verify by screenshot.
- [x] 2.3 Route input while paused: up/down/fire/back on the pause screen (Back = Continue), nothing reaches the ships. Verify with tests for keyboard and gamepad navigation and for no thrust/fire after resume.

- [x] 2.4 Route Back/Escape/Start during play to `pause()`; update the tests that expected Back to leave the game. Verify with tests for keyboard and gamepad Back pausing in single and multiplayer, and for Android Back being consumed.

## 3. Wrap-up

- [x] 3.1 Update the README controls section and the store-listing tool if it references the "Menu" button. Verify with `grep -rn '"Menu"' main.py spacepilgrim.kv tools README.md`.
- [x] 3.2 Run the whole test suite (`.venv/bin/python -m pytest tests`) and confirm it passes.
