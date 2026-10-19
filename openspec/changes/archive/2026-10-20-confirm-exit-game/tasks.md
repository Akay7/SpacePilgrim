# Tasks

## 1. Confirmation popup

- [x] 1.1 Add a `ConfirmScreen` (`ButtonColumn`) with "Are you sure?", "Yes" and "No" and its layout in `spacepilgrim.kv` (same dimmed backdrop as the pause screen), default selection "No". Verify: it renders in a screenshot run of the app.
- [x] 1.2 Make "Main menu" on `PauseScreen` open the popup (swapping out the pause screen) instead of calling `game_stop()`; "Yes" calls `game_stop()`, "No" restores the pause screen. Verify: tests show the game is still running state-wise after "No" and the menu is shown after "Yes".
- [x] 1.3 Route up/down/fire/back to the popup in `_input` while it is shown (Back = "No"); make `end_game()` and `resume()` safe when it is present. Verify: tests for keyboard navigation, Escape closing only the popup and fire on the default doing nothing destructive.

## 2. Confirm quitting the app

- [x] 2.1 Make "Exit" and desktop Escape on the main menu open the popup (`ConfirmScreen('exit')`); "Yes" stops the app, "No"/Escape returns to the menu. Verify: tests for No by default, Escape, and Yes quitting.

## 3. Checks

- [x] 3.1 Add tests to `tests/test_game.py` for the scenarios in specs/pause/spec.md and run the full suite in the venv. Verify: all tests pass.
- [x] 3.2 Run the app (`SDL_AUDIODRIVER=dummy`), pause, open the popup and check touch, keyboard and Escape by hand. Verify: behavior matches the spec scenarios.
