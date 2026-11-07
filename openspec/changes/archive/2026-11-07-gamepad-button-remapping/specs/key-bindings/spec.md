# Spec Delta

## MODIFIED Requirements

### Requirement: Settings screen access
The main menu "Settings" button SHALL be enabled and SHALL open a settings screen offering "Keyboard layout", "Gamepad buttons" and "Touch controls". "Keyboard layout" SHALL open a screen listing thrust, turn left, turn right and fire with their currently bound keys. "Gamepad buttons" SHALL open the gamepad bindings page (see gamepad-bindings). Each settings screen SHALL provide a way to go back: from the keyboard layout and the gamepad buttons page to the settings screen, and from the settings screen to the main menu.

#### Scenario: Open and close settings
- **WHEN** the player activates "Settings" in the main menu, then "Keyboard layout", then "Back" twice
- **THEN** the settings screen, the keyboard layout screen, the settings screen and finally the main menu are shown in turn

#### Scenario: Open gamepad buttons
- **WHEN** the player activates "Settings" in the main menu, then "Gamepad buttons", then "Back" twice
- **THEN** the settings screen, the gamepad buttons page, the settings screen and finally the main menu are shown in turn
