# Spec Delta

## MODIFIED Requirements

### Requirement: Join with a device
The join screen SHALL show four player slots. Pressing FIRE on a keyboard set or gamepad that has not joined SHALL take the first free slot with that device. On a device with a touchscreen, or once the game has received a touch, the join screen SHALL show a "Tap to join by touch" strip at the edge of each open touch seat (see Touch seats). Activating a strip SHALL take the first free slot with touch as a player at that seat. On a device without a touchscreen that has received no touch (such as Android TV), the strips SHALL NOT be shown. A keyboard set or gamepad SHALL hold at most one slot. There SHALL be two keyboard sets, so at most two players play on one keyboard.

#### Scenario: Two touch players at most
- **WHEN** two players have joined by touch on a screen that is not big enough for four touch seats
- **THEN** both side strips are disabled and name the player on that side until one of them leaves

#### Scenario: Four touch players on a big screen
- **WHEN** four players have joined by touch on a big enough screen, one at each edge
- **THEN** all four strips are disabled and each names the player at that edge, and the game can start with four touch players

#### Scenario: Keyboard set joins
- **WHEN** nobody has joined and someone presses Space
- **THEN** player 1's slot shows "Keyboard 1", with its keys W A D Space in the hint below

#### Scenario: Gamepad joins the next slot
- **WHEN** keyboard set 1 holds player 1's slot and a gamepad presses its fire button
- **THEN** player 2's slot shows that a gamepad has joined

#### Scenario: Touch joins a chosen slot
- **WHEN** player 1 has joined by keyboard and a player taps the strip at the right edge
- **THEN** player 2's slot shows "Touch · right" and the other slots are unchanged

#### Scenario: Touch joins at the top
- **WHEN** player 1 has joined by keyboard on a big enough screen and a player taps the strip at the top edge
- **THEN** player 2's slot shows "Touch · top"

#### Scenario: A device joins once
- **WHEN** keyboard set 1 has joined and Space is pressed again
- **THEN** no other slot is taken and player 1 toggles ready

#### Scenario: No strips on a TV
- **WHEN** the join screen opens on an Android TV without a touchscreen
- **THEN** no "Tap to join by touch" strip is shown and the empty slots only ask for FIRE on keys or a gamepad

#### Scenario: Strips appear on the first touch
- **WHEN** the join screen is open on a device without a touchscreen and the game receives a touch
- **THEN** the "Tap to join by touch" strips of all touch seats appear

#### Scenario: Short texts on a narrow panel
- **WHEN** the join screen opens on a 360 x 640 dp phone with a touch player at the right edge and keyboard set 1 joined
- **THEN** the slots show "Touch · right" and "Keyboard 1" whole, and the empty slots "Press FIRE on keys or a gamepad" and "or tap an edge to play by touch" inside their panels

