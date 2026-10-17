# Spec Delta

## Purpose

Lets players steer, thrust and fire using on-screen controls on any device with a touchscreen, laid out like a classic gamepad, while keyboard and gamepad keep working alongside.

## ADDED Requirements

### Requirement: Joystick layout
While a game is running and the touch controls are visible, the game SHALL show a virtual joystick at the bottom-left and a square red fire button labelled "FIRE" at the bottom-right. The joystick SHALL have a draggable centre knob that follows the finger within the joystick base and returns to the centre on release.

#### Scenario: Layout on a touch device
- **WHEN** a game starts with touch controls visible
- **THEN** a joystick with a centred knob is shown at the bottom-left and a red square button labelled "FIRE" at the bottom-right, and no separate left/right/up buttons are shown

#### Scenario: Knob follows and recentres
- **WHEN** the player drags the knob to the left and lifts the finger
- **THEN** the knob follows the finger while dragging and returns to the centre on release

### Requirement: Control appearance
The touch controls SHALL be translucent so the playfield stays visible, large enough to use with a thumb, and kept about 1 cm away from the screen edges. The fire button SHALL look pressed while held.

#### Scenario: Margin from the edges
- **WHEN** a game starts with touch controls visible
- **THEN** the joystick and the fire button do not touch the screen edges

### Requirement: Joystick directions
Dragging the knob SHALL activate the thrust, turn-left and turn-right actions: up gives thrust, left turns left, right turns right, and a position between up and left or right SHALL activate both actions at once. Dragging down or leaving the knob near the centre SHALL activate nothing. The fire button SHALL work independently, so the joystick and fire can be used with two fingers at once.

#### Scenario: Pure directions
- **WHEN** the player drags the knob straight up, then straight left
- **THEN** the ship thrusts, and then turns left without thrusting

#### Scenario: Between positions
- **WHEN** the player drags the knob to the upper-left
- **THEN** the ship thrusts and turns left at the same time

#### Scenario: Release
- **WHEN** the player lifts the finger from the joystick
- **THEN** thrust and turning stop

#### Scenario: Steer and fire
- **WHEN** the player holds the knob to the left and presses the fire button
- **THEN** the ship keeps turning left while a shot is fired

### Requirement: Shown on touch regardless of device type
The game SHALL show the touch controls on any platform once a touch is received, including devices detected as a TV or a desktop. Detection SHALL only decide the initial visibility; it SHALL NOT prevent the controls from ever appearing.

#### Scenario: Touchscreen on a device detected as TV
- **WHEN** the game runs on a device detected as a TV that has a touchscreen and the player touches the screen during a game
- **THEN** the touch controls appear and drive the ship

#### Scenario: Touch controls initially hidden where no touchscreen is expected
- **WHEN** a game starts on a desktop or TV with no touch received yet and the setting is Auto
- **THEN** the touch controls are not shown

### Requirement: Coexistence with keyboard and gamepad
Keyboard, gamepad and touch input SHALL all remain active at the same time. In Auto mode, pressing a keyboard key or gamepad input SHALL hide the touch controls and the next touch SHALL show them again; hidden controls SHALL NOT block or consume touches meant for other widgets.

#### Scenario: Switch from touch to keyboard
- **WHEN** the touch controls are visible and the player presses an arrow key
- **THEN** the ship responds to the key and the touch controls hide

#### Scenario: Switch back to touch
- **WHEN** the touch controls are hidden after keyboard use and the player touches the screen
- **THEN** the touch controls show again and the keyboard still works afterwards

### Requirement: Touch controls settings page
The settings screen SHALL offer a "Touch controls" page with a mode option (Auto, On, Off, cycled by activating it) and a size option. On SHALL keep the controls visible during games regardless of keyboard or gamepad use, Off SHALL never show them, and Auto SHALL behave as described in the other requirements. The default mode SHALL be Auto.

#### Scenario: Force on
- **WHEN** the player sets the mode to On and then uses the keyboard in a game
- **THEN** the touch controls stay visible

#### Scenario: Force off
- **WHEN** the player sets the mode to Off and touches the screen during a game
- **THEN** the touch controls are not shown

#### Scenario: Reachable by touch
- **WHEN** the player on a touchscreen taps "Settings", "Touch controls" and then the mode option
- **THEN** the mode changes to the next value without needing a keyboard

### Requirement: Touch controls size
The touch controls page SHALL provide a slider that sets the size of the on-screen controls from 50% to 400% of the default (100%), showing the current percentage. The slider SHALL also be adjustable with the left and right keys. The chosen size SHALL apply to both the joystick and the fire button in the next game, and the controls SHALL be limited so that they stay fully on screen and do not overlap each other.

#### Scenario: Larger controls
- **WHEN** the player drags the slider from 100% to 200% and starts a game with touch controls visible
- **THEN** the joystick and the fire button are twice as large as at 100%

#### Scenario: Maximum size on a small screen
- **WHEN** the size is 400% on a screen too small for controls that large
- **THEN** the controls are reduced to fit on screen and do not overlap

#### Scenario: Keyboard adjustment
- **WHEN** the player presses the right key on the touch controls page
- **THEN** the size increases and the displayed percentage updates

#### Scenario: Size stays independent of key bindings
- **WHEN** the player activates "Reset to defaults" on the keyboard layout screen
- **THEN** the touch controls mode and size are unchanged

### Requirement: Touch settings persist
The game SHALL save the touch controls mode and size to local storage and restore them at the next launch. Missing, unreadable or invalid saved data SHALL fall back to Auto and 100% without failing.

#### Scenario: Restored after restart
- **WHEN** the player sets the mode to On and the size to 200% and restarts the game
- **THEN** the touch controls page shows On and 200%, and touch controls are visible at that size (screen permitting) in a new game

#### Scenario: Corrupt saved data
- **WHEN** the saved setting file contains invalid data at launch
- **THEN** the game starts normally with Auto and 100%
