# Spec Delta

## MODIFIED Requirements

### Requirement: Survival time
A ship's survival time SHALL be the time in seconds from the start of the game until it lost its last life, counting only time the game was running. For a ship that is never lost it SHALL be the time until the game ended. For a ship that joined during a network game, the time SHALL count from when it joined. For a ship whose player left during a network game, it SHALL count until the player left.

#### Scenario: Earlier loss, shorter time
- **WHEN** player 1 loses their last life at 20 seconds and player 2 at 55 seconds
- **THEN** the results show 20 for player 1 and 55 for player 2

#### Scenario: Joined late
- **WHEN** player 3 joins a network game at 30 seconds and loses their last life at 50 seconds
- **THEN** the results show 20 for player 3

### Requirement: Save to the local leaderboard
The results screen SHALL offer a "Save to leaderboard" action. Activating it SHALL store one entry for the game's top player (the only player in single player; in multiplayer the player with the most points, ties broken by longer survival) with the entered nickname, its points and survival seconds, in a file on the device. Points are the entry's rating; the time is for information only and SHALL NOT affect the ranking except to break ties. The action SHALL work once per game and then show that the score is saved. Saved entries SHALL persist across app restarts. Entries SHALL only leave the device to be shared with the devices of a network game it is connected to. In a network game the action SHALL only be offered on the device of the top player. If the file cannot be written the game SHALL continue and say the score could not be saved.

#### Scenario: Save in multiplayer
- **WHEN** a four-player game ends and the player activates "Save to leaderboard"
- **THEN** exactly one entry, for the player with the most points, is added

#### Scenario: Saved only once
- **WHEN** the score has been saved and the action is activated again
- **THEN** no second entry is added

#### Scenario: Entries survive restart
- **WHEN** an entry was saved and the app is started again
- **THEN** the leaderboard still lists it

#### Scenario: Kept on the device outside network games
- **WHEN** a single-player or same-screen game's score is saved and the device never connects to a network game
- **THEN** the entry is sent nowhere

#### Scenario: Older leaderboard file
- **WHEN** the app starts with a leaderboard file written by an earlier version
- **THEN** every entry is still listed in the same order

### Requirement: Play again with the same configuration
The results screen SHALL offer "Play again", which starts a new game with the same number of players, the same devices in the same slots and the same cabin colours, without passing through the menu, ship selection or join screen. In a network game, "Play again" SHALL only be offered on the host. It SHALL restart the game on every device with the players whose devices are still connected. If fewer than two players remain, it SHALL return the host to its network join screen instead. A client SHALL show "Waiting for the host" in place of "Play again" and SHALL follow the host into the new game.

#### Scenario: Replay multiplayer
- **WHEN** a game with keyboard set 1, a gamepad and a touch player on the left ends and the player activates "Play again"
- **THEN** a new game starts with those three players on the same devices and colours

#### Scenario: Replay a network game
- **WHEN** a network game with a player on the host and two players on a client ends and the host activates "Play again"
- **THEN** a new game starts on both devices with the same three players, devices and colours

#### Scenario: Client waits for the host
- **WHEN** a network game ends
- **THEN** each client's results screen shows "Waiting for the host" instead of "Play again", and "Save to leaderboard" and "Main menu" still work there

#### Scenario: Too few players left
- **WHEN** a two-player network game ends, the client has left, and the host activates "Play again"
- **THEN** the host's network join screen is shown, still hosting, with its own player in their slot
