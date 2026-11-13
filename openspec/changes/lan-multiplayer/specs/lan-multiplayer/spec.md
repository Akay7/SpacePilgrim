# Spec Delta

## Purpose

Lets two to four people on the same local network play one SpacePilgrim game together, each on their own device: one device hosts and runs the game, the others join it, even while it runs, every device shows the same shared field, and connected devices share their leaderboards.

## ADDED Requirements

### Requirement: Network game entry
The main menu SHALL have a "Network game" entry between "Multiplayer" and "Leaderboard". It SHALL open a network screen with "Host a game", the list of games found, "Enter address" and "Back". The network screen SHALL be operable by touch, keyboard, gamepad and TV remote. Back/Escape on it SHALL return to the main menu.

#### Scenario: Open with a TV remote
- **WHEN** the main menu is shown on an Android TV and the player moves to "Network game" with the D-pad and presses the centre button
- **THEN** the network screen opens with "Host a game" selected

#### Scenario: Back from the network screen
- **WHEN** the network screen is shown and Escape is pressed
- **THEN** the main menu is shown

#### Scenario: Menu fits a phone
- **WHEN** the main menu is shown on a phone in landscape (about 360 dp high)
- **THEN** all six entries are fully visible and each can be tapped

### Requirement: Host a game
"Host a game" SHALL open the join screen as a network game hosted by this device. The join screen SHALL show this device's local network address and port. From then on the game SHALL be announced on the local network about once a second, both on the join screen and while a game runs. The announcement SHALL stop when the host leaves the network game.

#### Scenario: Hosting shows the address
- **WHEN** a player on a device with address 192.168.1.20 activates "Host a game"
- **THEN** the join screen opens with four empty slots and shows "Hosting on 192.168.1.20" with the port

#### Scenario: Local devices join on the host
- **WHEN** the host's join screen is open and keyboard set 1 on the host presses Space
- **THEN** player 1's slot is taken by keyboard set 1 of the host, as in local multiplayer

#### Scenario: Announcement stops
- **WHEN** the host presses Escape on its join screen
- **THEN** the main menu is shown, the game is no longer announced, and connected clients are told the host closed the game

### Requirement: Find games on the local network
While the network screen is open, it SHALL list the games announced on the local network. Each entry SHALL show the host's device name, the number of players out of four, and "in game" while a game runs. Games not announced for 3 seconds SHALL disappear from the list. Games of an incompatible version SHALL be listed as such and SHALL NOT be joinable. With no games found, the screen SHALL say it is searching.

#### Scenario: Game appears
- **WHEN** a device on the same Wi-Fi hosts a game with two players joined, and another device opens the network screen
- **THEN** within 2 seconds the list shows that host's name with "2/4"

#### Scenario: Running game listed
- **WHEN** a hosted game with three players is running
- **THEN** the list shows that host with "in game · 3/4" and it can be activated

#### Scenario: Host gone
- **WHEN** a listed host leaves the network game
- **THEN** its entry disappears from the list within 3 seconds

#### Scenario: Different version
- **WHEN** a host runs a game version with a different network protocol
- **THEN** its entry says the versions differ and activating it does nothing

### Requirement: Join by address
"Enter address" SHALL ask for the host's address as `IP` or `IP:port`, with the default port used when none is given. Accepting SHALL connect to that host. An address that cannot be parsed, a connection that cannot be set up within 5 seconds, or a refused connection SHALL show a message on the network screen and SHALL keep the player there.

#### Scenario: Join by IP
- **WHEN** the player enters "192.168.1.20" and accepts while that device hosts a game
- **THEN** the client shows the host's join screen, or the running game if one is in progress

#### Scenario: Nobody there
- **WHEN** the player enters an address where no game is hosted
- **THEN** within 5 seconds the network screen says the host could not be reached

### Requirement: Shared join screen
A connected client SHALL show the host's four slots with their current state. Every change on any device SHALL appear on all devices within half a second. The changes are: joining, leaving, colour, ready, and the device flash. A client's keyboard sets, gamepads and touch strips SHALL join, change colour, toggle ready and leave exactly as on a local join screen. Each device SHALL only change the slot it holds.

