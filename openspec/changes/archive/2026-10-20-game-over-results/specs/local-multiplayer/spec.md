# local-multiplayer Specification

## MODIFIED Requirements

### Requirement: Game end in multiplayer
A multiplayer game SHALL end when all ships are out of lives, and then the results screen SHALL be shown (see game-results). Back/Escape or a joined gamepad's Back/Start button SHALL pause the game instead; the game then ends only through "Main menu" on the pause screen.

#### Scenario: All ships lost
- **WHEN** the last ship loses its last life
- **THEN** the game ends and the results screen is shown

#### Scenario: Back in multiplayer
- **WHEN** Back/Escape is pressed during a multiplayer game
- **THEN** the game is paused, not ended
