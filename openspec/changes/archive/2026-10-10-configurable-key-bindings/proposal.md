# Proposal

## Why

Keyboard controls are hard-coded (arrows/WASD, Enter/Space for fire). Players with other layouts (AZERTY, Dvorak, one-handed setups) or preferences cannot change them. The main menu already has a disabled "Settings" button waiting for this.

## What Changes

- Enable the main menu "Settings" button and open a controls settings screen from it.
- The screen lists the in-game actions (thrust, turn left, turn right, fire) with their current keyboard key and lets the player rebind each by pressing a new key.
- Bindings are persisted between launches; a "Reset to defaults" action restores the original layout.
- Game input resolves keys through the configured bindings instead of the fixed table; defaults behave exactly as today.
- Menu navigation and leaving the game (arrows, Enter, Escape/Back) stay on fixed keys so a bad binding can never lock the player out.

## Capabilities

### New Capabilities
- `key-bindings`: Player-configurable keyboard bindings for in-game actions, including the settings screen, conflict handling, persistence and reset.

### Modified Capabilities

## Impact

- `main.py`: key-to-action lookup, new settings screen widget, load/save of bindings, menu wiring.
- `spacepilgrim.kv`: enable "Settings" menu button, settings screen layout.
- `tests/test_game.py`: new tests for rebinding, conflicts, persistence.
- New file in the app user data directory (`keybindings.json`); no new dependencies.
- Out of scope: gamepad button remapping, remapping on-screen touch buttons, remapping menu navigation keys.