#### Scenario: Client gamepad joins
- **WHEN** keyboard set 1 of the host holds player 1 and a gamepad on a client presses its fire button
- **THEN** player 2's slot shows the gamepad with the client's device name on both the host and the client

#### Scenario: Same device kind on two machines
- **WHEN** keyboard set 1 of the host holds player 1 and keyboard set 1 of a client presses Space
- **THEN** the client's keyboard set takes player 2, and each keyboard set only changes its own slot

#### Scenario: Touch player on a client
- **WHEN** a player taps the left touch strip on a client phone
- **THEN** a free slot is taken by a touch player at the left of that client

#### Scenario: Client leaves the join screen
- **WHEN** a client whose gamepad holds player 2 presses Escape on the join screen
- **THEN** the client disconnects and shows its main menu, and player 2's slot becomes empty on the host

### Requirement: Slots show the machine
A slot held by a device of another machine SHALL show that device as on a local join screen, followed by the name of the machine it is on. Slots of the viewing device's own devices SHALL be marked as "this device".

#### Scenario: Labels on the host
- **WHEN** player 2 is a gamepad on a client named "Pixel 8"
- **THEN** the host's slot 2 shows "Gamepad 1 · Pixel 8" and the client's slot 2 shows "Gamepad 1 · this device"

### Requirement: Start a network game
A network game SHALL start on all devices at once when at least two players have joined and all joined players are ready, wherever their devices are. A client SHALL NOT be able to start a game on its own.

#### Scenario: Two devices, two players
- **WHEN** one player on the host and one on a client have joined and both are ready
- **THEN** the game starts on both devices with two ships

#### Scenario: Host with no players
- **WHEN** two players on clients have joined and are ready and nobody on the host has joined
- **THEN** the game starts and the host shows the field without controls of its own

### Requirement: Connect to a running game
A client that connects while a game runs SHALL show the running game straight away, with every player's lives and points. Until one of its devices joins, it SHALL only watch, with a prompt that says how to join and how many slots are free.

#### Scenario: Watch on connect
- **WHEN** a phone connects to a host whose two-player game has been running for a minute
- **THEN** the phone shows the field with both ships, their lives and points, and a prompt to join with "2 slots free"

### Requirement: Join during a game
During a network game, a device that has not joined SHALL take the first free slot when it presses FIRE (keyboard set or gamepad) or taps "Tap to join" (touch). This applies to every connected machine, the host included. On a touch device, "Tap to join" SHALL be shown at its free touch seats. The joining player SHALL get their saved colour if free, else the first free colour. No other player SHALL be affected. When all four slots are taken, the device SHALL be told the game is full.

#### Scenario: Client gamepad joins a running game
- **WHEN** a two-player network game runs and a gamepad on a watching client presses its fire button
- **THEN** a third ship appears as player 3 on every device, driven by that gamepad, and the other two ships keep their lives, points and positions

#### Scenario: Host keyboard joins a running game
- **WHEN** a network game runs with two client players and keyboard set 1 on the host presses Space
- **THEN** keyboard set 1 of the host takes a free slot and gets a ship

#### Scenario: Touch joins a running game
- **WHEN** a watching client phone shows "Tap to join" at its left seat and the player taps it
- **THEN** that player takes a free slot with touch controls at the left of that phone

#### Scenario: Game full
- **WHEN** four players are in the game and a device that has not joined presses FIRE
- **THEN** that device shows that the game is full and no ship is added

### Requirement: A late ship starts safely
A ship that joins during a game SHALL start with full lives and no points. It SHALL appear at its slot's start position, or at the nearest point at least 200 px from every asteroid. Its survival time SHALL count from when it joined.

#### Scenario: Asteroid at the start position
- **WHEN** a player joins while an asteroid passes their slot's start position
- **THEN** the ship appears at least 200 px from every asteroid with 3 lives and 0 points

