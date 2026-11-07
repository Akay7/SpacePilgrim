# Spec Delta

## Purpose

Lets players choose, for each gamepad, which buttons thrust and fire and optionally a trigger that thrusts with variable power, so the game suits different pads, hands and accessibility needs, and keeps menus and Back/Start safe so a bad binding can never lock the player out.

## ADDED Requirements

### Requirement: Default gamepad buttons
The game SHALL ship with default gamepad buttons: A and X fire, B and Y thrust, and no thrust trigger. Steering SHALL be done with the left stick and the D-pad, and Back/Start SHALL act as Back (pause, leave, cancel). A gamepad without a saved layout SHALL use the defaults.

#### Scenario: Fresh install uses defaults
- **WHEN** the game is started with no saved gamepad bindings and a gamepad's A button is pressed during a single-player game
- **THEN** the ship fires

### Requirement: Layout per gamepad
Every gamepad model SHALL have its own layout, found again by the pad's name and identifier after a restart or reconnect, so that gamepads of different models in the same game each use their own buttons. Gamepads of the same model SHALL share one layout. Changing the layout of one model SHALL NOT change any other model.

#### Scenario: Two models, two layouts
- **WHEN** pad X has Fire rebound to Y while pad Z keeps the defaults, and both play a multiplayer game
- **THEN** pad X fires with Y and not with A, and pad Z fires with A

#### Scenario: Same model shares a layout
- **WHEN** two gamepads of the same model are connected and Fire is rebound on one of them
- **THEN** both fire with the new button

### Requirement: Gamepad buttons settings page
The settings screen SHALL offer a "Gamepad buttons" entry that opens a page with a selector for the gamepad being edited (cycling through the connected pads by name), the entries "Thrust" and "Fire" showing what is bound for that pad, a "Reset to defaults" action and a "Back" action that returns to the settings screen. The page SHALL be operable by touch, keyboard and gamepad.

#### Scenario: Open the page
- **WHEN** a gamepad is connected and the player opens Settings and activates "Gamepad buttons"
- **THEN** the page shows that pad's name with Thrust and Fire and their bound buttons, for example "Thrust: B, Y" and "Fire: A, X"

#### Scenario: No gamepad connected
- **WHEN** no gamepad is connected and the page is opened
- **THEN** it says that no gamepad is connected and no entry waits for a button

#### Scenario: Choose the pad to edit
- **WHEN** two different gamepads are connected and the player activates the pad selector
- **THEN** the page lists the layout of the other pad

#### Scenario: Operate with a gamepad
- **WHEN** the page is open and a gamepad moves the selection with the D-pad and activates "Back" with its fire button
- **THEN** the settings screen is shown again

### Requirement: No gamepad and button names
When no gamepad is connected the page SHALL say so and SHALL NOT offer to bind. Buttons SHALL be shown by name where known (A, B, X, Y) and as "Button N" otherwise.

#### Scenario: Unknown button name
- **WHEN** a pad's Fire is rebound to a button that has no known name, such as button 9
- **THEN** the page shows "Button 9" for fire

### Requirement: Rebind a gamepad action
The user SHALL be able to select Thrust or Fire on the page and then press a button on the selected gamepad to bind it (Thrust also takes a trigger, see below). While the game waits for the button the entry SHALL say so. Buttons of other connected gamepads SHALL be ignored while waiting. The new button SHALL replace all buttons previously bound to that action of that gamepad, take effect immediately, including in the game started afterwards, and SHALL be shown on the page.

#### Scenario: Rebind fire
- **WHEN** the user selects "Fire" for a pad and presses the Y button of that pad
- **THEN** the page shows Y for fire, and in a game that pad's Y fires while A and X no longer fire

#### Scenario: Another pad is ignored while waiting
- **WHEN** the user selects "Thrust" for pad X and presses a button on pad Z of another model
- **THEN** the binding is unchanged and the page still waits for a button of pad X

#### Scenario: Pressing buttons outside the page
- **WHEN** no entry is waiting for a button and a gamepad button is pressed on the page
- **THEN** no binding changes

