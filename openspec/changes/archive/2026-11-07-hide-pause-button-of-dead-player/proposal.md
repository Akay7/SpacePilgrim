# Proposal

## Why

In a multiplayer game a touch player whose ship is out of lives keeps their "Pause" button, although they no longer play. It sits in the status block next to the final lives and points and invites a press that means nothing to that player.

## What Changes

- The Pause button of a touch player disappears once their ship is out of lives. The status block with their lives and points stays.
- The other players keep their buttons, and pausing and resuming does not bring the button back.

## Capabilities

### New Capabilities

### Modified Capabilities
- `pause`: the "Pause button" requirement now says the button of a player out of lives disappears.

## Impact

- `main.py`: `lose_spaceship` hides the button of the status block of the lost ship.
- `tests/test_game.py`: `test_pause_button_goes_away_with_its_dead_player`.
- `README.md`: a changelog line.
- The code and test are already in place (they were made while working on `gamepad-button-remapping`); this change only gives them their own proposal and spec.