### Requirement: Destroyed players stay out
In a network game, a player whose ship lost its last life SHALL stay out until the game ends, keeping their slot. The device that drove that ship SHALL NOT join another slot in the same game. The game SHALL end when every ship is lost.

#### Scenario: No rejoin after loss
- **WHEN** player 2's ship is destroyed in a network game, a slot is free, and player 2's gamepad presses its fire button
- **THEN** no ship is added for that gamepad and player 2's slot still shows them out

### Requirement: Shared field on every device
The host SHALL run the game. Every client SHALL show the same ships, asteroids, shots, explosions, lives and points as the host. The field SHALL be scaled to fit the client's screen while keeping its proportions, and its edges SHALL be visible where the screen is wider or taller than the field. Ships, asteroids and shots SHALL wrap at the field edges. A client SHALL play the shot, explosion and engine sounds of the shared game.

#### Scenario: Same positions
- **WHEN** a ship on the host is a quarter of the field's width from its left edge
- **THEN** within 100 ms on a client the same ship is drawn a quarter of the field's width from the field's left edge

#### Scenario: Different screen shape
- **WHEN** the host has a 16:9 screen and a client a 4:3 screen
- **THEN** the client shows the whole field with visible field edges above and below it, and nothing of the field is cut off

#### Scenario: Sounds on the client
- **WHEN** a player on the host fires
- **THEN** the client plays the shot sound

### Requirement: Input drives the player's own ship
A device's own keyboard sets, gamepads and touch controls SHALL drive only the ship of the slot they joined. Thrust power, turning and fire SHALL reach the host within the network delay, including variable thrust from a trigger, stick or touch joystick. In-game input from devices that did not join SHALL only be used to join, except Back/Escape, which pauses. Touch controls and the Pause button SHALL appear only on the device of that touch player.

#### Scenario: Client player steers
- **WHEN** a client's keyboard player holds the turn-left key
- **THEN** that player's ship turns left on every device, and no other ship turns

#### Scenario: Half thrust from a client trigger
- **WHEN** a client's gamepad player pulls a bound thrust trigger halfway
- **THEN** that player's ship flies at half power

#### Scenario: Touch controls stay local
- **WHEN** a game has a touch player on a client and a keyboard player on the host
- **THEN** the joystick, FIRE and Pause button of the touch player are shown only on the client

### Requirement: Pause in a network game
Pausing on any device SHALL pause the shared game on every device. The device where it was pressed SHALL show its pause screen at once, without waiting for the host. Every other device SHALL show it when the pause reaches it. While paused, no input SHALL change a ship. "Continue" on any device SHALL resume the game on all devices from the frozen state. Nothing SHALL stay held after resuming.

#### Scenario: Client pauses
- **WHEN** a client player presses Escape during a network game
- **THEN** the world freezes and the pause screen is shown on the host and every client

#### Scenario: Host continues
- **WHEN** the game was paused by a client and a host player activates "Continue"
- **THEN** the game resumes on every device

#### Scenario: Pause with a silent host
- **WHEN** the host has stopped sending without closing the connection and a client player presses Escape
- **THEN** the client shows its pause screen at once, and "Main menu" there takes the client back to its main menu

### Requirement: Leave during a network game
A client SHALL be able to leave a running game by "Main menu" on its pause screen, after the usual confirmation, or by closing the app. Its players' ships SHALL leave the field on every device. Their results SHALL be recorded, and their slots SHALL become free for any device to join. The other players SHALL play on. "Main menu" on the host SHALL end the game for every device. Clients SHALL then show "The host ended the game" and their main menu.

#### Scenario: Client leaves
- **WHEN** three players play over the network and the client holding player 3 leaves through "Main menu"
- **THEN** player 3's ship leaves the field on every device, players 1 and 2 play on, and player 3's slot is free

#### Scenario: Freed slot taken again
- **WHEN** a client holding player 3 has left a running game and a gamepad on another client presses its fire button
- **THEN** the gamepad takes player 3's slot with a new ship

