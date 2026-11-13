# Spec Delta

## MODIFIED Requirements

### Requirement: Pause button
Each touch player's status block SHALL show a button labelled "Pause" while the game runs, turned to the seat of that player. It SHALL sit at the middle of the player's edge between their joystick and FIRE, with its outer side (toward the screen edge) in line with the outer side of their controls; in single player that is the middle of the bottom edge. Where the gap between the controls is too small, it SHALL stay inside the controls, next to the lives and points. The button SHALL have a transparent inside, a rounded blue outline, and SHALL show a faint fill while pressed. Keyboard and gamepad players SHALL NOT get the button. No in-game button SHALL be labelled "Menu". The button of a player whose ship is out of lives SHALL disappear, while their lives and points stay shown.

#### Scenario: Single touch player
- **WHEN** a single-player game runs with the touch controls visible
- **THEN** a "Pause" button with a rounded blue outline and transparent inside is shown at the middle of the bottom edge, between the joystick and FIRE, its bottom in line with their bottoms

#### Scenario: Multiplayer touch players
- **WHEN** a multiplayer game runs with two touch players
- **THEN** each touch player has a "Pause" button turned to their side, between their joystick and FIRE with its outer side in line with the controls' outer side, and no keyboard or gamepad player has one

#### Scenario: Controls too large for the gap
- **WHEN** a two-touch-player game runs on a 640 x 360 dp phone with the touch controls at 200%, so no Pause button fits between a player's joystick and FIRE
- **THEN** each player's "Pause" button is inside the controls next to their lives and points, and overlaps no joystick, FIRE button or status block

#### Scenario: Four players with large controls
- **WHEN** a four-touch-player game runs on a 15 cm × 10 cm screen with the touch controls at 400%
- **THEN** each player's "Pause" button is between their joystick and FIRE, which are made small enough to leave room for it, and overlaps nothing

#### Scenario: Player out of lives
- **WHEN** a touch player of a multiplayer game loses their last life while the others play on
- **THEN** that player's "Pause" button is no longer shown, their lives and points stay, and the other players keep their buttons
