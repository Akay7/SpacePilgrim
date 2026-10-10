# Design

## Context

`main.py` maps SDL key codes to actions via the module-level `KEY_ACTIONS` dict, used by `_on_key_down`/`_on_key_up`, and `_input` routes actions to the `Menu` or `ControlsManager`. The same actions drive menu navigation (`up`/`down`/`fire`/`back`). The menu is a `BoxLayout` of buttons with keyboard highlighting; the "Settings" button is currently `disabled`. Gamepad and touch buttons feed the same abstract actions. Kivy's `App.user_data_dir` is the writable location on desktop and Android.

## Goals / Non-Goals

**Goals:**
- Rebind keyboard keys for `up`, `left`, `right`, `fire` with persistence and reset.
- Keep default behaviour and all existing tests passing.
- Settings screen usable by keyboard and mouse/touch.

**Non-Goals:**
- Gamepad remapping, touch button layout, multiple keys per action in the UI, localisation of key names beyond Kivy's own.

## Decisions

1. **Bindings model**: a `KeyBindings` object holds `action -> list[int]` of SDL scancodes (physical keys, so bindings and latin labels are independent of the keyboard layout; saved file has `version: 2`) and exposes `action_for(key)`, `rebind(action, key)`, `reset()`. Defaults are split out of today's `KEY_ACTIONS` (gameplay keys only: arrows+WASD, Space). Rebinding replaces the list with the single new key. *Alternative*: add/append keys — rejected, it makes the screen and conflict handling more complex for little gain.
2. **Reserved keys stay fixed**: arrows, Enter, numpad Enter, Android Select, and Escape/Back remain in a separate fixed table consulted after the configurable one. This guarantees menu navigation and exit always work. A key in the reserved table cannot be bound. Consequence: arrows still steer even if the player rebinds thrust/turn keys; accepted since they are also menu keys.
3. **Conflict policy**: reject and show a message rather than silently stealing the key from another action. *Alternative*: swap bindings — rejected as surprising and harder to test.
4. **Capture flow**: selecting an action puts the settings screen into "waiting for key" state; the next `on_key_down` is consumed there (before normal routing) and either binds, rejects, or (Escape) cancels. `_on_keyboard` already swallows Escape on desktop, so cancel must not reach `back`.
5. **Settings screen**: a `SettingsScreen` widget (kv layout) replaces the `Menu` in `SpacePilgrimGame` the same way the menu is shown/hidden, reusing the menu's button highlighting and `move`/`activate` so it is keyboard/gamepad navigable. Rows: four actions, "Reset to defaults", "Back".
6. **Persistence**: JSON file `keybindings.json` in `App.user_data_dir`, written on every successful change/reset. Load validates structure (known actions, int lists, no duplicates/reserved keys) and falls back to defaults on any error. *Alternative*: Kivy `Settings`/config panel — rejected: `use_kivy_settings = False` and its UI is poor for key capture and TV/touch.

## Risks / Trade-offs

- [Player binds a key the Android soft keyboard/TV remote never sends] → touch buttons and arrows remain usable; reset is available.
- [Save failure on read-only storage] → catch `OSError`, keep in-memory bindings for the session.
- [Key names for special SDL codes are unfriendly] → use `Window.keycodes` reverse lookup with a fallback to the numeric code.
- [Tests currently import `KEY_ACTIONS`] → keep a compatible default constant or update tests alongside the refactor.
