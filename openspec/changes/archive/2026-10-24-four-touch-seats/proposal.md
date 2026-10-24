# Proposal

## Why

Multiplayer already has four slots, but only two of them can be touch players (left and right side), so four people around one tablet still need a keyboard or gamepads. A tablet lying on a table has room for a player at every edge, so on a screen that is big enough all four players should be able to play by touch.

## What Changes

- On a screen that is physically big enough (tablet size), the game offers two more touch seats: **top** and **bottom**, on the long edges. Together with the existing left and right seats, up to four players play by touch, one per edge, all facing the centre.
- The size check is automatic: no setting. On phone-sized screens nothing changes (two touch seats, left and right).
- The join screen shows "Tap to join by touch" strips at the top and bottom edges as well when four seats are available; the top strip reads upright from the top seat (turned half a circle).
- In a game with a top or bottom touch player:
  - Each seat's joystick is under the player's left hand and FIRE under the right hand as seen from that seat (bottom: joystick bottom-left, FIRE bottom-right; top: joystick top-right, FIRE top-left), with the joystick and the FIRE label turned toward the seat.
  - The four seats share the screen edges without overlap: the corners are left free, so the left/right controls move in from the corners and the top/bottom controls stay between them.
  - The top/bottom player's lives and points block (and Pause button) sits at the middle of their edge, just inside their controls, reading upright from their seat.
  - Keyboard and gamepad players' status blocks stay upright along the top, but move below the top seat's controls when the top seat is taken.
- Two-touch-player games on any screen keep today's layout.
- Up to four players in total, as before (no change to `MAX_PLAYERS`).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `local-multiplayer`: the touch seat requirements change — join strips for top and bottom on big screens, up to four touch players, per-seat layout of the controls and status blocks for four edges, joystick turned to the top and bottom seats.

## Impact

- `main.py`: seat constants (`TOUCH_SIDES`), a physical screen-size check, `ScreenButtonsLayout` layout for four seats, `Joystick` / `FireButton` angles for top (180°) and bottom (0°), `SideJoinButton` horizontal orientation, `JoinScreen` layout and labels, `SpaceshipStatus` placement, `game_start` seat handling.
- `spacepilgrim.kv`: `SpaceshipStatus` label and Pause button placement and rotation for top/bottom seats and for keyboard blocks under a taken top seat.
- `tests/test_game.py`: new tests for the size check, four-seat join, layout without overlap at several screen sizes and control scales, joystick directions per seat.
- No new dependencies; Android TV and phones unaffected.