### Requirement: Conflicting and reserved buttons
The game SHALL refuse a button that is already bound to the other action of the same gamepad (thrust buttons count only while thrust is on buttons), or that is reserved (the D-pad buttons where the platform reports the D-pad as buttons), SHALL keep the previous binding and SHALL tell the user why. Back/Start (always reserved) or Escape while waiting for a button SHALL cancel the rebind and SHALL NOT pause, leave or close the page. Left stick and D-pad movement while waiting SHALL be ignored.

#### Scenario: Button already in use
- **WHEN** the user rebinds "Fire" and presses the button currently bound to "Thrust" on that pad
- **THEN** the binding for "Fire" is unchanged and a message says the button is already used for Thrust

#### Scenario: Reserved button
- **WHEN** on a platform that reports the D-pad as buttons the user rebinds "Thrust" and presses a D-pad button
- **THEN** the binding is unchanged and a message says the button is reserved

#### Scenario: Same button on another pad
- **WHEN** pad Z has Fire on Y and the user binds Thrust of pad X to Y
- **THEN** the binding of pad X is accepted

#### Scenario: Cancel with Back
- **WHEN** the user selects "Fire" and presses the gamepad's Back button
- **THEN** the binding is unchanged, the page stays open and no waiting message remains

#### Scenario: Cancel with Escape
- **WHEN** the user selects "Fire" and presses Escape on the keyboard
- **THEN** the binding is unchanged and the page stays open

### Requirement: Thrust on a trigger
The "Thrust" entry SHALL also take a trigger: after selecting it, pulling a trigger of the selected gamepad SHALL bind that trigger to thrust, as pressing a button binds the button, so one entry serves both. Triggers that rest at either end of their range SHALL work the same. The left stick SHALL be ignored while waiting, and "Fire" SHALL wait for a button only. Binding a button to Thrust SHALL replace a bound trigger; binding a trigger SHALL replace the thrust buttons.

#### Scenario: Bind a trigger
- **WHEN** the user selects "Thrust" and pulls the right trigger of the pad
- **THEN** the page shows that thrust is on a trigger

#### Scenario: One entry, button or trigger
- **WHEN** the user selects "Thrust" and presses the X button, then selects it again and pulls a trigger
- **THEN** thrust is first bound to X and then to the trigger, which replaces X

#### Scenario: Back to a button
- **WHEN** thrust is on a trigger and the user selects "Thrust" and presses the Y button
- **THEN** thrust is on Y and the trigger no longer thrusts

#### Scenario: Stick ignored
- **WHEN** the user selects "Thrust" and pushes the left stick
- **THEN** nothing is bound and the page keeps waiting

#### Scenario: Fire ignores triggers
- **WHEN** the user selects "Fire" and pulls a trigger
- **THEN** nothing is bound and the page keeps waiting for a button

### Requirement: Trigger thrust power
While a trigger is bound for a gamepad it SHALL be the only thrust of that pad: the pad's thrust buttons SHALL have no effect, and the thrust power SHALL grow with how far the trigger is pulled, from no thrust at rest (a small dead zone included) to full thrust at the end of its travel. Without a bound trigger, thrust SHALL be full power while the Thrust button is held, as before.

#### Scenario: Half pull gives half power
- **WHEN** a trigger is bound and held half way in a game
- **THEN** the ship accelerates at about half of its full thrust speed, and fully pulled at full speed

#### Scenario: Release stops thrust
- **WHEN** the bound trigger is released
- **THEN** the ship stops thrusting and slows down as without thrust

#### Scenario: Thrust button ignored
- **WHEN** a trigger is bound for a pad and that pad's Thrust button is pressed in a game
- **THEN** the ship does not thrust

#### Scenario: Other players unaffected
- **WHEN** one player of a multiplayer game pulls their bound trigger while another holds the thrust key of their keyboard set
- **THEN** each ship thrusts with its own power

