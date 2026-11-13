# Spec Delta

## MODIFIED Requirements

### Requirement: Touch seats
Players on the touch screen SHALL sit at the edges of the screen, facing the centre: at most two at the short edges of the window (left and right on a wide window, top and bottom on a tall one), or on a big enough screen at most four, one per edge (left, right, top, bottom). While no touch player sits, the two seats SHALL move to the short edges when the window changes shape; a seated player SHALL keep their edge. A player who joins by touch SHALL sit at the edge whose join strip they tapped, and the joined slot SHALL name that side. Every text and control of a seat (join strip label, FIRE label, status block, Pause button) SHALL read upright from that seat: left turned −90°, right 90°, top 180°, bottom upright.

#### Scenario: Touch players take their side
- **WHEN** one player taps the right strip and then another taps the left strip
- **THEN** player 1's slot shows "Touch · right side" and player 2's slot "Touch · left side"

#### Scenario: Side freed by leaving
- **WHEN** the left touch player leaves
- **THEN** the left strip can be tapped again

#### Scenario: Top strip reads from the top seat
- **WHEN** the join screen shows four touch strips
- **THEN** the top strip's label is turned half a circle, so it reads upright for a player sitting at the top edge, and the bottom strip's label is upright

#### Scenario: Phone held upright
- **WHEN** the join screen opens on a phone held in portrait
- **THEN** "Tap to join by touch" strips are shown at the top and bottom edges, and a player who taps the top strip gets "Touch · top side"

#### Scenario: Empty seats follow a turn
- **WHEN** nobody sits by touch on a phone's join screen in landscape and the phone turns to portrait
- **THEN** the strips move from the left and right edges to the top and bottom edges

#### Scenario: Seated player keeps the edge
- **WHEN** a touch player sits at the left edge on a phone's join screen in landscape and the phone turns to portrait
- **THEN** the player keeps the left seat, with the strip still at the left edge

### Requirement: Four touch seats on a big screen
A screen SHALL count as big enough for four touch seats when its landscape size is at least 15 cm wide and 10 cm high, measured physically, not in pixels. The check SHALL be automatic, with no setting. On a big enough screen there SHALL be four touch seats, one per screen edge: left, right, top and bottom. On a smaller screen there SHALL be only the two seats at the short edges of the window: left and right on a wide window, top and bottom on a tall one.

#### Scenario: Tablet offers four seats
- **WHEN** the join screen opens on a tablet whose screen is 21 cm × 13 cm
- **THEN** "Tap to join by touch" strips are shown at the left, right, top and bottom edges

#### Scenario: Phone keeps two seats
- **WHEN** the join screen opens on a phone whose screen is 15 cm × 7 cm, held in landscape
- **THEN** strips are shown only at the left and right edges, as before

#### Scenario: Small tablet keeps two seats
- **WHEN** the join screen opens on a tablet whose screen is 15.5 cm × 8.7 cm, held in landscape
- **THEN** strips are shown only at the left and right edges

#### Scenario: Tablet held upright keeps four seats
- **WHEN** the join screen opens on a tablet whose screen is 13 cm × 21 cm, held in portrait
- **THEN** strips are shown at all four edges

### Requirement: Touch layout per side
A touch player's joystick and FIRE SHALL be at the two ends of their edge, the joystick under the left hand and FIRE under the right hand as seen from the seat: left side joystick at the top and FIRE at the bottom, right side FIRE at the top and joystick at the bottom, bottom side joystick at the left and FIRE at the right, top side FIRE at the left and joystick at the right. The "FIRE" label SHALL read upright from the seat. The controls SHALL keep a margin to the screen edges and SHALL NOT overlap the controls of any other seat. When only the left and right seats are taken, their controls SHALL reach into the bottom corners as before; when a top or bottom seat is taken, every seat SHALL have its two controls centred on the middle of its edge and as far apart as the screen allows. A seat with no touch seat taken at the edges crossing it (and, on a phone, no keyboard or gamepad players' status blocks beside the left and right edges) SHALL have its controls in the corners of its edge. Otherwise every seat SHALL have its two controls the same distance apart, so the controls at the short edges reach the corners (the left and right ones on a wide screen, the top and bottom ones on a tall screen). A corner holding a keyboard or gamepad player's status block SHALL stay free of touch controls; the other corners SHALL NOT be kept free. The controls SHALL follow when a touch player joins or leaves during the game. All controls SHALL fit, made smaller if needed, with the joystick and FIRE kept in their order.

#### Scenario: Both touch sets visible
- **WHEN** a game starts with two touch players at the left and right
- **THEN** on the left side FIRE is in the bottom-left corner and the joystick at the top of that side, on the right side the joystick is in the bottom-right corner and FIRE at the top of that side, and none touches the screen edges

#### Scenario: Four touch sets visible
- **WHEN** a game starts with four touch players on a big enough screen
- **THEN** the bottom player has the joystick left and FIRE right of the middle of the bottom edge, the top player FIRE left and the joystick right of the middle of the top edge, the gap between joystick and FIRE is the same on all four edges, and no two controls overlap or touch the screen edges

