# Spec Delta

## ADDED Requirements

### Requirement: Four touch seats on a big screen
A screen SHALL count as big enough for four touch seats when its landscape size is at least 15 cm wide and 10 cm high, measured physically, not in pixels. The check SHALL be automatic, with no setting. On a big enough screen there SHALL be four touch seats, one per screen edge: left, right, top and bottom. On a smaller screen there SHALL be only the left and right seats.

#### Scenario: Tablet offers four seats
- **WHEN** the join screen opens on a tablet whose screen is 21 cm × 13 cm
- **THEN** "Tap to join by touch" strips are shown at the left, right, top and bottom edges

#### Scenario: Phone keeps two seats
- **WHEN** the join screen opens on a phone whose screen is 15 cm × 7 cm
- **THEN** strips are shown only at the left and right edges, as before

#### Scenario: Small tablet keeps two seats
- **WHEN** the join screen opens on a tablet whose screen is 15.5 cm × 8.7 cm
- **THEN** strips are shown only at the left and right edges

## MODIFIED Requirements

### Requirement: Join with a device
The join screen SHALL show four player slots. Pressing FIRE on a keyboard set or gamepad that has not joined SHALL take the first free slot with that device. On a device with a touchscreen, or once the game has received a touch, the join screen SHALL show a "Tap to join by touch" strip at the edge of each touch seat: the left and right edges, and on a big enough screen also the top and bottom edges. Activating a strip SHALL take the first free slot with touch as a player at that seat. On a device without a touchscreen that has received no touch (such as Android TV), the strips SHALL NOT be shown. A keyboard set or gamepad SHALL hold at most one slot. There SHALL be two keyboard sets, so at most two players play on one keyboard.

#### Scenario: Two touch players at most
- **WHEN** two players have joined by touch on a screen that is not big enough for four touch seats
- **THEN** both side strips are disabled and name the player on that side until one of them leaves

#### Scenario: Four touch players on a big screen
- **WHEN** four players have joined by touch on a big enough screen, one at each edge
- **THEN** all four strips are disabled and each names the player at that edge, and the game can start with four touch players

#### Scenario: Keyboard set joins
- **WHEN** nobody has joined and someone presses Space
- **THEN** player 1's slot shows that keyboard set 1 (W A D Space) has joined

#### Scenario: Gamepad joins the next slot
- **WHEN** keyboard set 1 holds player 1's slot and a gamepad presses its fire button
- **THEN** player 2's slot shows that a gamepad has joined

#### Scenario: Touch joins a chosen slot
- **WHEN** player 1 has joined by keyboard and a player taps the strip at the right edge
- **THEN** player 2's slot shows "Touch · right side" and the other slots are unchanged

#### Scenario: Touch joins at the top
- **WHEN** player 1 has joined by keyboard on a big enough screen and a player taps the strip at the top edge
- **THEN** player 2's slot shows "Touch · top side"

#### Scenario: A device joins once
- **WHEN** keyboard set 1 has joined and Space is pressed again
- **THEN** no other slot is taken and player 1 toggles ready

#### Scenario: No strips on a TV
- **WHEN** the join screen opens on an Android TV without a touchscreen
- **THEN** no "Tap to join by touch" strip is shown and the empty slots only ask for FIRE on a keyboard set or gamepad

#### Scenario: Strips appear on the first touch
- **WHEN** the join screen is open on a device without a touchscreen and the game receives a touch
- **THEN** the "Tap to join by touch" strips of all touch seats appear

### Requirement: Touch seats
Players on the touch screen SHALL sit at the edges of the screen, facing the centre: at most two at the left and right sides, or on a big enough screen at most four, one per edge (left, right, top, bottom). A player who joins by touch SHALL sit at the edge whose join strip they tapped, and the joined slot SHALL name that side. Every text and control of a seat (join strip label, FIRE label, status block, Pause button) SHALL read upright from that seat: left turned −90°, right 90°, top 180°, bottom upright.

#### Scenario: Touch players take their side
- **WHEN** one player taps the right strip and then another taps the left strip
- **THEN** player 1's slot shows "Touch · right side" and player 2's slot "Touch · left side"

#### Scenario: Side freed by leaving
- **WHEN** the left touch player leaves
- **THEN** the left strip can be tapped again

#### Scenario: Top strip reads from the top seat
- **WHEN** the join screen shows four touch strips
- **THEN** the top strip's label is turned half a circle, so it reads upright for a player sitting at the top edge, and the bottom strip's label is upright

### Requirement: Players are told apart on screen
During a multiplayer game each player's lives and points SHALL be shown in a separate status block tinted with the colour of that player's cabin. A touch player's block SHALL be at the middle of their edge, next to their own touch controls on the inner side, turned to read upright from the seat, and SHALL NOT overlap any touch controls at any screen size or touch control size. Keyboard and gamepad players' blocks SHALL be upright along the top edge in player order, except when a top or bottom touch seat is taken: then they SHALL be upright in the screen corners (player 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right).

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

### Requirement: Touch layout per side
A touch player's joystick and FIRE SHALL be at the two ends of their edge, the joystick under the left hand and FIRE under the right hand as seen from the seat: left side joystick at the top and FIRE at the bottom, right side FIRE at the top and joystick at the bottom, bottom side joystick at the left and FIRE at the right, top side FIRE at the left and joystick at the right. The "FIRE" label SHALL read upright from the seat. The controls SHALL keep a margin to the screen edges and SHALL NOT overlap the controls of any other seat. When only the left and right seats are taken, their controls SHALL reach into the bottom corners as before; when a top or bottom seat is taken, every seat SHALL have its two controls the same distance apart, centred on the middle of its edge and as far apart as the screen allows, so the controls at the short edges reach the corners (the left and right ones on a wide screen, the top and bottom ones on a tall screen). The corners SHALL stay free only for keyboard or gamepad players' status blocks. All controls SHALL fit, made smaller if needed.

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

### Requirement: Joystick turned toward the seat
In a multiplayer game a touch player's joystick SHALL be turned toward their seat: pushing it away from the player, toward the centre of the screen, SHALL thrust, and pushing it to the player's own left or right, as seen from the seat, SHALL turn the ship left or right. The direction marks on the joystick SHALL be turned the same way. The single-player joystick SHALL keep screen directions.

#### Scenario: Left player pushes forward
- **WHEN** the left touch player pushes their joystick toward the screen centre (to the right on the screen)
- **THEN** their ship thrusts and does not turn

#### Scenario: Right player turns left
- **WHEN** the right touch player pushes their joystick toward the bottom of the screen, which is their left
- **THEN** their ship turns left

#### Scenario: Top player pushes forward
- **WHEN** the top touch player pushes their joystick toward the bottom of the screen
- **THEN** their ship thrusts and does not turn

#### Scenario: Top player turns right
- **WHEN** the top touch player pushes their joystick toward the left of the screen, which is their right
- **THEN** their ship turns right

#### Scenario: Bottom player uses screen directions
- **WHEN** the bottom touch player pushes their joystick up
- **THEN** their ship thrusts, like the single-player joystick