#### Scenario: App closed on a client
- **WHEN** the app on a client holding player 2 is closed during a game
- **THEN** player 2's ship leaves the field on every device and the game goes on

#### Scenario: Host leaves
- **WHEN** the host leaves through "Main menu"
- **THEN** every client shows "The host ended the game" and its main menu

### Requirement: Closed connections and silent devices
Only a closed connection SHALL end a device's part in a network game. A host whose connection to a client closes SHALL treat that client as leaving. A client whose connection to the host closes SHALL show "Connection to the host lost" and its main menu. Silence alone SHALL NOT end anything. The ship of a silent client SHALL keep its slot and the last input received, until it is destroyed or the client leaves.

#### Scenario: Silent client
- **WHEN** a client holding player 2 stops sending while its ship thrusts, and the connection stays open
- **THEN** player 2's ship keeps thrusting with its last input until it is destroyed, and player 2's slot stays taken

#### Scenario: Host app closed
- **WHEN** the app on the host is closed during a game
- **THEN** every client shows "Connection to the host lost" and its main menu

### Requirement: Results on every device
When the last ship is lost, every device SHALL show the results screen. It SHALL include every player who took part, those who left too, with their time and points.

#### Scenario: Results include a leaver
- **WHEN** player 3 left during a game and the last ship is then lost
- **THEN** every device's results screen lists player 3 with the time and points they had when they left

### Requirement: Shared leaderboard
When a client connects, the host and the client SHALL exchange their leaderboards. Each connected device SHALL keep the best 10 entries of the combined list in its own leaderboard. The combined entries stay after disconnecting. An entry SHALL appear once however often devices exchange. Any later new entry on a connected device SHALL reach every connected device. Only leaderboard entries SHALL be shared: nickname, points and time.

#### Scenario: Best player from another device
- **WHEN** a phone's best entry has 30 points, the host's best has 12, and the phone connects to the host
- **THEN** the host's leaderboard lists the 30-point entry first, and it is still listed after the phone disconnects

#### Scenario: No duplicates
- **WHEN** the same phone connects to the same host a second time
- **THEN** no entry appears twice on either device

### Requirement: Save a network game's score once
In a network game, "Save to leaderboard" on any device SHALL store the game's top player once, with the nickname entered there, on every connected device. Once it is saved, "Save to leaderboard" SHALL show the score as saved on every device, with the device that saved it.

#### Scenario: Save on a client
- **WHEN** a network game ends and a client player saves the score as "Ann"
- **THEN** the entry "Ann" appears in the leaderboard of the client, the host and every other connected client, and every results screen shows the score as saved

#### Scenario: Two devices save at once
- **WHEN** the host and a client both activate "Save to leaderboard" for the same game
- **THEN** exactly one entry is added on every device

### Requirement: Version check
Host and client SHALL exchange a network protocol version when connecting. If the versions differ, the host SHALL refuse the client. The client SHALL then say that the game versions differ and stay on the network screen.

#### Scenario: Old client
- **WHEN** a client with an older network protocol connects by address
- **THEN** it shows that the game versions differ and no slot is taken on the host

### Requirement: Robust against bad network data
The host and clients SHALL ignore malformed or oversized messages. They SHALL drop the connection that sent one without crashing or changing the game. Leaderboard entries received with an invalid nickname, points or time SHALL be ignored. The host SHALL accept at most eight connected clients, watching ones included.

#### Scenario: Garbage on the game port
- **WHEN** a program sends random bytes to the host's game port during a game
- **THEN** the host closes that connection and the game continues unchanged

#### Scenario: Ninth client
- **WHEN** eight clients are connected and a ninth tries to connect
- **THEN** the ninth is refused with a message that the game is full

### Requirement: Local network only
Network games SHALL only be announced on, and found on, the local network. Only game data SHALL be exchanged: slots, input, field state, pause, results and leaderboard entries. Nothing SHALL be sent to the internet.

#### Scenario: No internet traffic
- **WHEN** a network game is hosted and played
- **THEN** the only traffic the game sends is broadcast announcements on the local network and connections between the host and its clients
