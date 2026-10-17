# local-multiplayer Specification

## Purpose

Lets two to four people play SpacePilgrim together on one device, each with their own ship and their own input that they join with: one of two keyboard sets, a gamepad, or on-screen controls for up to two touch players. All ships share one playfield.

## Requirements

### Requirement: Start a multiplayer game
The main menu "Multiplayer" entry SHALL be enabled and SHALL lead to the join screen. The game SHALL start when at least two players have joined and every joined player is ready, with one ship per joined player. "Single player" SHALL keep starting a one-ship game.

#### Scenario: Multiplayer is available
- **WHEN** the main menu is shown
- **THEN** the "Multiplayer" entry can be activated with touch, keyboard and gamepad

#### Scenario: Ships for the joined players
- **WHEN** three players have joined and all three are ready
- **THEN** a game starts with three ships at different starting positions, all under control at once

#### Scenario: One ready player does not start alone
- **WHEN** only one player has joined and is ready
- **THEN** the join screen stays and says that at least two players are needed

### Requirement: Join with a device
The join screen SHALL show four player slots. Pressing FIRE on a keyboard set or gamepad that has not joined SHALL take the first free slot with that device. On a device with a touchscreen, or once the game has received a touch, the join screen SHALL show a "Tap to join by touch" strip at its left edge and one at its right edge; activating one SHALL take the first free slot with touch as a player on that side. On a device without a touchscreen that has received no touch (such as Android TV), the strips SHALL NOT be shown. A keyboard set or gamepad SHALL hold at most one slot. There SHALL be two keyboard sets, so at most two players play on one keyboard.

#### Scenario: Two touch players at most
- **WHEN** two players have joined by touch
- **THEN** both side strips are disabled and name the player on that side until one of them leaves

#### Scenario: Keyboard set joins
- **WHEN** nobody has joined and someone presses Space
- **THEN** player 1's slot shows that keyboard set 1 (W A D Space) has joined

#### Scenario: Gamepad joins the next slot
- **WHEN** keyboard set 1 holds player 1's slot and a gamepad presses its fire button
- **THEN** player 2's slot shows that a gamepad has joined

#### Scenario: Touch joins a chosen slot
- **WHEN** player 1 has joined by keyboard and a player taps the strip at the right edge
- **THEN** player 2's slot shows "Touch · right side" and the other slots are unchanged

#### Scenario: A device joins once
- **WHEN** keyboard set 1 has joined and Space is pressed again
- **THEN** no other slot is taken and player 1 toggles ready

#### Scenario: No strips on a TV
- **WHEN** the join screen opens on an Android TV without a touchscreen
- **THEN** no "Tap to join by touch" strip is shown and the empty slots only ask for FIRE on a keyboard set or gamepad

#### Scenario: Strips appear on the first touch
- **WHEN** the join screen is open on a device without a touchscreen and the game receives a touch
- **THEN** both "Tap to join by touch" strips appear

### Requirement: Players see their device
Each joined slot SHALL show which device drives it (keyboard set with its keys, gamepad, or touch), and SHALL visibly react when that device sends input, so that every player can tell which device belongs to which ship.

#### Scenario: Device shown and highlighted
- **WHEN** keyboard set 2 holds player 2's slot and its turn-right key is pressed
- **THEN** player 2's slot shows "Keys I J L K", highlights briefly and changes its colour, and no other slot changes

### Requirement: Players set up at the same time
On the join screen each joined device SHALL only change its own slot: turn left/right change the ship colour, fire toggles ready, and leave frees the slot. Several players SHALL be able to do this at the same time.

#### Scenario: Simultaneous setup
- **WHEN** player 1 (keyboard set 1) presses D while player 2 (gamepad) presses its fire button
- **THEN** player 1's colour changes and player 2 becomes ready, and neither affects the other slot

### Requirement: Leave a slot
A joined player SHALL be able to leave their slot with the thrust key of their keyboard set, the Back/Start button of their gamepad, or the Leave button of the slot. The slot SHALL become empty and the device SHALL be free to join again. Escape, or Back/Start of a gamepad that has not joined, SHALL return to the main menu.

#### Scenario: Keyboard player leaves
- **WHEN** keyboard set 1 holds player 1's slot and W is pressed
- **THEN** player 1's slot is empty and pressing Space joins again

#### Scenario: Gamepad player leaves
- **WHEN** a gamepad holds player 2's slot and presses Back
- **THEN** player 2's slot is empty and the join screen stays

#### Scenario: Escape cancels
- **WHEN** Escape is pressed on the join screen
- **THEN** the main menu is shown and no game is started

### Requirement: Input drives only the joined ship
In a multiplayer game each keyboard set, gamepad and touch set SHALL drive only the ship of the slot it joined. Devices that did not join SHALL be ignored, except Back. The arrow keys and Enter SHALL count as keyboard set 1.

#### Scenario: Swapped keyboard sets
- **WHEN** keyboard set 2 joined as player 1 and keyboard set 1 as player 2, and I is pressed in the game
- **THEN** ship 1 thrusts and ship 2 does not

#### Scenario: Device that did not join
- **WHEN** only gamepads and keyboard set 1 joined and I (keyboard set 2) is pressed in the game
- **THEN** no ship changes

#### Scenario: Two gamepads
- **WHEN** two gamepads joined as players 1 and 2 and each presses its fire button in the game
- **THEN** each ship fires, one per gamepad

