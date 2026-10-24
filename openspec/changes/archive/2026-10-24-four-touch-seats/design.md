# Design

## Context

See proposal.md for motivation and specs/local-multiplayer/spec.md for the required behaviour.

Today a touch seat is a string `'left'` / `'right'` (`TOUCH_SIDES` in `main.py`) carried through the device tuple `('touch', side)`, `ControlsManager.side`, `ScreenButtonsLayout.side` and `SpaceshipStatus.side`. Rotation is hard-coded as `-90 if side == 'left' else 90` in several places: `ScreenButtonsLayout._layout_side`, `SideJoinButton._redraw` and the `SpaceshipStatus` rules in `spacepilgrim.kv`. `SpaceshipStatus.side` also uses `'top'` to mean "keyboard or gamepad player, upright row along the top", which clashes with a top touch seat. `_layout_side` lets the left and right columns run from the bottom margin up to just under the 40 dp status row, so they fill the bottom corners and the top end of each edge.

## Goals / Non-Goals

**Goals:**
- One seat model for four edges, so the layout, rotation and labels come from one table instead of `left`/`right` branches.
- Keep the two-seat layout (left/right only) exactly as it is today on every screen, so the existing tests keep passing unchanged.

**Non-Goals:**
- More than four players in total, or more than one touch player per edge.
- Portrait orientation (the app stays landscape).
- Turning the join screen panels, pause screen or results screen toward the seats; they stay upright.

## Decisions

### Seat table
Add `SEAT_ANGLES = {'bottom': 0, 'right': 90, 'top': 180, 'left': -90}` and derive `TOUCH_SIDES` per screen: `('left', 'right')` normally, `('left', 'right', 'top', 'bottom')` on a big screen. Every rotation (FIRE label, joystick `angle`, join strip label, status block, Pause button) reads `SEAT_ANGLES[side]`. The joystick's existing `_turn` already rotates by any angle, so 180° and 0° work without new maths.

*Alternative:* keep `if/else` branches per side. Rejected: four sides × five places is where mistakes would come from.

### Big-screen check
A module function `four_seat_screen()` returns whether the window is at least 15 cm × 10 cm (landscape width × height). Size in cm is `pixels / dpi * 2.54`.
- On Android, read `DisplayMetrics.xdpi` / `ydpi` through `jnius` (the same way `has_touchscreen()` asks the activity), because Kivy's `Metrics.dpi` comes from the density bucket and can be off by 20% or more, which matters near the threshold.
- Elsewhere, or if the Android call fails, use `Metrics.dpi`. On a desktop this usually gives four seats, which is handy for trying the layout with a mouse.

The thresholds are module constants (`FOUR_SEAT_MIN_CM = (15, 10)`) and the function is patched in tests. It is evaluated when `show_ship_select` creates the `JoinScreen` (passed in as `seats=`), and the chosen seats are kept for the game; the app does not change size mid-session in landscape.

*Why 15 × 10 cm:* the four-edge layout at 100% control size needs about 525 dp of height (two corner bands + stick + FIRE + gaps, see below), which is about 8.4 cm. 10 cm leaves room for the status blocks and Pause buttons. It includes 8" and larger tablets and excludes phones (≈ 15 × 7 cm) and 7" tablets (≈ 15.5 × 8.7 cm).

