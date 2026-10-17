# key-bindings Specification

## Purpose

Lets players choose which keyboard keys control the ship, so the game is playable with layouts and preferences other than the built-in defaults.

## Requirements

### Requirement: Default key bindings
The game SHALL ship with two default keyboard sets, so that at most two players share one keyboard. Set 1: Up arrow or W for thrust, Left arrow or A for turn left, Right arrow or D for turn right, and Space or Enter for fire. Set 2: I for thrust, J for turn left, L for turn right and K for fire. In single player set 1 SHALL behave as before multiplayer existed.

#### Scenario: Fresh install uses defaults
- **WHEN** the game is started with no saved bindings and the player presses W during a single-player game
- **THEN** the ship thrusts

#### Scenario: Second set defaults
- **WHEN** keyboard set 2 joined a multiplayer game with no saved bindings and I is pressed
- **THEN** that player's ship thrusts

### Requirement: Settings screen access
The main menu "Settings" button SHALL be enabled and SHALL open a settings screen offering "Keyboard layout" and "Touch controls". "Keyboard layout" SHALL open a screen listing thrust, turn left, turn right and fire with their currently bound keys. Each settings screen SHALL provide a way to go back: from the keyboard layout to the settings screen, and from the settings screen to the main menu.

#### Scenario: Open and close settings
- **WHEN** the player activates "Settings" in the main menu, then "Keyboard layout", then "Back" twice
- **THEN** the settings screen, the keyboard layout screen, the settings screen and finally the main menu are shown in turn

### Requirement: Rebind an action
The user SHALL be able to select an action of a chosen keyboard set on the settings screen and press a key to bind it. The new key SHALL replace all keys previously bound to that action of that set and take effect immediately, including in the game started afterwards. Bindings of the other set SHALL be unchanged.

#### Scenario: Rebind fire
- **WHEN** the user selects "Fire" for set 1 in settings and presses the F key
- **THEN** the settings screen shows F for fire, and pressing F in a single-player game fires a shot while Space no longer does

#### Scenario: Rebind for set 2
- **WHEN** the user selects "Turn left" for set 2 and presses the U key
- **THEN** U turns left the ship of the player who joined with set 2, and the keys of set 1 are unchanged

### Requirement: Conflicting and reserved keys
The game SHALL reject a key that is already bound to any action of either set or is reserved for menu navigation and leaving the game (arrow keys, Enter, Escape/Back), SHALL keep the previous binding, and SHALL tell the user why. Pressing Escape while waiting for a key SHALL cancel the rebind.

#### Scenario: Key already in use
- **WHEN** the user rebinds "Turn left" and presses the key currently bound to "Fire"
- **THEN** the binding for "Turn left" is unchanged and a message says the key is already used

#### Scenario: Key used by the other set
- **WHEN** the user rebinds a set 2 action to W, which is set 1's thrust key
- **THEN** the binding is unchanged and a message says the key is already used by set 1

#### Scenario: Cancel rebind
- **WHEN** the user selects an action and presses Escape
- **THEN** the binding is unchanged and the game does not exit

### Requirement: Bindings persist
The game SHALL save changed bindings of both sets to local storage and restore them on the next launch. If the saved data is missing, unreadable or invalid, the game SHALL fall back to the defaults without failing. Bindings saved by a version that had only one set SHALL be kept for set 1 and set 2 SHALL get the defaults.

#### Scenario: Restored after restart
- **WHEN** the user rebinds set 1 "Up" to Y and the game is restarted
- **THEN** pressing Y thrusts the ship of set 1 in a new game

#### Scenario: Corrupt saved data
- **WHEN** the saved bindings file contains invalid data at launch
- **THEN** the game starts normally with default bindings

#### Scenario: Upgrade from a single set
- **WHEN** the saved file only holds the old single set with fire rebound to F
- **THEN** set 1 fires with F and set 2 has the default keys

### Requirement: Reset to defaults
The settings screen SHALL provide a "Reset to defaults" action that restores the default bindings of both sets and saves them.

#### Scenario: Reset
- **WHEN** the user has rebound set 1 "Fire" to F and set 2 "Fire" to H and activates "Reset to defaults"
- **THEN** set 1 fires with Space and set 2 with K, and F and H no longer fire

### Requirement: Keyboard set selection on the keyboard layout page
The keyboard layout settings page SHALL let the user choose whether keyboard set 1 or set 2 is shown and edited, and SHALL show the keys of the chosen set for thrust, turn left, turn right and fire.

#### Scenario: Switch to set 2
- **WHEN** the user opens the keyboard layout page and switches to set 2
- **THEN** the page lists the keys currently bound for set 2
