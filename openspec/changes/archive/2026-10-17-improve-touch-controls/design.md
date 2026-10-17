# Design

## Context

See proposal.md for motivation. Current state (observed in `main.py` / `spacepilgrim.kv`):

- `ScreenButtonsLayout` is an empty `Widget` subclass; its look comes from four stock `Button`s in the kv rule, positioned in cm.
- `SpacePilgrimGame.touchscreen = platform == 'android' and not is_android_tv()` is computed once. `_set_touch_ui(visible)` ANDs with `touchscreen`, so on a TV-detected device or on desktop the controls can never be made visible, and `_on_window_touch` is a no-op there.
- `ControlsManager.show_touch_buttons` toggles `opacity` and `disabled` on the layout. Input from keyboard/gamepad hides the controls via `_set_touch_ui(False)`; the next window touch brings them back.
- `SettingsScreen` is a `ButtonColumn` (keyboard-navigable, also touchable) bound to `KeyBindings`, which persists JSON in `user_data_dir/keybindings.json` with a safe fallback to defaults.
- `Window.on_touch_down` also fires for mouse clicks on desktop.

## Goals / Non-Goals

**Goals:**
- Controls that look like a classic gamepad and are drawn from canvas primitives (no new image assets required).
- A touch always has a way to surface the controls, plus an explicit setting as an escape hatch.
- Keyboard, gamepad and touch coexist with no mode switch the player must manage.

**Non-Goals:**
- Changing the action model (`up/left/right/fire` stay the only game actions) or `KeyBindings`.
- Analog/virtual-stick steering, multi-touch gesture handling beyond independent pressed controls.
- Fixing `is_android_tv()` detection itself; it only affects the *initial* visibility now.

## Decisions

1. **Replace `touchscreen` gating with a three-valued mode (`auto` / `on` / `off`) plus a runtime `touch_ui` flag.**
   - `off`: never visible. `on`: always visible in game, keyboard/gamepad input does not hide it. `auto`: visible initially only if `platform == 'android' and not is_android_tv()`; any touch shows it, keyboard/gamepad input hides it (today's behaviour, minus the platform check on the touch path).
   - Why: the bug is the hard platform gate; removing it from the touch path fixes devices misdetected as TV or non-Android touch devices, and the setting covers cases where touch events are indistinguishable from mouse/remote clicks.
   - Alternative considered: only drop the gate. Rejected: on devices where "touch" arrives as mouse-like events the player would still see no controls and have no recourse.

2. **Show controls on any `on_touch_down`, accepting that a desktop mouse click also shows them in Auto.**
   - A mouse click on the main menu happens before a game exists, so it is harmless; during a game a click revealing the pad is acceptable and arguably useful. Filtering on `touch.device` is fragile across Kivy providers (SDL2 on Android reports touches through the mouse provider), so it is not used.
   - Alternative: ignore `touch.device == 'mouse'`. Rejected as it would hide the pad on Android SDL2 builds where that is the only device name.

3. **Draw a virtual joystick plus a square red FIRE button with canvas instructions (no image assets).**
   - `Joystick`: translucent base circle with faint up/left/right markers and a draggable knob. The knob offset (clamped to the base radius, normalised to -1..1) maps to actions with a threshold of about 0.35: `dx < -T` left, `dx > T` right, `dy > T` up. Diagonals therefore press two actions at once; down and the dead zone press nothing. Press/release are sent only for actions that change, reusing `ControlsManager.press/release`.
   - The joystick keeps tracking its touch even when the finger leaves the base (knob clamped at the edge), like a typical on-screen stick; a second finger on the stick is ignored.
   - `FireButton`: square rounded-corner red button with a white "FIRE" label (as on arcade shooters), brighter while pressed, with per-touch press tracking so stick and fire work with two fingers.
   - Sizes in `cm` so they scale with density; positions anchored to window corners.
   - Alternative: keep the D-pad cross. Rejected on request: a stick allows in-between positions and feels more natural.

4. **Visibility toggling must not leave an invisible touch-blocking layer.**
   - Hide by removing interactivity (`disabled`) and `opacity = 0` as now, but the controls return False from `on_touch_down` when the overlay is inactive so touches reach whatever is below and still reach `Window.on_touch_down` for re-showing.

5. **Persist the setting in a small JSON file (`touch_ui.json` in `user_data_dir`, `{"mode": "auto"}`) reusing the defensive load/save pattern of `KeyBindings`.**
   - Alternative: add a key to `keybindings.json`. Rejected: mixes concerns and would couple "Reset to defaults" semantics (which resets keys only) to this option.
   - "Reset to defaults" continues to reset only key bindings.

6. **Settings becomes a small hub with two pages; each page is a `ButtonColumn`.**
   - `SettingsScreen` (hub: Keyboard layout / Touch controls / Back), `KeyboardSettings` (the former settings screen, unchanged logic), `TouchSettingsScreen` (mode, size, Back). `SpacePilgrimGame.settings` always points at the page currently shown, so existing key routing (move/activate/back) works for every page; each page knows its own "back" target (hub, or main menu for the hub).
   - Size is a `Slider` (50-400 %, step 5 %) with a percentage label. Keyboard/gamepad users adjust it with left/right (±10 %), handled by the game's input routing for the active page. It is saved when the finger lifts (or on each key step), not on every drag tick.
   - Size is applied when a game starts by resizing the joystick and fire button; each is clamped to the window height and half its width (minus margins) so 400 % never leaves the screen or overlaps; positions are anchored to the bottom corners.
   - Persistence: `touch_ui.json` now holds `{"mode": ..., "scale": ...}`; invalid values (non-numbers, out of the 50-400 % range) fall back individually.

## Risks / Trade-offs

- [Mouse clicks show the pad on desktop in Auto] → Acceptable; Off setting hides it, and keyboard use hides it again.
- [Touch events on some Android TV remotes/boxes may arrive as clicks and flash the pad] → Hidden again on the next key/D-pad press; user can set Off.
- [Keyboard page may not fit on a short landscape screen] → its height is clamped to the window height; verify at 480 px.
- [150% controls may overlap the HUD/playfield on small screens] → Largest step is limited; checked visually.
- [Circle hit-testing near the cluster edges] → Use generous radii and `collide_point` against circles via distance, covered by tests.
- [Auto-hide on any key could be annoying on hybrid devices] → `On` mode keeps it visible; this is the intended recourse.

## Open Questions

- Exact glyph/colour styling of the pad (can be tuned after a visual check on a device; does not change specs or tasks).
