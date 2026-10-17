# Spec Delta

## MODIFIED Requirements

### Requirement: Join with a device
The join screen SHALL show four player slots. Pressing FIRE on a keyboard set or gamepad that has not joined SHALL take the first free slot with that device. On a device with a touchscreen, or once the game has received a touch, the join screen SHALL show a "Tap to join by touch" strip at its left edge and one at its right edge; activating one SHALL take the first free slot with touch as a player on that side. On a device without a touchscreen that has received no touch (such as Android TV), the strips SHALL NOT be shown. A keyboard set or gamepad SHALL hold at most one slot. There SHALL be two keyboard sets, so at most two players play on one keyboard.

#### Scenario: Two touch players at most
- **WHEN** two players have joined by touch
- **THEN** both side strips are disabled and name the player on that side until one of them leaves

#### Scenario: Keyboard set joins
- **WHEN** nobody has joined and someone presses Space
- **THEN** player 1's slot shows that keyboard set 1 (W A D Space) has joined

#### Scenario: Gamepad joins the next slot
- **WHEN** keyboard set 1 holds player 1's slot and a gamepad presses its fire button
- **THEN** player 2's slot shows that a gamepad has joined

#### Scenario: Touch joins a chosen slot
- **WHEN** player 1 has joined by keyboard and a player taps the strip at the right edge
- **THEN** player 2's slot shows "Touch · right side" and the other slots are unchanged

#### Scenario: A device joins once
- **WHEN** keyboard set 1 has joined and Space is pressed again
- **THEN** no other slot is taken and player 1 toggles ready

#### Scenario: No strips on a TV
- **WHEN** the join screen opens on an Android TV without a touchscreen
- **THEN** no "Tap to join by touch" strip is shown and the empty slots only ask for FIRE on a keyboard set or gamepad

#### Scenario: Strips appear on the first touch
- **WHEN** the join screen is open on a device without a touchscreen and the game receives a touch
- **THEN** both "Tap to join by touch" strips appear

### Requirement: Players are told apart on screen
During a multiplayer game each player's lives and points SHALL be shown in a separate status block tinted with the colour of that player's cabin. A touch player's block SHALL be on their side at the vertical middle, next to their own touch controls on the inner side, turned to read upright from the seat (left −90°, right 90°), and SHALL NOT overlap their joystick or FIRE button at any screen size or touch control size. Keyboard and gamepad players' blocks SHALL be upright along the top edge of the screen in player order.

#### Scenario: Mixed status blocks
- **WHEN** a game runs with two touch players, a keyboard player and a gamepad player
- **THEN** the touch players' blocks are at the middle of the left and right sides next to their controls, turned toward them, and the other two blocks are upright at the top in player order, all in their cabin colours

#### Scenario: No overlap on a phone
- **WHEN** a two-touch-player game runs on a phone-sized screen with the touch controls at 100% or at a larger size
- **THEN** each touch player's lives and points are fully beside, not on top of, their joystick and FIRE button
