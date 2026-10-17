# Tasks

## 1. Touch visibility model and setting

- [x] 1.1 Add a persisted touch-controls mode (`auto`/`on`/`off`, default `auto`) stored in `touch_ui.json` under `user_data_dir`, with fallback to `auto` on missing/corrupt data; verify with unit tests for default, save/restore and corrupt file
- [x] 1.2 Rework `SpacePilgrimGame` visibility logic (`touchscreen`, `_set_touch_ui`, `_on_window_touch`) so any touch shows the controls on every platform in Auto, keyboard/gamepad hides them in Auto, `on` keeps them visible and `off` never shows them; verify with tests simulating `_on_window_touch`, key and joy input in each mode (including a "TV-detected" device)
- [x] 1.3 Add a "Touch controls: Auto/On/Off" button to the Settings screen (kv + `SettingsScreen`) that cycles, applies immediately and saves; make sure the column fits at 480 px window height and "Reset to defaults" still only resets keys; verify with a test that activating the button cycles and persists, and by activating it via a simulated touch on its widget

## 2. Joystick look

- [x] 2.1 Implement the canvas-drawn `Joystick` (base, markers, draggable knob mapping to up/left/right incl. diagonals) and the square red `FireButton`, replacing the square `Button`s; verify by running the app on desktop with the mode set to On and checking by eye that no square text buttons remain
- [x] 2.2 Make the joystick track its own touch (knob follows, recentres and releases actions on lift, ignores hidden/disabled) while fire stays independent; verify with tests for pure directions, diagonals, release, down/dead zone and stick+fire together
- [x] 2.3 Verify layout scaling at a phone-landscape size and a 1080p TV size by running with `Window.size` overrides, adjusting cm/dp sizes if controls overlap the HUD or leave the screen

## 3. Settings pages and size

- [x] 3.1 Split Settings into a hub with "Keyboard layout" and "Touch controls" pages (kv + classes), with Back navigation hub -> menu and page -> hub, including Escape/gamepad back; verify with tests that open each page and go back
- [x] 3.2 Add the size slider (50-400 %, label, left/right keys) and persistence to the touch controls page and apply it to the joystick and fire button when a game starts, clamped to the screen; verify with tests for slider/keyboard changes, persistence, invalid saved values and on-screen clamping at 400 %
- [x] 3.3 Check by eye on desktop that the pages fit and that 70% and 150% controls stay on screen and clear of the HUD

## 4. Docs and integration

- [x] 4.1 Update README Controls table and notes (touch pad layout, auto show/hide, "Touch controls" setting) and the Android TV checklist line about touch buttons; verify the README text matches the implemented behaviour
- [ ] 4.2 Run the full test suite (`pytest tests`) and verify it passes, then manually check on a device with both touchscreen and keyboard that either input can be used at any time, and that the controls can be enabled from Settings by touch