### Requirement: Variable thrust on the gamepad stick
While a game runs, pushing a gamepad's left stick up SHALL thrust with a power that grows with how far it is pushed, from none inside a dead zone near the centre to full at the end of its travel, as the on-screen joystick does. Turning with the stick, and thrust from the D-pad or a Thrust button, SHALL stay on or off at full power. In menus the stick SHALL navigate as before.

#### Scenario: Half push gives half power
- **WHEN** the left stick is held half way up in a game
- **THEN** the ship accelerates at about half of its full thrust speed, and fully pushed at full speed

#### Scenario: Release stops thrust
- **WHEN** the stick returns to the centre or is pushed down
- **THEN** the ship stops thrusting

#### Scenario: Stick and trigger together
- **WHEN** a pad's stick is held half way up while its bound trigger is pulled fully
- **THEN** the ship thrusts at full power, and at the stick's power after the trigger is released

#### Scenario: Menus unchanged
- **WHEN** the left stick is pushed up or down in a menu
- **THEN** the selection moves up or down

### Requirement: Menus keep the standard buttons
Remapped buttons SHALL apply only while a game runs. In every other screen (menus, join and ship selection, pause and confirmation popups, results, leaderboard, nickname entry, settings) every gamepad SHALL use the standard buttons whatever its layout: A and X activate the selected entry and join or get ready, B and Y move the selection up, and the D-pad, left stick and Back/Start navigate as before. A remapped button SHALL do nothing in those screens.

#### Scenario: Remapped fire does not change the menu
- **WHEN** Fire is rebound to the button 9 of a pad and the main menu is shown
- **THEN** pressing A on that pad activates the selected menu entry and pressing button 9 does nothing

#### Scenario: Join with the standard button
- **WHEN** Fire is rebound to another button and that pad presses A on the multiplayer join screen
- **THEN** that pad joins the first free slot

#### Scenario: Remapped buttons play the game
- **WHEN** a game has started after Fire was rebound to button 9
- **THEN** button 9 fires and A does not

### Requirement: Gamepad bindings persist
The game SHALL save changed gamepad layouts, including the trigger, to local storage and restore them on the next launch. If saving fails the bindings SHALL still apply for the session.

#### Scenario: Restored after restart
- **WHEN** the user rebinds "Thrust" of a pad to the X button and the game is restarted with the same pad
- **THEN** pressing X on that pad thrusts the ship in a new game

#### Scenario: Trigger restored after restart
- **WHEN** the user binds a thrust trigger for a pad and the game is restarted with the same pad
- **THEN** that trigger thrusts with variable power in a new game

#### Scenario: Reconnected pad
- **WHEN** a pad with a saved layout is unplugged and plugged in again
- **THEN** it uses its saved layout

### Requirement: Invalid or unidentified gamepad data
If the saved gamepad data is missing, unreadable or invalid (unknown actions, non-integer or reserved buttons, a button used twice in a layout, a malformed trigger), the game SHALL fall back to the defaults without failing, for the invalid layout or for all. A gamepad that cannot be identified SHALL use the defaults and its changes SHALL last for the session only.

#### Scenario: Corrupt saved data
- **WHEN** the saved gamepad bindings contain invalid data at launch
- **THEN** the game starts normally with the default gamepad buttons

#### Scenario: Unidentified pad
- **WHEN** a pad cannot be identified and its Fire is rebound on the page
- **THEN** the new button works in that session and after a restart the pad uses the defaults

### Requirement: Reset gamepad bindings
The "Reset to defaults" action on the Gamepad buttons page SHALL restore the default buttons, clear the thrust trigger and save the result for the selected gamepad only. It SHALL leave other gamepads' layouts and keyboard bindings unchanged.

#### Scenario: Reset
- **WHEN** the user has rebound "Fire" to Y, "Thrust" to X and bound a trigger for pad X and activates "Reset to defaults"
- **THEN** A and X fire and B and Y thrust on pad X, its trigger is cleared, and the layout of pad Z and the keyboard bindings are unchanged
