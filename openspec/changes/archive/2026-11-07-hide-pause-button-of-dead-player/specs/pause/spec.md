# Spec Delta

## MODIFIED Requirements

### Requirement: Pause button
Each touch player's status block SHALL show a button labelled "Pause" while the game runs, in the place and turned to the seat of that player as before. The button SHALL have a transparent inside, a rounded blue outline, and SHALL show a faint fill while pressed. Keyboard and gamepad players SHALL NOT get the button. No in-game button SHALL be labelled "Menu". The button of a player whose ship is out of lives SHALL disappear, while their lives and points stay shown.

#### Scenario: Single touch player
- **WHEN** a single-player game runs with the touch controls visible
- **THEN** a "Pause" button with a rounded blue outline and transparent inside is shown under the lives and points

#### Scenario: Multiplayer touch players
- **WHEN** a multiplayer game runs with two touch players
- **THEN** each touch player has a "Pause" button turned to their side, and no keyboard or gamepad player has one

#### Scenario: Player out of lives
- **WHEN** a touch player of a multiplayer game loses their last life while the others play on
- **THEN** that player's "Pause" button is no longer shown, their lives and points stay, and the other players keep their buttons
