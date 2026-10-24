# Tasks

## 1. Seats and big-screen check

- [x] 1.1 Add `SEAT_ANGLES`, `FOUR_SEAT_MIN_CM` and `four_seat_screen()` in `main.py` (Android `xdpi`/`ydpi` via `jnius`, else `Metrics.dpi`), and a `touch_seats()` helper that returns 2 or 4 seats; add tests in `tests/test_game.py` that a 21 × 13 cm and a 15 × 10 cm window get four seats and 15 × 7 cm / 15.5 × 8.7 cm get two (patch dpi and window size); verify with `pytest tests/test_game.py -k seat`
- [x] 1.2 Make the test fixtures default to a two-seat screen (patch `four_seat_screen` to `False` in `conftest.py` or the game fixtures) so existing tests do not depend on the desktop dpi; verify the full `pytest tests` run still passes unchanged

## 2. Joystick and FIRE for every seat

- [x] 2.1 Replace the `-90 if side == 'left' else 90` angle logic in `ScreenButtonsLayout` with `SEAT_ANGLES[side]` for `fire.text_angle` and `stick.angle`; add parametrised tests that the top seat's stick gives thrust when pushed down, turn right when pushed to screen-left, and the bottom seat's stick uses screen directions, and that the direction marks follow the angle; verify with `pytest -k stick`
- [x] 2.2 Add the `corners` flag and `_layout_edge()` to `ScreenButtonsLayout` (corner squares `C = max(m + s, CORNER_MIN)`, shared shrink factor `k` from the left/right stretch, stick/FIRE ends per seat as in design.md); keep `_layout_side()` for `corners=False`; add tests over screen sizes (15 × 10 cm, 21 × 13 cm, 1920 × 1080 px) and scales (0.5, 1, 4) that the eight controls stay on screen with the margin, do not overlap each other, keep the corners free, and have the same size for all seats; verify with `pytest -k four`
- [x] 2.3 Pass `corners=True` from `game_start` to every touch player's `ControlsManager`/`ScreenButtonsLayout` when any joined touch seat is `top` or `bottom`; test that a left+right touch game keeps today's positions (the existing `test_two_touch_sets_are_columns_on_each_side` passes) and a left+top game uses the corner layout

## 3. Status blocks and Pause buttons

- [x] 3.1 Rename the keyboard/gamepad status marker from `'top'` to `'row'` and add the corner mode; move label and Pause placement from the kv one-liners into `SpaceshipStatus` Python methods driven by `side`, `inset`, corner mode and `SEAT_ANGLES`, keeping the left/right/row/single-player positions identical; verify with the existing status and Pause tests (`pytest -k "status or pause"`) passing unchanged
- [x] 3.2 Extend `SpaceshipStatus.follow()` and placement to the top and bottom seats (middle of the edge, just inside the stick, turned 180° / 0°, Pause on the edge side between stick and FIRE); add tests with four touch players at scales 0.5, 1, 3 and 4 on a 15 × 10 cm screen that no block or Pause button overlaps any control or another block and that each block follows a later scale change
- [x] 3.3 Place keyboard/gamepad blocks in the corners by slot (TL, TR, BL, BR, two upright lines) when the corner layout is used; test a top+left touch game with keyboard set 1 as player 3 whose block is in the bottom-left corner and overlaps no control

## 4. Join screen

- [x] 4.1 Generalise `SideJoinButton` to any seat: horizontal strip for top/bottom, label turned by `SEAT_ANGLES`; test that the top strip label angle is 180 and the bottom 0, and left/right are unchanged
- [x] 4.2 Give `JoinScreen` a `seats` argument from `show_ship_select` (`touch_seats()`); with four seats fill the window and nest the strips around the panels as in design.md, show "tap an edge of the screen" in empty slots, and keep the two-seat layout as today; add tests that the four strips are at the four screen edges, that tapping top/bottom joins `('touch', 'top')` / `('touch', 'bottom')` with "Touch · top side", that four touch players can all get ready and start a game, and that strips stay hidden without a touchscreen until the first touch; verify existing join tests still pass

## 5. Docs and integration

- [x] 5.1 Update the Purpose paragraph of `openspec/specs/local-multiplayer/spec.md` ("up to two touch players" → up to two, or four on a big screen) and any README note on multiplayer touch players; verify the wording matches the delta spec
- [x] 5.2 Run the full test suite (`pytest tests`) and `openspec validate four-touch-seats --strict`; both pass
- [x] 5.3 Run the app on the desktop at a 15 × 10 cm and a phone-sized window (see the screenshot notes: `SDL_AUDIODRIVER=dummy`), join four touch players with the mouse and take screenshots of the join screen and the game; check that nothing overlaps and every label reads from its seat
- [ ] 5.4 Build the Android APK and try a four-player touch game on a real tablet (and a two-player game on a phone) to confirm the size check and that eight controls respond to simultaneous touches

## Workflow follow-up

- Archive the change after review, so the delta merges into `openspec/specs/local-multiplayer/spec.md`.
