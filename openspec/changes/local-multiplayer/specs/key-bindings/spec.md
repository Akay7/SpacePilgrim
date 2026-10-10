# Spec Delta

## ADDED Requirements

### Requirement: Player selection on the keyboard layout page
The keyboard layout settings page SHALL let the user choose whether player 1 or player 2 bindings are shown and edited, and SHALL show the keys of the chosen player for thrust, turn left, turn right and fire.

#### Scenario: Switch to player 2
- **WHEN** the user opens the keyboard layout page and selects player 2
- **THEN** the page lists the keys currently bound for player 2

## MODIFIED Requirements

### Requirement: Default key bindings
The game SHALL ship with default bindings for two players. Player 1: Up arrow or W for thrust, Left arrow or A for turn left, Right arrow or D for turn right, and Space for fire. Player 2: I for thrust, J for turn left, L for turn right and K for fire. Until the player changes them, player 1 input SHALL behave as before multiplayer existed.

#### Scenario: Fresh install uses defaults
- **WHEN** the game is started with no saved bindings and the player presses W during a game
- **THEN** the ship thrusts

#### Scenario: Second set defaults
- **WHEN** a two-player game is started with no saved bindings and the second player presses I
- **THEN** the second ship thrusts

### Requirement: Rebind an action
The user SHALL be able to select an action of a chosen player on the settings screen and press a key to bind it. The new key SHALL replace all keys previously bound to that action of that player and take effect immediately, including in the game started afterwards. Bindings of the other player SHALL be unchanged.

#### Scenario: Rebind fire
- **WHEN** the user selects "Fire" for player 1 in settings and presses the F key
- **THEN** the settings screen shows F for fire, and pressing F in a game fires a shot of ship 1 while Space no longer does

#### Scenario: Rebind for player 2
- **WHEN** the user selects "Turn left" for player 2 and presses the U key
- **THEN** U turns ship 2 left and the keys of player 1 are unchanged

### Requirement: Conflicting and reserved keys
The game SHALL reject a key that is already bound to any action of either player or is reserved for menu navigation and leaving the game (arrow keys, Enter, Escape/Back), SHALL keep the previous binding, and SHALL tell the user why. Pressing Escape while waiting for a key SHALL cancel the rebind.

#### Scenario: Key already in use
- **WHEN** the user rebinds "Turn left" and presses the key currently bound to "Fire"
- **THEN** the binding for "Turn left" is unchanged and a message says the key is already used

#### Scenario: Key used by the other player
- **WHEN** the user rebinds a player 2 action to W, which is player 1's thrust key
- **THEN** the binding is unchanged and a message says the key is already used

#### Scenario: Cancel rebind
- **WHEN** the user selects an action and presses Escape
- **THEN** the binding is unchanged and the game does not exit

### Requirement: Bindings persist
The game SHALL save changed bindings of both players to local storage and restore them on the next launch. If the saved data is missing, unreadable or invalid, the game SHALL fall back to the defaults without failing. Bindings saved by a version that had only one set SHALL be kept for player 1 and player 2 SHALL get the defaults.

#### Scenario: Restored after restart
- **WHEN** the user rebinds player 1 "Up" to Y and the game is restarted
- **THEN** pressing Y thrusts ship 1 in a new game

#### Scenario: Corrupt saved data
- **WHEN** the saved bindings file contains invalid data at launch
- **THEN** the game starts normally with default bindings

#### Scenario: Upgrade from a single set
- **WHEN** the saved file only holds the old single set with fire rebound to F
- **THEN** player 1 fires with F and player 2 has the default keys

### Requirement: Reset to defaults
The settings screen SHALL provide a "Reset to defaults" action that restores the default bindings of both players and saves them.

#### Scenario: Reset
- **WHEN** the user has rebound player 1 "Fire" to F and player 2 "Fire" to H and activates "Reset to defaults"
- **THEN** player 1 fires with Space and player 2 with K, and F and H no longer fire