### Requirement: Touch seats
Players on the touch screen SHALL sit at the edges of the screen, facing the centre, with the same seats on every join screen (a local game, a hosted one, one joined from another device, and the "Tap to join" strips while watching): on a big enough screen one per edge (left, right, top, bottom); else the two short edges, for two players facing each other, and one long edge, for one player holding the device with the joystick and FIRE under the thumbs: on a wide window left, right and bottom; on a tall window top, bottom and right (where a player's bottom is who turns the phone sideways, top to the left, while the screen stays upright). The long-edge seat and the short-edge seats SHALL NOT be taken together. While no touch player sits, the seats SHALL follow the window when it changes shape; a seated player SHALL keep their edge. A player who joins by touch SHALL sit at the edge whose join strip they tapped, and the joined slot SHALL name that side. Every text and control of a seat (join strip label, FIRE label, status block, Pause button) SHALL read upright from that seat: left turned −90°, right 90°, top 180°, bottom upright.

#### Scenario: Touch players take their side
- **WHEN** one player taps the right strip and then another taps the left strip
- **THEN** player 1's slot shows "Touch · right" and player 2's slot "Touch · left"

#### Scenario: Side freed by leaving
- **WHEN** the left touch player leaves
- **THEN** the left strip can be tapped again

#### Scenario: Top strip reads from the top seat
- **WHEN** the join screen shows four touch strips
- **THEN** the top strip's label is turned half a circle, so it reads upright for a player sitting at the top edge, and the bottom strip's label is upright

#### Scenario: Phone held upright
- **WHEN** the join screen opens on a phone held in portrait
- **THEN** "Tap to join by touch" strips are shown at the top, bottom and right edges, and a player who taps the top strip gets "Touch · top" and the right strip is hidden

#### Scenario: Phone held horizontally by one player
- **WHEN** the join screen opens on a phone held in landscape and a player taps the bottom strip
- **THEN** the player gets "Touch · bottom", the left and right strips are hidden, and in the game their joystick is in the bottom-left and FIRE in the bottom-right corner

#### Scenario: Side player closes the bottom seat
- **WHEN** a player taps the left strip on a phone held in landscape
- **THEN** the bottom strip is hidden and the right strip can still be tapped; when the player leaves, the bottom strip is shown again

#### Scenario: Phone joining a TV
- **WHEN** a phone held in landscape opens the join screen of a TV's game, or watches it running
- **THEN** "Tap to join" strips are at its left, right and bottom edges, as on its own join screen

#### Scenario: Empty seats follow a turn
- **WHEN** nobody sits by touch on a phone's join screen in landscape and the phone turns to portrait
- **THEN** the strips move from the left, right and bottom edges to the top, bottom and right edges

#### Scenario: Phone turned sideways with the screen upright
- **WHEN** a player taps the right strip of a phone held in portrait
- **THEN** the top and bottom strips are hidden, and in the game the player's joystick is at the bottom and FIRE at the top of the right edge

#### Scenario: Seated player keeps the edge
- **WHEN** a touch player sits at the left edge on a phone's join screen in landscape and the phone turns to portrait
- **THEN** the player keeps the left seat, with the strip still at the left edge

### Requirement: Four touch seats on a big screen
A screen SHALL count as big enough for four touch seats when its landscape size is at least 15 cm wide and 10 cm high, measured physically, not in pixels. The check SHALL be automatic, with no setting. On a big enough screen there SHALL be four touch seats, one per screen edge: left, right, top and bottom. On a smaller screen there SHALL be the seats at the short edges of the window and one long-edge seat (see Touch seats).

#### Scenario: Tablet offers four seats
- **WHEN** the join screen opens on a tablet whose screen is 21 cm × 13 cm
- **THEN** "Tap to join by touch" strips are shown at the left, right, top and bottom edges

#### Scenario: Phone keeps two seats
- **WHEN** the join screen opens on a phone whose screen is 15 cm × 7 cm, held in landscape
- **THEN** strips are shown at the left, right and bottom edges, not at the top

#### Scenario: Small tablet keeps two seats
- **WHEN** the join screen opens on a tablet whose screen is 15.5 cm × 8.7 cm, held in landscape
- **THEN** strips are shown at the left, right and bottom edges, not at the top

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
During a multiplayer game each player's lives and points SHALL be shown in a separate status block tinted with the colour of that player's cabin. A touch player's block SHALL be at the middle of their edge, next to their own touch controls on the inner side, turned to read upright from the seat, and SHALL NOT overlap any touch controls at any screen size or touch control size. Keyboard and gamepad players' blocks SHALL be upright along the top edge in player order, except when a top or bottom touch seat is taken: then they SHALL be upright in the screen corners (player 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right). On a window narrower than 600 dp, the blocks along the top edge SHALL show lives above points, two blocks per row in player order. On a two-seat screen whose touch seats are at the top and bottom, the keyboard and gamepad players' blocks SHALL be upright beside the middle of the left and right edges instead of the corners (player 1 left above, 2 right above, 3 left below, 4 right below), and the touch players' controls SHALL keep their whole edges; when the game starts on a wide window with only a bottom touch player, the blocks SHALL be along the top edge instead and the bottom player's controls in the corners of the bottom edge. No block SHALL overlap another block or any touch control.

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

#### Scenario: Keyboard player with a left touch seat
- **WHEN** a game runs at 800 x 360 dp with keyboard set 1 as player 1 and a touch player at the left
- **THEN** player 1's block is at the top and the left player's joystick starts below it, without overlapping

#### Scenario: Gamepad players on a phone held upright
- **WHEN** a game with two gamepad players and two keyboard sets runs on a 360 x 800 dp phone, with points up to 12345
- **THEN** the four blocks are at the top, two per row, each with lives above points, all inside the window and none overlapping another

#### Scenario: Phone held horizontally with a gamepad player
- **WHEN** a game starts on a phone held in landscape with a gamepad player, a touch player at the bottom and a keyboard player
- **THEN** the gamepad and keyboard players' blocks are along the top edge, and the touch player's joystick and FIRE are in the bottom corners with Pause between them

#### Scenario: Touch player at the top of a phone with a gamepad player
- **WHEN** a game runs on a phone with a touch player at the top as player 1 and a gamepad player as player 2, held upright or turned to landscape after the seat was taken
- **THEN** player 2's block is upright beside the middle of the right edge, the touch player's joystick and FIRE do not overlap and keep their whole top edge, and no block overlaps any control
