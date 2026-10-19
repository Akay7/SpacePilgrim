# Proposal

## Why

When the last ship is lost the game drops straight back to the main menu, so the player never sees how they did and has to click through the menu (and the ship/join screens) to play again. A results screen with replay and a local leaderboard gives the run a conclusion and a reason to try again.

## What Changes

- When a game ends because all ships are out of lives, show a **results screen** instead of returning to the main menu. It lists, per player: time survived (seconds) and points (the points are the rating).
- The player with the longest survival time is marked as the best survivor; in multiplayer the player with the most points is shown as well when different.
- Offer **Save to leaderboard**: stores the run's best player (the only player in single player; the top player in multiplayer) in a local leaderboard on the device. The button is usable once per game.
- Offer **Play again**: restarts with the same configuration (player count, devices/slots, cabin colours).
- Offer **Main menu**: goes to the main menu.
- Add a **Leaderboard** screen reachable from the main menu, listing the saved entries (top 10, best points first).
- Quitting with Back/Escape during play still goes straight to the main menu, with no results screen.
- **BREAKING (spec only)**: "Game end in multiplayer" no longer returns directly to the main menu when all ships are lost.

## Capabilities

### New Capabilities
- `game-results`: results screen after a game ends (stats, rating, save, play again, main menu), per-ship survival tracking, and the on-device leaderboard with its menu screen.

### Modified Capabilities
- `local-multiplayer`: "Game end in multiplayer" — losing all ships shows the results screen; Back/Escape still ends the game straight to the main menu.

## Impact

- `main.py`: survival timer and result capture in `SpacePilgrimGame`/`Spaceship`, a `Leaderboard` store class (JSON in `user_data_dir`, like `ShipColors`), new `ResultsScreen` and `LeaderboardScreen` (`ButtonColumn` subclasses), a new menu entry, input routing for the new screens.
- `spacepilgrim.kv`: layouts for the two new screens and the menu button.
- `tests/test_game.py`: tests for stats, rating, leaderboard persistence, replay and navigation.
- `README.md`: mention the results screen and leaderboard.
- No new dependencies; data stays on the device (PRIVACY.md unaffected, nothing is transmitted).

## Assumptions

- "Rating" is simply the points scored; the survival time is shown for information only.
- No name entry: leaderboard rows record points and survival seconds; in multiplayer the row is labelled with the player's slot colour/number.
- "Top player" in multiplayer is the player with the most points (ties: longer survival).
