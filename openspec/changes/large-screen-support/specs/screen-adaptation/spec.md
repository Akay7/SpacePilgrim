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

### Requirement: Seats and blocks follow the window's size
When the window changes size or shape, a join screen with nobody seated by touch SHALL offer the touch seats of the new size, also from a big screen's four seats to a small one's and back; a seated touch player SHALL keep their seat. During a multiplayer game the keyboard, gamepad and other devices' players' lives and points SHALL move to where a game started at the new size puts them, and the touch controls SHALL follow; touch players keep their seats.

#### Scenario: Window made small on the join screen
- **WHEN** nobody sits by touch on the join screen of a big window with four strips, and the window is made phone-sized and wide
- **THEN** the strips are at the left, right and bottom edges only

#### Scenario: Phone turned during a game
- **WHEN** a game started on a phone held upright with a touch player at the bottom and a gamepad player, and the phone turns to landscape
- **THEN** the gamepad player's block moves from beside the right edge to the top row, and the touch player's joystick and FIRE move into the bottom corners

#### Scenario: Window made small during a game
- **WHEN** a game started on a big window with a touch player at the bottom and a gamepad player in a corner, and the window is made phone-sized and wide
- **THEN** the gamepad player's block moves to the top row

### Requirement: A client's field uses its screen
A device that shows another device's game (a network client) SHALL show the whole host field at the biggest size its window allows, keeping the field's proportions, and SHALL turn the field a quarter when that shows it bigger.

#### Scenario: Wide host on a phone held upright
- **WHEN** the host's field is 1280 x 720 and a client's window is 720 x 1600, held upright
- **THEN** the client shows the field turned a quarter, filling the window's width, with nothing of the field cut off

#### Scenario: Turning shows it smaller
- **WHEN** the host's field is 1600 x 900 and a client's window is 1024 x 768
- **THEN** the field is not turned

### Requirement: A client's controls sit beside its field
Where a client's field leaves room beside it, the field SHALL keep its biggest size and be placed so that this device's touch controls, Pause buttons and lives and points are outside it where they fit; otherwise it SHALL be centred. Those that do not fit MAY cover the field's edges; the field SHALL NOT be made smaller for them. The field SHALL be placed again when the window changes or a player joins or leaves.

#### Scenario: Controls beside the field
- **WHEN** a client with a 1600 x 720 window shows a 1280 x 800 field and its touch player sits at the left
- **THEN** the field moves right, and the player's joystick, FIRE, Pause button and lives and points are left of it

#### Scenario: Controls below a turned field
- **WHEN** a client held upright at 720 x 1600 shows a 1280 x 720 field and its touch player sits at the bottom
- **THEN** the field is turned and moved up, and the player's controls and lives and points are below it

#### Scenario: Controls cover the edge of a field that fills the screen
- **WHEN** a client's field fills its window with no room beside it
- **THEN** the field keeps its size and the controls cover its edge

#### Scenario: Nothing to make room for
- **WHEN** a client without touch players shows a square field in a wide window
- **THEN** the field is centred

### Requirement: A client's touch controls go into the room
On a client with one touch player, when the room beside the field is at the two ends of the player's edge, the joystick and FIRE SHALL be in the corners of that edge, the player's lives and points beside the joystick and Pause beside FIRE, toward the middle of the edge.

#### Scenario: Controls at the ends of the edge
- **WHEN** a touch player sat at the bottom of a phone held upright, then turned it to 900 x 415 dp, and the phone shows a 1920 x 1080 field
- **THEN** the field keeps its biggest size, the joystick and FIRE are in the bottom corners, the lives and points above the joystick and Pause above FIRE, mostly in the room left and right of the field

### Requirement: A client's other players at the top left
On a client with at most one touch player, the lives and points of keyboard, gamepad and other devices' players SHALL be upright, two lines each, in the top-left corner, one after another in player order into the room beside the field. When this device's touch controls are in that corner (a seat at the top or left edge), the blocks SHALL go to the corner farthest from them: bottom-left for a top seat, top-right for a left seat. No block SHALL overlap a touch control.

#### Scenario: Blocks at the top left
- **WHEN** a client with a touch player at the bottom shows two players of other devices
- **THEN** both blocks are in the top-left corner, one under the other, clear of the joystick

#### Scenario: Touch controls in the top-left corner
- **WHEN** a client held upright has a touch player at the top, whose FIRE is in the top-left corner, and two players of other devices
- **THEN** their blocks are in the bottom-left corner, clear of the touch controls

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
