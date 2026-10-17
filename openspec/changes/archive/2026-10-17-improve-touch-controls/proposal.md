# Proposal

## Why

The on-screen controls are four square `Button` widgets (Left / Right / Up / Fire) that look like a debug UI, not a game pad. Worse, they are only ever shown when the app detects `platform == 'android'` and the device is *not* a TV (`is_android_tv()`). On a device that has a touchscreen but is detected as a TV/leanback device (or is not Android at all, e.g. a touch laptop), the buttons are never created visible and nothing in the UI can turn them on, so the touchscreen cannot be used to play.

## What Changes

- Replace the square text buttons with a virtual joystick (draggable knob; up = thrust, left, right, and in-between positions) on the left and a square red "FIRE" button on the right, drawn with canvas shapes/icons instead of stock `Button` backgrounds.
- Show the on-screen controls on **any** platform as soon as a real touch is received, regardless of TV detection; keyboard or gamepad input hides them again (existing behaviour kept).
- Split Settings into two pages: "Keyboard layout" (the existing key rebinding) and "Touch controls".
- On the Touch controls page, add a mode setting (Auto / On / Off) so a player can force the controls on (or off) when auto-detection gets it wrong, and a size setting to scale the joystick and fire button. Both are persisted locally.
- Keyboard, gamepad and touch SHALL work side by side: using one never disables the others, and a device with both a keyboard and a touchscreen can be played with either at any moment.
- Update the README controls table/notes accordingly.

## Capabilities

### New Capabilities
- `touch-controls`: On-screen touch controls for steering, thrust and fire — their appearance, when they are shown/hidden, the player-facing setting that overrides auto-detection, and coexistence with keyboard and gamepad input.

### Modified Capabilities
- `key-bindings`: the key rebinding screen now lives under Settings > Keyboard layout instead of being the Settings screen itself.

## Impact

- `spacepilgrim.kv`: replace `<ScreenButtonsLayout>` rules; add a touch-controls row/toggle to `<SettingsScreen>`.
- `main.py`: `ScreenButtonsLayout`, `ControlsManager.show_touch_buttons`, `SpacePilgrimGame._set_touch_ui` / `_on_window_touch` / `touchscreen` detection, settings hub, keyboard and touch pages (mode + size, persistence).
- `tests/test_game.py`: touch-visibility and setting tests.
- `README.md`: Controls section and the Android TV checklist line about touch buttons.
- Out of scope: gamepad/keyboard remapping changes, multi-touch gestures, haptics, Android manifest changes, new gameplay actions (e.g. a "down" control), redesigning the main menu look.
