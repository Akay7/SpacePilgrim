# Proposal

## Why

Choosing "Main menu" on the pause screen throws the running game away at once, so a mis-tap or a stray fire-key press loses all progress. The player should be asked to confirm first.

## What Changes

- "Main menu" on the pause screen opens a confirmation popup ("Are you sure?") with "Yes" and "No" instead of leaving immediately.
- "Yes" ends the game and shows the main menu, as "Main menu" did before.
- "No", and Escape / Back (or a gamepad's Back/Start) while the popup is shown, close the popup only; the game stays paused and the pause screen is shown again.
- "Exit" on the main menu (and Escape there on desktop) opens the same popup before the app quits. "No" or Escape returns to the main menu.
- The popup works with touch, keyboard navigation and gamepad like the other screens.

Out of scope: the Android Back key on the main menu (left to the system) and the results screen's "Main menu" button (the game is already over).

## Capabilities

### New Capabilities

### Modified Capabilities
- `pause`: leaving to the main menu from the pause screen, and quitting the app from the main menu, need a confirmation. This spec is introduced by the unarchived `pause-button` change; archive that change first.

## Impact

- `main.py`: new confirmation popup screen, input handling while it is shown, `PauseScreen` "Main menu" action.
- `spacepilgrim.kv`: layout of the popup.
- `tests/test_game.py`: tests for the popup.
