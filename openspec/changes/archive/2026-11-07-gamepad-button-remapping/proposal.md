# Proposal

## Why

Gamepad buttons are hard-coded (A / X fire, B / Y thrust), while the keyboard is fully rebindable in Settings. Players with different pads, hand preferences or accessibility needs, and TV players who only have a pad, cannot change which button fires or thrusts. In a local multiplayer game two people often hold different pads that need different layouts. Thrust is also on/off, although pads have analog triggers that suit a gentle or full burn. The README lists "Gamepad button remapping" as the first open ToDo.

## What Changes

- Add a **Gamepad buttons** page to Settings, next to "Keyboard layout" and "Touch controls". It first picks a gamepad (a selector that cycles through the connected pads by name), then lists **Thrust** and **Fire** with what is bound for that pad.
- **Per-gamepad layouts**: each pad model has its own layout, found again after a restart or reconnect by the pad's name and GUID. A pad with no saved layout uses the defaults. Pads of the same model share one layout (they cannot be told apart).
- Selecting Thrust or Fire and pressing a button on the chosen pad binds that button for that pad. **Thrust is one entry for buttons and triggers**: after selecting it, pressing a button or pulling a trigger binds whichever you use (Fire takes buttons only). It takes effect at once, including in the game started afterwards. A new binding replaces every button the action had before (as keyboard rebinding does).
- **Trigger thrust (analog)**: a pad's thrust can be a trigger. While it is, it is the pad's only thrust (the thrust buttons of that pad are ignored) and the thrust power follows how far it is pulled, from none to full. Binding a button to Thrust again returns the pad to a button. Without a bound trigger, thrust is as before: full power while the button is held. Keyboard and touch thrust stay full power.
- **Variable thrust on the sticks**: in the game, pushing the gamepad's left stick or the on-screen joystick up thrusts with a power that grows with how far it is pushed (from a dead zone at 35% to full at the edge), like the trigger. Turning stays on/off, and the D-pad and the Thrust button stay full power.
- Remapped buttons apply only while a game runs: menus, the join screen, popups and settings keep the standard buttons (A / X activate, B / Y move up) whatever the layout.
- Fixed and not rebindable: Back/Start (pause, leave, cancel), the left stick and D-pad (steering and menu navigation, including the D-pad "buttons" 11-14 on Android) and the keyboard. A button that is reserved or already used by the other action of that pad is refused with a message and the old binding is kept. Back/Start or Escape while waiting for a button or trigger cancels.
- **Reset to defaults** on the page restores the default buttons (and so clears a trigger) of the chosen pad only.
- Layouts are saved locally and restored on the next launch; missing, unreadable or invalid data falls back to the defaults. A pad that cannot be identified uses the defaults and its changes last for the session only.
- The page can be operated with touch, keyboard and gamepad, like the other settings pages.
- README: remove the finished ToDo, describe the page, update the controls table and the changelog.

Out of scope: remapping the sticks (they only gain thrust power), D-pad or Back/Start, triggers for anything but thrust, several buttons per action in the UI, separate maps for two pads of the same model, analog thrust for keyboard, and engine sound volume following the trigger.

## Capabilities

### New Capabilities
- `gamepad-bindings`: Per-gamepad layouts for thrust and fire, the optional analog thrust trigger, the settings page to change them, conflict and reserved-input rules, persistence and reset.

### Modified Capabilities
- `touch-controls`: the on-screen joystick's thrust power follows how far up the knob is pushed.
- `key-bindings`: the "Settings screen access" requirement now also offers "Gamepad buttons" on the settings screen.

## Impact

- `main.py`: `stick_level` and per-source analog thrust in `ControlsManager` (trigger, stick), used by the on-screen `Joystick` and the gamepad stick; new `GamepadBindings` store of per-pad layouts (defaults per platform from the existing `JOY_BUTTON_ACTIONS_*`, persistence like `KeyBindings`), a pad identity helper (name and GUID through SDL), new `GamepadSettings` screen, analog thrust level on `Spaceship` and `ControlsManager`, and wiring in `SpacePilgrimGame` (`_on_joy_button_down/up`, `_on_joy_axis`, `show_settings`, input routing while waiting).
- `spacepilgrim.kv`: new "Gamepad buttons" entry on `SettingsScreen` (taller) and a `GamepadSettings` rule.
- `tests/test_game.py`: tests for per-pad layouts, rebinding, conflicts, trigger capture and thrust power, persistence, reset and game input.
- `README.md`: ToDo, controls and settings docs, changelog.
- New local file `gamepad_buttons.json` in the user data directory. No new dependencies; no change to the Android manifest.
