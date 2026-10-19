# Spec Delta

## MODIFIED Requirements

### Requirement: Game end in multiplayer
A multiplayer game SHALL end and return to the main menu when all ships are out of lives. Back/Escape or a joined gamepad's Back/Start button SHALL pause the game instead; the game then ends only through "Main menu" on the pause screen.

#### Scenario: All ships lost
- **WHEN** the last ship loses its last life
- **THEN** the game ends and the main menu is shown

#### Scenario: Back in multiplayer
- **WHEN** Back/Escape is pressed during a multiplayer game
- **THEN** the game is paused, not ended
