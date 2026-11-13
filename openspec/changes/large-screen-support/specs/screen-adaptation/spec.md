# Spec Delta

## Purpose

Lets the game work on any display shape: every device may turn and resize the window, every screen and the running game fit and follow the window, and text boxes stay visible above the on-screen keyboard.

## ADDED Requirements

### Requirement: No orientation restriction
On Android, the game SHALL NOT restrict the orientation or the window size on any device. It SHALL follow the device's rotation in portrait and in landscape, either way up, and SHALL respect the system's rotation lock.

#### Scenario: Phone held upright
- **WHEN** the game runs on a phone held in portrait and rotation is not locked in the system
- **THEN** the game is shown in portrait

#### Scenario: Tablet turned
- **WHEN** a tablet showing the game in landscape is turned to portrait
- **THEN** the game turns to portrait

#### Scenario: System rotation lock
- **WHEN** the system rotation lock is on in landscape and the device is turned to portrait
- **THEN** the game stays in landscape

#### Scenario: Resizable window
- **WHEN** the game runs in a 500 dp wide window on a Chromebook
- **THEN** the game fills its window and the window can be resized

### Requirement: The game follows the window
Every screen and a running game SHALL fit the current window, down to a 360 dp wide phone held upright. When the window changes size or orientation they SHALL fit the new window without being reopened or restarted and without losing anything chosen on them: screens are centred and inside the window, touch controls, lives and points and Pause buttons move to their places, objects outside the field wrap into it, and network clients re-fit the host's field.

#### Scenario: Join screen on a phone held upright
- **WHEN** the join screen opens on a 360 x 800 dp window
- **THEN** the four slot panels are in two rows of two, the bottom row's buttons and device-name box are in two lines, and everything is inside the window and readable

#### Scenario: Join screen turned with players
- **WHEN** keyboard set 1 holds player 1 and a touch player sits at the left edge on a tablet's join screen in landscape, and the tablet turns to portrait
- **THEN** the join screen fills the portrait window with its strips at the screen edges, all four panels and the bottom row inside the window, and both players keep their slots and seats

#### Scenario: Other screens turned
- **WHEN** the window changes from landscape to portrait while the ship selection, menu, settings, leaderboard, pause, results, nickname, network game list or address screen is open
- **THEN** that screen is centred and fully inside the new window, with the same choices made on it

#### Scenario: Four touch players turned
- **WHEN** four touch players play on a tablet in portrait and the tablet turns to landscape
- **THEN** every player's joystick, FIRE, lives and points and Pause button are at their own edge of the landscape window, and the game goes on

#### Scenario: Ship outside the new field
- **WHEN** a ship is 1200 dp from the left edge and the window becomes 800 dp wide
- **THEN** the ship wraps into the field on the next frame

#### Scenario: Network host turned
- **WHEN** a host tablet in landscape turns to portrait during a network game
- **THEN** each client shows the portrait field, scaled to fit, with black bars beside it

### Requirement: Text boxes stay above the on-screen keyboard
When an on-screen keyboard opens for a text box, the game SHALL move its picture up just enough that the text box being typed in is fully visible above the keyboard, and SHALL move it back when the keyboard closes. Where the box is already above the keyboard, nothing SHALL move.

#### Scenario: Nickname on a phone
- **WHEN** a player opens "Save to leaderboard" on a phone and the on-screen keyboard covers the lower half of the screen
- **THEN** the nickname box is shown just above the keyboard, and the typed text is visible while typing

#### Scenario: Device name at the bottom of the join screen
- **WHEN** a player taps the "Device name" box in the join screen's bottom row and the on-screen keyboard opens
- **THEN** the box is shown just above the keyboard

#### Scenario: Keyboard closed
- **WHEN** the player presses Enter or closes the keyboard
- **THEN** the screen returns to its normal place
