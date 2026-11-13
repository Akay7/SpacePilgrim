# Proposal

## Why

Google Play flags the last release: "Remove resizability and orientation restrictions in your game to support large screen devices". The manifest declares no orientation (`screenOrientation="unspecified"`). The restriction comes at run time: `buildozer.spec` lists only `landscape,landscape-reverse`, so SDL calls `setRequestedOrientation(SENSOR_LANDSCAPE)` on every device. Android 16 (API 36, which the game targets) already ignores that request on large screens, so tablets, foldables and Chromebooks can show the game in portrait or in a resized window. Two screens break there:
- The single-player ship selection stays centred on the old window after the window turns.
- The multiplayer join screen keeps the size it had when it opened, so after a turn it is cut off. On a 360 dp wide phone window, its four slot panels are squeezed until the text wraps letter by letter.

On the Android screens that have them, the nickname, address and device-name boxes are hidden under the on-screen keyboard while players type.

## What Changes

- **No orientation restriction on any device.** Phones, tablets, foldables, Chromebooks and TVs follow the device's rotation, in portrait and in landscape. The system's rotation lock is respected. `buildozer.spec` allows all four orientations, and the game asks for nothing narrower.
- **Two touch players sit at the short edges.** On a screen with two touch seats (a phone), the seats are left and right on a wide window, as today, and top and bottom on a tall one. Either way each player holds a short end and has its full width for joystick and FIRE. The seats follow the window's shape while nobody sits in them; a seated player keeps their edge. Four-seat screens are unchanged.
- **Every screen fits the window and follows it**, down to a 360 dp wide phone held upright:
  - On a narrow window the join screen shows its four slot panels in two rows of two, and its bottom row in two lines.
  - The join screen re-fits its panels, touch strips and bottom row whenever the window changes, and the single-player ship selection re-centres.
  - The players already joined keep their slots, colours, ready state and seats.
- The game field, the touch controls, the status blocks and the Pause buttons already follow a window that changes size; that becomes a requirement with tests. In a network game, a host whose window changes shape sends the new field size, and clients re-fit it as they already do.
- **Keyboard and gamepad players' lives and points fit a phone held upright.** Along the top of a window narrower than 600 dp they show lives above points, two per row, instead of four one-line blocks in quarters that overlap and run off the screen. With touch players at the top and bottom of a phone, they sit beside the middle of the free left and right edges instead of the corners, which the touch players' controls need.
- **Touch controls use the free corners.** With a top or bottom touch seat taken, every seat's joystick and FIRE are kept near the middle of its edge, leaving the corners empty even when nobody needs them. A seat with no touch player at the edges crossing it now puts its controls in the corners of its edge, except a corner holding a keyboard or gamepad player's lives and points. With crossing seats, the layout is unchanged. The controls follow when a touch player joins or leaves during a game.
- **The Pause button sits with the player's controls.** Today it is on the inner side of the controls, next to the lives and points (in single player under the lives and points at the top). It moves to the middle of the player's edge between joystick and FIRE, with its outer side in line with the controls' outer side; in single player that is the bottom middle. If the controls leave no room between them (very large controls), it stays where it is now.
- **A client's field uses its screen.** A device showing another device's game turns the host's field a quarter when that shows it bigger, so a TV's landscape field fills a phone held upright. The field keeps its biggest size and moves within the spare room; this device's touch controls, Pause and lives and points go into that room where they fit, and other players' lives and points sit in the top-left corner, or the corner farthest from the touch controls. Every join screen offers the same touch seats; a phone also offers one long-edge seat (the bottom held horizontally, the right held upright), for one player holding it with both thumbs.
- **The top row of lives and points stays clear of side touch seats** (a left touch player's joystick ran into player 1's block).
- **Text boxes stay visible above the on-screen keyboard**: the nickname for the leaderboard, the host address and the device name.
- The README describes playing in portrait. It also suggests turning on the system rotation lock for touch games, so a turn mid-game does not move every player's controls to another edge.

## Capabilities

### New Capabilities

- `screen-adaptation`: no orientation restriction, every screen and the running game fitting and following the window, and text boxes staying visible above the on-screen keyboard.

### Modified Capabilities

- `pause`: "Pause button" is placed between the player's joystick and FIRE, lined up with the controls' outer side, instead of next to the lives and points.

- `local-multiplayer`:
  - "Touch seats": the two seats of a phone are at the short edges, top and bottom on a tall window.
  - "Four touch seats on a big screen": a smaller screen's two seats are the short edges, not always left and right.
  - "Touch layout per side": controls go into the corners of their edge when no seat crosses it and no lives and points are there.
  - "Players are told apart on screen": keyboard and gamepad players' blocks go two per row on a narrow window and beside the sides with top and bottom touch seats on a phone.

## Impact

- `buildozer.spec`: `orientation = landscape, portrait, landscape-reverse, portrait-reverse`. No Java or `jnius` code: SDL asks for `FULL_USER` by itself.
- `main.py`:
  - `touch_seats()` picks the short edges from the window's shape.
  - `JoinScreen` builds its strips for any seat set, re-fits on `Window.size` (two-by-two panels and a two-line bottom row on narrow windows), and re-chooses empty seats when the window changes shape.
  - `ShipSelectScreen` follows `Window.size`.
  - `SpaceshipStatus.pause_center` places Pause from the player's controls instead of from the lives and points.
  - `Window.softinput_mode = 'below_target'`.
- `tests/`:
  - resize tests for every screen, including 360 x 800 dp;
  - the join screen with players, strips and four seats;
  - a running touch game with top and bottom players on a tall phone window;
  - a network host's window turning.
- `README.md`: playing in portrait, the phone's touch seats, the rotation-lock tip, and a history line.
- Play Console: with no restriction left, the large-screen notice is expected to clear with the next release.
