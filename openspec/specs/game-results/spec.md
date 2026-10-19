# game-results Specification

## Purpose
Shows each player's time survived and points when a game ends, lets the top score be saved with a nickname to a local on-device leaderboard, and offers to play again with the same setup or return to the main menu.

## Requirements

### Requirement: Results screen after game over
When a game ends because every ship is out of lives, the game SHALL show a results screen instead of the main menu. For each player who took part it SHALL show the time survived in seconds and the points scored. The points are the rating; there is no separate score or star scale. The player who survived longest SHALL be marked. Leaving a game through "Main menu" on the pause screen SHALL NOT show the results screen.

#### Scenario: Single player game over
- **WHEN** the only ship loses its last life after 42 seconds with 7 points
- **THEN** the results screen shows 42 seconds and 7 points

#### Scenario: Multiplayer stats per player
- **WHEN** three players took part and the last ship is lost
- **THEN** the results screen has a row per player with that player's survival time and points, and marks the longest survivor

#### Scenario: Quitting skips results
- **WHEN** a player leaves a game through "Main menu" on the pause screen and confirms
- **THEN** the main menu is shown and no results screen appears

### Requirement: Survival time
A ship's survival time SHALL be the time in seconds from the start of the game until it lost its last life, counting only time the game was running. For a ship that is never lost it SHALL be the time until the game ended.

#### Scenario: Earlier loss, shorter time
- **WHEN** player 1 loses their last life at 20 seconds and player 2 at 55 seconds
- **THEN** the results show 20 for player 1 and 55 for player 2

### Requirement: Save to the local leaderboard
The results screen SHALL offer a "Save to leaderboard" action. Activating it SHALL store one entry for the game's top player (the only player in single player; in multiplayer the player with the most points, ties broken by longer survival) with the entered nickname, its points and survival seconds, in a file on the device. Points are the entry's rating; the time is for information only and SHALL NOT affect the ranking except to break ties. The action SHALL work once per game and then show that the score is saved. Saved entries SHALL persist across app restarts and SHALL never leave the device. If the file cannot be written the game SHALL continue and say the score could not be saved.

#### Scenario: Save in multiplayer
- **WHEN** a four-player game ends and the player activates "Save to leaderboard"
- **THEN** exactly one entry, for the player with the most points, is added

#### Scenario: Saved only once
- **WHEN** the score has been saved and the action is activated again
- **THEN** no second entry is added

#### Scenario: Entries survive restart
- **WHEN** an entry was saved and the app is started again
- **THEN** the leaderboard still lists it

### Requirement: Nickname for a saved score
Activating "Save to leaderboard" SHALL first ask for a nickname on a name entry screen with a text field, a "Save" action and a "Cancel" action. The field SHALL be prefilled with the nickname last saved on the device (or "Player" if none) and SHALL accept at most 12 characters; surrounding spaces SHALL be removed and an empty nickname SHALL be replaced by "Player". "Save" (or Enter in the field) stores the entry; "Cancel" (or Back/Escape) returns to the results screen without saving, so the score can still be saved. While the field is being typed in, game keys SHALL NOT trigger menu actions. A player with only a gamepad or remote can accept the prefilled nickname with "Save".

#### Scenario: Typed nickname is stored
- **WHEN** the player activates "Save to leaderboard", types "Ann" and presses Enter
- **THEN** the entry is stored with the nickname "Ann" and the results screen shows the score as saved

#### Scenario: Cancel keeps the score unsaved
- **WHEN** the player activates "Save to leaderboard" and then Cancel
- **THEN** the results screen is shown again, nothing is stored and "Save to leaderboard" is still available

#### Scenario: Nickname remembered
- **WHEN** "Ann" was saved earlier and the player saves another score
- **THEN** the field is prefilled with "Ann"

#### Scenario: Gamepad accepts the default
- **WHEN** a gamepad player opens the name entry and activates "Save"
- **THEN** the entry is stored with the prefilled nickname

### Requirement: Leaderboard screen
The main menu SHALL have a "Leaderboard" entry opening a screen that lists the saved entries, best points first (ties: longer survival first), each row showing the nickname, points and time survived, at most the top 10, with a way back. An empty leaderboard SHALL say that no scores are saved yet. Saving an entry beyond ten SHALL drop the lowest.

#### Scenario: Ordered list
- **WHEN** entries with 5, 30 and 12 points are saved
- **THEN** the screen lists 30, 12, 5 in that order

#### Scenario: Empty
- **WHEN** nothing has been saved
- **THEN** the screen says no scores are saved yet

### Requirement: Play again with the same configuration
The results screen SHALL offer "Play again", which starts a new game with the same number of players, the same devices in the same slots and the same cabin colours, without passing through the menu, ship selection or join screen.

#### Scenario: Replay multiplayer
- **WHEN** a game with keyboard set 1, a gamepad and a touch player on the left ends and the player activates "Play again"
- **THEN** a new game starts with those three players on the same devices and colours

### Requirement: Return to the main menu
The results screen SHALL offer "Main menu", which shows the main menu. Results, leaderboard and menu navigation SHALL work with touch, keyboard and gamepad; Back on the results screen SHALL act as "Main menu".

#### Scenario: Back leaves results
- **WHEN** the results screen is shown and Back/Escape is pressed
- **THEN** the main menu is shown
