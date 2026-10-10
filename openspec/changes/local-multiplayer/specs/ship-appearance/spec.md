# Spec Delta

## Purpose

Lets each player give their ship a distinct cabin colour and see the ship before starting the game, so the players can tell their ships apart in play.

## ADDED Requirements

### Requirement: Cabin colours
The game SHALL offer at least six cabin colours (blue, green, red, yellow, purple, orange). Only the cabin of the ship SHALL change colour; the rest of the ship SHALL look as before, both when flying and when not thrusting.

#### Scenario: Only the cabin changes
- **WHEN** a ship with a green cabin is shown
- **THEN** its cabin is green, and the hull and wings look the same as the standard ship

### Requirement: Ship selection before the game
Before a single-player or two-player game starts, the game SHALL show a ship selection screen with a large preview of each player's ship in the currently chosen cabin colour. A player SHALL be able to change the colour of their ship with next/previous controls, and the preview SHALL update immediately. The game SHALL start only after the players confirm.

#### Scenario: Preview updates
- **WHEN** player 1 selects the next colour
- **THEN** the preview of ship 1 changes to that cabin colour before the game has started

#### Scenario: Confirm starts the game
- **WHEN** all players have confirmed their ships
- **THEN** the game starts and each ship has the chosen cabin colour

#### Scenario: Back cancels
- **WHEN** a player activates Back on the selection screen
- **THEN** the main menu is shown and no game is started

### Requirement: Unique colours in multiplayer
In a two-player game the two ships SHALL NOT have the same cabin colour. A colour already taken by the other player SHALL be skipped when cycling and SHALL NOT be confirmable.

#### Scenario: Taken colour skipped
- **WHEN** player 1 has chosen red and player 2 cycles through the colours
- **THEN** red is never offered to player 2 and the next free colour is shown instead

### Requirement: Selection by every input
The selection screen SHALL be operable with touch, keyboard and gamepads. In a two-player game each player SHALL be able to change their own colour and confirm with their own controls (their keyboard set, gamepad or on-screen buttons).

#### Scenario: Player 2 uses their own keys
- **WHEN** player 2 presses the turn-right key of the second keyboard set on the selection screen
- **THEN** only the colour of ship 2 changes

### Requirement: Colour choice persists
The game SHALL remember the last chosen colour of each player in local storage and offer them again next time. Missing, unreadable or invalid saved data SHALL fall back to blue for player 1 and green for player 2 without failing.

#### Scenario: Restored after restart
- **WHEN** player 1 confirms a red ship and the game is restarted
- **THEN** the selection screen initially shows a red ship for player 1

#### Scenario: Corrupt saved data
- **WHEN** the saved colour file contains invalid data
- **THEN** the selection screen shows blue and green
