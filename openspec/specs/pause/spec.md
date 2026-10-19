# pause Specification

## Purpose
Lets a player stop a running game without losing it, look at the frozen state, and then either carry on or leave for the main menu.

## Requirements

### Requirement: Pause button
Each touch player's status block SHALL show a button labelled "Pause" while the game runs, in the place and turned to the seat of that player as before. The button SHALL have a transparent inside, a rounded blue outline, and SHALL show a faint fill while pressed. Keyboard and gamepad players SHALL NOT get the button. No in-game button SHALL be labelled "Menu".

#### Scenario: Single touch player
- **WHEN** a single-player game runs with the touch controls visible
- **THEN** a "Pause" button with a rounded blue outline and transparent inside is shown under the lives and points

#### Scenario: Multiplayer touch players
- **WHEN** a multiplayer game runs with two touch players
- **THEN** each touch player has a "Pause" button turned to their side, and no keyboard or gamepad player has one

### Requirement: Back pauses the game
During a game, Back/Escape, a joined gamepad's Back/Start button and the Back key SHALL pause the game exactly like the "Pause" button, for every player including keyboard and gamepad players. They SHALL NOT leave the game directly.

#### Scenario: Escape during play
- **WHEN** a game runs and a player presses Escape
- **THEN** the game is paused with the pause screen shown, and the main menu is not shown

#### Scenario: Gamepad Start during play
- **WHEN** a joined gamepad's Back/Start button is pressed during a multiplayer game
- **THEN** the game is paused

### Requirement: Pausing freezes the world
Pressing "Pause" SHALL freeze the game for all players: ships, asteroids, shots, explosions and the scrolling background SHALL stop moving, no new asteroids SHALL appear, no collisions SHALL be resolved, the elapsed game time SHALL stop counting, and the ship engine sound SHALL be silent. The frozen world and every player's lives and points SHALL stay visible. Input to the ships (touch, keyboard, gamepad) SHALL have no effect while paused.

#### Scenario: World stops
- **WHEN** a player presses "Pause" while asteroids and shots are moving
- **THEN** every object stays where it was and the lives and points remain displayed

#### Scenario: No game progress while paused
- **WHEN** the game stays paused for ten seconds
- **THEN** no asteroid appears, no life is lost and the elapsed time shown in the results is not increased by those ten seconds

### Requirement: Pause screen
While paused, a pause screen SHALL be shown over the frozen world with the entries "Continue" and "Main menu". It SHALL be operable by touch, by keyboard navigation keys with the fire key or Enter, and by any gamepad. Back/Escape (or a gamepad's Back/Start) on the pause screen SHALL act as "Continue".

#### Scenario: Pause screen contents
- **WHEN** the game is paused
- **THEN** the pause screen shows "Continue" and "Main menu" over the frozen world

#### Scenario: Keyboard navigation
- **WHEN** the game is paused and the player presses the down key and then the fire key
- **THEN** "Main menu" is activated

### Requirement: Continue
"Continue" SHALL remove the pause screen and resume the game exactly from the frozen state: the same positions, lives, points and elapsed time, with touch controls usable again. Pressing buttons or holding keys while paused SHALL NOT leave a ship thrusting or firing after resuming.

#### Scenario: Resume
- **WHEN** the player pauses, waits and presses "Continue"
- **THEN** objects continue from where they stopped and the game plays on

### Requirement: Exit to main menu from pause
"Main menu" on the pause screen SHALL NOT leave the game at once: it SHALL show a confirmation popup asking "Are you sure?" with the entries "Yes" and "No", over the frozen world. The popup SHALL be operable by touch, by keyboard navigation keys with the fire key or Enter, and by any gamepad, and its default selection SHALL be "No". "Yes" SHALL end the game without showing the results screen or saving a score, and SHALL show the main menu. "No", and Back/Escape (or a gamepad's Back/Start) while the popup is shown, SHALL close the popup only: the game SHALL stay paused with the pause screen shown, and the game state SHALL be unchanged.

#### Scenario: Ask before leaving
- **WHEN** the player pauses and chooses "Main menu"
- **THEN** a popup "Are you sure?" with "Yes" and "No" is shown and the game is still there

#### Scenario: Leave from pause
- **WHEN** the player pauses, chooses "Main menu" and then "Yes" in the confirmation popup
- **THEN** the game ends and the main menu is shown

#### Scenario: Decline
- **WHEN** the confirmation popup is shown and the player chooses "No"
- **THEN** the popup closes and the pause screen is shown over the same frozen game

#### Scenario: Escape closes the popup
- **WHEN** the confirmation popup is shown and the player presses Escape
- **THEN** the popup closes, the pause screen is shown and the player is still in the game; the main menu is not shown and the game is not resumed

#### Scenario: Keyboard default is safe
- **WHEN** the confirmation popup has just opened and the player presses the fire key
- **THEN** "No" is activated and the game is kept

### Requirement: Confirm before quitting the app
"Exit" on the main menu, and Escape on the main menu where it quits the app, SHALL NOT quit at once: they SHALL show the same "Are you sure?" popup with "Yes" and "No", defaulting to "No" and operable by touch, keyboard and gamepad. "Yes" SHALL quit the app. "No", and Back/Escape while the popup is shown, SHALL close the popup and show the main menu again.

#### Scenario: Ask before exit
- **WHEN** the player activates "Exit" on the main menu
- **THEN** the popup "Are you sure?" is shown and the app keeps running

#### Scenario: Decline exit
- **WHEN** the exit popup is shown and the player chooses "No" or presses Escape
- **THEN** the popup closes and the main menu is shown

#### Scenario: Confirm exit
- **WHEN** the exit popup is shown and the player chooses "Yes"
- **THEN** the app quits