### Two layouts for touch controls
`ScreenButtonsLayout` gets a `corners` flag next to `side`:
- `corners=False` (only left/right touch seats in the game): today's `_layout_side`, unchanged.
- `edges=True` (a top or bottom seat is taken): the new `_layout_edge`. (Final version, after review: every seat's two controls sit the same distance `half` either side of the middle of its edge. `half` is as large as allowed: the left/right controls may go to the screen margin, the top/bottom pairs must stay clear of the left/right column `m + s + STATUS_DP`, and only when a keyboard/gamepad player is in the game (`free_corners`) must everything keep out of the `CORNER_DP` corner squares. The rule follows the short edges, not left/right: on a tall (portrait) screen the top and bottom controls go to the corners and the left/right pairs stay clear of the top/bottom row. (The Android build is landscape-only; portrait matters for desktop windows and any later orientation change.) So on a wide screen the side controls are in the corners like the two-seat layout, and the shrink factor is the biggest `k` with `half(k) ≥ k·max(s, f) + pause/2`. The rest of this bullet list describes the first version.) Each seat uses the band of its edge, depth `m + s` (margin + stick size). The four corner squares of size `C = max(m + s, CORNER_MIN)` stay free. The left and right seats' two controls sit at the two ends of the stretch between the corners: left = stick top / FIRE bottom; right = FIRE top / stick bottom. The top and bottom seats use the same span, centred on the middle of their long edge, so every seat has its controls the same distance apart: bottom = stick left / FIRE right; top = FIRE left / stick right. (Changed after review: at first top and bottom used the ends of the long edge, which put their controls much further apart than the side players'.)
- The controls shrink by one factor `k ≤ 1` for all seats, the biggest that fits, found by bisection. The status text and Pause button sit at the middle of the edge, so each half of an edge must hold the bigger control: `2·(C + g) + 2·k·max(s, f) + pause_room ≤ H`. (Found during implementation: `k·(s + f)` let the Pause button touch the joystick at 300–400%.)
- The top and bottom seats' controls start further in than the corner, past the left/right players' status text column (`m + s + STATUS_DP`), and the same check applies along the width. Without this, at large control sizes the long rotated lives/points text of the left/right players reached the bottom/top joystick.
- `CORNER_MIN` (`CORNER_DP`, 140 dp) is big enough for a two-line upright keyboard status block.

`game_start` sets `corners` on every touch player's `ControlsManager` when any joined touch seat is `top` or `bottom`.

*Alternative:* always use the corner-free layout on a big screen. Rejected: with only left/right touch players it would make their controls smaller for no reason, and it would change today's two-player games on desktops and tablets.

### Status blocks
- Split `SpaceshipStatus.side` into `side` (seat: `''`, `left`, `right`, `top`, `bottom`, or `'row'` for keyboard/gamepad players) plus a `corner` mode for keyboard/gamepad players when `corners` is on. This removes the `'top'` clash.
- Touch seat blocks: `follow()` already sets `inset` from the controls. For top/bottom it measures the distance from that edge to the inner side of the stick, and the kv rules place the block at `Window.width / 2`, `inset` from the edge, rotated by `SEAT_ANGLES[side]`. The Pause button goes on the screen-edge side of the text, in the free stretch between that seat's stick and FIRE, as for left/right today.
- The kv expressions are already long one-liners. The placement moves to a Python method, `SpaceshipStatus.place_label(label)` / `place_pause(button)`, bound to size, inset and texture changes, and the kv keeps only the static styling. This also makes the overlap tests simpler.
- Keyboard/gamepad blocks in `corner` mode: upright, two lines ("Lives N" / "Points N"), centred in the corner square chosen by slot (0 TL, 1 TR, 2 BL, 3 BR). Slots are unique, so blocks never share a corner.

### Join screen
- `SideJoinButton` takes any seat. Left/right stay vertical strips. Top/bottom are horizontal strips of height `STRIP_WIDTH`; the label is not swapped to (h, w) and is turned by `SEAT_ANGLES[side]`.
- With four seats, `JoinScreen` fills the window (minus 5 dp per edge) and nests: horizontal `[left strip, centre column, right strip]`, centre column vertical `[top strip, spacer, panels + Back row, spacer, bottom strip]`. The panels keep their `dp(450)` height cap, so on a tablet they stay the same size as today. With two seats the layout stays as it is.
- `device_label` already formats `'Touch · {} side'`. The empty-slot hint becomes "tap an edge of the screen" when there are four seats.

## Risks / Trade-offs

- [The Android dpi is wrong on some devices] → Prefer `xdpi`/`ydpi`, fall back to `Metrics.dpi`. A wrong answer only means two seats on a big tablet or four tight seats on a near-threshold device; the layout still shrinks to fit and never overlaps.
- [Four players' fingers on one tablet: many simultaneous touches] → Kivy and Android support 10+ touch points; each control already grabs its own touch, so eight controls work independently. Check on a real tablet.
- [More code paths in the kv placement] → Moving the placement into Python with one function per seat keeps the logic in one place and makes it testable without kv tricks.
- [Desktop now shows four strips] → Only affects development/desktop builds. Existing tests set a two-seat screen through the patched `four_seat_screen()`, so they are unchanged.

## Migration Plan

No saved data changes. Seat strings in device tuples (`('touch', 'top')`) are new values of an existing field, so `last_config` / "Play again" keeps working. Rollback is reverting the commit.