#### Scenario: Single player ignores joining
- **WHEN** a single-player game runs and any keyboard set or gamepad is used
- **THEN** it drives the only ship, as before multiplayer existed

### Requirement: Shared field, separate scores
In a multiplayer game all ships SHALL share the same asteroids. Each ship SHALL have its own lives and points, and shots SHALL score for the ship that fired them. A ship that loses its last life SHALL leave the field while the other ships keep playing.

#### Scenario: Points go to the shooter
- **WHEN** player 2's shot destroys an asteroid
- **THEN** player 2's points increase and no other player's points do

#### Scenario: One ship is out
- **WHEN** player 1 loses the last life while other players still have lives
- **THEN** player 1's ship disappears and the game continues for the others

### Requirement: Game end in multiplayer
A multiplayer game SHALL end and return to the main menu when all ships are out of lives, or when Back/Escape or a joined gamepad's Back/Start button is pressed.

#### Scenario: All ships lost
- **WHEN** the last ship loses its last life
- **THEN** the game ends and the main menu is shown

### Requirement: Touch seats
At most two players SHALL play on the touch screen. They SHALL sit at the left and right sides of the screen, facing each other. A player who joins by touch SHALL sit on the side whose join strip they tapped, and the joined slot SHALL name that side.

#### Scenario: Touch players take their side
- **WHEN** one player taps the right strip and then another taps the left strip
- **THEN** player 1's slot shows "Touch · right side" and player 2's slot "Touch · left side"

#### Scenario: Side freed by leaving
- **WHEN** the left touch player leaves
- **THEN** the left strip can be tapped again

### Requirement: Players are told apart on screen
During a multiplayer game each player's lives and points SHALL be shown in a separate status block tinted with the colour of that player's cabin. A touch player's block SHALL be on their side at the vertical middle, next to their own touch controls on the inner side, turned to read upright from the seat (left −90°, right 90°), and SHALL NOT overlap their joystick or FIRE button at any screen size or touch control size. Keyboard and gamepad players' blocks SHALL be upright along the top edge of the screen in player order.

#### Scenario: Mixed status blocks
- **WHEN** a game runs with two touch players, a keyboard player and a gamepad player
- **THEN** the touch players' blocks are at the middle of the left and right sides next to their controls, turned toward them, and the other two blocks are upright at the top in player order, all in their cabin colours

#### Scenario: No overlap on a phone
- **WHEN** a two-touch-player game runs on a phone-sized screen with the touch controls at 100% or at a larger size
- **THEN** each touch player's lives and points are fully beside, not on top of, their joystick and FIRE button

### Requirement: Touch controls for touch players
In a multiplayer game only players who joined by touch SHALL get on-screen controls, and these SHALL stay shown for the whole game regardless of the touch controls setting and of keyboard or gamepad use by other players.

#### Scenario: Touch and keyboard players
- **WHEN** player 1 joined by touch and player 2 by keyboard, and player 2 presses a key in the game
- **THEN** player 1's joystick and FIRE stay visible on their side and player 2 has no touch controls

### Requirement: Touch layout per side
A touch player's joystick and FIRE SHALL be at the two ends of their side, the joystick under the left hand and FIRE under the right hand as seen from the seat: left side joystick at the top and FIRE in the bottom corner, right side FIRE at the top and joystick in the bottom corner. The "FIRE" label SHALL read upright from the seat. The controls SHALL keep a margin to the screen edges and SHALL NOT overlap the other side's controls.

#### Scenario: Both touch sets visible
- **WHEN** a game starts with two touch players
- **THEN** on the left side FIRE is in the bottom-left corner and the joystick at the top of that side, on the right side the joystick is in the bottom-right corner and FIRE at the top of that side, and none touches the screen edges

### Requirement: Joystick turned toward the seat
In a multiplayer game a touch player's joystick SHALL be turned toward their seat: pushing it away from the player, toward the centre of the screen, SHALL thrust, and pushing it to the player's own left or right, as seen from the seat, SHALL turn the ship left or right. The direction marks on the joystick SHALL be turned the same way. The single-player joystick SHALL keep screen directions.

#### Scenario: Left player pushes forward
- **WHEN** the left touch player pushes their joystick toward the screen centre (to the right on the screen)
- **THEN** their ship thrusts and does not turn

#### Scenario: Right player turns left
- **WHEN** the right touch player pushes their joystick toward the bottom of the screen, which is their left
- **THEN** their ship turns left

### Requirement: Touch independence
Each touch set SHALL only control its own ship, and both sets SHALL be usable at the same time with different fingers.

#### Scenario: Players steer independently
- **WHEN** the left touch player holds their joystick to the left and the right touch player presses their FIRE button
- **THEN** the left player's ship turns left and the right player's ship fires, while neither does what the other pressed

#### Scenario: Single player layout unchanged
- **WHEN** a single-player game starts with touch controls visible
- **THEN** one joystick is shown at the bottom-left and one FIRE button at the bottom-right as before

### Requirement: Menus stay usable by every player
In menus and settings, keyboard navigation keys, any gamepad and touch SHALL work for whoever uses them; menu navigation SHALL NOT depend on which slot an input belongs to.

#### Scenario: Second gamepad in the menu
- **WHEN** a second gamepad presses its fire button on the main menu
- **THEN** the highlighted menu entry is activated
