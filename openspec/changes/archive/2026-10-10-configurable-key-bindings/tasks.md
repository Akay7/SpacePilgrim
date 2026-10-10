# Tasks

## 1. Bindings model and persistence

- [x] 1.1 Add a `KeyBindings` model with defaults, reserved keys, `action_for`, `rebind` (rejecting conflicts/reserved keys) and `reset`; verify with unit tests for defaults, rebind replacing old keys, conflict and reserved rejection
- [x] 1.2 Add JSON load/save in the app user data dir with validation and fallback to defaults; verify with tests for round-trip, missing file, corrupt file and unwritable path

## 2. Input routing

- [x] 2.1 Switch `_on_key_down`/`_on_key_up` to resolve keys via the configured bindings plus fixed reserved keys; verify existing keyboard, WASD, repeat and menu navigation tests still pass and a rebound key drives the ship

## 3. Settings screen

- [x] 3.1 Add `SettingsScreen` widget and kv layout (four action rows showing current key, "Reset to defaults", "Back") navigable by keyboard/gamepad and pointer; verify opening/closing from the menu in a test
- [x] 3.2 Enable the main menu "Settings" button and wire it to open the screen; verify the button is no longer disabled and returns to the menu on Back
- [x] 3.3 Implement key capture (wait state, bind, reject with message, Escape cancels without exiting); verify with tests for rebind, conflict message, cancel and reset

## 4. Docs and final check

- [x] 4.1 Document the configurable controls in README.md and verify the described steps match the UI
- [x] 4.2 Run the full test suite and manually launch the game to rebind a key, restart and confirm it persisted