#### Scenario: Side controls in the corners of a wide screen
- **WHEN** a game starts with four touch players on a 21 cm × 13 cm screen
- **THEN** the left and right players' joystick and FIRE are in the corners of their sides, and the top and bottom players' joystick and FIRE are the same distance apart around the middle of their edges

#### Scenario: Top and bottom controls in the corners of a tall screen
- **WHEN** a game starts with four touch players on a screen held upright, 13 cm wide and 21 cm high
- **THEN** the top and bottom players' joystick and FIRE are in the corners of their edges, and the left and right players' joystick and FIRE are the same distance apart around the middle of their sides

#### Scenario: Corners kept for a keyboard player
- **WHEN** a game starts with touch players at the left and top and keyboard set 1 as player 3
- **THEN** no touch control is in a screen corner

#### Scenario: Large controls with four seats
- **WHEN** the touch controls size is 400% and a game starts with four touch players on a 15 cm × 10 cm screen
- **THEN** the controls are reduced so that all eight fit on screen without overlapping

#### Scenario: Bottom player with a keyboard player
- **WHEN** a game runs on a 21 cm × 13 cm screen with keyboard set 1 as player 1 and a touch player at the bottom as player 2
- **THEN** the touch player's joystick is in the bottom-left corner and FIRE in the bottom-right corner, with the Pause button between them, and player 1's block stays in the top-left corner

#### Scenario: Top and bottom players without crossing seats
- **WHEN** a game runs on a 21 cm × 13 cm screen with touch players at the top and bottom only
- **THEN** both players' joystick and FIRE are in the corners of their edges, and no two controls overlap

#### Scenario: Corner of the edge kept for lives and points
- **WHEN** a game runs on a 21 cm × 13 cm screen with a touch player at the bottom as player 1, a gamepad player as player 2 and keyboard set 1 as player 3
- **THEN** the touch player's joystick and FIRE keep clear of player 3's block in the bottom-left corner, the same distance from the middle of the edge on both sides

#### Scenario: A seat at a crossing edge joins
- **WHEN** a touch player sits at the bottom with the controls in the bottom corners and another touch player joins at the left during the game
- **THEN** the bottom player's controls move away from the corners, clear of the left player's controls, lives and points

### Requirement: Players are told apart on screen
During a multiplayer game each player's lives and points SHALL be shown in a separate status block tinted with the colour of that player's cabin. A touch player's block SHALL be at the middle of their edge, next to their own touch controls on the inner side, turned to read upright from the seat, and SHALL NOT overlap any touch controls at any screen size or touch control size. Keyboard and gamepad players' blocks SHALL be upright along the top edge in player order, except when a top or bottom touch seat is taken: then they SHALL be upright in the screen corners (player 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right). On a window narrower than 600 dp, the blocks along the top edge SHALL show lives above points, two blocks per row in player order. On a two-seat screen whose touch seats are at the top and bottom, the keyboard and gamepad players' blocks SHALL be upright beside the middle of the left and right edges instead of the corners (player 1 left above, 2 right above, 3 left below, 4 right below), and the touch players' controls SHALL keep their whole edges. No block SHALL overlap another block or any touch control.

#### Scenario: Mixed status blocks
- **WHEN** a game runs with two touch players on the left and right, a keyboard player and a gamepad player
- **THEN** the touch players' blocks are at the middle of the left and right sides next to their controls, turned toward them, and the other two blocks are upright at the top in player order, all in their cabin colours

#### Scenario: No overlap on a phone
- **WHEN** a two-touch-player game runs on a phone-sized screen with the touch controls at 100% or at a larger size
- **THEN** each touch player's lives and points are fully beside, not on top of, their joystick and FIRE button

#### Scenario: Four touch players
- **WHEN** a game runs with four touch players on a 15 cm × 10 cm screen with the touch controls at 100%, 50% or 400%
- **THEN** each block is at the middle of its edge, inside that player's controls and turned toward them, and no block or Pause button overlaps any joystick, FIRE button or other block

#### Scenario: Keyboard player with a top touch seat
- **WHEN** a game runs with touch players at the top and left and keyboard set 1 as player 3
- **THEN** player 3's block is upright in the bottom-left corner and overlaps no touch control

#### Scenario: Gamepad players on a phone held upright
- **WHEN** a game with two gamepad players and two keyboard sets runs on a 360 x 800 dp phone, with points up to 12345
- **THEN** the four blocks are at the top, two per row, each with lives above points, all inside the window and none overlapping another

#### Scenario: Touch player at the top of a phone with a gamepad player
- **WHEN** a game runs on a phone with a touch player at the top as player 1 and a gamepad player as player 2, held upright or turned to landscape after the seat was taken
- **THEN** player 2's block is upright beside the middle of the right edge, the touch player's joystick and FIRE do not overlap and keep their whole top edge, and no block overlaps any control
