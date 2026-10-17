# ship-appearance Specification

## Purpose

Lets each player give their ship a distinct cabin colour and see the ship before starting the game, so the players can tell their ships apart in play.

## Requirements

### Requirement: Cabin colours
The game SHALL offer at least six cabin colours (blue, green, red, yellow, purple, orange). Only the cabin of the ship SHALL change colour; the rest of the ship SHALL look as before, both when flying and when not thrusting.

#### Scenario: Only the cabin changes
- **WHEN** a ship with a green cabin is shown
- **THEN** its cabin is green, and the hull and wings look the same as the standard ship

### Requirement: Ship selection before the game
Before a game starts the game SHALL show a large preview of each player's ship in the currently chosen cabin colour: on the single-player selection screen for player 1, and in each joined slot of the multiplayer join screen. A player SHALL be able to change the colour of their ship with next/previous controls, and the preview SHALL update immediately. The game SHALL start only after the players confirm.

#### Scenario: Preview updates
- **WHEN** a joined player selects the next colour
- **THEN** the preview of that player's ship changes to that cabin colour before the game has started

#### Scenario: Confirm starts the game
- **WHEN** all joined players (at least two) have confirmed their ships
- **THEN** the game starts and each ship has the chosen cabin colour

#### Scenario: Back cancels
- **WHEN** Back is activated on the selection or join screen
- **THEN** the main menu is shown and no game is started

### Requirement: Unique colours in multiplayer
In a multiplayer game no two ships SHALL have the same cabin colour. A colour already taken by another joined player SHALL be skipped when cycling and SHALL NOT be confirmable. A player who joins SHALL get their saved colour if it is free, or else the first free colour.

#### Scenario: Taken colour skipped
- **WHEN** player 1 has red and player 3 has purple and player 2 cycles through the colours
- **THEN** red and purple are never offered to player 2 and the next free colour is shown instead

#### Scenario: Joining with a taken colour
- **WHEN** player 1 has chosen green and a device joins player 2's slot whose saved colour is green
- **THEN** player 2 gets the first free colour

### Requirement: Selection by every input
The selection and join screens SHALL be operable with touch, keyboard and gamepads. In multiplayer each player SHALL change their own colour and confirm with the device they joined with (keyboard set, gamepad, or the on-screen buttons of their slot).

#### Scenario: Player uses their own keys
- **WHEN** keyboard set 2 holds player 2's slot and its turn-right key is pressed
- **THEN** only the colour of ship 2 changes

### Requirement: Colour choice persists
The game SHALL remember the last chosen colour of each of the four player slots in local storage and offer them again next time. Missing, unreadable or invalid saved data SHALL fall back to blue, green, red and yellow for players 1–4 without failing. Data saved for two players SHALL keep those two colours.

#### Scenario: Restored after restart
- **WHEN** player 1 confirms a red ship and the game is restarted
- **THEN** the next time a device joins player 1's slot it shows a red ship

#### Scenario: Corrupt saved data
- **WHEN** the saved colour file contains invalid data
- **THEN** the slots show blue, green, red and yellow
