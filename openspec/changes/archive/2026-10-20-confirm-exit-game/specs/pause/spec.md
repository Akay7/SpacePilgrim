# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
