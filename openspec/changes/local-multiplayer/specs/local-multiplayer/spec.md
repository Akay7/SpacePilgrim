# Spec Delta

## Purpose

Lets two people play SpacePilgrim together on one device, each with their own ship and their own input (keyboard set, gamepad or on-screen controls), sharing one playfield.

## ADDED Requirements

### Requirement: Start a two-player game
The main menu "Multiplayer" entry SHALL be enabled and SHALL lead to the ship selection for two players, after which a game with two ships starts. "Single player" SHALL keep starting a one-ship game.

#### Scenario: Multiplayer is available
- **WHEN** the main menu is shown
- **THEN** the "Multiplayer" entry can be activated with touch, keyboard and gamepad

#### Scenario: Two ships in the field
- **WHEN** the players confirm their ships in multiplayer
- **THEN** a game starts with two ships at different starting positions, both under control at once

### Requirement: Shared field, separate scores
In a two-player game both ships SHALL share the same asteroids. Each ship SHALL have its own lives and points, and shots SHALL score for the ship that fired them. A ship that loses its last life SHALL leave the field while the other ship keeps playing.

#### Scenario: Points go to the shooter
- **WHEN** player 2's shot destroys an asteroid
- **THEN** player 2's points increase and player 1's points do not

#### Scenario: One ship is out
- **WHEN** player 1 loses the last life while player 2 still has lives
- **THEN** player 1's ship disappears and the game continues for player 2

### Requirement: Game end in multiplayer
A two-player game SHALL end and return to the main menu when both ships are out of lives, or when any player presses Back/Escape or the gamepad Back/Start button.

#### Scenario: Both ships lost
- **WHEN** the second ship loses its last life
- **THEN** the game ends and the main menu is shown

### Requirement: Players are told apart on screen
During a two-player game each player's lives and points SHALL be shown in a separate status block tinted with the colour of that player's cabin, on that player's own side of the screen (player 1 left, player 2 right) at the vertical middle, between where the joystick and the FIRE button are. The text SHALL be turned to read upright from that player's seat: player 1's block turned a quarter turn clockwise and player 2's a quarter turn counter-clockwise.

#### Scenario: Two status blocks
- **WHEN** a two-player game is running
- **THEN** two status blocks show each player's lives and points in the cabin colours, one in the middle of each side, between that player's joystick and FIRE button, each turned toward its player

### Requirement: Keyboard sets per player
Each player SHALL be controlled by their own configured keyboard set (thrust, turn left, turn right, fire) in a two-player game. Both sets SHALL work at the same time, including while keys of both are held.

#### Scenario: Both players on one keyboard
- **WHEN** player 1 holds W and A while player 2 holds the thrust key of the second set
- **THEN** ship 1 thrusts and turns left and ship 2 thrusts

#### Scenario: Single player ignores the second set
- **WHEN** a single-player game runs and the player presses a key of the second set
- **THEN** nothing happens

### Requirement: Gamepad assignment
In a two-player game the first connected gamepad that sends input SHALL control player 1 and the second one SHALL control player 2. A single gamepad SHALL control player 1 only. In a single-player game any gamepad SHALL control the only ship. Keyboard and touch input SHALL stay usable alongside the gamepads.

#### Scenario: Two gamepads
- **WHEN** two gamepads are connected and each presses its fire button in a two-player game
- **THEN** each ship fires, one per gamepad

#### Scenario: One gamepad and a keyboard
- **WHEN** one gamepad and the keyboard are used in a two-player game
- **THEN** the gamepad controls ship 1 and the second keyboard set controls ship 2

### Requirement: Two-player touch layout
In a two-player game each player's on-screen controls SHALL be on that player's own side of the screen, one control in the bottom corner and the other at the top of the same side, just below the status text. The players are assumed to sit on opposite sides with the screen between them.

#### Scenario: Controls use the whole side
- **WHEN** a two-player game starts with touch controls visible
- **THEN** each side has one control in its bottom corner and the other near the top, below the status text

### Requirement: Hand-correct touch controls
Each player SHALL have the joystick under the left hand and FIRE under the right hand as seen from their seat: player 1 (left side) joystick at the top and FIRE at the bottom, player 2 (right side) FIRE at the top and joystick at the bottom. The "FIRE" label SHALL be turned to read upright from the player's seat, like the status text.

#### Scenario: Both touch sets visible
- **WHEN** a two-player game starts with touch controls visible
- **THEN** on the left side FIRE is in the bottom-left corner and the joystick is at the top of that side under the status text, on the right side the joystick is in the bottom-right corner and FIRE at the top of that side, and none touches the screen edges or covers the status text

### Requirement: Two-player touch independence
Each touch set SHALL only control its own ship, and both sets SHALL be usable at the same time with different fingers. Which player is which SHALL NOT make any difference to how the game plays.

#### Scenario: Players steer independently
- **WHEN** player 1 holds their joystick to the left and player 2 presses their FIRE button
- **THEN** ship 1 turns left and ship 2 fires, while ship 1 does not fire and ship 2 does not turn

#### Scenario: Single player layout unchanged
- **WHEN** a single-player game starts with touch controls visible
- **THEN** one joystick is shown at the bottom-left and one FIRE button at the bottom-right as before

### Requirement: Menus stay usable by every player
In menus and settings, keyboard navigation keys, any gamepad and touch SHALL work for whoever uses them; menu navigation SHALL NOT depend on which player an input belongs to.

#### Scenario: Second gamepad in the menu
- **WHEN** the second gamepad presses its fire button on the main menu
- **THEN** the highlighted menu entry is activated
