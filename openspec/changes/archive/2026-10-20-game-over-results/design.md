## Context

`SpacePilgrimGame.lose_spaceship` calls `game_stop()` when the last ship is lost; `game_stop()` is also what Back/Escape calls, and it builds the `Menu`. Ships track `lives` and `points`. Persistent settings use small JSON-backed classes (`ShipColors`, `TouchSettings`) in `app.user_data_dir`. Screens are `ButtonColumn` subclasses styled in `spacepilgrim.kv`, navigated by `_input` routing for menu/select/settings.

## Goals / Non-Goals

**Goals:** results screen with per-player stats, local top-10 leaderboard, replay with identical configuration, return to menu; all input methods.
**Non-Goals:** online leaderboards, name entry, per-player leaderboard rows in multiplayer, persistent lifetime stats.

## Decisions

- **Separate "game over" from "quit".** Split `game_stop()` into `end_game()` (tears down ships/controls/statuses, as now) and callers: Back calls `end_game()` then shows the menu; losing the last ship builds a `GameResult` first, calls `end_game()`, then shows `ResultsScreen`. Alternative (flag on `game_stop`) rejected as easier to misuse.
- **Survival time via a game clock.** `update(dt)` accumulates `self.elapsed += dt` while the game runs (pause/resume therefore doesn't count). When a ship is lost, record `survived = self.elapsed` on it (new `Spaceship.survived`). At game over, ships still on the field cannot exist (game over means none), so every player has a value.
- **`GameResult` plain data** (list of per-slot `PlayerResult(slot, color, points, survived)`), built before teardown so the screen is independent of live widgets. Ships are removed on loss, so points/survival are copied into a per-slot record at `lose_spaceship` time rather than read afterwards.
- **Rating** is the points; no separate calculation. Survival time is informational and only a tie-breaker.
- **Replay config.** `game_start` stores `self.last_config = (players, colors, slots)`; "Play again" calls `game_start(*last_config)`. `game_start` currently removes `self.menu`; it must instead remove whichever of menu/results is showing.
- **Leaderboard** class mirrors `ShipColors`: `Leaderboard(path)`, `load()`, `add(entry)`, `top()`, `save()`; JSON `{version, entries}`, tolerant of missing/corrupt file (starts empty), write errors swallowed and reported to the screen. Entries sorted by (points desc, survived desc), capped at 10. `ResultsScreen` keeps a `saved` flag to enforce one save per game.
- **Nickname entry.** "Save to leaderboard" swaps the results screen for a `NameScreen` (`ButtonColumn` with a single-line `TextInput` limited to 12 characters, Save and Cancel buttons); Save stores the entry and returns to the results screen showing "Saved". The last nickname is kept as `last_name` in `leaderboard.json` and prefilled. While the screen is up, `_on_key_down` ignores bound game keys (like the key-rebinding page does) except Escape (cancel), so typing W/A/D/Space does not move the selection; Enter in the field validates. Gamepad/remote users navigate Save/Cancel with the existing menu routing and accept the prefilled name, since they cannot type.
- **Top player** = `max(results, key=(points, survived))`.
- **Screens** `ResultsScreen` and `LeaderboardScreen` subclass `ButtonColumn` (keyboard/gamepad navigation via existing `move/activate`; touch via buttons). `_input` gets `results_active` / `leaderboard_active` branches like `settings_active`; `back` maps to Main menu / back. Menu gets a "Leaderboard" button.
- **Input while dying.** Players mash FIRE at game over; ignore results-screen activation for ~1 s after it appears so a held/auto-fired button doesn't trigger "Play again" or leave immediately.

## Risks / Trade-offs

- Replaying with a gamepad that disconnected → its slot would have no input. Mitigation: replay keeps slots as-is; the player can leave via Main menu (acceptable, same as mid-game disconnect today).
- Android Back key is left to Kivy (pauses the app); results screen needs a visible Main menu button, which it has.
- Layout for 4 players on small phones: rows must fit; use compact rows within existing button-size conventions.

## Migration Plan

New file `leaderboard.json` created on first save; no migration. Rollback = remove feature; stray file is harmless.
