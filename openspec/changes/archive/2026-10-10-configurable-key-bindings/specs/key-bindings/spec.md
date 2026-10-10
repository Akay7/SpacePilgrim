# Spec Delta

## Purpose

Lets players choose which keyboard keys control the ship, so the game is playable with layouts and preferences other than the built-in defaults.

## ADDED Requirements

### Requirement: Default key bindings
The game SHALL ship with default bindings: Up arrow or W for thrust, Left arrow or A for turn left, Right arrow or D for turn right, and Space for fire. Until the player changes them, input SHALL behave as before this feature.

#### Scenario: Fresh install uses defaults
- **WHEN** the game is started with no saved bindings and the player presses W during a game
- **THEN** the ship thrusts

### Requirement: Settings screen access
The main menu "Settings" button SHALL be enabled and SHALL open a controls settings screen listing thrust, turn left, turn right and fire with their currently bound keys. The screen SHALL provide a way to return to the main menu.

#### Scenario: Open and close settings
- **WHEN** the player activates "Settings" in the main menu and then activates "Back"
- **THEN** the settings screen is shown and afterwards the main menu is shown again

### Requirement: Rebind an action
The player SHALL be able to select an action on the settings screen and press a key to bind it. The new key SHALL replace all keys previously bound to that action and take effect immediately, including in the game started afterwards.

#### Scenario: Rebind fire
- **WHEN** the player selects "Fire" in settings and presses the F key
- **THEN** the settings screen shows F for fire, and pressing F in a game fires a shot while Space no longer does

### Requirement: Conflicting and reserved keys
The game SHALL reject a key that is already bound to another action or is reserved for menu navigation and leaving the game (arrow keys, Enter, Escape/Back), SHALL keep the previous binding, and SHALL tell the player why. Pressing Escape while waiting for a key SHALL cancel the rebind.

#### Scenario: Key already in use
- **WHEN** the player rebinds "Turn left" and presses the key currently bound to "Fire"
- **THEN** the binding for "Turn left" is unchanged and a message says the key is already used

#### Scenario: Cancel rebind
- **WHEN** the player selects an action and presses Escape
- **THEN** the binding is unchanged and the game does not exit

### Requirement: Bindings persist
The game SHALL save changed bindings to local storage and restore them on the next launch. If the saved data is missing, unreadable or invalid, the game SHALL fall back to the defaults without failing.

#### Scenario: Restored after restart
- **WHEN** the player rebinds "Up" to I and the game is restarted
- **THEN** pressing I thrusts in a new game

#### Scenario: Corrupt saved data
- **WHEN** the saved bindings file contains invalid data at launch
- **THEN** the game starts normally with default bindings

### Requirement: Reset to defaults
The settings screen SHALL provide a "Reset to defaults" action that restores the default bindings and saves them.

#### Scenario: Reset
- **WHEN** the player has rebound "Fire" to F and activates "Reset to defaults"
- **THEN** fire is bound to Space again and F no longer fires
