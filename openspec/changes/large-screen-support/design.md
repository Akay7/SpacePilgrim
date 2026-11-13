# Design

## Context

See proposal.md for the motivation and the specs for the behaviour (`specs/screen-adaptation/spec.md`, and the `local-multiplayer` delta). Observed state:

- **Where the restriction comes from.** p4a writes `KIVY_ORIENTATION="LandscapeLeft LandscapeRight"` from `buildozer.spec`. Kivy's SDL2 window passes it to `SDL_HINT_ORIENTATIONS` when it creates the window. SDL's `SDLActivity.setOrientationBis` turns it into `setRequestedOrientation(SENSOR_LANDSCAPE)`. With all four orientations in the hint and a resizable window (Kivy's default `graphics.resizable = 1`, which the game keeps), SDL asks for `FULL_USER`: every orientation, following the user's rotation lock. The manifest stays `screenOrientation="unspecified"`.
- **Activity restarts.** The manifest's `configChanges` already lists `orientation|screenSize|smallestScreenSize|screenLayout`, so a turn or an unfold resizes the SDL window instead of restarting the activity. Kivy then updates `Window.size`.
- **Screens that already follow the window:**
  - The kv screens (menu, pause, results, nickname, leaderboard, settings pages, address) are centred with expressions on `Window.size`.
  - `NetworkScreen`, `JoinPrompt` and `FieldView` bind `Window.size`.
  - `ScreenButtonsLayout` is sized to `Window.size` in kv and lays out again on `size`. That covers the touch controls, the status blocks and the Pause buttons, and a rotated four-player tablet game re-lays itself out correctly. `_layout_edge` already puts the controls of the short edges in the corners, whichever edges those are.
- **Screens that do not:**
  - `ShipSelectScreen` centres itself only when its own size or parent changes.
  - `JoinScreen` computes its size, the middle column's width and, with four seats, its height once in `__init__`. It assumes left and right strips always exist, and treats "a top seat exists" as "four seats" (`four = 'top' in seats`).
- **Seats.** `touch_seats()` returns `TOUCH_SIDES = ('left', 'right')` or `FOUR_SEATS` from the physical screen size (`four_seat_screen`, which already ignores orientation). `_seat_layout` switches every touch player to the edge layout as soon as a top or bottom seat is taken.
- **The field** is `Window.size`. Objects wrap at it every frame, and the host sends `field` in every snapshot.

## Goals / Non-Goals

**Goals:**
- No orientation request narrower than SDL's `FULL_USER`, on any device.
- Every screen usable at 360 x 800 dp.
- One rule for every screen: follow `Window.size`.

**Non-Goals:**
- Moving seated touch players with the device's physical rotation (see Risks).
- Scaling the game field or sprites with the window: they stay in pixels, as today.
- Locking the orientation during a game. Android 16 would ignore that on large screens, and it would bring the Play notice back.

## Decisions

1. **All four orientations in `buildozer.spec`, and no orientation code.**
   - With `orientation = landscape, portrait, landscape-reverse, portrait-reverse`, SDL requests `FULL_USER`. That follows the rotation lock, and Play sees no restriction.
   - Alternative: keep phones in landscape with a runtime request based on the display size. The user chose no restriction anywhere; it also needs early `jnius` code and still makes a request Play might flag. Rejected.

2. **Two-seat screens sit at the short edges.**
   - `touch_seats(size=None)` returns `('left', 'right')` when the window is at least as wide as it is high, and `('top', 'bottom')` otherwise. Four-seat screens keep `FOUR_SEATS`.
   - On a tall phone, `_seat_layout` gives the top and bottom players the edge layout, which puts their controls in the corners of the short edges. It is the same arrangement players have at the left and right in landscape, so no new layout code is needed. A test proves it.
   - `JoinScreen` stops inferring "four seats" from `'top' in seats`. It builds a strip for each seat: left and right strips in the row, top and bottom strips in the middle column.
   - Alternative: keep left and right in portrait. That gives each player a long edge and leaves a field about 230 dp wide. Rejected by the user.

3. **Empty seats follow the window's shape; seated players keep theirs.**
   - On `Window.size`, a two-seat `JoinScreen` that has no touch player recomputes `touch_seats()` and rebuilds its strips when the result changed.
   - Once someone is seated, the seats stay as they are: the seated player's edge must not disappear under them. The free strip stays at the opposite edge, so a second player can sit facing them.
   - In a running game, seats never move. Only the layout follows the window.

4. **`JoinScreen` re-fits instead of rebuilding.**
   - The size computations move into `_fit()`. It runs at creation and on `Window.size` (unbound when the screen closes), then re-centres.
   - It picks the panel grid from the middle column's width: four across when there is room for four panels of at least 150 dp, otherwise two rows of two. The bottom row becomes two lines (Back and Device name, Local network and Join a network game) when the middle is narrower than 560 dp.
   - The widgets, `Lobby`, focus and the bottom-row highlight survive, because only sizes and the grid's `cols` change. The panels move between grid cells without being rebuilt.
   - Alternative: rebuild the screen on resize. That loses focus and the bottom-row state, and it costs more. Rejected.

5. **`ShipSelectScreen` binds `Window.size` to `_center`.** Its single-player width (280 dp) already fits 360 dp. The multiplayer variant is no longer used.

6. **Pause from the controls, not from the text.**
   - `SpaceshipStatus.place_pause`, called from `follow()` (which already tracks the controls for the inset, and now runs for single player too), returns the point midway between the joystick's and FIRE's centres along the edge, moved across the edge so that the button's outer side is at the joystick's outer side: `margin` from the screen edge, the same line for every control in single player and for the joystick in every seat.
   - The button is turned to the seat, so "outer side" is its bottom as the player reads it.
   - Fallback: if the gap between the joystick and FIRE along the edge is less than the button plus 8 dp on each side, Pause goes next to the lives and points instead.
     - For a touch seat it goes on the screen-centre side of the text. The old spot, on the edge side of the text, overlapped the controls on a 640 x 360 dp phone from 200% up (a bug that existed before this change), so the fallback moves away from them.
     - In single player it stays under the lives and points.
     - The fallback only happens with large controls on a small phone and two side seats, or in single player at 400%. Four seats never need it: the edge layout already shrinks the controls to leave room in the middle of each edge.
   - Single player: the controls are the joystick bottom-left and FIRE bottom-right, so Pause is at the bottom middle. The lives and points stay at the top right.
   - It re-places on the same triggers as the inset (the controls' `pos` and `size`), so it follows window changes like everything else.
   - Alternative: line it up with FIRE's outer side. FIRE is centred in the joystick's band and so sits higher than the joystick on most edges; the joystick's outer side is the line every seat shares. Rejected.

7. **Keyboard and gamepad players' lives and points on a phone held upright.**
   - Top row: below `COMPACT_DP` (600 dp) the blocks use the two-line text of the corners and sit two per row by slot (`slot % 2` across, `slot // 2` down). Four quarters of a 360 dp window are 90 dp each, while one line takes about 175 dp, and 215 dp with five-digit points. Placing by slot keeps the places fixed when players join or leave mid-game, as the quarters do.
   - New `flank` side: on a two-seat screen whose touch seats are the top and bottom ones (`_seat_layout`), keyboard and gamepad blocks go beside the middle of the left and right edges, and `free_corners` stays off. The corners are where those touch players' controls must go, and keeping them free squeezed a 360 dp edge until FIRE covered the joystick.
   - The test is the seats and the screen class (no left or right seat, not a four-seat screen), not the window's current shape. A player can sit at the top in portrait and the game can start after the phone was turned, and the layout must not collapse then.
   - The kv text asks `SpaceshipStatus.two_lines(side, Window.width)`. Importing `main` in kv would load `main.py` a second time when it runs as a script.

7a. **Touch controls take the free corners.** The edge layout used one reach for every seat and, with any keyboard or gamepad player in a corner, kept all four corners free. A bottom player alone with a keyboard player then had joystick and FIRE squeezed toward the middle of the bottom edge. Now every touch layout knows the taken seats, the corners that hold lives and points, and whether lives and points sit beside the sides (`flank`). The game shares these after every join and leave (`_share_seats`), so they come from the widgets and not from the start-of-game seat list. A seat whose crossing edges are empty reaches the corners of its edge, minus a corner with lives and points measured along the edge. With a crossing seat the old rule stays: every edge the same distance apart, the short edges in the corners. Control sizes stay common: they shrink until every taken edge fits. When the window is too small for that, the reach is at least one control and half a gap, so the joystick and FIRE never swap sides.

8. **On-screen keyboard: `Window.softinput_mode = 'below_target'`, set once at start-up.**
   - With SDL2 on Android, Kivy's `show_keyboard` then passes the focused `TextInput`'s rectangle to `SDL_SetTextInputRect`. SDL places its hidden edit view there, and Android pans the activity's window just enough to keep that rectangle above the keyboard. When the keyboard closes, the pan is undone.
   - That works in the game's fullscreen mode. `adjustResize` does not work in fullscreen, and Kivy's `resize` mode is not supported with SDL2 on Android. `Window.keyboard_height` is always 0 there, so the game cannot lay itself out around the keyboard.
   - Alternative: `pan`. It always moves the whole picture by the keyboard's height, even when the box is high on the screen. Rejected: `below_target` moves only as much as needed.
   - On the desktop the mode only affects Kivy's own virtual keyboard, which the game does not use, so it is set on every platform.

10. **A client's field turns and makes room.** `FieldView` compares the scale of the host's field as it is and turned a quarter, and turns it when that is bigger (a TV's field on a phone held upright). Steering is relative to the ship and the field holds no text, so the turn changes nothing in play; Kivy draws it with a `Rotate` between the translation and the scale, and `to_screen` follows. The field keeps its biggest size; only its place in the spare room changes. The game hands the view a function giving this device's HUD boxes (touch controls, lives and points, Pause). A box on one half of the window that starts within the spare room wants the space up to its far side; the field is then as central as leaves both sides free, or shares the room in proportion. It is placed again on the next frame after a window change or a join or leave (a `Clock` trigger), once the HUD has followed. Shrinking the field to keep the HUD off it was tried and rejected by the owner: the field stays as big as possible, and the HUD may cover its edge.

12. **A client's HUD goes beside its field.** On a client with at most one touch player, `FieldView` tells the game along which axis its spare room lies (`bands`). When that room is at the two ends of the touch player's edge (a bottom seat on a wide phone, the usual way after sitting down with the phone upright and turning it), `ScreenButtonsLayout.ends` puts the joystick and FIRE in the corners of the edge whatever else is on screen, and `SpaceshipStatus.ends` puts the lives and points beside the joystick (`along`) and Pause beside FIRE, two lines, 17 dp, so they fit the room. The other players' blocks get a `spot` (a corner and a direction): from the top-left corner, or the corner farthest from the touch controls when they are there (top seat: bottom left; left seat: top right), one after another into the room, turning the other way if the stack would reach the touch controls. With two or more touch players the local layout stays. A label whose text changes is measured again on the next frame (its `texture_size` triggers a refit).

13. **A phone joining a game held horizontally.** A phone's two seats are the short edges, made for two players facing each other. A phone that joins a TV's game is held by one player, and held horizontally the left or right seat turns the text and puts both controls on one short edge. `client_seats` adds the bottom edge to the left and right ones on a two-seat device in landscape; the client's join screen and its `JoinPrompt` use it and follow the window (`seats_for`). The prompt keeps a strip it made and only hides it, so turning a device does not create widgets. Local games keep `touch_seats`.

11. **The top row and the side seats.** The side layout kept 40 dp at the top for the row of keyboard and gamepad players' lives and points, but the row is about 70 dp deep (and the one-line row's position was in pixels, not dp), so a left seat's joystick ran into player 1's block. The layout now knows which slots are in the row (`rows`) and keeps room for the deepest of them: one line on a wide window, two lines two per row on a narrow one.

9. **Network.** Nothing new: the host's snapshots carry `field`, and `FieldView` re-fits on `set_field` and on its own `Window.size`. A client's touch seats are its own window's, chosen by the same rule. Tests cover a host resize and a client resize.

## Risks / Trade-offs

- [A device turned during a touch game moves every seated player's controls to another physical edge] → Seats are screen edges, as today with landscape and reverse landscape. The README advises turning on the system rotation lock for touch games, and `FULL_USER` respects it. Remapping seats from `Display.getRotation()` is left for later if players ask.
- [A phone turned in the middle of one-player touch play: the field becomes narrow and tall, and objects outside it wrap] → That is the expected result of following the window. The game keeps running and the controls move to their corners.
- [The join screen on a 360 x 640 dp phone (short and narrow) may be tight with two rows of panels, two strips and a two-line bottom row] → Panels give up height first (the ship preview shrinks). A test checks that everything stays inside a 360 x 640 dp window.
- [Android may not pan in some keyboard or launcher combinations, for example with a floating keyboard] → The box is at least usable: the panned position is the one Android chooses. Check it on the phone and on the TV with a remote keyboard (task 5.2).
- [Play still flags the release] → Nothing in the game narrows the orientation any more, so this would point to something outside the game's control. Check the notice after release.

## Migration Plan

- Ship with the next release. Rolling back means restoring the `orientation` line in `buildozer.spec`; the layout changes are harmless in landscape.
- After release, check the Play Console's large-screen notice.
