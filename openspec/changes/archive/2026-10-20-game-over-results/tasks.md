## 1. Stats tracking

- [x] 1.1 Add `PlayerResult`/`GameResult` data structures (slot, colour, points, survival seconds)
- [x] 1.2 Accumulate a game clock in `SpacePilgrimGame.update`, reset in `game_start`; record per-slot points, survival seconds and colour when a ship is lost (`lose_spaceship`)
- [x] 1.3 Store `last_config` (players, colors, slots) in `game_start`

## 2. Leaderboard store

- [x] 2.1 Add `Leaderboard` class (JSON in `user_data_dir/leaderboard.json`, load tolerant of missing/corrupt file, add, top-10 sorted by points then survival, save errors reported)
- [x] 2.2 Instantiate it in `SpacePilgrimGame.__init__` alongside the other stores

## 3. Screens and flow

- [x] 3.1 Split `game_stop` into teardown (`end_game`) and callers; Back/Escape goes to the menu, last-ship loss builds the result and shows `ResultsScreen`
- [x] 3.2 Add `ResultsScreen` (per-player rows with time, points, longest-survivor mark; buttons Save to leaderboard, Play again, Main menu; save once per game with confirmation/failure message; short input guard after appearing)
- [x] 3.3 Add `LeaderboardScreen` with empty-state text and a Back button; add "Leaderboard" entry to `Menu`
- [x] 3.4 Make `game_start` remove the results screen as well as the menu; wire "Play again" to `last_config`
- [x] 3.5 Add kv layouts in `spacepilgrim.kv` (fit 4 player rows on small screens)
- [x] 3.6 Route input (`results_active`, `leaderboard_active`) for keyboard, gamepad and touch; Back acts as Main menu / back

## 4. Tests and docs

- [x] 4.1 Tests: survival time per ship; leaderboard ordering, cap, persistence, corrupt file; save-once; top player in multiplayer
- [x] 4.2 Tests: game over shows results, Back skips results, Play again keeps players/slots/colours, Main menu shows menu
- [x] 4.3 Run the full test suite and check the results screen visually
- [x] 4.4 Update README.md (results screen, leaderboard)

## 5. Nickname

- [x] 5.1 Store a nickname per `Leaderboard` entry and the last used one (`last_name`); sanitise (trim, 12 chars, default "Player"); show it in the leaderboard rows
- [x] 5.2 Add `NameScreen` (TextInput prefilled, Save, Cancel) and kv layout; "Save to leaderboard" opens it, Save stores and returns to results, Cancel/Back/Escape returns without saving
- [x] 5.3 Suppress game-key routing while typing; gamepad can navigate Save/Cancel
- [x] 5.4 Tests (nickname stored/sanitised/remembered, cancel, key suppression, gamepad save) and README update
