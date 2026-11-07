# Tasks

## 1. Pad identity and bindings model

- [x] 1.1 In `main.py` split the Back and Android D-pad ids out of `JOY_BUTTON_ACTIONS_*` into a fixed table, keep the existing constants as the defaults, and add the button name table (A, B, X, Y, else "Button N"). Verify the existing tests that read `JOY_BUTTON_ACTIONS_ANDROID/DESKTOP` still pass.
- [x] 1.2 Add `PadIdentity` (instance id -> identity and name, connected pads) over the SDL library, returning `None` for anything it cannot resolve, with an injectable fake for tests. Verify with tests using the fake (known id, unknown id, no SDL) and by running it against the real SDL on the desktop with no pad connected (no crash, empty list).
- [x] 1.3 Add `GamepadBindings` (per-identity profiles with buttons and trigger, `action_for`, `label`, `rebind`, `bind_trigger`, `reset`, `load/save`, `gamepad_buttons.json` version 1) modelled on `KeyBindings`. Verify with unit tests in `tests/test_game.py`: defaults, replace on rebind, refusal of a button used by the other action and of reserved ids, the same button allowed on another pad, reset of one pad only, save/restore round trip, corrupt/invalid/unreadable file falling back to defaults (one invalid profile dropped, the rest kept), unidentified pad not saved, and a failing save keeping the in-memory bindings.

## 2. Game wiring for buttons

- [x] 2.1 Create `GamepadBindings` and `PadIdentity` in `SpacePilgrimGame.__init__` (path in `user_data_dir`) and use them in `_on_joy_button_down/up` with the action remembered at press time, so a rebind while a button is held cannot leave a ship thrusting or firing. Verify with tests that a remapped Fire/Thrust button drives the ship of that pad only, the old buttons no longer do, a second pad of another model keeps its own layout in a multiplayer game, and Back/Start and the Android D-pad ids still work.
- [x] 2.2 Verify with tests that menus keep the standard buttons: with Fire remapped, A / X still activate entries on the menu, join screen (joins a slot), pause and confirm popups, results and name entry, and the remapped button does nothing there.

## 3. Analog thrust

- [x] 3.1 Add `thrust_level` to `Spaceship` and `set_thrust(level)` to `ControlsManager` (speed is `3 * level` while thrusting; engine sound while above 0; `press('up')` stays full). Verify with tests that the speed after an update is 0, about half and full for levels 0, 0.5 and 1, that keyboard and touch thrust are unchanged, that the engine sound starts and stops as before, and that one ship's level does not change another's.
- [x] 3.2 Handle trigger axes in `_on_joy_axis`: for a pad with a bound trigger normalise `(v - rest) / (full - rest)` with a 0.1 dead zone and call `set_thrust` for that pad's ship, and ignore the pad's Thrust buttons. Verify with tests for triggers resting at -1 and at 0, half and full pull, release, the Thrust button being ignored while a trigger is bound, a pad without a trigger being unchanged, and stick axes 0 and 1 still steering.

## 4. Settings page

- [x] 4.1 Add the `GamepadSettings` page (pad selector, Thrust, Fire, Reset to defaults, Back, message label) in `main.py` and `spacepilgrim.kv`, add "Gamepad buttons" to `SettingsScreen` (taller to fit) and `show_gamepad_settings()` to the game. Verify with tests that Settings > Gamepad buttons > Back > Back walks settings, page, settings, menu, that the labels show e.g. "Thrust: B, Y" and "Fire: A, X", that the selector cycles through two fake pads, and that the "No gamepad connected" state disables binding.
- [x] 4.2 Add capture: `_on_joy_button_down` and `_on_joy_axis` hand input to a waiting page (before normal routing), only for the pad being edited; Back/Start buttons and Escape cancel without pausing or closing the page, stick and D-pad movement is ignored while waiting, and buttons pressed while not waiting change nothing. Verify with tests for bind, conflict message, reserved message, cancel by pad Back, cancel by Escape, another pad ignored, trigger binding (rest at -1 and 0), the stick ignored while waiting, Thrust taking a button or a trigger (and a button replacing the trigger), Fire ignoring triggers, and that the press selecting the entry does not bind itself.
- [x] 4.3 Run the app on the desktop (injected joystick events if no pad is available) following the "Running the app for screenshots" notes, open the page and check the layout at phone and TV sizes. Verify with a screenshot that all rows and the message fit on the page.

## 5. Docs and integration

- [x] 5.1 Update `README.md`: remove "Gamepad button remapping" from the ToDo, note in the controls table that gamepad buttons are rebindable per pad and that a trigger can thrust with variable power, describe Settings > Gamepad buttons (what is fixed, same-model pads sharing a layout, where it is saved), and add a changelog line. Verify the README renders the table correctly and mentions `gamepad_buttons.json`.
- [x] 5.2 Run the full test suite from the project venv and verify it passes.

## 6. Reconnecting gamepads

- [x] 6.1 Run the gamepad watcher on every platform, not only Android, so a pad that is switched on later or unplugged and plugged in again on the desktop sends events again and finds its saved layout (spec: "Reconnected pad"). Verify with tests that the watcher is started with SDL and opens a pad that appears later, and with a run against the real SDL on the desktop.

## 7. Thrust power on the sticks

- [x] 7.1 Add `stick_level`, per-source analog thrust in `ControlsManager`, and use it in the on-screen `Joystick` (thrust power from how far up the knob is, turning unchanged) and in the gamepad stick (axis 1 in the game; menus still navigate with it). Verify with tests: the level function, half and full push on both sticks, release, pad that did not join, stick and trigger together taking the stronger, D-pad and Thrust button staying full power, pause letting go, and menus still navigated with the stick.
- [x] 7.2 Document the stick thrust power in `README.md` (controls table, changelog) and verify the existing joystick tests still pass.

## 8. One Thrust entry for buttons and triggers

- [x] 8.1 Merge the "Thrust trigger" entry into "Thrust" on the gamepad page: waiting for Thrust takes a pressed button or a pulled trigger, a button replaces a bound trigger, Fire takes buttons only, the stick is ignored while waiting, the label shows "trigger (axis N)". Verify with tests (model: label, button replacing the trigger, free thrust buttons for Fire; page: button then trigger then button through one entry, Fire ignoring axes, stick ignored) and a screenshot of the page.

## Workflow follow-up

- Archive the change after implementation and review (`/opsx:archive`).
