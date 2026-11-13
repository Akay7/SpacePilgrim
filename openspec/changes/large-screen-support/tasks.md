# Tasks

## 1. No orientation restriction

- [ ] 1.1 Change `buildozer.spec` to `orientation = landscape, portrait, landscape-reverse, portrait-reverse`. Build a debug APK, then check that `aapt2 dump badging` shows no `screenOrientation` restriction and that `p4a_env_vars.txt` lists all four orientations. On the phone, the game turns to portrait when held upright, and stays in landscape with the system rotation lock on.

## 2. Touch seats at the short edges

- [x] 2.1 Make `touch_seats(size=None)` return `('left', 'right')` for a window at least as wide as it is high and `('top', 'bottom')` otherwise, keeping `FOUR_SEATS` for four-seat screens. Test 800 x 360, 360 x 800, 600 x 600 (square counts as wide) and a four-seat screen in both orientations, and verify with `pytest tests -k touch_seats`.
- [x] 2.2 Let `JoinScreen` build its strips for any seat set (left and right in the row, top and bottom in the middle column) instead of inferring four seats from `'top' in seats`. On `Window.size`, a two-seat screen with nobody seated by touch re-chooses its seats and rebuilds its strips; a seated player keeps their edge. Test the portrait phone strips (top and bottom, "Touch · top side"), empty seats moving on a turn, and a seated player keeping the left edge, and verify with `pytest tests -k "phone_seats or seats_follow"`.
- [x] 2.3 Test a two-player touch game with top and bottom seats on a 360 x 800 dp window: each player's joystick and FIRE are in the corners of their short edge, turned toward them, nothing overlaps or touches the edges, and the status blocks and Pause buttons read from their seats. Fix the layout if the test finds a problem, and verify with `pytest tests -k tall_phone_game`.

## 3. The game follows the window

- [x] 3.1 `JoinScreen`, the one screen that needs real work:
  - move the size, middle-width and four-seat middle-height computations into `_fit()`, called at creation and on `Window.size` and unbound when the screen closes;
  - choose four panels across, or two rows of two below room for four 150 dp panels;
  - put the bottom row in two lines below 560 dp.
  
  Test 360 x 800, 360 x 640, 800 x 360 and a turned tablet with keyboard set 1 joined, a seated touch player, the bottom row highlighted and a focused device-name box. Everything must be inside the window, with slots, seats, focus and highlight kept. Verify with `pytest tests -k join_screen_follows`.
- [x] 3.2 `ShipSelectScreen`: bind `Window.size` to `_center` and unbind when it closes. Add one parametrized resize test over every other screen (ship selection, menu, settings pages, leaderboard, pause, results, nickname, network list, address). At 360 x 800 dp and after landscape → portrait, each must be centred and inside the window, with its choices kept. Verify with `pytest tests -k screens_follow`.
- [x] 3.3 Add tests for a running game and the network:
  - a four-touch-player game resized to the other orientation keeps running, with each player's controls, lives and points and Pause button at their own edge;
  - a ship beyond the new width wraps on the next frame;
  - when the host's window turns, the client's `FieldView` takes the new field and re-fits it, and it re-fits again when the client's own window turns.
  
  Verify with `pytest tests -k "game_follows_window or field_follows"`.
- [x] 3.4 Check screenshots with the scratchpad rotation script: a phone (1600 x 720 at density 2) turned to portrait on the join screen and in a two-player touch game, and a tablet (2560 x 1600 at density 2) turned on the ship selection, the join screen with players and a four-player touch game. Confirm nothing is cut off or overlapping.

## 4. Pause with the controls

- [x] 4.1 Make `SpaceshipStatus.pause_center` place Pause from the player's touch controls: midway between joystick and FIRE along the edge, with its outer side at the joystick's outer side, and the bottom middle in single player. Fall back to the current place next to the lives and points when the gap is too small. Re-place it when the controls move or resize. Test single player at 800 x 360 and 360 x 800 dp, two touch players at left and right and at top and bottom, four touch players at 100% and at 400% (fallback, no overlap), and a player out of lives. Verify with `pytest tests -k pause_button`.
- [x] 4.2 Check screenshots of single player and a two-player touch game on a phone in landscape and portrait: Pause sits between the controls on their bottom line.
- [x] 4.3 Fit keyboard and gamepad players' lives and points on a phone: two-line blocks two per row below 600 dp, and `flank` blocks beside the left and right edges when a phone's touch seats are top and bottom (corners not kept free). Test 2, 3 and 4 such players at 360 x 800 with five-digit points (inside, no overlap), one-line quarters at 800 x 360, a turn to a narrow window, and touch top or bottom seats with keyboard and gamepad players at 360 x 800 and 800 x 360 (whole edges, no overlap), and that four-seat tablets keep the corners. Check screenshots of both orientations. Verify with `pytest tests -k status_`.
- [x] 4.4 Put touch controls in the free corners: `ScreenButtonsLayout` gets `seats` (taken touch edges), `corners` (corners holding lives and points) and `flank`, kept up to date by the game on every join and leave, in place of the single `free_corners` flag. A seat with no taken crossing edge reaches the corners of its edge, minus any corner with lives and points (measured along the edge); with crossing seats the layout stays as before. On a very small window the joystick and FIRE keep their order. Test a bottom or top seat with keyboard and gamepad players, top and bottom seats, a corner kept for lives and points, a crossing seat (short edges in the corners), a seat joining and leaving mid-game, a low wide window and a tiny window. Check screenshots at density 1 and 2. Verify with `pytest tests -k "corner or order"`.

## 5. On-screen keyboard

- [x] 5.1 Set `Window.softinput_mode = 'below_target'` once when the game starts. Test that the mode is set after `SpacePilgrimGame` is created, and that the nickname, address and device-name boxes are ordinary focusable `TextInput`s, so Kivy hands their rectangles to SDL. Verify with `pytest tests -k softinput`.
- [ ] 5.2 On the phone (debug APK): open *Save to leaderboard*, *Enter address* and the join screen's *Device name*, tap each box, and check that the box is shown above the on-screen keyboard and the screen moves back when the keyboard closes. Repeat in portrait. Note the result in this task.

## 6. Documentation

- [x] 6.1 README:
  - every device can be played in portrait or landscape;
  - on a phone the two touch players sit at its short ends (left and right in landscape, top and bottom in portrait);
  - a tip to turn on the system rotation lock for touch games;
  - the Pause button between a touch player's joystick and FIRE (the Pause section);
  - a history line under the next version.
  
  Update the Multiplayer section's seat description to match. Verify the README renders and the anchors resolve.
- [x] 6.2 Run the whole suite (`.venv/bin/python -m pytest tests`) and `openspec validate large-screen-support --strict`; both pass.

## Workflow follow-up

- Release together with the network game as 0.6.0 (`__version__` is already 0.6.0; the README history lists both under 0.6.0).
- After the release, check that the Play Console's large-screen notice is gone.
- Regenerate the store screenshots (`tools/play_listing.py`) if the join screen's landscape look changed.
- Archive the change after review, so that `screen-adaptation` moves to `openspec/specs/` and the `local-multiplayer` seat requirements are updated.
